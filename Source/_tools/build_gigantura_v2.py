# Gigantura v2 (2026-11-09): cleaner deep-sea horror body on the existing Gigantura_Rig (bones + actions kept).
# Smooth emaciated body, claw gashes, glowing photophore rows, tubular eyes with eyeshine, needle fangs, ray fins.
# exec after mk.py, rig.py, horror.py, horror2.py
random.seed(11)
S = 1.2
arm = bpy.data.objects["Gigantura_Rig"]; col = bpy.data.collections["Gigantura"]
prev_action = arm.animation_data.action if arm.animation_data else None
if arm.animation_data: arm.animation_data.action = None
for pb in arm.pose.bones: pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
old = bpy.data.objects.get("SK_Gigantura_Body")
if old: _m = old.data; bpy.data.objects.remove(old); bpy.data.meshes.remove(_m)


def _m(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)
M_skin, M_flesh, M_fin, M_ray = _m("M_GigX_Skin"), _m("M_GigX_Flesh"), _m("M_GigX_Fin"), _m("M_GigX_FinRay")
M_teeth, M_throat, M_lens = _m("M_GigX_Teeth"), _m("M_GigX_Throat"), _m("M_GigX_Lens")

KEYS = [(-1.25,0,0,-0.02),(-1.235,0.03,0.035,-0.02),(-1.19,0.075,0.095,-0.01),(-1.1,0.12,0.165,0.01),(-0.98,0.155,0.225,0.035),
        (-0.84,0.17,0.255,0.045),(-0.68,0.165,0.248,0.04),(-0.45,0.155,0.232,0.025),(-0.15,0.133,0.2,0.012),(0.15,0.106,0.158,0.004),
        (0.45,0.079,0.112,0.0),(0.72,0.053,0.076,0.0),(0.93,0.034,0.048,0.0),(1.06,0.021,0.03,0.0),(1.12,0.012,0.016,0.0),(1.14,0,0,0)]
JAW = [(-1.235,0,0,-0.055),(-1.2,0.06,0.03,-0.065),(-1.1,0.112,0.05,-0.088),(-0.95,0.138,0.058,-0.102),(-0.85,0.118,0.048,-0.097),(-0.79,0,0,-0.09)]
PAL = -0.045 * S


def prof(keys, y):
    for a, b in zip(keys, keys[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0]); return [a[i] + (b[i] - a[i]) * t for i in range(4)]
    return list(keys[0]) if y < keys[0][0] else list(keys[-1])
hx_at = lambda y: prof(KEYS, y)


def radial(y, a, x, z):
    yu = y / S; s = 1.0
    side = abs(math.cos(a)) ** 1.5; sa = math.sin(a)
    if -0.66 < yu < 0.32:                                              # emaciated: ribs show through the skin
        env = math.sin(math.pi * (yu + 0.66) / 0.98)
        rib = (0.5 + 0.5 * math.cos(yu * math.tau * 10)) ** 3
        s -= 0.035 * side * env * (1 - rib)
        if sa < 0: s -= 0.06 * abs(sa) ** 2 * env                       # sunken belly
    if -0.8 < yu < 0.95: s += 0.03 * math.exp(-((a - math.pi / 2) / 0.12) ** 2)   # spine keel
    if -0.8 < yu < -0.7:                                                # gill-cover groove
        s -= 0.035 * side * math.sin(math.pi * (yu + 0.8) / 0.1) * math.exp(-((sa - 0.1) / 0.7) ** 2)
    return s


def surf(yu, zf, sx=1, inset=0.97):
    p = hx_at(yu)
    return Vector((sx * p[1] * math.sqrt(max(0.0, 1 - zf * zf)) * S * inset, yu * S, (p[3] + zf * p[2]) * S))


# three parallel claw gashes raked across the +X flank
SLASHES = []
for (y0, z0, y1, z1, w) in [(-0.53, 0.62, -0.25, -0.5, 0.026), (-0.43, 0.68, -0.14, -0.45, 0.032), (-0.33, 0.58, -0.06, -0.38, 0.024)]:
    pts = []
    for k in range(8):
        t = k / 7
        pts.append(surf(y0 + (y1 - y0) * t + 0.025 * math.sin(math.pi * t), z0 + (z1 - z0) * t))
    SLASHES += surface_slash(pts, w)

