# Repair parts set 2 (2026-11-16): 4 new pickups + matching repair points on the submarine.
#   SM_PropBlade        -> Submarine   SOCKET_Repair_Prop      (top propeller blade missing)
#   SM_HullPatch        -> Submarine   SOCKET_Repair_Hull      (crack on the port hull, aft)
#   SM_ScrubberCartridge-> SubInterior SOCKET_Repair_Scrubber  (CO2 scrubber unit, port wall)
#   SM_CircuitBoard     -> SubInterior SOCKET_Repair_Circuit   (card cage in the console front)
# exec after mk.py in DiveGear_Scene.blend. Submarine / SubInterior roots: local frame = hull centre, +X forward.
import bpy, bmesh, math
from mathutils import Vector, Matrix

SUB = bpy.data.objects["Submarine"]; INT = bpy.data.objects["SubInterior"]
COL_SUB = SUB.users_collection[0]; COL_INT = INT.users_collection[0]

M_metal = bpy.data.materials["M_Sub_Metal"]; M_chrome = bpy.data.materials["M_Sub_Chrome"]
M_rust = bpy.data.materials["M_Sub_Rust"]; M_warn = bpy.data.materials["M_Sub_Warning"]
M_dark = bpy.data.materials["M_Sub_Interior"]; M_panel = bpy.data.materials["M_SubIn_Panel"]
M_yellow = bpy.data.materials["M_SubIn_Yellow"]; M_screen = bpy.data.materials["M_SubIn_Screen"]
M_crack = mat("M_Sub_Crack", (0.015, 0.012, 0.01), rough=0.9)
P_steel = bpy.data.materials["M_Part_Steel"]; P_dark = bpy.data.materials["M_Part_Dark"]
P_yellow = bpy.data.materials["M_Part_Yellow"]; P_red = bpy.data.materials["M_Part_Red"]
P_glass = bpy.data.materials["M_Part_Glass"]
P_pcb = mat("M_Part_PCB", (0.03, 0.22, 0.08), rough=0.45)
P_gold = mat("M_Part_Gold", (0.95, 0.7, 0.3), metal=1.0, rough=0.25)
P_canister = mat("M_Part_Canister", (0.62, 0.68, 0.72), metal=0.3, rough=0.4)
P_absorb = mat("M_Part_Absorbent", (0.45, 0.2, 0.6), rough=0.9)
P_rubber = mat("M_Part_Rubber", (0.02, 0.02, 0.02), rough=0.85)


def add(col, name, bm, material, parent, smooth=False):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    o = finish(col, name, bm, material, smooth=smooth)
    o.parent = parent
    return o


def along(n):                       # matrix rotating +Z onto direction n
    return Vector(n).to_track_quat("Z", "Y").to_matrix().to_4x4()


def lamp(col, name, pos, normal, parent):
    n = Vector(normal).normalized()
    add(col, name + "Base", cyl(0.03, 0.02, 16, (0, 0, 0.01), T(*pos) @ along(n)), M_metal, parent)
    add(col, name, lathe([(0.0, 0.035), (0.018, 0.03), (0.022, 0.02), (0.022, 0.0)], 16, T(*pos) @ along(n) @ T(0, 0, 0.02)), M_warn, parent, smooth=True)


# =====================================================================================  SUBMARINE
# ---- 1) propeller: top blade (SUB_Blade_1) is gone, a sheared stub remains
for n in ("SUB_Blade_1",):
    o = bpy.data.objects.get(n)
    if o:
        blade_src = o.data.copy()          # keep its shape for the pickup
        bpy.data.objects.remove(o, do_unlink=True)
    else:
        blade_src = bpy.data.meshes.get("SUB_Blade_1_shape")
blade_src.name = "SUB_Blade_1_shape"; blade_src.use_fake_user = True
HUBX = -3.42
bm = cyl(0.05, 0.025, 20, (0, 0, 0.0125), T(HUBX, 0, 0.115))           # mounting boss on the hub
add(COL_SUB, "SUB_PropBoss", bm, M_chrome, SUB)
bm = bmesh.new()                                                       # jagged sheared stub
pts = [(-0.05, 0.0), (0.05, 0.0), (0.05, 0.035), (0.03, 0.05), (0.012, 0.038), (-0.01, 0.06), (-0.035, 0.042), (-0.05, 0.05)]
vb = [bm.verts.new((HUBX + x, -0.012, 0.14 + z)) for x, z in pts]; vf = [bm.verts.new((HUBX + x, 0.012, 0.14 + z)) for x, z in pts]
bm.faces.new(vb); bm.faces.new(list(reversed(vf)))
for i in range(len(pts)):
    j = (i + 1) % len(pts); bm.faces.new((vb[i], vb[j], vf[j], vf[i]))
