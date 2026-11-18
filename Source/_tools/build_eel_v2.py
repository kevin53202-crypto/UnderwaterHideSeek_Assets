# Deep-sea (gulper) eel v2 (2026-11-09) on the existing DeepSeaEel_Rig (bones + actions kept).
# Slender whip body, long jaws with a pleated membrane pouch, tiny milky eyes at the snout, fin fringes,
# glowing eyeball lure at the tail tip.
# exec after mk.py, rig.py, horror.py, horror2.py
random.seed(23)
S = 1.25
arm = bpy.data.objects["DeepSeaEel_Rig"]; col = bpy.data.collections["DeepSeaEel"]
prev_action = arm.animation_data.action if arm.animation_data else None
if arm.animation_data: arm.animation_data.action = None
for pb in arm.pose.bones: pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
old = bpy.data.objects.get("SK_DeepSeaEel_Body")
if old: _om = old.data; bpy.data.objects.remove(old); bpy.data.meshes.remove(_om)


def _m(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)
M_skin, M_pouch, M_flesh, M_throat = _m("M_EelX_Skin"), _m("M_EelX_Pouch"), _m("M_EelX_Flesh"), _m("M_EelX_Throat")
M_teeth, M_fin, M_eye = _m("M_EelX_Teeth"), _m("M_EelX_Fin"), _m("M_EelX_Eye")
M_lflesh, M_leye, M_liris, M_pupil = _m("M_EelX_LureFlesh"), _m("M_EelX_LureEye"), _m("M_EelX_LureIris"), _m("M_EelX_Pupil")

KEYS = [(-0.62,0,0,0.004),(-0.605,0.012,0.011,0.004),(-0.56,0.026,0.019,0.006),(-0.42,0.042,0.027,0.009),(-0.22,0.064,0.038,0.012),
        (-0.02,0.094,0.066,0.01),(0.12,0.118,0.1,-0.008),(0.3,0.11,0.108,-0.015),(0.6,0.082,0.09,0.0),(1.0,0.052,0.066,0.0),
        (1.5,0.033,0.048,0.0),(2.0,0.02,0.032,0.0),(2.5,0.011,0.019,0.0),(2.9,0.006,0.01,0.0),(3.04,0.003,0.004,0.0),(3.07,0,0,0)]
DEPTH = [(-0.6, 0.0), (-0.5, 0.04), (-0.35, 0.11), (-0.18, 0.18), (-0.02, 0.165), (0.08, 0.06)]
PAL = -0.006 * S


def prof(keys, y):
    for a, b in zip(keys, keys[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0]); return [a[i] + (b[i] - a[i]) * t for i in range(len(a))]
    return list(keys[0]) if y < keys[0][0] else list(keys[-1])
p_at = lambda y: prof(KEYS, y)


def radial(y, a, x, z):
    yu = y / S; s = 1.0
    if 0.0 < yu < 0.7: s += 0.025 * (0.5 + 0.5 * math.sin(yu * 95)) ** 3 * (1 - yu / 0.7)       # loose neck folds
    if 0.1 < yu < 2.8: s += 0.025 * math.exp(-((a - math.pi / 2) / 0.18) ** 2)                 # spine ridge
    if 0.4 < yu: s *= 1.0 - 0.18 * abs(math.cos(a)) * min(1.0, (yu - 0.4) / 1.0)               # flatter tail
    return s


# ---------------- body ----------------
ST = [(y * S, hx * S, hz * S, zc * S) for y, hx, hz, zc in smooth_stations(KEYS, 150)]
body = finish(col, "SK_DeepSeaEel_Body", loft_fn(ST, 36, radial), M_skin)
body.parent = arm; body.matrix_parent_inverse = Matrix.Identity(4)
subdivide_displace(body, levels=1, lumps=0.003 * S, lump_scale=6, wrinkle=0.0006 * S, wrinkle_scale=90, seed=5)
me = body.data
for v in me.vertices:                                                    # flat palate under the upper jaw
    if v.co.y < 0.06 * S and v.co.z < PAL:
        w = smoothstep(0.0, 1.0, (0.06 * S - v.co.y) / (0.08 * S)); v.co.z += (PAL - v.co.z) * w
