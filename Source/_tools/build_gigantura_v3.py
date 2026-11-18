# Gigantura v3 (2026-11-09): monster-ified creature rebuilt from scratch on the existing Gigantura_Rig (bones + actions kept).
# Huge skull head with exposed bone and peeled skin flaps, retracted lips + splayed teeth, split underbite jaw,
# glowing sunken eyes + a cluster of extra eyes, spine spikes, ribs bursting out of the flank, tumours, claw-like fins.
# exec after mk.py, rig.py, horror.py, horror2.py
from mathutils.bvhtree import BVHTree
random.seed(31)
S = 1.2
arm = bpy.data.objects["Gigantura_Rig"]; col = bpy.data.collections["Gigantura"]
prev_action = arm.animation_data.action if arm.animation_data else None
if arm.animation_data: arm.animation_data.action = None
for pb in arm.pose.bones: pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
old = bpy.data.objects.get("SK_Gigantura_Body")
if old: _om = old.data; bpy.data.objects.remove(old); bpy.data.meshes.remove(_om)


def _m(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)
M_skin, M_flesh, M_bone, M_teeth = _m("M_GigX_Skin"), _m("M_GigX_Flesh"), _m("M_GigX_Bone"), _m("M_GigX_Teeth")
M_fin, M_eye, M_pupil, M_throat = _m("M_GigX_Fin"), _m("M_GigX_Eye"), _m("M_GigX_Pupil"), _m("M_GigX_Throat")
M_iris = _m("M_GigX_Iris")

KEYS = [(-1.27,0,0,0.0),(-1.255,0.035,0.04,0.0),(-1.21,0.08,0.09,0.01),(-1.12,0.13,0.15,0.03),(-1.0,0.17,0.21,0.06),
        (-0.86,0.19,0.27,0.09),(-0.7,0.185,0.31,0.1),(-0.5,0.17,0.3,0.08),(-0.25,0.15,0.26,0.05),(0.05,0.125,0.2,0.025),
        (0.35,0.095,0.14,0.01),(0.65,0.065,0.09,0.0),(0.9,0.04,0.055,0.0),(1.05,0.024,0.032,0.0),(1.12,0.012,0.016,0.0),(1.14,0,0,0)]
JH = [(-1.33,0,0,-0.072),(-1.31,0.025,0.022,-0.076),(-1.24,0.05,0.04,-0.09),(-1.12,0.07,0.055,-0.108),(-0.98,0.08,0.06,-0.118),
      (-0.88,0.07,0.052,-0.11),(-0.8,0,0,-0.095)]
PAL = -0.05 * S


def prof(keys, y):
    for a, b in zip(keys, keys[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0]); return [a[i] + (b[i] - a[i]) * t for i in range(len(a))]
    return list(keys[0]) if y < keys[0][0] else list(keys[-1])
hx_at = lambda y: prof(KEYS, y)


def radial(y, a, x, z):
    yu = y / S; s = 1.0
    side = abs(math.cos(a)) ** 1.5; sa = math.sin(a)
    if -1.05 < yu < 0.85:                                                   # hunched bony keel
        env = math.sin(math.pi * (yu + 1.05) / 1.9)
        s += 0.08 * env * math.exp(-((a - math.pi / 2) / 0.2) ** 2)
    if -0.6 < yu < 0.35:                                                    # starved: ribs + sunken belly
        env = math.sin(math.pi * (yu + 0.6) / 0.95)
        rib = (0.5 + 0.5 * math.cos(yu * math.tau * 11)) ** 3
        s -= 0.05 * side * env * (1 - rib)
        if sa < 0: s -= 0.09 * sa * sa * env
    if -0.82 < yu < -0.7:                                                   # deep gill slash
        s -= 0.06 * side * math.sin(math.pi * (yu + 0.82) / 0.12) * math.exp(-((sa - 0.05) / 0.6) ** 2)
    return s


