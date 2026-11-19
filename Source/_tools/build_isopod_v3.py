# Giant isopod v3 (2026-11-20): a faithful Bathynomus giganteus scaled to ~3 m (replaces v2, whose legs splayed out
# like a spider, body was a smooth pill, eyes were black balls on the back and colour was flat grey).
# Faces -Y, crawls on the ground (feet at z = 0). Bone and animation names are the same as v1/v2
# (is_root / is_body / is_seg1..7 / is_head / is_pleon / is_tail / is_uro{L,R} / is_leg{L,R}{1..7}_{1..3} /
#  is_ant{L,R}_{1..5} / is_claw{L,R}_{1,2} = maxillipeds), so the Unreal side keeps working.
# Anatomy: flattened oval shield. Small blunt cephalon set into the concave front of pereonite 1, with flat kidney-shaped
# compound eyes on its sides; 7 imbricated pereonites (each rear margin steps over the next) whose lateral epimera hang down
# and point backward more and more toward the rear; 5 short pleonites; broad rounded pleotelson with a low median keel and
# 11 marginal spines; paddle uropods. Legs are tucked UNDER the shield: thick basis under the body, knee at the margin,
# propodus/dactylus straight down to the floor (front 3 pairs forward, rear 4 back). Antennae swept back along the sides.
# Colour: pale lilac-grey, yellowish-brown margins, fine pits; AO baked into BaseColor.
# exec after mk.py, rig.py, horror.py, horror2.py, monsters_v2_pipeline.py.   bake_and_export() bakes 4096 textures + SK fbx.
from mathutils import Quaternion
random.seed(93)
RIG_LOC = (-6.5, -19.5, 0.0)
col = get_col("GiantIsopod", clear=True)
for a_ in [a_ for a_ in bpy.data.actions if a_.name.startswith("IS_")]:
    bpy.data.actions.remove(a_)


def _m(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)
M_back, M_belly, M_leg, M_eye, M_spine = _m("M_IsR_Carapace"), _m("M_IsR_Underside"), _m("M_IsR_Leg"), _m("M_IsR_Eye"), _m("M_IsR_Spine")

ZC = 0.22                                                    # shield margin height above the floor
WK = [(-1.2, 0.46), (-1.05, 0.53), (-0.7, 0.59), (-0.2, 0.625), (0.3, 0.62), (0.62, 0.57), (0.92, 0.5)]
HK = [(-1.2, 0.23), (-0.8, 0.28), (-0.2, 0.30), (0.4, 0.28), (0.62, 0.24), (0.92, 0.19)]
def interp(keys, y):
    if y <= keys[0][0]: return keys[0][1]
    for a, b in zip(keys, keys[1:]):
        if a[0] <= y <= b[0]: return a[1] + (b[1] - a[1]) * (y - a[0]) / (b[0] - a[0])
    return keys[-1][1]
Wf = lambda y: interp(WK, y); Hf = lambda y: interp(HK, y)
HEAD = (-1.5, -1.2); PER = [(-1.2 + 0.26 * i, -1.2 + 0.26 * (i + 1)) for i in range(7)]
PLEON = [(0.62 + 0.06 * i, 0.62 + 0.06 * (i + 1)) for i in range(5)]; TELSON = (0.92, 1.5)


def orient(n):
    return Vector(n).to_track_quat("Z", "Y").to_matrix().to_4x4()


def add_bm(dst, src):
    tmp = bpy.data.meshes.new("_t"); src.to_mesh(tmp); src.free(); dst.from_mesh(tmp); bpy.data.meshes.remove(tmp)


def surf(y0, y1, wfun, hfun, ext=0.0, lobe=0.0, dip=0.025, lip=0.018, keel=0.0):
    """Dorsal plate surface pos(u, xn): u 0 front..1 rear, xn -1..1 across. Front dips under the plate ahead,
    rear margin lifts (lip) so it steps over the next one; lateral corners pulled back (ext) / forward (lobe)."""
    def pos(u, xn):
        ax = min(1.0, abs(xn)); w, h = wfun(u), hfun(u)
        z = ZC + h * (1 - ax ** 2.4) ** 0.7 - dip * (1 - smoothstep(0.0, 0.22, u)) + lip * smoothstep(0.7, 1.0, u) * (1 - 0.5 * ax)
        z += keel * h * math.exp(-(xn / 0.12) ** 2) * u
        k = smoothstep(0.75, 1.0, ax)
        y = y0 + (y1 - y0) * u + ext * u * u * k - lobe * (1 - u) ** 3 * k
        return Vector((math.copysign(ax, xn) * w, y, z))
    return pos