# ---------------- deformable body ----------------
ST = [(y * S, hx * S, hz * S, zc * S) for y, hx, hz, zc in smooth_stations(KEYS, 110)]
body = finish(col, "SK_Gigantura_Body", loft_fn(ST, 56, radial), M_skin)
body.parent = arm; body.matrix_parent_inverse = Matrix.Identity(4)
subdivide_displace(body, levels=1, lumps=0.0035 * S, lump_scale=4, wrinkle=0.0007 * S, wrinkle_scale=90, seed=3)
me = body.data
for v in me.vertices:                                                   # flatten the snout underside into a palate
    if v.co.y < -0.78 * S and v.co.z < PAL:
        w = smoothstep(0.0, 1.0, (-0.78 * S - v.co.y) / (0.07 * S))
        v.co.z += (PAL - v.co.z) * w
me.update()
for v in me.vertices:                                                   # carve the gashes
    if v.co.x > 0:
        g = gash_mask_py(v.co, SLASHES)
        if g > 0: v.co -= v.normal * 0.03 * g
me.update()
me.materials.append(M_flesh)
for f in me.polygons:
    c = f.center
    if c.y < -0.8 * S and abs(c.z - PAL) < 0.004 * S and f.normal.z < -0.5:
        f.material_index = 1

extras = []
def add(name, bm, material):
    o = finish(col, name, bm, material); o.parent = arm; o.matrix_parent_inverse = Matrix.Identity(4); extras.append(o); return o

SC = Matrix.Scale(S, 4)
# dorsal + anal fins far back (as in the real fish), caudal fin with the long lower lobe
N = 15
db = [(0.3 + 0.56 * i / (N - 1), hx_at(0.3 + 0.56 * i / (N - 1))[3] + hx_at(0.3 + 0.56 * i / (N - 1))[2] * 1.02) for i in range(N)]
dt = [(b[0] + 0.1 + 0.06 * i / (N - 1), b[1] + 0.05 + 0.17 * (1 - i / (N - 1)) ** 0.8) for i, b in enumerate(db)]
m1, r1 = ray_fin(db, dt, 0.006, SC, tears=((6, 0.45),)); add("gx_dorsal", m1, M_fin); add("gx_dorsal_rays", r1, M_ray)
ab_ = [(0.28 + 0.6 * i / (N - 1), hx_at(0.28 + 0.6 * i / (N - 1))[3] - hx_at(0.28 + 0.6 * i / (N - 1))[2] * 1.0) for i in range(N)]
at_ = [(b[0] + 0.1 + 0.06 * i / (N - 1), b[1] - 0.05 - 0.16 * (1 - i / (N - 1)) ** 0.8) for i, b in enumerate(ab_)]
m2, r2 = ray_fin(ab_, at_, 0.006, SC, tears=((10, 0.3),)); add("gx_anal", m2, M_fin); add("gx_anal_rays", r2, M_ray)
NC = 19
cb = resample([(1.0, 0.035), (1.06, 0.0), (1.1, -0.03)], NC)
ct = resample([(1.2, 0.25), (1.3, 0.2), (1.25, 0.03), (1.42, -0.1), (1.8, -0.26), (2.08, -0.335)], NC)
m3, r3 = ray_fin(cb, ct, 0.007, SC, rows=10, tears=((7, 0.3),)); add("gx_caudal", m3, M_fin); add("gx_caudal_rays", r3, M_ray)

bpy.ops.object.select_all(action="DESELECT")
for o in [body] + extras: o.select_set(True)
bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
body.data.shade_smooth()

# ---------------- weights ----------------
spines = [f"gt_spine_{i:02d}" for i in range(1, 11)]
distance_weights(body, arm, spines, falloff=3.0, top=2)
blend_region(body, "gt_head", lambda c: max(0.0, min(1.0, (-0.9 * S - c.y) / (0.18 * S))))

# ---------------- rigid head parts ----------------
jaw = loft_fn([(y * S, hx * S, hz * S, zc * S) for y, hx, hz, zc in smooth_stations(JAW, 26)], 28)
jaw.normal_update()
jaw_in = jaw.copy()
bmesh.ops.delete(jaw, geom=[f for f in jaw.faces if f.normal.z > 0.35], context="FACES")
bmesh.ops.delete(jaw_in, geom=[f for f in jaw_in.faces if f.normal.z <= 0.35], context="FACES")
rigid_bm_to_group(body, jaw, M_skin, "gt_jaw")
rigid_bm_to_group(body, jaw_in, M_flesh, "gt_jaw")
tongue = loft_fn([(y * S, hx * S, hz * S, zc * S) for y, hx, hz, zc in smooth_stations(
    [(-1.13, 0, 0, -0.06), (-1.09, 0.03, 0.014, -0.062), (-0.98, 0.058, 0.024, -0.066), (-0.88, 0.05, 0.02, -0.07), (-0.85, 0, 0, -0.07)], 14)], 16)
