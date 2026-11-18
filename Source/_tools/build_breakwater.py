# Map prop: submerged breakwater (2026-11-18). exec after mk.py (+ weather_bake.py for the baked export) in DiveGear_Scene.blend.
# A 30 m section: six concrete caissons in a row (3.5 m high) with a capping slab, a sea-side mound of tetrapods
# (two layers, ~90 units) on a rubble core, rubble toe on the seabed.
# Hiding: voids inside the tetrapod pile (3, roofed by bridging units), the drainage culvert through caisson 4
# (open both ends -> escape to the land side), and the gap next to the broken caisson 2 (tilted seaward, cracked,
# a spalled chunk on the seabed).
# Details: expansion joints, bollards, rusty mooring rings with rust runs, rusty ladder on the land side, a marker
# pole with a hanging chain at the +X end, a fishing net with floats snagged on the tetrapods, a lost anchor,
# barnacles, mussels, anemones, algae patches.
# Frame: pivot = seabed (z = 0) at the middle of the wall's sea face; wall runs along X, sea side is -Y.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise

MT = bpy.data.materials
ROOT, POS, SFX, SM_NAME = "Breakwater", Vector((0, 125, 0)), "__BW", "SM_Breakwater"
SEG_X = [-15.0, -10.0, -5.0, 0.0, 5.0, 10.0, 15.0]          # caisson boundaries
WALL_Y, WALL_H = (0.0, 3.0), 3.5
CULVERT = (2.5, 1.05, 0.65, 0.8)                             # x, z centre, inner r, outer r (runs along Y)
BROKEN = 1                                                   # caisson index (0-based) that broke
HIDES = [Vector((-9.0, -4.6, 0)), Vector((8.4, -4.2, 0)), Vector((12.4, -5.8, 0))]   # tetrapod voids (x, y)
GAP_X = SEG_X[BROKEN + 1] - 0.45                             # centre of the slot next to the broken caisson
CORRIDORS = [(CULVERT[0], 1.6), (GAP_X, 1.3)]                # access lanes cut through the mound down to the seabed (x, half width)

C = {}
def mats():
    g = lambda n, c, **k: MT.get(n) or mat(n, c, **k)
    C["conc"] = mat("M_Bw_Concrete", (0.5, 0.49, 0.45), rough=0.9)
    C["tetra"] = mat("M_Bw_Tetrapod", (0.43, 0.42, 0.39), rough=0.9)
    C["cap"] = mat("M_Bw_CapSlab", (0.55, 0.54, 0.5), rough=0.9)
    C["steel"] = mat("M_Bw_SteelRusty", (0.3, 0.14, 0.06), rough=0.9)
    C["dark"] = mat("M_Bw_Dark", (0.03, 0.03, 0.03), rough=0.9)
    C["net"] = mat("M_Bw_Net", (0.14, 0.18, 0.14), rough=0.95)
    C["float"] = mat("M_Bw_Float", (0.9, 0.4, 0.05), rough=0.6)
    C["barn"] = mat("M_Bw_Barnacle", (0.68, 0.65, 0.58), rough=0.85)
    C["mussel"] = mat("M_Bw_Mussel", (0.06, 0.055, 0.05), metal=0.1, rough=0.35)
    C["anem"] = mat("M_Bw_Anemone", (0.95, 0.6, 0.35), rough=0.5)
    C["algae"] = mat("M_Bw_Algae", (0.16, 0.22, 0.12), rough=0.95)
    C["sed"] = g("M_Seabed_Sediment", (0.33, 0.31, 0.27), rough=0.95)
    C["rock"] = g("M_Seabed_Rock", (0.22, 0.21, 0.2), rough=0.85)
    W = {"conc": dict(rust=0.25, grime=0.7, streak=0.55, mold=0.5, pit=0.9, scale=0.9), "tetra": dict(rust=0.15, grime=0.75, mold=0.6, pit=1.0, scale=1.2),
         "cap": dict(rust=0.2, grime=0.6, streak=0.4, mold=0.45, pit=0.9), "steel": dict(rust=0.8, grime=0.6, pit=1.0, scale=3.0),
         "net": dict(rust=0.1, grime=0.6, mold=0.5, scale=3.0), "float": dict(rust=0.15, grime=0.6, mold=0.4, scale=3.0),
         "barn": dict(rust=0.1, grime=0.4, scale=4.0), "mussel": dict(rust=0.1, grime=0.3, scale=5.0, rough=0.4), "anem": dict(rust=0.0, grime=0.2),
         "algae": dict(rust=0.0, grime=0.4, mold=0.6, scale=2.0), "sed": dict(rust=0.0, grime=0.5, mold=0.2, scale=0.8, bump=0.6),
         "rock": dict(rust=0.1, grime=0.55, mold=0.35, scale=1.5)}
    if "weather" in globals():
        for k, prm in W.items(): weather(C[k], **prm)


