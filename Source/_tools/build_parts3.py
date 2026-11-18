# Parts / map props set 3 (2026-11-16). exec after mk.py in DiveGear_Scene.blend.
#   DomeGlass (submarine bow dome, replacement part), MotorRotor, SealantCan (waterproof sealant),
#   StreetLamp (map prop, SOCKET_Light), CopperWire (coil), Welder (welding machine + leads)
# Each model: root empty at its pivot, mesh children in root-local coords (pivot = origin). Front = +X.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

random.seed(3)
ROW_Y = -3.0


def model(name, x, specs, z=0.0, sockets=()):
    col = get_col(name)
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    objs = [finish(col, nm, bm, m, smooth=sm) for nm, bm, m, sm in specs]
    root = make_root(col, name, objs, (x, ROW_Y, z))
    for sk in sockets:
        socket(col, root, *sk)
    return root


def merged(bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("_t"); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out


# ------------------------------------------------------------------ 1) DomeGlass: acrylic bow dome + clamp ring (axis +X)
g_glass = mat("M_DomeGlass_Acrylic", (0.55, 0.75, 0.8), metal=0.0, rough=0.03, alpha=0.35)
g_metal = mat("M_DomeGlass_Ring", (0.35, 0.36, 0.38), metal=0.9, rough=0.35)
g_rubber = mat("M_DomeGlass_Gasket", (0.02, 0.02, 0.02), rough=0.8)
g_bolt = mat("M_DomeGlass_Bolt", (0.75, 0.75, 0.72), metal=1.0, rough=0.25)
R, TH = 0.95, 0.03
prof = [(R * math.cos(a), R * math.sin(a)) for a in (math.radians(i * 90 / 16) for i in range(17))]
prof += [((R - TH) * math.cos(a), (R - TH) * math.sin(a)) for a in (math.radians(90 - i * 90 / 16) for i in range(17))]
prof = [(max(r, 0.0), z + 0.06) for r, z in prof]
TOX = RY(90)                                              # lathe axis Z -> +X
spec = [("DG_Dome", lathe(prof + [prof[0]], 48, TOX), g_glass, True),
        ("DG_Flange", lathe([(0.9, 0.0), (1.07, 0.0), (1.07, 0.06), (0.9, 0.06), (0.9, 0.0)], 48, TOX), g_metal, True),
        ("DG_Gasket", lathe([(0.915, 0.055), (0.955, 0.055), (0.955, 0.075), (0.915, 0.075), (0.915, 0.055)], 48, TOX), g_rubber, True)]
bolts = []
for k in range(20):
    a = k / 20 * math.tau
    bolts.append(cyl(0.022, 0.025, 6, (0, 0, 0), T(0.07, 1.01 * math.cos(a), 1.01 * math.sin(a)) @ RY(90)))
spec.append(("DG_Bolts", merged(bolts), g_bolt, False))
for s in (-1, 1):                                          # lifting eyes for a crane / two divers
    spec.append((f"DG_Eye_{s}", torus(0.045, 0.012, 16, 6, T(0.03, s * 0.55, 0.93) @ RY(90) @ RX(90)), g_metal, True))
root_dg = model("DomeGlass", -3.6, spec, z=1.07)

# ------------------------------------------------------------------ 2) MotorRotor: shaft, laminated core with copper bars, commutator, bearings, fan (axis X)
r_steel = mat("M_Rotor_Shaft", (0.7, 0.7, 0.72), metal=1.0, rough=0.25)
r_core = mat("M_Rotor_Core", (0.18, 0.18, 0.2), metal=0.8, rough=0.45)
r_cu = mat("M_Rotor_Copper", (0.85, 0.42, 0.2), metal=1.0, rough=0.3)
r_ins = mat("M_Rotor_Insulation", (0.6, 0.12, 0.05), rough=0.6)
CZ = 0.09
ax = lambda m=Matrix.Identity(4): T(0, 0, CZ) @ RY(90) @ m
spec = [("RT_Shaft", cyl(0.02, 0.56, 16, (0, 0, 0), ax()), r_steel, True),
        ("RT_Core", cyl(0.08, 0.22, 36, (0, 0, -0.01), ax()), r_core, True)]
lam = [torus(0.0805, 0.0015, 36, 4, ax(T(0, 0, -0.12 + 0.22 * i / 14))) for i in range(15)]
spec.append(("RT_Laminations", merged(lam), r_steel, False))
bars = []
for k in range(24):
    a = k / 24 * math.tau
    bars.append(box((0.012, 0.012, 0.24), (0, 0, 0), ax(RZ(math.degrees(a)) @ T(0.082, 0, -0.01))))
spec.append(("RT_Bars", merged(bars), r_cu, False))
spec.append(("RT_EndRings", merged([torus(0.074, 0.012, 32, 8, ax(T(0, 0, z))) for z in (-0.125, 0.105)]), r_cu, True))
comm = [cyl(0.036, 0.06, 24, (0, 0, 0.17), ax())]
spec.append(("RT_Commutator", merged(comm), r_cu, True))
spec.append(("RT_CommSlots", merged([box((0.004, 0.074, 0.062), (0, 0, 0.17), ax(RZ(k * 22.5))) for k in range(8)]), r_core, False))
spec.append(("RT_CommInsul", cyl(0.03, 0.015, 24, (0, 0, 0.135), ax()), r_ins, True))
spec.append(("RT_Bearings", merged([lathe([(0.02, z - 0.012), (0.042, z - 0.012), (0.042, z + 0.012), (0.02, z + 0.012), (0.02, z - 0.012)], 24, ax())
                                    for z in (-0.23, 0.23)]), r_steel, True))
fan = [box((0.004, 0.05, 0.03), (0, 0, 0), ax(RZ(k * 45) @ T(0, 0.045, -0.17) @ RY(20))) for k in range(8)]
fan.append(cyl(0.032, 0.03, 20, (0, 0, -0.17), ax()))
spec.append(("RT_Fan", merged(fan), r_core, False))
spec.append(("RT_Key", box((0.012, 0.006, 0.05), (0, 0.021, 0.255), ax()), r_steel, False))
root_rt = model("MotorRotor", -1.4, spec)

# ------------------------------------------------------------------ 3) SealantCan: waterproof sealant tin with bail handle
s_tin = mat("M_Sealant_Tin", (0.7, 0.72, 0.74), metal=1.0, rough=0.3)
s_label = mat("M_Sealant_Label", (0.05, 0.25, 0.62), rough=0.5)
s_stripe = mat("M_Sealant_Stripe", (0.95, 0.85, 0.15), rough=0.5)
s_grip = mat("M_Sealant_Grip", (0.05, 0.05, 0.05), rough=0.7)
s_goo = mat("M_Sealant_Goo", (0.55, 0.57, 0.6), rough=0.25)
H, RC = 0.20, 0.085
spec = [("SL_Body", lathe([(0, 0), (RC - 0.004, 0), (RC, 0.006), (RC, H - 0.01), (RC + 0.004, H - 0.004), (RC + 0.004, H), (0, H)], 32), s_tin, True),
        ("SL_Label", cyl(RC + 0.0015, 0.12, 32, (0, 0, 0.085)), s_label, True),
        ("SL_Stripe", cyl(RC + 0.0025, 0.02, 32, (0, 0, 0.12)), s_stripe, True),
        ("SL_Lid", lathe([(0, H + 0.006), (RC - 0.01, H + 0.006), (RC - 0.006, H), (0, H)], 32), s_tin, True),
        ("SL_Ears", merged([box((0.012, 0.02, 0.03), (s * (RC + 0.006), 0, H - 0.03)) for s in (-1, 1)]), s_tin, False)]
bail = [Vector((-(RC + 0.008), 0, H - 0.03)), Vector((-0.07, 0, H + 0.06)), Vector((0, 0, H + 0.095)), Vector((0.07, 0, H + 0.06)), Vector((RC + 0.008, 0, H - 0.03))]
spec.append(("SL_Bail", tube(catmull(bail, 6), 0.003, up=(0, 1, 0), sides=6), s_tin, True))
spec.append(("SL_Grip", cyl(0.012, 0.07, 12, (0, 0, 0), T(0, 0, H + 0.093) @ RY(90)), s_grip, True))
drip = [Vector((0.06, -0.058, H + 0.004)), Vector((0.062, -0.062, H - 0.02)), Vector((0.063, -0.063, H - 0.06)), Vector((0.062, -0.062, H - 0.085))]
spec.append(("SL_Drip", tube(catmull(drip, 4), lambda s: 0.008 * (1 - 0.3 * s) + 0.004 * (s > 0.9), sides=6), s_goo, True))
root_sl = model("SealantCan", -0.75, spec)

# ------------------------------------------------------------------ 4) StreetLamp: seabed street light (map prop), lamp head faces +X
l_metal = mat("M_StreetLamp_Metal", (0.12, 0.16, 0.15), metal=0.7, rough=0.5)
l_conc = mat("M_StreetLamp_Concrete", (0.42, 0.41, 0.38), rough=0.95)
l_lens = mat("M_StreetLamp_Lens", (1.0, 0.85, 0.6), emit=(1.0, 0.82, 0.55), strength=12.0)
l_rust = mat("M_StreetLamp_Rust", (0.3, 0.13, 0.05), rough=0.9)
l_yellow = mat("M_StreetLamp_Hazard", (0.9, 0.7, 0.05), rough=0.6)
TOP = 3.1
spec = [("SLP_Plinth", cyl(0.24, 0.14, 8, (0, 0, 0.07)), l_conc, False),
        ("SLP_BasePlate", cyl(0.16, 0.02, 24, (0, 0, 0.15)), l_metal, True),
        ("SLP_Bolts", merged([cyl(0.014, 0.03, 6, (0.12 * math.cos(a), 0.12 * math.sin(a), 0.17)) for a in (k * math.pi / 2 + math.pi / 4 for k in range(4))]), l_rust, False),
        ("SLP_Post", lathe([(0, 0.16), (0.075, 0.16), (0.075, 0.32), (0.062, 0.36), (0.055, 1.6), (0.045, TOP), (0, TOP)], 20), l_metal, True),
        ("SLP_Rings", merged([torus(r, 0.01, 20, 6, T(0, 0, z)) for r, z in ((0.068, 0.34), (0.058, 1.2), (0.05, 2.4))]), l_metal, True),
        ("SLP_Hazard", cyl(0.0625, 0.12, 20, (0, 0, 0.5)), l_yellow, True),
        ("SLP_Box", box((0.07, 0.16, 0.24), (0.075, 0, 1.0)), l_metal, False),
        ("SLP_BoxDoor", box((0.006, 0.13, 0.2), (0.112, 0, 1.0)), l_rust, False)]
arm = [Vector((0, 0, TOP - 0.25)), Vector((0, 0, TOP + 0.05)), Vector((0.2, 0, TOP + 0.22)), Vector((0.5, 0, TOP + 0.24)), Vector((0.72, 0, TOP + 0.14))]
spec.append(("SLP_Arm", tube(catmull(arm, 6), 0.035, up=(0, 1, 0), sides=12), l_metal, True))
spec.append(("SLP_Brace", tube(catmull([Vector((0, 0, TOP - 0.45)), Vector((0.2, 0, TOP - 0.15)), Vector((0.42, 0, TOP + 0.2))], 5), 0.015, up=(0, 1, 0), sides=8), l_metal, True))
HX, HZ = 0.78, TOP + 0.06
spec.append(("SLP_Shade", lathe([(0.03, 0.12), (0.09, 0.09), (0.17, 0.0), (0.18, -0.02), (0.15, -0.02)], 24, T(HX, 0, HZ)), l_metal, True))
spec.append(("SLP_Lens", lathe([(0, -0.015), (0.15, -0.015), (0.15, -0.005), (0, 0.0)], 24, T(HX, 0, HZ)), l_lens, True))
spec.append(("SLP_Cap", cyl(0.035, 0.06, 12, (HX, 0, HZ + 0.14)), l_metal, True))
spec.append(("SLP_Cage", merged([box((0.008, 0.008, 0.07), (0, 0, 0), T(HX + 0.15 * math.cos(a), 0.15 * math.sin(a), HZ - 0.05) @ RZ(math.degrees(a))) for a in (k / 6 * math.tau for k in range(6))]
                                 + [torus(0.15, 0.005, 24, 4, T(HX, 0, HZ - 0.085))]), l_metal, False))
rust = []
for k in range(10):                                          # rust streaks running down the post
    a = random.uniform(0, math.tau); z0 = random.uniform(0.6, 2.8); L = random.uniform(0.2, 0.6)
    r0 = 0.055 + 0.003
    pts = [Vector((r0 * math.cos(a), r0 * math.sin(a), z0 - L * i / 5)) for i in range(6)]
    rust.append(strap(pts, Vector((math.cos(a), math.sin(a), 0)), lambda s: 0.02 * (1 - 0.8 * s), 0.002))
spec.append(("SLP_RustRuns", merged(rust), l_rust, False))
root_lp = model("StreetLamp", 2.2, spec, sockets=[("Light", (HX, 0, HZ - 0.02), (0, 90, 0))])

# ------------------------------------------------------------------ 5) CopperWire: hand-wound coil of copper wire, taped, two stripped ends
c_cu = mat("M_CopperWire_Copper", (0.9, 0.45, 0.22), metal=1.0, rough=0.28)
c_tape = mat("M_CopperWire_Tape", (0.05, 0.05, 0.06), rough=0.6)
c_tag = mat("M_CopperWire_Tag", (0.9, 0.9, 0.85), rough=0.6)
RW, rw = 0.13, 0.0045
pts = []
TURNS, PER = 9, 40
for i in range(TURNS * PER + 1):
    a = i / PER * math.tau
    rr = RW + 0.006 * math.sin(i * 0.37) + 0.004 * (i // PER % 3)
    z = rw + 0.0035 * (i / PER) + 0.004 * math.sin(a * 2 + i * 0.01)
    pts.append(Vector((rr * math.cos(a), rr * math.sin(a), z)))
spec = [("CW_Coil", tube(pts, rw, up=(0, 0, 1), sides=6), c_cu, True)]
tail1 = [pts[0], pts[0] + Vector((0.05, -0.04, 0.0)), pts[0] + Vector((0.12, -0.05, 0.0)), pts[0] + Vector((0.17, -0.02, 0.0))]
tail2 = [pts[-1], pts[-1] + Vector((0.03, 0.06, 0.0)), pts[-1] + Vector((-0.02, 0.13, -0.02)), pts[-1] + Vector((-0.08, 0.16, -0.03))]
spec.append(("CW_Tails", merged([tube(catmull(t, 5), rw, sides=6) for t in (tail1, tail2)]), c_cu, True))
ties = []
for k in range(3):                                           # tape wraps around the bundle
    a = k / 3 * math.tau + 0.4
    c = Vector((RW * math.cos(a), RW * math.sin(a), 0.022))
    t = Vector((-math.sin(a), math.cos(a), 0))
    ties.append(torus(0.03, 0.006, 16, 4, Matrix.Translation(c) @ t.to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Diagonal((1.0, 0.75, 1, 1))))
spec.append(("CW_Tape", merged(ties), c_tape, True))
spec.append(("CW_Tag", box((0.05, 0.03, 0.002), (0, 0, 0), T(RW * math.cos(0.4) + 0.03, RW * math.sin(0.4), 0.03) @ RZ(30)), c_tag, False))
root_cw = model("CopperWire", -0.15, spec)

# ------------------------------------------------------------------ 6) Welder: inverter welding machine + electrode holder + ground clamp
w_body = mat("M_Welder_Body", (0.75, 0.12, 0.05), metal=0.3, rough=0.45)
w_panel = mat("M_Welder_Panel", (0.04, 0.04, 0.045), rough=0.5)
w_metal = mat("M_Welder_Metal", (0.6, 0.6, 0.62), metal=1.0, rough=0.3)
w_cable = mat("M_Welder_Cable", (0.03, 0.03, 0.03), rough=0.6)
w_screen = mat("M_Welder_Screen", (0.2, 1.0, 0.3), emit=(0.2, 1.0, 0.3), strength=4.0)
w_red = mat("M_Welder_Red", (0.7, 0.05, 0.04), rough=0.5)
w_cu = mat("M_Welder_Copper", (0.85, 0.45, 0.22), metal=1.0, rough=0.3)
BX, BY, BZ = 0.24, 0.42, 0.30                             # body: front panel faces +X
spec = [("WD_Body", box((BX, BY, BZ), (0, 0, 0.02 + BZ / 2)), w_body, False),
        ("WD_Front", box((0.02, BY + 0.02, BZ + 0.02), (BX / 2 + 0.005, 0, 0.02 + BZ / 2)), w_panel, False),
        ("WD_Back", box((0.02, BY + 0.02, BZ + 0.02), (-BX / 2 - 0.005, 0, 0.02 + BZ / 2)), w_panel, False),
        ("WD_Feet", merged([box((0.04, 0.04, 0.02), (sx * 0.08, sy * 0.17, 0.01)) for sx in (-1, 1) for sy in (-1, 1)]), w_panel, False),
        ("WD_Screen", box((0.004, 0.09, 0.04), (BX / 2 + 0.016, -0.08, 0.25)), w_screen, False),
        ("WD_Knob", merged([cyl(0.028, 0.025, 20, (0, 0, 0), T(BX / 2 + 0.025, 0.08, 0.24) @ RY(90)),
                            box((0.006, 0.006, 0.02), (BX / 2 + 0.039, 0.08, 0.255))]), w_panel, True),
        ("WD_Dinse", merged([cyl(0.022, 0.02, 16, (0, 0, 0), T(BX / 2 + 0.02, y, 0.09) @ RY(90)) for y in (-0.1, 0.1)]), w_metal, True),
        ("WD_DinseRed", torus(0.024, 0.004, 16, 4, T(BX / 2 + 0.018, 0.1, 0.09) @ RY(90)), w_red, True),
        ("WD_Switch", box((0.01, 0.03, 0.04), (-BX / 2 - 0.02, 0.12, 0.26)), w_red, False),
        ("WD_Vents", merged([box((0.12, 0.004, 0.012), (0, s * (BY / 2 + 0.002), 0.08 + k * 0.03)) for s in (-1, 1) for k in range(6)]), w_panel, False)]
hand = [Vector((0, -0.12, 0.02 + BZ)), Vector((0, -0.11, 0.02 + BZ + 0.06)), Vector((0, 0.11, 0.02 + BZ + 0.06)), Vector((0, 0.12, 0.02 + BZ))]
spec.append(("WD_Handle", strap(hand, (1, 0, 0), 0.04, 0.02), w_panel, False))
# leads: electrode holder (stinger) and ground clamp lying on the floor in loose loops
lead1 = [Vector((BX / 2 + 0.03, -0.1, 0.09)), Vector((0.25, -0.15, 0.03)), Vector((0.42, -0.05, 0.015)), Vector((0.5, 0.15, 0.015)),
         Vector((0.35, 0.3, 0.015)), Vector((0.2, 0.22, 0.015)), Vector((0.3, 0.05, 0.015)), Vector((0.55, -0.1, 0.015)), Vector((0.7, -0.2, 0.02))]
lead2 = [Vector((BX / 2 + 0.03, 0.1, 0.09)), Vector((0.22, 0.2, 0.03)), Vector((0.3, 0.38, 0.015)), Vector((0.15, 0.5, 0.015)), Vector((0.0, 0.42, 0.015))]
spec.append(("WD_Leads", merged([tube(catmull(l, 5), 0.011, sides=8) for l in (lead1, lead2)]), w_cable, True))
st = Vector((0.7, -0.2, 0.025)); d = (lead1[-1] - lead1[-2]).normalized()
STM = Matrix.Translation(st) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
spec.append(("WD_StingerGrip", cyl(0.022, 0.16, 16, (0, 0, 0.08), STM), w_red, True))
spec.append(("WD_StingerJaw", merged([box((0.03, 0.012, 0.07), (0, s * 0.01, 0.19), STM) for s in (-1, 1)] + [cyl(0.003, 0.25, 6, (0, 0, 0), STM @ T(0, 0, 0.21) @ RY(60) @ T(0, 0, 0.12))]), w_metal, False))
gc = Vector((0.0, 0.42, 0.02)); d2 = (lead2[-1] - lead2[-2]).normalized()
GCM = Matrix.Translation(gc) @ d2.to_track_quat("Z", "Y").to_matrix().to_4x4()
spec.append(("WD_ClampJaws", merged([box((0.03, 0.012, 0.12), (0, 0, 0.07), GCM @ RX(s * 8)) for s in (-1, 1)]), w_cu, False))
spec.append(("WD_ClampSpring", torus(0.012, 0.004, 12, 4, GCM @ T(0, 0, 0.06) @ RX(90)), w_metal, True))
root_wd = model("Welder", 0.55, spec)

bpy.context.view_layer.update()
print("PARTS3", [r.name for r in (root_dg, root_rt, root_sl, root_lp, root_cw, root_wd)])