def plate(pos, rows, cols=40, rear_flag=0.68):
    """Mesh a surf(): dome + a short epimeral wall hanging down at both sides; 'pedge' = margin band for the shader."""
    bm = bmesh.new(); el = bm.verts.layers.float.new("pedge"); fl = bm.verts.layers.float.new("pfront"); grid = []
    for r in range(rows + 1):
        u = r / rows; L, R = pos(u, -1.0), pos(u, 1.0); row = []
        pts = [(L + Vector((-0.012, 0, -0.075)), 1.0), (L + Vector((-0.017, 0, -0.035)), 1.0)]
        pts += [(pos(u, -math.cos(math.pi * c / cols)), smoothstep(rear_flag, 1.0, u)) for c in range(cols + 1)]
        pts += [(R + Vector((0.017, 0, -0.035)), 1.0), (R + Vector((0.012, 0, -0.075)), 1.0)]
        for p, f in pts:
            v = bm.verts.new(p); v[el] = f; v[fl] = 1.0 - smoothstep(0.0, 0.2, u); row.append(v)
        grid.append(row)
    for r in range(rows):
        for c in range(len(grid[0]) - 1):
            bm.faces.new((grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]))
    bm.normal_update()
    if sum(f.normal.z for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.018)
    wrinkle_bm(bm, 0.0012, 45, int(pos(0.5, 0).y * 10) + 7)
    return bm


# plate shapes
def head_w(u):
    f = math.sqrt(max(0.0, 1 - (1 - min(1.0, u / 0.32)) ** 2))
    return max(0.02, 0.37 * f * (0.93 + 0.07 * u))
def head_h(u):
    f = math.sqrt(max(0.0, 1 - (1 - min(1.0, u / 0.32)) ** 2))
    return (0.08 + 0.14 * smoothstep(0.0, 0.8, u)) * f ** 0.5
HEAD_POS = surf(HEAD[0], HEAD[1] + 0.03, head_w, head_h, dip=0.0, lip=0.012)
EXT = [0.0, 0.01, 0.02, 0.035, 0.05, 0.065, 0.08]
PER_POS = []
for i, (y0, y1) in enumerate(PER):
    a, b = y0 - 0.03, y1 + 0.03
    PER_POS.append(surf(a, b, lambda u, a=a, b=b: Wf(a + (b - a) * u), lambda u, a=a, b=b: Hf(a + (b - a) * u),
                        ext=EXT[i], lobe=0.04 if i == 0 else 0.0))
PLEON_POS = []
for (y0, y1) in PLEON:
    a, b = y0 - 0.015, y1 + 0.02
    PLEON_POS.append(surf(a, b, lambda u, a=a, b=b: Wf(a + (b - a) * u) * 0.97, lambda u, a=a, b=b: Hf(a + (b - a) * u),
                          ext=0.05, dip=0.015, lip=0.012))
tel_w = lambda u: max(0.02, 0.5 * (1 - u ** 2.2) ** 0.55)
tel_h = lambda u: 0.19 * (1 - u ** 1.8) ** 0.8 + 0.012
TEL_POS = surf(TELSON[0] - 0.02, TELSON[1], tel_w, tel_h, dip=0.02, lip=0.0, keel=0.15)


def width_at(y):                                             # outline half-width (for the underside)
    if y < HEAD[1]: return head_w((y - HEAD[0]) / (HEAD[1] - HEAD[0]))
    if y > TELSON[0]: return tel_w((y - TELSON[0]) / (TELSON[1] - TELSON[0]))
    return Wf(y)


# ---------------- armature (v1 names) ----------------
SEG = PER
bones = [("is_root", (0, 0, 0), (0, 0.3, 0), None, False),
         ("is_body", (0, SEG[3][1], ZC), (0, SEG[3][0], ZC), "is_root", True)]
for i in (2, 1, 0):
    bones.append((f"is_seg{i + 1}", (0, SEG[i][1], ZC), (0, SEG[i][0], ZC), "is_body" if i == 2 else f"is_seg{i + 2}", True))
bones.append(("is_head", (0, HEAD[1], ZC), (0, HEAD[0], ZC), "is_seg1", True))
for i in (4, 5, 6):
    bones.append((f"is_seg{i + 1}", (0, SEG[i][0], ZC), (0, SEG[i][1], ZC), "is_body" if i == 4 else f"is_seg{i}", True))
bones += [("is_pleon", (0, PLEON[0][0], ZC), (0, TELSON[0], ZC), "is_seg7", True), ("is_tail", (0, TELSON[0], ZC), (0, TELSON[1], ZC), "is_pleon", True)]
for sx, sn in ((1, "R"), (-1, "L")):
    bones.append((f"is_uro{sn}", (sx * 0.4, 1.0, ZC - 0.03), (sx * 0.5, 1.42, ZC - 0.05), "is_tail", True))