add(COL_SUB, "SUB_BladeStub", bm, M_rust, SUB)
for k in range(3):                                                     # empty bolt holes
    a = k / 3 * math.tau
    add(COL_SUB, f"SUB_PropBolt_{k}", cyl(0.007, 0.006, 8, (0, 0, 0.003), T(HUBX + 0.034 * math.cos(a), 0.034 * math.sin(a), 0.14)), M_crack, SUB)
lamp(COL_SUB, "SUB_Warn_Prop", (-3.3, 0.0, 0.72), (0, 0, 1), SUB)
socket(COL_SUB, SUB, "Repair_Prop", (HUBX, 0, 0.14))

# ---- 2) hull crack, port side aft (between hull seams x=-1.6 and -0.9; forward of that the thruster hides it)
R = 1.15; HX = -1.25; PHI = math.asin(0.15 / R)
def hull_pt(x, arc, lift=0.0):                       # arc = metres along the circumference from the crack centre (+ = up)
    a = PHI + arc / R; r = R + lift
    return Vector((x, -r * math.cos(a), r * math.sin(a)))
def hull_n(arc):
    a = PHI + arc / R; return Vector((0, -math.cos(a), math.sin(a)))
crack = [(-0.15, -0.04), (-0.09, -0.01), (-0.05, -0.03), (0.0, 0.01), (0.04, -0.005), (0.08, 0.03), (0.13, 0.02), (0.17, 0.05)]
branches = [[(0.0, 0.01), (0.02, 0.06), (0.05, 0.09)], [(-0.05, -0.03), (-0.03, -0.08), (0.0, -0.11)], [(0.08, 0.03), (0.1, -0.03)]]
bm = bmesh.new()
for line, w in [(crack, 0.024)] + [(b, 0.012) for b in branches]:
    poly = [hull_pt(HX + x, z, 0.004) for x, z in line]
    bm2 = strap(poly, hull_n(0), lambda s, w=w: w * (1 - 0.6 * s), 0.004)
    me = bpy.data.meshes.new("_tmp"); bm2.to_mesh(me); bm2.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
add(COL_SUB, "SUB_HullCrack", bm, M_crack, SUB)
bm = bmesh.new()                                     # rust stain around the crack (conforms to the hull)
ctr = bm.verts.new(hull_pt(HX, 0, 0.002)); ring = []
for k in range(28):
    a = k / 28 * math.tau; rr = 1.0 + 0.18 * math.sin(3 * a + 0.7) + 0.1 * math.sin(7 * a)
    ring.append(bm.verts.new(hull_pt(HX + 0.19 * rr * math.cos(a), 0.11 * rr * math.sin(a) - 0.015, 0.002)))
for k in range(28):
    bm.faces.new((ctr, ring[k], ring[(k + 1) % 28]))
add(COL_SUB, "SUB_HullStain", bm, M_rust, SUB)
bm = bmesh.new()                                     # bent-out lips along the main crack (dented metal)
poly = [hull_pt(HX + x, z + 0.012, 0.006) for x, z in crack]
bm2 = strap(poly, hull_n(0), 0.012, 0.006); me = bpy.data.meshes.new("_tmp"); bm2.to_mesh(me); bm2.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
add(COL_SUB, "SUB_HullCrackLip", bm, M_rust, SUB)
for i, (dx, da) in enumerate([(-0.17, -0.12), (0.17, -0.12), (-0.17, 0.12), (0.17, 0.12)]):     # patch bolt bosses
    p = hull_pt(HX + dx, da); n = hull_n(da)
    add(COL_SUB, f"SUB_PatchBoss_{i}", cyl(0.018, 0.012, 12, (0, 0, 0.006), T(*p) @ along(n)), M_metal, SUB)
lamp(COL_SUB, "SUB_Warn_Hull", hull_pt(HX, 0.30), hull_n(0.30), SUB)
rot = (Matrix.Rotation(-PHI, 4, "X") @ Matrix.Rotation(math.radians(-90), 4, "Z")).to_euler()
socket(COL_SUB, SUB, "Repair_Hull", hull_pt(HX, 0), tuple(math.degrees(a) for a in rot))

