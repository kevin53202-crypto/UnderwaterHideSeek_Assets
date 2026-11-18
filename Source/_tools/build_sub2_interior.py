# Submarine Mk2 interior (2026-11-18): own cabin design for the white Mk2, 3 states + 2 moving parts.
# exec after mk.py in DiveGear_Scene.blend. Roots Sub2Int / Sub2Int_Wrecked / Sub2Int_Repaired sit on the Mk2 roots.
# Frame (root-local, same as Submarine2): hull centre = origin, +X forward, inner hull radius ~1.025,
# floor top z = -0.70, aft bulkhead x = -1.6, dome from x = 2.24, hatch trunk centre x = 0.15 (r 0.38), ground z = -1.55.
# Layout aft -> fore: power panel (aft bulkhead) | hide locker (port) + equipment rack (stbd) | battery-bay cabinet (port),
# ladder (centre), fold seat + medkit + wall lockers (stbd) | O2 station (port), CO2 scrubber (stbd) | 2 bucket seats,
# wrap console with 3 screens and the circuit-board slot.
# Sockets keep the original interior names; in the scene they carry a suffix (__I2G...), stripped on export.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

MT = bpy.data.materials
FLOOR = -0.70
IR = 1.025
HOST = {"G": "Submarine2", "W": "Submarine2_Wrecked", "R": "Submarine2_Repaired"}
NAME = {"G": "Sub2Int", "W": "Sub2Int_Wrecked", "R": "Sub2Int_Repaired"}
SFX = {"G": "__I2G", "W": "__I2W", "R": "__I2R"}
SM = {"G": "SM_Sub2_Interior", "W": "SM_Sub2_Interior_Wrecked", "R": "SM_Sub2_Interior_Repaired"}

C = {}
def mats():
    C["white"] = mat("M_Sub2In_PanelWhite", (0.86, 0.87, 0.86), rough=0.45)
    C["orange"] = MT["M_Sub2_PaintOrange"]
    C["grey"] = mat("M_Sub2In_PanelGrey", (0.32, 0.34, 0.36), metal=0.2, rough=0.5)
    C["floor"] = mat("M_Sub2In_Floor", (0.13, 0.14, 0.15), metal=0.3, rough=0.75)
    C["metal"] = MT["M_Sub2_Metal"]; C["dark"] = MT["M_Sub2_DarkMetal"]; C["chrome"] = MT["M_Sub_Chrome"]
    C["cushion"] = mat("M_Sub2In_Cushion", (0.85, 0.3, 0.05), rough=0.85)
    C["fabric"] = mat("M_Sub2In_FabricDark", (0.07, 0.075, 0.08), rough=0.9)
    C["screen"] = mat("M_Sub2In_Screen", (0.05, 0.35, 0.45), emit=(0.2, 0.75, 0.95), strength=3.0)
    C["led"] = mat("M_Sub2In_LED", (1.0, 0.98, 0.95), emit=(1.0, 0.97, 0.92), strength=10.0)
    C["guide"] = mat("M_Sub2In_FloorGuide", (0.3, 0.8, 0.9), emit=(0.3, 0.85, 1.0), strength=4.0)
    C["green"] = mat("M_Sub2In_StatusGreen", (0.1, 0.8, 0.3), emit=(0.15, 1.0, 0.4), strength=4.0)
    C["cross"] = mat("M_Sub2In_MedGreen", (0.05, 0.55, 0.25), rough=0.5)
    C["red"] = MT["M_SubIn_Red"]; C["black"] = MT.get("M_SubIn_Black") or mat("M_SubIn_Black", (0.025, 0.025, 0.028), rough=0.7)
    C["warn"] = MT["M_Sub_Warning"]; C["ok"] = MT["M_Sub_OK"]; C["cable"] = MT["M_Sub_Cable"]
    C["hazard"] = MT["M_Sub2_Hazard"]; C["hole"] = MT["M_Sub_Interior"]
    C["tankwhite"] = mat("M_Sub2In_TankWhite", (0.9, 0.9, 0.88), metal=0.3, rough=0.3)
    # wrecked
    C["dirty"] = mat("M_Sub2In_PanelDirty", (0.52, 0.5, 0.44), rough=0.8)
    C["floordirty"] = mat("M_Sub2In_FloorDirty", (0.11, 0.105, 0.09), rough=0.9)
    C["off"] = MT["M_SubIn_LightOff"]; C["broken"] = MT["M_SubIn_ScreenBroken"]
    C["water"] = MT["M_SubIn_Water"]; C["silt"] = MT["M_SubIn_Silt"]; C["mold"] = MT["M_SubIn_Mold"]
    C["glass"] = MT["M_DomeGlass_Acrylic"]; C["foam"] = MT["M_SubIn_Foam"]


