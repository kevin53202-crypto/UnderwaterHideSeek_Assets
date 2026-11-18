# Submarine interior detail pass (2026-11-16). exec after mk.py in DiveGear_Scene.blend.
# Adds IN_D_* objects under SubInterior (rebuildable: all IN_D_* are deleted first).
# Interior frame: hull centre = origin, +X forward, inner hull radius ~1.05, floor top z=-0.70, aft bulkhead x=-1.6.
import bpy, bmesh, math
from mathutils import Vector

INT = bpy.data.objects["SubInterior"]; COL = INT.users_collection[0]
for o in [o for o in bpy.data.objects if o.name.startswith("IN_D_")]:
    bpy.data.objects.remove(o, do_unlink=True)

M = bpy.data.materials
metal, chrome, panel = M["M_Sub_Metal"], M["M_Sub_Chrome"], M["M_SubIn_Panel"]
red, yellow, white, cable = M["M_SubIn_Red"], M["M_SubIn_Yellow"], M["M_SubIn_White"], M["M_Sub_Cable"]
warn, screen, crate, floor_m = M["M_Sub_Warning"], M["M_SubIn_Screen"], M["M_SubIn_Crate"], M["M_SubIn_Floor"]
black = mat("M_SubIn_Black", (0.025, 0.025, 0.028), rough=0.7)
dark = M["M_Sub_Interior"]
_n = [0]


def put(name, bm, material, smooth=False):
    _n[0] += 1
    o = finish(COL, "IN_D_" + name, bm, material, smooth=smooth)
    o.parent = INT
    return o