# ---------------- base body ----------------
ST = [(y * S, hx * S, hz * S, zc * S) for y, hx, hz, zc in smooth_stations(KEYS, 120)]
body = finish(col, "SK_Gigantura_Body", loft_fn(ST, 64, radial), M_skin)
body.parent = arm; body.matrix_parent_inverse = Matrix.Identity(4)
subdivide_displace(body, levels=1, lumps=0.006 * S, lump_scale=5, wrinkle=0.0012 * S, wrinkle_scale=70, seed=9)
me = body.data
for v in me.vertices:                                                       # palate under the snout
    if v.co.y < -0.8 * S and v.co.z < PAL:
        v.co.z += (PAL - v.co.z) * smoothstep(0.0, 1.0, (-0.8 * S - v.co.y) / (0.07 * S))
me.update()

bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [p.vertices[:] for p in me.polygons])
def hit(origin, target):
    o = Vector(origin); d = (Vector(target) - o).normalized()
    loc, nor, _, _ = bvh.ray_cast(o, d)
    return loc.copy(), nor.normalized()
def ring_hit(yu, ang, side=1):
    p = hx_at(yu); a = math.radians(ang); c = Vector((0, yu * S, p[3] * S))
    return hit(c + Vector((side * math.cos(a), 0, math.sin(a))) * 1.5, c)

SCULPT = []                                     # (centre, radii, amount along normal)
MASK = {"bone": [], "flesh": [], "tumor": [], "wound": []}
EYES = []                                       # (centre, radius, look, main, socket normal)

for sx in (-1, 1):                                                           # big sunken eyes under a heavy brow
    p, n = hit((sx * 0.42 * S, -1.6 * S, 0.36 * S), (sx * 0.03 * S, -0.95 * S, 0.1 * S))
    SCULPT.append((p, Vector((0.078, 0.078, 0.07)) * S, -0.055 * S))
    SCULPT.append((p + Vector((sx * 0.01, 0.02, 0.07)) * S, Vector((0.085, 0.05, 0.035)) * S, 0.04 * S))
    SCULPT.append((p + Vector((sx * 0.05, 0.05, -0.075)) * S, Vector((0.05, 0.06, 0.035)) * S, 0.03 * S))
    SCULPT.append((p + Vector((sx * 0.04, 0.13, 0.04)) * S, Vector((0.05, 0.06, 0.05)) * S, -0.03 * S))   # temple hollow
    EYES.append((p - n * 0.024 * S, 0.05 * S, (n + Vector((0, -0.7, 0.05))).normalized(), True, n))
    MASK["flesh"].append((p, 0.05 * S))
for yu, ang, side, r in [(-1.0, 8, -1, 0.03), (-0.93, -8, -1, 0.021), (-0.89, 16, -1, 0.017), (-1.06, -14, -1, 0.015),
                         (-0.85, 30, -1, 0.013), (-0.96, -24, -1, 0.012), (-0.97, 38, 1, 0.016), (-0.9, 52, 1, 0.011)]:
    p, n = ring_hit(yu, ang, side)
    SCULPT.append((p, Vector((r, r, r)) * 1.5 * S, -r * 0.9 * S))
    look = (n + Vector((random.uniform(-0.7, 0.7), random.uniform(-0.7, 0.4), random.uniform(-0.6, 0.6)))).normalized()
    EYES.append((p - n * r * 0.3 * S, r * S, look, False, n))
    MASK["flesh"].append((p, r * 1.6 * S))
for k in range(9):                                                            # tumour cluster on the left neck
    p, n = ring_hit(random.uniform(-0.8, -0.48), random.uniform(-15, 50), -1)
    r = random.uniform(0.025, 0.065)
    SCULPT.append((p, Vector((r, r * 1.2, r)) * S, r * 0.85 * S))
    MASK["tumor"].append((p, r * 1.7 * S))
WOUND_P, WOUND_N = ring_hit(-0.3, -12, 1)                                     # ribs burst out of the right flank
SCULPT.append((WOUND_P, Vector((0.06, 0.16, 0.06)) * S, -0.06 * S))
MASK["wound"].append((WOUND_P, 0.13 * S))
SKULL_P, SKULL_N = hit((0, -1.5 * S, 0.33 * S), (0, -1.0 * S, 0.0))         # skin torn off the snout
SCULPT.append((SKULL_P, Vector((0.09, 0.1, 0.08)) * S, -0.012 * S))
SCULPT.append((SKULL_P + Vector((0, 0.03, 0.01)) * S, Vector((0.016, 0.1, 0.016)) * S, 0.018 * S))  # nasal ridge
for sx in (-1, 1):                                                            # bony nostril pits + brow plates
    SCULPT.append((SKULL_P + Vector((sx * 0.03, -0.03, -0.02)) * S, Vector((0.012, 0.015, 0.012)) * S, -0.014 * S))
    SCULPT.append((SKULL_P + Vector((sx * 0.045, 0.05, 0.03)) * S, Vector((0.03, 0.04, 0.015)) * S, 0.012 * S))
