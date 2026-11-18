# Key-pose animation kit for Diver_Rig (2026-11-16, replaces the sine/smoothstep approach of build_diver_anims.py).
# exec in Blender (Diver.blend or DiveGear_Scene.blend). Character faces -Y, left side +X, T-pose rest.
#
# Ideas (README 4-C):
#  - a pose = dict bone -> [(axis, deg)] with axes 'X','Y','Z' = rest-frame world axes, 'T' = twist about the bone,
#    plus ('L', (x, y, z)) = location offset in metres (world rest axes, pelvis/root only).
#  - keys are sparse full-body poses on Bezier curves; transitional keys get a per-bone lag
#    (eyes/head lead, then torso, shoulder, elbow, wrist; legs follow) so joints never start/stop together.
#  - hand contacts are solved with a temporary IK constraint at the key and written back as FK (export stays FK-only).
#  - loops use Cycles modifiers; one-shots get a tiny noise "breathing" layer so no frame is fully still.
import bpy, math
from mathutils import Vector, Quaternion

rig = bpy.data.objects["Diver_Rig"]
D = math.radians
AX = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}
BONES = [b.name for b in rig.data.bones]

LAG = {"head": 0, "neck_01": 1, "spine_03": 2, "spine_02": 3, "spine_01": 3, "pelvis": 4, "root": 0,
       "clavicle_l": 3, "upperarm_l": 4, "lowerarm_l": 6, "hand_l": 8,
       "clavicle_r": 3, "upperarm_r": 4, "lowerarm_r": 6, "hand_r": 8,
       "thigh_l": 5, "calf_l": 7, "foot_l": 9, "ball_l": 10,
       "thigh_r": 6, "calf_r": 8, "foot_r": 10, "ball_r": 11}


def rest3(bn):
    return rig.data.bones[bn].matrix_local.to_3x3()


def quat(bn, rots):
    q = Quaternion()
    Ri = rest3(bn).inverted()
    for ax, v in rots:
        if ax == "L":
            continue
        if ax == "T":
            r = Quaternion((0, 1, 0), D(v))
        else:
            a = Ri @ AX[ax]
            r = Quaternion(a.normalized(), D(v)) if a.length > 1e-6 else Quaternion()
        q = q @ r
    return q


def loc(bn, rots):
    for ax, v in rots:
        if ax == "L":
            return rest3(bn).inverted() @ Vector(v)
    return Vector()


def mirror(spec):
    out = {}
    for bn, rots in spec.items():
        if bn.endswith("_l"):
            out[bn[:-2] + "_r"] = [(ax, (-v if ax in ("Y", "Z", "T") else v)) if ax != "L" else (ax, (-v[0], v[1], v[2]))
                                   for ax, v in rots]
    return out


def sym(left, **extra):
    s = dict(left); s.update(mirror(left)); s.update(extra); return s


def merge(*specs):
    """Later specs add onto earlier ones (same axis -> degrees summed; 'L' replaced)."""
    out = {}
    for s in specs:
        for bn, rots in s.items():
            cur = list(out.get(bn, []))
            for ax, v in rots:
                for i, (a0, v0) in enumerate(cur):
                    if a0 == ax and ax != "L":
                        cur[i] = (ax, v0 + v); break
                    if a0 == ax and ax == "L":
                        cur[i] = (ax, tuple(p + q for p, q in zip(v0, v))); break
                else:
                    cur.append((ax, v))
            out[bn] = cur
    return out


def set_pose(spec):
    for bn in BONES:
        pb = rig.pose.bones[bn]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = quat(bn, spec.get(bn, []))
        pb.location = loc(bn, spec.get(bn, []))
    bpy.context.view_layer.update()


# ---------------- IK solve -> FK ----------------
_ik_empties = {}


def _empty(name):
    e = bpy.data.objects.get(name)
    if not e:
        e = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(e)
    return e


def solve_hands(spec, hands):
    """hands: {'l'|'r': (target_xyz_world, extra_hand_rots)} -> returns spec with upperarm/lowerarm/hand from IK.
    The FK arm pose already in spec is the IK starting guess (decides elbow direction)."""
    ad = rig.animation_data
    keep = (ad.action, getattr(ad, "action_slot", None)) if ad else (None, None)
    if ad:
        ad.action = None              # otherwise depsgraph updates overwrite the pose from the action being built
    try:
        return _solve_hands(spec, hands)
    finally:
        if ad and keep[0]:
            ad.action = keep[0]
            if keep[1] is not None:
                ad.action_slot = keep[1]


