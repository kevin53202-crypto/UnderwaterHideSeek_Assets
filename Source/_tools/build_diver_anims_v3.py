# Diver animations v3 (2026-11-20) — replaces build_diver_anims_v2.py.  exec after anim_kit.py (diver_poses.py not needed).
# Fixes from v2: (1) IK hand targets were world positions while Diver_Rig sits at x=-3.5 in the scene, so the arms
# reached 3.5 m sideways and locked straight ("zombie arms") -> the rig is built at the origin now; (2) the idle stood
# upright like on land -> horizontal-ish frog trim; (3) pickup flipped upright->face-down -> continuous pitch from trim;
# (4) work targets were beyond arm's reach -> panel 45-50 cm in front of a body that leans in, elbows bent.
# 24 fps, in place.  Same names as v2 + new: DV_SwimFast, DV_Hit, DV_Death, DV_Hide_Enter / _Idle / _Exit.
V = Vector
_rig_loc = rig.location.copy(); rig.location = (0, 0, 0); bpy.context.view_layer.update()


def side_r(rots):                     # write a right-hand rotation using left-side conventions
    return [(ax, (-v if ax in ("Y", "Z", "T") else v)) for ax, v in rots]


# ---------------------------------------------------------------- base poses
# Axes (anim_kit): X+ = bend forward (spine) / leg back (thigh) / knee bend (calf) / toes down (foot);
# arms (left): Y+ = arm down, Z- = arm forward; T = twist.  Right side via sym()/side_r().
ARMS_REST = sym({"clavicle_l": [("Y", 3)], "upperarm_l": [("Z", -38), ("Y", 66)], "lowerarm_l": [("Z", -92)],
                 "hand_l": [("Y", 12), ("T", -25)]})                       # forearms folded loosely in front of the belly
FROG = sym({"thigh_l": [("X", 6), ("Y", -12)], "calf_l": [("X", 96)], "foot_l": [("X", 62)]})   # knees out, fins back-up
TRIM = merge({"pelvis": [("X", 52)], "spine_02": [("X", -2)], "spine_03": [("X", -4)], "neck_01": [("X", -16)], "head": [("X", -24)]},
             ARMS_REST, FROG)
BREATH_IN = {"spine_03": [("X", -2.5)], "spine_02": [("X", -1)], "clavicle_l": [("Y", -3)], "clavicle_r": [("Y", 3)], "neck_01": [("X", 1.5)]}
SCULL_A = sym({"lowerarm_l": [("Z", -10)], "hand_l": [("T", -20), ("Y", -8)]})
SCULL_B = sym({"lowerarm_l": [("Z", 8)], "hand_l": [("T", 14), ("Y", 8)]})

# ---------------------------------------------------------------- DV_SwimIdle (96f loop): hover in trim
act = new_action("DV_SwimIdle")
KEYS = [
    (1,  TRIM),
    (20, merge(TRIM, BREATH_IN, SCULL_A, {"head": [("Z", 12), ("X", -3)]})),                         # look left
    (40, merge(TRIM, SCULL_B, {"head": [("Z", 4), ("X", 4)], "pelvis": [("X", 3)],
                               "thigh_r": [("X", 10)], "calf_r": [("X", -25)], "foot_r": [("X", -12)]})),   # one small fin scull
    (58, merge(TRIM, BREATH_IN, {"head": [("Z", -14), ("X", -2)], "lowerarm_r": [("Z", 10)], "hand_r": [("T", 15)]})),  # look right
    (78, merge(TRIM, SCULL_A, {"head": [("Z", -4), ("X", 3)], "pelvis": [("X", -3)],
                               "thigh_l": [("X", 8)], "calf_l": [("X", -20)]})),
    (97, TRIM),
]
for f, p in KEYS:
    key_pose(f, p, lag=1.0)
finish(act, 1, 96, loop=True, arms=True, legs=0.7)