MASK["bone"].append((SKULL_P, 0.095 * S))
SPIKES = []
for i in range(23):                                                           # vertebral spikes through the back
    yu = -0.8 + i * 0.062
    p, n = ring_hit(yu, 90 + random.uniform(-4, 4))
    env = math.exp(-((yu + 0.45) / 0.55) ** 2)
    SPIKES.append((p, n, 0.04 + 0.15 * env * random.uniform(0.6, 1.2), (0.009 + 0.012 * env) * random.uniform(0.8, 1.2)))
    MASK["flesh"].append((p, (0.02 + 0.02 * env) * S))

for v in me.vertices:
    d = 0.0
    for c, rad, amt in SCULPT:
        q = v.co - c
        e = (q.x / rad.x) ** 2 + (q.y / rad.y) ** 2 + (q.z / rad.z) ** 2
        if e < 9: d += amt * math.exp(-e)
    if d: v.co += v.normal * d
me.update()
me.materials.append(M_flesh)
for f in me.polygons:
    if f.center.y < -0.8 * S and abs(f.center.z - PAL) < 0.004 * S and f.normal.z < -0.5: f.material_index = 1

extras = []
def add(name, bm, material):
    o = finish(col, name, bm, material); o.parent = arm; o.matrix_parent_inverse = Matrix.Identity(4); extras.append(o); return o
def orient(n):
    return n.to_track_quat("Z", "Y").to_matrix().to_4x4()

for k, (p, n, L, r) in enumerate(SPIKES):
    m = T(*(p - n * 0.012 * S)) @ orient((n + Vector((0, 0.8, 0))).normalized())
    add(f"gx_spike_{k}", xf(needle(r * S, L * S, (0, 0, 0), 0, 0, 0.12 * random.choice((1, -1)), segs=7), m), M_bone)
for k, yu in enumerate([-0.4, -0.31, -0.23]):                                # broken ribs splaying out of the wound
    p = hx_at(yu); jit = random.uniform(-0.015, 0.015)
    out_len = [0.13, 0.17, 0.08][k]
    z0 = p[3] - p[2] * 0.12 + jit
    pts = [Vector((p[1] * 0.4, yu - 0.02, z0 + 0.03)), Vector((p[1] * 0.85, yu, z0)),
           Vector((p[1] * 1.0 + out_len * 0.5, yu + 0.03, z0 - 0.02)), Vector((p[1] * 1.0 + out_len, yu + 0.07, z0 - 0.06))]
    pts = [q * S for q in catmull(pts, 5)]
    add(f"gx_rib_{k}", wrinkle_bm(tube(pts, lambda s: 0.011 * S * (1 - 0.88 * s ** 2.5), up=(0, 1, 0), sides=8), 0.0015, 120, k), M_bone)


def fin_rays(base, tips, ext, r, m, every=1, curl=0.0):
    bm = bmesh.new()
    for i in range(0, len(base), every):
        b = Vector(base[i]); t = Vector(tips[i])
        pts = []
        for k in range(9):
            s = k / 8; q = b + (t - b) * s * ext
            pts.append(Vector((curl * s * s, q.x, q.y)))
        part = tube(pts, lambda s: r * (1 - 0.9 * s) * (1 + 0.25 * math.sin(s * math.pi * 5) ** 8), up=(1, 0, 0), sides=6)
        tmp = bpy.data.meshes.new("_r"); part.to_mesh(tmp); part.free(); bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    return xf(bm, m)