def _solve_hands(spec, hands):
    set_pose(spec)
    cons = []
    for side, (tgt, _) in hands.items():
        e = _empty("_IKT_" + side); e.location = Vector(tgt)
        c = rig.pose.bones["lowerarm_" + side].constraints.new("IK")
        c.target = e; c.chain_count = 2; c.use_tail = True; c.iterations = 500
        cons.append((side, c))
    bpy.context.view_layer.update()
    out = {k: list(v) for k, v in spec.items()}
    mats = {}
    for side, _ in cons:
        for bn in ("upperarm_" + side, "lowerarm_" + side):
            mats[bn] = rig.pose.bones[bn].matrix.copy()
    for side, c in cons:
        rig.pose.bones["lowerarm_" + side].constraints.remove(c)
    bpy.context.view_layer.update()
    res = {}
    for side, _ in cons:          # parent first: write upperarm, update, then lowerarm
        for bn in ("upperarm_" + side, "lowerarm_" + side):
            pb = rig.pose.bones[bn]
            m = rig.convert_space(pose_bone=pb, matrix=mats[bn], from_space="POSE", to_space="LOCAL")
            pb.rotation_quaternion = m.to_quaternion()
            bpy.context.view_layer.update()
            res[bn] = m.to_quaternion()
    return out, res


# ---------------- actions & keys ----------------
def new_action(name):
    act = bpy.data.actions.get(name)
    if act:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = act
    if hasattr(rig.animation_data, "action_slot") and len(act.slots):
        rig.animation_data.action_slot = act.slots[0]
    return act


_prev_q = {}


def _drop_keys_after(bn, f):
    act = rig.animation_data.action if rig.animation_data else None
    if not act:
        return
    for fc in fcurves(act):
        if fc.data_path.startswith('pose.bones["%s"]' % bn):
            for kp in reversed(list(fc.keyframe_points)):
                if kp.co.x > f + 0.5:
                    fc.keyframe_points.remove(kp)


def key_pose(frame, spec, lag=1.0, pin=(), hands=None, only=None):
    """Key a full-body pose. lag scales LAG (0 = all bones exactly at frame). pin = bones forced to lag 0.
    hands = IK contacts (see solve_hands); IK bones are keyed with lag 0."""
    ikq = {}
    if hands:
        spec, ikq = solve_hands(spec, hands)
        pin = tuple(pin) + tuple(ikq.keys()) + tuple("hand_" + s for s in hands)
        for s, (_, hrot) in hands.items():
            if hrot is not None:
                spec = dict(spec); spec["hand_" + s] = hrot
    for bn in BONES:
        if only and bn not in only:
            continue
        pb = rig.pose.bones[bn]
        q = ikq.get(bn) or quat(bn, spec.get(bn, []))
        pq = _prev_q.get(bn)
        if pq is not None and pq.dot(q) < 0:
            q = -q
        _prev_q[bn] = q.copy()
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = q
        f = frame + (0 if bn in pin else round(LAG.get(bn, 0) * lag))
        _drop_keys_after(bn, f)       # a lagged key from an earlier pose must not overtake this one
        pb.keyframe_insert("rotation_quaternion", frame=f)
        if bn in ("pelvis", "root"):
            pb.location = loc(bn, spec.get(bn, []))
            pb.keyframe_insert("location", frame=f)


def fcurves(act):
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
        return list(act.fcurves)
    out = []
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out += list(cb.fcurves)
    return out


def finish(act, start, end, loop=False, noise=0.0, seed=0, layer=1.0, legs=1.0, arms=False, spine=1.0, smooth=2):
    """Key curves -> per-frame bake with (1) temporal smoothing (removes snaps where lagged keys bunch up) and
    (2) an additive 'floating' layer: breathing, buoyancy bob, slow head drift, slow fin sculling (+ arm drift).
    Loops: layer is periodic over the clip. One-shots: layer fades to 0 at both ends so clips blend cleanly."""
    _finish_curves(act, start, end, loop)
    return postprocess(act, start, end, loop, layer, legs, arms, spine, smooth, seed)


def _finish_curves(act, start, end, loop):
    _prev_q.clear()
    for fc in fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"; kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()
        if loop:
            fc.modifiers.new("CYCLES")


def _qrot(bn, ax, deg):
    if ax == "T":
        return Quaternion((0, 1, 0), D(deg))
    a = rest3(bn).inverted() @ AX[ax]
    return Quaternion(a.normalized(), D(deg))