SEGBONE = {i: ("is_body" if i == 3 else f"is_seg{i + 1}") for i in range(7)}
BODY_BONES = ["is_head", "is_seg1", "is_seg2", "is_seg3", "is_body", "is_seg5", "is_seg6", "is_seg7", "is_pleon", "is_tail"]
LEGS = {}
for i in range(7):
    ym = (SEG[i][0] + SEG[i][1]) / 2; W = Wf(ym)
    dy = -(0.3 - 0.07 * i) if i < 3 else 0.12 + 0.08 * (i - 3)            # front 3 pairs reach forward, rear 4 back
    for sx, sn in ((1, "R"), (-1, "L")):
        P = [Vector((sx * W * 0.5, ym, ZC - 0.08)), Vector((sx * (W + 0.02), ym + dy * 0.3, ZC - 0.04)),
             Vector((sx * (W + 0.2), ym + dy * 0.65, ZC + 0.05)), Vector((sx * (W + 0.32), ym + dy, 0.0))]
        names = []
        for k in range(3):
            nm = f"is_leg{sn}{i + 1}_{k + 1}"
            bones.append((nm, tuple(P[k]), tuple(P[k + 1]), names[-1] if names else SEGBONE[i], True)); names.append(nm)
        LEGS[(i, sx)] = (P, names)
ANT = {}
for sx, sn in ((1, "R"), (-1, "L")):                                      # long antennae swept back along the sides
    P0 = Vector((sx * 0.2, -1.46, ZC + 0.01))
    raw = [P0, P0 + Vector((sx * 0.12, -0.13, 0.0)), P0 + Vector((sx * 0.34, -0.12, -0.04)), P0 + Vector((sx * 0.52, 0.15, -0.1)),
           P0 + Vector((sx * 0.63, 0.6, -0.16)), P0 + Vector((sx * 0.68, 1.0, -0.2))]
    pts = catmull(raw, 10)
    idx = [round(k * (len(pts) - 1) / 5) for k in range(6)]
    names = []
    for k in range(5):
        nm = f"is_ant{sn}_{k + 1}"
        bones.append((nm, tuple(pts[idx[k]]), tuple(pts[idx[k + 1]]), names[-1] if names else "is_head", True)); names.append(nm)
    ANT[sx] = (pts, names)
CLAW = {}
for sx, sn in ((1, "R"), (-1, "L")):                                     # maxillipeds (mouth appendages) on the claw bones
    P = [Vector((sx * 0.07, -1.36, ZC - 0.06)), Vector((sx * 0.11, -1.45, ZC - 0.09)), Vector((sx * 0.04, -1.52, ZC - 0.08))]
    bones.append((f"is_claw{sn}_1", tuple(P[0]), tuple(P[1]), "is_head", True))
    bones.append((f"is_claw{sn}_2", tuple(P[1]), tuple(P[2]), f"is_claw{sn}_1", True))
    CLAW[sx] = (P, [f"is_claw{sn}_1", f"is_claw{sn}_2"])
rig = make_armature(col, "GiantIsopod_Rig", bones, (0, 0, 0))


def weighted(name, bm, material, bone_list, falloff=3.0, top=2):
    o_ = finish(col, name, bm, material)
    o_.parent = rig; o_.matrix_parent_inverse = Matrix.Identity(4); bpy.context.view_layer.update()
    distance_weights(o_, rig, bone_list, falloff=falloff, top=top)
    return o_


