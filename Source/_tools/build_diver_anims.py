# Diver interaction animations (2026-11-09) on Diver_Rig, 24 fps, in place (no root motion):
#   DV_SwimIdle (loop), DV_Swim (loop), DV_Pickup, DV_Repair (loop), DV_Install
# Poses are written as rotations about world axes in each bone's rest frame (character faces -Y, left arm +X).
# exec after mk.py, rig.py
from mathutils import Quaternion
rig = bpy.data.objects["Diver_Rig"]
D = math.radians
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
BONES = [b.name for b in rig.data.bones if b.name != "root"]
for pb in rig.pose.bones:
    pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)


def bq(bone, axis, deg):
    R = rig.data.bones[bone].matrix_local.to_3x3()
    ax = R.inverted() @ axis
    return Quaternion(ax.normalized(), D(deg)) if ax.length > 1e-6 else Quaternion()


def twist(bone, deg):                       # about the bone's own length (local Y)
    return Quaternion((0, 1, 0), D(deg))


def mirror(spec):
    """Left-side spec -> right side (flip Y/Z rotation signs, keep X)."""
    out = {}
    for bone, rots in spec.items():
        if bone.endswith("_l"):
            out[bone[:-2] + "_r"] = [(ax, -deg if ax in ("Y", "Z", "T") else deg) for ax, deg in rots]
    return out


AXES = {"X": X, "Y": Y, "Z": Z}
def apply(f, spec):
    """spec: bone -> [(axis 'X'|'Y'|'Z'|'T', degrees)]; unlisted bones return to rest."""
    for bn in BONES:
        q = Quaternion()
        for ax, deg in spec.get(bn, []):
            q = q @ (twist(bn, deg) if ax == "T" else bq(bn, AXES[ax], deg))
        pb = rig.pose.bones[bn]; pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", frame=f)


def blend(a, b, t):
    """Interpolate two specs (per-axis degree lists of equal shape, missing = 0)."""
    out = {}
    for bn in set(a) | set(b):
        ra, rb = a.get(bn, []), b.get(bn, [])
        axes = [ax for ax, _ in ra] + [ax for ax, _ in rb if ax not in [x for x, _ in ra]]
        da = dict(ra); db = dict(rb)
        out[bn] = [(ax, da.get(ax, 0.0) + (db.get(ax, 0.0) - da.get(ax, 0.0)) * t) for ax in axes]
    return out


def merge(*specs):
    """Combine specs; rotations about the same axis on the same bone are added."""
    out = {}
    for s in specs:
        for bn, rots in s.items():
            cur = dict(out.get(bn, [])); order = [ax for ax, _ in out.get(bn, [])]
            for ax, deg in rots:
                if ax not in cur: order.append(ax)
                cur[ax] = cur.get(ax, 0.0) + deg
            out[bn] = [(ax, cur[ax]) for ax in order]
    return out


def sym(left, **extra):
    s = dict(left); s.update(mirror(left)); s.update(extra); return s


def new_act(name, frames):
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = act
    if hasattr(rig.animation_data, "action_slot") and len(act.slots): rig.animation_data.action_slot = act.slots[0]
    return act


def finish_act(act, frames):
    act.frame_range = (1, frames)
    if hasattr(rig.animation_data, "action_slot") and len(act.slots): rig.animation_data.action_slot = act.slots[0]


ease = lambda x: (lambda t: t * t * (3 - 2 * t))(max(0.0, min(1.0, x)))

# ---------------- base poses ----------------
LEGS_HOVER = {"thigh_l": [("X", -12)], "calf_l": [("X", 28)], "foot_l": [("X", 40)],
              "thigh_r": [("X", 4)], "calf_r": [("X", 18)], "foot_r": [("X", 40)]}
HOVER = merge(sym({"upperarm_l": [("Z", -22), ("Y", 68)], "lowerarm_l": [("Z", -38)], "hand_l": [("Y", 12)], "clavicle_l": [("Y", 4)]}),
              LEGS_HOVER, {"pelvis": [("X", 14)], "spine_02": [("X", 4)], "head": [("X", -10)]})
HOLD = merge(sym({"upperarm_l": [("Z", -52), ("Y", 48)], "lowerarm_l": [("Z", -98)], "hand_l": [("Y", 8)]}),
             LEGS_HOVER, {"pelvis": [("X", 12)], "spine_02": [("X", 6)], "head": [("X", 4)]})
WORK = merge({"upperarm_l": [("Z", -66), ("Y", 22)], "lowerarm_l": [("Z", -55)], "hand_l": [("Y", 10)],
              "upperarm_r": [("Z", 70), ("Y", -18)], "lowerarm_r": [("Z", 62)], "hand_r": [("Y", -8)]},
             LEGS_HOVER, {"pelvis": [("X", 6)], "spine_02": [("X", 6)], "spine_03": [("X", 3)], "head": [("X", 12)]})

# ---------------- DV_SwimIdle ----------------
F = 64; act = new_act("DV_SwimIdle", F)
for f in range(1, F + 1):
    t = (f - 1) / (F - 1); s = math.sin(math.tau * t); c = math.cos(math.tau * t)
    apply(f, merge(HOVER, {"spine_03": [("X", 2 * s)], "thigh_l": [("X", 5 * s)], "thigh_r": [("X", -5 * s)],
                           "upperarm_l": [("Z", 4 * c)], "upperarm_r": [("Z", -4 * c)], "head": [("Z", 4 * math.sin(math.tau * t * 0.5 * 2))]}))
finish_act(act, F)

