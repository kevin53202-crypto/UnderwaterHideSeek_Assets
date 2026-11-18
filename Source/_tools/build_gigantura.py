# Rebuild the horror Gigantura body on the existing Gigantura_Rig (bones + actions are kept).
# exec after mk.py, rig.py, horror.py
random.seed(7)
S = 1.2
arm = bpy.data.objects["Gigantura_Rig"]; col = bpy.data.collections["Gigantura"]
prev_action = arm.animation_data.action if arm.animation_data else None
if arm.animation_data: arm.animation_data.action = None
for pb in arm.pose.bones: pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
old = bpy.data.objects.get("SK_Gigantura_Body")
if old: _m = old.data; bpy.data.objects.remove(old); bpy.data.meshes.remove(_m)

M_skin  = bpy.data.materials.get("M_GigX_Skin") or bpy.data.materials.new("M_GigX_Skin")
M_fin   = mat("M_GigX_Fin",     (0.12, 0.015, 0.025), rough=0.4)
M_bone  = mat("M_GigX_Bone",    (0.42, 0.33, 0.22), rough=0.45)
M_teeth = mat("M_GigX_Teeth",   (0.7, 0.62, 0.4), rough=0.3)
M_gum   = mat("M_GigX_Gum",     (0.3, 0.02, 0.04), rough=0.15)
M_flesh = mat("M_GigX_Flesh",   (0.22, 0.01, 0.02), rough=0.1)
M_throat= mat("M_GigX_Throat",  (0.05, 0.0, 0.005), rough=0.2)
M_scl   = mat("M_GigX_Sclera",  (0.75, 0.76, 0.6), rough=0.08, emit=(0.5, 0.65, 0.4), strength=1.2)
M_pupil = mat("M_GigX_Pupil",   (0.004, 0.004, 0.004), rough=0.04)
M_pus   = mat("M_GigX_Pustule", (0.65, 0.8, 0.18), rough=0.12, emit=(0.55, 0.85, 0.12), strength=5)
M_worm  = mat("M_GigX_Worm",    (0.75, 0.5, 0.45), rough=0.2)

KEYS = [(-1.25,0,0,0.0),(-1.22,0.04,0.05,0.0),(-1.12,0.12,0.17,0.03),(-0.98,0.17,0.25,0.06),(-0.82,0.18,0.27,0.06),
        (-0.66,0.155,0.235,0.04),(-0.45,0.155,0.23,0.02),(-0.15,0.13,0.2,0.01),(0.15,0.105,0.155,0.0),(0.45,0.08,0.11,0.0),
        (0.72,0.055,0.075,0.0),(0.95,0.035,0.045,0.0),(1.1,0.018,0.025,0.0),(1.14,0,0,0)]
WOUND = (-0.21, 0.19)           # (y, radius) unscaled, on the +X flank

def hx_at(y):
    for a, b in zip(KEYS, KEYS[1:]):
        if a[0] <= y <= b[0]:
            t = (y-a[0])/(b[0]-a[0]); return [a[i]+(b[i]-a[i])*t for i in range(4)]
    return KEYS[-1]

def radial(y, a, x, z):
    yu = y / S; s = 1.0
    side = abs(math.cos(a)) ** 1.5
    if -0.62 < yu < 0.3:
        rib = max(0.0, math.sin(yu * math.tau * 9)) ** 5
        s -= 0.075 * side * (1 - rib)
        if math.sin(a) < 0: s -= 0.06 * abs(math.sin(a)) * math.sin(math.pi * (yu + 0.62) / 0.92)
    top = math.exp(-((a - math.pi/2) / 0.16) ** 2)
    if -0.75 < yu < 0.9: s += 0.09 * top * (0.5 + 0.5 * math.sin(yu * math.tau * 13)) ** 3
    if -1.0 < yu < -0.72: s -= 0.06 * side * math.exp(-((math.sin(a) - 0.45) / 0.3) ** 2)
    # torn wound crater on the +X flank
    d = math.hypot((yu - WOUND[0]) / WOUND[1], math.sin(a) / 0.55)
    if math.cos(a) > 0 and d < 1.0: s -= 0.16 * (1 - d * d)
    return s