# =====================================================================================  INTERIOR
# ---- 3) CO2 scrubber unit on the port wall between the bay cabinet and the pilot seats
SX, SY = 0.67, -0.90
parts = [
    ("IN_Scrub_Back",    box((0.38, 0.02, 0.70), (SX, -0.99, 0.05)), M_panel),
    ("IN_Scrub_SideL",   box((0.03, 0.20, 0.70), (SX - 0.175, SY, 0.05)), M_panel),
    ("IN_Scrub_SideR",   box((0.03, 0.20, 0.70), (SX + 0.175, SY, 0.05)), M_panel),
    ("IN_Scrub_Top",     box((0.38, 0.20, 0.20), (SX, SY, 0.30)), M_panel),
    ("IN_Scrub_Base",    box((0.38, 0.20, 0.12), (SX, SY, -0.24)), M_panel),
    ("IN_Scrub_Cavity",  box((0.32, 0.005, 0.38), (SX, -0.977, 0.01)), M_dark),
    ("IN_Scrub_Stripe",  box((0.38, 0.004, 0.035), (SX, -0.798, -0.21)), M_yellow),
    ("IN_Scrub_Display", box((0.12, 0.006, 0.06), (SX - 0.07, -0.797, 0.34)), M_screen),
    ("IN_Scrub_RingBot", torus(0.085, 0.01, 24, 8, T(SX, SY, -0.18)), M_chrome),
    ("IN_Scrub_RingTop", torus(0.085, 0.01, 24, 8, T(SX, SY, 0.20)), M_chrome),
    ("IN_Scrub_Fan",     torus(0.06, 0.008, 24, 6, T(SX + 0.06, -0.80, 0.27) @ RX(90)), M_metal),
]
for k in range(4):
    a = k * 45
    parts.append((f"IN_Scrub_FanBar_{k}", box((0.11, 0.004, 0.008), (0, 0, 0), T(SX + 0.06, -0.797, 0.27) @ RY(a)), M_metal))
for nm, bm, m in parts:
    add(COL_INT, nm, bm, m, INT)
hose = catmull([(SX - 0.1, -0.88, 0.40), (SX - 0.12, -0.86, 0.55), (SX - 0.05, -0.80, 0.75), (SX + 0.05, -0.62, 0.90)], 6)
add(COL_INT, "IN_Scrub_Hose", tube(hose, 0.025, sides=10), M_metal, INT, smooth=True)
lamp(COL_INT, "IN_Warn_Scrubber", (SX + 0.09, -0.80, 0.37), (0, 1, 0), INT)
socket(COL_INT, INT, "Repair_Scrubber", (SX, SY, -0.18))

# ---- 4) circuit card cage in the console front (console face x = 1.79, faces -X toward the seats)
CX, CZ = 1.79, -0.40
parts = [
    ("IN_Cage_Opening", box((0.004, 0.40, 0.22), (CX - 0.002, 0, CZ + 0.07)), M_dark),
    ("IN_Cage_FrameT",  box((0.02, 0.44, 0.02), (CX - 0.01, 0, CZ + 0.19)), M_metal),
    ("IN_Cage_FrameB",  box((0.02, 0.44, 0.02), (CX - 0.01, 0, CZ - 0.05)), M_metal),
    ("IN_Cage_FrameL",  box((0.02, 0.02, 0.24), (CX - 0.01, -0.21, CZ + 0.07)), M_metal),
    ("IN_Cage_FrameR",  box((0.02, 0.02, 0.24), (CX - 0.01, 0.21, CZ + 0.07)), M_metal),
    ("IN_Cage_Rail",    box((0.03, 0.40, 0.015), (CX - 0.012, 0, CZ - 0.0075)), M_chrome),
    # access cover swung open on a vertical hinge at +Y
    ("IN_Cage_Cover",   box((0.012, 0.44, 0.26), (0, -0.22, 0), T(CX - 0.02, 0.23, CZ + 0.07) @ RZ(-115)), M_panel),
]
for y in (-0.16, -0.08, 0.08, 0.16):                 # installed boards: front edges + ejector handles; slot y=0 is empty
    parts.append((f"IN_Card_{y:+.2f}", box((0.03, 0.003, 0.12), (CX - 0.012, y, CZ + 0.06)), P_pcb))
    parts.append((f"IN_CardHandle_{y:+.2f}", box((0.014, 0.012, 0.03), (CX - 0.03, y, CZ + 0.105)), P_red))