# ---------------------------------------------------------------- DV_Swim (56f loop, frog kick)
act = new_action("DV_Swim")
SWIM_UP = {"pelvis": [("X", 84)], "spine_01": [("X", -3)], "spine_02": [("X", -4)], "spine_03": [("X", -6)],
           "neck_01": [("X", -30)], "head": [("X", -40)]}
ARMS_TUCK = sym({"clavicle_l": [("Z", -6)], "upperarm_l": [("Z", -50), ("Y", 72)], "lowerarm_l": [("Z", -105)],
                 "hand_l": [("Y", 5), ("T", -30)]})
BODY = merge(SWIM_UP, ARMS_TUCK)
GLIDE = sym({"thigh_l": [("X", 2), ("Y", -4)], "calf_l": [("X", 10)], "foot_l": [("X", 58)]})
GLIDE2 = sym({"thigh_l": [("X", -2), ("Y", -6)], "calf_l": [("X", 20)], "foot_l": [("X", 50)]})
RECOV = sym({"thigh_l": [("X", -8), ("Y", -16), ("T", 20)], "calf_l": [("X", 100)], "foot_l": [("X", 10), ("T", -15)]})
TURN = sym({"thigh_l": [("X", -6), ("Y", -26), ("T", 26)], "calf_l": [("X", 92)], "foot_l": [("X", -5), ("T", -30)]})
POWER = sym({"thigh_l": [("X", 4), ("Y", -20), ("T", 10)], "calf_l": [("X", 40)], "foot_l": [("X", 20), ("T", -15)]})
SNAP = sym({"thigh_l": [("X", 5), ("Y", -3)], "calf_l": [("X", 6)], "foot_l": [("X", 64)]})
SURGE = {"spine_03": [("X", -3)], "head": [("X", -3)], "pelvis": [("X", -2)]}
KEYS = [(1, merge(BODY, GLIDE2)), (14, merge(BODY, RECOV, {"pelvis": [("X", 2)]})), (21, merge(BODY, TURN, {"pelvis": [("X", 2)]})),
        (28, merge(BODY, POWER, SURGE)), (34, merge(BODY, SNAP, SURGE)), (46, merge(BODY, GLIDE, {"head": [("Z", 4)]})), (57, merge(BODY, GLIDE2))]
for f, p in KEYS:
    key_pose(f, p, lag=0.6)
finish(act, 1, 56, loop=True, arms=True, legs=0.2, layer=0.8)

# ---------------------------------------------------------------- DV_SwimFast (28f loop): flee, fast flutter kick, streamlined
act = new_action("DV_SwimFast")
FAST = merge({"pelvis": [("X", 88)], "spine_02": [("X", -4)], "spine_03": [("X", -6)], "neck_01": [("X", -32)], "head": [("X", -44)]},
             sym({"clavicle_l": [("Z", 4)], "upperarm_l": [("Z", 12), ("Y", 82)], "lowerarm_l": [("Z", -8)], "hand_l": [("Y", 4), ("T", -10)]}))   # arms streamlined along the sides
def flutter(s):        # s = +1: left leg up / right leg down-kick
    return {"thigh_l": [("X", 16 * s), ("Y", -3)], "calf_l": [("X", 12 + 26 * max(0, -s))], "foot_l": [("X", 60 + 8 * s)],
            "thigh_r": [("X", -16 * s), ("Y", 3)], "calf_r": [("X", 12 + 26 * max(0, s))], "foot_r": [("X", 60 - 8 * s)],
            "pelvis": [("Y", 3 * s)], "spine_03": [("Y", -2 * s)]}
KEYS = [(1, merge(FAST, flutter(1))), (8, merge(FAST, flutter(-1), {"pelvis": [("X", -2)]})), (15, merge(FAST, flutter(1))),
        (22, merge(FAST, flutter(-1), {"pelvis": [("X", -2)]})), (29, merge(FAST, flutter(1)))]