def wrinkle(bm, amp=0.002, sc=60, seed=1):
    bm.normal_update(); off = Vector((seed, seed*2, seed*3))
    for v in bm.verts: v.co += v.normal * amp * noise.noise(v.co*sc + off)
    return bm

def sphere(r, center, segs=16, m=None):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=max(6, segs//2), radius=r)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts); return xf(bm, m) if m else bm

def fang(r, L, at, tilt_x, tilt_y):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=r, radius2=r*0.08, depth=L)
    bmesh.ops.translate(bm, vec=(0, 0, L/2), verts=bm.verts)
    for v in bm.verts: v.co.y += 0.25 * L * (v.co.z / L) ** 2
    return xf(bm, T(*at) @ RX(tilt_x) @ RY(tilt_y))

def jag_fin(base, thick, teeth=10, depth=0.03):
    pts = []
    for (y0, z0), (y1, z1) in zip(base, base[1:] + base[:1]):
        pts.append((y0, z0))
        for k in range(1, teeth):
            t = k / teeth; y = y0 + (y1-y0)*t; z = z0 + (z1-z0)*t
            j = depth * (random.random()*0.9 + 0.1) * (1 if k % 2 else -0.3)
            pts.append((y + j*0.3, z + j))
    bm = bmesh.new()
    a = [bm.verts.new((-thick/2, y*S, z*S)) for y, z in pts]; b = [bm.verts.new((thick/2, y*S, z*S)) for y, z in pts]
    bm.faces.new(a); bm.faces.new(list(reversed(b)))
    for i in range(len(pts)):
        j = (i+1) % len(pts); bm.faces.new((a[i], b[i], b[j], a[j]))
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm

def ray_spines(base_pts, tip_pts, r=0.004):
    bm = bmesh.new()
    for (y0, z0), (y1, z1) in zip(base_pts, tip_pts):
        part = tube([Vector((0, y0*S, z0*S)), Vector((0, y1*S, z1*S))], lambda s: r*(1-0.85*s), up=(1,0,0), sides=5)
        tmp = bpy.data.meshes.new("_r"); part.to_mesh(tmp); part.free(); bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    return bm

# ---------------- deformable body ----------------
ST = [(y*S, hx*S, hz*S, zc*S) for y, hx, hz, zc in smooth_stations(KEYS, 72)]
body = finish(col, "SK_Gigantura_Body", loft_fn(ST, 48, radial), M_skin)
body.parent = arm; body.matrix_parent_inverse = Matrix.Identity(4)
subdivide_displace(body, levels=1, lumps=0.007*S, lump_scale=5, wrinkle=0.0022*S, wrinkle_scale=70, seed=3)
# open the mouth: flatten the underside of the snout into a wet palate (the jaw closes against it)
PAL = -0.045*S
body.data.materials.append(M_flesh)
for v in body.data.vertices:
    if v.co.y < -0.8*S and v.co.z < PAL:
        w = min(1.0, (-0.8*S - v.co.y) / (0.05*S))
        v.co.z = v.co.z + (PAL - v.co.z) * w
for f in body.data.polygons:
    c = f.center
    if c.y < -0.83*S and abs(c.z - PAL) < 0.004*S:
        f.material_index = 1
body.data.update()
extras = []
def add(name, bm, material):
    o = finish(col, name, bm, material); o.parent = arm; o.matrix_parent_inverse = Matrix.Identity(4); extras.append(o); return o
add("gx_dorsal", jag_fin([(0.3,0.1),(0.5,0.3),(0.85,0.24),(0.92,0.06)], 0.01, 12, 0.035), M_fin)
add("gx_dorsal_rays", ray_spines([(0.35+0.06*k, 0.1) for k in range(9)], [(0.38+0.065*k, 0.34 - 0.012*k) for k in range(9)]), M_bone)
add("gx_anal", jag_fin([(0.28,-0.11),(0.5,-0.3),(0.8,-0.24),(0.92,-0.05)], 0.01, 12, 0.035), M_fin)
add("gx_caudal", jag_fin([(1.0,0.02),(1.22,0.2),(1.28,0.14),(1.15,0.0),(1.45,-0.12),(1.85,-0.27),(2.08,-0.33),(1.88,-0.17),(1.3,-0.04),(1.0,-0.03)], 0.009, 6, 0.03), M_fin)
# wound: wet flesh lining the crater, half-buried yellowed ribs, worms crawling out
wy, wr = WOUND
p = hx_at(wy)
flesh = sphere(1.0, (0, 0, 0), 24)
for v in flesh.verts:
    v.co = Vector((v.co.x * 0.03*S, v.co.y * wr*0.8*S, v.co.z * p[2]*0.55*S))
