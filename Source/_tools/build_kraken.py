# Kraken (2026-11-09): monster-ified kraken with its own rig + KR_Idle / KR_Swim / KR_Attack.
# Faces -Y (arms forward), mantle toward +Y. Same horror style as Gigantura v3.
# exec after mk.py, rig.py, horror.py, horror2.py
from mathutils import Quaternion
from mathutils.bvhtree import BVHTree
random.seed(51)
RIG_LOC = (-6.5, -12.5, 1.6)
col = get_col("Kraken", clear=True)
for nm in ("Kraken_Rig", "SK_Kraken_Body"):
    o = bpy.data.objects.get(nm)
    if o: bpy.data.objects.remove(o, do_unlink=True)


def _m(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)
M_skin, M_sucker, M_hook, M_flesh = _m("M_KrX_Skin"), _m("M_KrX_Sucker"), _m("M_KrX_Hook"), _m("M_KrX_Flesh")
M_beak, M_eye, M_iris, M_pupil, M_fin = _m("M_KrX_Beak"), _m("M_KrX_Eye"), _m("M_KrX_Iris"), _m("M_KrX_Pupil"), _m("M_KrX_Fin")


def orient(n):
    return n.to_track_quat("Z", "Y").to_matrix().to_4x4()


def resample3(pts, n):
    L = [0.0]
    for a, b in zip(pts, pts[1:]): L.append(L[-1] + (b - a).length)
    out = []
    for k in range(n):
        d = L[-1] * k / (n - 1)
        for j in range(len(pts) - 1):
            if L[j] <= d <= L[j + 1] + 1e-9:
                t = (d - L[j]) / max(1e-9, L[j + 1] - L[j]); out.append(pts[j] + (pts[j + 1] - pts[j]) * t); break
    return out, L[-1]


# ---------------- limb paths (rest pose) ----------------
LIMBS = []          # dict(name, pts, radius fn, club)
def grow_path(start, d0, o, L, curl_k, curl_sign, droop, wobble, seed, steps=60):
    """Integrate a limb centreline: gentle droop, then a tightening curl near the tip."""
    p = start.copy(); d = d0.normalized(); raw = [p.copy()]
    ds = L / steps
    for k in range(1, steps + 1):
        t = k / steps
        side = d.cross(o)
        if side.length < 1e-6: side = d.orthogonal()
        side.normalize()
        kappa = curl_sign * curl_k * smoothstep(0.45, 1.0, t) ** 1.3 + 0.25 * curl_sign
        d = Quaternion(side, kappa * ds) @ d
        d = Quaternion(Vector((1, 0, 0)), droop * ds) @ d                                   # sag
        d = Quaternion(o, wobble * math.sin(t * 6 + seed) * ds) @ d
        p = p + d * ds; raw.append(p.copy())
    return raw

for i in range(8):
    th = math.pi / 8 + i * math.pi / 4
    o = Vector((math.cos(th), 0, math.sin(th)))
    L = random.uniform(2.5, 3.0); seed = i * 1.7
    raw = grow_path(Vector((0, -0.3, 0)) + o * 0.2, o * 0.75 + Vector((0, -1, 0)), o, L,
                    random.uniform(4.0, 6.5), random.choice((1, 1, -1)), 0.12 + 0.12 * (1 - math.sin(th)), 0.9, seed)
    pts, _ = resample3(raw, 80)
    LIMBS.append(dict(name=f"arm{i + 1}", pts=pts, th=th, rad=lambda t: 0.115 * (1 - t) ** 0.95 + 0.005, club=False))
for j, th in enumerate((-math.pi / 2 - 0.28, -math.pi / 2 + 0.28)):
    o = Vector((math.cos(th), 0, math.sin(th)))
    L = 4.0; raw = []
    for k in range(25):
        t = k / 24
        p = Vector((0, -0.3, 0)) + o * 0.11
        p += Vector((0, -1, 0)) * L * 0.92 * t + o * (L * 0.18 * t) + Vector((0, 0, -1)) * 0.5 * L * t * t * 0.5
        p += Vector((1, 0, 0)) * 0.06 * math.sin(t * 7 + j * 2) * t
        raw.append(p)
    pts, _ = resample3(catmull(raw, 4), 96)
    def club_r(t):
        r = 0.045 * (1 - t) ** 0.7 + 0.004
        if t > 0.78: r *= 1 + 1.3 * math.sin(math.pi * min(1.0, (t - 0.78) / 0.2)) ** 1.5
        return r
    LIMBS.append(dict(name="tent" + ("L" if j else "R"), pts=pts, th=th, rad=club_r, club=True))