for f, p in KEYS:
    key_pose(f, p, lag=0.4)
finish(act, 1, 28, loop=True, legs=0.0, layer=0.4)

# ---------------------------------------------------------------- DV_Pickup (72f, GrabItem @34): tip forward from trim, never flip
act = new_action("DV_Pickup")
ITEM = V((-0.10, -0.84, 0.64))                    # right wrist at the part: ~85 cm ahead, ~30 cm below the pelvis
LOOK = merge(TRIM, {"neck_01": [("X", 10)], "head": [("X", 18)]})
TIP = merge(TRIM, {"pelvis": [("X", 26)], "spine_02": [("X", 4)], "spine_03": [("X", 4)], "neck_01": [("X", 12)], "head": [("X", 20)],
                   "thigh_l": [("X", 10)], "calf_l": [("X", -14)], "thigh_r": [("X", 4)],
                   "upperarm_l": [("Z", -20), ("Y", -24)], "lowerarm_l": [("Z", 40)]})        # left arm out for balance
KICK = merge(TIP, {"thigh_l": [("X", 14)], "calf_l": [("X", -40)], "foot_l": [("X", 8)], "thigh_r": [("X", 12)], "calf_r": [("X", -34)]})
REACH = merge(TIP, {"pelvis": [("X", 8), ("L", (0, -0.04, -0.03))], "spine_03": [("X", 3)]})
OPEN = side_r([("Y", -10), ("T", -15)]); CURL = side_r([("Y", 18), ("T", -10)])
RISE = merge(TRIM, {"pelvis": [("X", 10)], "neck_01": [("X", 6)], "head": [("X", 10)]})
INSPECT = merge(TRIM, {"head": [("X", 16), ("Z", -8), ("Y", 8)], "neck_01": [("X", 6)]})
KEYS = [
    (1,  TRIM, 0, None),
    (9,  LOOK, 1.0, None),                                                   # eyes find the part first
    (20, KICK, 1.0, None),                                                   # one small fin kick while tipping forward
    (30, REACH, 0.6, {"r": (ITEM + V((0.02, 0.04, 0.09)), OPEN)}),
    (34, REACH, 0, {"r": (ITEM, OPEN)}),                                     # touch -> GrabItem
    (37, REACH, 0, {"r": (ITEM + V((0, 0, -0.012)), CURL)}),
    (42, REACH, 0, {"r": (ITEM + V((0, 0.01, -0.025)), CURL)}),              # weight: hand dips
    (51, RISE, 0.8, {"r": (V((-0.12, -0.62, 0.98)), CURL)}),                 # elbow leads, part comes to the body
    (58, INSPECT, 0.8, {"r": (V((-0.06, -0.62, 1.12)), side_r([("Y", 10), ("T", 35)]))}),
    (65, TRIM, 0.8, {"r": (V((-0.22, -0.18, 0.86)), side_r([("Y", 20)]))}),  # into the thigh pocket
    (72, TRIM, 0, None),
]
for f, p, lg, hands in KEYS:
    key_pose(f, p, lag=lg, hands=hands)
finish(act, 1, 72, seed=3, legs=0.6, spine=0.6, smooth=2)

# ---------------------------------------------------------------- Repair (panel 45-50 cm in front of the chest)
BOLT = V((-0.06, -0.50, 1.22)); GRIP = V((0.24, -0.44, 1.34)); R = 0.13
WORK = merge({"pelvis": [("X", 22)], "spine_02": [("X", 3)], "spine_03": [("X", 3)], "neck_01": [("X", -4)], "head": [("X", -2)],
              "thigh_l": [("X", 34), ("Y", -8)], "calf_l": [("X", 70)], "foot_l": [("X", 50)],
              "thigh_r": [("X", 26), ("Y", 8)], "calf_r": [("X", 84)], "foot_r": [("X", 56)]},          # knees folded back
             sym({"upperarm_l": [("Z", -40), ("Y", 55)], "lowerarm_l": [("Z", -70)]}))            # IK guess: elbows down/out
