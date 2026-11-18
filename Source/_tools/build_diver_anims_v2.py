# Diver animations v2 (2026-11-16) — hand-placed key poses (README 4-C), replaces build_diver_anims.py.
# exec after anim_kit.py + diver_poses.py.  24 fps, in place (no root motion).
#   DV_SwimIdle (96f loop), DV_Swim (56f loop, frog kick),
#   DV_Pickup (72f, GrabItem @34),
#   DV_Repair_Start (24f) / DV_Repair_LoopA (48f, wrench) / DV_Repair_LoopB (36f, two-hand strain) /
#   DV_Repair_LoopC (36f, inspect) / DV_Repair_End (24f)  — loops start & end on the same WORK pose,
#   DV_Install (48f, AttachPart @24, LockPart @36)
V = Vector

for old in ["DV_Repair"]:
    if bpy.data.actions.get(old):
        bpy.data.actions.remove(bpy.data.actions[old])

def side_r(rots):                     # write a right-hand rotation using left-side conventions
    return [(ax, (-v if ax in ("Y", "Z", "T") else v)) for ax, v in rots]

# ---------------------------------------------------------------- DV_SwimIdle (96f loop)
act = new_action("DV_SwimIdle")
BREATH_IN = {"spine_03": [("X", -2.5)], "spine_02": [("X", -1)], "clavicle_l": [("Y", -3)], "clavicle_r": [("Y", 3)], "neck_01": [("X", 1.5)]}
SCULL_A = sym({"lowerarm_l": [("Z", -8)], "hand_l": [("T", -18), ("Y", -6)]})
SCULL_B = sym({"lowerarm_l": [("Z", 6)], "hand_l": [("T", 12), ("Y", 6)]})
KEYS = [
    (1,  merge(HOVER)),
    (22, merge(HOVER, BREATH_IN, SCULL_A, {"head": [("Z", 9), ("X", -4)], "thigh_l": [("X", 5)], "thigh_r": [("X", -4)]})),
    (44, merge(HOVER, SCULL_B, {"head": [("Z", 3), ("X", 3)], "pelvis": [("X", 2)],
                                # small one-legged fin scull to hold position
                                "thigh_r": [("X", 12)], "calf_r": [("X", -22)], "foot_r": [("X", 18)]})),
    (60, merge(HOVER, BREATH_IN, {"head": [("Z", -10), ("X", -2)], "thigh_r": [("X", -4)], "calf_r": [("X", 8)],
                                  "lowerarm_r": [("Z", 10)], "hand_r": [("T", 15)]})),
    (78, merge(HOVER, SCULL_A, {"head": [("Z", -4), ("X", 4)], "pelvis": [("X", -2)], "thigh_l": [("X", -6)]})),
    (97, merge(HOVER)),
]
for f, p in KEYS:
    key_pose(f, p, lag=1.0)
finish(act, 1, 96, loop=True, arms=True, legs=0.7)

# ---------------------------------------------------------------- DV_Swim (56f loop, frog kick)
act = new_action("DV_Swim")
SWIM_UP = {"pelvis": [("X", 82)], "spine_01": [("X", -3)], "spine_02": [("X", -4)], "spine_03": [("X", -6)],
           "neck_01": [("X", -30)], "head": [("X", -38)]}
ARMS_TUCK = sym({"clavicle_l": [("Z", -6)], "upperarm_l": [("Z", -55), ("Y", 70)], "lowerarm_l": [("Z", -110)],
                 "hand_l": [("Y", 5), ("T", -30)]})
BODY = merge(SWIM_UP, ARMS_TUCK)
GLIDE = sym({"thigh_l": [("X", 2), ("Y", -3)], "calf_l": [("X", 12)], "foot_l": [("X", 55)]})
GLIDE2 = sym({"thigh_l": [("X", -2), ("Y", -5)], "calf_l": [("X", 22)], "foot_l": [("X", 45)]})
RECOV = sym({"thigh_l": [("X", -20), ("Y", -14), ("T", 25)], "calf_l": [("X", 105)], "foot_l": [("X", -5), ("T", -20)]})
TURN = sym({"thigh_l": [("X", -16), ("Y", -26), ("T", 30)], "calf_l": [("X", 95)], "foot_l": [("X", -15), ("T", -35)]})
POWER = sym({"thigh_l": [("X", 4), ("Y", -22), ("T", 10)], "calf_l": [("X", 35)], "foot_l": [("X", 20), ("T", -15)]})
SNAP = sym({"thigh_l": [("X", 6), ("Y", -2)], "calf_l": [("X", 6)], "foot_l": [("X", 62)]})
SURGE = {"spine_03": [("X", -3)], "head": [("X", -3)], "pelvis": [("X", -2)]}
KEYS = [
    (1,  merge(BODY, GLIDE2)),
    (14, merge(BODY, RECOV, {"pelvis": [("X", 2)]})),
    (21, merge(BODY, TURN, {"pelvis": [("X", 2)]})),
    (28, merge(BODY, POWER, SURGE)),
    (34, merge(BODY, SNAP, SURGE)),
    (46, merge(BODY, GLIDE, {"head": [("Z", 4)]})),
    (57, merge(BODY, GLIDE2)),
]
for f, p in KEYS:
    key_pose(f, p, lag=0.6)