def limb_frames(pts):
    fr = []
    for k, p in enumerate(pts):
        a = pts[max(0, k - 1)]; b = pts[min(len(pts) - 1, k + 1)]
        T_ = (b - a).normalized()
        inn = Vector((0, p.y, -0.1)) - p
        inn = (inn - T_ * inn.dot(T_))
        if inn.length < 1e-6: inn = T_.orthogonal()
        inn.normalize()
        fr.append((T_, inn, T_.cross(inn).normalized()))
    return fr


def build_limb(lb):
    pts = lb["pts"]; fr = limb_frames(pts); n = len(pts); sides = 12
    bm = bmesh.new(); kl = bm.verts.layers.float.new("kside")
    rings = []
    for k, p in enumerate(pts):
        t = k / (n - 1); r = lb["rad"](t); T_, I, K = fr[k]
        ring = []
        for s in range(sides):
            ph = s / sides * math.tau; c = math.cos(ph)
            rr = r * (1 - 0.28 * max(0.0, c)) * (1 + 0.05 * math.sin(t * 140) * (1 - max(0.0, c)))
            v = bm.verts.new(p + (I * c + K * math.sin(ph)) * rr)
            v[kl] = smoothstep(0.1, 0.8, c); ring.append(v)
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for s in range(sides):
            bm.faces.new((r0[s], r0[(s + 1) % sides], r1[(s + 1) % sides], r1[s]))
    bm.faces.new(list(reversed(rings[0]))); tipv = bm.verts.new(pts[-1] + fr[-1][0] * 0.01); tipv[kl] = 0.5
    for s in range(sides): bm.faces.new((rings[-1][s], rings[-1][(s + 1) % sides], tipv))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    wrinkle_bm(bm, 0.003, 40, hash(lb["name"]) % 17)
    # suckers (+ hooks on big ones and on the club)
    suck = bmesh.new(); hooks = bmesh.new()
    d = 0.06; row = 0
    total = sum((pts[k + 1] - pts[k]).length for k in range(n - 1))
    acc = 0.0; k = 0
    while k < n - 1:
        seg = (pts[k + 1] - pts[k]).length
        acc += seg; k += 1
        t = k / (n - 1)
        if acc < d or t < 0.04 or t > 0.97: continue
        r = lb["rad"](t); acc = 0.0
        on_club = lb["club"] and t > 0.78
        if lb["club"] and not on_club and t > 0.08: continue          # bare tentacle stalk
        rs = r * (0.42 if not on_club else 0.3)
        d = max(0.024, rs * 2.7)
        T_, I, K = fr[k]
        for ph in ((0.38, -0.38) if not on_club else (0.55, 0.0, -0.55)):
            if not on_club and ((row % 2) != (ph > 0)): continue
            N = (I * math.cos(ph) + K * math.sin(ph)).normalized()
            base = pts[k] + N * r * (1 - 0.28 * max(0.0, math.cos(ph))) * 0.93
            prof_ = [(0, rs * 0.15), (rs * 0.82, rs * 0.45), (rs, rs * 0.55), (rs * 1.05, rs * 0.2), (rs * 0.9, -rs * 0.3)]
            part = lathe(prof_, 7, T(*base) @ orient(N))
            tmp = bpy.data.meshes.new("_s"); part.to_mesh(tmp); part.free(); suck.from_mesh(tmp); bpy.data.meshes.remove(tmp)
            if on_club or rs > 0.03:                                     # ring of hooked teeth on the sucker rim
                M0 = T(*base) @ orient(N)
                nt = 6 if on_club else 5
                for q in range(nt):
                    a_ = q / nt * math.tau + random.uniform(0, 0.4)
                    rim = M0 @ Vector((math.cos(a_) * rs * 0.8, math.sin(a_) * rs * 0.8, rs * 0.5))
                    dv = ((M0.to_3x3() @ Vector((-math.cos(a_), -math.sin(a_), 1.2))).normalized())
                    hk = xf(needle(rs * 0.12, rs * (0.75 if on_club else 0.5), (0, 0, 0), 0, 0, 0.5, segs=4), T(*rim) @ orient(dv))
                    tmp = bpy.data.meshes.new("_h"); hk.to_mesh(tmp); hk.free(); hooks.from_mesh(tmp); bpy.data.meshes.remove(tmp)
        row += 1
    return bm, suck, hooks