rigid_bm_to_group(body, tongue, M_flesh, "gt_jaw")
rigid_bm_to_group(body, xf(lathe([(0, 0), (0.07 * S, 0.0), (0.075 * S, 0.06 * S), (0.0, 0.1 * S)], 16), T(0, -0.82 * S, PAL - 0.1 * S)), M_throat, "gt_head")

jaw_at = lambda y: prof(JAW, y)
def rim_up(y):  p = hx_at(y); return Vector((p[1] * S * 0.84, y * S, PAL))
def rim_lo(y):  p = jaw_at(y); return Vector((p[1] * S * 0.84, y * S, (p[3] + p[2] * 0.55) * S))
ys = [-1.212 + i * 0.024 for i in range(16)]
for row in range(2):
    for i, y in enumerate(ys):
        for sx in (-1, 1):
            for up, rim, bone in ((True, rim_up, "gt_head"), (False, rim_lo, "gt_jaw")):
                p = rim(y); p.x *= sx
                if row: p.x -= sx * 0.014 * S; p.y += 0.008 * S
                fang_k = (i % 3 == 1) and row == 0
                L = (random.uniform(0.085, 0.14) if fang_k else random.uniform(0.028, 0.055)) * S * (0.6 if row else 1.0)
                if i < 2: L *= 0.7
                r = (0.0075 if fang_k else 0.0048) * S
                if up:
                    tilt_x = 180 + random.uniform(-10, 10); bend = -0.22
                else:
                    tilt_x = random.uniform(-10, 10); bend = 0.22
                rigid_bm_to_group(body, needle(r, L, p.to_tuple(), tilt_x, sx * random.uniform(4, 16), bend, segs=6), M_teeth, bone)
for x in (-0.018, 0.0, 0.018):                                         # front fangs at the snout tip
    rigid_bm_to_group(body, needle(0.006 * S, random.uniform(0.07, 0.1) * S, (x * S, -1.225 * S, PAL), 180 + 18, 0, -0.25, segs=6), M_teeth, "gt_head")

EYES = []
for sx in (-1, 1):                                                       # forward-pointing telescope eyes
    tm = T(sx * 0.072 * S, -0.94 * S, 0.19 * S) @ RX(38) @ RY(sx * 7)
    prof_e = [(0.0, -0.06 * S), (0.11 * S, -0.06 * S), (0.085 * S, 0.0), (0.072 * S, 0.04 * S), (0.065 * S, 0.11 * S), (0.066 * S, 0.18 * S), (0.071 * S, 0.212 * S), (0.0, 0.216 * S)]
    rigid_bm_to_group(body, lathe(prof_e, 28, tm), M_skin, "gt_head")
    lens = bmesh.new(); bmesh.ops.create_uvsphere(lens, u_segments=28, v_segments=16, radius=0.066 * S)
    xf(lens, tm @ T(0, 0, 0.205 * S) @ Matrix.Diagonal((1, 1, 0.72, 1)))
    rigid_bm_to_group(body, lens, M_lens, "gt_head")
    rigid_bm_to_group(body, torus(0.069 * S, 0.0055 * S, 28, 8, tm @ T(0, 0, 0.21 * S)), M_skin, "gt_head")
    EYES.append((tm @ Vector((0, 0, 0.205 * S + 0.066 * S * 0.72)), tm.to_3x3() @ Vector((0, 0, 1))))

for sx, bone in ((1, "gt_pec_l"), (-1, "gt_pec_r")):                    # long wing-like pectoral fins
    n = 11
    base = [(0.0, 0.035 - 0.07 * i / (n - 1)) for i in range(n)]
    tips = []
    for i in range(n):
        ang = math.radians(10 - 34 * i / (n - 1)); L = 0.46 - 0.2 * abs(i - 2) / (n - 1)
        tips.append((L * math.cos(ang), base[i][1] + L * math.sin(ang)))
    m = T(sx * 0.15 * S, -0.62 * S, 0.11 * S) @ RZ(-sx * 22) @ RY(sx * 25) @ RX(-12) @ SC
    mb, rb = ray_fin(base, tips, 0.005, m, rows=8, ray_every=1, scallop=0.0, tears=((7, 0.35),) if sx > 0 else ())
    rigid_bm_to_group(body, mb, M_fin, bone); rigid_bm_to_group(body, rb, M_ray, bone)

mod = body.modifiers.get("Armature") or body.modifiers.new("Armature", "ARMATURE"); mod.object = arm
if prev_action: arm.animation_data.action = prev_action


