# Map prop: underwater cave (2026-11-18). exec after mk.py (+ weather_bake.py for the baked export) in DiveGear_Scene.blend.
# A rock hill (~19 x 13 x 6 m) with a winding cave: main entrance (+X) -> curved tunnel -> central chamber -> narrow
# back passage (squeeze) -> back exit (-X). Two exits = escape route. Hiding: a crevice alcove in the chamber wall and
# behind fallen boulders in the chamber.
# Built by carving: displaced rock mass minus tunnel tubes / chamber / alcove (exact booleans, cut faces get the
# interior rock material). Decoration is placed by ray casting onto the carved rock.
# Outside: cold-water corals, glass sponges, crinoids, urchins, anemones, boulders. Inside: ceiling spikes,
# sand patches, glowing patches (emissive, not baked), a yellow cave-diving guideline with pegs, lost dive gear.
# Frame: pivot = seabed (z = 0) at the hill centre, main entrance +X.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

MT = bpy.data.materials
ROOT, POS, SFX, SM_NAME = "SeaCave", Vector((0, 100, 0)), "__SC", "SM_SeaCave"
ROCK_C, ROCK_R = Vector((0, 0.5, 0)), Vector((9.5, 6.5, 6.0))
MAIN = [Vector(p) for p in ((12.0, -1.6, 1.0), (9.0, -1.4, 1.1), (6.5, -0.9, 1.4), (4.2, -0.1, 1.7), (2.2, 0.6, 2.0), (0.0, 0.8, 2.2))]
BACK = [Vector(p) for p in ((-1.0, 0.7, 2.0), (-3.2, 0.2, 1.8), (-5.2, -0.9, 1.4), (-7.4, -2.1, 1.1), (-9.4, -2.8, 0.9), (-12.0, -3.3, 0.8))]
CHAMBER = (Vector((0.0, 0.8, 2.4)), Vector((3.4, 3.0, 2.3)))
ALCOVE = (Vector((0.9, 4.1, 1.9)), Vector((0.95, 1.0, 1.05)))
SQUEEZE_T = 0.45                     # where the back passage is narrowest (fraction along BACK)

C = {}
def mats():
    g = lambda n, c, **k: MT.get(n) or mat(n, c, **k)
    C["rock"] = mat("M_Cave_Rock", (0.21, 0.2, 0.19), rough=0.9)
    C["inner"] = mat("M_Cave_RockInner", (0.15, 0.14, 0.13), rough=0.85)
    C["sed"] = g("M_Seabed_Sediment", (0.33, 0.31, 0.27), rough=0.95)
    C["boulder"] = g("M_Seabed_Rock", (0.22, 0.21, 0.2), rough=0.85)
    C["coral"] = mat("M_Cave_Coral", (0.88, 0.86, 0.8), rough=0.7)
    C["sponge"] = mat("M_Cave_GlassSponge", (0.84, 0.8, 0.66), rough=0.6)
    C["crinoid"] = mat("M_Cave_Crinoid", (0.72, 0.26, 0.14), rough=0.6)
    C["urchin"] = mat("M_Cave_Urchin", (0.42, 0.12, 0.24), rough=0.6)
    C["anem"] = mat("M_Cave_Anemone", (0.92, 0.55, 0.6), rough=0.5)
    C["glow"] = mat("M_Cave_Glow", (0.2, 0.8, 0.7), emit=(0.25, 1.0, 0.85), strength=4.0)
    C["rope"] = mat("M_Cave_Guideline", (0.85, 0.7, 0.12), rough=0.6)
    C["tank"] = mat("M_Cave_LostTank", (0.75, 0.62, 0.15), metal=0.3, rough=0.5)
    C["gear"] = mat("M_Cave_LostGear", (0.06, 0.06, 0.065), rough=0.6)
    W = {"rock": dict(rust=0.15, grime=0.6, mold=0.45, pit=0.9, scale=0.7, bump=0.9), "inner": dict(rust=0.2, grime=0.75, mold=0.6, pit=1.0, scale=0.9, bump=0.9),
         "sed": dict(rust=0.0, grime=0.5, mold=0.2, scale=0.8, bump=0.6), "boulder": dict(rust=0.1, grime=0.55, mold=0.35, scale=1.5),
         "coral": dict(rust=0.05, grime=0.35, mold=0.2, scale=4.0), "sponge": dict(rust=0.05, grime=0.35, scale=4.0), "crinoid": dict(rust=0.0, grime=0.25, scale=5.0),
         "urchin": dict(rust=0.0, grime=0.3, scale=5.0), "anem": dict(rust=0.0, grime=0.2), "rope": dict(rust=0.1, grime=0.6, mold=0.4, scale=4.0),
         "tank": dict(rust=0.6, grime=0.6, mold=0.3, scale=3.0), "gear": dict(rust=0.2, grime=0.5, mold=0.3, scale=3.0)}
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