def merge_bms(bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("_t"); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out


def wall(x, ang, r):                          # ang in degrees from +Z toward +Y (starboard +)
    a = math.radians(ang); return Vector((x, r * math.sin(a), r * math.cos(a)))


def along(n):
    return Vector(n).to_track_quat("Z", "Y").to_matrix().to_4x4()


# ---------------------------------------------------------------- 1) hull ribs (frames)
for x, r in ((-0.9, 1.025), (0.47, 1.025), (0.95, 1.025), (1.6, 1.0)):
    a0 = math.degrees(math.acos(-0.68 / r))
    poly = [wall(x, -a0 + 2 * a0 * k / 48, r) for k in range(49)]
    put(f"Rib_{x:+.2f}", strap(poly, (1, 0, 0), 0.045, 0.05), metal)
    for side in (-1, 1):                          # rib feet on the floor
        put(f"RibFoot_{x:+.2f}_{side}", box((0.09, 0.06, 0.03), (x, side * (math.sqrt(r * r - 0.68 ** 2) - 0.03), -0.685)), metal)

# ---------------------------------------------------------------- 2) cable trays + bundles along both upper walls
TA, TR = 48, 0.95
for side in (-1, 1):
    a = side * TA
    n_in = -wall(0, a, 1).normalized()
    p0, p1 = wall(-1.45, a, TR), wall(1.7, a, TR)
    put(f"Tray_{side}", strap([p0, p1], n_in, 0.16, 0.008), metal)
    tang = Vector((0, math.cos(math.radians(a)), -math.sin(math.radians(a))))
    for lip in (-1, 1):
        q0 = p0 + tang * lip * 0.08 + n_in * 0.02; q1 = p1 + tang * lip * 0.08 + n_in * 0.02
        put(f"TrayLip_{side}_{lip}", strap([q0, q1], tang, 0.04, 0.006), metal)
    for k, (off, rad, m) in enumerate(((-0.045, 0.018, cable), (0.0, 0.022, black), (0.045, 0.014, yellow))):
        pts = [wall(-1.45 + 3.15 * i / 12, a, TR - 0.03) + tang * off for i in range(13)]
        # sag a little between clamps
        pts = [p + n_in * (0.006 * math.sin(math.pi * ((i % 4) / 4))) for i, p in enumerate(pts)]
        put(f"Cable_{side}_{k}", tube(catmull(pts, 3), rad, sides=8), m, smooth=True)
    for i in range(8):                            # clamps across the bundle
        x = -1.3 + i * 0.42
        c = wall(x, a, TR - 0.03)
        put(f"TrayClamp_{side}_{i}", strap([c - tang * 0.085, c + tang * 0.085], n_in, 0.025, 0.006, ), chrome)
        put(f"TrayHanger_{side}_{i}", box((0.02, 0.02, 0.08), (0, 0, 0.04), Matrix.Translation(wall(x, a, TR + 0.005)) @ along(-n_in)), metal)

# ---------------------------------------------------------------- 3) clamps holding the existing ceiling pipes (y=±0.6, z=0.8)
for side in (-1, 1):
    for i in range(6):
        x = -1.3 + i * 0.6
        c = Vector((x, side * 0.6, 0.8))
        put(f"PipeClamp_{side}_{i}", torus(0.042, 0.008, 16, 6, Matrix.Translation(c) @ RY(90)), chrome, smooth=True)
        up = Vector((0, side * 0.6, 0.8)).normalized()
        put(f"PipeHanger_{side}_{i}", box((0.015, 0.015, 0.2), (0, 0, 0.1), Matrix.Translation(c + up * 0.04) @ along(up)), metal)

# ---------------------------------------------------------------- 4) starboard aft valve station (between locker and O2 panel)
VA = 72; VX0, VX1 = -0.95, -0.42
n_in = -wall(0, VA, 1).normalized()
pc = wall((VX0 + VX1) / 2, VA, 1.0)
put("Valve_Panel", box((VX1 - VX0, 0.02, 0.36), (0, 0, 0), Matrix.Translation(pc) @ along(n_in) @ RX(90)), panel)
for k, x in enumerate((-0.86, -0.52)):          # two pipes rising from floor to the tray
    pts = [Vector((x, 0.70, -0.70)), Vector((x, 0.80, -0.3)), wall(x, VA, 0.94), wall(x, 52, 0.94)]
    put(f"Valve_Pipe_{k}", tube(catmull(pts, 6), 0.025, sides=12), chrome if k else metal, smooth=True)
    for f, z in enumerate((-0.55, 0.0)):
        put(f"Valve_Flange_{k}_{f}", cyl(0.04, 0.025, 16, (0, 0, 0), Matrix.Translation(Vector((x, 0.78 if z < -0.3 else 0.88, z)))), metal)
hw = wall(-0.86, VA, 0.86)                       # handwheel valve on the first pipe
put("Valve_Body", cyl(0.04, 0.08, 16, (0, 0, 0.02), Matrix.Translation(wall(-0.86, VA, 0.94)) @ along(n_in)), metal)
put("Valve_Wheel", torus(0.07, 0.009, 24, 8, Matrix.Translation(hw) @ along(n_in)), red, smooth=True)
for s in range(3):
    put(f"Valve_Spoke_{s}", box((0.14, 0.012, 0.012), (0, 0, 0), Matrix.Translation(hw) @ along(n_in) @ RZ(s * 60)), red)
for g, (x, dz) in enumerate(((-0.72, 0.08), (-0.62, 0.08), (-0.67, -0.08))):   # gauge cluster
    gp = wall(x, VA - math.degrees(dz), 0.985)
    put(f"Gauge_Rim_{g}", cyl(0.042, 0.03, 20, (0, 0, 0.015), Matrix.Translation(gp) @ along(n_in)), chrome)
    put(f"Gauge_Face_{g}", cyl(0.036, 0.004, 20, (0, 0, 0.031), Matrix.Translation(gp) @ along(n_in)), white)
    put(f"Gauge_Needle_{g}", box((0.004, 0.03, 0.002), (0, 0.012, 0.034), Matrix.Translation(gp) @ along(n_in) @ RZ(35 - 50 * g)), red)
jb = wall(-0.5, VA + 12, 0.97)                   # junction box with conduit to the tray
put("JBox", box((0.16, 0.2, 0.08), (0, 0, 0.04), Matrix.Translation(jb) @ along(n_in)), panel)
put("JBox_Lid", box((0.14, 0.18, 0.01), (0, 0, 0.085), Matrix.Translation(jb) @ along(n_in)), yellow)
put("JBox_Conduit", tube(catmull([jb + n_in * 0.04 + Vector((0, 0, 0.1)), wall(-0.5, 60, 0.93), wall(-0.45, TA, TR - 0.03)], 5), 0.012, sides=8), black, smooth=True)

# ---------------------------------------------------------------- 5) fire extinguisher (starboard, between light switch and seats)
EX, EY, EZ = 0.75, 0.90, -0.56
put("Ext_Body", lathe([(0, 0), (0.055, 0), (0.06, 0.01), (0.06, 0.33), (0.05, 0.37), (0.02, 0.385), (0, 0.385)], 24, Matrix.Translation((EX, EY, EZ))), red, smooth=True)
put("Ext_Label", cyl(0.0605, 0.08, 24, (0, 0, 0.17), Matrix.Translation((EX, EY, EZ))), white, smooth=True)
put("Ext_Valve", cyl(0.018, 0.05, 12, (0, 0, 0.41), Matrix.Translation((EX, EY, EZ))), chrome)
put("Ext_Lever", box((0.1, 0.018, 0.008), (-0.03, 0, 0.44), Matrix.Translation((EX, EY, EZ))), black)
put("Ext_Hose", tube(catmull([Vector((EX + 0.015, EY - 0.01, EZ + 0.42)), Vector((EX + 0.07, EY - 0.05, EZ + 0.36)),
                               Vector((EX + 0.075, EY - 0.06, EZ + 0.2)), Vector((EX + 0.06, EY - 0.065, EZ + 0.12))], 5), 0.009, sides=8), black, smooth=True)
put("Ext_Nozzle", cyl(0.014, 0.05, 10, (0, 0, 0), Matrix.Translation((EX + 0.06, EY - 0.065, EZ + 0.1))), black)
for z in (0.08, 0.28):
    put(f"Ext_Band_{z}", torus(0.063, 0.006, 24, 6, Matrix.Translation((EX, EY, EZ + z))), metal, smooth=True)
put("Ext_Bracket", box((0.12, 0.02, 0.32), (EX, 0.97, EZ + 0.18)), metal)
put("Ext_Shelf", box((0.14, 0.12, 0.012), (EX, 0.92, EZ - 0.006)), metal)

# ---------------------------------------------------------------- 6) things on top of the bay cabinet (port, top z=0.40)
TZ = 0.40
put("Toolbox", box((0.32, 0.17, 0.11), (-0.45, -0.85, TZ + 0.055)), red)
put("Toolbox_Lid", box((0.33, 0.18, 0.02), (-0.45, -0.85, TZ + 0.12)), red)
put("Toolbox_Handle", tube(catmull([Vector((-0.55, -0.85, TZ + 0.13)), Vector((-0.53, -0.85, TZ + 0.17)), Vector((-0.37, -0.85, TZ + 0.17)), Vector((-0.35, -0.85, TZ + 0.13))], 4), 0.008, up=(0, 1, 0), sides=6), black, smooth=True)
put("Toolbox_Latch", box((0.03, 0.005, 0.03), (-0.45, -0.763, TZ + 0.1)), chrome)
put("Logbook", box((0.22, 0.16, 0.035), (0, 0, 0), Matrix.Translation((-0.1, -0.84, TZ + 0.018)) @ RZ(8)), M["M_SubIn_Seat"])
put("Logbook_Pages", box((0.21, 0.15, 0.03), (0.004, 0, 0), Matrix.Translation((-0.1, -0.84, TZ + 0.018)) @ RZ(8)), white)
put("Torch", cyl(0.02, 0.17, 12, (0, 0, 0), Matrix.Translation((0.12, -0.80, TZ + 0.022)) @ RZ(25) @ RY(90)), black, smooth=True)
put("Torch_Head", cyl(0.028, 0.04, 12, (0, 0, 0.1), Matrix.Translation((0.12, -0.80, TZ + 0.022)) @ RZ(25) @ RY(90)), yellow, smooth=True)
put("Mug", lathe([(0, 0), (0.035, 0), (0.038, 0.09), (0.033, 0.09), (0.03, 0.006), (0, 0.006)], 16, Matrix.Translation((0.22, -0.88, TZ))), white, smooth=True)
put("Mug_Handle", torus(0.022, 0.006, 12, 6, Matrix.Translation((0.258, -0.88, TZ + 0.045)) @ RX(90)), white, smooth=True)
put("Bungee", strap([Vector((-0.65, -0.70, TZ)), Vector((-0.65, -0.70, TZ + 0.13)), Vector((-0.2, -0.70, TZ + 0.06)), Vector((0.32, -0.70, TZ + 0.04)), Vector((0.33, -0.70, TZ))],
                    (0, 1, 0), 0.012, 0.006), black)

# ---------------------------------------------------------------- 7) floor: anti-slip edge strips + bilge access hatch
for side in (-1, 1):
    put(f"FloorEdge_{side}", box((3.3, 0.05, 0.006), (0.15, side * 0.70, -0.697)), yellow)
HX_, HY_ = -0.55, 0.28
put("Bilge_Hatch", box((0.5, 0.4, 0.012), (HX_, HY_, -0.694)), metal)
put("Bilge_Ring", torus(0.035, 0.006, 16, 6, Matrix.Translation((HX_ + 0.15, HY_, -0.686))), chrome, smooth=True)
for i, (dx, dy) in enumerate([(-0.22, -0.17), (0.22, -0.17), (-0.22, 0.17), (0.22, 0.17)]):
    put(f"Bilge_Bolt_{i}", cyl(0.01, 0.008, 6, (HX_ + dx, HY_ + dy, -0.684)), chrome)
for k in range(5):                                # tread ribs on the hatch
    put(f"Bilge_Tread_{k}", box((0.012, 0.3, 0.004), (HX_ - 0.16 + k * 0.06, HY_, -0.686)), metal)

# ---------------------------------------------------------------- 8) aft bulkhead: high-voltage sign, vent grille
SX_ = -1.585
put("HV_Plate", box((0.006, 0.36, 0.08), (SX_, -0.28, 0.46)), yellow)
for k in range(6):
    put(f"HV_Stripe_{k}", box((0.004, 0.025, 0.11), (0, 0, 0), Matrix.Translation((SX_ + 0.004, -0.43 + k * 0.06, 0.46)) @ RX(35)), black)
put("HV_Mask", box((0.008, 0.40, 0.03), (SX_ + 0.002, -0.28, 0.515)), panel)       # trims stripe ends top
put("HV_Mask2", box((0.008, 0.40, 0.03), (SX_ + 0.002, -0.28, 0.405)), panel)
put("Vent_Frame", box((0.02, 0.22, 0.16), (SX_ + 0.005, -0.66, 0.05)), metal)
for k in range(6):
    put(f"Vent_Slat_{k}", box((0.012, 0.19, 0.012), (0, 0, 0), Matrix.Translation((SX_ + 0.017, -0.66, -0.01 + k * 0.025)) @ RY(-30)), dark)

# ---------------------------------------------------------------- 9) cargo straps over the aft crates
for i, x in enumerate((-1.4, -1.22, -0.85)):
    top = -0.31 if x < -1.05 else -0.39
    y0, y1 = (-0.59, -0.17) if x < -1.05 else (-0.59, -0.25)
    pts = [Vector((x, y0, -0.70)), Vector((x, y0, top + 0.01)), Vector((x, (y0 + y1) / 2, top + 0.012)), Vector((x, y1, top + 0.01)), Vector((x, y1, -0.70))]
    put(f"CargoStrap_{i}", strap(pts, (1, 0, 0), 0.035, 0.005), yellow)
    put(f"CargoBuckle_{i}", box((0.05, 0.012, 0.035), (x, y0 - 0.005, top - 0.12)), chrome)

# ---------------------------------------------------------------- 10) ladder & hatch-trunk warning collar, headset on the console
put("Trunk_Collar", torus(0.33, 0.02, 32, 8, Matrix.Translation((0.15, 0, 1.0))), yellow, smooth=True)
hs = Vector((1.82, 0.42, 0.06))
put("Headset_Band", torus(0.075, 0.008, 20, 6, Matrix.Translation(hs + Vector((0, 0, 0.07))) @ RY(90)), black, smooth=True)
for s in (-1, 1):
    put(f"Headset_Cup_{s}", cyl(0.04, 0.03, 16, (0, 0, 0), Matrix.Translation(hs + Vector((0, s * 0.075, 0.03))) @ RX(90)), black, smooth=True)
put("Headset_Mic", tube(catmull([hs + Vector((0, -0.075, 0.03)), hs + Vector((-0.05, -0.05, 0.0)), hs + Vector((-0.08, -0.01, 0.01))], 4), 0.004, sides=6), black, smooth=True)

bpy.context.view_layer.update()
print("INTERIOR_DETAIL", _n[0], "objects")