def postprocess(act, f0, f1, loop, layer, legs, arms, spine, smooth, seed):
    scene = bpy.context.scene
    name = act.name
    rig.animation_data.action = act
    if hasattr(rig.animation_data, "action_slot") and len(act.slots):
        rig.animation_data.action_slot = act.slots[0]
    N = f1 - f0 + 1
    Q = {bn: [] for bn in BONES}; L = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        for bn in BONES:
            Q[bn].append(rig.pose.bones[bn].rotation_quaternion.copy())
        L.append(rig.pose.bones["pelvis"].location.copy())
    # --- temporal smoothing (binomial kernel, wraps for loops)
    W = {0: [1], 1: [1, 2, 1], 2: [1, 4, 6, 4, 1], 3: [1, 6, 15, 20, 15, 6, 1]}[smooth]
    h = len(W) // 2; ws = sum(W)
    idx = (lambda i: i % N) if loop else (lambda i: min(max(i, 0), N - 1))
    for bn in BONES:
        qs = Q[bn]
        for i in range(1, N):
            if qs[i].dot(qs[i - 1]) < 0: qs[i] = -qs[i]
        out = []
        for i in range(N):
            acc = Quaternion((0, 0, 0, 0))
            for k, w in enumerate(W):
                q = qs[idx(i + k - h)]
                if q.dot(qs[i]) < 0: q = -q
                acc = Quaternion([a + w * b for a, b in zip(acc, q)])
            acc = Quaternion([a / ws for a in acc]); acc.normalize(); out.append(acc)
        Q[bn] = out
    L = [sum((L[idx(i + k - h)] * w for k, w in enumerate(W)), Vector()) / ws for i in range(N)]
    # --- floating layer
    rnd = (seed * 0.37) % 1.0
    for i in range(N):
        t = i / N
        if loop:
            cyc = lambda period: max(1, round(N / period))        # whole cycles per loop
            env = 1.0
            ph = lambda period, off=0.0: math.sin(math.tau * (cyc(period) * t + off + rnd))
        else:
            env = max(0.0, math.sin(math.pi * i / (N - 1))) ** 0.7 if N > 1 else 0
            ph = lambda period, off=0.0: math.sin(math.tau * (i / period + off + rnd))
        A = layer * env
        b = ph(84)                                   # breathing ~3.5 s
        bob = ph(110, 0.3)                           # buoyancy ~4.6 s
        hd1, hd2 = ph(130, 0.6), ph(70, 0.15)        # slow head drift
        fin = ph(64, 0.4)                            # slow fin scull ~2.7 s
        adds = {
            "spine_03": [("X", -1.4 * b * spine)], "spine_02": [("X", -0.7 * b * spine), ("Z", 0.5 * hd1 * spine)],
            "clavicle_l": [("Y", -1.2 * b)], "clavicle_r": [("Y", 1.2 * b)], "neck_01": [("X", 0.8 * b)],
            "head": [("Z", 2.2 * hd1), ("X", 1.2 * hd2)], "pelvis": [("X", 1.0 * bob * spine)],
            "thigh_l": [("X", 4.0 * fin * legs)], "thigh_r": [("X", -4.0 * fin * legs)],
            "calf_l": [("X", 5.0 * ph(64, 0.55) * legs)], "calf_r": [("X", -5.0 * ph(64, 0.55) * legs)],
            "foot_l": [("X", 7.0 * ph(64, 0.7) * legs)], "foot_r": [("X", -7.0 * ph(64, 0.7) * legs)],
        }
        if arms:
            adds.update({"upperarm_l": [("Z", 2.5 * ph(96, 0.2))], "upperarm_r": [("Z", -2.5 * ph(96, 0.45))],
                         "lowerarm_l": [("Z", -3.0 * ph(96, 0.35))], "lowerarm_r": [("Z", 3.0 * ph(96, 0.6))],
                         "hand_l": [("T", -6 * ph(48, 0.1))], "hand_r": [("T", 6 * ph(48, 0.5))]})
        for bn, rots in adds.items():
            q = Q[bn][i]
            for ax, deg in rots:
                q = q @ _qrot(bn, ax, deg * A)
            Q[bn][i] = q
        L[i] = L[i] + rest3("pelvis").inverted() @ Vector((0, 0, 0.012 * bob * A))
    # --- rewrite as a clean per-frame action
    bpy.data.actions.remove(act)
    act = new_action(name)
    for i in range(N):
        f = f0 + i
        for bn in BONES:
            pb = rig.pose.bones[bn]; pb.rotation_quaternion = Q[bn][i]
            pb.keyframe_insert("rotation_quaternion", frame=f)
        rig.pose.bones["pelvis"].location = L[i]
        rig.pose.bones["pelvis"].keyframe_insert("location", frame=f)
    for fc in fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    act.frame_range = (f0, f1)
    act.use_frame_range = True
    if hasattr(act, "use_cyclic"):
        act.use_cyclic = loop
    return act