# ---------------- armature ----------------
bones = [("kr_root", (0, 0, 0), (0, 0.3, 0), None, False),
         ("kr_head", (0, 0, 0), (0, -0.35, 0), "kr_root", True),
         ("kr_mantle_01", (0, 0, 0), (0, 0.6, 0), "kr_root", True),
         ("kr_mantle_02", (0, 0.6, 0), (0, 1.2, 0), "kr_mantle_01", True),
         ("kr_mantle_03", (0, 1.2, 0), (0, 1.9, 0), "kr_mantle_02", True)]
CHAINS = {}
for lb in LIMBS:
    nb_ = 6 if not lb["club"] else 8
    idx = [round(k * (len(lb["pts"]) - 1) / nb_) for k in range(nb_ + 1)]
    names = []
    for k in range(nb_):
        nm = f"kr_{lb['name']}_{k + 1}"
        bones.append((nm, tuple(lb["pts"][idx[k]]), tuple(lb["pts"][idx[k + 1]]), names[-1] if names else "kr_head", True))
        names.append(nm)
    CHAINS[lb["name"]] = names
rig = make_armature(col, "Kraken_Rig", bones, (0, 0, 0))

# ---------------- mantle + head ----------------
KEYS = [(-0.37, 0, 0, 0), (-0.365, 0.08, 0.08, 0), (-0.34, 0.2, 0.19, 0), (-0.25, 0.29, 0.27, 0.02), (-0.12, 0.31, 0.29, 0.03),
        (-0.02, 0.27, 0.25, 0.03), (0.06, 0.29, 0.28, 0.03), (0.4, 0.34, 0.32, 0.05), (0.9, 0.35, 0.33, 0.06), (1.35, 0.29, 0.28, 0.05),
        (1.7, 0.18, 0.18, 0.03), (1.9, 0.065, 0.065, 0.02), (1.96, 0, 0, 0.02)]
def kprof(y):
    for a, b in zip(KEYS, KEYS[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0]); return [a[i] + (b[i] - a[i]) * t for i in range(4)]
    return list(KEYS[0]) if y < KEYS[0][0] else list(KEYS[-1])
def mradial(y, a, x, z):
    s = 1.0
    if y > 0.08: s += 0.025 * math.sin(a * 9 + y * 4) * min(1.0, (y - 0.08) / 0.3) + 0.02 * math.sin(y * 22 + a * 2) ** 3
    if -0.04 < y < 0.06: s -= 0.06 * math.sin(math.pi * (y + 0.04) / 0.1)                 # mantle collar
    return s
body = finish(col, "SK_Kraken_Body", loft_fn(smooth_stations(KEYS, 110), 56, mradial), M_skin)
subdivide_displace(body, levels=0, lumps=0.012, lump_scale=4, wrinkle=0.003, wrinkle_scale=45, seed=4)
me = body.data
bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [p.vertices[:] for p in me.polygons])
def hit(origin, target):
    o_ = Vector(origin); d_ = (Vector(target) - o_).normalized()
    loc, nor, _, _ = bvh.ray_cast(o_, d_); return loc.copy(), nor.normalized()

SCULPT, EYES, MASK = [], [], {"flesh": [], "wound": []}
for sx in (-1, 1):
    p, n = hit((sx * 1.0, -0.3, 0.25), (0, -0.15, 0.02))
    SCULPT += [(p, Vector((0.12, 0.12, 0.1)), -0.065), (p + Vector((sx * 0.0, 0.03, 0.12)), Vector((0.13, 0.09, 0.045)), 0.05),
               (p + Vector((0, 0.13, -0.06)), Vector((0.1, 0.1, 0.07)), -0.03)]
    EYES.append((p - n * 0.04, 0.1, (n + Vector((0, -0.9, 0))).normalized(), True, n))
    MASK["flesh"].append((p, 0.1))
for k in range(10):                                                      # tumour lumps on the mantle
    yv = random.uniform(0.3, 1.4); a = random.uniform(-0.6, 2.4); pr = kprof(yv)
    p, n = hit((math.cos(a) * 1.0, yv, pr[3] + math.sin(a) * 1.0), (0, yv, pr[3]))
    r = random.uniform(0.04, 0.09)
    SCULPT.append((p, Vector((r, r * 1.3, r)), r * 0.7))
