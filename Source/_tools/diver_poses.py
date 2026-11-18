# Diver key poses (2026-11-16). exec after anim_kit.py. Degrees about rest-frame world axes:
#  X+ = bend forward (spine) / leg back (thigh) / knee bend (calf) / toes down (foot)
#  arms (left, +X): Y+ = arm down, Z- = arm forward;  'T' = twist about the bone.
HOVER = merge(sym({"clavicle_l": [("Y", 4)], "upperarm_l": [("Z", -38), ("Y", 58)], "lowerarm_l": [("Z", -70)],
                   "hand_l": [("Y", 12), ("T", -20)],
                   "thigh_l": [("X", -52), ("Y", -8)], "calf_l": [("X", 100)], "foot_l": [("X", 72)]}),
              {"pelvis": [("X", 24)], "spine_02": [("X", 3)], "spine_03": [("X", 2)], "neck_01": [("X", -8)], "head": [("X", -14)],
               "thigh_r": [("X", 14)], "calf_r": [("X", -20)], "foot_r": [("X", -40)]})