GRIP_ROT = [("Y", -15), ("T", 55)]
def wrench(deg):           # hand on the wrench handle; deg in the panel plane (0 = handle pointing right/-X)
    a = D(deg); return BOLT + V((-math.cos(a) * R, 0.02, math.sin(a) * R))
def wrot(deg):
    return side_r([("T", -40 + deg * 0.8), ("Y", 5)])
W0 = 30
WH = {"l": (GRIP, GRIP_ROT), "r": (wrench(W0), wrot(W0))}

act = new_action("DV_Repair_Start")
KEYS = [
    (1, TRIM, 0, None),
    (6, merge(TRIM, {"head": [("X", 6), ("Z", -6)], "neck_01": [("X", 3)]}), 1.0, None),                 # look at the panel
    (13, merge(WORK, {"pelvis": [("X", 8), ("L", (0, 0.05, 0))]}), 0.7, {"l": (GRIP + V((0.02, 0.06, 0.05)), [("Y", -25), ("T", 40)])}),
    (19, WORK, 0, {"l": (GRIP, GRIP_ROT), "r": (wrench(W0) + V((0, 0.08, -0.08)), wrot(W0))}),
    (24, WORK, 0, WH),
]
for f, p, lg, hands in KEYS:
    key_pose(f, p, lag=lg, hands=hands)
finish(act, 1, 24, seed=5, spine=0.5, smooth=1)

act = new_action("DV_Repair_LoopA")       # wrench: 3 short strokes (Ratchet at 8 / 24 / 39)
PULL = {"spine_03": [("Z", 5), ("X", 2)], "spine_02": [("Z", 2)], "pelvis": [("L", (0.01, 0.01, 0))], "clavicle_r": [("Y", 6)], "head": [("Z", -3)]}
KEYS = [(1, WORK, WH)]
for t0, sweep, dur in ((1, 80, 16), (17, 95, 15), (32, 70, 17)):
    KEYS.append((t0 + 7, merge(WORK, PULL), {"l": (GRIP, GRIP_ROT), "r": (wrench(W0 - sweep), wrot(W0 - sweep))}))
    KEYS.append((t0 + 9, merge(WORK, PULL), {"l": (GRIP, GRIP_ROT), "r": (wrench(W0 - sweep - 4), wrot(W0 - sweep - 4))}))
    KEYS.append((t0 + dur - 2, WORK, {"l": (GRIP, GRIP_ROT), "r": (wrench(W0 + 4), wrot(W0 + 4))}))
KEYS = [k for k in KEYS if k[0] < 47] + [(49, WORK, WH)]
for f, p, hands in KEYS:
    key_pose(min(f, 49), p, lag=(0 if f in (1, 49) else 0.5), hands=hands)
finish(act, 1, 48, seed=8, spine=0.4, smooth=1)

act = new_action("DV_Repair_LoopB")       # two-handed strain (Strain at 16)
BRACE = merge(WORK, {"clavicle_l": [("Y", -8)], "clavicle_r": [("Y", 8)], "spine_02": [("X", 6)], "spine_03": [("X", 5)],
                     "head": [("X", 6)], "thigh_l": [("X", -10)], "calf_l": [("X", 15)], "thigh_r": [("X", -8)]})
TWO = lambda d: {"l": (wrench(d) + V((-0.07, 0.0, 0.03)), [("Y", 10), ("T", 70)]), "r": (wrench(d), wrot(d))}
KEYS = [
    (1, WORK, WH),
    (8, WORK, {"l": (wrench(W0) + V((-0.04, 0.05, 0.09)), [("Y", -10), ("T", 50)]), "r": (wrench(W0), wrot(W0))}),
    (12, BRACE, TWO(W0)),
    (20, merge(BRACE, {"spine_02": [("X", 3)], "head": [("X", 4)]}), TWO(W0 - 12)),
    (26, merge(WORK, {"spine_03": [("X", -3)]}), TWO(W0 - 60)),
    (32, WORK, {"l": (GRIP + V((0.02, 0.04, 0.04)), GRIP_ROT), "r": (wrench(W0 - 40), wrot(W0 - 40))}),
    (37, WORK, WH),
]
for f, p, hands in KEYS:
    key_pose(f, p, lag=(0 if f in (1, 37) else 0.5), hands=hands)
