# Map prop: giant whale skeleton (2026-11-18, replaces the rotting whale carcass). exec after mk.py in DiveGear_Scene.blend.
# Clean bones only, no flesh: a ~20 m baleen-whale skeleton on the seabed. The spine arches up to ~2.4 m over the chest and
# 14 rib pairs curve down into the sand, forming a tunnel-like ribcage. Two starboard ribs are snapped -> the gap lets a
# diver slip inside the ribcage to hide (partly visible through the gaps between ribs).
# Also: baleen-whale skull (flat rostrum, ridge, crest, zygomatic arches, orbits), lower jaws, shoulder blades,
# flipper bones, pelvic remnants, tail chevrons; shallow sand mound, rocks, a few crabs, small Osedax tufts, bacterial mats.
# Frame: pivot = seabed (z = 0) under the middle of the ribcage, head +X.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise

MT = bpy.data.materials
ROOT, POS, SFX, SM_NAME = "WhaleSkeleton", Vector((0, 40, 0)), "__WSK", "SM_WhaleSkeleton"
RIB_X0, RIB_DX, NRIB = 3.2, 0.5, 14
BROKEN = (6, 7)                    # starboard ribs snapped -> entrance gap

C = {}
def mats():
    C["bone"] = mat("M_Whale_Bone", (0.78, 0.74, 0.62), rough=0.7)
    C["bone2"] = mat("M_Whale_BoneStained", (0.6, 0.55, 0.44), rough=0.75)
    C["hole"] = mat("M_Whale_Hole", (0.02, 0.015, 0.015), rough=0.9)
    C["matw"] = mat("M_Whale_BacteriaWhite", (0.9, 0.9, 0.84), rough=0.9)
    C["worm"] = mat("M_Whale_Osedax", (0.78, 0.06, 0.08), rough=0.5)
    C["crab"] = mat("M_Whale_Crab", (0.75, 0.32, 0.12), rough=0.5)
    C["sed"] = mat("M_Seabed_Sediment", (0.33, 0.31, 0.27), rough=0.95)
    C["rock"] = mat("M_Seabed_Rock", (0.22, 0.21, 0.2), rough=0.85)
    W = {"bone": dict(rust=0.25, grime=0.6, mold=0.45, pit=0.8, scale=2.0, rough=0.8), "bone2": dict(rust=0.4, grime=0.75, mold=0.55, pit=0.9, scale=2.0, rough=0.8),
         "hole": dict(rust=0.1, grime=0.5), "matw": dict(rust=0.0, grime=0.3, mold=0.2, scale=2.0), "worm": dict(rust=0.0, grime=0.2),
         "crab": dict(rust=0.1, grime=0.35, scale=4.0), "sed": dict(rust=0.0, grime=0.5, mold=0.2, scale=0.8, bump=0.6), "rock": dict(rust=0.1, grime=0.55, mold=0.35, scale=1.5)}
    if "weather" in globals():   # weathered procedural look for the bake (weather_bake.py)
        for k, prm in W.items(): weather(C[k], **prm)