SC = Matrix.Scale(S, 4)
NC = 21                                                                     # tattered caudal fin, rays poke past the membrane
cb = resample([(1.0, 0.035), (1.06, 0.0), (1.1, -0.03)], NC)
ct = resample([(1.24, 0.26), (1.34, 0.18), (1.26, 0.02), (1.42, -0.14), (1.68, -0.28), (1.82, -0.33)], NC)
mb, _ = ray_fin(cb, ct, 0.006, SC, rows=10, ray_every=2, scallop=0.3, tears=((4, 0.6), (9, 0.45), (15, 0.5)))
add("gx_caudal", mb, M_fin); add("gx_caudal_rays", fin_rays(cb, ct, 1.12, 0.0045, SC, every=2), M_bone)
N = 11
ab_ = [(0.35 + 0.45 * i / (N - 1), hx_at(0.35 + 0.45 * i / (N - 1))[3] - hx_at(0.35 + 0.45 * i / (N - 1))[2]) for i in range(N)]
at_ = [(b[0] + 0.08, b[1] - 0.04 - 0.12 * (1 - i / (N - 1))) for i, b in enumerate(ab_)]
mb, _ = ray_fin(ab_, at_, 0.006, SC, rows=5, ray_every=2, scallop=0.3, tears=((3, 0.6), (7, 0.5)))
add("gx_anal", mb, M_fin); add("gx_anal_rays", fin_rays(ab_, at_, 1.15, 0.004, SC, every=2), M_bone)

bpy.ops.object.select_all(action="DESELECT")
for o in [body] + extras: o.select_set(True)
bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
body.data.shade_smooth()
spines = [f"gt_spine_{i:02d}" for i in range(1, 11)]
distance_weights(body, arm, spines, falloff=3.0, top=2)
blend_region(body, "gt_head", lambda c: max(0.0, min(1.0, (-0.88 * S - c.y) / (0.16 * S))))

# ---------------- rigid head parts ----------------
for k, (ctr, r, look, main, n) in enumerate(EYES):                        # dark wet orbs, glowing slit irises
    rigid_bm_to_group(body, uvsphere(r, T(*ctr), 22 if main else 14, 12 if main else 8), M_eye, "gt_head")
    rot = orient(look)
    rigid_bm_to_group(body, uvsphere(r * 0.62, T(*(ctr + look * r * 0.83)) @ rot @ Matrix.Diagonal((1, 1, 0.3, 1)), 18, 8), M_iris, "gt_head")
    slit = (0.16, 0.9) if main else (0.3, 0.6)
    rigid_bm_to_group(body, uvsphere(r * 0.6, T(*(ctr + look * r * 0.9)) @ rot @ Matrix.Diagonal((slit[0], slit[1], 0.22, 1)), 12, 6), M_pupil, "gt_head")
    lid = torus(r * 0.98, r * 0.16, 24 if main else 14, 8, T(*(ctr + n * r * 0.5)) @ orient(n))
    rigid_bm_to_group(body, wrinkle_bm(lid, r * 0.05, 90, k), M_skin, "gt_head")

def jaw_xc(y, sx):
    hj = prof(JH, y); g = 0.035 * max(0.0, min(1.0, (-1.12 - y) / 0.21))
    return sx * (g + hj[1] * 0.9)
for sx in (-1, 1):                                                           # split underbite jaw
    jb = loft_fn([(y * S, hx * S, hz * S, zc * S) for y, hx, hz, zc in smooth_stations(JH, 28)], 22)
    for v in jb.verts: v.co.x += jaw_xc(v.co.y / S, sx) * S
    wrinkle_bm(jb, 0.002 * S, 60, 3 + sx); jb.normal_update()
    jin = jb.copy()
    bmesh.ops.delete(jb, geom=[f for f in jb.faces if f.normal.z > 0.8], context="FACES")
    bmesh.ops.delete(jin, geom=[f for f in jin.faces if f.normal.z <= 0.8], context="FACES")
    rigid_bm_to_group(body, jb, M_skin, "gt_jaw"); rigid_bm_to_group(body, jin, M_flesh, "gt_jaw")
tongue = loft_fn([(y * S, hx * S, hz * S, zc * S) for y, hx, hz, zc in smooth_stations(
    [(-1.29, 0, 0, -0.085), (-1.25, 0.018, 0.012, -0.088), (-1.12, 0.04, 0.02, -0.095), (-0.95, 0.055, 0.025, -0.1), (-0.84, 0, 0, -0.1)], 20)], 14)