# ---------------------------------------------------------------- helpers
def merged(bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("_t"); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out


def nz(p, sc):
    return noise.noise(Vector(p) * sc)


def rock(center, size, seed, sub=2, amp=0.35):
    b = bmesh.new(); bmesh.ops.create_icosphere(b, subdivisions=sub, radius=1.0)
    for v in b.verts:
        v.co *= 1.0 + amp * nz(v.co + Vector((seed, 0, 0)), 1.4)
    bmesh.ops.transform(b, matrix=Matrix.Translation(center) @ Matrix.Diagonal((*size, 1)), verts=b.verts); return b


def mound_z(x, y):
    """Top of the rubble core under the tetrapods (sea side, y < 0); pockets under the hiding voids."""
    z = 2.6 + 0.5 * y + 0.08 * nz((x * 0.5, y * 0.5, 2.0), 1.0)
    for h in HIDES:
        d = math.hypot(x - h.x, y - h.y)
        if d < 1.6: z -= 0.6 * (1 - (d / 1.6) ** 2)
    for cx, w in CORRIDORS:                                    # lanes to the culvert mouth and the broken gap
        t = max(0.0, 1 - (abs(x - cx) / (w + 0.8)) ** 2)
        z = z * (1 - t) + 0.02 * t
    return max(z, 0.05 * nz((x, y, 5.0), 1.0))


TETRA_DIRS = [Vector(v).normalized() for v in ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1))]

def tetrapod(center, R, size=1.0):
    """Four tapered concrete legs at tetrahedral angles + a rounded hub."""
    parts = [rock(center, (0.36 * size,) * 3, 1, sub=2, amp=0.02)]
    for d in TETRA_DIRS:
        d = R @ d; L = 1.2 * size                                # long tapering legs (classic tetrapod proportions)
        b = lathe([(0.0, 0.0), (0.34 * size, 0.0), (0.2 * size, L), (0.15 * size, L + 0.05 * size), (0.0, L + 0.07 * size)], 14,
                  Matrix.Translation(center) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4())
        parts.append(b)
    out = merged(parts)
    for v in out.verts:                                        # chipped edges
        v.co += Vector((nz(v.co * 3, 1.0), nz(v.co * 3 + Vector((5, 0, 0)), 1.0), nz(v.co * 3 + Vector((0, 5, 0)), 1.0))) * 0.03 * size
    return out


def rand_rot(rnd):
    return (Matrix.Rotation(rnd.uniform(0, math.tau), 3, "Z") @ Matrix.Rotation(rnd.uniform(0, math.tau), 3, "X") @ Matrix.Rotation(rnd.uniform(0, math.tau), 3, "Y"))


