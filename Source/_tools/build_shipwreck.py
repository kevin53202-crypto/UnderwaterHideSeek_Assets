# Map prop: shipwreck (2026-11-18). exec after mk.py in DiveGear_Scene.blend.
# A sunken 24 m steel fishing trawler, listing 18 deg to port and 3 deg bow-down, half-buried in a sediment mound.
# Weathering (v2): faded paint, rust blooms and peeled primer on the hull, barnacle crust, silt and rust on the decks,
# rusted-through deck holes, bent/missing bulwark panels, rust runs under the wheelhouse windows.
# Interior (v2): wheelhouse fittings (radar, radio, binnacle, settee, shelves, life jackets, clutter, stairs down),
# a new crew-quarters deck under the wheelhouse (bunks, lockers, mess table, galley) with a door into the hold, and
# extra hold clutter (shelving, rope, net bundles, ice boxes, ladder, chain, fish bones).
# Hiding places: the cargo hold (enter through the open deck hatch or a torn hole in the starboard topsides; crates,
# barrels and fish boxes slid to the low port side) and the wheelhouse (broken windows, doorless doorway; console,
# wheel, toppled chair, chart table).
# Ship-local frame (before the list): x along the hull (-12 stern .. +12 bow), baseline z = 0, +Y starboard.
# Everything on the ship is built in that frame and moved by SHIP; seabed parts are built in the root frame.
# Root frame: pivot = seabed (z = 0) under midships, bow +X.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise

MT = bpy.data.materials
ROOT, POS, SFX, SM_NAME = "Shipwreck", Vector((0, 80, 0)), "__SW", "SM_Shipwreck"
L = 24.0
LIST, PITCH, SINK = 18.0, 3.0, -0.6
SHIP = Matrix.Translation((0, 0, SINK)) @ Matrix.Rotation(math.radians(PITCH), 4, "Y") @ Matrix.Rotation(math.radians(LIST), 4, "X")
TH = 0.06                                  # hull plate thickness
NS_, NT_ = 140, 56
HOLE = (0.47, 1.25, 0.045, 0.24)           # starboard torn hole: s, theta (rad), half-sizes
HOLD = (0.35, 0.62)                        # hold between two bulkheads (s)
HATCH = (0.43, 0.54, 1.3)                  # deck hatch: s0, s1, half-width (m)
FLOOR_Z = 0.9                              # hold floor (tank top), also the crew-quarters floor
CABIN = (0.10, 0.35)                       # crew quarters under the wheelhouse (aft bulkhead .. hold bulkhead)
STAIR = (0.146, 0.182, -1.65, -0.85)       # stair hole in the wheelhouse floor: s0, s1, y0, y1
DECK_HOLES = [(0.30, -2.0, 0.3), (0.40, 1.7, 0.33), (0.58, 0.9, 0.3), (0.66, -1.3, 0.42), (0.72, 1.4, 0.3)]   # rusted-through: s, y, r
DOOR = (-0.45, 0.45, 1.85)                 # doorway hold <-> crew quarters (y0, y1, height)

C = {}
def mats():
    g = lambda n, c, **k: MT.get(n) or mat(n, c, **k)
    C["black"] = mat("M_Wreck_HullBlack", (0.11, 0.1, 0.095), metal=0.2, rough=0.85)          # faded black paint
    C["anti"] = mat("M_Wreck_Antifoul", (0.27, 0.11, 0.08), rough=0.9)
    C["boot"] = mat("M_Wreck_BootTop", (0.5, 0.47, 0.41), rough=0.85)
    C["primer"] = mat("M_Wreck_Primer", (0.38, 0.36, 0.32), rough=0.9)
    C["silt"] = mat("M_Wreck_Silt", (0.36, 0.33, 0.27), rough=0.98)
    C["barnacle"] = mat("M_Wreck_Barnacle", (0.68, 0.65, 0.58), rough=0.85)
    C["mattress"] = mat("M_Wreck_Mattress", (0.33, 0.29, 0.22), rough=0.98)
    C["fabric"] = mat("M_Wreck_Fabric", (0.17, 0.2, 0.24), rough=0.95)
    C["screen"] = mat("M_Wreck_Screen", (0.04, 0.07, 0.06), metal=0.3, rough=0.15)
    C["brass"] = mat("M_Wreck_Brass", (0.42, 0.33, 0.14), metal=0.8, rough=0.5)
    C["ceramic"] = mat("M_Wreck_Ceramic", (0.72, 0.7, 0.64), rough=0.4)
    C["bottle"] = mat("M_Wreck_Bottle", (0.14, 0.22, 0.12), metal=0.1, rough=0.15)
    C["bone"] = MT.get("M_Whale_Bone") or mat("M_Whale_Bone", (0.78, 0.74, 0.62), rough=0.7)
    C["rust"] = mat("M_Wreck_Rust", (0.3, 0.14, 0.06), rough=0.95)
    C["rust2"] = mat("M_Wreck_RustDark", (0.2, 0.09, 0.05), rough=0.95)
    C["deck"] = mat("M_Wreck_Deck", (0.24, 0.21, 0.17), metal=0.2, rough=0.9)
    C["white"] = mat("M_Wreck_PaintWhite", (0.52, 0.49, 0.42), rough=0.85)                  # stained, faded white
    C["metal"] = mat("M_Wreck_Metal", (0.3, 0.3, 0.3), metal=0.6, rough=0.6)
    C["inside"] = mat("M_Wreck_Inside", (0.12, 0.1, 0.08), rough=0.9)
    C["glass"] = mat("M_Wreck_Glass", (0.1, 0.16, 0.16), metal=0.2, rough=0.1, alpha=0.5)
    C["hole"] = mat("M_Wreck_Dark", (0.02, 0.02, 0.02), rough=0.9)
    C["wood"] = mat("M_Wreck_WoodRotten", (0.26, 0.2, 0.13), rough=0.95)
    C["net"] = mat("M_Wreck_Net", (0.13, 0.17, 0.13), rough=0.95)
    C["float"] = mat("M_Wreck_Float", (0.9, 0.4, 0.05), rough=0.6)
    C["barrel"] = mat("M_Wreck_Barrel", (0.2, 0.27, 0.38), metal=0.3, rough=0.7)
    C["fishbox"] = mat("M_Wreck_FishBox", (0.2, 0.45, 0.55), rough=0.6)
    C["anem_w"] = mat("M_Wreck_AnemoneWhite", (0.9, 0.88, 0.82), rough=0.5)
    C["anem_o"] = mat("M_Wreck_AnemoneOrange", (0.95, 0.45, 0.12), rough=0.5)
    C["sponge"] = mat("M_Wreck_Sponge", (0.85, 0.7, 0.2), rough=0.9)
    C["sed"] = g("M_Seabed_Sediment", (0.33, 0.31, 0.27), rough=0.95)
    C["rock"] = g("M_Seabed_Rock", (0.22, 0.21, 0.2), rough=0.85)
    # weathered procedural look (needs weather_bake.py exec'd first); interior materials get the heaviest rust/grime
    W = {"black": dict(rust=0.55, grime=0.35, streak=0.6, mold=0.1), "anti": dict(rust=0.4, grime=0.45, streak=0.2, mold=0.35),
         "boot": dict(rust=0.55, grime=0.4, streak=0.6), "primer": dict(rust=0.45, grime=0.4), "rust": dict(rust=0.75, grime=0.65, pit=1.0, streak=0.4, mold=0.15),
         "rust2": dict(rust=0.6, grime=0.6, pit=1.0, mold=0.15), "deck": dict(rust=0.75, grime=0.55, mold=0.25), "white": dict(rust=0.5, grime=0.55, streak=0.85, mold=0.2),
         "metal": dict(rust=0.9, grime=0.7, streak=0.5, pit=1.0, mold=0.2, scale=3.0), "inside": dict(rust=0.9, grime=0.7, streak=0.7, mold=0.4, scale=1.4),
         "wood": dict(rust=0.3, grime=1.0, mold=0.7, bump=0.6, scale=2.0), "net": dict(rust=0.1, grime=0.6, mold=0.5), "float": dict(rust=0.15, grime=0.6, mold=0.4),
         "barrel": dict(rust=0.85, grime=0.7, streak=0.5, scale=2.5), "fishbox": dict(rust=0.35, grime=1.0, mold=0.7, scale=2.5), "mattress": dict(rust=0.45, grime=1.0, mold=0.9, scale=2.0),
         "fabric": dict(rust=0.3, grime=1.0, mold=0.8, scale=2.0), "screen": dict(rust=0.1, grime=0.7, mold=0.2), "brass": dict(rust=0.3, grime=0.5, mold=0.7),
         "ceramic": dict(rust=0.5, grime=0.9, mold=0.6, scale=3.0), "bottle": dict(rust=0.1, grime=0.6, mold=0.3), "silt": dict(rust=0.0, grime=0.4, bump=0.8),
         "barnacle": dict(rust=0.15, grime=0.4), "sponge": dict(rust=0.0, grime=0.3), "anem_w": dict(rust=0.0, grime=0.2), "anem_o": dict(rust=0.0, grime=0.2),
         "hole": dict(rust=0.3, grime=0.3), "bone": dict(rust=0.1, grime=0.5, mold=0.3)}
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


def ship(b):
    bmesh.ops.transform(b, matrix=SHIP, verts=b.verts); return b


def rock(center, size, seed, sub=2, amp=0.35):
    b = bmesh.new(); bmesh.ops.create_icosphere(b, subdivisions=sub, radius=1.0)
    for v in b.verts:
        v.co *= 1.0 + amp * nz(v.co + Vector((seed, 0, 0)), 1.4)
    bmesh.ops.transform(b, matrix=Matrix.Translation(center) @ Matrix.Diagonal((*size, 1)), verts=b.verts); return b


def plate_poly(pts, thick):
    """Flat n-gon plate from a closed point loop, solidified."""
    b = bmesh.new(); vs = [b.verts.new(p) for p in pts]; b.faces.new(vs)
    bmesh.ops.solidify(b, geom=b.faces[:], thickness=thick); return b


# ---------------------------------------------------------------- hull lines
def sx(s): return -L / 2 + L * s

def beam(s):
    if s < 0.15: return 2.6 + 0.6 * (s / 0.15) ** 0.5
    if s <= 0.6: return 3.2
    return max(0.05, 3.2 * math.cos((s - 0.6) / 0.4 * math.pi / 2) ** 0.8)