finish(act, 1, 56, loop=True, arms=True, legs=0.2, layer=0.8)

# ---------------------------------------------------------------- DV_Pickup (72f)
act = new_action("DV_Pickup")
ITEM = V((-0.12, -0.76, 0.62))         # wrist target at the item (front ~76cm, ~70cm below the shoulders)
LOOK = merge(HOVER, {"neck_01": [("X", 8)], "head": [("X", 20)]})
BEND = merge(HOVER, {"pelvis": [("X", 36), ("L", (0, -0.04, -0.02))], "spine_01": [("X", 8)], "spine_02": [("X", 10)],
                     "spine_03": [("X", 6)], "neck_01": [("X", 4)], "head": [("X", 10)],
                     "thigh_l": [("X", 22)], "thigh_r": [("X", 14)], "calf_l": [("X", -10)],
                     "upperarm_r": side_r([("Z", -20), ("Y", -10)]),
                     # left arm reaches forward-out for balance
                     "upperarm_l": [("Z", -10), ("Y", -14)], "lowerarm_l": [("Z", 30)]})
KICK = merge(BEND, {"thigh_l": [("X", 14)], "calf_l": [("X", -45)], "foot_l": [("X", 10)],
                    "thigh_r": [("X", 10)], "calf_r": [("X", -30)]})
REACH = merge(BEND, {"pelvis": [("X", 6), ("L", (0, -0.05, -0.03))], "spine_03": [("X", 3)], "head": [("X", 4)]})
CURL = side_r([("Y", 16), ("T", -12)])           # wrist folds round the part
OPEN = side_r([("Y", -10), ("T", -15)])
RISE = merge(HOVER, {"pelvis": [("X", 14)], "spine_02": [("X", 4)], "head": [("X", 14)]})
INSPECT = merge(HOVER, {"head": [("X", 16), ("Z", -8), ("Y", 8)], "neck_01": [("X", 6)], "spine_03": [("X", 3)]})
KEYS = [
    (1,  HOVER, 0, None),
    (9,  LOOK, 1.0, None),                                           # eyes find the part first
    (20, KICK, 1.0, None),                                           # one small fin kick while tipping forward
    (31, REACH, 0.6, {"r": (ITEM + V((0.02, 0.04, 0.09)), OPEN)}),   # hand arrives above the part
    (34, REACH, 0, {"r": (ITEM, OPEN)}),                             # touch -> GrabItem
    (37, REACH, 0, {"r": (ITEM + V((0, 0, -0.012)), CURL)}),         # hesitate, wrist wraps
    (42, REACH, 0, {"r": (ITEM + V((0, 0.01, -0.02)), CURL)}),       # weight: hand dips
    (51, RISE, 0.8, {"r": (V((-0.10, -0.50, 0.95)), CURL)}),         # elbow leads, part comes to the body
    (58, INSPECT, 0.8, {"r": (V((-0.06, -0.44, 1.12)), side_r([("Y", 10), ("T", 40)]))}),  # look at it
    (65, HOVER, 0.8, {"r": (V((-0.21, -0.20, 0.82)), side_r([("Y", 20)]))}),  # into the thigh pocket
    (72, HOVER, 0, None),
]
for f, p, lg, hands in KEYS:
    key_pose(f, p, lag=lg, hands=hands)
finish(act, 1, 72, seed=3, legs=0.6, spine=0.6, smooth=2)

# ---------------------------------------------------------------- Repair (panel in front, chest height)
BOLT = V((-0.06, -0.57, 1.26)); GRIP = V((0.22, -0.52, 1.42)); R = 0.10
WORK = merge(HOVER, {"pelvis": [("X", -6)], "spine_02": [("X", 4)], "spine_03": [("X", 4)], "neck_01": [("X", 2)], "head": [("X", 8)],
                     "thigh_l": [("X", 34)], "calf_l": [("X", 14)], "foot_l": [("X", 4)],
                     "thigh_r": [("X", 30)], "calf_r": [("X", 28)], "foot_r": [("X", 30)],
                     "upperarm_l": [("Z", -30), ("Y", -20)], "upperarm_r": side_r([("Z", -25), ("Y", -15)])})
GRIP_ROT = [("Y", -15), ("T", 60)]