for yv, ang, r in [(-0.2, 70, 0.022), (-0.1, 95, 0.018), (-0.16, 115, 0.02), (-0.27, 100, 0.014), (-0.05, 75, 0.013), (0.12, 105, 0.016)]:
    a = math.radians(ang); pr = kprof(yv)
    p, n = hit((math.cos(a) * 1.0, yv, pr[3] + math.sin(a) * 1.0), (0, yv, pr[3]))
    SCULPT.append((p, Vector((r, r, r)) * 1.5, -r * 0.9))
    look = (n + Vector((random.uniform(-0.6, 0.6), random.uniform(-0.7, 0.3), random.uniform(-0.4, 0.4)))).normalized()
    EYES.append((p - n * r * 0.3, r, look, False, n)); MASK["flesh"].append((p, r * 1.6))
for k in range(3):                                                       # claw gashes on the mantle
    for j in range(4):                                                    # each gash = a staggered chain of thin cuts
        p, n = hit((1.0, 0.5 + k * 0.09 + j * 0.035, 0.5 - j * 0.12), (0, 0.55 + k * 0.09 + j * 0.035, 0.05 - j * 0.1))
        w = 0.016 * (1 - abs(j - 1.5) / 3)
        SCULPT.append((p, Vector((0.02, w * 1.2, 0.07)), -0.022)); MASK["wound"].append((p, Vector((0.025, w * 1.6, 0.085))))
for v in me.vertices:
    dd = 0.0
    for c, rad, amt in SCULPT:
        q = v.co - c; e = (q.x / rad.x) ** 2 + (q.y / rad.y) ** 2 + (q.z / rad.z) ** 2
        if e < 9: dd += amt * math.exp(-e)
    if dd: v.co += v.normal * dd
me.update()
ks = me.attributes.new("kside", "FLOAT", "POINT")
for v in me.vertices:
    pr = kprof(max(-0.369, min(1.959, v.co.y)))
    a = math.atan2((v.co.z - pr[3]) / max(1e-3, pr[2]), v.co.x / max(1e-3, pr[1]))
    ks.data[v.index].value = 0.65 * max(0.0, -math.sin(a)) ** 1.5

parts = []
def add(name, bm, material):
    o_ = finish(col, name, bm, material); parts.append(o_); return o_
for sx, tears in ((1, ((5, 0.5), (11, 0.35))), (-1, ((8, 0.6),))):    # ragged side fins on the mantle tail
    N = 14
    base = [(1.15 + 0.75 * i / (N - 1), sx * kprof(1.15 + 0.75 * i / (N - 1))[1] * 0.9) for i in range(N)]
    tips = [(b[0] + 0.12, b[1] + sx * (0.08 + 0.32 * math.sin(math.pi * (0.15 + 0.85 * i / (N - 1))))) for i, b in enumerate(base)]
    mb, rb = ray_fin(base, tips, 0.012, RY(90), rows=6, ray_every=2, scallop=0.2, tears=tears, ray_r=0.006)
    add(f"kr_fin_{sx}", mb, M_fin); add(f"kr_finrays_{sx}", rb, M_fin)
bvh2 = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [p.vertices[:] for p in me.polygons])
for k in range(16):                                                      # hooked bony spines along the mantle ridge
    yv = 0.1 + k * 0.1; pr = kprof(yv)
    if pr[1] < 0.08: break
    for off in ((0.0,) if k % 2 else (-0.5, 0.5)):
        a = math.pi / 2 + off
        loc, n, _, _ = bvh2.ray_cast(Vector((math.cos(a), yv, pr[3] + math.sin(a))), -Vector((math.cos(a), 0, math.sin(a))))
        if loc is None: continue
        env = math.sin(math.pi * min(1.0, (yv - 0.05) / 1.6))
        L = (0.05 + 0.13 * env) * random.uniform(0.7, 1.2)
        add(f"kr_spine_{k}_{off}", xf(needle((0.012 + 0.012 * env), L, (0, 0, 0), 0, 0, 0.35, segs=7),
                                     T(*(loc - n * 0.01)) @ orient((n + Vector((0, 0.9, 0))).normalized())), M_hook)
        MASK["flesh"].append((loc.copy(), 0.03 + 0.02 * env))
add("kr_siphon", tube(catmull([Vector((0, -0.04, -0.2)), Vector((0, -0.16, -0.24)), Vector((0, -0.27, -0.25))], 4),
                      lambda s: 0.055 - 0.02 * s, up=(0, 0, 1), sides=12), M_skin)
bpy.ops.object.select_all(action="DESELECT")
for o_ in [body] + parts: o_.select_set(True)
bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
body.parent = rig; body.matrix_parent_inverse = Matrix.Identity(4)
bpy.context.view_layer.update()
distance_weights(body, rig, ["kr_head", "kr_mantle_01", "kr_mantle_02", "kr_mantle_03"], falloff=3.0, top=2)

