# Giant isopod (2026-11-09): monster-ified Bathynomus crawler with its own rig + IS_Idle / IS_Walk / IS_Attack.
# Faces -Y, crawls on the ground (feet at z = 0). Same horror style as the other monsters.
# exec after mk.py, rig.py, horror.py, horror2.py
from mathutils import Quaternion
random.seed(77)
RIG_LOC = (-6.5, -19.5, 0.0)
col = get_col("GiantIsopod", clear=True)


def _m(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)
M_chit, M_soft, M_raw, M_claw = _m("M_IsX_Chitin"), _m("M_IsX_Soft"), _m("M_IsX_Raw"), _m("M_IsX_Claw")
M_eye, M_egg, M_barn, M_throat = _m("M_IsX_Eye"), _m("M_IsX_Egg"), _m("M_IsX_Barnacle"), _m("M_IsX_Throat")

ZC = 0.36
WK = [(-1.25, 0.03), (-1.22, 0.16), (-1.12, 0.28), (-0.98, 0.34), (-0.75, 0.44), (-0.5, 0.5), (-0.25, 0.51), (0.0, 0.49),
      (0.3, 0.45), (0.55, 0.4), (0.85, 0.33), (1.0, 0.28), (1.15, 0.18), (1.25, 0.03)]
HK = [(-1.25, 0.03), (-1.22, 0.08), (-1.12, 0.16), (-0.98, 0.2), (-0.75, 0.24), (-0.3, 0.26), (0.2, 0.25), (0.55, 0.2),
      (0.85, 0.12), (1.1, 0.08), (1.25, 0.03)]
def interp(keys, y):
    if y <= keys[0][0]: return keys[0][1]
    for a, b in zip(keys, keys[1:]):
        if a[0] <= y <= b[0]: return a[1] + (b[1] - a[1]) * (y - a[0]) / (b[0] - a[0])
    return keys[-1][1]
Wf = lambda y: interp(WK, y); Hf = lambda y: interp(HK, y)


def orient(n):
    return n.to_track_quat("Z", "Y").to_matrix().to_4x4()


def surf_pt(y, a, out=0.0):
    W, H = Wf(y), Hf(y)
    p = Vector((W * math.cos(a), y, ZC + H * math.sin(a)))
    n = Vector((math.cos(a) / max(W, 1e-3), 0, math.sin(a) / max(H, 1e-3))).normalized()
    return p + n * out, n


SECTION = [(1.12, -0.38, 1), (1.06, -0.18, 1)] + [(math.cos(math.pi * k / 24), math.sin(math.pi * k / 24), 0) for k in range(25)] + [(-1.06, -0.18, 1), (-1.12, -0.38, 1)]
def plate(y0, y1, rows=7, hole=None):
    """Armoured arched tergite from y0 to y1 (rear edge flares to overlap the next plate)."""
    bm = bmesh.new(); el = bm.verts.layers.float.new("pedge"); grid = []
    for r in range(rows + 1):
        u = r / rows; y = y0 + (y1 - y0) * u
        W, H = Wf(y), Hf(y); sc = 0.96 + 0.07 * u
        row = []
        for x, z, side in SECTION:
            v = bm.verts.new((x * W * sc, y, ZC + z * H * sc + 0.02 * u + H * 0.06 * math.sin(math.pi * u)))
            v[el] = max(smoothstep(0.6, 1.0, abs(2 * u - 1)), float(side))
            row.append(v)
        grid.append(row)
    nC = len(SECTION)
    for r in range(rows):
        for c in range(nC - 1):
            bm.faces.new((grid[r][c], grid[r + 1][c], grid[r + 1][c + 1], grid[r][c + 1]))
    if hole:
        hc, hr = hole
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if (f.calc_center_median() - hc).length < hr * (0.8 + 0.4 * noise.noise(f.calc_center_median() * 20))], context="FACES")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.014)
    wrinkle_bm(bm, 0.003, 25, int(y0 * 10))
    return bm