def fbm(p, sc, oct=4):
    a, f, s = 1.0, sc, 0.0
    for _ in range(oct):
        s += a * noise.noise(Vector(p) * f); a *= 0.5; f *= 2.1
    return s


def blob(center, radii, seed, sub=3, amp=0.25, flat=None):
    b = bmesh.new(); bmesh.ops.create_icosphere(b, subdivisions=sub, radius=1.0)
    for v in b.verts:
        d = v.co.normalized(); k = 1.0 + amp * fbm(d * 1.5 + Vector((seed, 0, 0)), 1.0, 3)
        v.co = Vector((d.x * radii[0], d.y * radii[1], d.z * radii[2])) * k
        if flat is not None and v.co.z < flat: v.co.z = flat + (v.co.z - flat) * 0.05
    bmesh.ops.translate(b, vec=center, verts=b.verts); return b


def catmull_pts(pts, n):
    return catmull(pts, n)


def tunnel(pts, rad, seed, n=10, sides=26):
    """Closed tube with a noisy, flat-floored section; rad(t) -> (half width, half height)."""
    path = catmull_pts(pts, n); bm = bmesh.new(); rings = []; N = len(path)
    for i, p in enumerate(path):
        t = i / (N - 1); a = path[max(i - 1, 0)]; b = path[min(i + 1, N - 1)]; d = (b - a).normalized()
        side = d.cross(Vector((0, 0, 1))).normalized(); up = side.cross(d).normalized()
        w, h = rad(t); ring = []
        for k in range(sides):
            ang = k / sides * math.tau; c, s = math.cos(ang), math.sin(ang)
            r = 1.0 + 0.18 * fbm((p.x * 0.6, p.y * 0.6 + ang, seed), 1.0, 3)
            q = p + side * (math.copysign(abs(c) ** 0.8, c) * w * r) + up * (math.copysign(abs(s) ** 0.8, s) * h * r)
            q.z = max(q.z, p.z - 0.62 * h)                                     # flat-ish floor
            ring.append(bm.verts.new(q))
        rings.append(ring)
    for i in range(N - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, path


def coral(p, seed, scale=1.0):
    """Branching cold-water coral (Lophelia-like): recursive white branches with cup tips."""
    rnd = random.Random(seed); parts = []
    def branch(a, d, L, r, depth):
        b = a + d * L
        parts.append(tube([a, a.lerp(b, 0.5) + Vector((rnd.uniform(-0.03, 0.03),) * 3) * L, b], r, sides=6))
        if depth == 0:
            parts.append(lathe([(0.0, 0.0), (r * 1.6, 0.02 * scale), (r * 1.9, 0.04 * scale), (r * 1.2, 0.04 * scale), (0.0, 0.03 * scale)], 6,
                               Matrix.Translation(b) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4())); return
        for _ in range(rnd.choice((2, 2, 3))):
            nd = (d + Vector((rnd.uniform(-0.8, 0.8), rnd.uniform(-0.8, 0.8), rnd.uniform(-0.1, 0.5)))).normalized()
            branch(b, nd, L * rnd.uniform(0.6, 0.8), r * 0.75, depth - 1)
    for k in range(rnd.randint(2, 4)):
        d = Vector((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), 1.0)).normalized()
        branch(p, d, 0.22 * scale, 0.025 * scale, 3)
    return merged(parts)


def glass_sponge(p, h, seed):
    rnd = random.Random(seed)
    prof = [(0.0, 0.0), (0.05, 0.0), (0.08, h * 0.25), (0.12, h * 0.6), (0.17, h * 0.95), (0.18, h), (0.15, h), (0.1, h * 0.62), (0.06, h * 0.25), (0.0, h * 0.2)]
    return lathe([(r * rnd.uniform(0.85, 1.15), z) for r, z in prof], 14, Matrix.Translation(p) @ Matrix.Rotation(rnd.uniform(-0.2, 0.2), 4, "X"))