parts.append(("IN_CardGuide_L", box((0.03, 0.006, 0.13), (CX - 0.012, -0.012, CZ + 0.06)), M_chrome))
parts.append(("IN_CardGuide_R", box((0.03, 0.006, 0.13), (CX - 0.012, 0.012, CZ + 0.06)), M_chrome))
for nm, bm, m in parts:
    add(COL_INT, nm, bm, m, INT)
wires = [[(CX - 0.01, -0.12, CZ + 0.17), (CX - 0.06, -0.10, CZ + 0.12), (CX - 0.08, -0.05, CZ - 0.02), (CX - 0.05, 0.02, CZ - 0.10)],
         [(CX - 0.01, 0.13, CZ + 0.17), (CX - 0.05, 0.15, CZ + 0.10), (CX - 0.07, 0.09, CZ - 0.03)]]
for i, w in enumerate(wires):
    add(COL_INT, f"IN_Cage_Wire_{i}", tube(catmull(w, 6), 0.006, sides=6), bpy.data.materials["M_Sub_Cable"], INT, smooth=True)
lamp(COL_INT, "IN_Warn_Circuit", (CX - 0.002, 0.0, CZ + 0.24), (-1, 0, 0), INT)
socket(COL_INT, INT, "Repair_Circuit", (CX, 0.0, CZ), (0, 0, 180))

# =====================================================================================  PICKUPS
ROW_Y = -1.35
def item(name, specs, x):
    col = get_col(name)
    objs = []
    for nm, bm, m, sm in specs:
        o = finish(col, nm, bm, m, smooth=sm); objs.append(o)
    old = bpy.data.objects.get(name)
    if old and old.type == "EMPTY":
        bpy.data.objects.remove(old, do_unlink=True)
    return make_root(col, name, objs, (x, ROW_Y, 0))

# ---- PropBlade: same shape as the submarine blades + root flange; pivot = flange bottom centre, blade along +Z
bm = bmesh.new(); bm.from_mesh(blade_src)
xf(bm, T(-HUBX, 0, -0.06 + 0.03))
spec = [("PB_Blade", bm, M_chrome, True),
        ("PB_Flange", cyl(0.045, 0.03, 24, (0, 0, 0.015)), P_steel, False),
        ("PB_Neck", cyl(0.022, 0.02, 16, (0, 0, 0.035)), P_steel, False)]
for k in range(3):
    a = k / 3 * math.tau
    spec.append((f"PB_Bolt_{k}", cyl(0.007, 0.01, 6, (0.034 * math.cos(a), 0.034 * math.sin(a), 0.035)), P_dark, False))
root_pb = item("PropBlade", spec, -0.6)

# ---- HullPatch: curved steel plate (hull radius), contact face at origin, outward +X, hull axis = item Y
def curved_plate(w, h, thick, r=R, nx=8, nz=8, inset=0.0):
    bm = bmesh.new(); grid = []
    for side in (0, 1):
        row = []
        for i in range(nz + 1):
            arc = (-h / 2 + h * i / nz); a = arc / r
            line = []
            for j in range(nx + 1):
                y = -w / 2 + w * j / nx
                rr = r + side * thick
                line.append(bm.verts.new((rr * math.cos(a) - r + inset, y, rr * math.sin(a))))
            row.append(line)
        grid.append(row)
    for s, flip in ((0, True), (1, False)):
        g = grid[s]
        for i in range(nz):
            for j in range(nx):
                f = (g[i][j], g[i][j + 1], g[i + 1][j + 1], g[i + 1][j])
                bm.faces.new(tuple(reversed(f)) if flip else f)
    a0, a1 = grid
    edges = [[(i, 0) for i in range(nz + 1)], [(nz, j) for j in range(nx + 1)], [(i, nx) for i in range(nz, -1, -1)], [(0, j) for j in range(nx, -1, -1)]]
    ring = [p for e in edges for p in e]
    for k in range(len(ring) - 1):
        (i0, j0), (i1, j1) = ring[k], ring[k + 1]
        if (i0, j0) != (i1, j1):
            try:
                bm.faces.new((a0[i0][j0], a0[i1][j1], a1[i1][j1], a1[i0][j0]))
            except ValueError:
                pass
    return bm
spec = [("HP_Plate", curved_plate(0.44, 0.34, 0.012), P_steel, True),
        ("HP_Gasket", curved_plate(0.46, 0.36, 0.006, inset=-0.004), P_rubber, True),
        ("HP_Stripe", curved_plate(0.44, 0.04, 0.004, inset=0.011), P_yellow, True)]