# ---------------- profile attribute for the skin shader: (sin of body angle, y, |cos|) ----------------
def _gprof(co):
    p = hx_at(max(-1.249, min(1.139, co.y / S)))
    hx = max(1e-3, p[1] * S); hz = max(1e-3, p[2] * S)
    a = math.atan2((co.z - p[3] * S) / hz, co.x / hx)
    return (math.sin(a), co.y, abs(math.cos(a)))
set_profile_attr(body, "gprof", _gprof)


# ---------------- shaders ----------------
def gig_skin_v2(mat):
    nb = NB(mat)
    s, y, c = nb_attr(nb, "gprof")
    belly_t = nb_map(nb, s, -0.85, 0.05); dors_t = nb_map(nb, s, 0.15, 0.75)
    col_ = nb.mix((0.3, 0.23, 0.23), (0.07, 0.058, 0.064), belly_t)
    col_ = nb.mix(col_, (0.011, 0.011, 0.015), dors_t)
    mott = nb.noise(3.5, 6, 0.6)
    col_ = nb.mix(col_, nb.ramp(mott.outputs["Fac"], [(0.3, (0.65, 0.65, 0.65)), (0.7, (1, 1, 1))]).outputs[0], 1.0, "MULTIPLY")
    nec = nb.noise(4.5, 5, 0.6, distortion=0.8)
    necm = nb_map(nb, nec.outputs["Fac"], 0.6, 0.68)
    col_ = nb.mix(col_, (0.13, 0.11, 0.11), nb.math("MULTIPLY", necm, 0.35))
    vn = nb.noise(7.0, 4, 0.5, distortion=3.0)
    veins = nb.ramp(vn.outputs["Fac"], [(0.485, (0, 0, 0)), (0.5, (1, 1, 1)), (0.515, (0, 0, 0))]).outputs[0]
    vmask = nb.math("MULTIPLY", veins, nb.math("ADD", nb.math("MULTIPLY", nb.math("SUBTRACT", 1.0, belly_t), 0.6), 0.12))
    col_ = nb.mix(col_, (0.22, 0.015, 0.05), vmask)
    cosr = nb.math("COSINE", nb.math("MULTIPLY", y, math.tau * 10 / S, clamp=False), clamp=False)
    groove = nb_map(nb, cosr, -1.0, 0.3, 1.0, 0.0)
    region = nb.math("MULTIPLY", nb_map(nb, y, -0.7 * S, -0.55 * S), nb_map(nb, y, 0.32 * S, 0.18 * S))
    rib = nb.math("MULTIPLY", nb.math("MULTIPLY", groove, region), nb_map(nb, c, 0.3, 0.8))
    col_ = nb.mix(col_, (0.0, 0.0, 0.0), nb.math("MULTIPLY", rib, 0.45))
    line = nb.math("MULTIPLY", nb_map(nb, nb.math("ABSOLUTE", nb.math("SUBTRACT", s, 0.1, clamp=False)), 0.004, 0.012, 1.0, 0.0),
                   nb_map(nb, y, -0.85 * S, -0.8 * S))
    pores = nb_dot_row(nb, s, y, 0.1, 0.02, 0.35, 0.014, -0.8 * S, 1.1 * S)
    col_ = nb.mix(col_, (0.42, 0.4, 0.36), nb.math("MULTIPLY", line, 0.35))
    col_ = nb.mix(col_, (0.0, 0.0, 0.0), nb.math("MULTIPLY", pores, 0.8))
    ph = nb.math("MAXIMUM", nb_dot_row(nb, s, y, -0.55, 0.075, 0.3, 0.09, -1.05 * S, 0.95 * S),
                 nb_dot_row(nb, s, y, -0.85, 0.065, 0.32, 0.07, -1.0 * S, 0.7 * S, 0.5))
    ph_n = nb.noise(9.0, 2, 0.5)                                         # some organs dead / dim
    ph = nb.math("MULTIPLY", ph, nb_map(nb, ph_n.outputs["Fac"], 0.35, 0.55, 0.15, 1.0))
    col_ = nb.mix(col_, (0.5, 0.72, 0.68), ph)
    P = nb_warp(nb, 0.014, 22.0)
    g = None
    for a, b, w0, t0, t1 in SLASHES:
        mk_ = nb_seg_mask(nb, P, a, b, w0, t0, t1)
        g = mk_ if g is None else nb.math("MAXIMUM", g, mk_)
    rim = nb.math("MULTIPLY", nb_map(nb, g, 0.0, 0.12), nb_map(nb, g, 0.4, 0.2))
    inner = nb_map(nb, g, 0.2, 0.45); core = nb_map(nb, g, 0.6, 0.9)
    fl = nb.noise(30.0, 5, 0.6)
    flesh_c = nb.ramp(fl.outputs["Fac"], [(0.3, (0.12, 0.004, 0.01)), (0.7, (0.42, 0.04, 0.05))]).outputs[0]
    col_ = nb.mix(col_, (0.42, 0.16, 0.15), nb.math("MULTIPLY", rim, 0.85))
    col_ = nb.mix(col_, flesh_c, inner)
    col_ = nb.mix(col_, (0.035, 0.0, 0.004), core)
    # dried blood running down from the gashes
    drip_n = nb.noise(18.0, 3, 0.5, vec=nb.mapping(scale=(6, 6, 0.6)))
    drip = nb.math("MULTIPLY", nb_map(nb, drip_n.outputs["Fac"], 0.55, 0.62), nb_map(nb, g, 0.0, 0.02))
    rough = nb_map(nb, belly_t, 0.0, 1.0, 0.24, 0.34)
    rough = nb.math("ADD", rough, nb.math("MULTIPLY", necm, 0.3))
    rough = nb.math("SUBTRACT", rough, nb.math("MULTIPLY", inner, 0.3))
    wr = nb.noise(60.0, 6, 0.6, vec=nb.mapping(scale=(1, 0.4, 1)))
    pv = nb.voronoi(260.0, "F1")
    porebump = nb_map(nb, pv.outputs["Distance"], 0.0, 0.25, 0.0, 1.0)
    h = nb.math("ADD", nb.math("MULTIPLY", wr.outputs["Fac"], 0.35), nb.math("MULTIPLY", porebump, 0.12), clamp=False)
    h = nb.math("SUBTRACT", h, nb.math("MULTIPLY", g, 1.4), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", rim, 0.35), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", ph, 0.25), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", vmask, 0.25), clamp=False)
    emit = nb.mix((0, 0, 0), (0.2, 0.95, 0.85), ph)
    nb_finish_full(nb, col_, rough, h, bump=0.35, dist=0.01, emit=emit, emit_strength=1.0)
    mat.diffuse_color = (0.05, 0.045, 0.05, 1)


