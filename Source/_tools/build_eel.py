# Rebuild the horror deep-sea (gulper) eel body on the existing DeepSeaEel_Rig (bones + actions kept).
# exec after mk.py, rig.py, horror.py
random.seed(21)
S = 1.25
arm = bpy.data.objects["DeepSeaEel_Rig"]; col = bpy.data.collections["DeepSeaEel"]
prev_action = arm.animation_data.action if arm.animation_data else None
if arm.animation_data: arm.animation_data.action = None
for pb in arm.pose.bones: pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
old = bpy.data.objects.get("SK_DeepSeaEel_Body")
if old: _m = old.data; bpy.data.objects.remove(old); bpy.data.meshes.remove(_m)

M_skin  = bpy.data.materials.get("M_EelX_Skin") or bpy.data.materials.new("M_EelX_Skin")
M_pouch = bpy.data.materials.get("M_EelX_Pouch") or bpy.data.materials.new("M_EelX_Pouch")
M_flesh = mat("M_EelX_Flesh",   (0.25, 0.015, 0.03), rough=0.1)
M_throat= mat("M_EelX_Throat",  (0.04, 0.0, 0.005), rough=0.2)
M_teeth = mat("M_EelX_Teeth",   (0.62, 0.56, 0.38), rough=0.3)
M_fin   = mat("M_EelX_Fin",     (0.08, 0.02, 0.04), rough=0.35)
M_scl   = mat("M_EelX_Sclera",  (0.26, 0.29, 0.3), rough=0.3, emit=(0.2, 0.24, 0.28), strength=0.15)   # cataract-milky
M_pupil = mat("M_EelX_Pupil",   (0.004, 0.004, 0.004), rough=0.04)
M_cloud = mat("M_EelX_DeadPupil", (0.16, 0.17, 0.19), rough=0.35)
M_lure  = mat("M_EelX_LureEye", (0.85, 0.7, 0.68), rough=0.08, emit=(1.0, 0.3, 0.4), strength=4)
M_iris  = mat("M_EelX_LureIris", (0.5, 0.02, 0.04), rough=0.1, emit=(1.0, 0.05, 0.1), strength=8)
M_pus   = mat("M_EelX_Pustule", (0.75, 0.6, 0.2), rough=0.12, emit=(0.7, 0.5, 0.1), strength=3)

KEYS = [(-0.62,0,0,0.0),(-0.58,0.025,0.02,0.0),(-0.4,0.062,0.036,0.01),(-0.2,0.092,0.05,0.02),(0.0,0.122,0.09,0.0),
        (0.15,0.13,0.12,-0.02),(0.35,0.11,0.12,-0.02),(0.6,0.08,0.09,0.0),(1.0,0.055,0.06,0.0),(1.5,0.038,0.042,0.0),
        (2.0,0.025,0.028,0.0),(2.5,0.015,0.017,0.0),(2.9,0.008,0.009,0.0),(3.05,0.004,0.004,0.0),(3.08,0,0,0)]
def prof_at(y):
    for a, b in zip(KEYS, KEYS[1:]):
        if a[0] <= y <= b[0]:
            t = (y-a[0])/(b[0]-a[0]); return [a[i]+(b[i]-a[i])*t for i in range(4)]
    return KEYS[-1]
def radial(y, a, x, z):
    yu = y / S; s = 1.0
    if 0.0 < yu < 0.7: s += 0.035 * (0.5 + 0.5*math.sin(yu*95)) ** 3 * (1 - yu/0.7)       # neck skin folds
    top = math.exp(-((a - math.pi/2) / 0.2) ** 2)
    if 0.1 < yu < 2.8: s += 0.06 * top * (0.5 + 0.5*math.sin(yu*48)) ** 4                   # knobby spine
    side = abs(math.cos(a))
    if -0.5 < yu < -0.32: s -= 0.12 * side * math.exp(-((math.sin(a) - 0.4) / 0.35) ** 2)    # sunken eye sockets
    return s
def wrinkle(bm, amp=0.002, sc=60, seed=1):
    bm.normal_update(); off = Vector((seed, seed*2, seed*3))
    for v in bm.verts: v.co += v.normal * amp * noise.noise(v.co*sc + off)
    return bm
def sphere(r, center, segs=14, m=None):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=max(6, segs//2), radius=r)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts); return xf(bm, m) if m else bm
def hook(r, L, at, tilt_x, tilt_y, back=0.35):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=5, radius1=r, radius2=r*0.08, depth=L)
    bmesh.ops.translate(bm, vec=(0, 0, L/2), verts=bm.verts)
    for v in bm.verts: v.co.y += back * L * (v.co.z / L) ** 2          # teeth hook back toward the throat
    return xf(bm, T(*at) @ RX(tilt_x) @ RY(tilt_y))

