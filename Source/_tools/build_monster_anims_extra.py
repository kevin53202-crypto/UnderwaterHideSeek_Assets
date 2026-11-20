# Extra monster clips (2026-11-20): <X>_Search (looking for divers, loop) and <X>_Hit (struck / flashlight flinch) for
# Gigantura, DeepSeaEel and Kraken, added onto the rigs already in the scene (the isopod gets IS_Search / IS_Hit in
# build_isopod_v3.py).  Also keys the root location to 0 in the older clips that never keyed it, so the attack lunge
# offset no longer leaks into idle / swim on export.
# exec after mk.py + rig.py (uses key / new_action).  Then export_skeletal(rig, "SK_<name>") per rig.
import math
from mathutils import Vector, Quaternion
D = math.radians
TAU = math.tau


def ease(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def actions_of(prefix):
    return [a for a in bpy.data.actions if a.name.startswith(prefix)]


def _fcurves(act):
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
        return list(act.fcurves)
    return [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def key_missing_root(rig, prefix, root):
    """Old clips without root-location keys: key (0,0,0) at the first frame."""
    path = 'pose.bones["%s"].location' % root
    for act in actions_of(prefix):
        if any(fc.data_path == path for fc in _fcurves(act)):
            continue
        rig.animation_data.action = act
        if hasattr(rig.animation_data, "action_slot") and len(act.slots):
            rig.animation_data.action_slot = act.slots[0]
        pb = rig.pose.bones[root]; pb.location = (0, 0, 0)
        pb.keyframe_insert("location", frame=int(act.frame_range[0]))
        print("ROOTKEY", act.name, flush=True)


# ---------------------------------------------------------------- fish (Gigantura, eel): spine yaw = local Z, jaw/head pitch = local X
def fish_clips(rig, P, spine, jaw_sign, pecs=()):
    root, head, jaw = P.lower() + "_root", P.lower() + "_head", P.lower() + "_jaw"
    n = len(spine); sc = 6.0 / n                        # per-bone angles shrink with bone count (whole-body curve stays the same)

    new_action(rig, P + "_Search")          # hovering, head sweeps left/right, tastes the water, pecs scull
    F = 96
    for f in range(F + 1):
        t = f / F
        look = D(18) * math.sin(TAU * t) + D(5) * math.sin(TAU * t * 3 + 0.5)
        key(rig.pose.bones[head], f + 1, rot=(D(5) * math.sin(TAU * t * 2 + 1.0), 0, look))
        key(rig.pose.bones[jaw], f + 1, rot=(jaw_sign * (D(4) + D(10) * max(0.0, math.sin(TAU * t * 4)) ** 3), 0, 0))
        for i, bn in enumerate(spine):
            u = i / max(1, n - 1)
            wave = D(2 + 4 * u) * sc * math.sin(TAU * (2 * t - 0.8 * u))
            counter = -look * 0.3 * sc * max(0.0, 1 - 3 * u)                  # neck turns against the head
            key(rig.pose.bones[bn], f + 1, rot=(D(2) * math.sin(TAU * t + u), 0, wave + counter))
        for k, bn in enumerate(pecs):
            key(rig.pose.bones[bn], f + 1, rot=(D(12) * math.sin(TAU * t * 4 + k * math.pi), 0, 0))
        key(rig.pose.bones[root], f + 1, rot=(0, 0, 0), loc=(0, 0, 0.03 * math.sin(TAU * t * 2)))
    rig.animation_data.action.frame_range = (1, F + 1)

    new_action(rig, P + "_Hit")             # jerks into a C-curve away from the hit, jaw snaps, thrashes, recovers
    F = 30
    for f in range(F + 1):
        j = ease(f / 3) * (1 - ease((f - 7) / 18))
        thrash = math.sin(TAU * f / 9) * math.exp(-f / 9)
        key(rig.pose.bones[head], f + 1, rot=(D(12) * j, 0, -D(22) * j + D(8) * thrash))
        key(rig.pose.bones[jaw], f + 1, rot=(jaw_sign * D(32) * ease(f / 2) * (1 - ease((f - 8) / 6)), 0, 0))
        for i, bn in enumerate(spine):
            u = i / max(1, n - 1)
            key(rig.pose.bones[bn], f + 1, rot=(D(2) * j * sc, 0, (D(9) * j * (1 - 1.6 * u) + D(9) * u * thrash) * sc))
        for k, bn in enumerate(pecs):
            key(rig.pose.bones[bn], f + 1, rot=(D(28) * j, 0, 0))
        key(rig.pose.bones[root], f + 1, rot=(0, 0, 0), loc=(0, 0.3 * ease(f / 4) * (1 - ease((f - 10) / 18)), 0.04 * j))
    rig.animation_data.action.frame_range = (1, F + 1)


g_rig = bpy.data.objects["Gigantura_Rig"]
key_missing_root(g_rig, "GT_", "gt_root")
fish_clips(g_rig, "GT", sorted(b.name for b in g_rig.data.bones if b.name.startswith("gt_spine_")), -1,
           tuple(b.name for b in g_rig.data.bones if b.name.startswith("gt_pec_")))
e_rig = bpy.data.objects["DeepSeaEel_Rig"]
key_missing_root(e_rig, "EEL_", "eel_root")
fish_clips(e_rig, "EEL", sorted(b.name for b in e_rig.data.bones if b.name.startswith("eel_spine_")), 1)   # 12 (v2) or 16 (v3) bones


# ---------------------------------------------------------------- Kraken: per-limb curl / side-sway axes (as in build_kraken.py)
k_rig = bpy.data.objects["Kraken_Rig"]
key_missing_root(k_rig, "KR_", "kr_root")
CH = [["kr_arm%d_%d" % (a, k) for k in range(1, 7)] for a in range(1, 9)] + \
     [["kr_tent%s_%d" % (s, k) for k in range(1, 9)] for s in ("R", "L")]
AXES = {}
for ch in CH:
    h = k_rig.data.bones[ch[0]].head_local
    o = Vector((h.x, 0, h.z)).normalized()
    for bn in ch:
        b = k_rig.data.bones[bn]; d = (b.tail_local - b.head_local).normalized()
        AXES[bn] = (o.cross(d).normalized(), o)


def kq(bn, axis, ang):
    ax = k_rig.data.bones[bn].matrix_local.to_3x3().inverted() @ axis
    return Quaternion(ax.normalized(), ang) if ax.length > 1e-6 else Quaternion()


def pose_k(f, fn):
    for ci, ch in enumerate(CH):
        club = ch[0].startswith("kr_tent")
        for k, bn in enumerate(ch):
            curl, side = fn(ci, k, len(ch), club)
            ca, sa = AXES[bn]
            key(k_rig.pose.bones[bn], f, rot=(kq(bn, ca, curl) @ kq(bn, sa, side)).to_euler("XYZ"))


def mantle_k(f, z, x):
    for k, bn in enumerate(("kr_mantle_01", "kr_mantle_02", "kr_mantle_03")):
        key(k_rig.pose.bones[bn], f, rot=(x * (k + 1) * 0.5, 0, z * (k + 1) * 0.6))


bpy.context.view_layer.objects.active = k_rig
new_action(k_rig, "KR_Search")              # arms reach out one after another and feel around; the two long tentacles sweep ahead
F = 96
for f in range(F + 1):
    t = f / F
    def search(ci, k, n, club):
        if club:
            return (D(-8 + 6 * math.sin(TAU * (t * 2 - 0.1 * k) + ci)), D(10) * math.sin(TAU * t + ci * math.pi - 0.15 * k))
        probe = max(0.0, math.sin(TAU * (t - ci / 8))) ** 2
        return (D(-16) * probe * (1 - 0.1 * k) + D(5 + 2 * k) * math.sin(TAU * (t * 2 - 0.15 * k) + ci),
                D(7) * math.sin(TAU * (t + ci / 8) - 0.2 * k))
    pose_k(f + 1, search)
    mantle_k(f + 1, D(5) * math.sin(TAU * t + 0.4), D(3) * math.sin(TAU * t * 2))
    key(k_rig.pose.bones["kr_head"], f + 1, rot=(D(3) * math.sin(TAU * t * 2), 0, D(12) * math.sin(TAU * t)))
    key(k_rig.pose.bones["kr_root"], f + 1, rot=(0, 0, 0), loc=(0, 0, 0.04 * math.sin(TAU * t * 2)))
k_rig.animation_data.action.frame_range = (1, F + 1)

new_action(k_rig, "KR_Hit")                 # all arms snap inward, mantle clenches, jerks back, then unfurls
F = 30
for f in range(F + 1):
    j = ease(f / 3) * (1 - ease((f - 8) / 18))
    def hit(ci, k, n, club):
        wob = D(4) * math.sin(TAU * f / 8 + ci + 0.4 * k) * math.exp(-f / 10)
        if club:                                         # same curl direction as KR_Attack's grab: base in, tip back out
            return (D(14) * j * (1 if k < 3 else -0.4) + wob * 0.5, 0.0)
        return (D(28 + 5 * k) * j + wob, 0.0)
    pose_k(f + 1, hit)
    mantle_k(f + 1, 0.0, -D(10) * j)
    key(k_rig.pose.bones["kr_head"], f + 1, rot=(D(10) * j, 0, D(6) * math.sin(TAU * f / 10) * math.exp(-f / 10)))
    key(k_rig.pose.bones["kr_root"], f + 1, rot=(0, 0, 0), loc=(0, 0.4 * ease(f / 4) * (1 - ease((f - 10) / 18)), 0.05 * j))
k_rig.animation_data.action.frame_range = (1, F + 1)

for r_, a_ in ((g_rig, "GT_Swim"), (e_rig, "EEL_Swim"), (k_rig, "KR_Swim")):
    act = bpy.data.actions[a_]; r_.animation_data.action = act
    if hasattr(r_.animation_data, "action_slot") and len(act.slots):
        r_.animation_data.action_slot = act.slots[0]
print("EXTRA_ANIMS", sorted(a.name for a in bpy.data.actions if a.name.split("_")[0] in ("GT", "EEL", "KR")), flush=True)