def wrench(deg):           # hand position on the wrench handle, deg measured in the panel plane (0 = handle pointing right/-X)
    a = D(deg); return BOLT + V((-math.cos(a) * R, 0.02, math.sin(a) * R))

def wrot(deg):
    return side_r([("T", -40 + deg * 0.8), ("Y", 5)])

W0 = 25
WH = {"l": (GRIP, GRIP_ROT), "r": (wrench(W0), wrot(W0))}

act = new_action("DV_Repair_Start")
KEYS = [
    (1, HOVER, 0, None),
    (7, merge(HOVER, {"head": [("X", 8), ("Z", -6)], "neck_01": [("X", 3)]}), 1.0, None),
    (11, merge(WORK, {"pelvis": [("L", (0, 0.03, 0))]}), 0.7, {"l": (GRIP + V((0.02, 0.05, 0.05)), [("Y", -25), ("T", 40)])}),
    (18, WORK, 0, {"l": (GRIP, GRIP_ROT), "r": (wrench(W0) + V((0, 0.08, -0.06)), wrot(W0))}),
    (24, WORK, 0, WH),
]
for f, p, lg, hands in KEYS:
    key_pose(f, p, lag=lg, hands=hands)
finish(act, 1, 24, seed=5, spine=0.5, smooth=1)

act = new_action("DV_Repair_LoopA")       # wrench: 3 short strokes (Ratchet notify at 8 / 24 / 39)
PULL = {"spine_03": [("Z", 3), ("X", 1.5)], "pelvis": [("L", (0.006, 0.008, 0))], "clavicle_r": [("Y", 4)]}
KEYS = [(1, WORK, WH)]
for t0, sweep, dur in ((1, 70, 16), (17, 85, 15), (32, 60, 17)):
    KEYS.append((t0 + 7, merge(WORK, PULL), {"l": (GRIP, GRIP_ROT), "r": (wrench(W0 - sweep), wrot(W0 - sweep))}))
    KEYS.append((t0 + 9, merge(WORK, PULL), {"l": (GRIP, GRIP_ROT), "r": (wrench(W0 - sweep - 3), wrot(W0 - sweep - 3))}))
    KEYS.append((t0 + dur - 2, WORK, {"l": (GRIP, GRIP_ROT), "r": (wrench(W0 + 4), wrot(W0 + 4))}))
KEYS = [k for k in KEYS if k[0] < 47] + [(49, WORK, WH)]
for f, p, hands in KEYS:
    key_pose(min(f, 49), p, lag=(0 if f in (1, 49) else 0.5), hands=hands)
finish(act, 1, 48, seed=8, spine=0.4, smooth=1)

act = new_action("DV_Repair_LoopB")       # two-handed strain on a stuck bolt (Strain notify at 16)
BRACE = merge(WORK, {"clavicle_l": [("Y", -7)], "clavicle_r": [("Y", 7)], "spine_02": [("X", 5)], "spine_03": [("X", 4)],
                     "head": [("X", 6)], "thigh_l": [("X", -10)], "calf_l": [("X", 15)], "thigh_r": [("X", -8)]})
TWO = lambda d: {"l": (wrench(d) + V((-0.07, 0.0, 0.02)), [("Y", 10), ("T", 70)]), "r": (wrench(d), wrot(d))}
KEYS = [
    (1, WORK, WH),
    (8, WORK, {"l": (wrench(W0) + V((-0.04, 0.04, 0.08)), [("Y", -10), ("T", 50)]), "r": (wrench(W0), wrot(W0))}),
    (12, BRACE, TWO(W0)),
    (20, merge(BRACE, {"spine_02": [("X", 2)], "head": [("X", 3)]}), TWO(W0 - 12)),   # bolt barely moves
    (26, merge(WORK, {"spine_03": [("X", -2)]}), TWO(W0 - 55)),                        # gives way, body unfolds
    (32, WORK, {"l": (GRIP + V((0.02, 0.04, 0.04)), GRIP_ROT), "r": (wrench(W0 - 40), wrot(W0 - 40))}),
    (37, WORK, WH),
]
for f, p, hands in KEYS:
    key_pose(f, p, lag=(0 if f in (1, 37) else 0.5), hands=hands)
finish(act, 1, 36, seed=9, spine=0.4, smooth=1)

act = new_action("DV_Repair_LoopC")       # stop, peer in with the headlamp, wipe the panel (Inspect notify at 10)
PEER = merge(WORK, {"spine_03": [("X", 6)], "neck_01": [("X", 6)], "head": [("Z", 14), ("Y", 10), ("X", 6)],
                    "pelvis": [("L", (0, -0.02, 0))]})