rigid_bm_to_group(body, wrinkle_bm(tongue, 0.003 * S, 60, 4), M_flesh, "gt_jaw")
rigid_bm_to_group(body, uvsphere(0.075 * S, T(0, -0.8 * S, -0.1 * S) @ Matrix.Diagonal((1, 1.3, 0.8, 1)), 16, 10), M_throat, "gt_head")
ring_c = Vector((0, -0.87 * S, -0.09 * S))                                   # inner (pharyngeal) tooth ring
rigid_bm_to_group(body, torus(0.055 * S, 0.016 * S, 20, 8, T(*ring_c) @ RX(90)), M_flesh, "gt_head")
for k in range(12):
    a = k / 12 * math.tau; q = ring_c + Vector((math.cos(a), 0, math.sin(a))) * 0.05 * S
    dv = (ring_c + Vector((0, -0.05 * S, 0)) - q).normalized()
    rigid_bm_to_group(body, xf(needle(0.005 * S, random.uniform(0.03, 0.05) * S, (0, 0, 0), 0, 0, 0.0, segs=5), T(*q) @ orient(dv)), M_teeth, "gt_head")


def tooth(p, down, sx, scale=1.0, row=0):
    roll = random.random()
    if roll < 0.2: L, r = random.uniform(0.1, 0.19), 0.008                   # fang
    elif roll < 0.3: L, r = random.uniform(0.015, 0.03), 0.009               # broken stump
    else: L, r = random.uniform(0.03, 0.07), 0.0055
    L *= S * scale * (1 - 0.3 * row); r *= S * (1 - 0.25 * row)
    splay = sx * random.uniform(18, 38) * (1 - 0.5 * row)
    tx = (180 if down else 0) + random.uniform(-18, 18)
    return needle(r, L, p.to_tuple(), tx, splay if down else splay, (-1 if down else 1) * random.uniform(0.1, 0.35), segs=6)
for i in range(18):
    y = -1.245 + i * 0.022
    for sx in (-1, 1):
        for row in range(3):
            if row == 2 and i % 2: continue
            p = Vector((sx * (hx_at(y)[1] * 0.86 - 0.012 * row) * S, (y + 0.006 * row) * S, PAL))
            rigid_bm_to_group(body, tooth(p, True, sx, 1.0, row), M_teeth, "gt_head")
            hj = prof(JH, y - 0.03)
            if hj[1] > 0.01:
                q = Vector(((jaw_xc(y - 0.03, sx) + sx * (hj[1] * 0.75 - 0.012 * row)) * S, (y - 0.03 + 0.006 * row) * S, (hj[3] + hj[2] * 0.55) * S))
                rigid_bm_to_group(body, tooth(q, False, sx, 1.1, row), M_teeth, "gt_jaw")
for sx in (-1, 1):                                                           # tusks from the split chin
    q = Vector((jaw_xc(-1.29, sx) * S, -1.29 * S, -0.075 * S))
    rigid_bm_to_group(body, needle(0.012 * S, 0.21 * S, q.to_tuple(), 28, sx * 14, 0.3, segs=7), M_teeth, "gt_jaw")

for sx, bone in ((1, "gt_pec_l"), (-1, "gt_pec_r")):                        # pectoral fins as skeletal claws
    n = 5
    base = [(0.0, 0.03 - 0.06 * i / (n - 1)) for i in range(n)]
    tips = [(L * math.cos(math.radians(a)), b[1] + L * math.sin(math.radians(a))) for b, L, a in
            zip(base, [0.34, 0.4, 0.37, 0.32, 0.26], [14, 4, -6, -16, -26])]
    m = T(sx * 0.16 * S, -0.64 * S, 0.03 * S) @ RZ(-sx * 12) @ RY(sx * 18) @ RX(-45) @ SC
    short = [Vector(b) + (Vector(t) - Vector(b)) * 0.62 for b, t in zip(base, tips)]
    mb, _ = ray_fin(base, short, 0.006, m, rows=5, ray_every=1, scallop=0.25, tears=((2, 0.5),) if sx > 0 else ((1, 0.4),))
    rigid_bm_to_group(body, mb, M_fin, bone)
    rigid_bm_to_group(body, fin_rays(base, tips, 1.0, 0.014, m, every=1, curl=sx * 0.11), M_bone, bone)