finish(act, 1, 36, seed=9, spine=0.4, smooth=1)

act = new_action("DV_Repair_LoopC")       # peer in with the headlamp, wipe the panel (Inspect at 10)
PEER = merge(WORK, {"spine_03": [("X", 6)], "neck_01": [("X", 6)], "head": [("Z", 16), ("Y", 12), ("X", 6)], "pelvis": [("L", (0, -0.03, 0))]})
KEYS = [
    (1, WORK, WH),
    (8, PEER, {"l": (GRIP, GRIP_ROT), "r": (wrench(W0) + V((0.0, 0.10, -0.05)), side_r([("Y", 15)]))}),
    (16, merge(PEER, {"head": [("Z", -8)]}), {"l": (GRIP, GRIP_ROT), "r": (V((-0.18, -0.48, 1.18)), side_r([("Y", -20), ("T", 80)]))}),
    (25, merge(PEER, {"head": [("Z", -16)]}), {"l": (GRIP, GRIP_ROT), "r": (V((0.04, -0.48, 1.30)), side_r([("Y", -20), ("T", 80)]))}),
    (31, WORK, {"l": (GRIP, GRIP_ROT), "r": (wrench(W0) + V((0, 0.05, 0.02)), wrot(W0))}),
    (37, WORK, WH),
]
for f, p, hands in KEYS:
    key_pose(f, p, lag=(0 if f in (1, 37) else 0.5), hands=hands)
finish(act, 1, 36, seed=9, spine=0.4, smooth=1)

act = new_action("DV_Repair_End")
KEYS = [
    (1, WORK, 0, WH),
    (7, WORK, 0, {"l": (GRIP + V((0.03, 0.07, 0.03)), [("Y", -10), ("T", 30)]), "r": (wrench(W0) + V((0, 0.12, -0.06)), wrot(W0))}),
    (15, merge(TRIM, {"pelvis": [("X", -10), ("L", (0, 0.05, 0))]}), 1.0, None),            # push off backwards
    (24, TRIM, 0, None),
]
for f, p, lg, hands in KEYS:
    key_pose(f, p, lag=lg, hands=hands)
finish(act, 1, 24, seed=7, spine=0.5, smooth=1)

# ---------------------------------------------------------------- DV_Install (48f, AttachPart @24, LockPart @36)
act = new_action("DV_Install")
GRIP_ROT_I = [("Y", -15), ("T", -5)]
SLOT = V((0.0, -0.50, 1.24))
def held(c, wob=0.0, tw=0.0):
    return {"l": (c + V((0.075, 0, 0)), [("Y", 20), ("T", -60 + tw)]), "r": (c + V((-0.075, 0, 0)), side_r([("Y", 20), ("T", -60 - tw)]))}