# ---------------- armature ----------------
SEG = [(-0.95 + i * 0.214, -0.95 + (i + 1) * 0.214) for i in range(7)]
bones = [("is_root", (0, 0, 0), (0, 0.3, 0), None, False),
         ("is_body", (0, SEG[3][1], ZC), (0, SEG[3][0], ZC), "is_root", True)]
for i in (2, 1, 0):
    bones.append((f"is_seg{i + 1}", (0, SEG[i][1], ZC), (0, SEG[i][0], ZC), "is_body" if i == 2 else f"is_seg{i + 2}", True))
bones.append(("is_head", (0, -0.95, ZC), (0, -1.25, ZC), "is_seg1", True))
for i in (4, 5, 6):
    bones.append((f"is_seg{i + 1}", (0, SEG[i][0], ZC), (0, SEG[i][1], ZC), "is_body" if i == 4 else f"is_seg{i}", True))
bones += [("is_pleon", (0, 0.548, ZC), (0, 0.85, ZC), "is_seg7", True), ("is_tail", (0, 0.85, ZC), (0, 1.25, ZC), "is_pleon", True)]
SEGBONE = {i: ("is_body" if i == 3 else f"is_seg{i + 1}") for i in range(7)}
BODY_BONES = ["is_head", "is_seg1", "is_seg2", "is_seg3", "is_body", "is_seg5", "is_seg6", "is_seg7", "is_pleon", "is_tail"]
LEGS = {}
for i in range(7):
    ym = (SEG[i][0] + SEG[i][1]) / 2; W = Wf(ym); dy = (i - 3) * 0.075
    for sx, sn in ((1, "R"), (-1, "L")):
        P = [Vector((sx * W * 0.55, ym, 0.24)), Vector((sx * (W + 0.12), ym + dy * 0.3, 0.37)),
             Vector((sx * (W + 0.32), ym + dy * 0.7, 0.22)), Vector((sx * (W + 0.4), ym + dy, 0.0))]
        names = []
        for k in range(3):
            nm = f"is_leg{sn}{i + 1}_{k + 1}"
            bones.append((nm, tuple(P[k]), tuple(P[k + 1]), names[-1] if names else SEGBONE[i], True)); names.append(nm)
        LEGS[(i, sx)] = (P, names)
ANT = {}
for sx, sn in ((1, "R"), (-1, "L")):
    P0 = Vector((sx * 0.13, -1.2, 0.42))
    raw = [P0, P0 + Vector((sx * 0.12, -0.25, 0.1)), P0 + Vector((sx * 0.45, -0.38, 0.14)), P0 + Vector((sx * 0.85, -0.25, 0.08)), P0 + Vector((sx * 1.1, 0.15, 0.02))]
    pts = catmull(raw, 8)
    idx = [round(k * (len(pts) - 1) / 5) for k in range(6)]
    names = []
    for k in range(5):
        nm = f"is_ant{sn}_{k + 1}"
        bones.append((nm, tuple(pts[idx[k]]), tuple(pts[idx[k + 1]]), names[-1] if names else "is_head", True)); names.append(nm)
    ANT[sx] = (pts, names)
CLAW = {}
for sx, sn in ((1, "R"), (-1, "L")):
    P = [Vector((sx * 0.09, -1.1, 0.24)), Vector((sx * 0.13, -1.25, 0.17)), Vector((sx * 0.03, -1.38, 0.2))]
    bones.append((f"is_claw{sn}_1", tuple(P[0]), tuple(P[1]), "is_head", True))
    bones.append((f"is_claw{sn}_2", tuple(P[1]), tuple(P[2]), f"is_claw{sn}_1", True))
    CLAW[sx] = (P, [f"is_claw{sn}_1", f"is_claw{sn}_2"])
rig = make_armature(col, "GiantIsopod_Rig", bones, (0, 0, 0))


def weighted(name, bm, material, bone_list, base_blend=None):
    o_ = finish(col, name, bm, material)
    o_.parent = rig; o_.matrix_parent_inverse = Matrix.Identity(4); bpy.context.view_layer.update()
    distance_weights(o_, rig, bone_list, falloff=3.0, top=2)
    if base_blend: blend_region(o_, base_blend[0], base_blend[1])
    return o_