mod = body.modifiers.get("Armature") or body.modifiers.new("Armature", "ARMATURE"); mod.object = arm
if prev_action: arm.animation_data.action = prev_action


def _gprof(co):
    p = hx_at(max(-1.269, min(1.139, co.y / S)))
    hx = max(1e-3, p[1] * S); hz = max(1e-3, p[2] * S)
    a = math.atan2((co.z - p[3] * S) / hz, co.x / hx)
    return (math.sin(a), co.y, abs(math.cos(a)))
set_profile_attr(body, "gprof", _gprof)


# ---------------- shaders ----------------
def nb_sphere(nb, P, c, r, soft=0.5):
    dist = nb.n("ShaderNodeVectorMath", operation="DISTANCE"); nb.L(P, dist.inputs[0]); dist.inputs[1].default_value = tuple(c)
    return nb_map(nb, dist.outputs["Value"], r * (1 - soft), r, 1.0, 0.0)
def nb_union(nb, P, items, soft=0.5):
    out = None
    for c, r in items:
        mk_ = nb_sphere(nb, P, c, r, soft)
        out = mk_ if out is None else nb.math("MAXIMUM", out, mk_)
    return out


def skin_v3(mat):
    nb = NB(mat)
    s, y, c = nb_attr(nb, "gprof")
    P = nb_warp(nb, 0.06, 9.0)
    sep = nb.n("ShaderNodeSeparateXYZ"); nb.L(nb.obj, sep.inputs[0]); Z = sep.outputs["Z"]; Y = sep.outputs["Y"]
    belly_t = nb_map(nb, s, -0.85, 0.0); dors_t = nb_map(nb, s, 0.05, 0.7)
    col_ = nb.mix((0.075, 0.05, 0.048), (0.026, 0.016, 0.017), belly_t)
    col_ = nb.mix(col_, (0.009, 0.007, 0.008), dors_t)
    bruise = nb.noise(2.6, 6, 0.6, distortion=0.4)
    col_ = nb.mix(col_, (0.06, 0.01, 0.022), nb.math("MULTIPLY", nb_map(nb, bruise.outputs["Fac"], 0.5, 0.68), 0.55))
    mott = nb.noise(9.0, 6, 0.65)
    col_ = nb.mix(col_, nb.ramp(mott.outputs["Fac"], [(0.3, (0.6, 0.6, 0.6)), (0.7, (1, 1, 1))]).outputs[0], 1.0, "MULTIPLY")
    sc_n = nb.noise(4.0, 3, 0.5, distortion=1.4, vec=nb.mapping(scale=(5, 0.6, 5)))
    scars = nb.ramp(sc_n.outputs["Fac"], [(0.496, (0, 0, 0)), (0.5, (1, 1, 1)), (0.504, (0, 0, 0))]).outputs[0]
    scars = nb.math("MULTIPLY", scars, nb_map(nb, nb.noise(1.5, 2).outputs["Fac"], 0.48, 0.58))
    col_ = nb.mix(col_, (0.12, 0.08, 0.075), nb.math("MULTIPLY", scars, 0.3))
    vn = nb.noise(6.0, 4, 0.5, distortion=3.2)
    veins = nb.ramp(vn.outputs["Fac"], [(0.486, (0, 0, 0)), (0.5, (1, 1, 1)), (0.514, (0, 0, 0))]).outputs[0]
    tum = nb_union(nb, P, MASK["tumor"], 0.6)
    vmask = nb.math("MULTIPLY", veins, nb.math("ADD", nb.math("MULTIPLY", nb.math("SUBTRACT", 1.0, belly_t), 0.5), nb.math("ADD", 0.2, tum)))
    col_ = nb.mix(col_, (0.2, 0.0, 0.03), vmask)
    lump = nb.noise(35.0, 4, 0.6)
    tum_c = nb.ramp(lump.outputs["Fac"], [(0.3, (0.2, 0.14, 0.1)), (0.7, (0.42, 0.32, 0.2))]).outputs[0]
    col_ = nb.mix(col_, tum_c, nb.math("MULTIPLY", tum, 0.85))
    col_ = nb.mix(col_, (0.25, 0.0, 0.03), nb.math("MULTIPLY", nb.math("MULTIPLY", veins, tum), 0.9))
    # raw flesh: eye sockets, spike bases, gums (retracted lips)
    gum = nb.math("MULTIPLY", nb_map(nb, Z, PAL + 0.04 * S, PAL + 0.008 * S), nb_map(nb, Y, -0.78 * S, -0.86 * S))
    gum = nb.math("MULTIPLY", gum, nb_map(nb, Z, PAL - 0.004 * S, PAL + 0.002 * S))
    fl = nb.math("MAXIMUM", nb_union(nb, P, MASK["flesh"], 0.6), gum)
    fib = nb.noise(80.0, 3, 0.5, vec=nb.mapping(scale=(1, 0.15, 1)))
    raw = nb.ramp(fib.outputs["Fac"], [(0.3, (0.1, 0.004, 0.01)), (0.7, (0.38, 0.03, 0.04))]).outputs[0]
    col_ = nb.mix(col_, raw, fl)
    # rib wound: torn ring of skin, wet muscle, black core
    wsub = nb.n("ShaderNodeVectorMath", operation="SUBTRACT"); nb.L(P, wsub.inputs[0]); wsub.inputs[1].default_value = tuple(WOUND_P)
    wmul = nb.n("ShaderNodeVectorMath", operation="MULTIPLY"); nb.L(wsub.outputs[0], wmul.inputs[0]); wmul.inputs[1].default_value = (1.3, 0.62, 1.5)
    wd = nb.n("ShaderNodeVectorMath", operation="LENGTH"); nb.L(wmul.outputs[0], wd.inputs[0])
    wr_ = 0.13 * S
    w_in = nb_map(nb, wd.outputs["Value"], wr_ * 0.95, wr_ * 0.75); w_core = nb_map(nb, wd.outputs["Value"], wr_ * 0.45, wr_ * 0.2)
    w_rim = nb.math("MULTIPLY", nb_map(nb, wd.outputs["Value"], wr_ * 1.25, wr_ * 1.0), nb_map(nb, wd.outputs["Value"], wr_ * 0.75, wr_ * 0.95))
    col_ = nb.mix(col_, (0.16, 0.05, 0.05), nb.math("MULTIPLY", w_rim, 0.7))
    col_ = nb.mix(col_, raw, w_in); col_ = nb.mix(col_, (0.03, 0.0, 0.004), w_core)
    # exposed skull: cracked yellow bone, flesh rim
    bd = nb.n("ShaderNodeVectorMath", operation="DISTANCE"); nb.L(P, bd.inputs[0]); bd.inputs[1].default_value = tuple(SKULL_P)
    br = 0.095 * S
    b_in = nb_map(nb, bd.outputs["Value"], br * 0.85, br * 0.65)
    b_rim = nb.math("MULTIPLY", nb_map(nb, bd.outputs["Value"], br * 0.98, br * 0.86), nb.math("SUBTRACT", 1.0, b_in))
    crk = nb.voronoi(70.0, "DISTANCE_TO_EDGE", vec=P)
    cracks = nb.math("MULTIPLY", nb_map(nb, crk.outputs["Distance"], 0.0, 0.03, 1.0, 0.0), nb_map(nb, nb.noise(8.0, 2).outputs["Fac"], 0.45, 0.6))
    grime = nb.noise(25.0, 5, 0.6)
    bone_c = nb.ramp(grime.outputs["Fac"], [(0.25, (0.1, 0.06, 0.03)), (0.55, (0.3, 0.22, 0.12)), (0.8, (0.45, 0.36, 0.22))]).outputs[0]
    bone_c = nb.mix(bone_c, (0.03, 0.015, 0.01), cracks)
    col_ = nb.mix(col_, raw, b_rim); col_ = nb.mix(col_, bone_c, b_in)
    wet = nb.math("MAXIMUM", nb.math("MAXIMUM", fl, w_in), b_rim)
    rough = nb_map(nb, mott.outputs["Fac"], 0.3, 0.7, 0.22, 0.42)
    rough = nb.math("SUBTRACT", rough, nb.math("MULTIPLY", wet, 0.25))
    rough = nb.math("ADD", rough, nb.math("MULTIPLY", b_in, 0.1))
    wr = nb.noise(55.0, 6, 0.65, vec=nb.mapping(scale=(1, 0.35, 1)))
    pv = nb.voronoi(220.0, "F1")
    h = nb.math("ADD", nb.math("MULTIPLY", wr.outputs["Fac"], 0.6), nb.math("MULTIPLY", nb_map(nb, pv.outputs["Distance"], 0.0, 0.3), 0.2), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", vmask, 0.5), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", scars, 0.4), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", nb.math("MULTIPLY", lump.outputs["Fac"], tum), 0.8), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", nb.math("MULTIPLY", fib.outputs["Fac"], fl), 0.6), clamp=False)
    h = nb.math("SUBTRACT", h, nb.math("MULTIPLY", nb.math("MULTIPLY", cracks, b_in), 0.8), clamp=False)
    h = nb.math("SUBTRACT", h, nb.math("MULTIPLY", w_core, 1.0), clamp=False)
    nb_finish_full(nb, col_, rough, h, bump=0.45, dist=0.008, spec=0.55)
    mat.diffuse_color = (0.04, 0.02, 0.025, 1)