def deck_z(s):
    z = 3.4 + 1.2 * max(0.0, (s - 0.65) / 0.35) ** 1.8
    if s < 0.3: z += 0.25 * (1 - s / 0.3) ** 2
    return z

def keel_z(s):
    if s > 0.82: return 1.6 * ((s - 0.82) / 0.18) ** 2
    if s < 0.05: return 0.6 * (1 - s / 0.05) ** 2
    return 0.0

def ncur(s): return 3.2 - 1.2 * max(0.0, (s - 0.6) / 0.4)

def hull_pt(s, th, inner=False):
    """th in [-pi/2, pi/2]: -pi/2 port deck edge, 0 keel, +pi/2 starboard deck edge."""
    s = min(1.0, max(0.0, s)); th = math.copysign(min(abs(th), math.pi / 2), th)
    b, d, k, n = beam(s), deck_z(s), keel_z(s), ncur(s)
    if inner: b = max(0.02, b - TH); k = k + TH
    a = abs(th); c, sn = max(0.0, math.cos(a)), math.sin(a)
    y = math.copysign(b * sn ** (2 / n), th) if a > 1e-9 else 0.0
    z = k + (d - k) * (1 - c ** (2 / n))
    p = Vector((sx(s), y, z))
    if not inner:   # dents and plate waviness
        p.y += math.copysign(0.06 * nz((p.x * 0.25, p.z * 0.3, 1.0), 1.0) + 0.02 * nz((p.x, p.z, 4.0), 1.0) + 0.012 * math.sin(p.x * 1.7), th) * min(1.0, a * 2)
    return p

def hull_n(s, th):
    e = 1e-3
    n = (hull_pt(s + e, th) - hull_pt(s - e, th)).cross(hull_pt(s, th + e) - hull_pt(s, th - e)).normalized()
    if n.dot(Vector((0, math.copysign(1, th), 0.3 if abs(th) < 0.2 else 0))) < 0: n = -n
    return n

def inner_y(s, z):
    """Inner-hull half breadth at height z (for floors / bulkheads)."""
    b, d, k, n = max(0.02, beam(s) - TH), deck_z(s), keel_z(s) + TH, ncur(s)
    zr = min(1.0, max(0.0, (z - k) / (d - k)))
    c = (1 - zr) ** (n / 2); a = math.acos(min(1.0, c))
    return b * math.sin(a) ** (2 / n)


def in_hole(s, th):
    q = ((s - HOLE[0]) / HOLE[2]) ** 2 + ((th - HOLE[1]) / HOLE[3]) ** 2
    return q < 1.0 + 0.35 * nz((s * 30, th * 6, 2.0), 1.0)


def hull_bm():
    bm = bmesh.new(); ths = [-math.pi / 2 + math.pi * j / NT_ for j in range(NT_ + 1)]
    ss = [k / NS_ for k in range(NS_ + 1)]
    O = [[bm.verts.new(hull_pt(s, th)) for th in ths] for s in ss]
    I = [[bm.verts.new(hull_pt(min(max(s, 0.0025), 0.995), th, True)) for th in ths] for s in ss]
    def fcen(i, j): return (ss[i] + ss[i + 1]) / 2, (ths[j] + ths[j + 1]) / 2
    def skip(i, j):
        if i < 0 or j < 0 or i >= NS_ or j >= NT_: return False
        return in_hole(*fcen(i, j))
    def mat_i(th):
        a = abs(th); return 1 if a < 0.95 else (2 if a < 1.02 else 0)       # antifoul / boot top / black
    for i in range(NS_):
        for j in range(NT_):
            if skip(i, j): continue
            f = bm.faces.new((O[i][j], O[i + 1][j], O[i + 1][j + 1], O[i][j + 1])); f.material_index = mat_i(fcen(i, j)[1])
            g = bm.faces.new((I[i][j + 1], I[i + 1][j + 1], I[i + 1][j], I[i][j])); g.material_index = 3
    bm.faces.new([O[0][j] for j in range(NT_ + 1)]).material_index = 0                      # transom
    bm.faces.new([I[0][j] for j in reversed(range(NT_ + 1))]).material_index = 3
    bm.faces.new([O[NS_][j] for j in reversed(range(NT_ + 1))]).material_index = 0          # stem
    bm.faces.new([I[NS_][j] for j in range(NT_ + 1)]).material_index = 3
    for i in range(NS_):                                                                  # sheer lips
        for j in (0, NT_):
            bm.faces.new((O[i][j], I[i][j], I[i + 1][j], O[i + 1][j])).material_index = 0
    edge = set()
    for i in range(NS_):
        for j in range(NT_):
            if skip(i, j) != skip(i, j - 1): edge |= {(i, j), (i + 1, j)}
            if skip(i, j) != skip(i - 1, j): edge |= {(i, j), (i, j + 1)}
    for (i, j) in edge:   # torn edge: snap onto the ragged ellipse
        s, th = ss[i], ths[j]; a, b = (s - HOLE[0]) / HOLE[2], (th - HOLE[1]) / HOLE[3]
        k = math.sqrt((1.0 + 0.35 * nz((s * 30, th * 6, 2.0), 1.0)) / max(a * a + b * b, 1e-6))
        s2, t2 = HOLE[0] + HOLE[2] * a * k, HOLE[1] + HOLE[3] * b * k
        O[i][j].co = hull_pt(s2, t2)
        I[i][j].co = hull_pt(s2, t2, True)
    for i in range(NS_):
        for j in range(NT_):
            if skip(i, j) != skip(i, j - 1): bm.faces.new((O[i][j], O[i + 1][j], I[i + 1][j], I[i][j])).material_index = 4
            if skip(i, j) != skip(i - 1, j): bm.faces.new((O[i][j], O[i][j + 1], I[i][j + 1], I[i][j])).material_index = 4
    return bm


def deck_bm():
    """Cambered steel deck with the hold hatch opening."""
    bm = bmesh.new(); NSd, NY = 96, 28; rows = []
    for i in range(NSd + 1):
        s = 0.004 + 0.99 * i / NSd; row = []
        for j in range(NY + 1):
            f = -1 + 2 * j / NY; y = f * max(0.02, beam(s) - TH)
            row.append(bm.verts.new((sx(s), y, deck_z(s) + 0.12 * (1 - f * f) - 0.02)))
        rows.append(row)
    for i in range(NSd):
        for j in range(NY):
            v = rows[i][j].co; v2 = rows[i + 1][j + 1].co; s = (v.x + v2.x) / 2 / L + 0.5; y = (v.y + v2.y) / 2
            if HATCH[0] < s < HATCH[1] and abs(y) < HATCH[2]: continue
            if STAIR[0] < s < STAIR[1] and STAIR[2] < y < STAIR[3]: continue
            if any(math.hypot((s - hs) * L, y - hy) < hr * (1 + 0.3 * nz((s * 40, y * 3, 9.0), 1.0)) for hs, hy, hr in DECK_HOLES): continue
            bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.05)
    return bm


# ---------------------------------------------------------------- walls with openings
def wall(axis, c, a0, a1, z0, z1, t, holes=()):
    """Thin wall plane at axis-coordinate c spanning a0..a1 (along the other horizontal axis), z0..z1,
    with rectangular openings holes=[(b0, b1, h0, h1)]. axis 'x': wall normal along X (spans Y)."""
    cuts = sorted(holes); parts = []; prev = a0
    def bx(p0, p1, q0, q1):
        if p1 - p0 < 1e-4 or q1 - q0 < 1e-4: return
        if axis == "x": parts.append(box((t, p1 - p0, q1 - q0), (c, (p0 + p1) / 2, (q0 + q1) / 2)))
        else: parts.append(box((p1 - p0, t, q1 - q0), ((p0 + p1) / 2, c, (q0 + q1) / 2)))
    for (b0, b1, h0, h1) in cuts:
        bx(prev, b0, z0, z1); bx(b0, b1, z0, h0); bx(b0, b1, h1, z1); prev = b1
    bx(prev, a1, z0, z1)
    return parts



# ---------------------------------------------------------------- weathering / interior helpers
def deck_top(x, y):
    s = x / L + 0.5; f = y / max(0.05, beam(s) - TH)
    return deck_z(s) + 0.12 * (1 - min(1.0, f * f)) - 0.02


def slab(pts, depth):
    """Closed top outline -> slab extruded downward by depth (silt piles, rugs, patches)."""
    b = bmesh.new(); vs = [b.verts.new(p) for p in pts]; f = b.faces.new(vs)
    r = bmesh.ops.extrude_face_region(b, geom=[f])
    bmesh.ops.translate(b, vec=(0, 0, -depth), verts=[e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)])
    return b


def blot(cx, cy, r, seed, ztop, segs=20, sy=0.75):
    """Irregular flat patch outline at height ztop(x, y)."""
    pts = []
    for a in range(segs):
        ph = a / segs * math.tau; rr = r * (1 + 0.4 * nz((math.cos(ph), math.sin(ph), seed), 1.7))
        x, y = cx + rr * math.cos(ph), cy + rr * sy * math.sin(ph); pts.append(Vector((x, y, ztop(x, y))))
    return pts


def hull_decal(sc, thc, rs, rt, seed, off, rings=4, segs=22):
    """Irregular patch on the hull surface (rust blooms, peeled primer)."""
    bm = bmesh.new(); rows = []
    for k in range(1, rings + 1):
        row = []
        for a in range(segs):
            ph = a / segs * math.tau; rr = k / rings * (1 + 0.38 * nz((math.cos(ph), math.sin(ph), seed), 1.6))
            ss, tt = sc + rs * rr * math.cos(ph), thc + rt * rr * math.sin(ph)
            row.append(bm.verts.new(hull_pt(ss, tt) + hull_n(ss, tt) * off))
        rows.append(row)
    c0 = bm.verts.new(hull_pt(sc, thc) + hull_n(sc, thc) * off)
    for a in range(segs):
        bm.faces.new((c0, rows[0][a], rows[0][(a + 1) % segs]))
    for k in range(rings - 1):
        for a in range(segs):
            bm.faces.new((rows[k][a], rows[k + 1][a], rows[k + 1][(a + 1) % segs], rows[k][(a + 1) % segs]))
    return bm