def crinoid(p, seed):
    rnd = random.Random(seed); h = rnd.uniform(0.4, 0.8); top = p + Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), h))
    parts = [tube(catmull([p, p.lerp(top, 0.5) + Vector((0.04, 0, 0)), top], 4), 0.012, sides=5)]
    for k in range(10):
        a = k / 10 * math.tau; d = Vector((math.cos(a), math.sin(a), 0))
        arm = [top, top + d * 0.12 + Vector((0, 0, 0.08)), top + d * 0.2 + Vector((0, 0, 0.02)), top + d * 0.24 + Vector((0, 0, -0.06))]
        parts.append(tube(catmull(arm, 3), lambda q: 0.009 * (1 - 0.6 * q), sides=4))
    return merged(parts)


def urchin(p, seed):
    rnd = random.Random(seed); parts = [blob(p + Vector((0, 0, 0.05)), (0.07, 0.07, 0.05), seed, sub=2, amp=0.05)]
    for k in range(26):
        d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), abs(rnd.gauss(0, 1)) + 0.2)).normalized()
        sp = bmesh.new(); bmesh.ops.create_cone(sp, cap_ends=True, segments=4, radius1=0.006, radius2=0.0, depth=0.12)
        bmesh.ops.transform(sp, matrix=Matrix.Translation(p + Vector((0, 0, 0.05)) + d * 0.1) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4(), verts=sp.verts); parts.append(sp)
    return merged(parts)


def anemone(p, n, sc):
    b = cyl(0.05 * sc, 0.1 * sc, 10, (0, 0, 0), Matrix.Translation(p) @ n.to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Translation((0, 0, 0.05 * sc)))
    for k in range(12):
        fr = bmesh.new(); bmesh.ops.create_cone(fr, cap_ends=True, segments=4, radius1=0.012 * sc, radius2=0.002, depth=0.1 * sc)
        bmesh.ops.transform(fr, matrix=Matrix.Translation(p) @ n.to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Translation((0, 0, 0.1 * sc)) @
                            Matrix.Rotation(k / 12 * math.tau, 4, "Z") @ Matrix.Rotation(math.radians(50), 4, "X") @ Matrix.Translation((0, 0, 0.05 * sc)), verts=fr.verts)
        me = bpy.data.meshes.new("_t"); fr.to_mesh(me); fr.free(); b.from_mesh(me); bpy.data.meshes.remove(me)
    return b