# ---------------- body ----------------
ST = [(y*S, hx*S, hz*S, zc*S) for y, hx, hz, zc in smooth_stations(KEYS, 110)]
body = finish(col, "SK_DeepSeaEel_Body", loft_fn(ST, 36, radial), M_skin)
body.parent = arm; body.matrix_parent_inverse = Matrix.Identity(4)
subdivide_displace(body, levels=1, lumps=0.005*S, lump_scale=6, wrinkle=0.0018*S, wrinkle_scale=80, seed=5)
PAL = -0.014*S
body.data.materials.append(M_flesh)
for v in body.data.vertices:                                             # mouth roof
    if v.co.y < 0.04*S and v.co.z < PAL:
        w = min(1.0, (0.04*S - v.co.y) / (0.06*S)); v.co.z += (PAL - v.co.z) * w
for f in body.data.polygons:
    if f.center.y < 0.02*S and abs(f.center.z - PAL) < 0.003*S: f.material_index = 1
body.data.update()
extras = []
def add(name, bm, material):
    o = finish(col, name, bm, material); o.parent = arm; o.matrix_parent_inverse = Matrix.Identity(4); extras.append(o); return o
for sgn, nm in ((1, "dorsal"), (-1, "ventral")):                        # ragged fin ribbons
    top, bot = [], []
    for k in range(40):
        y = 0.4 + k*0.065; p = prof_at(y)
        rag = 0.02 * random.random() * (1 if k % 3 else 0.2)
        top.append((y, sgn*(p[2] + 0.03 - 0.0005*k + rag))); bot.append((y, sgn*p[2]*0.6))
    bm = bmesh.new()
    a1 = [bm.verts.new((-0.003, y*S, z*S)) for y, z in top]; a2 = [bm.verts.new((-0.003, y*S, z*S)) for y, z in bot]
    b1 = [bm.verts.new((0.003, y*S, z*S)) for y, z in top];  b2 = [bm.verts.new((0.003, y*S, z*S)) for y, z in bot]
    for i in range(len(top)-1):
        bm.faces.new((a2[i], a2[i+1], a1[i+1], a1[i])); bm.faces.new((b1[i], b1[i+1], b2[i+1], b2[i]))
        bm.faces.new((a1[i], a1[i+1], b1[i+1], b1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    add(f"ex_{nm}", bm, M_fin)
for k in range(10):                                                      # weeping pustules along the body
    y = random.uniform(0.3, 2.2); p = prof_at(y); a = random.uniform(-1.2, 1.2) + (math.pi if random.random() < 0.5 else 0)
    r = random.uniform(0.006, 0.014)*S
    c = Vector((p[1]*S*math.cos(a), y*S, (p[3] + p[2]*math.sin(a))*S))
    add(f"ex_pus_{k}", sphere(r, c.to_tuple(), 10), M_pus)
for k in range(5):                                                       # extra eyes growing in the wrong places
    y = random.uniform(0.05, 0.5); p = prof_at(y); a = random.uniform(0.2, 1.2) * random.choice((1, -1)) + (0 if random.random() < 0.5 else math.pi)
    c = Vector((p[1]*S*math.cos(a)*0.97, y*S, (p[3] + p[2]*math.sin(a))*S))
    r = random.uniform(0.008, 0.016)*S
    add(f"ex_xeye_{k}", sphere(r, c.to_tuple(), 12), M_scl)
    add(f"ex_xpup_{k}", sphere(r*0.45, (c + c.normalized()*0.0 + Vector((math.cos(a), 0, math.sin(a)))*r*0.85).to_tuple(), 8), M_pupil)
# tail lure: fleshy stalks ending in glowing eyeballs that stare in different directions
tip = Vector((0, 3.06*S, 0))
for k in range(6):
    a = k/6*math.tau; L = random.uniform(0.06, 0.13)
    d = Vector((0.6*math.cos(a), 1.0, 0.6*math.sin(a))).normalized()
    pts = [tip, tip + d*L*0.5 + Vector((0, 0, 0.01*math.sin(k))), tip + d*L]
    add(f"ex_stalk_{k}", tube(catmull(pts, 4), lambda s: 0.006*(1 - 0.5*s), up=(1,0,0), sides=6), M_fin)
    r = random.uniform(0.014, 0.022)
    ctr = tip + d*(L + r*0.6)
    add(f"ex_lure_{k}", sphere(r, ctr.to_tuple(), 14), M_lure)
    look = (d + Vector((random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.2), random.uniform(-0.6, 0.6)))).normalized()
    rot = look.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    add(f"ex_liris_{k}", sphere(r*0.62, (0, 0, 0), 12, T(*(ctr + look*r*0.86)) @ rot @ Matrix.Scale(0.3, 4, (0, 0, 1))), M_iris)
    add(f"ex_lpup_{k}", sphere(r*0.3, (0, 0, 0), 10, T(*(ctr + look*r*0.98)) @ rot @ Matrix.Scale(0.4, 4, (0, 0, 1))), M_pupil)
bpy.ops.object.select_all(action="DESELECT")
for o in [body] + extras: o.select_set(True)
bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
body.data.shade_smooth()

# ---------------- weights ----------------
spines = [f"eel_spine_{i:02d}" for i in range(1, 13)]
distance_weights(body, arm, spines, falloff=3.0, top=2)
blend_region(body, "eel_head", lambda c: max(0.0, min(1.0, (0.12*S - c.y) / (0.15*S))))

# ---------------- giant pouch jaw (wrinkled membrane outside, wet flesh inside) ----------------
POUCH = [(-0.6,0,0,-0.03),(-0.55,0.04,0.03,-0.05),(-0.4,0.095,0.1,-0.1),(-0.2,0.135,0.17,-0.16),(0.0,0.135,0.15,-0.13),(0.08,0,0,-0.06)]
def pouch_at(y):
    for a, b in zip(POUCH, POUCH[1:]):
        if a[0] <= y <= b[0]:
            t = (y-a[0])/(b[0]-a[0]); return [a[i]+(b[i]-a[i])*t for i in range(4)]
    return POUCH[-1]
def pouch_radial(y, a, x, z):
    return 1.0 + 0.05 * (0.5 + 0.5*math.sin(a*14 + y*20)) ** 3                         # stretch folds
pouch = loft_fn([(y*S, hx*S, hz*S, zc*S) for y, hx, hz, zc in smooth_stations(
        [(-0.6,0,0,-0.03),(-0.55,0.04,0.03,-0.05),(-0.4,0.095,0.1,-0.1),(-0.2,0.135,0.17,-0.16),(0.0,0.135,0.15,-0.13),(0.08,0,0,-0.06)], 30)], 36, pouch_radial)
wrinkle(pouch, 0.003, 60, 3); pouch.normal_update()
inner = pouch.copy()
bmesh.ops.delete(pouch, geom=[f for f in pouch.faces if f.normal.z > 0.4 and f.calc_center_median().z > -0.07*S], context="FACES")
bmesh.ops.delete(inner, geom=[f for f in inner.faces if not (f.normal.z > 0.4 and f.calc_center_median().z > -0.07*S)], context="FACES")
rigid_bm_to_group(body, pouch, M_pouch, "eel_jaw")
rigid_bm_to_group(body, wrinkle(inner, 0.004, 90, 7), M_flesh, "eel_jaw")
for k in range(7):                                                       # gill-like ridges inside the pouch
    yy = (-0.45 + k*0.07)*S
    w = 0.12*S*min(1.0, (yy/S + 0.6)/0.3)
    rr = catmull([Vector((-w*0.8, yy, -0.07*S)), Vector((0, yy + 0.02*S, -0.11*S)), Vector((w*0.8, yy, -0.07*S))], 6)
    rigid_bm_to_group(body, wrinkle(tube(rr, 0.006*S, up=(0,1,0), sides=6), 0.002, 120, k), M_flesh, "eel_jaw")
rigid_bm_to_group(body, sphere(0.06*S, (0, 0.05*S, PAL - 0.02*S), 14), M_throat, "eel_head")
# rows of hooked teeth on both jaws
for y in [-0.56 + i*0.028 for i in range(22)]:
    p = prof_at(y); pp = prof_at(min(0.05, y))
    for sx in (-1, 1):
        for row in range(2):
            x = sx*(p[1]*0.92 - 0.01*row)*S
            L = random.uniform(0.018, 0.04)*S * (1.6 if random.random() < 0.12 else 1.0)
            rigid_bm_to_group(body, hook(0.004*S, L, (x, y*S, PAL), 180 + random.uniform(-15, 15), sx*random.uniform(0, 15)), M_teeth, "eel_head")
            q = pouch_at(y); u = 0.72 - 0.08*row                      # sit on the pouch rim surface
            xl = sx*q[1]*u*S; zl = (q[3] + q[2]*math.sqrt(max(0.0, 1 - u*u)))*S - 0.004*S
            rigid_bm_to_group(body, hook(0.004*S, L*0.9, (xl, y*S, zl), random.uniform(-15, 15), -sx*random.uniform(0, 15)), M_teeth, "eel_jaw")
# sunken milky eyes
for sx in (-1, 1):
    c = Vector((sx*0.05*S, -0.41*S, 0.022*S))
    rigid_bm_to_group(body, sphere(0.017*S, c.to_tuple(), 14), M_scl, "eel_head")
    rigid_bm_to_group(body, sphere(0.008*S, (c + Vector((sx*0.012*S, -0.004*S, 0.003*S))).to_tuple(), 8), M_cloud, "eel_head")
    rigid_bm_to_group(body, wrinkle(torus(0.018*S, 0.005*S, 16, 6, T(*c) @ RY(90*sx)), 0.0015, 150, sx), M_skin, "eel_head")   # puffy lids

mod = body.modifiers.get("Armature") or body.modifiers.new("Armature", "ARMATURE"); mod.object = arm
if prev_action: arm.animation_data.action = prev_action
eel_skin_shader(M_skin); eel_pouch_shader(M_pouch); flesh_shader(M_flesh, (0.22, 0.012, 0.025))
sick_eye_shader(M_scl, (0.36, 0.38, 0.37), 0.08)
EEL_INFO = {"tris": sum(len(p.vertices)-2 for p in body.data.polygons),
            "unweighted": sum(1 for v in body.data.vertices if not v.groups),
            "mats": [m.name for m in body.data.materials]}