# ---------------- DV_Swim (horizontal, flutter kick) ----------------
F = 32; act = new_act("DV_Swim", F)
SWIM = merge(sym({"upperarm_l": [("Z", -30), ("Y", 78)], "lowerarm_l": [("Z", -95)], "hand_l": [("Y", 10)]}),
             {"pelvis": [("X", 78)], "spine_03": [("X", -8)], "neck_01": [("X", -25)], "head": [("X", -30)]})
for f in range(1, F + 1):
    t = (f - 1) / (F - 1); ph = math.tau * t
    k = {"thigh_l": [("X", 18 * math.sin(ph))], "thigh_r": [("X", -18 * math.sin(ph))],
         "calf_l": [("X", 20 + 15 * math.sin(ph - 1.0))], "calf_r": [("X", 20 - 15 * math.sin(ph - 1.0))],
         "foot_l": [("X", 45 + 12 * math.sin(ph - 1.8))], "foot_r": [("X", 45 - 12 * math.sin(ph - 1.8))],
         "spine_01": [("Z", 2 * math.sin(ph))]}
    apply(f, merge(SWIM, k))
finish_act(act, F)

# ---------------- DV_Pickup (grab at frame 20) ----------------
F = 40; act = new_act("DV_Pickup", F)
BEND = merge({"upperarm_l": [("Z", -30), ("Y", 58)], "lowerarm_l": [("Z", -30)],
              "upperarm_r": [("Z", 72), ("Y", -38)], "lowerarm_r": [("Z", 12)], "hand_r": [("X", 18)]},
             {"pelvis": [("X", 55)], "spine_01": [("X", 10)], "spine_02": [("X", 10)], "spine_03": [("X", 6)], "head": [("X", -18)],
              "thigh_l": [("X", -38)], "calf_l": [("X", 62)], "foot_l": [("X", 40)], "thigh_r": [("X", -22)], "calf_r": [("X", 48)], "foot_r": [("X", 40)]})
REACH = merge(BEND, {"pelvis": [("X", 10)], "upperarm_r": [("Z", 12), ("Y", 14)], "hand_r": [("X", 6)]})
CHEST = merge({"upperarm_l": [("Z", -25), ("Y", 62)], "lowerarm_l": [("Z", -40)],
               "upperarm_r": [("Z", 40), ("Y", -66)], "lowerarm_r": [("Z", 112)], "hand_r": [("Y", -12)]},
              LEGS_HOVER, {"pelvis": [("X", 22)], "spine_02": [("X", 6)], "head": [("X", 8)]})
KEYS = [(1, HOVER), (11, BEND), (18, REACH), (22, REACH), (31, CHEST), (40, HOVER)]
for f in range(1, F + 1):
    for (f0, a), (f1, b) in zip(KEYS, KEYS[1:]):
        if f0 <= f <= f1:
            apply(f, blend(a, b, ease((f - f0) / (f1 - f0)))); break
finish_act(act, F)

# ---------------- DV_Repair (loop) ----------------
F = 48; act = new_act("DV_Repair", F)
for f in range(1, F + 1):
    t = (f - 1) / (F - 1); ph = math.tau * t
    k = {"lowerarm_r": [("T", 38 * math.sin(ph * 2))], "upperarm_r": [("Z", 7 * math.sin(ph * 2 + 0.6)), ("Y", 5 * math.cos(ph * 2))],
         "hand_r": [("Z", 15 * math.sin(ph * 2 + 1.2))],
         "upperarm_l": [("Z", 2 * math.sin(ph * 3))], "spine_02": [("X", 2.5 * math.sin(ph))],
         "head": [("Z", 6 * math.sin(ph)), ("X", 3 * math.sin(ph * 2))],
         "thigh_l": [("X", 4 * math.sin(ph))], "thigh_r": [("X", -4 * math.sin(ph))]}
    apply(f, merge(WORK, k))
finish_act(act, F)

# ---------------- DV_Install (part goes in at frame 16) ----------------
F = 36; act = new_act("DV_Install", F)
PUSH = merge(sym({"upperarm_l": [("Z", -80), ("Y", 18)], "lowerarm_l": [("Z", -18)], "hand_l": [("Y", 6)]}),
             LEGS_HOVER, {"pelvis": [("X", 14)], "spine_02": [("X", 10)], "spine_03": [("X", 4)], "head": [("X", 10)]})
TWIST = merge(PUSH, {"hand_r": [("T", 55)], "hand_l": [("T", 55)], "lowerarm_r": [("T", 25)], "lowerarm_l": [("T", 25)]})
LET = merge(sym({"upperarm_l": [("Z", -60), ("Y", 35)], "lowerarm_l": [("Z", -45)]}), LEGS_HOVER, {"pelvis": [("X", 12)], "head": [("X", 4)]})
KEYS = [(1, HOLD), (12, PUSH), (16, PUSH), (21, TWIST), (25, TWIST), (30, LET), (36, HOVER)]
for f in range(1, F + 1):
    for (f0, a), (f1, b) in zip(KEYS, KEYS[1:]):
        if f0 <= f <= f1:
            apply(f, blend(a, b, ease((f - f0) / (f1 - f0)))); break
finish_act(act, F)

_a = bpy.data.actions["DV_SwimIdle"]; rig.animation_data.action = _a
if hasattr(rig.animation_data, "action_slot") and len(_a.slots): rig.animation_data.action_slot = _a.slots[0]
print("DV_ANIMS", [(a.name, tuple(a.frame_range)) for a in bpy.data.actions if a.name.startswith("DV_")])