for i, (dy, dz) in enumerate([(-0.17, -0.12), (0.17, -0.12), (-0.17, 0.12), (0.17, 0.12)]):
    spec.append((f"HP_Bolt_{i}", cyl(0.016, 0.014, 6, (0, 0, 0.007), T(0.012, dy, dz) @ RY(90)), P_dark, False))
for i, dz in enumerate((-0.09, 0.09)):                # two grab handles on the outer face
    hp = [Vector((0.012, -0.08, dz)), Vector((0.05, -0.06, dz)), Vector((0.055, 0.0, dz)), Vector((0.05, 0.06, dz)), Vector((0.012, 0.08, dz))]
    spec.append((f"HP_Handle_{i}", tube(catmull(hp, 4), 0.009, up=(0, 0, 1), sides=8), P_dark, True))
root_hp = item("HullPatch", spec, -0.15); root_hp.location.z = 0.18

# ---- ScrubberCartridge: canister, pivot = bottom centre
prof = [(0.0, 0.0), (0.062, 0.0), (0.068, 0.006), (0.068, 0.30), (0.062, 0.306), (0.0, 0.306)]
spec = [("SC_Body", lathe(prof, 32), P_canister, True),
        ("SC_Window", cyl(0.0685, 0.12, 32, (0, 0, 0.15)), P_absorb, True),
        ("SC_Label", cyl(0.069, 0.05, 32, (0, 0, 0.255)), P_yellow, True),
        ("SC_CapTop", cyl(0.05, 0.02, 24, (0, 0, 0.316)), P_steel, False),
        ("SC_Port", cyl(0.02, 0.02, 16, (0, 0, 0.336)), P_dark, False)]
for k, z in enumerate((0.03, 0.08, 0.22)):
    spec.append((f"SC_Rib_{k}", torus(0.069, 0.004, 32, 6, T(0, 0, z)), P_steel, True))
for k in range(6):                                    # window bars (perforated look)
    a = k / 6 * math.tau
    spec.append((f"SC_Bar_{k}", box((0.012, 0.012, 0.12), (0.069 * math.cos(a), 0.069 * math.sin(a), 0.15)), P_steel, False))
spec.append(("SC_Handle", tube(catmull([Vector((-0.04, 0, 0.326)), Vector((-0.03, 0, 0.37)), Vector((0.0, 0, 0.385)),
                                         Vector((0.03, 0, 0.37)), Vector((0.04, 0, 0.326))], 5), 0.006, up=(0, 1, 0), sides=8), P_dark, True))
root_sc = item("ScrubberCartridge", spec, 0.3)

# ---- CircuitBoard: card slides in along -X (handle at +X), pivot = front-edge bottom centre
spec = [("CB_Board", box((0.16, 0.003, 0.12), (-0.08, 0, 0.06)), P_pcb, False),
        ("CB_Edge", box((0.012, 0.0034, 0.10), (-0.154, 0, 0.06)), P_gold, False),
        ("CB_Stiffener", box((0.15, 0.006, 0.008), (-0.08, 0, 0.116)), P_steel, False),
        ("CB_Handle", box((0.014, 0.014, 0.12), (0.006, 0, 0.06)), P_red, False),
        ("CB_Glow", box((0.006, 0.004, 0.006), (-0.02, 0.004, 0.015)), bpy.data.materials["M_Part_GlowBlue"], False)]
for k, (x, z, sx, sz) in enumerate([(-0.05, 0.07, 0.035, 0.035), (-0.11, 0.07, 0.03, 0.025), (-0.08, 0.03, 0.05, 0.02), (-0.03, 0.03, 0.02, 0.02)]):
    spec.append((f"CB_Chip_{k}", box((sx, 0.004, sz), (x, 0.0035, z)), P_dark, False))
for k, (x, z) in enumerate([(-0.13, 0.03), (-0.125, 0.10), (-0.02, 0.09)]):
    spec.append((f"CB_Cap_{k}", cyl(0.005, 0.012, 10, (0, 0, 0), T(x, 0.0075, z) @ RX(-90)), P_steel, False))
root_cb = item("CircuitBoard", spec, 0.75)

bpy.context.view_layer.update()
print("REPAIR2_BUILT", [r.name for r in (root_pb, root_hp, root_sc, root_cb)])