xf(flesh, T(p[1]*S*0.8, wy*S, p[3]*S))
add("gx_wound_flesh", wrinkle(flesh, 0.006, 40, 6), M_flesh)
for k in range(5):
    yu = wy - 0.13 + k*0.065; pp = hx_at(yu); arc = []
    for j in range(11):
        a = math.radians(-42 + 84*j/10)
        arc.append(Vector((pp[1]*S*math.cos(a)*0.97, yu*S, (pp[3] + pp[2]*math.sin(a))*S*0.95)))
    add(f"gx_rib_{k}", wrinkle(tube(arc, lambda s: 0.009*(1 - 0.35*abs(2*s-1)), up=(0,1,0), sides=6), 0.0015, 120, k), M_bone)
for k in range(9):
    yu = wy + random.uniform(-0.12, 0.12); pp = hx_at(yu); z0 = random.uniform(-0.25, 0.25)
    base = Vector((pp[1]*S*0.86, yu*S, (pp[3] + z0*pp[2])*S))
    pts = [base + Vector((0.012*i + 0.014*math.sin(i*1.7+k), 0.014*math.sin(i*1.1+k), 0.014*math.cos(i*1.3+k))) for i in range(8)]
    add(f"gx_worm_{k}", tube(catmull(pts, 4), lambda s: 0.0055*(1-0.6*s), up=(0,0,1), sides=6), M_worm)
for site in [(-0.55, 0.8, 0.0), (0.1, -0.9, 0.4), (0.4, 0.95, 0.2), (0.62, -0.9, -0.3), (-0.2, -0.95, -0.6), (0.25, 0.9, -0.5)]:
    yu, sx, zf = site
    for k in range(random.randint(4, 7)):
        y2 = yu + random.uniform(-0.04, 0.04); p2 = hx_at(y2); zz = max(-0.95, min(0.95, zf + random.uniform(-0.25, 0.25)))
        x = sx * p2[1]*S*math.sqrt(max(0.05, 1 - zz*zz)); r = random.uniform(0.006, 0.016)*S
        add(f"gx_pus_{yu}_{k}", lathe([(0,0),(r,0),(r*0.9,r*0.6),(r*0.5,r*0.95),(0,r)], 10, T(x, y2*S, (p2[3]+zz*p2[2])*S) @ RY(90*sx)), M_pus)
bpy.ops.object.select_all(action="DESELECT")
for o in [body] + [e for e in extras if e]: o.select_set(True)
bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
body.data.shade_smooth()

# ---------------- weights ----------------
spines = [f"gt_spine_{i:02d}" for i in range(1, 11)]
distance_weights(body, arm, spines, falloff=3.0, top=2)
blend_region(body, "gt_head", lambda c: max(0.0, min(1.0, (-0.9*S - c.y) / (0.18*S))))

# ---------------- rigid head parts ----------------
jaw = loft_fn([(y*S, hx*S, hz*S, zc*S) for y, hx, hz, zc in smooth_stations(
      [(-1.23,0,0,-0.055),(-1.18,0.07,0.035,-0.07),(-1.05,0.125,0.06,-0.1),(-0.92,0.14,0.06,-0.11),(-0.84,0.11,0.045,-0.095),(-0.8,0,0,-0.085)], 18)], 24)