def eye_v3(mat):
    nb = NB(mat)
    cl = nb.noise(18.0, 5, 0.6)
    base = nb.ramp(cl.outputs["Fac"], [(0.3, (0.02, 0.012, 0.01)), (0.7, (0.09, 0.05, 0.03))]).outputs[0]
    v = nb.noise(22.0, 4, 0.5, distortion=4.0)
    veins = nb.ramp(v.outputs["Fac"], [(0.485, (0, 0, 0)), (0.5, (1, 1, 1)), (0.515, (0, 0, 0))]).outputs[0]
    c = nb.mix(base, (0.25, 0.01, 0.02), nb.math("MULTIPLY", veins, 0.7))
    nb_finish_full(nb, c, 0.04, veins, bump=0.1, dist=0.003, spec=0.9)
    mat.diffuse_color = (0.05, 0.03, 0.02, 1)


def iris_v3(mat):
    nb = NB(mat)
    rays = nb.noise(60.0, 4, 0.6, vec=nb.mapping(scale=(1, 1, 8)))
    c = nb.ramp(rays.outputs["Fac"], [(0.3, (0.3, 0.1, 0.005)), (0.7, (0.75, 0.42, 0.06))]).outputs[0]
    nb_finish_full(nb, c, 0.05, rays.outputs["Fac"], bump=0.1, dist=0.002, emit=c, emit_strength=1.0, spec=0.9)
    mat.diffuse_color = (0.8, 0.55, 0.1, 1)