# ---------------------------------------------------------------- helpers
def merged(bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("_t"); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out


def nz(p, sc):
    return noise.noise(Vector(p) * sc)


def catmull1(vals, t):
    n = len(vals); i = min(int(t), n - 2); f = t - i
    p0, p1, p2, p3 = vals[max(i - 1, 0)], vals[i], vals[i + 1], vals[min(i + 2, n - 1)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)


def rock(center, size, seed, sub=2, amp=0.35):
    b = bmesh.new(); bmesh.ops.create_icosphere(b, subdivisions=sub, radius=1.0)
    for v in b.verts:
        v.co *= 1.0 + amp * nz(v.co + Vector((seed, 0, 0)), 1.4)
    bmesh.ops.transform(b, matrix=Matrix.Translation(center) @ Matrix.Diagonal((*size, 1)), verts=b.verts); return b


def along_m(p, d):
    """Local frame: Z along d, Y as close to world up as possible, X sideways."""
    return Matrix.Translation(p) @ Vector(d).to_track_quat("Z", "Y").to_matrix().to_4x4()


def etube(poly, rw, rh, up=(0, 0, 1), sides=12):
    """Tube with an elliptical section: rh along 'up', rw sideways. rw/rh: f(t)."""
    bm = bmesh.new(); up = Vector(up); n = len(poly); rings = []
    for i, p in enumerate(poly):
        a = poly[max(i - 1, 0)]; b = poly[min(i + 1, n - 1)]; t = (b - a).normalized()
        w = (up - t * up.dot(t)); w = w.normalized() if w.length > 1e-6 else t.orthogonal().normalized(); nn = t.cross(w)
        s = i / max(1, n - 1)
        rings.append([bm.verts.new(p + w * math.cos(k / sides * math.tau) * rh(s) + nn * math.sin(k / sides * math.tau) * rw(s)) for k in range(sides)])
    for i in range(n - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    return bm


def ground(x, y):
    """Shallow sand mound along the skeleton, 0 at the rim."""
    s = math.hypot((x + 4.5) / 11.0, y / 3.4)
    if s >= 1.0: return 0.0
    return 0.18 * (1 - s * s) ** 1.5 + 0.03 * nz((x, y, 3.0), 0.7) * (1 - s)


SPINE = [(4.3, 1.25), (3.0, 2.15), (1.5, 2.45), (0.0, 2.45), (-1.8, 2.25), (-3.5, 1.7), (-5.5, 1.0), (-8.0, 0.55), (-11.0, 0.32), (-14.5, 0.2)]

def spine_at(x):
    xs = [p[0] for p in SPINE]
    for i in range(len(xs) - 1):
        if xs[i] >= x >= xs[i + 1]:
            t = i + (xs[i] - x) / (xs[i] - xs[i + 1]); break
    else:
        t = 0 if x > xs[0] else len(xs) - 1
    z = catmull1([p[1] for p in SPINE], min(t, len(xs) - 1.0001))
    y = 0.25 * math.sin(min(0.0, x + 5.0) * 0.45)          # tail drifts slightly sideways
    return Vector((x, y, z))


def vsize(x):
    if x > 1.0: return 0.85 + 0.15 * (4.3 - x) / 3.3
    if x > -2.0: return 1.0
    return max(0.25, 1.0 - 0.75 * (-2.0 - x) / 12.3)


# ---------------------------------------------------------------- skull and jaws (baleen whale)
ROST = [(5.0, 0.95, 1.25, 0.30), (5.8, 0.72, 1.12, 0.24), (6.8, 0.5, 0.86, 0.17), (7.8, 0.32, 0.55, 0.11), (8.7, 0.18, 0.2, 0.06)]   # x, cz, width/2, thick/2

def rost_at(x):
    t = (x - ROST[0][0]) / (ROST[-1][0] - ROST[0][0]) * (len(ROST) - 1)
    return [catmull1([r[k] for r in ROST], max(0.0, min(len(ROST) - 1, t))) for k in range(4)]


def skull_bms():
    bms = []
    bm = bmesh.new(); rings = []; NS, SEG = 46, 32            # flat rostrum, central ridge, scalloped edges
    for k in range(NS + 1):
        x = ROST[0][0] - 0.05 + (ROST[-1][0] - ROST[0][0] + 0.05) * k / NS
        _, cz, w, h = rost_at(x); ring = []
        for j in range(SEG):
            a = j / SEG * math.tau; c, s = math.cos(a), math.sin(a)
            y = w * math.copysign(abs(c) ** (2 / 3.2), c); z = h * math.copysign(abs(s) ** (2 / 2.2), s)
            if s > 0: z += 0.07 * math.exp(-(y / 0.1) ** 2) * (1 - k / NS * 0.6)
            y *= 1 + 0.03 * math.sin(x * 9) * abs(c) ** 6
            p = Vector((x, y, cz + z)); p += Vector((0, 0, 1)) * 0.012 * nz(p, 5.0)
            ring.append(bm.verts.new(p))
        rings.append(ring)
    for k in range(NS):
        for j in range(SEG):
            bm.faces.new((rings[k][j], rings[k + 1][j], rings[k + 1][(j + 1) % SEG], rings[k][(j + 1) % SEG]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1]); bms.append(bm)
    st = [(4.4, 1.22, 0.78, 0.7), (4.8, 1.25, 1.05, 0.78), (5.15, 1.05, 1.2, 0.5), (5.35, 0.95, 1.1, 0.32)]   # cranium + crest
    cols = list(zip(*st)); bm = bmesh.new(); rings = []; NS, SEG = 18, 30
    for k in range(NS + 1):
        t = k / NS * (len(st) - 1); x, cz, ry, rz = (catmull1(list(c), t) for c in cols); ring = []
        for j in range(SEG):
            a = j / SEG * math.tau; p = Vector((x, ry * math.cos(a), cz + rz * math.sin(a)))
            if math.sin(a) > 0.6: p.z += 0.08 * (math.sin(a) - 0.6) / 0.4 * (1 - t / 3)
            p += Vector((0, math.cos(a), math.sin(a))) * 0.025 * nz(p, 2.5)
            ring.append(bm.verts.new(p))
        rings.append(ring)
    for k in range(NS):
        for j in range(SEG):
            bm.faces.new((rings[k][j], rings[k + 1][j], rings[k + 1][(j + 1) % SEG], rings[k][(j + 1) % SEG]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1]); bms.append(bm)
    for s in (-1, 1):                                          # zygomatic arches
        pts = catmull([Vector((4.7, s * 0.95, 1.05)), Vector((4.95, s * 1.45, 0.92)), Vector((5.35, s * 1.42, 0.78)), Vector((5.6, s * 1.15, 0.75))], 6)
        bms.append(etube(pts, lambda t: 0.08 - 0.02 * t, lambda t: 0.06, sides=10))
    return bms


def jaw_bm(s, off):
    pts = [Vector((4.3, s * 0.95, 0.32)), Vector((5.6, s * 1.42, 0.2)), Vector((7.0, s * 1.32, 0.13)), Vector((8.65, s * 0.42, 0.1))]
    poly = [p + off for p in catmull(pts, 10)]
    for p in poly: p.z = max(p.z, ground(p.x, p.y) + 0.06)
    b = etube(poly, lambda t: 0.15 - 0.09 * t, lambda t: 0.1 - 0.06 * t, sides=14)
    cond = lathe([(0.0, -0.1), (0.13, -0.06), (0.15, 0.02), (0.1, 0.1), (0.0, 0.12)], 14, Matrix.Translation(poly[0] + Vector((-0.08, 0, 0.02))))
    return merged([b, cond])


# ---------------------------------------------------------------- vertebra
def vertebra(p, d, f, t, chevron):
    """t: 0 chest .. 1 tail tip (processes shrink and vanish toward the tail)."""
    M = along_m(p, d); parts = []
    L, R = 0.26 * f, 0.21 * f
    parts.append(lathe([(0.0, -L / 2), (R, -L / 2), (R * 1.04, -L / 2 + 0.02 * f), (R * 0.86, 0.0), (R * 1.04, L / 2 - 0.02 * f), (R, L / 2), (0.0, L / 2)], 16, M))
    if t < 0.8:
        for sx in (-1, 1):
            parts.append(box((0.045 * f, 0.16 * f, 0.1 * f), (sx * 0.07 * f, R + 0.07 * f, 0), M))
        hs = 0.5 * f * (1 - 0.75 * t)
        sp = bmesh.new(); vs = [sp.verts.new(v) for v in ((-0.02 * f, R + 0.12 * f, -0.07 * f), (-0.02 * f, R + 0.12 * f, 0.07 * f),
                                                          (-0.02 * f, R + 0.12 * f + hs, -0.08 * f + hs * 0.3), (-0.02 * f, R + 0.12 * f + hs, 0.05 * f + hs * 0.3))]
        sp.faces.new((vs[0], vs[1], vs[3], vs[2])); bmesh.ops.solidify(sp, geom=sp.faces[:], thickness=0.045 * f)
        bmesh.ops.transform(sp, matrix=M, verts=sp.verts); parts.append(sp)
        lt = 0.6 * f * (1 - 0.7 * t)
        for sx in (-1, 1):
            parts.append(strap([M @ Vector((sx * R * 0.8, 0, 0)), M @ Vector((sx * (R + lt * 0.6), -0.03 * f, 0)), M @ Vector((sx * (R + lt), -0.08 * f, 0.02 * f))],
                               M.to_3x3() @ Vector((0, 0, 1)), lambda q: 0.13 * f * (1 - 0.5 * q), 0.03 * f))
    if chevron:
        for sx in (-1, 1):
            parts.append(strap([M @ Vector((sx * 0.03 * f, -R * 0.9, 0.04 * f)), M @ Vector((sx * 0.02 * f, -R - 0.12 * f, 0.05 * f)), M @ Vector((0, -R - 0.24 * f, 0.08 * f))],
                               M.to_3x3() @ Vector((0, 0, 1)), 0.04 * f, 0.02 * f))
    return parts


def worms(points, seed, per=14):
    rnd = random.Random(seed); out = []
    for p in points:
        for _ in range(per):
            q = Vector(p) + Vector((rnd.uniform(-0.06, 0.06), rnd.uniform(-0.06, 0.06), 0)); h = rnd.uniform(0.02, 0.045)
            b = cyl(0.004, h, 5, (q.x, q.y, q.z + h / 2))
            for k in range(4):
                fr = bmesh.new(); bmesh.ops.create_cone(fr, cap_ends=True, segments=4, radius1=0.006, radius2=0.0015, depth=0.03)
                bmesh.ops.transform(fr, matrix=Matrix.Translation(q + Vector((0, 0, h + 0.012))) @ Matrix.Rotation(k / 4 * math.tau + rnd.random(), 4, "Z") @ Matrix.Rotation(math.radians(40), 4, "X") @ Matrix.Translation((0, 0, 0.012)), verts=fr.verts)
                me = bpy.data.meshes.new("_t"); fr.to_mesh(me); fr.free(); b.from_mesh(me); bpy.data.meshes.remove(me)
            out.append(b)
    return merged(out)


def crab(p, yaw, size=1.0):
    parts = [rock(p + Vector((0, 0, 0.03 * size)), (0.1 * size, 0.08 * size, 0.035 * size), 3, sub=1, amp=0.15)]
    Mz = Matrix.Rotation(yaw, 4, "Z")
    for s in (-1, 1):
        for k in range(4):
            a = math.radians(-50 + 30 * k)
            b0 = p + Mz @ Vector((0.05 * size * math.cos(a), s * 0.07 * size, 0.035 * size))
            b1 = b0 + Mz @ Vector((0.08 * size * math.cos(a), s * 0.12 * size, 0.05 * size))
            b2 = b1 + Mz @ Vector((0.06 * size * math.cos(a), s * 0.08 * size, -0.09 * size))
            parts.append(tube([b0, b1, b2], 0.008 * size, sides=5))
        c0 = p + Mz @ Vector((0.09 * size, s * 0.05, 0.04 * size)); c1 = c0 + Mz @ Vector((0.1 * size, s * 0.04, 0.02))
        parts += [tube([c0, c1], 0.012 * size, sides=6), rock(c1 + Mz @ Vector((0.04 * size, 0, 0)), (0.05 * size, 0.025 * size, 0.02 * size), 7, sub=1, amp=0.15)]
    return merged(parts)


def drape(cx, cy, r, seed, lift=0.012, rings=6, segs=26):
    bm = bmesh.new(); grid = []
    for k in range(1, rings + 1):
        s = k / rings; row = []
        for a in range(segs):
            ph = a / segs * math.tau; rr = r * s * (1 + 0.35 * nz((math.cos(ph), math.sin(ph), seed), 1.6))
            x, y = cx + rr * math.cos(ph), cy + rr * 0.7 * math.sin(ph)
            row.append(bm.verts.new((x, y, ground(x, y) + lift)))
        grid.append(row)
    c0 = bm.verts.new((cx, cy, ground(cx, cy) + lift))
    for a in range(segs):
        bm.faces.new((c0, grid[0][a], grid[0][(a + 1) % segs]))
    for k in range(rings - 1):
        for a in range(segs):
            bm.faces.new((grid[k][a], grid[k + 1][a], grid[k + 1][(a + 1) % segs], grid[k][(a + 1) % segs]))
    return bm


def scapula(s):
    """Fan-shaped shoulder blade standing against the front ribs."""
    bm = bmesh.new(); base = Vector((3.45, s * 1.95, 0.55)); vs = [bm.verts.new(base)]
    for k in range(13):
        a = math.radians(-70 + 140 * k / 12); r = 0.95 * (1 + 0.05 * math.cos(a * 5))
        vs.append(bm.verts.new(base + Vector((r * math.sin(a) * 0.9, -s * 0.12 * math.cos(a) ** 2, r * math.cos(a)))))   # slightly cupped
    for k in range(1, 13):
        bm.faces.new((vs[0], vs[k], vs[k + 1]))
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.1)
    R = Matrix.Translation(base) @ Matrix.Rotation(math.radians(s * 18), 4, "X") @ Matrix.Translation(-base)
    bmesh.ops.transform(bm, matrix=R, verts=bm.verts)
    return bm


def flipper(base, d):
    d = d.normalized(); side = d.cross(Vector((0, 0, 1)))
    fl = [etube([base, base + d * 0.55], lambda t: 0.11, lambda t: 0.09, sides=10)]
    fl += [etube([base + d * 0.57 + side * o_, base + d * 1.12 + side * o_ * 1.4], lambda t: 0.06, lambda t: 0.045, sides=8) for o_ in (-0.065, 0.065)]
    for g in range(4):
        dg = Matrix.Rotation(math.radians(-24 + 16 * g), 3, "Z") @ d; p0 = base + d * 1.15 + side * (-0.13 + 0.085 * g)
        for ph in range(4 - (g == 3)):
            fl.append(lathe([(0.0, -0.065), (0.038 - 0.005 * ph, -0.055), (0.027 - 0.004 * ph, 0.0), (0.038 - 0.005 * ph, 0.055), (0.0, 0.065)], 8,
                            along_m(p0 + dg * (0.08 + 0.15 * ph), dg)))
    return merged(fl)


# ---------------------------------------------------------------- build
def build():
    rnd = random.Random(21)
    for o in [o for o in bpy.data.objects if o.name.endswith(SFX)]:
        bpy.data.objects.remove(o, do_unlink=True)
    col = get_col(ROOT)
    old = bpy.data.objects.get(ROOT)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    root = bpy.data.objects.new(ROOT, None); col.objects.link(root); root.location = POS

    def put(name, bm, mats_, smooth=True):
        mats_ = mats_ if isinstance(mats_, (list, tuple)) else [mats_]
        o = finish(col, "WS_" + name + SFX, bm, mats_[0], smooth=smooth)
        for m in mats_[1:]: o.data.materials.append(m)
        o.parent = root; return o

    def sock(name, loc, rot=(0, 0, 0)):
        e = bpy.data.objects.new("SKT_" + name + SFX, None); col.objects.link(e)
        e.empty_display_type = "ARROWS"; e.empty_display_size = 0.3; e.parent = root
        e.location = loc; e.rotation_euler = tuple(math.radians(a) for a in rot)

    # sand mound
    bm = bmesh.new(); NR, NA = 34, 128; rings = []; c0 = bm.verts.new((-4.5, 0, ground(-4.5, 0)))
    for r in range(1, NR + 1):
        s = r / NR; ring = []
        for a in range(NA):
            ph = a / NA * math.tau; x, y = -4.5 + 11.0 * s * math.cos(ph), 3.4 * s * math.sin(ph)
            ring.append(bm.verts.new((x, y, ground(x, y) if r < NR else 0.0)))
        rings.append(ring)
    for a in range(NA):
        bm.faces.new((c0, rings[0][a], rings[0][(a + 1) % NA]))
    for r in range(NR - 1):
        for a in range(NA):
            bm.faces.new((rings[r][a], rings[r + 1][a], rings[r + 1][(a + 1) % NA], rings[r][(a + 1) % NA]))
    put("Sand", bm, C["sed"])

    # skull, orbits / nostrils, jaws
    put("Skull", merged(skull_bms()), C["bone"])
    put("SkullHoles", merged([lathe([(0.0, -0.02), (0.17, -0.02), (0.12, 0.03), (0.0, 0.04)], 18, Matrix.Translation((5.0, s * 1.22, 0.9)) @ Matrix.Rotation(math.radians(-s * 80), 4, "X"))
                              for s in (-1, 1)] +
                             [cyl(0.05, 0.02, 12, (0, 0, 0), Matrix.Translation((5.05, s * 0.09, 1.5)) @ Matrix.Diagonal((2.2, 1, 1, 1))) for s in (-1, 1)]), C["hole"])
    put("Jaws", merged([jaw_bm(1, Vector((0.25, 0.35, 0))), jaw_bm(-1, Vector((0, -0.1, 0)))]), C["bone2"])

    # vertebral column: neck at the skull -> arched chest -> tail on the sand (tail tip scattered)
    va, vb_ = [], []; x = 4.05; k = 0; tops = []
    while x > -14.3:
        f = vsize(x); p = spine_at(x); d = (spine_at(x - 0.05) - spine_at(x + 0.05)).normalized(); t = max(0.0, min(1.0, (-x + 1.0) / 15.3))
        if x < -12.0:
            p = p + Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.3, 0.3), 0)); d = Matrix.Rotation(rnd.uniform(-0.7, 0.7), 3, "Z") @ d
        p.z = max(p.z, ground(p.x, p.y) + 0.21 * f)
        (va if k % 5 else vb_).extend(vertebra(p, d, f, t, -11.0 < x < -5.5))
        if k % 6 == 2: tops.append(p + Vector((0, 0, 0.21 * f + 0.12 * f)))
        x -= 0.36 * f + 0.06; k += 1
    put("Vertebrae", merged(va), C["bone"])
    put("VertebraeStained", merged(vb_), C["bone2"])

    # ribcage: 14 pairs angled back, tips buried in the sand; 2 starboard ribs snapped (entrance), fragments outside
    ribs, ribs2, frags = [], [], []
    for k in range(NRIB):
        x = RIB_X0 - RIB_DX * k; zs = spine_at(x).z; sc = 0.78 + 0.22 * math.sin(math.pi * (k + 1) / (NRIB + 1))
        for s in (-1, 1):
            pts = [Vector((x, s * 0.25, zs + 0.02)), Vector((x - 0.05, s * 1.0 * sc, zs + 0.12)), Vector((x - 0.12, s * 1.75 * sc, zs - 0.55)),
                   Vector((x - 0.2, s * 1.9 * sc, (zs - 0.55) * 0.45)), Vector((x - 0.25, s * 1.7 * sc, 0.08)), Vector((x - 0.27, s * 1.5 * sc, -0.12))]
            if s > 0 and k in BROKEN:                       # snapped: stub stays, the rest lies on the sand outside
                pts = pts[:3]; pts[-1] = pts[1].lerp(pts[2], 0.45)
                fx = x - 0.3 + 0.3 * (k - BROKEN[0])
                frag = [Vector((fx, 2.2 + 0.15 * (k - BROKEN[0]), 0)), Vector((fx - 0.5, 2.55, 0)), Vector((fx - 1.0, 2.75, 0))]
                for p in frag: p.z = ground(p.x, p.y) + 0.05
                frags.append(strap(catmull(frag, 6), Vector((0, 0, 1)), lambda q: 0.13 - 0.05 * q, 0.06))
            elif rnd.random() < 0.15:                       # slight sag on a few ribs
                for p in pts[2:]: p.y *= 0.95
            bm_ = strap(catmull(pts, 10), Vector((1, 0, 0)), lambda q: 0.14 - 0.07 * q, lambda q: 0.07 - 0.03 * q)
            (ribs2 if (k + (s > 0)) % 4 == 0 else ribs).append(bm_)
            ribs.append(rock(pts[0] + Vector((0, -s * 0.04, 0)), (0.08, 0.08, 0.07), 200 + k, sub=1, amp=0.15))     # rib head
    put("Ribs", merged(ribs + frags), C["bone"])
    put("RibsStained", merged(ribs2), C["bone2"])

    # shoulder blades + flippers lying forward on the sand, pelvic remnants
    put("Scapulae", merged([scapula(s) for s in (-1, 1)]), C["bone2"])
    fl = []
    for s, off in ((-1, Vector()), (1, Vector((0.3, 0.25, 0)))):
        base = Vector((3.3, s * 2.0, 0)) + off; base.z = ground(base.x, base.y) + 0.09
        fl.append(flipper(base, Vector((0.5, s * 0.85, 0))))
    put("Flippers", merged(fl), C["bone"])
    pel = []
    for s in (-1, 1):
        a = Vector((-5.6, s * 0.55, 0)); b = Vector((-6.4, s * 0.75, 0))
        for p in (a, b): p.z = ground(p.x, p.y) + 0.05
        pel.append(etube([a, (a + b) / 2 + Vector((0, 0, 0.04)), b], lambda t: 0.05, lambda t: 0.035, sides=8))
    put("Pelvis", merged(pel), C["bone2"])

    # small life: Osedax tufts, crabs, a few bacterial mats, rocks
    put("Osedax", worms(tops[::2] + [Vector((5.6, 0.3, 1.32)), Vector((4.75, -0.4, 2.02))], 9), C["worm"])
    put("Crabs", merged([crab(Vector((6.1, 0.4, 0.93)), 1.0), crab(Vector((-1.3, 1.95, ground(-1.3, 1.95))), 2.2, 1.1),
                         crab(Vector((-7.0, -0.9, ground(-7.0, -0.9))), 4.0, 0.9)]), C["crab"])
    put("BacteriaWhite", merged([drape(-0.4 + rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0.3, 0.7), 300 + i) for i in range(3)] +
                                [drape(-8.5 + 2.5 * i, rnd.uniform(-1.5, 1.5), rnd.uniform(0.3, 0.6), 310 + i) for i in range(3)]), C["matw"])
    rocks = []
    for i in range(16):
        ph = rnd.uniform(0, math.tau); s = rnd.uniform(0.55, 0.95); x, y = -4.5 + 11.0 * s * math.cos(ph), 3.4 * s * math.sin(ph); sz = rnd.uniform(0.08, 0.3)
        rocks.append(rock(Vector((x, y, ground(x, y) + sz * 0.2)), (sz, sz * 0.8, sz * 0.5), i))
    put("Rocks", merged(rocks), C["rock"])

    # sockets
    gx = RIB_X0 - RIB_DX * (BROKEN[0] + BROKEN[1]) / 2 - 0.15
    sock("Hide_Inside", (gx, 0, ground(gx, 0)))
    sock("Hide_Entrance", (gx, 1.75, 0.7), (-90, 0, 0))       # +Z = outward (+Y) through the broken-rib gap
    sock("Interact_Enter", (gx, 2.5, 0.4))
    sock("Camera_Inside", (gx - 1.2, 0, 1.3))
    bpy.context.view_layer.update()
    return root


def export_all():
    """export_unreal with the scene-only socket suffix removed."""
    root = bpy.data.objects[ROOT]
    mine = [o for o in root.children if o.name.startswith("SKT_") and o.name.endswith(SFX)]
    parked = []
    for o in mine:
        plain = o.name[:-len(SFX)]; other = bpy.data.objects.get(plain)
        if other: other.name = plain + "__park"; parked.append((other, plain))
        o.name = plain
    try:
        if "bake_export" in globals():
            return bake_export(ROOT, SM_NAME, "WhaleSkeleton", size=4096)
        return export_unreal(ROOT, SM_NAME, (0, 0, 0))
    finally:
        for o in mine: o.name = o.name + SFX
        for other, plain in parked: other.name = plain


mats()
for nm in ("WhaleCarcass", "WhaleCarcass_Burst"):          # retire the rotting-carcass versions from the scene
    r = bpy.data.objects.get(nm)
    if r:
        for o in [r, *r.children_recursive]: bpy.data.objects.remove(o, do_unlink=True)
    c = bpy.data.collections.get(nm)
    if c: bpy.data.collections.remove(c)
build()
print("WHALE SKELETON built")