wrinkle(jaw, 0.0025, 70, 4)
jaw.normal_update()
jaw_in = jaw.copy()                                                   # split: skin outside, wet flesh inside
bmesh.ops.delete(jaw, geom=[f for f in jaw.faces if f.normal.z > 0.35], context="FACES")
bmesh.ops.delete(jaw_in, geom=[f for f in jaw_in.faces if f.normal.z <= 0.35], context="FACES")
rigid_bm_to_group(body, jaw, M_skin, "gt_jaw")
rigid_bm_to_group(body, wrinkle(jaw_in, 0.003, 90, 8), M_flesh, "gt_jaw")
tongue = loft_fn([(y*S, hx*S, hz*S, zc*S) for y, hx, hz, zc in [(-1.12,0,0,-0.05),(-1.08,0.035,0.018,-0.052),(-0.98,0.065,0.03,-0.058),(-0.88,0.055,0.025,-0.062),(-0.85,0,0,-0.062)]], 14)
rigid_bm_to_group(body, wrinkle(tongue, 0.004, 50, 9), M_flesh, "gt_jaw")
for k in range(5):                                                    # palate ridges
    yy = (-1.1 + k*0.045)*S; ww = hx_at(yy/S)[1]*S*0.75
    rigid_bm_to_group(body, tube(catmull([Vector((-ww, yy, PAL-0.002)), Vector((0, yy-0.012, PAL-0.006)), Vector((ww, yy, PAL-0.002))], 5), 0.005*S, up=(0,0,1), sides=6), M_flesh, "gt_head")
rigid_bm_to_group(body, sphere(0.075*S, (0, -0.84*S, PAL - 0.02*S), 16), M_throat, "gt_head")  # black gullet

def gum_line(z, scale, ys):
    pts = [Vector((-hx_at(y)[1]*S*scale, y*S, z*S)) for y in ys] + [Vector((0, -1.215*S, z*S))] + \
          [Vector(( hx_at(y)[1]*S*scale, y*S, z*S)) for y in reversed(ys)]
    return catmull(pts, 4)
ys = [-0.87, -0.95, -1.03, -1.1, -1.16, -1.2]
up_line = gum_line(-0.042, 0.9, ys); lo_line = gum_line(-0.07, 0.88, ys)
gum_r = lambda s: (0.007 + 0.004*abs(math.sin(s*37)))*S          # thin, lumpy receding gums
rigid_bm_to_group(body, wrinkle(tube(up_line, gum_r, up=(0,0,1), sides=8), 0.0025, 90, 2), M_gum, "gt_head")
rigid_bm_to_group(body, wrinkle(tube(lo_line, gum_r, up=(0,0,1), sides=8), 0.0025, 90, 5), M_gum, "gt_jaw")

def teeth_on(line, down, bone, rows=3):
    n = len(line)
    for r in range(rows):
        for i in range(2, n-2, 1 if r == 0 else 2):
            pt = line[i]
            if abs(pt.x) < 0.035*S: continue
            inward = Vector((-pt.x, 0, 0)).normalized() * (0.012*S*r)
            L = random.uniform(0.04, 0.13)*S * (1 - 0.3*r)
            if random.random() < 0.15: L *= 0.35
            tx = (180 if down else 0) + random.uniform(-18, 18)
            ty = random.uniform(-14, 14) + (12 if pt.x > 0 else -12) * (1 if down else -1)
            rigid_bm_to_group(body, fang(random.uniform(0.006, 0.011)*S, L, (pt + inward).to_tuple(), tx, ty), M_teeth, bone)
teeth_on(up_line, True, "gt_head"); teeth_on(lo_line, False, "gt_jaw")
for k in range(4):                                                   # human-like incisors at the front
    x = (-0.027 + k*0.018)*S
    for z, bone, sgn in ((-0.05, "gt_head", -1), (-0.062, "gt_jaw", 1)):
        t = box((0.016*S, 0.007*S, 0.03*S), (0, 0, sgn*0.015*S))
        for v in t.verts:
            if v.co.z*sgn < 0: v.co.x *= 0.75
        xf(t, T(x, -1.207*S + abs(x)*0.6, z*S) @ RZ(-x/S*250) @ RX(random.uniform(-6, 6)))
        rigid_bm_to_group(body, t, M_teeth, bone)