# ---------------------------------------------------------------- geometry helpers
def merged(bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("_t"); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out


def wallp(x, ang, r=IR):                       # ang: degrees from +Z toward +Y (starboard positive)
    a = math.radians(ang); return Vector((x, r * math.sin(a), r * math.cos(a)))


def shell_patch(x0, x1, a0, a1, r_out, thick, nx=2, na=10):
    """Curved panel on the cabin cylinder (axis X), outer radius r_out, between angles a0..a1 (deg)."""
    bm = bmesh.new(); grid = []
    for side, r in enumerate((r_out, r_out - thick)):
        g = [[bm.verts.new(wallp(x0 + (x1 - x0) * i / nx, a0 + (a1 - a0) * j / na, r)) for j in range(na + 1)] for i in range(nx + 1)]
        grid.append(g)
    o, n = grid
    for i in range(nx):
        for j in range(na):
            bm.faces.new((o[i][j], o[i + 1][j], o[i + 1][j + 1], o[i][j + 1]))
            bm.faces.new((n[i][j + 1], n[i + 1][j + 1], n[i + 1][j], n[i][j]))
    for i in range(nx):
        bm.faces.new((o[i][0], n[i][0], n[i + 1][0], o[i + 1][0])); bm.faces.new((o[i + 1][na], n[i + 1][na], n[i][na], o[i][na]))
    for j in range(na):
        bm.faces.new((o[0][j + 1], n[0][j + 1], n[0][j], o[0][j])); bm.faces.new((o[nx][j], n[nx][j], n[nx][j + 1], o[nx][j + 1]))
    return bm


def rib(x, a0, a1, w=0.05, depth=0.06):
    return shell_patch(x - w / 2, x + w / 2, a0, a1, IR, depth, nx=1, na=16)


def disc(r, z, center, seg=20, sx=1.0, sy=1.0, jitter=0.0, seed=0):
    rnd = random.Random(seed); bm = bmesh.new()
    vs = [bm.verts.new((center[0] + math.cos(a) * r * sx * (1 + rnd.uniform(-jitter, jitter)),
                        center[1] + math.sin(a) * r * sy * (1 + rnd.uniform(-jitter, jitter)), z))
          for a in (k / seg * math.tau for k in range(seg))]
    bm.faces.new(vs); return bm


def about(bm, pivot, R):
    return xf(bm, Matrix.Translation(pivot) @ R @ Matrix.Translation(-Vector(pivot)))


# ---------------------------------------------------------------- moving parts (pivot = hinge)
def mk_part(nm, specs, loc):
    col = get_col(nm); old = bpy.data.objects.get(nm)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    objs = [finish(col, f"{nm}_{i}", b, m, smooth=sm) for i, (b, m, sm) in enumerate(specs)]
    return make_root(col, nm, objs, loc)

LOCKER = dict(x0=-1.50, x1=-1.02, y0=-0.72, y1=-0.28, z1=0.70)
DOOR_W, DOOR_H = 0.48, 1.38

def build_parts():
    slats = merged([box((0.30, 0.03, 0.012), (0.24, -0.006, 1.16 + k * 0.035)) for k in range(4)])
    mk_part("Sub2LockerDoor", [
        (box((DOOR_W, 0.022, DOOR_H), (DOOR_W / 2, 0, DOOR_H / 2)), C["white"], False),
        (box((0.012, 0.026, DOOR_H), (DOOR_W - 0.006, 0, DOOR_H / 2)), C["orange"], False),   # orange edge stripe
        (slats, C["dark"], False),                                                             # vent slats to look out
        (box((0.025, 0.04, 0.16), (DOOR_W - 0.06, -0.025, 0.78)), C["metal"], False),         # handle (cabin side = -Y)
        (merged([cyl(0.012, 0.06, 10, (0.01, 0, z)) for z in (0.15, DOOR_H - 0.15)]), C["metal"], True)],  # hinge knuckles
        (-1.0, 24.0, 0.0))
    mk_part("Sub2PowerLever", [
        (box((0.05, 0.07, 0.06), (0, 0, 0)), C["dark"], False),
        (cyl(0.012, 0.30, 10, (0, 0, 0.15)), C["metal"], True),
        (cyl(0.026, 0.09, 14, (0, 0, 0.32)), C["orange"], True)],
        (0.5, 24.0, 0.0))


# ---------------------------------------------------------------- one interior state
def build(state):
    random.seed(7)
    W, R = state == "W", state == "R"
    sfx = SFX[state]
    for o in [o for o in bpy.data.objects if o.name.endswith(sfx)]:
        bpy.data.objects.remove(o, do_unlink=True)
    col = get_col(NAME[state])
    old = bpy.data.objects.get(NAME[state])
    if old: bpy.data.objects.remove(old, do_unlink=True)
    root = bpy.data.objects.new(NAME[state], None); col.objects.link(root)
    root.location = bpy.data.objects[HOST[state]].location.copy()

    white = C["dirty"] if W else C["white"]
    led = C["off"] if W else C["led"]
    scr = C["broken"] if W else C["screen"]
    lamp = C["ok"] if R else (C["off"] if W else C["warn"])
    status = C["off"] if W else C["green"]

    def put(name, bm, material, smooth=False):
        o = finish(col, "S2I_" + name + sfx, bm, material, smooth=smooth); o.parent = root; return o

    def sock(name, loc, rot=(0, 0, 0)):
        e = bpy.data.objects.new("SKT_" + name + sfx, None); col.objects.link(e)
        e.empty_display_type = "ARROWS"; e.empty_display_size = 0.08; e.parent = root
        e.location = loc; e.rotation_euler = tuple(math.radians(a) for a in rot)

    # ---- floor: dark anti-slip plates, orange edges, seams, guide lights
    put("Floor", box((3.78, 1.50, 0.04), (0.31, 0, FLOOR - 0.02)), C["floordirty"] if W else C["floor"])
    put("FloorEdge", merged([box((3.70, 0.05, 0.006), (0.31, s * 0.71, FLOOR + 0.003)) for s in (-1, 1)]), C["orange"])
    put("FloorSeams", merged([box((0.012, 1.36, 0.004), (x, 0, FLOOR + 0.002)) for x in (-1.0, -0.4, 0.2, 0.8, 1.4, 2.0)]), C["dark"])
    put("FloorGuide", merged([box((2.5, 0.015, 0.006), (-0.2, s * 0.62, FLOOR + 0.004)) for s in (-1, 1)]), C["off"] if W else C["guide"])

    # ---- frames (ribs) and white wall liner with orange trim
    put("Ribs", merged([rib(x, a0 * s, a1 * s) if s > 0 else rib(x, -a1, -a0) for x in (-0.95, 0.42, 1.02) for s in (1, -1)
                        for (a0, a1) in ((30, 108),)]), C["dark"])
    bays = [(-1.55, -0.99), (-0.91, 0.38), (0.46, 0.98), (1.06, 2.05)]
    liner = [shell_patch(x0 + 0.01, x1 - 0.01, s * 36 if s > 0 else -66, 66 if s > 0 else -36, 1.0, 0.025, nx=2, na=8)
             for (x0, x1) in bays for s in (1, -1)]
    if W:   # port mid liner panel torn loose: hangs from its lower edge, leaning into the aisle
        liner.pop(3)
        hinge = wallp(0, -66, 1.0)
        put("LinerFallen", about(shell_patch(-0.90, 0.37, -66, -36, 1.0, 0.025, 2, 8), (0, hinge.y, hinge.z), RX(-35)), white, smooth=True)
    put("AftBulkhead", lathe([(0.0, -0.005), (1.02, -0.005), (1.02, 0.005), (0.0, 0.005)], 48, T(-1.588, 0, 0) @ RY(90)), white)
    put("DomeTrim", lathe([(0.96, 0.0), (1.02, 0.0), (1.02, 0.02), (0.96, 0.02)], 48, T(2.18, 0, 0) @ RY(90)), C["orange"], smooth=True)
    lower = [shell_patch(x0 + 0.01, x1 - 0.01, *((70, 110) if s > 0 else (-110, -70)), 1.0, 0.025, nx=2, na=10)
             for (x0, x1) in bays for s in (1, -1)]
    kick = [shell_patch(x0 + 0.01, x1 - 0.01, *((111, 131) if s > 0 else (-131, -111)), 1.0, 0.025, nx=2, na=5)
            for (x0, x1) in bays for s in (1, -1)]
    put("Liner", merged(liner + lower), white, smooth=True)
    put("LinerKick", merged(kick), C["grey"], smooth=True)
    put("LinerTrim", merged([shell_patch(-1.55, 2.05, s * 67 if s > 0 else -69, 69 if s > 0 else -67, 1.005, 0.008, nx=4, na=1)
                             for s in (1, -1)]), C["orange"], smooth=True)

    # ---- ceiling: white panels around the hatch trunk, 3 LED light panels, trunk collar, grab rails
    ceil = [shell_patch(-1.55, -0.30, -34, 34, 1.0, 0.025, 3, 12), shell_patch(0.60, 2.05, -34, 34, 1.0, 0.025, 3, 12)]
    lights = [(-0.95, 0.5), (0.85, 0.36), (1.55, 0.5)]
    if W:   # forward light panel torn down, hanging by its cables
        hang = shell_patch(1.30, 1.80, -8, 8, 0.97, 0.012, 2, 4)
        put("CeilingLightHanging", xf(hang, Matrix.Translation((1.30, 0, 0.97)) @ Matrix.Rotation(math.radians(52), 4, "Y")
                                      @ Matrix.Translation((-1.30, 0, -0.97))), led)
        put("HangingCables", merged([tube(catmull([Vector((1.3, y, 0.97)), Vector((1.36, y * 1.5, 0.75)), Vector((1.42, y, 0.62))], 6), 0.008, sides=6)
                                     for y in (-0.05, 0.04)]), C["cable"], smooth=True)
        lights = lights[:2]
    put("Ceiling", merged(ceil), white, smooth=True)
    put("CeilingLights", merged([shell_patch(x - w / 2, x + w / 2, -8, 8, 0.975, 0.012, 2, 4) for x, w in lights]), led, smooth=True)
    for i, (x, _) in enumerate([(-0.95, 0), (0.85, 0), (1.55, 0)]):
        sock(f"CabinLight_{i + 1}", (x, 0, 0.93), (0, 90, 0))
    put("TrunkCollar", lathe([(0.38, 0.88), (0.47, 0.88), (0.47, 0.95), (0.38, 0.95)], 32, Matrix.Translation((0.15, 0, 0))), C["orange"], smooth=True)
    put("GrabRails", merged([tube([Vector((x0, s * 0.42, 0.88)), Vector((x0, s * 0.42, 0.84)), Vector((x1, s * 0.42, 0.84)), Vector((x1, s * 0.42, 0.88))],
                                  0.014, sides=8) for s in (-1, 1) for (x0, x1) in ((-0.85, -0.35), (0.65, 1.0))]), C["orange"], smooth=True)

    # ---- ladder (same place as the original: rails at x -0.08, up through the trunk)
    put("LadderRails", merged([cyl(0.02, 2.70, 12, (-0.08, s * 0.17, FLOOR + 1.35)) for s in (-1, 1)]), C["metal"], smooth=True)
    put("LadderRungs", merged([box((0.03, 0.34, 0.025), (-0.08, 0, -0.42 + k * 0.28)) for k in range(9)]), C["black"])
    sock("Ladder_Bottom", (0.15, 0, FLOOR)); sock("Ladder_Top", (0.15, 0, 1.97))

    # ---- aft bulkhead: power panel + lever
    put("PowerPanel", box((0.05, 0.50, 0.64), (-1.565, 0.07, 0.10)), white)
    put("PowerHeader", box((0.006, 0.50, 0.05), (-1.538, 0.07, 0.395)), C["orange"])
    put("PowerSlot", box((0.004, 0.05, 0.30), (-1.538, 0.05, 0.12)), C["dark"])
    put("PowerLamps", merged([cyl(0.018, 0.012, 12, (0, 0, 0), T(-1.535, y, -0.13) @ RY(90)) for y in (0.17, 0.22, 0.27)]), lamp)
    put("PowerDisplay", box((0.006, 0.16, 0.09), (-1.538, 0.22, 0.15)), scr)
    sock("PowerLeverPivot", (-1.53, 0.05, 0.12)); sock("Interact_PowerLever", (-1.40, 0.05, 0.10))
    put("AftVent", merged([box((0.01, 0.30, 0.012), (-1.578, 0.07, -0.45 + k * 0.03)) for k in range(6)]), C["dark"])

    # ---- hide locker (aft port): open box facing +Y, door is SM_Sub2_LockerDoor
    L = LOCKER; t = 0.02; zc = (FLOOR + L["z1"]) / 2; h = L["z1"] - FLOOR
    shell = [box((L["x1"] - L["x0"], t, h), ((L["x0"] + L["x1"]) / 2, L["y0"] + t / 2, zc)),
             box((t, L["y1"] - L["y0"], h), (L["x0"] + t / 2, (L["y0"] + L["y1"]) / 2, zc)),
             box((t, L["y1"] - L["y0"], h), (L["x1"] - t / 2, (L["y0"] + L["y1"]) / 2, zc)),
             box((L["x1"] - L["x0"], L["y1"] - L["y0"], t), ((L["x0"] + L["x1"]) / 2, (L["y0"] + L["y1"]) / 2, L["z1"] - t / 2))]
    put("Locker", merged(shell), white)
    put("LockerInside", box((L["x1"] - L["x0"] - 2 * t, 0.004, h - t), ((L["x0"] + L["x1"]) / 2, L["y0"] + t + 0.002, zc)), C["grey"])
    put("LockerHook", cyl(0.008, 0.08, 8, (0, 0, 0), T((L["x0"] + L["x1"]) / 2, L["y0"] + 0.06, 0.55) @ RX(90)), C["metal"], smooth=True)
    sock("LockerDoorHinge", (L["x0"], L["y1"] + 0.012, FLOOR + 0.01))
    sock("Hide_Locker", ((L["x0"] + L["x1"]) / 2, (L["y0"] + L["y1"]) / 2, FLOOR))

    # ---- equipment rack (aft starboard)
    put("Rack", box((0.50, 0.30, 1.22), (-1.27, 0.57, FLOOR + 0.61)), C["grey"])
    put("RackFronts", merged([box((0.46, 0.006, 0.20), (-1.27, 0.418, FLOOR + 0.18 + k * 0.24)) for k in range(5)]), white)
    rnd = random.Random(3)
    put("RackLEDs", merged([cyl(0.006, 0.006, 6, (0, 0, 0), T(-1.45 + i * 0.04, 0.414, FLOOR + 0.24 + k * 0.24) @ RX(90))
                            for k in range(5) for i in range(8) if rnd.random() < 0.6]), status)
    put("RackScreen", box((0.26, 0.006, 0.14), (-1.22, 0.414, FLOOR + 1.12)), scr)

    # ---- battery-bay cabinet (port mid) + shelf with odds and ends
    put("BayCabinet", box((1.16, 0.18, 0.84), (-0.20, -0.73, 0.0)), white)
    put("BayStripe", box((1.16, 0.006, 0.05), (-0.20, -0.638, 0.33)), C["orange"])
    put("BayHazard", merged([box((0.03, 0.006, 0.14), (0, 0, 0), T(-0.62 + k * 0.06, -0.637, -0.25) @ RY(30)) for k in range(5)]), C["hazard"])
    put("BayLamp", cyl(0.02, 0.012, 12, (0, 0, 0), T(0.25, -0.636, 0.25) @ RX(90)), lamp)
    put("BayDrawers", box((1.10, 0.10, 0.24), (-0.20, -0.67, FLOOR + 0.13)), C["grey"])
    put("BayDrawerHandles", merged([box((0.18, 0.02, 0.02), (x, -0.61, FLOOR + 0.17)) for x in (-0.55, -0.20, 0.15)]), C["orange"])
    if W:   # shelf knocked down by the falling liner panel
        put("Shelf", box((1.10, 0.20, 0.02), (0, 0, 0), T(-0.35, -0.42, FLOOR + 0.03) @ RZ(12) @ RX(8)), C["grey"])
    else:
        put("Shelf", box((1.10, 0.20, 0.02), (-0.20, -0.74, 0.47)), C["grey"])
        put("Tablet", box((0.22, 0.15, 0.012), (0, 0, 0), T(-0.45, -0.73, 0.487) @ RZ(8)), C["black"])
        put("TabletScreen", box((0.19, 0.12, 0.002), (0, 0, 0), T(-0.45, -0.73, 0.494) @ RZ(8)), scr)
        put("Mug", lathe([(0.0, 0.0), (0.04, 0.0), (0.04, 0.09), (0.035, 0.09), (0.035, 0.01), (0.0, 0.01)], 16, Matrix.Translation((0.1, -0.74, 0.48))), C["orange"], smooth=True)

    # ---- starboard mid: wall lockers, fold seat, medkit
    put("WallLockers", box((1.12, 0.22, 0.42), (-0.24, 0.63, 0.28)), white)
    put("WallLockerSeams", merged([box((0.006, 0.006, 0.40), (x, 0.518, 0.28)) for x in (-0.43, -0.05)]), C["dark"])
    put("WallLockerHandles", merged([box((0.08, 0.02, 0.02), (x, 0.512, 0.12)) for x in (-0.62, -0.24, 0.14)]), C["orange"])
    seat_bm = merged([box((0.40, 0.28, 0.06), (-0.55, 0.57, -0.28)), box((0.40, 0.04, 0.30), (-0.55, 0.70, -0.08))])
    put("FoldSeat", seat_bm, C["cushion"])
    put("FoldSeatArms", merged([box((0.02, 0.26, 0.02), (x, 0.57, -0.32)) for x in (-0.74, -0.36)] +
                               [box((0.02, 0.02, 0.38), (x, 0.70, -0.51)) for x in (-0.74, -0.36)]), C["metal"])
    mk = box((0.28, 0.08, 0.22), (0.19, 0.69, -0.17))
    if W:   # medkit knocked off the wall, lying on the floor with bandages spilled
        put("Medkit", xf(mk, T(0.30, 0.30, FLOOR + 0.04) @ RZ(35) @ RX(90) @ T(-0.19, -0.69, 0.17)), white)
        put("Bandages", merged([cyl(0.025, 0.06, 10, (0, 0, 0), T(0.10 + i * 0.09, 0.15 + i * 0.05, FLOOR + 0.025) @ RZ(20 * i) @ RX(90)) for i in range(3)]), C["white"], smooth=True)
    else:
        put("Medkit", mk, C["white"])
        put("MedkitCross", merged([box((0.08, 0.004, 0.025), (0.19, 0.648, -0.17)), box((0.025, 0.004, 0.08), (0.19, 0.648, -0.17))]), C["cross"])
    sock("Interact_Medkit", (0.19, 0.55, -0.17))

    # ---- O2 station (forward port)
    put("O2Panel", box((0.52, 0.05, 0.70), (0.72, -0.79, 0.05)), white)
    put("O2Header", box((0.52, 0.006, 0.04), (0.72, -0.763, 0.37)), C["green"] if not W else C["off"])
    tanks = []
    for i, x in enumerate((0.60, 0.84)):
        tb = lathe([(0.0, 0.0), (0.085, 0.0), (0.09, 0.02), (0.09, 0.55), (0.06, 0.62), (0.025, 0.64), (0.0, 0.64)], 20,
                   Matrix.Translation((x, -0.64, FLOOR)))
        if W and i == 1:   # one tank broke loose and rolled into the aisle
            tb = about(tb, Vector((x, -0.64, FLOOR)), Matrix.Rotation(math.radians(86), 4, "Y"))
            tb = xf(tb, Matrix.Translation((-0.25, 0.42, 0.09)) @ RZ(0))
        tanks.append(tb)
    put("O2Tanks", merged(tanks), C["tankwhite"], smooth=True)
    put("O2Bands", merged([cyl(0.093, 0.06, 20, (x, -0.64, FLOOR + 0.42)) for x in ((0.60,) if W else (0.60, 0.84))]), C["cross"], smooth=True)
    put("O2Straps", merged([box((0.20, 0.012, 0.03), (x, -0.73, FLOOR + 0.30)) for x in (0.60, 0.84)]), C["dark"])
    put("O2Gauge", cyl(0.06, 0.02, 20, (0, 0, 0), T(0.72, -0.76, 0.18) @ RX(90)), C["white"], smooth=True)
    put("O2GaugeRim", lathe([(0.06, -0.012), (0.068, -0.012), (0.068, 0.012), (0.06, 0.012)], 20, Matrix.Translation((0.72, -0.76, 0.18)) @ RX(90)), C["chrome"], smooth=True)
    put("O2Hose", tube(catmull([Vector((0.95, -0.765, 0.05)), Vector((1.0, -0.70, -0.15)), Vector((0.97, -0.62, -0.25)), Vector((0.95, -0.60, -0.10))], 6),
                       0.014, sides=8), C["black"], smooth=True)
    sock("Interact_O2Refill", (0.72, -0.48, -0.10))

    # ---- CO2 scrubber (forward starboard): open cavity facing -Y, cartridge stands on SOCKET_Repair_Scrubber
    sx0, sx1, sy0, sy1 = 0.48, 0.96, 0.58, 0.82
    put("ScrubberBody", merged([box((sx1 - sx0, 0.02, 0.70), ((sx0 + sx1) / 2, sy1 - 0.01, 0.05)),
                                box((0.04, sy1 - sy0, 0.70), (sx0 + 0.02, (sy0 + sy1) / 2, 0.05)),
                                box((0.04, sy1 - sy0, 0.70), (sx1 - 0.02, (sy0 + sy1) / 2, 0.05)),
                                box((sx1 - sx0, sy1 - sy0, 0.18), ((sx0 + sx1) / 2, (sy0 + sy1) / 2, 0.31)),
                                box((sx1 - sx0, sy1 - sy0, 0.12), ((sx0 + sx1) / 2, (sy0 + sy1) / 2, -0.24))]), white)
    put("ScrubberCavity", box((sx1 - sx0 - 0.08, 0.004, 0.40), ((sx0 + sx1) / 2, sy1 - 0.022, 0.01)), C["hole"])
    put("ScrubberRings", merged([torus(0.085, 0.008, 24, 6, Matrix.Translation((0.72, 0.70, z))) for z in (-0.175, 0.205)]), C["chrome"], smooth=True)
    put("ScrubberGrill", merged([box((0.30, 0.004, 0.008), (0.72, sy0 - 0.002, 0.27 + k * 0.022)) for k in range(5)]), C["dark"])
    put("ScrubberStripe", box((sx1 - sx0, 0.004, 0.03), ((sx0 + sx1) / 2, sy0 - 0.002, -0.21)), C["orange"])
    put("ScrubberLamp", cyl(0.018, 0.01, 12, (0, 0, 0), T(0.90, sy0 - 0.004, 0.36) @ RX(90)), lamp)
    sock("Repair_Scrubber", (0.72, 0.70, -0.18))
    put("LightSwitch", merged([box((0.08, 0.02, 0.12), (1.12, 0.93, 0.15)), box((0.02, 0.02, 0.04), (1.12, 0.915, 0.15))]), C["white"])
    sock("Interact_LightSwitch", (1.12, 0.85, 0.15))
    ext = lathe([(0.0, 0.0), (0.055, 0.0), (0.055, 0.34), (0.03, 0.38), (0.0, 0.38)], 16, T(1.12, 0.60, FLOOR + 0.02))
    if W:   # fell off its bracket and lies in the aisle
        about(ext, Vector((1.12, 0.60, FLOOR + 0.055)), RX(-90))
    put("Extinguisher", ext, C["red"], smooth=True)

    # ---- cockpit seats (bucket seats facing +X)
    seats = []; cush = []; arms = []
    for s in (-1, 1):
        y = s * 0.36
        post = [cyl(0.05, 0.36, 14, (1.40, y, FLOOR + 0.18))]
        c_ = [box((0.44, 0.44, 0.08), (1.38, y, -0.30)),
              box((0.10, 0.46, 0.62), (0, 0, 0.31), T(1.15, y, -0.27) @ RY(-12)),
              box((0.08, 0.26, 0.14), (0, 0, 0), T(1.07, y, 0.41) @ RY(-12))]
        a_ = [box((0.30, 0.05, 0.04), (1.38, y + s * 0.24, -0.12)), box((0.04, 0.05, 0.16), (1.30, y + s * 0.24, -0.20)),
              cyl(0.012, 0.09, 8, (1.48, y + s * 0.24, -0.06)), cyl(0.022, 0.04, 12, (1.48, y + s * 0.24, 0.0))]   # side-stick
        if W and s > 0:   # starboard seat snapped off its post and tipped into the aisle (stump stays)
            post = [cyl(0.05, 0.12, 14, (1.40, y, FLOOR + 0.06))]
            tip = T(1.40, 0.10, FLOOR + 0.25) @ RX(-80) @ T(-1.40, -y, 0.30)
            for b in c_ + a_: xf(b, tip)
        seats += post + [box((0.30, 0.30, 0.03), (1.40, y, FLOOR + 0.02))]
        cush += c_; arms += a_
        sock("Seat_L" if s > 0 else "Seat_R", (1.38, y, -0.26))
    put("SeatPosts", merged(seats), C["dark"], smooth=True)
    put("SeatCushions", merged(cush), C["fabric"] if W else C["cushion"])
    put("SeatArms", merged(arms), C["dark"], smooth=True)

    # ---- console under the dome: knee-height upper desk + lower base with the circuit-board slot
    put("ConsoleBase", box((0.22, 1.24, 0.40), (2.06, 0, FLOOR + 0.20)), white)
    desk = box((0.38, 1.24, 0.08), (0, 0, 0)); xf(desk, Matrix.Translation((1.98, 0, -0.06)) @ RY(-10))
    put("ConsoleDesk", desk, C["grey"])
    put("ConsoleFront", box((0.03, 1.24, 0.30), (1.80, 0, -0.22)), white)
    put("ConsoleStripe", box((0.006, 1.24, 0.03), (1.783, 0, -0.10)), C["orange"])
    scr_frames, scr_faces = [], []
    for yc, yaw, w in ((0.0, 0, 0.56), (-0.47, 28, 0.30), (0.47, -28, 0.30)):
        Mf = Matrix.Translation((2.10, yc, 0.17)) @ RZ(yaw) @ RY(-15)
        scr_frames.append(box((0.04, w + 0.04, 0.30), (0, 0, 0), Mf))
        scr_faces.append(box((0.004, w, 0.26), (-0.022, 0, 0), Mf))
    put("ScreenFrames", merged(scr_frames), C["dark"])
    put("Screens", merged(scr_faces), scr)
    rnd = random.Random(5)
    put("Buttons", merged([box((0.025, 0.025, 0.01), (0, 0, 0), Matrix.Translation((1.90 + 0.05 * (k // 6), -0.20 + 0.08 * (k % 6), -0.01 + 0.009 * (k // 6))) @ RY(-10))
                           for k in range(12)]), status)
    put("Throttle", merged([box((0.10, 0.10, 0.04), (1.98, 0, 0.0)), cyl(0.012, 0.12, 8, (0, 0, 0), T(1.98, 0, 0.07) @ RY(-20)),
                            cyl(0.03, 0.05, 12, (0, 0, 0), T(1.96, 0, 0.13) @ RX(90))]), C["dark"], smooth=True)
    # circuit-board cage (front of the lower base)
    put("CageFrame", merged([box((0.02, 0.44, 0.02), (1.945, 0, z)) for z in (-0.47, -0.21)] +
                            [box((0.02, 0.02, 0.28), (1.945, y, -0.34)) for y in (-0.21, 0.21)]), C["metal"])
    put("CageOpening", box((0.004, 0.40, 0.24), (1.953, 0, -0.34)), C["hole"])
    put("CageGuides", merged([box((0.03, 0.006, 0.14), (1.97, y, -0.34)) for y in (-0.012, 0.012)]), C["chrome"])
    put("CageCards", merged([box((0.16, 0.004, 0.12), (2.03, y, -0.34)) for y in (-0.16, -0.08, 0.08, 0.16)]), MT["M_Part_PCB"])
    put("CageLamp", cyl(0.018, 0.01, 12, (0, 0, 0), T(1.935, 0, -0.17) @ RY(90)), lamp)
    sock("Repair_Circuit", (1.95, 0, -0.40), (0, 0, 180))
    sock("Interact_Console", (1.68, 0, -0.10))
    put("Footrest", box((0.16, 1.0, 0.03), (0, 0, 0), T(1.86, 0, FLOOR + 0.12) @ RY(-20)), C["dark"])

    # ---- wrecked dressing
    if W:
        rnd = random.Random(11)
        put("Puddles", merged([disc(r, FLOOR + 0.002, (x, y), 22, sx, 1.0, 0.25, i) for i, (x, y, r, sx) in
                               enumerate(((-0.6, 0.1, 0.32, 1.6), (1.1, -0.2, 0.22, 1.3), (0.4, 0.35, 0.18, 1.0), (-1.3, 0.05, 0.2, 1.2)))]), C["water"])
        # silt banks along the floor edges (max half-length 0.2*1.6*1.35 = 0.43 m, kept inside x -1.6..2.2)
        put("Silt", merged([disc(0.2, FLOOR + 0.004 + 0.001 * i, (x, s * 0.66), 18, 1.6, 0.35, 0.35, 20 + i) for i, (x, s) in
                            enumerate(((-1.1, -1), (-0.3, 1), (0.6, -1), (1.3, 1), (1.65, -1), (-0.9, 1)))]), C["silt"])
        put("Mold", merged([shell_patch(x - 0.12, x + 0.12, a - 6, a + 6, 0.973, 0.002, 1, 3) for x, a in
                            ((-1.3, 50), (-0.5, -52), (0.7, 45), (1.4, -48), (0.1, 55), (1.8, 40))]), C["mold"], smooth=True)
        shards = []
        for i in range(60):   # dome glass fragments in the cockpit
            x = rnd.uniform(1.55, 2.15) if i < 40 else rnd.uniform(1.85, 2.15)
            y = rnd.uniform(-0.65, 0.65); z = FLOOR + 0.004 if i < 40 else 0.0
            b = bmesh.new(); s_ = rnd.uniform(0.015, 0.05)
            for _ in range(5):
                a = rnd.uniform(0, math.tau); b.verts.new((x + s_ * math.cos(a), y + s_ * math.sin(a), z + rnd.uniform(0.0, 0.008)))
            bmesh.ops.convex_hull(b, input=b.verts[:]); shards.append(b)
        put("GlassShards", merged(shards), C["glass"])
        put("Foam", merged([disc(0.04, -0.21, (1.38 + rnd.uniform(-0.1, 0.1), 0.36 + rnd.uniform(-0.1, 0.1)), 8, 1, 1, 0.4, 40 + i) for i in range(5)]), C["foam"])
        put("Papers", merged([box((0.21, 0.297, 0.002), (0, 0, 0), Matrix.Translation((rnd.uniform(-1.2, 1.4), rnd.uniform(-0.4, 0.4), FLOOR + 0.006 + i * 0.001)) @ RZ(rnd.uniform(0, 180)))
                              for i in range(7)]), C["white"])

    # ---- repaired: install the pickups on their sockets
    if R:
        for item, skt in (("ScrubberCartridge", "Repair_Scrubber"), ("CircuitBoard", "Repair_Circuit")):
            it = bpy.data.objects[item]; S = bpy.data.objects["SKT_" + skt + sfx].matrix_basis.copy()
            for c in it.children_recursive:
                if c.type != "MESH": continue
                d = c.copy(); d.data = c.data.copy(); d.name = f"S2I_Inst_{c.name}{sfx}"; col.objects.link(d)
                d.parent = root; d.matrix_parent_inverse = Matrix.Identity(4); d.matrix_basis = S @ (it.matrix_world.inverted() @ c.matrix_world)

    # soften the boxy furniture (bevel modifier, applied by export_unreal through the evaluated mesh)
    for nm, w in (("Locker", 0.006), ("Rack", 0.008), ("BayCabinet", 0.012), ("BayDrawers", 0.008), ("WallLockers", 0.012),
                  ("FoldSeat", 0.015), ("Medkit", 0.01), ("O2Panel", 0.01), ("ScrubberBody", 0.008), ("PowerPanel", 0.008),
                  ("ConsoleBase", 0.012), ("ConsoleDesk", 0.015), ("ConsoleFront", 0.008), ("SeatCushions", 0.025), ("ScreenFrames", 0.008)):
        o = bpy.data.objects.get("S2I_" + nm + sfx)
        if o: bevel(o, w, 3 if nm == "SeatCushions" else 2)
    bpy.context.view_layer.update()
    return root


def export_state(state):
    """export_unreal with the scene-only socket suffix removed (other models own the plain SKT_ names)."""
    sfx = SFX[state]; root = bpy.data.objects[NAME[state]]
    mine = [o for o in root.children if o.name.startswith("SKT_") and o.name.endswith(sfx)]
    parked = []
    for o in mine:
        plain = o.name[:-len(sfx)]
        other = bpy.data.objects.get(plain)
        if other: other.name = plain + "__park"; parked.append((other, plain))
        o.name = plain
    try:
        return export_unreal(NAME[state], SM[state], (0, 0, -1.55))
    finally:
        for o in mine: o.name = o.name + sfx
        for other, plain in parked: other.name = plain


mats()
build_parts()
for st in ("G", "W", "R"):
    build(st)
print("MK2 INTERIOR built", list(NAME.values()))