# ---------------- limbs + web ----------------
limb_objs = []
for lb in LIMBS:
    bm, suck, hooks = build_limb(lb)
    o_ = finish(col, "kr_" + lb["name"], bm, M_skin)
    for bmx, mt in ((suck, M_sucker), (hooks, M_hook)):
        if len(bmx.verts):
            tmp = finish(col, "_tmp", bmx, mt)
            bpy.ops.object.select_all(action="DESELECT"); o_.select_set(True); tmp.select_set(True)
            bpy.context.view_layer.objects.active = o_; bpy.ops.object.join()
        else: bmx.free()
    o_.parent = rig; o_.matrix_parent_inverse = Matrix.Identity(4); bpy.context.view_layer.update()
    distance_weights(o_, rig, CHAINS[lb["name"]], falloff=3.0, top=2)
    b0 = lb["pts"][0]
    blend_region(o_, "kr_head", lambda c, b0=b0: max(0.0, min(1.0, 1 - (c - b0).length / 0.15)))
    limb_objs.append(o_)
arms = [lb for lb in LIMBS if not lb["club"]]
for i in range(8):                                                       # webbing between neighbouring arms
    A, B = arms[i]["pts"], arms[(i + 1) % 8]["pts"]
    bm = bmesh.new(); kl = bm.verts.layers.float.new("kside"); grid = []
    NU, NS = 16, 10
    for u in range(NU):
        row_ = []
        for s in range(NS):
            sv = s / (NS - 1)
            tmax = 0.36 - 0.14 * math.sin(math.pi * sv)
            k = min(len(A) - 1, int(tmax * (len(A) - 1) * u / (NU - 1)))
            pa, pb = A[k], B[k]
            p = pa.lerp(pb, sv)
            sag = math.sin(math.pi * sv) * (0.03 + 0.08 * u / (NU - 1))
            p += Vector((0, 0.25, 0)) * sag - Vector((p.x, 0, p.z)).normalized() * sag * 0.5
            v = bm.verts.new(p); v[kl] = 0.55; row_.append(v)
        grid.append(row_)
    for u in range(NU - 1):
        for s in range(NS - 1):
            bm.faces.new((grid[u][s], grid[u][s + 1], grid[u + 1][s + 1], grid[u + 1][s]))
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.008)
    wrinkle_bm(bm, 0.003, 35, i)
    o_ = finish(col, f"kr_web_{i}", bm, M_skin)
    o_.parent = rig; o_.matrix_parent_inverse = Matrix.Identity(4); bpy.context.view_layer.update()
    distance_weights(o_, rig, CHAINS[arms[i]["name"]][:2] + CHAINS[arms[(i + 1) % 8]["name"]][:2] + ["kr_head"], falloff=3.0, top=2)
    limb_objs.append(o_)
bpy.ops.object.select_all(action="DESELECT")
for o_ in [body] + limb_objs: o_.select_set(True)
bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
body.data.shade_smooth()

# ---------------- rigid head parts: eyes, beak, tooth ring ----------------
for k, (ctr, r, look, main, n) in enumerate(EYES):
    rigid_bm_to_group(body, uvsphere(r, T(*ctr), 24 if main else 14, 12 if main else 8), M_eye, "kr_head")
    rot = orient(look)
    rigid_bm_to_group(body, uvsphere(r * 0.66, T(*(ctr + look * r * 0.82)) @ rot @ Matrix.Diagonal((1, 1, 0.3, 1)), 18, 8), M_iris, "kr_head")
    rigid_bm_to_group(body, uvsphere(r * 0.6, T(*(ctr + look * r * 0.9)) @ rot @ Matrix.Diagonal((0.95, 0.2, 0.22, 1) if main else (0.5, 0.5, 0.22, 1)), 14, 6), M_pupil, "kr_head")
    rigid_bm_to_group(body, wrinkle_bm(torus(r * 0.98, r * 0.17, 24 if main else 14, 8, T(*(ctr + n * r * 0.5)) @ orient(n)), r * 0.05, 90, k), M_skin, "kr_head")