HOLD = merge(TRIM, {"pelvis": [("X", -12)], "head": [("X", 8)]})
PUSH = merge(WORK, {"pelvis": [("L", (0, -0.04, 0))], "spine_02": [("X", 4)]})
KEYS = [
    (1,  HOLD, 0, held(V((0, -0.42, 1.10)))),
    (6,  merge(HOLD, {"head": [("X", 4)]}), 0.6, held(SLOT + V((0.02, 0.12, 0.01)), tw=8)),
    (11, merge(WORK, {"head": [("Z", 4)]}), 0.5, held(SLOT + V((-0.015, 0.10, -0.01)), tw=-8)),
    (15, WORK, 0, held(SLOT + V((0.005, 0.08, 0.005)), tw=3)),
    (22, PUSH, 0, held(SLOT + V((0, 0.012, 0)))),
    (24, PUSH, 0, held(SLOT + V((0, 0.006, 0)))),                     # catches -> AttachPart
    (27, merge(PUSH, {"pelvis": [("L", (0, -0.01, 0))]}), 0, held(SLOT)),
    (32, WORK, 0, {"l": (GRIP, GRIP_ROT_I), "r": (SLOT + V((-0.03, 0.01, 0.03)), side_r([("Y", 10), ("T", -60)]))}),
    (36, merge(WORK, {"spine_03": [("Z", 4)]}), 0, {"l": (GRIP, GRIP_ROT_I), "r": (SLOT + V((-0.035, 0.01, -0.03)), side_r([("Y", 10), ("T", 30)]))}),
    (41, merge(WORK, {"head": [("X", -10), ("Z", -8)], "neck_01": [("X", -4)]}), 0.8,
         {"l": (GRIP + V((0.02, 0.06, 0.02)), GRIP_ROT_I), "r": (SLOT + V((-0.06, 0.13, -0.06)), side_r([("Y", 20)]))}),
    (48, TRIM, 0, None),
]
for f, p, lg, hands in KEYS:
    key_pose(f, p, lag=lg, hands=hands)
finish(act, 1, 48, seed=11, spine=0.4, smooth=1)

# ---------------------------------------------------------------- DV_Hit (28f): struck from the front, recoils, recovers
act = new_action("DV_Hit")
JOLT = merge(TRIM, {"pelvis": [("X", -16), ("L", (0, 0.14, 0.04))], "spine_02": [("X", -8)], "spine_03": [("X", -10)],
                    "neck_01": [("X", -14)], "head": [("X", -18), ("Z", 8)]},
             sym({"upperarm_l": [("Y", -28), ("Z", 22)], "lowerarm_l": [("Z", 40)], "hand_l": [("Y", -20)],
                  "thigh_l": [("X", -18)], "calf_l": [("X", -25)], "foot_l": [("X", -15)]}))
GUARD = merge(TRIM, {"pelvis": [("X", -8), ("L", (0, 0.1, 0.02))], "spine_02": [("X", 8)], "spine_03": [("X", 8)], "neck_01": [("X", 10)], "head": [("X", 14)]},
              sym({"upperarm_l": [("Y", -30), ("Z", -30)], "lowerarm_l": [("Z", -50)], "hand_l": [("Y", -10)]}))   # arms up to protect the mask
KEYS = [(1, TRIM, 0), (4, JOLT, 0.3), (9, merge(JOLT, {"pelvis": [("X", -6)]}), 0.6), (16, GUARD, 0.8), (28, TRIM, 1.0)]
for f, p, lg in KEYS:
    key_pose(f, p, lag=lg)
finish(act, 1, 28, seed=13, smooth=1, layer=0.5)

# ---------------------------------------------------------------- DV_Death (84f): jolt, struggle, go limp, roll and sink
act = new_action("DV_Death")
SPASM = merge(JOLT, {"spine_03": [("Z", 10)], "head": [("Z", -12)]}, sym({"thigh_l": [("X", 30)], "calf_l": [("X", 60)]}))
LIMP = merge({"pelvis": [("X", 70), ("Y", 25), ("L", (0, 0.05, -0.18))], "spine_02": [("X", 10), ("Z", 6)], "spine_03": [("X", 10)],
              "neck_01": [("X", 25)], "head": [("X", 30), ("Z", 10)]},
             sym({"clavicle_l": [("Y", 6)], "upperarm_l": [("Y", 70), ("Z", -5)], "lowerarm_l": [("Z", -25)], "hand_l": [("Y", 25)],
                  "thigh_l": [("X", -12), ("Y", -6)], "calf_l": [("X", 35)], "foot_l": [("X", 45)]}))