KEYS = [
    (1, WORK, WH),
    (8, PEER, {"l": (GRIP, GRIP_ROT), "r": (wrench(W0) + V((0.0, 0.10, -0.04)), side_r([("Y", 15)]))}),
    (16, merge(PEER, {"head": [("Z", -6)]}), {"l": (GRIP, GRIP_ROT), "r": (V((-0.16, -0.55, 1.22)), side_r([("Y", -20), ("T", 80)]))}),
    (25, merge(PEER, {"head": [("Z", -14)]}), {"l": (GRIP, GRIP_ROT), "r": (V((0.04, -0.55, 1.33)), side_r([("Y", -20), ("T", 80)]))}),
    (31, WORK, {"l": (GRIP, GRIP_ROT), "r": (wrench(W0) + V((0, 0.05, 0.02)), wrot(W0))}),
    (37, WORK, WH),
]
for f, p, hands in KEYS:
    key_pose(f, p, lag=(0 if f in (1, 37) else 0.5), hands=hands)
finish(act, 1, 36, seed=9, spine=0.4, smooth=1)

act = new_action("DV_Repair_End")
KEYS = [
    (1, WORK, 0, WH),
    (7, WORK, 0, {"l": (GRIP + V((0.03, 0.06, 0.03)), [("Y", -10), ("T", 30)]), "r": (wrench(W0) + V((0, 0.10, -0.05)), wrot(W0))}),
    (14, merge(HOVER, {"pelvis": [("X", -4), ("L", (0, 0.04, 0))]}), 1.0, None),   # push off backwards
    (24, HOVER, 0, None),
]
for f, p, lg, hands in KEYS:
    key_pose(f, p, lag=lg, hands=hands)
finish(act, 1, 24, seed=7, spine=0.5, smooth=1)

# ---------------------------------------------------------------- DV_Install (48f)
act = new_action("DV_Install")
GRIP_ROT_I = [("Y", -15), ("T", -5)]      # less wrist twist coming off the held part
SLOT = V((0.0, -0.60, 1.28))
def held(c, wob=0.0, tw=0.0):
    return {"l": (c + V((0.075, 0, 0)), [("Y", 20), ("T", -60 + tw)]), "r": (c + V((-0.075, 0, 0)), side_r([("Y", 20), ("T", -60 - tw)]))}
HOLD = merge(HOVER, {"spine_03": [("X", 2)], "head": [("X", 10)], "upperarm_l": [("Z", -20)], "upperarm_r": side_r([("Z", -20)])})
PUSH = merge(WORK, {"pelvis": [("L", (0, -0.03, 0))], "spine_02": [("X", 3)]})
KEYS = [
    (1,  HOLD, 0, held(V((0, -0.40, 1.18)))),
    (6,  merge(HOLD, {"head": [("X", 4)]}), 0.6, held(SLOT + V((0.015, 0.11, 0.01)), tw=8)),
    (11, merge(WORK, {"head": [("Z", 4)]}), 0.5, held(SLOT + V((-0.012, 0.09, -0.008)), tw=-8)),
    (15, WORK, 0, held(SLOT + V((0.004, 0.07, 0.004)), tw=3)),
    (22, PUSH, 0, held(SLOT + V((0, 0.012, 0)))),
    (24, PUSH, 0, held(SLOT + V((0, 0.006, 0)))),                     # catches -> AttachPart
    (27, merge(PUSH, {"pelvis": [("L", (0, -0.01, 0))]}), 0, held(SLOT)),
    (32, WORK, 0, {"l": (GRIP, GRIP_ROT_I), "r": (SLOT + V((-0.03, 0.01, 0.03)), side_r([("Y", 10), ("T", -60)]))}),
    (36, merge(WORK, {"spine_03": [("Z", 3)]}), 0, {"l": (GRIP, GRIP_ROT_I), "r": (SLOT + V((-0.035, 0.01, -0.03)), side_r([("Y", 10), ("T", 30)]))}),  # 90 deg turn -> LockPart @36
    (41, merge(WORK, {"head": [("X", -10), ("Z", -8)], "neck_01": [("X", -4)]}), 0.8,
         {"l": (GRIP + V((0.02, 0.05, 0.02)), GRIP_ROT_I), "r": (SLOT + V((-0.06, 0.12, -0.06)), side_r([("Y", 20)]))}),  # watch the warning light go out
    (48, HOVER, 0, None),
]
for f, p, lg, hands in KEYS:
    key_pose(f, p, lag=lg, hands=hands)
finish(act, 1, 48, seed=11, spine=0.4, smooth=1)

for e in [o for o in bpy.data.objects if o.name.startswith("_IKT_")]:
    bpy.data.objects.remove(e)
_a = bpy.data.actions["DV_SwimIdle"]; rig.animation_data.action = _a
if hasattr(rig.animation_data, "action_slot") and len(_a.slots):
    rig.animation_data.action_slot = _a.slots[0]
print("DV_ANIMS", [(a.name, tuple(a.frame_range)) for a in bpy.data.actions if a.name.startswith("DV_")])