def merge(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o_ in objs: o_.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join(); return objs[0]


def add_bm(dst, src):
    tmp = bpy.data.meshes.new("_t"); src.to_mesh(tmp); src.free(); dst.from_mesh(tmp); bpy.data.meshes.remove(tmp)


# ---------------- body: plates, soft core, brood pouch, eggs, barnacles ----------------
HOLE_C, HOLE_N = surf_pt(-0.19, math.radians(35))
plates = bmesh.new()
add_bm(plates, plate(-1.25, -0.93, rows=9))
for i, (y0, y1) in enumerate(SEG):
    add_bm(plates, plate(y0 - 0.03, y1 + 0.03, hole=(HOLE_C, 0.14) if i == 3 else None))
for k in range(5):
    y0 = 0.548 + k * 0.06; add_bm(plates, plate(y0 - 0.015, y0 + 0.075, rows=3))
add_bm(plates, plate(0.84, 1.25, rows=9))
body_parts = [weighted("is_plates", plates, M_chit, BODY_BONES)]
core_st = [(-1.21, 0, 0, ZC - 0.04)] + [(y, Wf(y) * 0.86, 0.17 * smoothstep(0.0, 0.08, 1.2 - abs(y)) + 0.01, ZC - 0.04)
                                       for y in [-1.18 + 2.36 * k / 60 for k in range(61)]] + [(1.21, 0, 0, ZC - 0.04)]
core = loft_fn(core_st, 36,
               lambda y, a, x, z: 1 + 0.04 * math.sin(y * 60) * max(0.0, -math.sin(a)))
core.verts.ensure_lookup_table()
wrinkle_bm(core, 0.006, 30, 3)
body_parts.append(weighted("is_core", core, M_soft, BODY_BONES))
pouch = uvsphere(1.0, None, 28, 14)
for v in pouch.verts:
    v.co = Vector((v.co.x * 0.3, -0.32 + v.co.y * 0.42, 0.2 + v.co.z * 0.09))
    v.co += v.co.normalized() * 0.0
wrinkle_bm(pouch, 0.008, 18, 5)
body_parts.append(weighted("is_pouch", pouch, M_soft, BODY_BONES))
eggs = bmesh.new()
for k in range(44):
    a = random.uniform(0, math.tau); b = random.uniform(0.2, 1.0)
    p = Vector((0.3 * math.cos(a) * b, -0.32 + 0.42 * math.sin(a) * b, 0.2 - 0.09 * math.sqrt(max(0.0, 1 - b * b)) - 0.004))
    add_bm(eggs, uvsphere(random.uniform(0.02, 0.034), T(*p), 12, 8))
body_parts.append(weighted("is_eggs", eggs, M_egg, BODY_BONES))
barn = bmesh.new()
for k in range(16):
    y = random.uniform(-0.9, 1.0); a = random.uniform(0.35, math.pi - 0.35)
    p, n = surf_pt(y, a, 0.01); r = random.uniform(0.018, 0.04)
    prof_ = [(0, r * 0.3), (r * 0.35, r * 0.35), (r * 0.5, r * 0.9), (r * 0.75, r * 0.95), (r, r * 0.2), (r * 1.05, -r * 0.2)]
    add_bm(barn, wrinkle_bm(lathe(prof_, 10, T(*p) @ orient(n)), r * 0.08, 200, k))
body_parts.append(weighted("is_barnacles", barn, M_barn, BODY_BONES))
spines = bmesh.new()
for k in range(11):                                                        # spines on the tail shield rim
    t = k / 10; a = -0.9 + 1.8 * t
    y = 1.25 - 0.35 * (1 - math.cos(a)) ; W = Wf(min(1.24, y))
    p = Vector((math.sin(a) * W * 1.05, y, ZC + 0.01)); d = Vector((math.sin(a), 1.2, -0.1)).normalized()
    add_bm(spines, xf(needle(0.012, random.uniform(0.06, 0.12), (0, 0, 0), 0, 0, 0.1, segs=6), T(*p) @ orient(d)))
for i in range(7):                                                         # spikes on the plate side flares
    ym = (SEG[i][0] + SEG[i][1]) / 2
    for sx in (-1, 1):
        p = Vector((sx * Wf(ym) * 1.12, ym + 0.08, ZC - Hf(ym) * 0.38))
        add_bm(spines, xf(needle(0.014, random.uniform(0.05, 0.09), (0, 0, 0), 0, 0, 0.1, segs=6), T(*p) @ orient(Vector((sx, 0.5, -0.5)).normalized())))
for i, (y0, y1) in enumerate(SEG):                                        # serrated spikes on each plate's rear edge
    for a in [math.radians(d_) for d_ in (35, 60, 90, 120, 145)]:
        if random.random() < 0.25: continue
        p, n = surf_pt(y1 + 0.02, a, 0.015)
        d = (n + Vector((0, 1.4, 0))).normalized()
        add_bm(spines, xf(needle(0.012, random.uniform(0.04, 0.09) * (1.4 if a == math.pi / 2 else 1.0), (0, 0, 0), 0, 0, 0.2, segs=6), T(*p) @ orient(d)))
body_parts.append(weighted("is_spines", spines, M_claw, BODY_BONES))
bulge = uvsphere(1.0, None, 20, 12)                                         # raw flesh pushing out of the broken plate
for v in bulge.verts:
    v.co = HOLE_C - HOLE_N * 0.03 + Vector((v.co.x * 0.1, v.co.y * 0.12, v.co.z * 0.08)) + v.co * 0.02 * noise.noise(v.co * 4)
wrinkle_bm(bulge, 0.01, 30, 7)
body_parts.append(weighted("is_wound", bulge, M_raw, BODY_BONES))
body = merge(body_parts); body.name = "SK_GiantIsopod_Body"; body.data.name = "SK_GiantIsopod_Body"

# ---------------- legs, antennae, claws ----------------
limbs = []
for (i, sx), (P, names) in LEGS.items():
    bm = bmesh.new(); tipbm = bmesh.new()
    radii = [(0.034, 0.026), (0.026, 0.018), (0.018, 0.003)]
    for k in range(3):
        a_, b_ = P[k], P[k + 1]
        mid = (a_ + b_) / 2 + Vector((0, 0, 0.015 if k < 2 else 0))
        seg = tube(catmull([a_, mid, b_], 4), lambda s, k=k: (radii[k][0] + (radii[k][1] - radii[k][0]) * s) * (1 + 0.12 * math.sin(math.pi * s)), up=(0, 1, 0), sides=9)
        add_bm(tipbm if k == 2 else bm, seg)
        if k < 2: add_bm(bm, uvsphere(radii[k][1] * 1.05, T(*b_), 10, 6))
        for q in range(2 if k < 2 else 1):                                 # spines along the leg
            s = 0.35 + 0.35 * q; p = a_.lerp(b_, s)
            d = (Vector((sx, 0, 0.6)) + (b_ - a_).normalized() * 0.8).normalized()
            add_bm(bm, xf(needle(radii[k][0] * 0.35, random.uniform(0.03, 0.055), (0, 0, 0), 0, 0, 0.2, segs=5), T(*p) @ orient(d)))
    limbs.append(weighted(f"is_leg_{i}_{sx}", bm, M_chit, names + [SEGBONE[i]]))
    limbs.append(weighted(f"is_legtip_{i}_{sx}", tipbm, M_claw, names))
for sx, (pts, names) in ANT.items():
    bm = tube(pts, lambda s: (0.012 * (1 - s) + 0.003) * (1 + 0.25 * math.sin(s * 160) ** 8), up=(0, 0, 1), sides=8)
    limbs.append(weighted(f"is_ant_{sx}", bm, M_claw, names))
for sx, (P, names) in CLAW.items():
    bm = tube(catmull([P[0], P[1], P[2] + (P[2] - P[1]) * -0.2], 4), lambda s: 0.026 * (1 - 0.6 * s), up=(0, 0, 1), sides=10)
    tipd = (P[2] - P[1]).normalized()
    add_bm(bm, xf(needle(0.016, 0.1, (0, 0, 0), 0, 0, 0.6, segs=8), T(*(P[2] - tipd * 0.03)) @ orient(tipd)))
    for q in range(3):
        p = P[1].lerp(P[2], 0.2 + 0.25 * q)
        add_bm(bm, xf(needle(0.006, 0.035, (0, 0, 0), 0, 0, 0.3, segs=5), T(*p) @ orient(Vector((-sx, -0.3, 0.2)).normalized())))
    limbs.append(weighted(f"is_claw_{sx}", bm, M_claw, names))
body = merge([body] + limbs)
body.data.shade_smooth()

# ---------------- rigid head parts: compound eyes, mouth, short antennae ----------------
EYE_C = []
for sx in (-1, 1):
    c = Vector((sx * 0.3, -1.05, ZC + 0.07))
    e = uvsphere(1.0, None, 28, 16)
    xf(e, T(*c) @ RZ(sx * 25) @ Matrix.Diagonal((0.085, 0.13, 0.08, 1)))
    rigid_bm_to_group(body, wrinkle_bm(torus(1.0, 0.12, 28, 8, T(*c) @ RZ(sx * 25) @ RY(sx * 90) @ Matrix.Diagonal((0.075, 0.12, 0.07, 1))), 0.004, 60, 1), M_chit, "is_head")
    rigid_bm_to_group(body, e, M_eye, "is_head"); EYE_C.append(c)
mc = Vector((0, -1.12, 0.2))
rigid_bm_to_group(body, wrinkle_bm(torus(0.07, 0.025, 20, 8, T(*mc) @ RX(-30)), 0.005, 50, 3), M_raw, "is_head")
rigid_bm_to_group(body, uvsphere(0.065, T(0, -1.09, 0.23), 14, 8), M_throat, "is_head")
for k in range(14):
    a = k / 14 * math.tau
    q = mc + (RX(-30).to_3x3() @ Vector((math.cos(a), math.sin(a), 0))) * 0.06
    dv = (mc + RX(-30).to_3x3() @ Vector((0, 0, -0.04)) - q).normalized()
    rigid_bm_to_group(body, xf(needle(0.006, random.uniform(0.03, 0.05), (0, 0, 0), 0, 0, 0.3, segs=5), T(*q) @ orient(dv)), M_claw, "is_head")
for sx in (-1, 1):
    P0 = Vector((sx * 0.06, -1.22, 0.38))
    rigid_bm_to_group(body, tube(catmull([P0, P0 + Vector((sx * 0.06, -0.12, 0.06)), P0 + Vector((sx * 0.12, -0.2, 0.02))], 4), lambda s: 0.012 * (1 - 0.7 * s), up=(0, 0, 1), sides=6), M_chit, "is_head")
mod = body.modifiers.new("Armature", "ARMATURE"); mod.object = rig


# ---------------- animation ----------------
def bend_q(bname, world_axis, ang):
    R = rig.data.bones[bname].matrix_local.to_3x3()
    ax = R.inverted() @ Vector(world_axis)
    return Quaternion(ax.normalized(), ang) if ax.length > 1e-6 else Quaternion()
def kr(bn, f, q): key(rig.pose.bones[bn], f, rot=q.to_euler("XYZ"))
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
D = math.radians
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def antennae(f, t, amp=1.0):
    for sx, (pts, names) in ANT.items():
        for k, bn in enumerate(names):
            kr(bn, f, bend_q(bn, Z, D(6 + 2 * k) * amp * math.sin(math.tau * t - 0.5 * k + sx)) @ bend_q(bn, X, D(4) * amp * math.sin(math.tau * t * 2 - 0.4 * k)))


def claws(f, open_):
    for sx, (P, names) in CLAW.items():
        kr(names[0], f, bend_q(names[0], Z, -sx * open_ * D(35)) @ bend_q(names[0], X, open_ * D(15)))
        kr(names[1], f, bend_q(names[1], Z, sx * open_ * D(10)))


bpy.context.view_layer.objects.active = rig
new_action(rig, "IS_Idle")
F = 80
for f in range(F + 1):
    t = f / F
    antennae(f + 1, t)
    claws(f + 1, 0.15 + 0.15 * max(0.0, math.sin(math.tau * t * 3)) ** 8)
    for (i, sx), (P, names) in LEGS.items():
        kr(names[0], f + 1, bend_q(names[0], Z, sx * D(2) * math.sin(math.tau * t + i)))
    key(rig.pose.bones["is_body"], f + 1, loc=(0, 0, 0.004 * math.sin(math.tau * t)))
rig.animation_data.action.frame_range = (1, F + 1)

new_action(rig, "IS_Walk")
F = 32
for f in range(F + 1):
    t = f / F
    for (i, sx), (P, names) in LEGS.items():
        ph = math.tau * (t - i * 0.13 + (0.5 if sx < 0 else 0.0))
        swing = D(20) * math.cos(ph); lift = D(16) * max(0.0, math.sin(ph))
        kr(names[0], f + 1, bend_q(names[0], Z, sx * swing) @ bend_q(names[0], Y, -sx * lift))
        kr(names[1], f + 1, bend_q(names[1], Y, -sx * lift * 0.6))
        kr(names[2], f + 1, bend_q(names[2], Y, sx * lift * 0.5))
    antennae(f + 1, t * 2, 0.6)
    claws(f + 1, 0.2)
    for k, bn in enumerate(BODY_BONES[1:9]):
        kr(bn, f + 1, bend_q(bn, Z, D(1.5) * math.sin(math.tau * t * 2 - k * 0.5)))
    key(rig.pose.bones["is_body"], f + 1, loc=(0, 0, 0.008 * math.sin(math.tau * t * 2)))
rig.animation_data.action.frame_range = (1, F + 1)

new_action(rig, "IS_Attack")
F = 30
FRONT = ["is_seg3", "is_seg2", "is_seg1", "is_head"]
for f in range(F + 1):
    rear = ease(f / 9) * (1 - ease((f - 10) / 4))
    slam = ease((f - 10) / 5) * (1 - ease((f - 18) / 10))
    for k, bn in enumerate(FRONT):
        kr(bn, f + 1, bend_q(bn, X, -D(13) * rear + D(7) * slam))
    claws(f + 1, 1.0 * rear + 0.2 - 0.6 * slam)
    for (i, sx), (P, names) in LEGS.items():
        if i < 2:                                                          # front legs rise and reach
            kr(names[0], f + 1, bend_q(names[0], Y, -sx * D(35) * rear) @ bend_q(names[0], Z, -sx * D(25) * rear))
            kr(names[1], f + 1, bend_q(names[1], Y, sx * D(20) * rear))
        else:
            kr(names[0], f + 1, Quaternion())
    antennae(f + 1, f / 30, 1.5 * rear + 0.3)
    lunge = -0.6 * ease((f - 9) / 6)
    key(rig.pose.bones["is_root"], f + 1, loc=(0, lunge, 0))
rig.animation_data.action.frame_range = (1, F + 1)
_act = bpy.data.actions["IS_Walk"]; rig.animation_data.action = _act
if hasattr(rig.animation_data, "action_slot") and len(_act.slots): rig.animation_data.action_slot = _act.slots[0]
rig.location = RIG_LOC


# ---------------- shaders ----------------
def chitin(mat):
    nb = NB(mat)
    a = nb.n("ShaderNodeAttribute", attribute_name="pedge"); edge = a.outputs["Fac"]
    P = nb_warp(nb, 0.02, 10.0)
    sep = nb.n("ShaderNodeSeparateXYZ"); nb.L(nb.obj, sep.inputs[0]); Zc = sep.outputs["Z"]
    mott = nb.noise(6.0, 6, 0.6)
    col_ = nb.ramp(mott.outputs["Fac"], [(0.3, (0.03, 0.022, 0.018)), (0.55, (0.1, 0.078, 0.055)), (0.8, (0.2, 0.16, 0.11))]).outputs[0]
    lil = nb.noise(2.0, 3, 0.5)
    col_ = nb.mix(col_, (0.09, 0.06, 0.08), nb.math("MULTIPLY", nb_map(nb, lil.outputs["Fac"], 0.45, 0.65), 0.5))
    low = nb_map(nb, Zc, ZC + 0.05, ZC - 0.15)                               # grime toward the underside
    col_ = nb.mix(col_, (0.05, 0.035, 0.03), nb.math("MULTIPLY", low, 0.6))
    rust = nb.noise(9.0, 4, 0.6, vec=nb.mapping(scale=(4, 4, 0.8)))
    stain = nb.math("MULTIPLY", nb_map(nb, rust.outputs["Fac"], 0.5, 0.65), nb.math("ADD", edge, 0.25))
    col_ = nb.mix(col_, (0.2, 0.05, 0.025), nb.math("MULTIPLY", stain, 0.8))
    col_ = nb.mix(col_, (0.06, 0.03, 0.025), nb.math("MULTIPLY", edge, 0.55))
    crk = nb.voronoi(18.0, "DISTANCE_TO_EDGE", vec=P)
    cracks = nb.math("MULTIPLY", nb_map(nb, crk.outputs["Distance"], 0.0, 0.02, 1.0, 0.0), nb_map(nb, nb.noise(4.0, 2).outputs["Fac"], 0.56, 0.64))
    col_ = nb.mix(col_, (0.02, 0.01, 0.008), cracks)
    pits = nb_map(nb, nb.voronoi(120.0, "F1").outputs["Distance"], 0.05, 0.15, 1.0, 0.0)
    col_ = nb.mix(col_, (0.06, 0.04, 0.03), nb.math("MULTIPLY", pits, 0.6))
    hd = nb.n("ShaderNodeVectorMath", operation="DISTANCE"); nb.L(P, hd.inputs[0]); hd.inputs[1].default_value = tuple(HOLE_C)
    hole_rim = nb_map(nb, hd.outputs["Value"], 0.2, 0.09)                    # blood + cracks around the broken plate
    col_ = nb.mix(col_, (0.12, 0.01, 0.015), nb.math("MULTIPLY", hole_rim, 0.85))
    rough = nb_map(nb, mott.outputs["Fac"], 0.3, 0.7, 0.32, 0.55)
    rough = nb.math("SUBTRACT", rough, nb.math("MULTIPLY", nb.math("MAXIMUM", edge, hole_rim), 0.2))
    h = nb.math("ADD", nb.math("MULTIPLY", nb.noise(40.0, 6, 0.6).outputs["Fac"], 0.4), nb.math("MULTIPLY", mott.outputs["Fac"], 0.3), clamp=False)
    h = nb.math("SUBTRACT", h, nb.math("MULTIPLY", cracks, 0.9), clamp=False)
    h = nb.math("SUBTRACT", h, nb.math("MULTIPLY", pits, 0.7), clamp=False)
    ridges = nb.noise(30.0, 4, 0.6, vec=nb.mapping(scale=(0.4, 6, 0.4)))
    h = nb.math("ADD", h, nb.math("MULTIPLY", ridges.outputs["Fac"], 0.5), clamp=False)
    nb_finish_full(nb, col_, rough, h, bump=0.7, dist=0.012, spec=0.5)
    mat.diffuse_color = (0.3, 0.26, 0.22, 1)


def soft_flesh(mat):
    nb = NB(mat)
    hd = nb.n("ShaderNodeVectorMath", operation="DISTANCE"); nb.L(nb_warp(nb, 0.03, 10.0), hd.inputs[0]); hd.inputs[1].default_value = tuple(HOLE_C)
    raw_m = nb_map(nb, hd.outputs["Value"], 0.18, 0.1)
    m = nb.noise(12.0, 5, 0.6)
    col_ = nb.ramp(m.outputs["Fac"], [(0.3, (0.16, 0.09, 0.09)), (0.7, (0.3, 0.19, 0.18))]).outputs[0]
    v = nb.noise(7.0, 4, 0.5, distortion=3.0)
    veins = nb.ramp(v.outputs["Fac"], [(0.485, (0, 0, 0)), (0.5, (1, 1, 1)), (0.515, (0, 0, 0))]).outputs[0]
    col_ = nb.mix(col_, (0.2, 0.0, 0.04), nb.math("MULTIPLY", veins, 0.75))
    fib = nb.noise(60.0, 3, 0.5, vec=nb.mapping(scale=(1, 0.2, 1)))
    raw = nb.ramp(fib.outputs["Fac"], [(0.3, (0.08, 0.003, 0.008)), (0.7, (0.38, 0.03, 0.04))]).outputs[0]
    col_ = nb.mix(col_, raw, raw_m)
    rough = nb.math("SUBTRACT", nb_map(nb, m.outputs["Fac"], 0.3, 0.7, 0.15, 0.3), nb.math("MULTIPLY", raw_m, 0.1))
    h = nb.math("ADD", nb.math("MULTIPLY", nb.noise(35.0, 5, 0.6, vec=nb.mapping(scale=(1, 0.3, 1))).outputs["Fac"], 0.6), nb.math("MULTIPLY", veins, 0.5), clamp=False)
    nb_finish_full(nb, col_, rough, h, bump=0.45, dist=0.008, spec=0.55)
    mat.diffuse_color = (0.25, 0.15, 0.15, 1)


def compound_eye(mat):
    nb = NB(mat)
    fac = nb.voronoi(260.0, "DISTANCE_TO_EDGE")
    facet = nb_map(nb, fac.outputs["Distance"], 0.0, 0.06)
    shine = nb.noise(6.0, 3, 0.5)
    base = nb.ramp(shine.outputs["Fac"], [(0.3, (0.01, 0.012, 0.02)), (0.7, (0.06, 0.05, 0.09))]).outputs[0]
    c = nb.mix((0.0, 0.0, 0.0), base, facet)
    glow = nb.mix((0, 0, 0), (0.035, 0.045, 0.012), nb.math("MULTIPLY", facet, nb_map(nb, shine.outputs["Fac"], 0.4, 0.7, 0.0, 1.0)))
    nb_finish_full(nb, c, 0.08, facet, bump=0.3, dist=0.002, emit=glow, emit_strength=1.0, spec=0.8)
    mat.diffuse_color = (0.04, 0.04, 0.06, 1)


def egg(mat):
    nb = NB(mat)
    n = nb.noise(25.0, 4, 0.6)
    emb = nb.voronoi(30.0, "F1")
    spot = nb_map(nb, emb.outputs["Distance"], 0.08, 0.2, 1.0, 0.0)
    c = nb.ramp(n.outputs["Fac"], [(0.3, (0.35, 0.42, 0.1)), (0.7, (0.65, 0.72, 0.25))]).outputs[0]
    c = nb.mix(c, (0.04, 0.03, 0.01), nb.math("MULTIPLY", spot, 0.8))
    e = nb.mix(nb.mix((0, 0, 0), (0.55, 0.85, 0.12), 0.8), (0, 0, 0), spot)
    nb_finish_full(nb, c, 0.06, n.outputs["Fac"], bump=0.1, dist=0.003, emit=e, emit_strength=1.0, spec=0.8)
    mat.diffuse_color = (0.5, 0.6, 0.2, 1)


chitin(M_chit); soft_flesh(M_soft); compound_eye(M_eye); egg(M_egg)
flesh_shader(M_raw, (0.2, 0.008, 0.018))
simple_shader(M_claw, (0.07, 0.045, 0.035), 0.25, noise_scale=40, var=0.5, bump=0.2, veins=(20.0, (0.2, 0.12, 0.06), 0.4))
simple_shader(M_barn, (0.11, 0.1, 0.085), 0.6, noise_scale=80, var=0.45, bump=0.6, veins=(40.0, (0.08, 0.06, 0.05), 0.8))
simple_shader(M_throat, (0.25, 0.0, 0.01), 0.15, noise_scale=20, var=0.5, emit=(0.6, 0.02, 0.02), emit_strength=0.5)
for m_ in bpy.data.materials:
    if m_.name.startswith("M_IsX_"): m_.use_fake_user = True
IS_INFO = {"tris": sum(len(p.vertices) - 2 for p in body.data.polygons), "bones": len(rig.data.bones),
           "unweighted": sum(1 for v in body.data.vertices if not v.groups), "mats": [m.name for m in body.data.materials],
           "dims": tuple(round(d, 2) for d in body.dimensions)}
print("IS_INFO", IS_INFO)