SINK = merge(LIMP, {"pelvis": [("Y", 30), ("X", 10), ("L", (0, 0.05, -0.4))], "head": [("X", 6)]},
             {"upperarm_l": [("Y", 8)], "upperarm_r": side_r([("Y", 12)]), "calf_r": [("X", 15)]})
KEYS = [(1, TRIM, 0), (4, JOLT, 0.3), (10, SPASM, 0.5), (18, merge(JOLT, {"head": [("Z", 14)]}), 0.6), (34, LIMP, 1.2), (84, SINK, 1.0)]
for f, p, lg in KEYS:
    key_pose(f, p, lag=lg)
finish(act, 1, 84, seed=17, smooth=2, layer=0.25)

# ---------------------------------------------------------------- Hide: curl up small in a crevice / locker
BALL = merge({"pelvis": [("X", 30), ("L", (0, 0, 0.12))], "spine_01": [("X", 10)], "spine_02": [("X", 14)], "spine_03": [("X", 12)],
              "neck_01": [("X", 6)], "head": [("X", -4)]},
             sym({"clavicle_l": [("Z", -8)], "upperarm_l": [("Z", -62), ("Y", 46)], "lowerarm_l": [("Z", -120)], "hand_l": [("Y", 10), ("T", -30)],
                  "thigh_l": [("X", -105), ("Y", -6)], "calf_l": [("X", 135)], "foot_l": [("X", 55)]}))
act = new_action("DV_Hide_Enter")
KEYS = [(1, TRIM, 0), (8, merge(TRIM, {"head": [("Z", 18)], "neck_01": [("Z", 6)]}), 1.0),                 # glance back
        (18, merge(BALL, {"pelvis": [("X", 8)], "head": [("X", 6)]}), 0.8), (30, BALL, 0.6)]
for f, p, lg in KEYS:
    key_pose(f, p, lag=lg)
finish(act, 1, 30, seed=19, smooth=1, layer=0.5)

act = new_action("DV_Hide_Idle")          # holding still: slow shallow breathing, small peeks toward the opening
SHALLOW = {"spine_03": [("X", -1.5)], "clavicle_l": [("Y", -2)], "clavicle_r": [("Y", 2)]}
KEYS = [(1, BALL), (20, merge(BALL, SHALLOW)), (36, merge(BALL, {"head": [("Z", 14), ("X", -6)], "neck_01": [("Z", 5)]})),   # peek
        (46, merge(BALL, {"head": [("Z", 12), ("X", -4)]})), (60, merge(BALL, SHALLOW, {"head": [("Z", -6)]})), (97, BALL)]
for f, p in KEYS:
    key_pose(f, p, lag=1.0)
finish(act, 1, 96, loop=True, seed=21, legs=0.15, spine=0.5, layer=0.5)

act = new_action("DV_Hide_Exit")
KEYS = [(1, BALL, 0), (8, merge(BALL, {"head": [("Z", -10), ("X", -8)]}), 1.0),
        (16, merge(TRIM, {"pelvis": [("X", -8)], "calf_l": [("X", 20)], "calf_r": [("X", 20)]}), 0.8), (24, TRIM, 0.6)]
for f, p, lg in KEYS:
    key_pose(f, p, lag=lg)
finish(act, 1, 24, seed=23, smooth=1, layer=0.5)

# ---------------------------------------------------------------- tidy up
for e in [o for o in bpy.data.objects if o.name.startswith("_IKT_")]:
    bpy.data.objects.remove(e)
rig.location = _rig_loc
_a = bpy.data.actions["DV_SwimIdle"]; rig.animation_data.action = _a
if hasattr(rig.animation_data, "action_slot") and len(_a.slots):
    rig.animation_data.action_slot = _a.slots[0]
print("DV_ANIMS", [(a.name, tuple(a.frame_range)) for a in bpy.data.actions if a.name.startswith("DV_")])