def lens_shader(mat, eyes):
    nb = NB(mat)
    glow = None; pupil = None
    for k, (front, axis) in enumerate(eyes):
        off = Vector((0.006 * S * (1 if k else -1), 0, 0.004 * S * (1 if k else 0)))
        gl = nb.sphere_mask(front.to_tuple(), 0.05 * S, 0.5)
        pu = nb.sphere_mask((front + off).to_tuple(), 0.03 * S if k else 0.04 * S, 0.3)
        glow = gl if glow is None else nb.math("MAXIMUM", glow, gl)
        pupil = pu if pupil is None else nb.math("MAXIMUM", pupil, pu)
    film = nb.noise(25.0, 4, 0.6)
    filmm = nb_map(nb, film.outputs["Fac"], 0.45, 0.65, 0.0, 0.35)
    c = nb.mix((0.006, 0.008, 0.006), (0.06, 0.08, 0.02), glow)
    c = nb.mix(c, (0.35, 0.37, 0.33), nb.math("MULTIPLY", filmm, 0.5))
    c = nb.mix(c, (0.0, 0.0, 0.0), pupil)
    e = nb.mix(nb.mix((0, 0, 0), (0.12, 0.17, 0.035), nb.math("MULTIPLY", glow, 0.8)), (0, 0, 0), pupil)
    nb_finish_full(nb, c, 0.04, film.outputs["Fac"], bump=0.05, dist=0.002, emit=e, emit_strength=1.0, spec=0.8)
    mat.diffuse_color = (0.2, 0.25, 0.1, 1)


gig_skin_v2(M_skin)
flesh_shader(M_flesh, (0.2, 0.01, 0.02))
simple_shader(M_fin, (0.045, 0.022, 0.028), 0.3, noise_scale=12, var=0.35, bump=0.25, veins=(9.0, (0.2, 0.01, 0.03), 0.6))
simple_shader(M_ray, (0.2, 0.15, 0.13), 0.4, noise_scale=40, var=0.2)
simple_shader(M_teeth, (0.7, 0.64, 0.48), 0.2, noise_scale=60, var=0.18, bump=0.1)
simple_shader(M_throat, (0.012, 0.0, 0.002), 0.25)
lens_shader(M_lens, EYES)
GIG_INFO = {"tris": sum(len(p.vertices) - 2 for p in body.data.polygons),
            "unweighted": sum(1 for v in body.data.vertices if not v.groups),
            "mats": [m.name for m in body.data.materials]}
print("GIG_INFO", GIG_INFO)