# ---------------------------------------------------------------- build
def build():
    rnd = random.Random(23)
    for o in [o for o in bpy.data.objects if o.name.endswith(SFX)]:
        bpy.data.objects.remove(o, do_unlink=True)
    col = get_col(ROOT)
    old = bpy.data.objects.get(ROOT)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    root = bpy.data.objects.new(ROOT, None); col.objects.link(root); root.location = POS

    def put(name, bm, mats_, smooth=False):
        mats_ = mats_ if isinstance(mats_, (list, tuple)) else [mats_]
        o = finish(col, "BW_" + name + SFX, bm, mats_[0], smooth=smooth)
        for m in mats_[1:]: o.data.materials.append(m)
        o.parent = root; return o

    def sock(name, loc, normal=None):
        e = bpy.data.objects.new("SKT_" + name + SFX, None); col.objects.link(e)
        e.empty_display_type = "ARROWS"; e.empty_display_size = 0.4; e.parent = root
        R = Vector(normal).to_track_quat("Z", "Y").to_matrix().to_4x4() if normal else Matrix()
        e.matrix_basis = Matrix.Translation(loc) @ R

    # ---- caissons (with joints, slight settling), broken one tilted seaward with a crack and a fallen chunk
    y0, y1 = WALL_Y; walls, caps = [], []
    culvert_seg = None; broken_M = Matrix()
    for i in range(len(SEG_X) - 1):
        xa, xb = SEG_X[i] + 0.04, SEG_X[i + 1] - 0.04
        if i == BROKEN: xb -= 0.85                                                     # gap next to the broken caisson
        b = box((xb - xa, y1 - y0, WALL_H), ((xa + xb) / 2, (y0 + y1) / 2, WALL_H / 2))
        cap = box((xb - xa + 0.06, y1 - y0 + 0.3, 0.35), ((xa + xb) / 2, (y0 + y1) / 2, WALL_H + 0.17))
        settle = Matrix.Translation((0, rnd.uniform(-0.04, 0.04), rnd.uniform(-0.05, 0.0))) @ Matrix.Rotation(math.radians(rnd.uniform(-0.6, 0.6)), 4, "Z")
        if i == BROKEN:
            settle = Matrix.Translation(((xa + xb) / 2, y0, 0)) @ Matrix.Rotation(math.radians(-7), 4, "X") @ Matrix.Rotation(math.radians(2), 4, "Y") @ Matrix.Translation((-(xa + xb) / 2, -y0, -0.25))
        xf(b, settle); xf(cap, settle)
        if i == BROKEN: broken_M = settle
        if SEG_X[i] < CULVERT[0] < SEG_X[i + 1]: culvert_seg = b
        else: walls.append(b)
        caps.append(cap)
    # culvert hole through its caisson (exact boolean on a temporary object)
    me = bpy.data.meshes.new("_cs"); culvert_seg.to_mesh(me); culvert_seg.free()
    seg_o = bpy.data.objects.new("_cs", me); col.objects.link(seg_o)
    cut = cyl(CULVERT[3], 6.0, 32, (0, 0, 0), Matrix.Translation((CULVERT[0], 1.5, CULVERT[1])) @ Matrix.Rotation(math.radians(90), 4, "X"))
    me2 = bpy.data.meshes.new("_cc"); cut.to_mesh(me2); cut.free(); cut_o = bpy.data.objects.new("_cc", me2); col.objects.link(cut_o)
    m = seg_o.modifiers.new("hole", "BOOLEAN"); m.operation = "DIFFERENCE"; m.solver = "EXACT"; m.object = cut_o
    new_me = bpy.data.meshes.new_from_object(seg_o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(seg_o, do_unlink=True); bpy.data.objects.remove(cut_o, do_unlink=True); bpy.data.meshes.remove(me); bpy.data.meshes.remove(me2)
    hb = bmesh.new(); hb.from_mesh(new_me); bpy.data.meshes.remove(new_me); walls.append(hb)
    put("Caissons", merged(walls), C["conc"])
    put("CapSlabs", merged(caps), C["cap"])
    # crack on the broken caisson + spalled chunk on the seabed in front of the gap
    bx = (SEG_X[BROKEN] + SEG_X[BROKEN + 1] - 0.85) / 2
    crack = [broken_M @ Vector((bx + 0.9 + 0.25 * math.sin(k * 1.7), y0 - 0.012, WALL_H - 0.45 * k)) for k in range(8)]   # on the tilted sea face
    put("Crack", strap(crack, broken_M.to_3x3() @ Vector((0, 1, 0)), 0.06, 0.02), C["dark"])
    put("SpalledChunk", rock(Vector((GAP_X - 2.0, -2.6, 0.45)), (0.9, 0.7, 0.5), 7, sub=1, amp=0.25), C["conc"])     # beside the lane, not in it
    # culvert pipe (open both ends), silt inside, a broken grate on the land end
    pipe = lathe([(CULVERT[2], -1.4), (CULVERT[3], -1.4), (CULVERT[3], 1.4), (CULVERT[2], 1.4), (CULVERT[2], -1.4)], 32,
                 Matrix.Translation((CULVERT[0], 1.5, CULVERT[1])) @ Matrix.Rotation(math.radians(90), 4, "X"))
    put("CulvertPipe", pipe, C["conc"], smooth=True)
    put("CulvertSilt", box((CULVERT[2] * 1.4, 5.4, 0.12), (CULVERT[0], 1.5, CULVERT[1] - CULVERT[2] + 0.07)), C["sed"])
    bars = [cyl(0.02, 1.2, 6, (0, 0, 0), Matrix.Translation((CULVERT[0] - 0.45 + 0.15 * k, y1 + 1.35, CULVERT[1] - 0.1 * (k % 3 == 1))) @ Matrix.Rotation(math.radians(20 * (k == 3)), 4, "Y"))
            for k in range(7) if k != 4]
    put("CulvertGrate", merged(bars + [box((1.3, 0.04, 0.05), (CULVERT[0], y1 + 1.35, CULVERT[1] + 0.55))]), C["steel"], smooth=True)

    # ---- bollards, mooring rings with rust runs, ladder (land side), marker pole + chain at +X end
    put("Bollards", merged([lathe([(0.0, 0.0), (0.22, 0.0), (0.2, 0.35), (0.28, 0.45), (0.28, 0.52), (0.0, 0.52)], 16, Matrix.Translation((x, 1.5, WALL_H + 0.35)))
                            for x in (-12.5, 7.5, 12.5)]), C["steel"], smooth=True)
    rings, runs = [], []
    for x in (-12.5, -2.5, 7.5, 12.5):
        M = Matrix.Translation((x, y0 - 0.06, WALL_H - 0.6)) @ Matrix.Rotation(math.radians(90), 4, "X")
        rings.append(torus(0.18, 0.03, 16, 6, M @ Matrix.Translation((0, -0.2, 0))))
        rings.append(box((0.12, 0.1, 0.12), (x, y0 - 0.05, WALL_H - 0.42)))
        runs.append(box((0.08, 0.006, 1.6), (x + rnd.uniform(-0.05, 0.05), y0 - 0.004, WALL_H - 1.4)))
    put("MooringRings", merged(rings), C["steel"], smooth=True)
    put("RustRuns", merged(runs), C["steel"])
    lad = [box((0.05, 0.05, WALL_H + 0.3), (x, y1 + 0.18, (WALL_H + 0.3) / 2)) for x in (-1.3, -0.9)]
    lad += [box((0.42, 0.04, 0.04), (-1.1, y1 + 0.18, 0.3 + 0.3 * k)) for k in range(11) if k != 6]
    lad += [box((0.05, 0.2, 0.05), (x, y1 + 0.08, z)) for x in (-1.3, -0.9) for z in (0.6, 2.0, 3.3)]
    put("Ladder", merged(lad), C["steel"])
    put("MarkerPole", merged([cyl(0.12, 4.0, 14, (14.2, 1.5, WALL_H + 2.35)), cyl(0.3, 0.15, 14, (14.2, 1.5, WALL_H + 0.42)),
                              lathe([(0.0, 0.0), (0.22, 0.0), (0.22, 0.3), (0.12, 0.42), (0.0, 0.42)], 14, Matrix.Translation((14.2, 1.5, WALL_H + 4.35)))]), C["steel"], smooth=True)
    links = []
    chain = catmull([Vector((14.2, 1.3, WALL_H + 3.0)), Vector((14.6, -0.4, WALL_H + 0.6)), Vector((14.8, -1.2, 1.2)), Vector((15.6, -2.5, 0.1)), Vector((16.8, -3.0, 0.08))], 10)
    for k in range(len(chain) - 1):
        d = chain[k + 1] - chain[k]; M = Matrix.Translation(chain[k]) @ d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Rotation(math.radians(90 * (k % 2)), 4, "Z")
        links.append(torus(0.1, 0.028, 10, 5, M @ Matrix.Diagonal((0.7, 1.0, 1.0, 1.0))))
    put("MarkerChain", merged(links), C["steel"], smooth=True)

    # ---- rubble core (sea side) with pockets under the voids, rubble toe, seabed
    bm = bmesh.new(); NX, NY = 72, 26; rows = []
    for j in range(NY + 1):
        y = -9.0 + 9.0 * j / NY; row = []
        for i in range(NX + 1):
            x = -15.5 + 31.0 * i / NX; row.append(bm.verts.new((x, y, mound_z(x, y) - 0.35)))
        rows.append(row)
    for j in range(NY):
        for i in range(NX):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    put("RubbleCore", bm, C["rock"], smooth=True)
    toe = []
    for k in range(70):
        x = rnd.uniform(-15, 15); y = rnd.uniform(-10.5, -6.5); s = rnd.uniform(0.25, 0.7)
        toe.append(rock(Vector((x, y, max(0.0, mound_z(x, y) - 0.35) + s * 0.3)), (s, s * 0.8, s * 0.6), 100 + k, sub=2, amp=0.35))
    for k in range(25):                                                                 # land-side rubble at the wall foot
        x = rnd.uniform(-15, 15); s = rnd.uniform(0.2, 0.5); toe.append(rock(Vector((x, y1 + rnd.uniform(0.2, 1.2), s * 0.3)), (s, s * 0.8, s * 0.6), 200 + k))
    put("RubbleToe", merged(toe), C["rock"], smooth=True)
    bm = bmesh.new(); NX, NY = 64, 30; rows = []
    for j in range(NY + 1):
        y = -14.0 + 22.0 * j / NY; row = []
        for i in range(NX + 1):
            x = -19.0 + 38.0 * i / NX
            row.append(bm.verts.new((x, y, 0.04 * nz((x, y, 1.0), 0.6) * min(1.0, (19 - abs(x)) / 3, (y + 14) / 3, (8 - y) / 3))))
        rows.append(row)
    for j in range(NY):
        for i in range(NX):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    put("Seabed", bm, C["sed"], smooth=True)

    # ---- tetrapods: two layers on the slope, voids kept open around HIDES and roofed by a bridging unit
    tps, roofs = [], []
    for layer in range(2):
        for row in range(4 if layer == 0 else 2):
            y = -1.5 - 2.0 * row - 1.0 * layer
            for col_ in range(14):
                x = -14.4 + 2.3 * col_ + (1.15 if (row + layer) % 2 else 0.0) + rnd.uniform(-0.2, 0.2)
                if x > 14.6: continue
                yy = y + rnd.uniform(-0.25, 0.25)
                if any(math.hypot(x - h.x, yy - h.y) < 1.6 for h in HIDES): continue
                if any(abs(x - cx) < w + 0.9 for cx, w in CORRIDORS): continue        # keep the access lanes open
                if layer == 1 and rnd.random() < 0.35: continue                      # patchy second layer
                z = mound_z(x, yy) + 0.65 + 0.9 * layer
                tps.append(tetrapod(Vector((x, yy, z)), rand_rot(rnd), rnd.uniform(0.92, 1.08)))
    for h in HIDES:                                                                     # roof over each void
        z = mound_z(h.x, h.y) + 1.9
        roofs.append(tetrapod(Vector((h.x + 0.2, h.y + 0.1, z)), rand_rot(rnd), 1.05))
    put("Tetrapods", merged(tps + roofs), C["tetra"], smooth=True)

    # ---- snagged fishing net with floats, lost anchor
    net = []
    NX0 = -13.2                                                        # snagged on the tetrapods at the -X end (clear of the lanes)
    for k in range(4):
        pts = [Vector((NX0 + 0.9 * k, -1.6, mound_z(NX0 + 0.9 * k, -1.6) + 1.4)), Vector((NX0 + 0.3 + 0.9 * k, -3.2, mound_z(NX0 + 0.3, -3.2) + 1.0)),
               Vector((NX0 + 0.5 + 0.9 * k, -4.8, mound_z(NX0 + 0.5, -4.8) + 0.8)), Vector((NX0 + 0.8 + 0.9 * k, -6.4, mound_z(NX0 + 0.8, -6.4) + 0.5))]
        net.append(strap(catmull(pts, 8), Vector((1, 0, 0)), lambda q: 0.85 - 0.25 * q, 0.06))
    put("FishingNet", merged(net), C["net"], smooth=True)
    put("NetFloats", merged([lathe([(0.0, -0.12), (0.12, -0.08), (0.13, 0.0), (0.12, 0.08), (0.0, 0.12)], 12, Matrix.Translation((NX0 + 0.9 * k, -1.5 - 1.6 * j, mound_z(NX0, -1.5 - 1.6 * j) + 1.5 - 0.25 * j)))
                             for k in range(4) for j in range(3)]), C["float"], smooth=True)
    ap = Vector((-3.5, -8.4, 0.2))
    put("LostAnchor", merged([box((0.14, 0.14, 1.6), (0, 0, 0), Matrix.Translation(ap) @ Matrix.Rotation(math.radians(75), 4, "Y")),
                              box((1.1, 0.14, 0.14), (0, 0, 0), Matrix.Translation(ap + Vector((-0.75, 0, 0.2))) @ Matrix.Rotation(math.radians(-15), 4, "Y")),
                              torus(0.15, 0.04, 12, 5, Matrix.Translation(ap + Vector((0.8, 0, 0.3))) @ Matrix.Rotation(math.radians(90), 4, "X"))]), C["steel"], smooth=True)

    # ---- marine growth: barnacles + mussels low on the sea face and on tetrapods, anemones, algae patches
    barn, mus, ane, alg = [], [], [], []
    for k in range(700):
        if k < 450:   # sea face of the wall (lower 2 m)
            p = Vector((rnd.uniform(-15, 15), y0 - 0.01, rnd.uniform(0.1, 2.2))); n = Vector((0, -1, 0))
        else:         # top of the cap slab edge
            p = Vector((rnd.uniform(-15, 15), y0 - 0.16, WALL_H + rnd.uniform(0.0, 0.33))); n = Vector((0, -1, 0))
        h = rnd.uniform(0.015, 0.04); b = bmesh.new(); bmesh.ops.create_cone(b, cap_ends=True, segments=6, radius1=h * 1.1, radius2=h * 0.35, depth=h)
        bmesh.ops.transform(b, matrix=Matrix.Translation(p + n * (h / 2)) @ n.to_track_quat("Z", "Y").to_matrix().to_4x4(), verts=b.verts); barn.append(b)
    for k in range(40):   # mussel clumps at the wall foot
        cx = rnd.uniform(-15, 15)
        for _ in range(rnd.randint(8, 14)):
            p = Vector((cx + rnd.gauss(0, 0.12), y0 - 0.05 - abs(rnd.gauss(0, 0.05)), abs(rnd.gauss(0.25, 0.15))))
            b = bmesh.new(); bmesh.ops.create_uvsphere(b, u_segments=6, v_segments=4, radius=1.0)
            bmesh.ops.transform(b, matrix=Matrix.Translation(p) @ Matrix.Rotation(rnd.uniform(0, 6.3), 4, "Y") @ Matrix.Rotation(rnd.uniform(-0.5, 0.5), 4, "X") @ Matrix.Diagonal((0.06, 0.028, 0.024, 1)), verts=b.verts); mus.append(b)
    for k in range(40):
        p = Vector((rnd.uniform(-14, 14), rnd.uniform(-8, -1.5), 0)); p.z = mound_z(p.x, p.y) + 1.25 + 0.6 * rnd.random()
        b = cyl(0.04, 0.08, 8, (p.x, p.y, p.z + 0.04))
        for q in range(10):
            fr = bmesh.new(); bmesh.ops.create_cone(fr, cap_ends=True, segments=4, radius1=0.01, radius2=0.002, depth=0.08)
            bmesh.ops.transform(fr, matrix=Matrix.Translation(p + Vector((0, 0, 0.08))) @ Matrix.Rotation(q / 10 * math.tau, 4, "Z") @ Matrix.Rotation(math.radians(55), 4, "X") @ Matrix.Translation((0, 0, 0.04)), verts=fr.verts)
            mm = bpy.data.meshes.new("_t"); fr.to_mesh(mm); fr.free(); b.from_mesh(mm); bpy.data.meshes.remove(mm)
        ane.append(b)
    for k in range(26):   # algae / sponge-mat patches on the sea face
        x = rnd.uniform(-14.5, 14.5); z = rnd.uniform(0.3, 2.8); r = rnd.uniform(0.3, 0.9)
        alg.append(plate_poly_y([Vector((x + r * math.cos(a) * (1 + 0.4 * nz((a, k, 1), 2)), y0 - 0.008, z + r * 0.6 * math.sin(a))) for a in (q / 14 * math.tau for q in range(14))]))
    put("Barnacles", merged(barn), C["barn"])
    put("Mussels", merged(mus), C["mussel"], smooth=True)
    put("Anemones", merged(ane), C["anem"], smooth=True)
    put("AlgaePatches", merged(alg), C["algae"])

    # ---- sockets
    for i, h in enumerate(HIDES): sock(f"Hide_Tetrapod_{i + 1}", Vector((h.x, h.y, max(mound_z(h.x, h.y) - 0.35, 0.0) + 0.02)))   # on the pocket floor
    sock("Hide_Culvert", Vector((CULVERT[0], 1.5, CULVERT[1] - CULVERT[2] + 0.13)))
    sock("Culvert_SeaEnd", Vector((CULVERT[0], -0.4, CULVERT[1] - CULVERT[2] + 0.13)), (0, -1, 0))
    sock("Culvert_LandEnd", Vector((CULVERT[0], 3.4, CULVERT[1] - CULVERT[2] + 0.13)), (0, 1, 0))
    sock("Hide_BrokenGap", Vector((GAP_X, 1.0, 0.1)))
    sock("Ladder_Bottom", Vector((-1.1, y1 + 0.6, 0.0))); sock("Ladder_Top", Vector((-1.1, y1 - 0.3, WALL_H + 0.35)))
    bpy.context.view_layer.update()
    return root


def plate_poly_y(pts):
    b = bmesh.new(); vs = [b.verts.new(p) for p in pts]; b.faces.new(vs)
    bmesh.ops.solidify(b, geom=b.faces[:], thickness=0.006); return b


def export_all():
    root = bpy.data.objects[ROOT]
    mine = [o for o in root.children if o.name.startswith("SKT_") and o.name.endswith(SFX)]
    parked = []
    for o in mine:
        plain = o.name[:-len(SFX)]; other = bpy.data.objects.get(plain)
        if other: other.name = plain + "__park"; parked.append((other, plain))
        o.name = plain
    try:
        if "bake_export" in globals():
            return bake_export(ROOT, SM_NAME, "Breakwater", size=4096)
        return export_unreal(ROOT, SM_NAME, (0, 0, 0))
    finally:
        for o in mine: o.name = o.name + SFX
        for other, plain in parked: other.name = plain


mats()
build()
print("BREAKWATER built")