mc = Vector((0, -0.36, 0))
rigid_bm_to_group(body, wrinkle_bm(torus(0.085, 0.03, 24, 10, T(*mc) @ RX(90)), 0.006, 50, 2), M_flesh, "kr_head")
rigid_bm_to_group(body, uvsphere(0.07, T(0, -0.33, 0), 16, 10), M_flesh, "kr_head")
for sz, sgn in ((0.05, 1), (0.04, -1)):                                  # parrot beak, upper + lower
    b = needle(sz, 0.15 if sgn > 0 else 0.11, (0, 0, 0), 0, 0, 0.0, segs=12)
    for v in b.verts: v.co.y += -sgn * 0.5 * (v.co.z ** 2) / 0.15            # hook downward / upward
    rigid_bm_to_group(body, xf(b, T(0, -0.37, sgn * 0.012) @ RX(90) @ Matrix.Diagonal((1.0, 0.7, 1, 1))), M_beak, "kr_head")
for k in range(16):
    a = k / 16 * math.tau; q = mc + Vector((math.cos(a), 0, math.sin(a))) * 0.075
    dv = (mc + Vector((0, -0.05, 0)) - q).normalized()
    rigid_bm_to_group(body, xf(needle(0.006, random.uniform(0.035, 0.06), (0, 0, 0), 0, 0, 0.3, segs=5), T(*q) @ orient(dv)), M_hook, "kr_head")
mod = body.modifiers.new("Armature", "ARMATURE"); mod.object = rig


# ---------------- animation ----------------
def bend_q(bname, world_axis, ang):
    R = rig.data.bones[bname].matrix_local.to_3x3()
    ax = (R.inverted() @ world_axis)
    if ax.length < 1e-6: return Quaternion()
    return Quaternion(ax.normalized(), ang)
LIMB_AX = {}
for lb in LIMBS:
    o = Vector((math.cos(lb["th"]), 0, math.sin(lb["th"])))
    for bn in CHAINS[lb["name"]]:
        b = rig.data.bones[bn]; d = (b.tail_local - b.head_local).normalized()
        LIMB_AX[bn] = (o.cross(d).normalized(), o)              # (curl-inward axis, side-sway axis)


def pose_limbs(f, fn):
    for lb in LIMBS:
        for k, bn in enumerate(CHAINS[lb["name"]]):
            curl, side = fn(lb, k, len(CHAINS[lb["name"]]))
            ca, sa = LIMB_AX[bn]
            q = bend_q(bn, ca, curl) @ bend_q(bn, sa, side)
            key(rig.pose.bones[bn], f, rot=q.to_euler("XYZ"))


def mantle(f, ang_z, ang_x=0.0):
    for k, bn in enumerate(("kr_mantle_01", "kr_mantle_02", "kr_mantle_03")):
        key(rig.pose.bones[bn], f, rot=(ang_x * (k + 1) * 0.5, 0, ang_z * (k + 1) * 0.6))


def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

bpy.context.view_layer.objects.active = rig
new_action(rig, "KR_Idle")
F = 80
for f in range(F + 1):
    t = f / F
    pose_limbs(f + 1, lambda lb, k, n: (math.radians(5 + 2.5 * k) * math.sin(math.tau * (t - 0.11 * k) + lb["th"] * 2.3),
                                        math.radians(4 + 1.5 * k) * math.sin(math.tau * (t - 0.08 * k) + lb["th"] * 1.3 + 1.0)))
    mantle(f + 1, math.radians(3) * math.sin(math.tau * t), math.radians(2) * math.sin(math.tau * t + 1))
    key(rig.pose.bones["kr_head"], f + 1, rot=(math.radians(2) * math.sin(math.tau * t), 0, 0))
rig.animation_data.action.frame_range = (1, F + 1)

new_action(rig, "KR_Swim")
F = 40
for f in range(F + 1):
    t = f / F
    def swim(lb, k, n):
        w = math.sin(math.tau * t - 0.6 * k)
        base = math.radians(16 if not lb["club"] else 6)
        return (base * w * (1 - 0.06 * k), math.radians(3) * math.sin(math.tau * t * 2 - 0.4 * k + lb["th"]))
    pose_limbs(f + 1, swim)
    mantle(f + 1, math.radians(5) * math.sin(math.tau * t + 0.5), math.radians(4) * math.sin(math.tau * t))
    key(rig.pose.bones["kr_head"], f + 1, rot=(0, 0, 0))
rig.animation_data.action.frame_range = (1, F + 1)