def merge(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o_ in objs: o_.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join(); return objs[0]


# ---------------- body: plates, underside, spines, uropods, pleopods ----------------
plates = bmesh.new()
add_bm(plates, plate(HEAD_POS, 16))
for p_ in PER_POS: add_bm(plates, plate(p_, 10))
for p_ in PLEON_POS: add_bm(plates, plate(p_, 4))
add_bm(plates, plate(TEL_POS, 18, rear_flag=2.0))
parts = [weighted("is_plates", plates, M_back, BODY_BONES)]
ys = [-1.47 + 2.93 * k / 80 for k in range(81)]
under = [(-1.49, 0, 0, ZC - 0.03)] + [(y, max(0.01, width_at(y) * 0.86), 0.09 * smoothstep(0.0, 0.12, min(y + 1.49, 1.49 - y)) + 0.005, ZC - 0.02) for y in ys] + [(1.48, 0, 0, ZC - 0.03)]
core = loft_fn(under, 40, lambda y, a, x, z: 1 + 0.025 * math.sin(y * 24.0) ** 6 * max(0.0, -math.sin(a)))   # sternite ridges
wrinkle_bm(core, 0.002, 30, 3)
parts.append(weighted("is_underside", core, M_belly, BODY_BONES))
spines = bmesh.new()
for side in (-1, 1):                                                       # 2 x 5 marginal spines + 1 central = 11
    for k in range(5):
        u = 0.55 + 0.09 * k; E = TEL_POS(u, side); t = TEL_POS(min(1.0, u + 0.01), side) - E
        d = (Vector((side * t.y, -side * t.x, 0)).normalized() + Vector((0, 0.6, -0.12))).normalized()
        add_bm(spines, xf(needle(0.011, 0.055 + 0.01 * (k > 2), (0, 0, 0), 0, 0, 0.05, segs=6), T(*(E - d * 0.006 + Vector((0, 0, -0.02)))) @ orient(d)))
E = TEL_POS(1.0, 0.0)
add_bm(spines, xf(needle(0.012, 0.07, (0, 0, 0), 0, 0, 0.03, segs=6), T(*(E + Vector((0, -0.006, -0.02)))) @ orient((0, 1, -0.1))))
parts.append(weighted("is_spines", spines, M_spine, BODY_BONES))
for sx, sn in ((1, "R"), (-1, "L")):                                       # uropods: protopod + two flat rami, spined margins
    uro = bmesh.new()
    base = Vector((sx * 0.42, 0.98, ZC - 0.03))
    add_bm(uro, xf(uvsphere(1.0, None, 14, 8), T(*base) @ Matrix.Diagonal((0.07, 0.09, 0.035, 1))))
    for k, (ang, ln, wd) in enumerate(((14, 0.44, 0.1), (-4, 0.38, 0.085))):
        c = base + Vector((sx * (0.05 + 0.06 * k), 0.24, -0.005 * k))
        add_bm(uro, xf(uvsphere(1.0, None, 20, 8), T(*c) @ RZ(sx * ang) @ Matrix.Diagonal((wd, ln / 2, 0.014, 1))))
        for q in range(8):
            t = 0.15 + 0.8 * q / 7; p = c + RZ(sx * ang).to_3x3() @ Vector((sx * wd * math.sin(math.pi * t), (t - 0.5) * ln, 0))
            add_bm(uro, xf(needle(0.005, 0.03, (0, 0, 0), 0, 0, 0.0, segs=4), T(*p) @ orient(Vector((sx, 0.6, 0)).normalized())))
    parts.append(weighted(f"is_uropod_{sn}", uro, M_back, [f"is_uro{sn}"], top=1))
pleo = bmesh.new()                                                         # pleopods (gill plates) under the pleon
for k in range(5):
    for sx in (-1, 1):
        add_bm(pleo, xf(uvsphere(1.0, None, 12, 6), T(sx * 0.13, 0.66 + 0.11 * k, ZC - 0.1) @ RX(-15) @ Matrix.Diagonal((0.12, 0.09, 0.012, 1))))
parts.append(weighted("is_pleopods", pleo, M_belly, ["is_pleon", "is_tail"]))
body = merge(parts); body.name = "SK_GiantIsopod_Body"; body.data.name = "SK_GiantIsopod_Body"

# ---------------- legs (6 podomeres along one tube), antennae, maxillipeds ----------------
limbs = []
QB = [0.0, 0.28, 0.4, 0.58, 0.7, 0.86, 1.0]                               # basis, ischium, merus, carpus, propodus, dactylus
def leg_r(q, s):
    j = max(i for i in range(6) if QB[i] <= q) if q < 1 else 5
    t = (q - QB[j]) / (QB[j + 1] - QB[j])
    base = s * (0.034 * (1 - q) ** 0.35 + 0.012)
    if j == 5: return base * (1 - t) ** 0.6 + 0.002
    return base * (0.8 + 0.2 * smoothstep(0.0, 0.15, t)) * (1 + 0.08 * t) * (1.25 if j == 0 else 1.0)
for (i, sx), (P, names) in LEGS.items():
    pts = catmull(P, 10); s = 1.12 if i < 3 else 1.0
    bm = tube(pts, lambda q, s=s: leg_r(q, s), up=(0, 1, 0), sides=12)
    for q in (0.6, 0.66, 0.74, 0.8):                                       # spines on carpus / propodus
        p = pts[int(q * (len(pts) - 1))]; d = Vector((-sx * 0.6, 0.0, -1.0)).normalized()
        add_bm(bm, xf(needle(0.006, 0.03, (0, 0, 0), 0, 0, 0.1, segs=4), T(*p) @ orient(d)))
    limbs.append(weighted(f"is_leg_{i}_{sx}", bm, M_leg, names + [SEGBONE[i]], top=2))
    claw = xf(needle(0.012, 0.05, (0, 0, 0), 0, 0, 0.05, segs=5), T(*pts[-4]) @ orient((P[3] - P[2]).normalized()))
    limbs.append(weighted(f"is_dactyl_{i}_{sx}", claw, M_spine, [names[2]], top=1))
for sx, (pts, names) in ANT.items():                                      # thick peduncle, annulated flagellum
    bm = tube(pts, lambda q: (0.028 * (1 - q) ** 1.6 + 0.004) * (1 + (0.12 if q < 0.25 else 0.3) * math.sin(q * (60 if q < 0.25 else 260)) ** 8), up=(0, 0, 1), sides=9)
    limbs.append(weighted(f"is_ant_{sx}", bm, M_leg, names))
for sx, (P, names) in CLAW.items():
    bm = tube(catmull([P[0], P[1], P[2]], 4), lambda q: 0.03 * (1 - 0.5 * q), up=(0, 0, 1), sides=10)
    add_bm(bm, xf(uvsphere(1.0, None, 12, 6), T(*P[0].lerp(P[1], 0.5)) @ Matrix.Diagonal((0.06, 0.07, 0.015, 1))))
    limbs.append(weighted(f"is_maxilliped_{sx}", bm, M_leg, names))
body = merge([body] + limbs)
body.data.shade_smooth()

# ---------------- rigid head parts: compound eyes (follow the head surface), antennules, mandibles ----------------
def head_normal(u, xn, sx):
    a = HEAD_POS(min(1, u + 1e-3), xn) - HEAD_POS(max(0, u - 1e-3), xn)
    b = HEAD_POS(u, xn + 1e-3) - HEAD_POS(u, xn - 1e-3)
    n = a.cross(b).normalized()
    return n if n.dot(Vector((sx * 0.5, 0, 1))) > 0 else -n
for sx in (-1, 1):
    eye = bmesh.new(); NA, NB_ = 18, 10; g = []
    for a in range(NA + 1):
        u = 0.1 + 0.52 * a / NA; xi = 0.995 - 0.47 * math.sin(math.pi * a / NA) ** 0.6   # oval patch along the head margin
        row = []
        for b in range(NB_ + 1):
            xn = sx * (xi + (0.995 - xi) * b / NB_)
            off = 0.004 + 0.02 * (math.sin(math.pi * a / NA) * math.sin(math.pi * b / NB_)) ** 0.6
            row.append(eye.verts.new(HEAD_POS(u, xn) + head_normal(u, xn, sx) * off))
        g.append(row)
    for a in range(NA):
        for b in range(NB_):
            eye.faces.new((g[a][b], g[a][b + 1], g[a + 1][b + 1], g[a + 1][b]))
    eye.normal_update()
    if sum(f.normal.dot(Vector((sx * 0.5, 0, 1))) for f in eye.faces) < 0:
        bmesh.ops.reverse_faces(eye, faces=eye.faces[:])
    rigid_bm_to_group(body, eye, M_eye, "is_head")
    P0 = Vector((sx * 0.06, -1.49, ZC + 0.03))                              # antennule (short first antenna)
    rigid_bm_to_group(body, tube(catmull([P0, P0 + Vector((sx * 0.03, -0.1, 0.05)), P0 + Vector((sx * 0.09, -0.2, 0.06)), P0 + Vector((sx * 0.16, -0.27, 0.04))], 4),
                                 lambda q: 0.013 * (1 - 0.7 * q) * (1 + 0.25 * math.sin(q * 90) ** 8), up=(0, 0, 1), sides=7), M_leg, "is_head")
    rigid_bm_to_group(body, xf(uvsphere(1.0, None, 12, 6), T(sx * 0.07, -1.43, ZC - 0.07) @ RZ(sx * 20) @ Matrix.Diagonal((0.05, 0.035, 0.03, 1))), M_spine, "is_head")   # mandible
rigid_bm_to_group(body, xf(uvsphere(1.0, None, 14, 6), T(0, -1.49, ZC - 0.03) @ Matrix.Diagonal((0.08, 0.03, 0.025, 1))), M_back, "is_head")                      # frontal lamina
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
            kr(bn, f, bend_q(bn, Z, D(4 + 2 * k) * amp * math.sin(math.tau * t - 0.6 * k + sx)) @ bend_q(bn, X, D(3) * amp * math.sin(math.tau * t * 2 - 0.4 * k)))


def mouth(f, open_):
    for sx, (P, names) in CLAW.items():
        kr(names[0], f, bend_q(names[0], Z, -sx * open_ * D(28)) @ bend_q(names[0], X, open_ * D(12)))
        kr(names[1], f, bend_q(names[1], Z, sx * open_ * D(15)))


def uropods(f, t, amp):
    for sx, sn in ((1, "R"), (-1, "L")):
        kr(f"is_uro{sn}", f, bend_q(f"is_uro{sn}", Z, sx * D(6) * amp * math.sin(math.tau * t + sx)))


bpy.context.view_layer.objects.active = rig
new_action(rig, "IS_Idle")                       # antennae sweep slowly, legs shift a little, mouthparts work, slow breathing
F = 96
for f in range(F + 1):
    t = f / F
    antennae(f + 1, t)
    mouth(f + 1, 0.15 + 0.2 * max(0.0, math.sin(math.tau * t * 4)) ** 6)
    uropods(f + 1, t * 2, 0.6)
    for (i, sx), (P, names) in LEGS.items():
        kr(names[0], f + 1, bend_q(names[0], Z, sx * D(2.5) * math.sin(math.tau * t + i * 0.9)))
    key(rig.pose.bones["is_body"], f + 1, loc=(0, 0, 0.005 * math.sin(math.tau * t * 2)))
rig.animation_data.action.frame_range = (1, F + 1)

new_action(rig, "IS_Walk")                       # metachronal wave: phase runs back-to-front, left/right in antiphase
F = 36
for f in range(F + 1):
    t = f / F
    for (i, sx), (P, names) in LEGS.items():
        ph = math.tau * (t + i * 0.12 + (0.5 if sx < 0 else 0.0))
        swing = D(16) * math.cos(ph); lift = D(12) * max(0.0, math.sin(ph))
        kr(names[0], f + 1, bend_q(names[0], Z, sx * swing) @ bend_q(names[0], Y, -sx * lift))
        kr(names[1], f + 1, bend_q(names[1], Y, -sx * lift * 0.6))
        kr(names[2], f + 1, bend_q(names[2], Y, sx * lift * 0.5))
    antennae(f + 1, t * 2, 0.7)
    mouth(f + 1, 0.15)
    uropods(f + 1, t * 2, 1.0)
    for k, bn in enumerate(BODY_BONES[1:9]):
        kr(bn, f + 1, bend_q(bn, Z, D(1.0) * math.sin(math.tau * t * 2 - k * 0.5)))
    key(rig.pose.bones["is_body"], f + 1, loc=(0, 0, 0.005 * math.sin(math.tau * t * 2)))
rig.animation_data.action.frame_range = (1, F + 1)

new_action(rig, "IS_Attack")                     # rears the front body, front legs reach and pin, mouthparts open, ~0.6 m lunge
F = 30
FRONT = ["is_seg3", "is_seg2", "is_seg1", "is_head"]
for f in range(F + 1):
    rear = ease(f / 9) * (1 - ease((f - 10) / 4))
    slam = ease((f - 10) / 5) * (1 - ease((f - 18) / 10))
    for k, bn in enumerate(FRONT):
        kr(bn, f + 1, bend_q(bn, X, -D(12) * rear + D(6) * slam))
    mouth(f + 1, 1.0 * rear + 0.3 * slam + 0.1)
    for (i, sx), (P, names) in LEGS.items():
        if i < 3:
            r_ = rear * (1.0 - 0.25 * i)
            kr(names[0], f + 1, bend_q(names[0], Y, -sx * D(38) * r_) @ bend_q(names[0], Z, -sx * D(22) * r_))
            kr(names[1], f + 1, bend_q(names[1], Y, sx * D(25) * r_ - sx * D(15) * slam))
            kr(names[2], f + 1, bend_q(names[2], Y, sx * D(20) * slam))
        else:
            kr(names[0], f + 1, Quaternion())
    antennae(f + 1, f / 30, 1.4 * rear + 0.3)
    uropods(f + 1, f / 15, 1.5 * rear)
    key(rig.pose.bones["is_root"], f + 1, loc=(0, -0.6 * ease((f - 9) / 6), 0))
rig.animation_data.action.frame_range = (1, F + 1)
_act = bpy.data.actions["IS_Walk"]; rig.animation_data.action = _act
if hasattr(rig.animation_data, "action_slot") and len(_act.slots): rig.animation_data.action_slot = _act.slots[0]
rig.location = RIG_LOC


# ---------------- shaders (procedural; baked into T_GiantIsopod_* by bake_and_export) ----------------
def carapace(mat):
    nb = NB(mat)
    edge = nb.n("ShaderNodeAttribute", attribute_name="pedge").outputs["Fac"]
    front = nb.n("ShaderNodeAttribute", attribute_name="pfront").outputs["Fac"]
    mott = nb.noise(2.5, 6, 0.6)                                                           # big blotches, strong contrast
    col_ = nb.ramp(mott.outputs["Fac"], [(0.32, (0.46, 0.3, 0.4)), (0.5, (0.64, 0.45, 0.53)), (0.7, (0.78, 0.6, 0.62))]).outputs[0]   # mauve-lilac
    tint = nb_map(nb, nb.noise(0.9, 3, 0.5).outputs["Fac"], 0.42, 0.66)
    col_ = nb.mix(col_, (0.72, 0.5, 0.24), nb.math("MULTIPLY", tint, 0.7))                  # amber-tan regions
    col_ = nb.mix(col_, (0.66, 0.4, 0.14), nb.math("MULTIPLY", edge, 0.9))                 # amber-brown margin bands
    col_ = nb.mix(col_, (0.26, 0.15, 0.18), nb.math("MULTIPLY", front, 0.8))               # dark front strip slid under the plate ahead
    spots = nb_map(nb, nb.voronoi(32.0, "F1").outputs["Distance"], 0.06, 0.14, 1.0, 0.0)   # ~2-3 cm speckles
    col_ = nb.mix(col_, (0.36, 0.2, 0.22), nb.math("MULTIPLY", spots, 0.65))
    pits = nb_map(nb, nb.voronoi(90.0, "F1").outputs["Distance"], 0.05, 0.13, 1.0, 0.0)   # punctation
    col_ = nb.mix(col_, (0.3, 0.18, 0.2), nb.math("MULTIPLY", pits, 0.7))
    silt = nb_map(nb, nb.noise(4.0, 5, 0.65).outputs["Fac"], 0.56, 0.68)                   # sediment patches
    col_ = nb.mix(col_, (0.5, 0.4, 0.26), nb.math("MULTIPLY", silt, 0.6))
    scr = nb_map(nb, nb.noise(30.0, 2, 0.5, vec=nb.mapping(scale=(6, 0.4, 6))).outputs["Fac"], 0.66, 0.72)   # fine scratches
    col_ = nb.mix(col_, (0.8, 0.76, 0.72), nb.math("MULTIPLY", scr, 0.35))
    gran = nb.noise(60.0, 4, 0.6)
    rough = nb.math("ADD", nb_map(nb, mott.outputs["Fac"], 0.3, 0.7, 0.24, 0.4), nb.math("MULTIPLY", silt, 0.4))
    h = nb.math("SUBTRACT", nb.math("MULTIPLY", gran.outputs["Fac"], 0.35), nb.math("ADD", nb.math("MULTIPLY", pits, 0.6), nb.math("MULTIPLY", spots, 0.25)), clamp=False)
    growth = nb.noise(22.0, 3, 0.5, vec=nb.mapping(scale=(0.25, 8, 0.25)))                 # growth lines across each segment
    h = nb.math("ADD", h, nb.math("MULTIPLY", growth.outputs["Fac"], 0.35), clamp=False)
    nb_finish_full(nb, col_, rough, h, bump=0.8, dist=0.008, spec=0.55)
    mat.diffuse_color = (0.64, 0.45, 0.5, 1)


def underside(mat):
    nb = NB(mat)
    m = nb.noise(8.0, 5, 0.6)
    col_ = nb.ramp(m.outputs["Fac"], [(0.3, (0.8, 0.6, 0.5)), (0.7, (0.92, 0.78, 0.62))]).outputs[0]   # warm cream
    rid = nb.noise(20.0, 3, 0.5, vec=nb.mapping(scale=(0.3, 6, 0.3)))
    col_ = nb.mix(col_, (0.6, 0.5, 0.45), nb.math("MULTIPLY", nb_map(nb, rid.outputs["Fac"], 0.5, 0.65), 0.5))
    rough = nb_map(nb, m.outputs["Fac"], 0.3, 0.7, 0.3, 0.45)
    h = nb.math("ADD", nb.math("MULTIPLY", rid.outputs["Fac"], 0.5), nb.math("MULTIPLY", nb.noise(40.0, 5, 0.6).outputs["Fac"], 0.3), clamp=False)
    nb_finish_full(nb, col_, rough, h, bump=0.35, dist=0.006, spec=0.5)
    mat.diffuse_color = (0.8, 0.7, 0.62, 1)


def legs(mat):
    nb = NB(mat)
    m = nb.noise(10.0, 5, 0.6)
    col_ = nb.ramp(m.outputs["Fac"], [(0.3, (0.76, 0.56, 0.54)), (0.7, (0.9, 0.74, 0.64))]).outputs[0]   # pale, slightly translucent cream-lilac
    rings = nb.noise(60.0, 2, 0.5, vec=nb.mapping(scale=(0.2, 0.2, 6)))
    col_ = nb.mix(col_, (0.5, 0.42, 0.38), nb.math("MULTIPLY", nb_map(nb, rings.outputs["Fac"], 0.55, 0.7), 0.55))
    col_ = nb.mix(col_, (0.72, 0.48, 0.24), nb.math("MULTIPLY", nb_map(nb, nb.noise(3.0, 3, 0.5).outputs["Fac"], 0.45, 0.65), 0.45))
    spk = nb_map(nb, nb.voronoi(70.0, "F1").outputs["Distance"], 0.05, 0.12, 1.0, 0.0)
    col_ = nb.mix(col_, (0.36, 0.3, 0.3), nb.math("MULTIPLY", spk, 0.5))
    nb_finish_full(nb, col_, 0.33, m.outputs["Fac"], bump=0.25, dist=0.004, spec=0.55)
    mat.diffuse_color = (0.74, 0.65, 0.6, 1)


def compound_eye(mat):
    nb = NB(mat)
    fac = nb.voronoi(380.0, "DISTANCE_TO_EDGE")
    facet = nb_map(nb, fac.outputs["Distance"], 0.0, 0.06)
    shine = nb.noise(4.0, 3, 0.5)
    base = nb.ramp(shine.outputs["Fac"], [(0.3, (0.035, 0.03, 0.04)), (0.7, (0.09, 0.075, 0.085))]).outputs[0]
    c = nb.mix((0.16, 0.14, 0.15), base, facet)                                            # lighter facet borders, not a black blob
    glint = nb.mix((0, 0, 0), (0.035, 0.04, 0.03), nb.math("MULTIPLY", facet, nb_map(nb, shine.outputs["Fac"], 0.5, 0.75)))   # eyeshine
    nb_finish_full(nb, c, 0.08, facet, bump=0.35, dist=0.0015, emit=glint, emit_strength=1.0, spec=0.85)
    mat.diffuse_color = (0.08, 0.07, 0.08, 1)


carapace(M_back); underside(M_belly); legs(M_leg); compound_eye(M_eye)
simple_shader(M_spine, (0.48, 0.38, 0.27), 0.3, noise_scale=40, var=0.4, bump=0.2)
M_spine.diffuse_color = (0.48, 0.38, 0.27, 1)
for m_ in bpy.data.materials:
    if m_.name.startswith("M_IsR_"): m_.use_fake_user = True
IS_INFO = {"tris": sum(len(p.vertices) - 2 for p in body.data.polygons), "bones": len(rig.data.bones),
           "unweighted": sum(1 for v in body.data.vertices if not v.groups), "mats": [m.name for m in body.data.materials],
           "dims": tuple(round(d, 2) for d in body.dimensions)}
print("IS_INFO", IS_INFO)


def bake_and_export(size=4096):
    """UV-unwrap, bake BaseColor (x baked AO) / Normal / Roughness / Emissive in the rest pose, swap to M_GiantIsopod, export SK_GiantIsopod.fbx."""
    import os, numpy as np
    uv_prep(["SK_GiantIsopod_Body"])
    o = bpy.data.objects["SK_GiantIsopod_Body"]; rig.data.pose_position = "REST"
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()                                       # equal texel density first ...
    bm = bmesh.from_edit_mesh(o.data); uvl = bm.loops.layers.uv.active
    SC = {i: {"M_IsR_Carapace": 2.0, "M_IsR_Eye": 2.0, "M_IsR_Underside": 0.7}.get(m.name, 1.0) for i, m in enumerate(o.data.materials)}
    for f in bm.faces:                                                       # ... then 2x for the back and eyes (what players see), less for the belly
        for l in f.loops: l[uvl].uv *= SC[f.material_index]
    bmesh.update_edit_mesh(o.data)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    scn = bpy.context.scene; scn.render.engine = "CYCLES"; scn.cycles.device = "CPU"
    scn.render.bake.margin = 8; scn.render.bake.use_clear = True
    if scn.world: scn.world.light_settings.distance = 0.25
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    out_dir = os.path.join(OUT_DIR, "Textures"); os.makedirs(out_dir, exist_ok=True)
    passes = [("BaseColor", "DIFFUSE", "sRGB"), ("Normal", "NORMAL", "Non-Color"), ("Roughness", "ROUGHNESS", "Non-Color"),
              ("Emissive", "EMIT", "sRGB"), ("AO", "AO", "Non-Color")]
    imgs = {l: bpy.data.images.new(f"T_GiantIsopod_{l}", size, size, alpha=False) for l, _, _ in passes}
    for l, _, cs in passes: imgs[l].colorspace_settings.name = cs
    nodes = []
    for s in o.material_slots:
        n = s.material.node_tree.nodes.new("ShaderNodeTexImage"); n.name = "_bake"; s.material.node_tree.nodes.active = n; nodes.append(n)
    for l, bt, _ in passes:
        scn.cycles.samples = 16 if bt == "AO" else 4
        for n in nodes: n.image = imgs[l]; n.id_data.nodes.active = n
        kw = dict(pass_filter={"COLOR"}) if bt == "DIFFUSE" else (dict(normal_space="TANGENT") if bt == "NORMAL" else {})
        bpy.ops.object.bake(type=bt, **kw); print("BAKED", l, flush=True)
    for n in nodes: n.id_data.nodes.remove(n)
    px = size * size * 4                                                     # AO multiplied into BaseColor (crevices between plates, under the shield)
    b = np.empty(px, np.float32); imgs["BaseColor"].pixels.foreach_get(b)
    a = np.empty(px, np.float32); imgs["AO"].pixels.foreach_get(a)
    b = b.reshape(-1, 4); b[:, :3] *= 0.5 + 0.5 * a.reshape(-1, 4)[:, :1]
    imgs["BaseColor"].pixels.foreach_set(b.ravel())
    for l in ("BaseColor", "Normal", "Roughness", "Emissive"):
        p = os.path.join(out_dir, f"T_GiantIsopod_{l}.png"); imgs[l].filepath_raw = p; imgs[l].file_format = "PNG"; imgs[l].save()
    bpy.data.images.remove(imgs["AO"])
    rig.data.pose_position = "POSE"
    return finalize(["SK_GiantIsopod_Body"])