def bulkhead(s, z0, door=None, n=26, m=18):
    """Transverse bulkhead following the inner hull section from z0 to the deck, optional doorway."""
    bm = bmesh.new(); zt = deck_z(s) - 0.02; ym = max(0.05, beam(s) - TH)
    grid = [[bm.verts.new((sx(s), -ym + 2 * ym * j / n, z0 + (zt - z0) * i / m)) for j in range(n + 1)] for i in range(m + 1)]
    for i in range(m):
        for j in range(n):
            y = -ym + 2 * ym * (j + 0.5) / n; z = z0 + (zt - z0) * (i + 0.5) / m
            if abs(y) > inner_y(s, z) - 0.02: continue
            if door and door[0] < y < door[1] and z < z0 + door[2]: continue
            bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.05)
    return bm


def lamp(p, drop):
    return merged([cyl(0.006, drop, 4, (p.x, p.y, p.z - drop / 2)),
                   lathe([(0.0, 0.0), (0.16, -0.12), (0.17, -0.14), (0.0, -0.05)], 14, Matrix.Translation(p - Vector((0, 0, drop))))])


def fish_bones(p, yaw, L_):
    M = Matrix.Translation(p) @ RZ(yaw); parts = [tube([M @ Vector((-L_ / 2, 0, 0.02)), M @ Vector((L_ / 2, 0, 0.02))], 0.006, sides=5)]
    for k in range(9):
        x = -L_ / 2 + L_ * (k + 1) / 10
        for sd in (-1, 1):
            parts.append(tube([M @ Vector((x, 0, 0.02)), M @ Vector((x - 0.02, sd * 0.06 * (1 - abs(x) / L_), 0.01))], 0.003, sides=4))
    parts.append(rock(M @ Vector((L_ / 2 + 0.04, 0, 0.03)), (0.05, 0.03, 0.03), 3, sub=1, amp=0.2))
    return merged(parts)