new_action(rig, "KR_Attack")
F = 30
for f in range(F + 1):
    open_ = ease(f / 9) * (1 - ease((f - 10) / 5))
    grab = ease((f - 10) / 6) * (1 - ease((f - 22) / 8) * 0.6)
    def atk(lb, k, n):
        if lb["club"]:
            return (math.radians(-10) * open_ + math.radians(14) * grab * (1 if k < 3 else -0.4), 0.0)
        return (math.radians(-22 + 2 * k) * open_ + math.radians(12 + 5 * k) * grab, 0.0)
    pose_limbs(f + 1, atk)
    mantle(f + 1, 0.0, math.radians(-6) * open_ + math.radians(4) * grab)
    lunge = -1.0 * ease((f - 9) / 7) + 0.2 * open_ * (1 - ease((f - 9) / 3))
    key(rig.pose.bones["kr_root"], f + 1, loc=(0, lunge, 0))
    key(rig.pose.bones["kr_head"], f + 1, rot=(math.radians(-8) * grab, 0, 0))
rig.animation_data.action.frame_range = (1, F + 1)
_act = bpy.data.actions["KR_Swim"]
rig.animation_data.action = _act
if hasattr(rig.animation_data, "action_slot") and len(_act.slots):
    rig.animation_data.action_slot = _act.slots[0]
rig.location = RIG_LOC