me.update()
me.materials.append(M_flesh)
for f in me.polygons:
    if f.center.y < 0.04 * S and abs(f.center.z - PAL) < 0.002 * S and f.normal.z < -0.5: f.material_index = 1

extras = []
def add(name, bm, material):
    o = finish(col, name, bm, material); o.parent = arm; o.matrix_parent_inverse = Matrix.Identity(4); extras.append(o); return o
SC = Matrix.Scale(S, 4)
for sgn, nm, y0, y1 in ((1, "dorsal", 0.45, 2.95), (-1, "anal", 0.6, 2.95)):      # continuous fin fringes
    N = 46
    base, tips = [], []
    for i in range(N):
        t = i / (N - 1); y = y0 + (y1 - y0) * t; p = p_at(y)
        h = 0.004 + 0.026 * math.sin(math.pi * min(1.0, t * 1.15)) ** 0.6
        base.append((y, p[3] + sgn * p[2] * 0.97)); tips.append((y + 0.02, p[3] + sgn * (p[2] + h)))
    mb, rb = ray_fin(base, tips, 0.004, SC, rows=3, ray_every=2, scallop=0.12, tears=((17, 0.5),) if sgn > 0 else ((30, 0.4),), ray_r=0.0018)
    add(f"ex_{nm}", mb, M_fin); add(f"ex_{nm}_rays", rb, M_fin)

# tail lure: a swollen translucent bulb studded with glowing eyeballs, trailing filaments
tip = Vector((0, 3.07 * S, 0))
bulb = bmesh.new(); bmesh.ops.create_uvsphere(bulb, u_segments=20, v_segments=12, radius=1.0)
for v in bulb.verts:
    v.co = Vector((v.co.x * 0.026, v.co.y * 0.045, v.co.z * 0.026)) * S
    v.co += v.co.normalized() * 0.003 * noise.noise(v.co * 60)
xf(bulb, T(0, 3.1 * S, 0))
add("ex_bulb", bulb, M_lflesh)
stalk = tube([tip - Vector((0, 0.06, 0)), tip, Vector((0, 3.075 * S, 0))], lambda s: 0.006, up=(1, 0, 0), sides=8)
add("ex_bulb_stalk", stalk, M_lflesh)
for k, (dx, dy, dz, r) in enumerate([(1, -0.2, 0.3, 0.017), (-1, 0.1, 0.4, 0.014), (0.2, 0.3, -1, 0.016), (-0.5, 0.6, -0.6, 0.012), (0.6, 0.7, 0.7, 0.011)]):
    d = Vector((dx, dy, dz)).normalized()
    ctr = Vector((0, 3.1 * S, 0)) + Vector((d.x * 0.026, d.y * 0.045, d.z * 0.026)) * S * 0.9
    look = (d + Vector((random.uniform(-0.5, 0.5), random.uniform(-0.3, 0.3), random.uniform(-0.5, 0.5)))).normalized()
    rot = look.to_track_quat("Z", "Y").to_matrix().to_4x4()
    add(f"ex_leye_{k}", uvsphere(r, T(*ctr), 16, 10), M_leye)
    add(f"ex_liris_{k}", uvsphere(r * 0.6, T(*(ctr + look * r * 0.84)) @ rot @ Matrix.Diagonal((1, 1, 0.32, 1)), 14, 8), M_liris)
    add(f"ex_lpup_{k}", uvsphere(r * 0.28, T(*(ctr + look * r * 1.0)) @ rot @ Matrix.Diagonal((0.55 if k % 2 else 1, 1, 0.3, 1)), 10, 6), M_pupil)
for k in range(4):                                                          # trailing filaments
    a = k / 4 * math.tau + 0.4
    pts = [Vector((0, 3.14 * S, 0))]
    for i in range(1, 6):
        t = i / 5
        pts.append(Vector((0.02 * math.cos(a) * t + 0.01 * math.sin(i * 1.7 + k), 3.14 * S + 0.12 * t, 0.02 * math.sin(a) * t)))
    add(f"ex_fil_{k}", tube(catmull(pts, 3), lambda s: 0.0028 * (1 - 0.7 * s), up=(1, 0, 0), sides=5), M_lflesh)