for sx in (-1, 1):                                                   # telescope eyes, mismatched dead stares
    tm = T(sx*0.075*S, -0.9*S, 0.21*S) @ RX(55) @ RY(-12*sx)
    prof = [(0,0)] + [(0.062*S + 0.004*S*math.sin(k*1.9) + 0.006*S*(k/14), 0.26*S*k/14) for k in range(15)] + [(0.0, 0.26*S)]
    rigid_bm_to_group(body, wrinkle(lathe(prof, 20, tm), 0.002, 90, sx+3), M_skin, "gt_head")
    rigid_bm_to_group(body, wrinkle(torus(0.068*S, 0.006*S, 20, 6, tm @ T(0, 0, 0.255*S)), 0.002, 120, sx), M_flesh, "gt_head")
    rigid_bm_to_group(body, sphere(0.068*S, (0, 0, 0.27*S), 20, tm), M_scl, "gt_head")
    look = RX(18 if sx > 0 else -10) @ RY(25*sx)
    rigid_bm_to_group(body, sphere(0.022*S, (0, 0, 0.0), 12, tm @ T(0, 0, 0.27*S) @ look @ T(0, 0, 0.062*S) @ Matrix.Scale(0.45, 4, (0, 0, 1))), M_pupil, "gt_head")
    for k in range(9):
        y = random.uniform(-1.05, -0.86); pp = hx_at(y); zz = random.uniform(0.0, 0.55)
        x = sx * pp[1]*S*math.sqrt(1 - zz*zz)*0.99
        rigid_bm_to_group(body, sphere(random.uniform(0.007, 0.018)*S, (x, y*S, (pp[3] + zz*pp[2])*S), 10), M_pupil, "gt_head")

for k in range(7):                                                   # chin tendrils
    x = random.uniform(-0.08, 0.08)*S; y = random.uniform(-1.12, -0.95)*S
    L = random.uniform(0.35, 0.8)
    pts = [Vector((x, y, -0.12*S))]
    for i in range(1, 8):
        t = i/7
        pts.append(Vector((x + 0.03*math.sin(i*1.3+k), y + 0.35*L*t, -0.12*S - L*t + 0.05*math.sin(i*2.1+k))))
    rigid_bm_to_group(body, tube(catmull(pts, 4), lambda s: 0.008*(1 - 0.8*s), up=(1,0,0), sides=6), M_skin, "gt_jaw")
    if k % 2 == 0:
        rigid_bm_to_group(body, sphere(0.014, pts[-1].to_tuple(), 10), M_pus, "gt_jaw")

for sx, bone in ((1, "gt_pec_l"), (-1, "gt_pec_r")):                 # ragged pectoral fins
    m = T(sx*0.15*S, -0.62*S, 0.1*S) @ RZ(-60*sx)
    pts = [(0,0),(0.1,0.04),(0.45,0.0),(0.42,-0.08),(0.05,-0.05)]
    bm = bmesh.new(); outline = []
    for (a0, b0), (a1, b1) in zip(pts, pts[1:] + pts[:1]):
        for k in range(6):
            t = k/6; j = random.uniform(-0.015, 0.02) if k else 0
            outline.append((a0 + (a1-a0)*t, b0 + (b1-b0)*t + j))
    va = [bm.verts.new((u*S, w*S, -0.004)) for u, w in outline]; vb = [bm.verts.new((u*S, w*S, 0.004)) for u, w in outline]
    bm.faces.new(va); bm.faces.new(list(reversed(vb)))
    for i in range(len(outline)):
        j = (i+1) % len(outline); bm.faces.new((va[i], vb[i], vb[j], va[j]))
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    rigid_bm_to_group(body, xf(bm, m), M_fin, bone)
    for k in range(5):
        a = math.radians(-35 + k*12)
        r = tube([Vector((0, 0, 0)), Vector((0.47*S*math.cos(a), 0.47*S*math.sin(a) + 0.02, 0))], lambda s: 0.005*(1-0.85*s), up=(0,0,1), sides=5)
        rigid_bm_to_group(body, xf(r, m), M_bone, bone)

mod = body.modifiers.get("Armature") or body.modifiers.new("Armature", "ARMATURE"); mod.object = arm
if prev_action: arm.animation_data.action = prev_action
_wp = hx_at(WOUND[0])
gig_skin_shader(M_skin, S, (_wp[1]*S*0.85, WOUND[0]*S, _wp[3]*S), WOUND[1]*S*0.75)
flesh_shader(M_flesh, (0.2, 0.01, 0.02)); flesh_shader(M_gum, (0.26, 0.02, 0.035))
sick_eye_shader(M_scl, (0.55, 0.5, 0.36), 0.3)
GIG_INFO = {"tris": sum(len(p.vertices)-2 for p in body.data.polygons),
            "unweighted": sum(1 for v in body.data.vertices if not v.groups),
            "mats": [m.name for m in body.data.materials]}