# ---------------- shaders ----------------
def kraken_skin(mat):
    nb = NB(mat)
    a = nb.n("ShaderNodeAttribute", attribute_name="kside"); side = a.outputs["Fac"]
    P = nb_warp(nb, 0.03, 8.0)
    col_ = nb.mix((0.03, 0.01, 0.014), (0.2, 0.1, 0.1), side)
    blot = nb.noise(3.0, 6, 0.6, distortion=0.5)
    col_ = nb.mix(col_, (0.07, 0.012, 0.035), nb.math("MULTIPLY", nb_map(nb, blot.outputs["Fac"], 0.5, 0.66), nb.math("SUBTRACT", 1.0, side)))
    mott = nb.noise(10.0, 6, 0.65)
    col_ = nb.mix(col_, nb.ramp(mott.outputs["Fac"], [(0.3, (0.6, 0.6, 0.6)), (0.7, (1, 1, 1))]).outputs[0], 1.0, "MULTIPLY")
    chrom = nb.voronoi(55.0, "F1")                                        # chromatophores: dark + rusty red dots
    cd = nb_map(nb, chrom.outputs["Distance"], 0.12, 0.28, 1.0, 0.0)
    cr = nb.n("ShaderNodeSeparateColor"); nb.L(chrom.outputs["Color"], cr.inputs[0])
    col_ = nb.mix(col_, (0.005, 0.002, 0.003), nb.math("MULTIPLY", cd, nb.math("GREATER_THAN", cr.outputs[0], 0.45)))
    col_ = nb.mix(col_, (0.22, 0.03, 0.02), nb.math("MULTIPLY", nb.math("MULTIPLY", cd, nb.math("LESS_THAN", cr.outputs[0], 0.2)), 0.8))
    vn = nb.noise(6.0, 4, 0.5, distortion=3.2)
    veins = nb.ramp(vn.outputs["Fac"], [(0.487, (0, 0, 0)), (0.5, (1, 1, 1)), (0.513, (0, 0, 0))]).outputs[0]
    col_ = nb.mix(col_, (0.25, 0.0, 0.035), nb.math("MULTIPLY", veins, nb.math("ADD", 0.25, nb.math("MULTIPLY", side, 0.6))))
    sc_n = nb.noise(3.0, 3, 0.5, distortion=1.4, vec=nb.mapping(scale=(4, 1.0, 4)))
    scars = nb.ramp(sc_n.outputs["Fac"], [(0.496, (0, 0, 0)), (0.5, (1, 1, 1)), (0.504, (0, 0, 0))]).outputs[0]
    scars = nb.math("MULTIPLY", scars, nb_map(nb, nb.noise(1.5, 2).outputs["Fac"], 0.48, 0.58))
    col_ = nb.mix(col_, (0.2, 0.13, 0.12), nb.math("MULTIPLY", scars, 0.45))
    fl = None
    for c, r in MASK["flesh"]:
        dist = nb.n("ShaderNodeVectorMath", operation="DISTANCE"); nb.L(P, dist.inputs[0]); dist.inputs[1].default_value = tuple(c)
        m_ = nb_map(nb, dist.outputs["Value"], r * 0.5, r, 1.0, 0.0)
        fl = m_ if fl is None else nb.math("MAXIMUM", fl, m_)
    wd = None
    for c, rv in MASK["wound"]:
        sub = nb.n("ShaderNodeVectorMath", operation="SUBTRACT"); nb.L(P, sub.inputs[0]); sub.inputs[1].default_value = tuple(c)
        mul = nb.n("ShaderNodeVectorMath", operation="MULTIPLY"); nb.L(sub.outputs[0], mul.inputs[0]); mul.inputs[1].default_value = (1 / rv.x, 1 / rv.y, 1 / rv.z)
        ln = nb.n("ShaderNodeVectorMath", operation="LENGTH"); nb.L(mul.outputs[0], ln.inputs[0])
        m_ = nb_map(nb, ln.outputs["Value"], 0.6, 1.0, 1.0, 0.0)
        wd = m_ if wd is None else nb.math("MAXIMUM", wd, m_)
    fib = nb.noise(70.0, 3, 0.5, vec=nb.mapping(scale=(1, 0.2, 1)))
    raw = nb.ramp(fib.outputs["Fac"], [(0.3, (0.09, 0.004, 0.01)), (0.7, (0.36, 0.03, 0.04))]).outputs[0]
    rawm = nb.math("MAXIMUM", fl, wd)
    col_ = nb.mix(col_, raw, rawm)
    col_ = nb.mix(col_, (0.03, 0.0, 0.004), nb_map(nb, wd, 0.7, 0.95))
    rough = nb_map(nb, mott.outputs["Fac"], 0.3, 0.7, 0.16, 0.36)
    rough = nb.math("SUBTRACT", rough, nb.math("MULTIPLY", rawm, 0.12))
    wr = nb.noise(45.0, 6, 0.65, vec=nb.mapping(scale=(1, 0.5, 1)))
    h = nb.math("ADD", nb.math("MULTIPLY", wr.outputs["Fac"], 0.6), nb.math("MULTIPLY", veins, 0.5), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", cd, 0.25), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", scars, 0.4), clamp=False)
    h = nb.math("SUBTRACT", h, nb.math("MULTIPLY", wd, 1.0), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", nb.math("MULTIPLY", fib.outputs["Fac"], rawm), 0.5), clamp=False)
    nb_finish_full(nb, col_, rough, h, bump=0.45, dist=0.01, spec=0.55)
    mat.diffuse_color = (0.04, 0.015, 0.02, 1)


def iris_k(mat):
    nb = NB(mat)
    rays = nb.noise(60.0, 4, 0.6, vec=nb.mapping(scale=(1, 1, 8)))
    c = nb.ramp(rays.outputs["Fac"], [(0.3, (0.3, 0.1, 0.005)), (0.7, (0.75, 0.42, 0.06))]).outputs[0]
    nb_finish_full(nb, c, 0.05, rays.outputs["Fac"], bump=0.1, dist=0.002, emit=c, emit_strength=1.0, spec=0.9)
    mat.diffuse_color = (0.8, 0.55, 0.1, 1)


kraken_skin(M_skin)
simple_shader(M_sucker, (0.22, 0.1, 0.1), 0.15, noise_scale=40, var=0.35, bump=0.3, veins=(20.0, (0.16, 0.01, 0.03), 0.6))
simple_shader(M_hook, (0.34, 0.27, 0.17), 0.22, noise_scale=70, var=0.4, bump=0.15, veins=(30.0, (0.14, 0.07, 0.03), 0.6))
flesh_shader(M_flesh, (0.2, 0.008, 0.018))
simple_shader(M_beak, (0.02, 0.012, 0.01), 0.12, noise_scale=30, var=0.6, bump=0.3, veins=(12.0, (0.12, 0.06, 0.03), 0.5))
simple_shader(M_eye, (0.04, 0.02, 0.015), 0.04, noise_scale=20, var=0.5, bump=0.1, veins=(22.0, (0.25, 0.01, 0.02), 0.7))
iris_k(M_iris)
simple_shader(M_pupil, (0.003, 0.002, 0.002), 0.04, var=0.0)
simple_shader(M_fin, (0.04, 0.012, 0.02), 0.3, noise_scale=10, var=0.45, bump=0.3, veins=(9.0, (0.22, 0.0, 0.03), 0.7))
for m_ in bpy.data.materials:
    if m_.name.startswith("M_KrX_"): m_.use_fake_user = True
KR_INFO = {"tris": sum(len(p.vertices) - 2 for p in body.data.polygons), "bones": len(rig.data.bones),
           "unweighted": sum(1 for v in body.data.vertices if not v.groups), "mats": [m.name for m in body.data.materials],
           "dims": tuple(round(d, 2) for d in body.dimensions)}
print("KR_INFO", KR_INFO)