# ---------------------------------------------------------------- build
def build():
    rnd = random.Random(17)
    for o in [o for o in bpy.data.objects if o.name.endswith(SFX)]:
        bpy.data.objects.remove(o, do_unlink=True)
    col = get_col(ROOT)
    old = bpy.data.objects.get(ROOT)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    root = bpy.data.objects.new(ROOT, None); col.objects.link(root); root.location = POS

    def put(name, bm, mats_, smooth=True):
        mats_ = mats_ if isinstance(mats_, (list, tuple)) else [mats_]
        o = finish(col, "SC_" + name + SFX, bm, mats_[0], smooth=smooth)
        for m in mats_[1:]: o.data.materials.append(m)
        o.parent = root; return o

    def sock(name, loc, normal=None):
        e = bpy.data.objects.new("SKT_" + name + SFX, None); col.objects.link(e)
        e.empty_display_type = "ARROWS"; e.empty_display_size = 0.4; e.parent = root
        R = Vector(normal).to_track_quat("Z", "Y").to_matrix().to_4x4() if normal else Matrix()
        e.matrix_basis = Matrix.Translation(loc) @ R

    # ---- rock mass: big displaced ellipsoid, ridged, flattened into the seabed
    b = bmesh.new(); bmesh.ops.create_icosphere(b, subdivisions=6, radius=1.0)
    for v in b.verts:
        d = v.co.normalized()
        k = 1.0 + 0.22 * fbm(d * 1.2, 1.0, 5) + 0.08 * abs(nz(d * 4.0, 1.0))          # lumps + ridges
        q = Vector((d.x * ROCK_R.x, d.y * ROCK_R.y, d.z * ROCK_R.z)) * k
        q.z += 0.6 * fbm((q.x * 0.15, q.y * 0.15, 4.0), 1.0, 2)                        # uneven top
        hz = Vector((d.x, d.y, 0)).normalized() if abs(d.z) < 0.98 else Vector()
        q += hz * 0.12 * math.sin(q.z * 3.2 + 1.5 * nz(q * 0.3, 1.0)) * (1 - abs(d.z))    # horizontal strata
        q += d * 0.04 * fbm(q * 0.9, 1.0, 3)                                              # fine roughness
        if q.z < 0.0: q.z *= 0.12                                                     # buried base
        v.co = q + ROCK_C
    rock = put("Rock", b, [C["rock"], C["inner"]])

    # ---- cutters: main tunnel, chamber, back passage (squeeze), alcove
    def rad_main(t): return (1.25 + 0.15 * math.sin(t * 7), 1.0 + 0.2 * t)
    def rad_back(t):
        sq = 1.0 - 0.42 * math.exp(-((t - SQUEEZE_T) / 0.12) ** 2)
        return (0.95 * sq, 0.85 * sq)
    tb, main_path = tunnel(MAIN, rad_main, 1.0)
    tb2, back_path = tunnel(BACK, rad_back, 2.0)
    # all overlapping cutters go into ONE operand (self-intersection on) and are subtracted in one exact boolean;
    # sequential booleans silently skipped the chamber/alcove where they overlapped the tunnel end caps
    ch = blob(*CHAMBER, 5, sub=4, amp=0.18); al = blob(*ALCOVE, 6, sub=3, amp=0.15)
    for b_, fz in ((ch, CHAMBER[0].z - 1.25), (al, ALCOVE[0].z - 0.7)):      # flat floors without folding the mesh
        for v in b_.verts:
            if v.co.z < fz: v.co.z = fz
    cut_bm = merged([tb, tb2, ch, al])
    me = bpy.data.meshes.new("CaveCutter"); cut_bm.to_mesh(me); cut_bm.free(); me.materials.append(C["inner"])
    co = bpy.data.objects.new("CaveCutter", me); col.objects.link(co); co.parent = root; co.hide_render = True; cut_objs = [co]
    m = rock.modifiers.new("Carve", "BOOLEAN"); m.operation = "DIFFERENCE"; m.solver = "EXACT"; m.object = co
    if hasattr(m, "material_mode"): m.material_mode = "TRANSFER"
    m.use_self = True; m.use_hole_tolerant = True
    dg = bpy.context.evaluated_depsgraph_get()
    new_me = bpy.data.meshes.new_from_object(rock.evaluated_get(dg)); old_me = rock.data
    rock.modifiers.clear(); rock.data = new_me; bpy.data.meshes.remove(old_me)
    for co in cut_objs: bpy.data.objects.remove(co, do_unlink=True)
    rock.data.shade_smooth()
    bvh = BVHTree.FromObject(rock, bpy.context.evaluated_depsgraph_get())
    def ray(o, d):                       # root-local ray -> (hit, normal) in root-local
        hit = bvh.ray_cast(Vector(o), Vector(d).normalized())
        return (hit[0], hit[1]) if hit[0] is not None else (None, None)

    # ---- seabed apron around the hill
    bm = bmesh.new(); NR, NA = 24, 120; rings = []
    for r in range(NR + 1):
        s = 0.8 + (1.7 - 0.8) * r / NR; ring = []
        for a in range(NA):
            ph = a / NA * math.tau; x, y = ROCK_C.x + ROCK_R.x * s * math.cos(ph), ROCK_C.y + ROCK_R.y * s * math.sin(ph)
            z = 0.0 if r == NR else (0.35 * max(0.0, (1.7 - s) / 0.9) ** 1.5 + 0.05 * nz((x, y, 1.0), 0.8)) - (0.4 if s < 0.95 else 0.0)
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)
    for r in range(NR):
        for a in range(NA):
            bm.faces.new((rings[r][a], rings[r][(a + 1) % NA], rings[r + 1][(a + 1) % NA], rings[r + 1][a]))
    put("Seabed", bm, C["sed"])

    # ---- inside: sand floor patches, ceiling spikes, glowing patches, boulders, guideline, lost gear
    sand, spikes, glow, glow_pts = [], [], [], []
    inside = catmull(MAIN, 6)[6:] + [CHAMBER[0] + Vector((rnd.uniform(-2.5, 2.5), rnd.uniform(-2, 2), 0)) for _ in range(14)] + catmull(BACK, 6)[:-6]
    n_main = len(catmull(MAIN, 6)[6:])
    for k, p in enumerate(inside):
        h, n = ray(p, (0, 0, -1))
        if h is not None and n.z > 0.6 and n_main <= k < n_main + 14 and k % 2 == 0:    # thin sand drifts in the chamber only
            pts = []
            for q in range(16):
                a = q / 16 * math.tau; rr = rnd.uniform(0.35, 0.8) * (1 + 0.3 * nz((a, k, 1), 1.5))
                x, y = h.x + rr * 1.6 * math.cos(a), h.y + rr * 1.3 * math.sin(a); hh, _ = ray((x, y, h.z + 0.6), (0, 0, -1))
                pts.append(Vector((x, y, (hh.z if hh is not None and abs(hh.z - h.z) < 0.4 else h.z) + 0.015)))
            b = bmesh.new(); vs = [b.verts.new(v) for v in pts]; b.faces.new(vs)
            r_ = bmesh.ops.extrude_face_region(b, geom=b.faces[:]); bmesh.ops.translate(b, vec=(0, 0, -0.04), verts=[e for e in r_["geom"] if isinstance(e, bmesh.types.BMVert)])
            sand.append(b)
        h, n = ray(p, (0, 0, 1))
        if h is not None and n.z < -0.4:
            for _ in range(3):
                q0 = h + Vector((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), 0.3)); hh, nn = ray(q0, (0, 0, 1))
                if hh is None: continue
                ln = rnd.uniform(0.15, 0.6); sp = bmesh.new(); bmesh.ops.create_cone(sp, cap_ends=True, segments=7, radius1=ln * 0.18, radius2=0.004, depth=ln)
                bmesh.ops.transform(sp, matrix=Matrix.Translation(hh + Vector((0, 0, 0.02))) @ Matrix.Rotation(math.pi, 4, "X") @ Matrix.Translation((0, 0, ln / 2)), verts=sp.verts)
                spikes.append(sp)
        if k % 3 == 0:
            a = rnd.uniform(0, math.tau); d = Vector((math.cos(a), math.sin(a), rnd.uniform(-0.2, 0.5)))
            hh, nn = ray(p, d)
            if hh is not None and (hh - p).length < 4.0:
                cl = []
                for q in range(rnd.randint(5, 9)):
                    off = nn.orthogonal().normalized(); off2 = nn.cross(off)
                    c_ = hh + off * rnd.uniform(-0.3, 0.3) + off2 * rnd.uniform(-0.3, 0.3)
                    cl.append(blob(c_ + nn * 0.01, (rnd.uniform(0.03, 0.09),) * 2 + (0.02,), 50 + k * 10 + q, sub=1, amp=0.2))
                    bmesh.ops.transform(cl[-1], matrix=Matrix.Translation(c_) @ nn.to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Translation(-c_), verts=cl[-1].verts)
                glow += cl; glow_pts.append(hh + nn * 0.3)
    put("SandInside", merged(sand), C["sed"])
    put("CeilingSpikes", merged(spikes), C["inner"])
    put("GlowPatches", merged(glow), C["glow"])
    cc = CHAMBER[0]; boulders = []
    for k, (dx, dy, s_) in enumerate(((-1.6, 1.6, 0.9), (1.2, 2.0, 0.7), (-0.4, -1.4, 0.6), (2.0, -0.6, 0.55), (-2.2, -0.4, 0.5))):
        h, _ = ray(cc + Vector((dx, dy, 0)), (0, 0, -1))
        if h is not None: boulders.append(blob(h + Vector((0, 0, s_ * 0.55)), (s_, s_ * 0.85, s_ * 0.7), 80 + k, sub=3, amp=0.3))
    put("Boulders", merged(boulders), C["boulder"])
    # guideline: from outside the main entrance, along the floor into the chamber and to the alcove, with pegs
    gl_pts = []
    for p in catmull(MAIN, 4)[1:] + [cc + Vector((0.6, 1.8, 0)), ALCOVE[0] + Vector((0, -0.4, 0))]:
        h, _ = ray(Vector(p) + Vector((0, 0, 0.5)), (0, 0, -1))
        if h is not None: gl_pts.append(h + Vector((0, 0, 0.12)))
    pegs = [cyl(0.02, 0.25, 6, (p.x, p.y, p.z - 0.05)) for p in gl_pts[::3]]
    put("Guideline", merged([tube(catmull(gl_pts, 3), 0.008, sides=5)] + pegs), C["rope"])
    h, _ = ray(cc + Vector((1.4, -1.6, 0)), (0, 0, -1))
    if h is not None:
        tk = Matrix.Translation(h + Vector((0, 0, 0.1))) @ Matrix.Rotation(math.radians(88), 4, "X") @ Matrix.Rotation(0.6, 4, "Y")
        put("LostTank", merged([lathe([(0.0, -0.32), (0.09, -0.3), (0.09, 0.28), (0.05, 0.33), (0.02, 0.36), (0.0, 0.36)], 16, tk)]), C["tank"])
        put("LostGear", merged([cyl(0.025, 0.08, 8, (0, 0, 0), tk @ Matrix.Translation((0, 0, 0.4))),
                                box((0.18, 0.5, 0.012), (0, 0, 0), Matrix.Translation(h + Vector((-0.6, 0.3, 0.03))) @ Matrix.Rotation(0.4, 4, "Z")),
                                cyl(0.035, 0.22, 10, (0, 0, 0), Matrix.Translation(h + Vector((0.5, 0.5, 0.05))) @ Matrix.Rotation(math.radians(90), 4, "Y"))]), C["gear"])

    # ---- outside: corals, glass sponges, crinoids, urchins, anemones, boulders around the base
    cor, spo, cri, urc, ane, bld = [], [], [], [], [], []
    k = 0
    while k < 150:
        x, y = ROCK_C.x + rnd.uniform(-1, 1) * ROCK_R.x * 1.1, ROCK_C.y + rnd.uniform(-1, 1) * ROCK_R.y * 1.1; k += 1
        h, n = ray((x, y, 12.0), (0, 0, -1))
        if h is None or n.z < 0.45: continue
        if any((h - p).length < 2.2 for p in (MAIN[1], BACK[-2])): continue       # keep the entrances clear
        r = rnd.random()
        if r < 0.3: cor.append(coral(h, 900 + k, rnd.uniform(0.8, 1.5)))
        elif r < 0.45: spo.append(glass_sponge(h, rnd.uniform(0.3, 0.7), k))
        elif r < 0.6: cri.append(crinoid(h, k))
        elif r < 0.75: urc.append(urchin(h, k))
        else: ane.append(anemone(h, n, rnd.uniform(0.7, 1.3)))
    for k in range(18):
        a = rnd.uniform(0, math.tau); s = rnd.uniform(1.0, 1.45)
        x, y = ROCK_C.x + ROCK_R.x * s * math.cos(a), ROCK_C.y + ROCK_R.y * s * math.sin(a); sz = rnd.uniform(0.3, 1.1)
        if any((Vector((x, y, 0)) - p).length < 2.5 for p in (MAIN[0], MAIN[1], BACK[-1], BACK[-2])): continue
        bld.append(blob(Vector((x, y, sz * 0.25)), (sz, sz * 0.8, sz * 0.6), 300 + k, sub=3, amp=0.3))
    put("Corals", merged(cor), C["coral"])
    put("GlassSponges", merged(spo), C["sponge"])
    put("Crinoids", merged(cri), C["crinoid"])
    put("Urchins", merged(urc), C["urchin"])
    put("Anemones", merged(ane), C["anem"])
    put("OuterBoulders", merged(bld), C["boulder"])

    # ---- sockets
    def floor_at(p):
        h, _ = ray(Vector(p) + Vector((0, 0, 0.5)), (0, 0, -1)); return h if h is not None else Vector(p)
    sock("Hide_Alcove", floor_at(ALCOVE[0]))
    sock("Hide_Chamber", floor_at(cc + Vector((-2.7, 0.5, 0))))          # inside the chamber, behind the big boulder (seen from the main tunnel)          # behind the big boulder, seen from the main tunnel
    sock("Entrance_Main", floor_at(MAIN[1]), Vector((1, 0, 0)))
    sock("Entrance_Back", floor_at(BACK[-2]), Vector((-1, -0.3, 0)))
    sq = catmull(BACK, 10)[int(SQUEEZE_T * (len(catmull(BACK, 10)) - 1))]
    sock("Squeeze", floor_at(sq))
    for i, p in enumerate(glow_pts[:4]): sock(f"Glow_{i + 1}", p)
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
        if "bake_export" in globals():
            return bake_export(ROOT, SM_NAME, "SeaCave", nobake={"M_Cave_Glow"}, size=4096)
        return export_unreal(ROOT, SM_NAME, (0, 0, 0))
    finally:
        for o in mine: o.name = o.name + SFX
        for other, plain in parked: other.name = plain


mats()
build()
print("CAVE built")