# ---------------------------------------------------------------- build
def build():
    rnd = random.Random(5)
    for o in [o for o in bpy.data.objects if o.name.endswith(SFX)]:
        bpy.data.objects.remove(o, do_unlink=True)
    col = get_col(ROOT)
    old = bpy.data.objects.get(ROOT)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    root = bpy.data.objects.new(ROOT, None); col.objects.link(root); root.location = POS

    def put(name, bm, mats_, smooth=False, on_ship=True):
        if on_ship: ship(bm)
        mats_ = mats_ if isinstance(mats_, (list, tuple)) else [mats_]
        o = finish(col, "SW_" + name + SFX, bm, mats_[0], smooth=smooth)
        for m in mats_[1:]: o.data.materials.append(m)
        o.parent = root; return o

    def sock(name, loc_ship, normal=None):
        """Socket in the ship frame; with 'normal', its +Z points along that (ship-frame) direction."""
        e = bpy.data.objects.new("SKT_" + name + SFX, None); col.objects.link(e)
        e.empty_display_type = "ARROWS"; e.empty_display_size = 0.4; e.parent = root
        R = Vector(normal).to_track_quat("Z", "Y").to_matrix().to_4x4() if normal else Matrix()
        e.matrix_basis = SHIP @ Matrix.Translation(loc_ship) @ R

    # hull + deck
    put("Hull", hull_bm(), [C["black"], C["anti"], C["boot"], C["inside"], C["rust"]], smooth=True)
    put("Deck", deck_bm(), C["deck"])

    # rubbing strake + bulwark with freeing ports + top rail (gaps rusted away)
    rub, bulw, bulw_r, rail = [], [], [], []
    for side in (-1, 1):
        rub.append(tube([hull_pt(s, side * math.pi / 2) + Vector((0, side * 0.04, -0.15)) for s in [0.01 + 0.97 * k / 60 for k in range(61)]], 0.07, sides=6))
        s = 0.05
        while s < 0.93:
            s1 = min(0.93, s + rnd.uniform(0.04, 0.09))
            r_ = rnd.random()
            if r_ > 0.26:   # else: rusted away
                p0, p1 = hull_pt(s, side * math.pi / 2), hull_pt(s1, side * math.pi / 2)
                lean = Vector((0, side * rnd.uniform(0.15, 0.45), -0.1)) if r_ < 0.42 else Vector((0, 0, 0))    # bent outward
                q = [p0 + Vector((0, -side * 0.03, 0)), p1 + Vector((0, -side * 0.03, 0)), p1 + Vector((0, -side * 0.03, 0.75)) + lean, p0 + Vector((0, -side * 0.03, 0.75)) + lean]
                (bulw if rnd.random() > 0.45 else bulw_r).append(plate_poly(q, 0.03))     # many panels rusted through the paint
                rail.append(tube([q[3] + Vector((0, 0, 0.03)), q[2] + Vector((0, 0, 0.03))], 0.035, sides=6))
            s = s1 + rnd.uniform(0.0, 0.012)
    put("Rubbing", merged(rub), C["rust2"], smooth=True)
    put("Bulwark", merged(bulw), C["black"])
    put("BulwarkRusty", merged(bulw_r), C["rust2"])
    put("BulwarkRail", merged(rail), C["rust"], smooth=True)

    # hatch coaming (+ cover lying aside), forward hatch closed
    s0, s1, hw = HATCH; x0, x1 = sx(s0), sx(s1); dz = deck_z((s0 + s1) / 2) + 0.1
    coam = [box((x1 - x0 + 0.2, 0.12, 0.55), ((x0 + x1) / 2, sd * (hw + 0.06), dz + 0.27)) for sd in (-1, 1)] + \
           [box((0.12, 2 * hw + 0.24, 0.55), (xx, 0, dz + 0.27)) for xx in (x0 - 0.06, x1 + 0.06)]
    put("HatchCoaming", merged(coam), C["rust"])
    put("HatchCover", box((x1 - x0 - 0.1, hw * 1.2, 0.1), (0, 0, 0), Matrix.Translation(((x0 + x1) / 2 + 0.2, -2.0, dz + 0.65)) @ RX(-28) @ RZ(8)), C["rust2"])
    fs = 0.76; put("ForeHatch", merged([box((1.4, 1.4, 0.45), (sx(fs), 0, deck_z(fs) + 0.3)), box((1.5, 1.5, 0.08), (sx(fs), 0, deck_z(fs) + 0.55))]), C["rust"])

    # hold: floor, bulkheads (inner shape), contents piled to port
    hs0, hs1 = HOLD; fl = []
    xa, xb = sx(hs0), sx(hs1)
    ya, yb = inner_y(hs0, FLOOR_Z), inner_y(hs1, FLOOR_Z)
    fl.append(box((xb - xa, 2 * min(ya, yb) - 0.05, 0.06), ((xa + xb) / 2, 0, FLOOR_Z - 0.03)))
    fl += [bulkhead(hs0, FLOOR_Z - 0.05, DOOR), bulkhead(hs1, FLOOR_Z - 0.05), bulkhead(CABIN[0], FLOOR_Z - 0.05)]
    ca, cb = sx(CABIN[0]), sx(CABIN[1]); yc = min(inner_y(CABIN[0], FLOOR_Z), inner_y(CABIN[1], FLOOR_Z))
    fl.append(box((cb - ca, 2 * yc - 0.05, 0.06), ((ca + cb) / 2, 0, FLOOR_Z - 0.03)))
    put("HoldStructure", merged(fl), C["inside"])
    put("DoorFrame", merged([box((0.1, 0.08, DOOR[2]), (xa + 0.02, y, FLOOR_Z + DOOR[2] / 2)) for y in (DOOR[0] - 0.04, DOOR[1] + 0.04)] +
                            [box((0.1, DOOR[1] - DOOR[0] + 0.16, 0.08), (xa + 0.02, 0, FLOOR_Z + DOOR[2] + 0.04))]), C["metal"])
    frames = []                                                      # hold frames (ribs) inside the hull
    for k in range(9):
        s = hs0 + (hs1 - hs0) * (k + 0.5) / 9
        if abs(s - HOLE[0]) < HOLE[2] * 1.1: continue
        pts = [hull_pt(s, th, True) for th in [-math.pi / 2 + math.pi * q / 20 for q in range(21)] if hull_pt(s, th, True).z > FLOOR_Z]
        frames.append(strap(pts, Vector((1, 0, 0)), 0.08, 0.1))
    put("HoldFrames", merged(frames), C["rust"])
    crates, barrels, bands, fishb = [], [], [], []
    for (x, y, z, sz, rz, ry) in ((-2.6, -1.6, 0, 0.9, 10, 0), (-2.5, -1.5, 0.9, 0.8, -15, 0), (-1.6, -1.8, 0, 1.0, 30, 0), (-0.9, -1.4, 0, 0.8, 5, 12),
                                  (1.4, -1.7, 0, 0.9, -20, 0), (1.9, -1.2, 0.85, 0.7, 40, 20), (0.6, -0.4, 0, 0.6, 70, 85)):
        crates.append(box((sz, sz * 0.9, sz * 0.8), (0, 0, sz * 0.4), Matrix.Translation((x, y, FLOOR_Z + z)) @ RZ(rz) @ RY(ry)))
    for k, (x, y, lying) in enumerate(((0.2, -2.0, False), (0.75, -2.05, False), (-0.2, -1.1, True), (2.4, -0.5, True), (0.4, 0.5, True))):
        M = Matrix.Translation((x, y, FLOOR_Z + (0.3 if lying else 0.45))) @ (RX(90) @ RZ(rnd.uniform(0, 180)) if lying else Matrix())
        barrels.append(cyl(0.3, 0.88, 18, (0, 0, 0), M)); bands += [torus(0.302, 0.02, 18, 4, M @ Matrix.Translation((0, 0, h))) for h in (-0.28, 0.28)]
    for k in range(12):
        x, y = rnd.uniform(-3.2, 2.4), rnd.uniform(-2.2, 1.6); z = FLOOR_Z + (0.15 * (k % 3) if k < 6 else 0)
        fishb.append(box((0.8, 0.5, 0.28), (0, 0, 0.14), Matrix.Translation((x, y, z)) @ RZ(rnd.uniform(0, 180)) @ RX(rnd.uniform(-8, 8))))
    put("HoldCrates", merged(crates), C["wood"])
    put("HoldBarrels", merged(barrels), C["barrel"], smooth=True)
    put("HoldBarrelBands", merged(bands), C["rust"], smooth=True)
    put("HoldFishBoxes", merged(fishb), C["fishbox"])
    # hold extras: shelving rack (starboard), rope coils, net bundles, ice boxes, hatch ladder, chain pile, planks, fish bones
    rack = []; rx0, rx1 = -3.3, -1.9; ry_ = inner_y(0.42, FLOOR_Z + 1.0) - 0.35
    for x in (rx0, rx1):
        for y in (ry_ - 0.25, ry_ + 0.25): rack.append(box((0.05, 0.05, 1.8), (x, y, FLOOR_Z + 0.9)))
    for z in (0.5, 1.1, 1.7): rack.append(box((rx1 - rx0 + 0.05, 0.55, 0.03), ((rx0 + rx1) / 2, ry_, FLOOR_Z + z)))
    put("HoldRack", merged(rack), C["metal"])
    put("HoldRackBoxes", merged([box((0.35, 0.4, 0.3), (0, 0, 0.15), Matrix.Translation((rx0 + 0.25 + 0.4 * (k % 3), ry_, FLOOR_Z + 0.52 + 0.6 * (k // 3))) @ RZ(rnd.uniform(-15, 15)))
                                 for k in range(6) if k != 4]), C["wood"])
    put("RopeCoils", merged([torus(0.28 - 0.04 * j, 0.035, 18, 6, Matrix.Translation((x, y, FLOOR_Z + 0.035 + 0.06 * j))) for x, y in ((0.9, 1.2), (-0.4, 1.6)) for j in range(4)]), C["net"], smooth=True)
    put("NetBundles", merged([rock(Vector((x, y, FLOOR_Z + 0.25)), (0.55, 0.4, 0.28), 300 + k, amp=0.45) for k, (x, y) in enumerate(((2.2, 1.0), (1.6, 1.7), (-2.6, 0.9)))]), C["net"], smooth=True)
    ib = [box((0.9, 0.6, 0.55), (x, y, FLOOR_Z + 0.275)) for x, y in ((1.0, -0.6), (2.3, -1.9))] + \
         [box((0.92, 0.62, 0.06), (0, 0, 0), Matrix.Translation((1.05, -0.35, FLOOR_Z + 0.62)) @ RX(-35))]
    put("IceBoxes", merged(ib), C["ceramic"])
    lx = sx(HATCH[1]) - 0.15
    put("HatchLadder", merged([box((0.05, 0.05, deck_z(0.5) - FLOOR_Z + 0.5), (lx, y, (deck_z(0.5) + FLOOR_Z) / 2 + 0.25)) for y in (-0.25, 0.25)] +
                              [box((0.04, 0.5, 0.04), (lx, 0, FLOOR_Z + 0.3 + 0.3 * k)) for k in range(9)]), C["metal"])
    links = []
    for k in range(40):
        a = k * 0.55; r_ = 0.15 + 0.012 * k; c_ = Vector((-0.2, 0.3, FLOOR_Z + 0.04 + 0.004 * k))
        links.append(torus(0.06, 0.016, 8, 4, Matrix.Translation(c_ + Vector((r_ * math.cos(a), r_ * math.sin(a), 0))) @ RZ(math.degrees(a)) @ RX(90 * (k % 2)) @ Matrix.Diagonal((0.7, 1, 1, 1))))
    put("ChainPile", merged(links), C["rust2"], smooth=True)
    put("Planks", merged([box((rnd.uniform(0.5, 1.0), 0.12, 0.025), (0, 0, 0), Matrix.Translation((rnd.uniform(-3, 2.5), rnd.uniform(-1.5, 1.6), FLOOR_Z + 0.02 + 0.03 * k)) @ RZ(rnd.uniform(0, 180)))
                          for k in range(10)]), C["wood"])
    put("FishBones", merged([fish_bones(Vector((rnd.uniform(-3, 2.5), rnd.uniform(-1.5, 1.5), FLOOR_Z)), rnd.uniform(0, 6.3), rnd.uniform(0.35, 0.6)) for _ in range(5)]), C["bone"], smooth=True)

    # ---- crew quarters (under the wheelhouse): bunks, lockers, mess table, galley, clutter
    ca, cb = sx(CABIN[0]), sx(CABIN[1]); F = FLOOR_Z
    bunk_f, matt = [], []
    for sd in (-1, 1):
        yo = sd * (inner_y(0.15, F + 1.3) - 0.45)
        for zz in (0.45, 1.4):
            bunk_f += [box((1.95, 0.8, 0.06), (ca + 1.2, yo, F + zz)), box((1.95, 0.05, 0.2), (ca + 1.2, yo - sd * 0.4, F + zz + 0.1))]
            m_ = rock(Vector(), (0.95, 0.38, 0.07), 400 + int(zz * 10) + sd, sub=2, amp=0.12)
            bmesh.ops.transform(m_, matrix=Matrix.Translation((ca + 1.2, yo, F + zz + 0.09)) @ RX(sd * rnd.uniform(-4, 4)), verts=m_.verts); matt.append(m_)
        bunk_f += [box((0.06, 0.06, 1.75), (x, yo - sd * 0.38, F + 0.87)) for x in (ca + 0.25, ca + 2.15)]
    put("Bunks", merged(bunk_f), C["metal"])
    put("Mattresses", merged(matt), C["mattress"], smooth=True)
    put("Pillows", merged([rock(Vector((ca + 0.45, sd * (inner_y(0.15, F + 1.3) - 0.45), F + 0.6 + 0.95 * k)), (0.2, 0.28, 0.07), 410 + k, sub=1, amp=0.2) for sd in (-1, 1) for k in range(2)]), C["ceramic"], smooth=True)
    put("Curtain", merged([strap([Vector((ca + 0.4 + 0.3 * k, 0.95, F + 1.95)), Vector((ca + 0.45 + 0.3 * k, 0.97, F + 1.5)), Vector((ca + 0.5 + 0.3 * k, 1.0, F + 1.1 - 0.2 * (k % 2)))],
                                 Vector((1, 0, 0)), 0.28, 0.01) for k in range(4)]), C["fabric"], smooth=True)
    ly = inner_y(0.29, F + 1.0) - 0.35
    put("Lockers", merged([box((0.52, 0.5, 1.8), (cb - 0.45 - 0.55 * k, ly, F + 0.9)) for k in range(4)]), C["metal"])
    put("LockerDoors", merged([box((0.48, 0.03, 1.7), (cb - 0.45 - 0.55 * k, ly - 0.26, F + 0.9)) for k in (0, 2, 3)] +
                              [box((0.48, 0.03, 1.7), (0, 0, 0), Matrix.Translation((cb - 1.0 - 0.24, ly - 0.26, F + 0.9)) @ RZ(-100) @ Matrix.Translation((0.24, 0, 0)))]), C["rust2"])
    put("LockerClothes", merged([rock(Vector((cb - 1.0, ly - 0.05, F + 1.3)), (0.2, 0.12, 0.35), 420, amp=0.3), rock(Vector((cb - 1.1, ly - 0.45, F + 0.12)), (0.3, 0.25, 0.1), 421, amp=0.4)]), C["fabric"], smooth=True)
    mx, my = ca + 3.35, 0.7
    put("MessTable", merged([box((1.2, 0.75, 0.05), (mx, my, F + 0.74)), cyl(0.05, 0.72, 10, (mx, my, F + 0.36))]), C["wood"], smooth=True)
    put("MessBenches", merged([box((1.2, 0.35, 0.06), (mx, my + 0.6, F + 0.44)), box((1.2, 0.06, 0.4), (mx, my + 0.8, F + 0.22)),
                               box((0.9, 0.35, 0.06), (0, 0, 0), Matrix.Translation((mx + 0.1, my - 0.75, F + 0.2)) @ RX(70))]), C["wood"])          # one bench toppled
    tw = [lathe([(0.0, 0.0), (0.12, 0.0), (0.13, 0.02), (0.0, 0.015)], 16, Matrix.Translation((mx - 0.3 + 0.3 * k, my + 0.1 * (k % 2), F + 0.77))) for k in range(3)]
    tw += [lathe([(0.0, 0.0), (0.12, 0.0), (0.13, 0.02), (0.0, 0.015)], 16, Matrix.Translation((mx + 0.4, my - 1.1, F + 0.01)) @ RX(8))]
    put("Plates", merged(tw), C["ceramic"], smooth=True)
    put("Bottles", merged([lathe([(0.0, 0.0), (0.04, 0.0), (0.04, 0.2), (0.014, 0.25), (0.014, 0.3), (0.0, 0.3)], 10, Matrix.Translation(p) @ RX(r) @ RZ(z)) for p, r, z in
                           ((Vector((mx + 0.3, my + 0.2, F + 0.77)), 0, 0), (Vector((mx - 0.6, my - 1.0, F + 0.04)), 90, 40), (Vector((ca + 2.4, -0.2, F + 0.04)), 90, -70),
                            (Vector((ca + 2.6, 0.1, F + 0.04)), 90, 10))]), C["bottle"], smooth=True)
    gx0 = cb - 1.6; gy = -(inner_y(0.3, F + 0.9) - 0.4)
    put("Galley", merged([box((1.6, 0.6, 0.9), (gx0 + 0.6, gy, F + 0.45)), box((1.6, 0.35, 0.6), (gx0 + 0.6, gy - 0.12, F + 1.75))]), C["white"])
    put("Stove", merged([box((0.6, 0.55, 0.05), (gx0 + 0.25, gy, F + 0.93))] + [torus(0.08, 0.012, 14, 4, Matrix.Translation((gx0 + 0.12 + 0.26 * (k % 2), gy - 0.12 + 0.24 * (k // 2), F + 0.96))) for k in range(4)] +
                        [box((0.03, 0.3, 0.03), (gx0 - 0.08, gy + 0.05 * k, F + 0.6)) for k in range(-1, 2)]), C["rust2"], smooth=True)
    put("Sink", box((0.45, 0.4, 0.04), (gx0 + 0.95, gy, F + 0.91)), C["metal"])
    put("CupboardDoor", box((0.4, 0.03, 0.55), (0, 0, 0), Matrix.Translation((gx0 + 0.5, gy + 0.08, F + 1.48)) @ RX(-60) @ Matrix.Translation((0, 0, -0.27))), C["white"])
    put("Pots", merged([lathe([(0.0, 0.0), (0.14, 0.0), (0.14, 0.16), (0.13, 0.16), (0.13, 0.01), (0.0, 0.01)], 16, Matrix.Translation(p) @ RX(r)) for p, r in
                        ((Vector((gx0 + 0.15, gy, F + 0.96)), 0), (Vector((gx0 - 0.2, gy + 0.6, F + 0.14)), 95))] +
                       [cyl(0.012, 0.25, 6, (0, 0, 0), Matrix.Translation((gx0 - 0.05, gy + 0.6, F + 0.14)) @ RY(90))]), C["metal"], smooth=True)
    cans = [cyl(0.04, 0.11, 10, (ca + 0.2 + 0.1 * (k % 6), -0.6 + 0.12 * (k // 6), F + 1.55 + 0.055)) for k in range(14) if rnd.random() > 0.2]
    cans += [cyl(0.04, 0.11, 10, (0, 0, 0), Matrix.Translation((ca + rnd.uniform(0.4, 2.0), rnd.uniform(-0.8, 0.5), F + 0.04)) @ RX(90) @ RZ(rnd.uniform(0, 180))) for _ in range(6)]
    put("Cans", merged(cans), C["metal"], smooth=True)
    put("CanShelf", box((0.75, 0.3, 0.03), (ca + 0.45, -0.3, F + 1.53)), C["wood"])
    put("Boots", merged([rock(Vector((ca + 2.8 + 0.25 * k, -0.9 + 0.2 * k, F + 0.12)), (0.14, 0.06, 0.12), 430 + k, sub=1, amp=0.2) for k in range(2)]), C["fabric"], smooth=True)
    put("ClothesPiles", merged([rock(Vector((x, y, F + 0.06)), (0.35, 0.25, 0.08), 440 + k, amp=0.45) for k, (x, y) in enumerate(((ca + 1.6, 0.1), (ca + 3.9, -0.6), (cb - 0.6, -0.3)))]), C["fabric"], smooth=True)
    put("CabinLamps", merged([lamp(Vector((ca + 1.5, 0.0, deck_z(0.15) - 0.05)), 0.35), lamp(Vector((ca + 3.6, 0.3, deck_z(0.28) - 0.05)), 0.5)]), C["metal"], smooth=True)

    # wheelhouse (aft), with window openings, doorway, interior fittings
    wa, wb = sx(0.14), sx(0.26); wz = deck_z(0.2) + 0.08; H = 2.3; hw2 = 1.8; t = 0.06
    win_front = [(-1.45, -0.6, wz + 1.15, wz + 1.95), (-0.45, 0.45, wz + 1.15, wz + 1.95), (0.6, 1.45, wz + 1.15, wz + 1.95)]
    walls = wall("x", wb, -hw2, hw2, wz, wz + H, t, win_front)
    walls += wall("x", wa, -hw2, hw2, wz, wz + H, t, [(-0.4, 0.4, wz + 1.2, wz + 1.8)])
    walls += wall("y", hw2, wa, wb, wz, wz + H, t, [(wa + 0.4, wa + 1.25, wz, wz + 1.95), (wb - 1.3, wb - 0.5, wz + 1.15, wz + 1.85)])   # starboard: doorway + window
    walls += wall("y", -hw2, wa, wb, wz, wz + H, t, [(wa + 0.5, wa + 1.2, wz + 1.15, wz + 1.85), (wb - 1.3, wb - 0.5, wz + 1.15, wz + 1.85)])
    put("Wheelhouse", merged(walls), C["white"])
    put("WheelhouseRoof", merged([box((wb - wa + 0.5, 2 * hw2 + 0.4, 0.1), ((wa + wb) / 2 + 0.1, 0, wz + H + 0.05))] +
                                 [box((wb - wa + 0.5, 0.06, 0.15), ((wa + wb) / 2 + 0.1, sd * (hw2 + 0.2), wz + H + 0.17)) for sd in (-1, 1)]), C["white"])
    put("WheelhouseTrim", merged([box((0.08, 2 * hw2, 0.12), (wb + 0.02, 0, wz + 1.1)), box((wb - wa, 0.08, 0.12), ((wa + wb) / 2, hw2 + 0.02, wz + 1.1)),
                                  box((wb - wa, 0.08, 0.12), ((wa + wb) / 2, -hw2 - 0.02, wz + 1.1))]), C["rust"])
    shards = []
    for (b0, b1, h0, h1) in win_front[:1]:     # one front window still has glass fragments
        shards.append(plate_poly([Vector((wb, b0, h0)), Vector((wb, b1, h0)), Vector((wb, b1 - 0.25, h0 + 0.45)), Vector((wb, b0 + 0.1, h0 + 0.3))], 0.01))
    put("WindowGlass", merged(shards), C["glass"])
    cons = [box((0.6, 2 * hw2 - 0.3, 0.95), (wb - 0.35, 0, wz + 0.47)), box((0.5, 2 * hw2 - 0.3, 0.06), (0, 0, 0), Matrix.Translation((wb - 0.4, 0, wz + 1.0)) @ RY(-15))]
    put("Console", merged(cons), C["metal"])
    wheel_p = Matrix.Translation((wb - 0.75, 0.0, wz + 1.15)) @ RY(90)
    put("ShipsWheel", merged([torus(0.32, 0.025, 24, 6, wheel_p), cyl(0.05, 0.12, 10, (0, 0, 0), wheel_p)] +
                             [cyl(0.015, 0.8, 6, (0, 0, 0), wheel_p @ RZ(a) @ RX(90)) for a in (0, 45, 90, 135)] +
                             [cyl(0.05, 0.4, 8, (0, 0, 0), Matrix.Translation((wb - 0.55, 0, wz + 1.15)) @ RY(90))]), C["wood"], smooth=True)
    put("Chair", xf(merged([box((0.45, 0.45, 0.08), (0, 0, 0.0)), box((0.08, 0.45, 0.5), (-0.2, 0, 0.25)), cyl(0.03, 0.5, 8, (0, 0, -0.25))]),
                    Matrix.Translation((wa + 1.3, -0.9, wz + 0.25)) @ RX(85) @ RZ(30)), C["wood"])     # toppled
    put("ChartTable", merged([box((0.9, 0.7, 0.05), (wa + 1.75, -1.35, wz + 0.95)), box((0.85, 0.65, 0.9), (wa + 1.75, -1.35, wz + 0.47))]), C["wood"])
    put("Charts", merged([box((0.6, 0.45, 0.004), (0, 0, 0), Matrix.Translation((wa + 1.7 + 0.1 * k, -1.35, wz + 0.98 + 0.004 * k)) @ RZ(10 * k)) for k in range(3)]), C["primer"])
    # navigation gear on the console: radar, radio, binnacle, throttles, overhead panel
    rad = Matrix.Translation((wb - 0.35, -1.1, wz + 1.15)) @ RY(-25)
    put("Radar", merged([box((0.45, 0.5, 0.35), (wb - 0.35, -1.1, wz + 1.15)), cyl(0.17, 0.03, 20, (0, 0, 0), rad @ Matrix.Translation((0, 0, 0.2)))]), C["metal"], smooth=True)
    put("RadarScreen", cyl(0.15, 0.01, 20, (0, 0, 0), rad @ Matrix.Translation((0, 0, 0.22))), C["screen"])
    put("Radio", merged([box((0.3, 0.42, 0.26), (wb - 0.35, 1.15, wz + 1.15))] + [cyl(0.025, 0.04, 8, (0, 0, 0), Matrix.Translation((wb - 0.51, 1.0 + 0.1 * k, wz + 1.1)) @ RY(90)) for k in range(4)]), C["metal"], smooth=True)
    put("Binnacle", lathe([(0.0, 0.0), (0.14, 0.0), (0.12, 0.08), (0.13, 0.12), (0.0, 0.26)], 18, Matrix.Translation((wb - 0.35, 0.35, wz + 1.03))), C["brass"], smooth=True)
    put("Throttles", merged([cyl(0.012, 0.22, 6, (0, 0, 0), Matrix.Translation((wb - 0.4, 0.65 + 0.08 * k, wz + 1.15)) @ RY(-20 - 15 * k)) for k in range(2)] +
                            [lathe([(0.0, -0.03), (0.03, 0.0), (0.0, 0.03)], 10, Matrix.Translation((wb - 0.44 + 0.03 * k, 0.65 + 0.08 * k, wz + 1.25))) for k in range(2)]), C["rust2"], smooth=True)
    put("OverheadPanel", merged([box((0.35, 1.6, 0.12), (wb - 0.25, 0, wz + H - 0.12))] + [box((0.03, 0.04, 0.03), (wb - 0.25 + 0.1 * (k % 3 - 1), -0.6 + 0.15 * (k // 3), wz + H - 0.19)) for k in range(18)]), C["metal"])
    # settee on the aft wall, shelves with books, life jackets, clock, fallen lamp, floor clutter
    put("Settee", merged([box((0.5, 1.5, 0.42), (wa + 0.3, 0.15, wz + 0.21)), box((0.12, 1.5, 0.55), (wa + 0.1, 0.15, wz + 0.7))]), C["wood"])
    put("SetteeCushion", merged([box((0.46, 1.4, 0.1), (0, 0, 0), Matrix.Translation((wa + 0.32, 0.15, wz + 0.47)) @ RX(3)), box((0.4, 0.5, 0.08), (0, 0, 0), Matrix.Translation((wa + 0.6, 0.5, wz + 0.04)) @ RZ(25))]), C["fabric"], smooth=True)
    books = []
    for k in range(2):
        books.append(box((0.9, 0.22, 0.025), (wa + 1.75, -hw2 + 0.13, wz + 1.45 + 0.35 * k)))
        for j in range(9):
            if rnd.random() < 0.25: continue
            h = rnd.uniform(0.18, 0.28); books.append(box((0.05, 0.16, h), (0, 0, h / 2), Matrix.Translation((wa + 1.37 + 0.09 * j, -hw2 + 0.13, wz + 1.47 + 0.35 * k)) @ RY(rnd.uniform(-12, 12))))
    put("ShelvesBooks", merged(books), C["wood"])
    put("LifeJackets", merged([box((0.35, 0.1, 0.5), (0, 0, 0), Matrix.Translation((wa + 0.08, -0.95 + 0.45 * k, wz + 1.55)) @ RX(5 * k)) for k in range(2)]), C["float"])
    put("Clock", cyl(0.13, 0.04, 20, (0, 0, 0), Matrix.Translation((wa + 0.05, 1.3, wz + 1.75)) @ RY(90)), C["ceramic"], smooth=True)
    put("ClockRim", torus(0.13, 0.015, 20, 5, Matrix.Translation((wa + 0.07, 1.3, wz + 1.75)) @ RY(90)), C["brass"], smooth=True)
    put("FallenLamp", merged([lathe([(0.0, 0.0), (0.16, -0.12), (0.17, -0.14), (0.0, -0.05)], 14, Matrix.Translation((wa + 1.0, 0.5, wz + 0.12)) @ RX(100)),
                              tube([Vector((wa + 1.0, 0.5, wz + 0.1)), Vector((wa + 1.2, 0.2, wz + 0.02)), Vector((wa + 1.5, 0.0, wz + H))], 0.006, sides=4)]), C["metal"], smooth=True)
    clutter = [box((0.21, 0.297, 0.003), (0, 0, 0), Matrix.Translation((rnd.uniform(wa + 1.1, wb - 0.8), rnd.uniform(-1.2, 1.4), wz + 0.006 + 0.002 * k)) @ RZ(rnd.uniform(0, 180))) for k in range(9)]
    put("Papers", merged(clutter), C["primer"])
    put("Mugs", merged([lathe([(0.0, 0.0), (0.045, 0.0), (0.045, 0.1), (0.04, 0.1), (0.04, 0.01), (0.0, 0.01)], 12, Matrix.Translation(p) @ RX(r)) for p, r in
                        ((Vector((wb - 0.5, -0.6, wz + 1.12)), 0), (Vector((wa + 1.6, 0.9, wz + 0.05)), 90))]), C["ceramic"], smooth=True)
    bino = Matrix.Translation((wa + 2.0, -1.2, wz + 1.0)) @ RZ(30) @ RY(90)
    put("Binoculars", merged([cyl(0.04, 0.17, 10, (0, sd * 0.045, 0), bino) for sd in (-1, 1)]), C["rust2"], smooth=True)
    # stairs down to the crew quarters (from the stair hole in the wheelhouse floor)
    xs0, xs1 = sx(STAIR[0]) + 0.05, sx(STAIR[0]) + 1.45; ys = (STAIR[2] + STAIR[3]) / 2; ztop = deck_top(sx(STAIR[0]), ys)
    steps = [box((0.24, 0.62, 0.04), ((xs0 + (xs1 - xs0) * k / 9), ys, ztop - (ztop - FLOOR_Z) * k / 9 - 0.12)) for k in range(1, 10)]
    steps += [strap([Vector((xs0, ys + sd * 0.33, ztop)), Vector((xs1 + 0.1, ys + sd * 0.33, FLOOR_Z))], Vector((0, 1, 0)), 0.04, 0.2) for sd in (-1, 1)]
    steps.append(tube([Vector((xs0, ys + 0.38, ztop + 0.9)), Vector((xs1, ys + 0.38, FLOOR_Z + 0.9))], 0.02, sides=6))
    steps += [box((sx(STAIR[1]) - sx(STAIR[0]), 0.05, 0.6), ((sx(STAIR[0]) + sx(STAIR[1])) / 2, STAIR[3] + 0.03, ztop + 0.3))]   # guard rail on the wheelhouse floor
    put("Stairs", merged(steps), C["metal"])
    put("Funnel", merged([lathe([(0.0, 0.0), (0.42, 0.0), (0.38, 1.9), (0.0, 1.9)], 20, Matrix.Translation((wa - 0.6, 0.6, wz)) @ RY(-8)),
                          lathe([(0.39, 1.5), (0.41, 1.5), (0.4, 1.9), (0.38, 1.9)], 20, Matrix.Translation((wa - 0.6, 0.6, wz)) @ RY(-8))]), C["black"], smooth=True)

    # A-frame gantry, winch drums, nets with floats over the stern
    sg = 0.03; zg = deck_z(sg)
    legs = [tube([Vector((sx(sg), sd * 2.3, zg)), Vector((sx(sg) - 0.4, sd * 1.9, zg + 4.2))], 0.12, sides=10) for sd in (-1, 1)]
    legs.append(tube([Vector((sx(sg) - 0.4, -1.95, zg + 4.2)), Vector((sx(sg) - 0.4, 1.95, zg + 4.2))], 0.12, sides=10))
    put("Gantry", merged(legs), C["rust"], smooth=True)
    blk = Matrix.Translation((sx(sg) - 0.4, 0.5, zg + 3.6))
    put("GantryBlock", merged([cyl(0.25, 0.12, 16, (0, 0, 0), blk @ RX(90)), box((0.12, 0.2, 0.6), (0, 0, 0.3), blk)]), C["metal"], smooth=True)
    put("Cable", tube(catmull([Vector((sx(sg) - 0.4, 0.5, zg + 3.35)), Vector((sx(sg) - 0.6, 0.6, zg + 1.5)), Vector((sx(sg) - 0.9, 0.9, 0.0))], 6), 0.02, sides=6), C["metal"], smooth=True)
    sw = 0.1; zw = deck_z(sw)
    put("Winches", merged([cyl(0.35, 0.8, 18, (0, 0, 0), Matrix.Translation((sx(sw), sd * 1.0, zw + 0.55)) @ RX(90)) for sd in (-1, 1)] +
                          [box((0.4, 2.6, 0.3), (sx(sw), 0, zw + 0.15))]), C["metal"], smooth=True)
    net, floats = [], []
    for k in range(5):
        pts = [Vector((sx(0.06) + rnd.uniform(-0.3, 0.3), -1.6 + 0.8 * k + rnd.uniform(-0.2, 0.2), deck_z(0.06) + 0.25)),
               Vector((sx(0.0) - 0.3, -1.4 + 0.7 * k, deck_z(0.0) - 0.4)), Vector((sx(0.0) - 0.6, -1.2 + 0.6 * k, 1.2)), Vector((sx(0.0) - 1.2, -1.0 + 0.5 * k, 0.4))]
        net.append(strap(catmull(pts, 8), Vector((0, 1, 0)), lambda q: 0.9 - 0.3 * q, 0.12))
        for q in catmull(pts, 3)[::2]: floats.append(lathe([(0.0, -0.12), (0.12, -0.08), (0.13, 0.0), (0.12, 0.08), (0.0, 0.12)], 12, Matrix.Translation(q + Vector((0, 0.3, 0.1)))))
    for k in range(6):
        net.append(rock(Vector((sx(0.07) + rnd.uniform(-0.6, 0.6), rnd.uniform(-1.5, 1.5), deck_z(0.07) + 0.2)), (0.6, 0.45, 0.25), 60 + k, sub=2, amp=0.4))
    put("Nets", merged(net), C["net"], smooth=True)
    put("NetFloats", merged(floats), C["float"], smooth=True)

    # mast snapped near the base, top lying across the deck and over the port side
    ms = 0.33; mz = deck_z(ms); mb = Vector((sx(ms), 0, mz))
    put("MastStump", merged([cyl(0.14, 1.1, 14, (sx(ms), 0, mz + 0.55)), cyl(0.2, 0.1, 14, (sx(ms), 0, mz + 0.05))]), C["rust"], smooth=True)
    top = [mb + Vector((0.3, -0.2, 1.1)), mb + Vector((2.0, -2.6, 1.0)), mb + Vector((4.0, -4.8, -0.6)), mb + Vector((5.6, -6.6, -2.8))]
    put("MastFallen", merged([tube(top, lambda q: 0.13 - 0.04 * q, sides=12),
                              tube([top[1] + Vector((0.6, 0.5, 0.05)), top[1] + Vector((-0.6, -0.5, 0.05))], 0.05, sides=6)]), C["rust"], smooth=True)

    # bow: windlass, anchor in the hawse, chain to the seabed (built in ship frame down to below the seabed)
    bw = 0.86; zb = deck_z(bw)
    put("Windlass", merged([box((0.6, 1.2, 0.4), (sx(bw), 0, zb + 0.2)), cyl(0.22, 1.5, 16, (0, 0, 0), Matrix.Translation((sx(bw), 0, zb + 0.5)) @ RX(90))]), C["metal"], smooth=True)
    ah = hull_pt(0.93, 1.1) + Vector((0, 0.1, 0))
    put("Anchor", merged([box((0.12, 0.12, 1.2), (0, 0, -0.6), Matrix.Translation(ah) @ RX(15)),
                          box((0.9, 0.12, 0.12), (0, 0, 0), Matrix.Translation(ah + Vector((0, 0.15, -1.2))) @ RX(15)),
                          box((0.15, 0.1, 0.4), (0, 0, 0), Matrix.Translation(ah + Vector((0.42, 0.15, -1.05))) @ RX(15) @ RY(25)),
                          box((0.15, 0.1, 0.4), (0, 0, 0), Matrix.Translation(ah + Vector((-0.42, 0.15, -1.05))) @ RX(15) @ RY(-25))]), C["rust2"])
    links = []
    chain = catmull([hull_pt(0.9, 1.35) + Vector((0, 0.2, 0)), hull_pt(0.92, 1.0) + Vector((0.6, 0.9, -1.0)), Vector((sx(0.95) + 1.5, 4.0, -0.6)), Vector((sx(0.95) + 3.5, 4.6, -1.3))], 14)
    for k in range(len(chain) - 1):
        d = (chain[k + 1] - chain[k]); M = Matrix.Translation(chain[k]) @ d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4() @ RZ(90 * (k % 2))
        links.append(torus(0.09, 0.025, 10, 5, M @ Matrix.Diagonal((0.7, 1.0, 1.0, 1.0))))
    put("AnchorChain", merged(links), C["rust2"], smooth=True)

    # stern: rudder + propeller, bilge keels, portholes
    st = sx(0.0)
    put("Rudder", plate_poly([Vector((st - 0.2, 0, 0.55)), Vector((st - 1.2, 0, 0.55)), Vector((st - 1.25, 0, 2.2)), Vector((st - 0.2, 0, 2.3))], 0.08), C["anti"])
    hub = Matrix.Translation((st + 0.15, 0, 1.25)) @ RY(90)
    prop = [cyl(0.18, 0.4, 14, (0, 0, 0), hub)]
    for k in range(4):
        b = plate_poly([Vector((0.15, -0.12, 0)), Vector((0.95, -0.25, 0)), Vector((1.0, 0.1, 0)), Vector((0.15, 0.1, 0))], 0.03)
        bmesh.ops.transform(b, matrix=hub @ RZ(90 * k + 20) @ RX(25), verts=b.verts); prop.append(b)
    put("Propeller", merged(prop), C["rust2"], smooth=True)
    put("BilgeKeels", merged([strap([hull_pt(s, sd * 0.55) for s in [0.3 + 0.3 * k / 20 for k in range(21)]], Vector((0, 0, 1)), 0.05, 0.35) for sd in (-1, 1)]), C["anti"])
    rings, glass = [], []
    for sd in (-1, 1):
        for k in range(14):
            s = 0.18 + 0.045 * k
            if sd > 0 and abs(s - HOLE[0]) < HOLE[2] * 1.6: continue
            th = sd * 1.35; p = hull_pt(s, th); n = hull_n(s, th); M = Matrix.Translation(p + n * 0.01) @ n.to_track_quat("Z", "Y").to_matrix().to_4x4()
            rings.append(torus(0.19, 0.035, 18, 6, M)); (glass if rnd.random() < 0.6 else []).append(cyl(0.17, 0.02, 16, (0, 0, -0.02), M))
    put("Portholes", merged(rings), C["metal"], smooth=True)
    put("PortholeGlass", merged(glass), C["hole"])

    # growth: anemones on rails / roof / gantry, sponges on the hull, rusticles hanging from edges
    an_w, an_o, spon, rust = [], [], [], []
    def anemone(p, sc, tgt):
        b = cyl(0.04 * sc, 0.08 * sc, 8, (p.x, p.y, p.z + 0.04 * sc))
        for k in range(10):
            fr = bmesh.new(); bmesh.ops.create_cone(fr, cap_ends=True, segments=4, radius1=0.012 * sc, radius2=0.002, depth=0.09 * sc)
            bmesh.ops.transform(fr, matrix=Matrix.Translation(p + Vector((0, 0, 0.08 * sc))) @ RZ(36 * k) @ RX(55) @ Matrix.Translation((0, 0, 0.045 * sc)), verts=fr.verts)
            me = bpy.data.meshes.new("_t"); fr.to_mesh(me); fr.free(); b.from_mesh(me); bpy.data.meshes.remove(me)
        tgt.append(b)
    for k in range(70):
        s = rnd.uniform(0.06, 0.92); sd = rnd.choice((-1, 1)); p = hull_pt(s, sd * math.pi / 2) + Vector((0, -sd * 0.03, 0.8))
        anemone(p, rnd.uniform(0.5, 1.0), an_w if k % 3 else an_o)
    for k in range(18):
        p = Vector((rnd.uniform(wa, wb + 0.2), rnd.uniform(-hw2, hw2), wz + H + 0.1)); anemone(p, rnd.uniform(0.6, 1.1), an_o if k % 2 else an_w)
    for k in range(26):
        s = rnd.uniform(0.1, 0.85); th = rnd.uniform(0.9, 1.45) * rnd.choice((-1, 1)); p = hull_pt(s, th)
        spon.append(rock(p + hull_n(s, th) * 0.05, (rnd.uniform(0.1, 0.25),) * 2 + (0.08,), 90 + k, sub=1, amp=0.4))
    def rusticle(p, ln):
        b = bmesh.new(); bmesh.ops.create_cone(b, cap_ends=True, segments=6, radius1=0.004, radius2=0.04 * ln ** 0.5, depth=ln)
        bmesh.ops.translate(b, vec=p + Vector((0, 0, -ln / 2)), verts=b.verts); return b
    for k in range(90):
        s = rnd.uniform(0.05, 0.92); sd = rnd.choice((-1, 1)); p = hull_pt(s, sd * math.pi / 2) + Vector((0, sd * 0.08, -0.2))
        rust.append(rusticle(p, rnd.uniform(0.1, 0.45)))
    for k in range(25):
        p = Vector((rnd.uniform(wa - 0.2, wb + 0.3), rnd.choice((-1, 1)) * (hw2 + 0.2), wz + H)); rust.append(rusticle(p, rnd.uniform(0.1, 0.35)))
    for k in range(20):   # around the torn hole
        a = rnd.uniform(0, math.tau); s = HOLE[0] + HOLE[2] * 1.05 * math.cos(a); th = HOLE[1] + HOLE[3] * 1.05 * math.sin(a)
        rust.append(rusticle(hull_pt(s, th) + hull_n(s, th) * 0.02, rnd.uniform(0.08, 0.3)))
    put("AnemonesWhite", merged(an_w), C["anem_w"], smooth=True)
    put("AnemonesOrange", merged(an_o), C["anem_o"], smooth=True)
    put("Sponges", merged(spon), C["sponge"], smooth=True)
    put("Rusticles", merged(rust), C["rust"], smooth=True)
    # rust streaks running down the topsides
    streaks = []
    for k in range(34):
        s = rnd.uniform(0.08, 0.9); sd = rnd.choice((-1, 1)); w = rnd.uniform(0.03, 0.09); ln = rnd.uniform(0.6, 1.8)
        a0 = sd * math.pi / 2; pts = []
        for q in range(7):
            th = a0 - sd * (ln / 3.4) * q / 6
            pts.append(hull_pt(s, th) + hull_n(s, th) * 0.008)
        streaks.append(strap(pts, hull_n(s, a0 - sd * 0.2), lambda q: w * (1 - 0.6 * q), 0.004))
    put("RustStreaks", merged(streaks), C["rust"])
    # plate seams: longitudinal strakes (constant theta) and vertical butts (constant s), skipped around the hole
    seams = []
    for sd in (-1, 1):
        for th in (0.35, 0.7, 1.08, 1.3):
            run = []
            for k in range(121):
                s = 0.01 + 0.98 * k / 120
                if sd > 0 and in_hole(s, th * sd) or abs(th - 0.95) < 0.07:
                    if len(run) > 1: seams.append(strap(run, hull_n(0.5, sd * th), 0.025, 0.012))
                    run = []; continue
                run.append(hull_pt(s, sd * th) + hull_n(s, sd * th) * 0.006)
            if len(run) > 1: seams.append(strap(run, hull_n(0.5, sd * th), 0.025, 0.012))
        for k in range(1, 16):
            s = k / 16; run = []
            for q in range(31):
                th = sd * (0.05 + 1.5 * q / 30)
                if in_hole(s, th):
                    if len(run) > 1: seams.append(strap(run, Vector((1, 0, 0)), 0.025, 0.012))
                    run = []; continue
                run.append(hull_pt(s, th) + hull_n(s, th) * 0.006)
            if len(run) > 1: seams.append(strap(run, Vector((1, 0, 0)), 0.025, 0.012))
    put("PlateSeams", merged(seams), C["rust2"])
    # rusty torn rim around the hole (jagged outer edge), covers the stretched faces at the cut
    rim = bmesh.new(); NA_ = 72; rows = []
    for r in range(4):
        row = []
        for q in range(NA_):
            ph = q / NA_ * math.tau; a_, b_ = math.cos(ph), math.sin(ph)
            s1, t1 = HOLE[0] + HOLE[2] * a_, HOLE[1] + HOLE[3] * b_
            k0 = math.sqrt(max(0.3, 1.0 + 0.35 * nz((s1 * 30, t1 * 6, 2.0), 1.0)))            # follow the torn cut
            rr = k0 * 0.99 + (0.1 + 0.22 * abs(nz((a_ * 3, b_ * 3, 7.0), 2.5)) + 0.08 * abs(nz((a_ * 9, b_ * 9, 8.0), 3.0))) * r / 3
            ss, tt = HOLE[0] + HOLE[2] * a_ * rr, HOLE[1] + HOLE[3] * b_ * rr
            row.append(rim.verts.new(hull_pt(ss, tt) + hull_n(ss, tt) * 0.014))
        rows.append(row)
    for r in range(3):
        for q in range(NA_):
            rim.faces.new((rows[r][q], rows[r + 1][q], rows[r + 1][(q + 1) % NA_], rows[r][(q + 1) % NA_]))
    bmesh.ops.solidify(rim, geom=rim.faces[:], thickness=0.012)
    put("HoleRim", rim, C["rust2"])
    # rust blooms + peeled primer on the hull (stay clear of the hole), barnacle crust low on the hull
    blooms, blooms2, primer = [], [], []
    for k in range(48):
        sc = rnd.uniform(0.03, 0.97); thc = rnd.choice((-1, 1)) * rnd.uniform(0.25, 1.5)
        if abs(sc - HOLE[0]) < HOLE[2] * 2.2 and abs(thc - HOLE[1]) < HOLE[3] * 2.2: continue
        b = hull_decal(sc, thc, rnd.uniform(0.008, 0.045), rnd.uniform(0.06, 0.28), 500 + k, 0.016 + 0.0004 * (k % 5))
        (blooms if k % 3 else blooms2).append(b)
    for k in range(16):
        sc = rnd.uniform(0.08, 0.9); thc = rnd.choice((-1, 1)) * rnd.uniform(1.05, 1.45)
        if abs(sc - HOLE[0]) < HOLE[2] * 2.2 and abs(thc - HOLE[1]) < HOLE[3] * 2.2: continue
        primer.append(hull_decal(sc, thc, rnd.uniform(0.006, 0.02), rnd.uniform(0.04, 0.12), 600 + k, 0.013))
    put("RustBlooms", merged(blooms), C["rust"], smooth=True)
    put("RustBloomsDark", merged(blooms2), C["rust2"], smooth=True)
    put("PeeledPrimer", merged(primer), C["primer"], smooth=True)
    barn = []
    for k in range(750):
        sc = rnd.uniform(0.02, 0.98); th = rnd.choice((-1, 1)) * (rnd.uniform(0.15, 1.05) if k < 600 else rnd.uniform(1.1, 1.5))
        if in_hole(sc, th): continue
        p = hull_pt(sc, th); n = hull_n(sc, th); h = rnd.uniform(0.015, 0.04)
        b = bmesh.new(); bmesh.ops.create_cone(b, cap_ends=True, segments=6, radius1=h * 1.1, radius2=h * 0.35, depth=h)
        bmesh.ops.transform(b, matrix=Matrix.Translation(p + n * (h / 2)) @ n.to_track_quat("Z", "Y").to_matrix().to_4x4(), verts=b.verts); barn.append(b)
    put("Barnacles", merged(barn), C["barnacle"])
    # decks: silt piles (thicker toward the low port side) and rust patches; rusted-through hole rims
    silt, drust = [], []
    def clear(x, y, r):
        s_ = x / L + 0.5
        if HATCH[0] - 0.03 < s_ < HATCH[1] + 0.03 and abs(y) < HATCH[2] + r: return False
        if 0.12 < s_ < 0.28: return False                       # wheelhouse / stair area
        return all(math.hypot(x - sx(hs), y - hy) > hr + r + 0.1 for hs, hy, hr in DECK_HOLES)
    for k in range(60):
        x = sx(rnd.uniform(0.04, 0.9)); y = rnd.uniform(-1, 1) * (beam(x / L + 0.5) - 0.6); r = rnd.uniform(0.3, 0.9)
        if not clear(x, y, r): continue
        if k % 2: silt.append(slab(blot(x, y, r, 700 + k, lambda a, b: deck_top(a, b) + 0.02 + 0.03 * max(0.0, -b / 3)), 0.06))
        else: drust.append(slab(blot(x, y, r * 0.8, 700 + k, lambda a, b: deck_top(a, b) + 0.008), 0.02))
    put("DeckSilt", merged(silt), C["silt"], smooth=True)
    put("DeckRust", merged(drust), C["rust"])
    rims = []
    for hs, hy, hr in DECK_HOLES:
        cx = sx(hs); pts_o = blot(cx, hy, hr * 1.55, 800 + int(hs * 100), lambda a, b: deck_top(a, b) + 0.01, segs=24, sy=1.0)
        for q in range(24):
            ph, ph2 = q / 24 * math.tau, (q + 1) / 24 * math.tau
            p1 = Vector((cx + hr * 0.95 * math.cos(ph), hy + hr * 0.95 * math.sin(ph), 0)); p1.z = deck_top(p1.x, p1.y) + 0.01
            p2 = Vector((cx + hr * 0.95 * math.cos(ph2), hy + hr * 0.95 * math.sin(ph2), 0)); p2.z = deck_top(p2.x, p2.y) + 0.01
            rims.append(plate_poly([p1, pts_o[q], pts_o[(q + 1) % 24], p2], 0.01))
    put("DeckHoleRims", merged(rims), C["rust2"])
    # wheelhouse: rust runs under the windows and from the roof edge, rust patches, silt on the roof
    runs = []
    for (b0, b1, h0, h1) in win_front:
        for k in range(3):
            y = rnd.uniform(b0, b1); ln = rnd.uniform(0.4, 1.0)
            runs.append(box((0.006, rnd.uniform(0.03, 0.08), ln), (wb + 0.035, y, h0 - ln / 2)))
    for sd in (-1, 1):
        for k in range(7):
            x = rnd.uniform(wa + 0.1, wb - 0.1); ln = rnd.uniform(0.3, 1.4)
            runs.append(box((rnd.uniform(0.03, 0.09), 0.006, ln), (x, sd * (hw2 + 0.035), wz + H - ln / 2)))
    for k in range(10):
        x = rnd.uniform(wa + 0.2, wb - 0.2); sd = rnd.choice((-1, 1)); z = rnd.uniform(wz + 0.2, wz + 1.0); r = rnd.uniform(0.1, 0.3)
        runs.append(plate_poly([Vector((x + r * math.cos(a) * (1 + 0.4 * nz((a, k, 1), 2)), sd * (hw2 + 0.036), z + r * 0.7 * math.sin(a))) for a in (q / 12 * math.tau for q in range(12))], 0.004))
    put("WheelhouseRust", merged(runs), C["rust"])
    put("RoofSilt", slab(blot((wa + wb) / 2, -0.3, 1.2, 900, lambda a, b: wz + H + 0.1 + 0.04 * max(0.0, -b)), 0.05), C["silt"], smooth=True)
    inner_silt = [slab(blot(x, y, r, 950 + k, lambda a, b: FLOOR_Z + 0.015), 0.03) for k, (x, y, r) in
                  enumerate(((-1.5, -1.9, 0.7), (1.5, -2.0, 0.6), (-2.8, -1.0, 0.5), (sx(0.15), -1.3, 0.6), (sx(0.25), -1.6, 0.5)))]
    put("InteriorSilt", merged(inner_silt), C["silt"], smooth=True)
    # rusticles hanging from the deck underside inside the hold and crew quarters
    rin = []
    for k in range(60):
        s_ = rnd.uniform(CABIN[0] + 0.01, HOLD[1] - 0.01)
        if HATCH[0] - 0.01 < s_ < HATCH[1] + 0.01: continue
        x = sx(s_); y = rnd.uniform(-1, 1) * (inner_y(s_, deck_z(s_) - 0.3) - 0.2)
        rin.append(rusticle(Vector((x, y, deck_top(x, y) - 0.05)), rnd.uniform(0.08, 0.35)))
    put("RusticlesInside", merged(rin), C["rust"], smooth=True)

    # ---- seabed (root frame): mound with the hull bedded in, spilled debris
    def ground(x, y):
        sx_, sy_ = x / 12.8, (y + 0.4) / 3.9; s = math.hypot(sx_, sy_)
        if s < 0.62: h = -2.4
        elif s < 1.0: h = -2.4 + 2.85 * ((s - 0.62) / 0.38) ** 0.9
        elif s < 1.65: h = 0.45 * (1 - (s - 1.0) / 0.65) ** 2
        else: h = 0.0
        return h + 0.04 * nz((x, y, 4.0), 0.6) * min(1.0, max(0.0, 1.65 - s) * 3)
    bm = bmesh.new(); NR, NA = 40, 140; rings_ = []
    for r in range(NR + 1):
        s = 0.62 + (1.65 - 0.62) * r / NR; ring = []
        for a in range(NA):
            ph = a / NA * math.tau; x, y = 12.8 * s * math.cos(ph), -0.4 + 3.9 * s * math.sin(ph)
            ring.append(bm.verts.new((x, y, ground(x, y) if r < NR else 0.0)))
        rings_.append(ring)
    for r in range(NR):
        for a in range(NA):
            bm.faces.new((rings_[r][a], rings_[r][(a + 1) % NA], rings_[r + 1][(a + 1) % NA], rings_[r + 1][a]))
    put("Seabed", bm, C["sed"], smooth=True, on_ship=False)
    deb_w, deb_b, deb_p, rocks = [], [], [], []
    for k in range(8):     # crates / fish boxes spilled out of the hole onto the starboard seabed
        x, y = rnd.uniform(-2.5, 1.5), rnd.uniform(4.8, 7.5); deb_w.append(box((0.8, 0.6, 0.5), (0, 0, 0.25), Matrix.Translation((x, y, ground(x, y))) @ RZ(rnd.uniform(0, 90)) @ RX(rnd.uniform(-15, 15))))
    for k in range(4):
        x, y = rnd.uniform(-6, 6), rnd.choice((-1, 1)) * rnd.uniform(5.2, 6.8)
        deb_b.append(cyl(0.3, 0.88, 16, (0, 0, 0), Matrix.Translation((x, y, ground(x, y) + 0.28)) @ RX(90) @ RZ(rnd.uniform(0, 180))))
    for k in range(10):    # torn plates
        x, y = rnd.uniform(-10, 10), rnd.choice((-1, 1)) * rnd.uniform(4.6, 7.0); sz = rnd.uniform(0.4, 1.1)
        b = plate_poly([Vector((math.cos(a) * sz * (1 + 0.4 * rnd.random()), math.sin(a) * sz * 0.6 * (1 + 0.4 * rnd.random()), 0)) for a in (q / 7 * math.tau for q in range(7))], 0.03)
        bmesh.ops.transform(b, matrix=Matrix.Translation((x, y, ground(x, y) + 0.05)) @ RZ(rnd.uniform(0, 180)) @ RX(rnd.uniform(-20, 20)), verts=b.verts); deb_p.append(b)
    for k in range(20):
        a = rnd.uniform(0, math.tau); s = rnd.uniform(1.05, 1.6); x, y = 12.8 * s * math.cos(a), -0.4 + 3.9 * s * math.sin(a); sz = rnd.uniform(0.1, 0.4)
        rocks.append(rock(Vector((x, y, ground(x, y) + sz * 0.2)), (sz, sz * 0.8, sz * 0.5), 200 + k))
    put("DebrisCrates", merged(deb_w), C["wood"], on_ship=False)
    put("DebrisBarrels", merged(deb_b), C["barrel"], smooth=True, on_ship=False)
    put("DebrisPlates", merged(deb_p), C["rust2"], on_ship=False)
    put("Rocks", merged(rocks), C["rock"], smooth=True, on_ship=False)

    # sockets (ship frame -> root via SHIP)
    hc = hull_pt(HOLE[0], HOLE[1]); hn = hull_n(HOLE[0], HOLE[1])
    sock("Hide_Hold", (-1.3, -0.9, FLOOR_Z + 0.02))
    sock("Hide_Wheelhouse", (wa + 0.8, 0.6, wz + 0.02))
    sock("Enter_HullHole", tuple(hc), hn)                    # +Z = outward through the hole
    sock("Interact_Enter_Hole", tuple(hc + hn * 0.9))
    sock("Enter_Hatch", ((x0 + x1) / 2, 0, dz + 0.6))
    sock("Enter_WheelhouseDoor", (wa + 0.82, hw2 + 0.5, wz + 0.05))
    sock("Hide_Cabin", (sx(CABIN[1]) - 1.0, inner_y(0.29, FLOOR_Z + 1.0) - 0.35, FLOOR_Z + 0.02))   # inside the open locker
    sock("Enter_Stairs", ((sx(STAIR[0]) + sx(STAIR[1])) / 2, (STAIR[2] + STAIR[3]) / 2, deck_top(sx(STAIR[0]), -1.25)))
    sock("Door_HoldCabin", (sx(HOLD[0]), 0, FLOOR_Z))
    bpy.context.view_layer.update()
    return root


def export_all():
    root = bpy.data.objects[ROOT]
    mine = [o for o in root.children if o.name.startswith("SKT_") and o.name.endswith(SFX)]
    parked = []
    for o in mine:
        plain = o.name[:-len(SFX)]; other = bpy.data.objects.get(plain)
        if other: other.name = plain + "__park"; parked.append((other, plain))
        o.name = plain
    try:
        if "bake_export" in globals():   # texture-baked export (weather_bake.py)
            return bake_export(ROOT, SM_NAME, "Shipwreck", nobake={"M_Seabed_Sediment", "M_Seabed_Rock", "M_Wreck_Glass"}, size=4096)
        return export_unreal(ROOT, SM_NAME, (0, 0, 0))
    finally:
        for o in mine: o.name = o.name + SFX
        for other, plain in parked: other.name = plain


mats()
build()
print("SHIPWRECK built")