bpy.ops.object.select_all(action="DESELECT")
for o in [body] + extras: o.select_set(True)
bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
body.data.shade_smooth()

# ---------------- weights ----------------
spines = [f"eel_spine_{i:02d}" for i in range(1, 13)]
distance_weights(body, arm, spines, falloff=3.0, top=2)
blend_region(body, "eel_head", lambda c: max(0.0, min(1.0, (0.12 * S - c.y) / (0.15 * S))))

# ---------------- jaws + pleated pouch ----------------
d_at = lambda y: prof(DEPTH, y)[1]
def rim(y, sx):
    p = p_at(y); return Vector((sx * p[1] * 0.92 * S, y * S, PAL - 0.005 * S))
NY, NT = 44, 44
grid = []
pb = bmesh.new()
for i in range(NY):
    y = -0.585 + (0.08 + 0.585) * i / (NY - 1)
    p = p_at(y); w = p[1] * 0.92; d = d_at(y); bw = max(w, 0.48 * d); zr = PAL / S - 0.005
    row = []
    for j in range(NT):
        th = math.pi * j / (NT - 1)
        sn = math.sin(th)
        x = math.cos(th) * (w * (1 - sn) + bw * sn)
        z = -d * sn ** 0.9
        pleat = 1 + 0.05 * math.sin(th * 18 + y * 8) * sn * min(1.0, d / 0.06)
        row.append(pb.verts.new((x * pleat * S, y * S, (zr + z * pleat) * S)))
    grid.append(row)
for i in range(NY - 1):
    for j in range(NT - 1):
        pb.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
bmesh.ops.remove_doubles(pb, verts=pb.verts, dist=1e-6)
for v in pb.verts:                                                            # slight sag / unevenness
    v.co += Vector((noise.noise(v.co * 25), 0, noise.noise(v.co * 25 + Vector((3, 3, 3))))) * 0.004
bmesh.ops.recalc_face_normals(pb, faces=pb.faces)
pb.normal_update()
res = bmesh.ops.solidify(pb, geom=pb.faces[:], thickness=0.004 * S)
pb.normal_update()
inner = pb.copy()
def facing_in(f):
    c = f.calc_center_median(); yu = c.y / S
    axis = Vector((0, c.y, PAL - d_at(yu) * S * 0.5))
    return f.normal.dot(axis - c) > 0
bmesh.ops.delete(pb, geom=[f for f in pb.faces if facing_in(f)], context="FACES")
bmesh.ops.delete(inner, geom=[f for f in inner.faces if not facing_in(f)], context="FACES")
rigid_bm_to_group(body, pb, M_pouch, "eel_jaw")
rigid_bm_to_group(body, inner, M_flesh, "eel_jaw")
for sx in (-1, 1):                                                            # thin lower-jaw bones along the pouch rims
    pts = [rim(-0.6 + 0.66 * k / 10, sx) for k in range(11)]
    rigid_bm_to_group(body, tube(catmull(pts, 3), lambda s: (0.0035 + 0.003 * s) * S, up=(0, 0, 1), sides=8), M_skin, "eel_jaw")
rigid_bm_to_group(body, xf(lathe([(0, 0), (0.05 * S, 0.0), (0.055 * S, 0.05 * S), (0.0, 0.08 * S)], 14), T(0, 0.06 * S, PAL - 0.08 * S)), M_throat, "eel_head")
for y in [-0.585 + i * 0.022 for i in range(29)]:                            # needle teeth on both jaws
    p = p_at(y)
    for sx in (-1, 1):
        L = random.uniform(0.012, 0.026) * S * (1.9 if random.random() < 0.15 else 1.0)
        up = Vector((sx * p[1] * 0.85 * S, y * S, PAL))
        rigid_bm_to_group(body, needle(0.0028 * S, L, up.to_tuple(), 180 + random.uniform(-12, 12), sx * random.uniform(0, 14), -0.25, segs=5), M_teeth, "eel_head")
        lo = rim(y, sx) + Vector((-sx * 0.002 * S, 0, 0.003 * S))
        L2 = random.uniform(0.01, 0.024) * S * (1.8 if random.random() < 0.15 else 1.0)
        rigid_bm_to_group(body, needle(0.0026 * S, L2, lo.to_tuple(), random.uniform(-12, 12), sx * random.uniform(0, 14), 0.25, segs=5), M_teeth, "eel_jaw")