skin_v3(M_skin)
flesh_shader(M_flesh, (0.2, 0.008, 0.018))
simple_shader(M_bone, (0.3, 0.24, 0.16), 0.4, noise_scale=30, var=0.45, bump=0.3, veins=(14.0, (0.06, 0.03, 0.015), 0.8))
simple_shader(M_teeth, (0.5, 0.43, 0.28), 0.22, noise_scale=70, var=0.4, bump=0.15, veins=(30.0, (0.15, 0.08, 0.03), 0.6))
simple_shader(M_fin, (0.035, 0.012, 0.018), 0.3, noise_scale=10, var=0.45, bump=0.3, veins=(9.0, (0.22, 0.0, 0.03), 0.7))
simple_shader(M_pupil, (0.003, 0.002, 0.002), 0.04, var=0.0)
simple_shader(M_throat, (0.25, 0.0, 0.01), 0.15, noise_scale=20, var=0.5, emit=(0.8, 0.03, 0.03), emit_strength=0.6)
eye_v3(M_eye); iris_v3(M_iris)
GIG_INFO = {"tris": sum(len(p.vertices) - 2 for p in body.data.polygons),
            "unweighted": sum(1 for v in body.data.vertices if not v.groups),
            "mats": [m.name for m in body.data.materials]}
print("GIG_INFO", GIG_INFO)