for sx in (-1, 1):                                                            # tiny milky eyes at the snout
    c = Vector((sx * 0.021 * S, -0.53 * S, 0.012 * S))
    rigid_bm_to_group(body, uvsphere(0.0085 * S, T(*c), 16, 10), M_eye, "eel_head")
    rigid_bm_to_group(body, torus(0.0088 * S, 0.0022 * S, 16, 6, T(*c) @ RY(90 * sx) @ T(0, 0, -0.002)), M_skin, "eel_head")

mod = body.modifiers.get("Armature") or body.modifiers.new("Armature", "ARMATURE"); mod.object = arm
if prev_action: arm.animation_data.action = prev_action


def _eprof(co):
    p = p_at(max(-0.619, min(3.069, co.y / S)))
    hx = max(1e-3, p[1] * S); hz = max(1e-3, p[2] * S)
    a = math.atan2((co.z - p[3] * S) / hz, co.x / hx)
    return (math.sin(a), co.y, abs(math.cos(a)))
set_profile_attr(body, "eprof", _eprof)


# ---------------- shaders ----------------
def eel_skin_v2(mat):
    nb = NB(mat)
    s, y, c = nb_attr(nb, "eprof")
    belly_t = nb_map(nb, s, -0.9, -0.1); dors_t = nb_map(nb, s, 0.1, 0.7)
    col_ = nb.mix((0.07, 0.04, 0.045), (0.028, 0.018, 0.022), belly_t)
    col_ = nb.mix(col_, (0.006, 0.005, 0.007), dors_t)
    mott = nb.noise(4.0, 6, 0.62)
    col_ = nb.mix(col_, nb.ramp(mott.outputs["Fac"], [(0.3, (0.55, 0.55, 0.55)), (0.72, (1.0, 1.0, 1.0))]).outputs[0], 1.0, "MULTIPLY")
    sc_n = nb.noise(5.0, 3, 0.5, distortion=1.2, vec=nb.mapping(scale=(4, 0.5, 4)))
    scars = nb.ramp(sc_n.outputs["Fac"], [(0.494, (0, 0, 0)), (0.5, (1, 1, 1)), (0.506, (0, 0, 0))]).outputs[0]
    scar_m = nb.math("MULTIPLY", scars, nb_map(nb, nb.noise(2.0, 2).outputs["Fac"], 0.5, 0.6))
    col_ = nb.mix(col_, (0.22, 0.17, 0.17), nb.math("MULTIPLY", scar_m, 0.6))
    vn = nb.noise(9.0, 4, 0.5, distortion=3.0)
    veins = nb.ramp(vn.outputs["Fac"], [(0.487, (0, 0, 0)), (0.5, (1, 1, 1)), (0.513, (0, 0, 0))]).outputs[0]
    col_ = nb.mix(col_, (0.16, 0.0, 0.03), nb.math("MULTIPLY", veins, nb.math("ADD", nb.math("MULTIPLY", nb.math("SUBTRACT", 1.0, belly_t), 0.5), 0.15)))
    pores = nb.math("MAXIMUM", nb_dot_row(nb, s, y, 0.05, 0.03, 0.3, 0.05, 0.1 * S, 3.0 * S),
                    nb_dot_row(nb, s, y, -0.25, 0.04, 0.28, 0.05, 0.1 * S, 2.2 * S, 0.5))
    col_ = nb.mix(col_, (0.25, 0.2, 0.2), nb.math("MULTIPLY", pores, 0.7))
    slime = nb.noise(14.0, 4, 0.6)
    rough = nb_map(nb, slime.outputs["Fac"], 0.3, 0.7, 0.1, 0.32)
    wr = nb.noise(70.0, 6, 0.6, vec=nb.mapping(scale=(1, 0.3, 1)))
    h = nb.math("ADD", nb.math("MULTIPLY", wr.outputs["Fac"], 0.4), nb.math("MULTIPLY", veins, 0.3), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", scar_m, 0.5), clamp=False)
    h = nb.math("SUBTRACT", h, nb.math("MULTIPLY", pores, 0.5), clamp=False)
    nb_finish_full(nb, col_, rough, h, bump=0.3, dist=0.008, spec=0.6)
    mat.diffuse_color = (0.02, 0.015, 0.018, 1)


def pouch_v2(mat):
    nb = NB(mat)
    mott = nb.noise(6.0, 5, 0.6)
    col_ = nb.ramp(mott.outputs["Fac"], [(0.3, (0.012, 0.007, 0.01)), (0.7, (0.05, 0.022, 0.03))]).outputs[0]
    vn = nb.noise(6.0, 5, 0.55, distortion=4.0)
    veins = nb.ramp(vn.outputs["Fac"], [(0.47, (0, 0, 0)), (0.5, (1, 1, 1)), (0.53, (0, 0, 0))]).outputs[0]
    vn2 = nb.noise(18.0, 4, 0.5, distortion=3.0)
    veins2 = nb.ramp(vn2.outputs["Fac"], [(0.49, (0, 0, 0)), (0.5, (1, 1, 1)), (0.51, (0, 0, 0))]).outputs[0]
    vm = nb.math("MAXIMUM", veins, nb.math("MULTIPLY", veins2, 0.6))
    col_ = nb.mix(col_, (0.12, 0.008, 0.025), nb.math("MULTIPLY", vm, 0.4))
    folds = nb.noise(28.0, 4, 0.5, vec=nb.mapping(scale=(3, 0.3, 0.3)))
    h = nb.math("ADD", nb.math("MULTIPLY", folds.outputs["Fac"], 0.5), nb.math("MULTIPLY", vm, 0.6), clamp=False)
    nb_finish_full(nb, col_, 0.22, h, bump=0.4, dist=0.006, spec=0.6)
    mat.diffuse_color = (0.03, 0.015, 0.02, 1)


eel_skin_v2(M_skin); pouch_v2(M_pouch)
flesh_shader(M_flesh, (0.17, 0.008, 0.02))
simple_shader(M_throat, (0.01, 0.0, 0.002), 0.25)
simple_shader(M_teeth, (0.62, 0.57, 0.44), 0.2, noise_scale=80, var=0.15, bump=0.1)
simple_shader(M_fin, (0.03, 0.018, 0.024), 0.25, noise_scale=10, var=0.4, bump=0.2, veins=(10.0, (0.14, 0.01, 0.03), 0.5))
simple_shader(M_eye, (0.1, 0.12, 0.13), 0.05, noise_scale=120, var=0.5, bump=0.05, emit=(0.15, 0.2, 0.22), emit_strength=0.3)
simple_shader(M_lflesh, (0.5, 0.12, 0.2), 0.15, noise_scale=40, var=0.35, bump=0.2, emit=(0.9, 0.12, 0.35), emit_strength=0.45, veins=(25.0, (0.25, 0.0, 0.05), 0.7))
simple_shader(M_leye, (0.85, 0.62, 0.6), 0.08, noise_scale=50, var=0.15, bump=0.1, emit=(1.0, 0.4, 0.45), emit_strength=0.5, veins=(30.0, (0.6, 0.02, 0.05), 0.9))
simple_shader(M_liris, (0.7, 0.05, 0.08), 0.1, noise_scale=90, var=0.3, emit=(1.0, 0.12, 0.18), emit_strength=1.0)
simple_shader(M_pupil, (0.002, 0.002, 0.002), 0.04, var=0.0)
EEL_INFO = {"tris": sum(len(p.vertices) - 2 for p in body.data.polygons),
            "unweighted": sum(1 for v in body.data.vertices if not v.groups),
            "mats": [m.name for m in body.data.materials]}
print("EEL_INFO", EEL_INFO)
