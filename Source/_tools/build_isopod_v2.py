# Giant isopod v2 (2026-11-19): a REALISTIC Bathynomus giganteus scaled up to ~3 m (replaces the 2026-11-09 monster-ified v1).
# Faces -Y, crawls on the ground (feet at z = 0). Bone names and animation names are kept from v1
# (is_root / is_body / is_seg1..7 / is_head / is_pleon / is_tail / is_leg{L,R}{1..7}_{1..3} / is_ant{L,R}_{1..5} /
#  is_claw{L,R}_{1,2} = maxillipeds) + new is_uro{L,R} (uropods), so the Unreal side keeps working.
# Anatomy: cephalon with large kidney-shaped compound eyes, antennules + long annulated antennae, maxillipeds;
# 7 overlapping pereonites with pointed coxal plates; 5 short pleonites; broad pleotelson with a spined rear margin;
# leaf-like uropods; 7 pairs of 6-segment walking legs (front 3 pairs point forward, rear 4 back); 5 pairs of pleopods.
# Colour: pale lilac-grey back with darker rear margins, cream-pink underside, near-black faceted eyes.
# exec after mk.py, rig.py, horror.py, horror2.py, monsters_v2_pipeline.py.   bake_and_export() bakes 4096 textures + SK fbx.
from mathutils import Quaternion
random.seed(91)
RIG_LOC = (-6.5, -19.5, 0.0)
col = get_col("GiantIsopod", clear=True)
for a_ in [a_ for a_ in bpy.data.actions if a_.name.startswith("IS_")]:
    bpy.data.actions.remove(a_)


def _m(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)
M_back, M_belly, M_leg, M_eye, M_spine = _m("M_IsR_Carapace"), _m("M_IsR_Underside"), _m("M_IsR_Leg"), _m("M_IsR_Eye"), _m("M_IsR_Spine")

ZC = 0.34
WK = [(-1.5, 0.05), (-1.46, 0.22), (-1.38, 0.32), (-1.24, 0.38), (-1.18, 0.47), (-0.9, 0.55), (-0.5, 0.6), (0.0, 0.62),
      (0.4, 0.6), (0.62, 0.56), (0.92, 0.5), (1.1, 0.46), (1.3, 0.36), (1.45, 0.2), (1.5, 0.05)]
HK = [(-1.5, 0.03), (-1.4, 0.1), (-1.24, 0.15), (-1.18, 0.2), (-0.6, 0.26), (0.0, 0.27), (0.5, 0.24), (0.92, 0.17), (1.2, 0.1), (1.5, 0.03)]
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


# dorsal section: dome + lateral coxal flare (pointed, slightly down) ; side flag marks the rim for the shader
SECTION = [(1.16, -0.42, 1), (1.08, -0.2, 1)] + [(math.cos(math.pi * k / 28), math.sin(math.pi * k / 28) ** 0.85, 0) for k in range(29)] + [(-1.08, -0.2, 1), (-1.16, -0.42, 1)]
def tergite(y0, y1, rows=7, flare=1.0, lip=0.03):
    """Arched dorsal plate y0..y1: rear edge lifts and overlaps the next plate; lateral flares form the coxal points."""
    bm = bmesh.new(); el = bm.verts.layers.float.new("pedge"); grid = []
    for r in range(rows + 1):
        u = r / rows; y = y0 + (y1 - y0) * u
        W, H = Wf(y), Hf(y); sc = 0.97 + 0.05 * u
        row = []
        for x, z, side in SECTION:
            fx = x if not side else math.copysign(1.0 + (abs(x) - 1.0) * flare * (0.6 + 0.6 * u), x)    # coxal point grows to the rear edge
            v = bm.verts.new((fx * W * sc, y + (0.05 * u * side * flare), ZC + z * H * sc + lip * u))
            v[el] = max(smoothstep(0.7, 1.0, u), float(side))
            row.append(v)
        grid.append(row)
    for r in range(rows):
        for c in range(len(SECTION) - 1):
            bm.faces.new((grid[r][c], grid[r + 1][c], grid[r + 1][c + 1], grid[r][c + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.016)
    wrinkle_bm(bm, 0.0015, 40, int(y0 * 10) + 7)
    return bm


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
    bones.append((f"is_uro{sn}", (sx * 0.4, 1.0, ZC - 0.06), (sx * 0.5, 1.46, ZC - 0.1), "is_tail", True))
SEGBONE = {i: ("is_body" if i == 3 else f"is_seg{i + 1}") for i in range(7)}
BODY_BONES = ["is_head", "is_seg1", "is_seg2", "is_seg3", "is_body", "is_seg5", "is_seg6", "is_seg7", "is_pleon", "is_tail"]
LEGS = {}
for i in range(7):
    ym = (SEG[i][0] + SEG[i][1]) / 2; W = Wf(ym); dy = (i - 3) * 0.1 + (-0.06 if i < 3 else 0.04)
    for sx, sn in ((1, "R"), (-1, "L")):
        P = [Vector((sx * W * 0.5, ym, ZC - 0.12)), Vector((sx * (W + 0.04), ym + dy * 0.3, ZC + 0.02)),
             Vector((sx * (W + 0.3), ym + dy * 0.7, 0.2)), Vector((sx * (W + 0.38), ym + dy, 0.0))]
        names = []
        for k in range(3):
            nm = f"is_leg{sn}{i + 1}_{k + 1}"
            bones.append((nm, tuple(P[k]), tuple(P[k + 1]), names[-1] if names else SEGBONE[i], True)); names.append(nm)
        LEGS[(i, sx)] = (P, names)
ANT = {}
for sx, sn in ((1, "R"), (-1, "L")):
    P0 = Vector((sx * 0.14, -1.46, ZC + 0.0))
    raw = [P0, P0 + Vector((sx * 0.14, -0.2, 0.05)), P0 + Vector((sx * 0.48, -0.28, 0.05)), P0 + Vector((sx * 0.82, -0.05, 0.02)), P0 + Vector((sx * 0.98, 0.42, -0.04))]
    pts = catmull(raw, 10)
    idx = [round(k * (len(pts) - 1) / 5) for k in range(6)]
    names = []
    for k in range(5):
        nm = f"is_ant{sn}_{k + 1}"
        bones.append((nm, tuple(pts[idx[k]]), tuple(pts[idx[k + 1]]), names[-1] if names else "is_head", True)); names.append(nm)
    ANT[sx] = (pts, names)
CLAW = {}
for sx, sn in ((1, "R"), (-1, "L")):                                     # maxillipeds (mouth appendages) on v1's claw bones
    P = [Vector((sx * 0.07, -1.34, ZC - 0.11)), Vector((sx * 0.11, -1.44, ZC - 0.15)), Vector((sx * 0.04, -1.52, ZC - 0.14))]
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


# ---------------- body: dorsal plates, underside, spines, uropods, pleopods ----------------
plates = bmesh.new()
add_bm(plates, tergite(HEAD[0], HEAD[1] + 0.03, rows=9, flare=0.25, lip=0.015))           # cephalon
for (y0, y1) in PER:
    add_bm(plates, tergite(y0 - 0.025, y1 + 0.03))                                         # pereonites (overlap)
for (y0, y1) in PLEON:
    add_bm(plates, tergite(y0 - 0.012, y1 + 0.02, rows=3, flare=0.8, lip=0.012))           # pleonites
add_bm(plates, tergite(TELSON[0] - 0.02, TELSON[1], rows=12, flare=0.15, lip=0.0))        # pleotelson
parts = [weighted("is_plates", plates, M_back, BODY_BONES)]
under = [(HEAD[0] + 0.03, 0, 0, ZC - 0.05)] + [(y, Wf(y) * 0.88, 0.13 * smoothstep(0.0, 0.1, 1.45 - abs(y)) + 0.01, ZC - 0.05)
                                               for y in [HEAD[0] + 0.06 + (TELSON[1] - HEAD[0] - 0.12) * k / 72 for k in range(73)]] + [(TELSON[1] - 0.03, 0, 0, ZC - 0.05)]
core = loft_fn(under, 40, lambda y, a, x, z: 1 + 0.03 * math.sin(y * 24.0) ** 6 * max(0.0, -math.sin(a)))   # sternite ridges
wrinkle_bm(core, 0.003, 30, 3)
parts.append(weighted("is_underside", core, M_belly, BODY_BONES))
spines = bmesh.new()
for k in range(9):                                                                         # pleotelson rear-margin spines
    a = -0.95 + 1.9 * k / 8; y = TELSON[1] - 0.3 * (1 - math.cos(a)); W = Wf(min(1.49, y))
    p = Vector((math.sin(a) * W * 1.02, y, ZC + 0.01)); d = Vector((math.sin(a) * 0.9, 1.0, -0.05)).normalized()
    add_bm(spines, xf(needle(0.016, 0.09 + 0.02 * (k == 4), (0, 0, 0), 0, 0, 0.05, segs=7), T(*p) @ orient(d)))
parts.append(weighted("is_spines", spines, M_spine, BODY_BONES))
for sx, sn in ((1, "R"), (-1, "L")):                                                       # uropods: protopod + two leaf rami with setae
    uro = bmesh.new()
    base = Vector((sx * 0.42, 1.0, ZC - 0.06))
    add_bm(uro, xf(uvsphere(1.0, None, 14, 8), T(*base) @ Matrix.Diagonal((0.07, 0.1, 0.04, 1))))
    for k, (ang, ln, wd) in enumerate(((10, 0.46, 0.11), (-14, 0.4, 0.09))):
        leaf = uvsphere(1.0, None, 18, 8)
        xf(leaf, T(*(base + Vector((sx * (0.04 + 0.05 * k), 0.24, -0.02 - 0.01 * k)))) @ RZ(sx * ang) @ Matrix.Diagonal((wd, ln / 2, 0.018, 1)))
        add_bm(uro, leaf)
        for q in range(9):                                                                 # fringing setae on the outer edge
            t = q / 8; p = base + Vector((sx * (0.04 + 0.05 * k), 0.06 + ln * 0.9 * t, -0.02))
            p += (RZ(sx * ang).to_3x3() @ Vector((sx * wd * math.sin(math.pi * t), 0, 0)))
            add_bm(uro, xf(needle(0.004, 0.045, (0, 0, 0), 0, 0, 0.0, segs=4), T(*p) @ orient(Vector((sx, 0.5, 0)).normalized())))
    parts.append(weighted(f"is_uropod_{sn}", uro, M_back, [f"is_uro{sn}"], top=1))
pleo = bmesh.new()                                                                         # pleopods (gill plates) under the pleon
for k in range(5):
    for sx in (-1, 1):
        lf = uvsphere(1.0, None, 12, 6)
        xf(lf, T(sx * 0.13, 0.66 + 0.11 * k, ZC - 0.17) @ RX(-15) @ Matrix.Diagonal((0.12, 0.09, 0.012, 1)))
        add_bm(pleo, lf)
parts.append(weighted("is_pleopods", pleo, M_belly, ["is_pleon", "is_tail"]))
body = merge(parts); body.name = "SK_GiantIsopod_Body"; body.data.name = "SK_GiantIsopod_Body"

# ---------------- legs (6 podomeres on 3 bones), antennae, maxillipeds ----------------
limbs = []
POD = [(0.05, 0.042), (0.042, 0.034), (0.034, 0.028), (0.028, 0.022), (0.022, 0.014), (0.014, 0.003)]   # basis .. dactyl radii
for (i, sx), (P, names) in LEGS.items():
    bm = bmesh.new(); s = 0
    for k in range(3):                                                                     # two podomeres per bone, joint knobs between
        a_, b_ = P[k], P[k + 1]
        for h in range(2):
            p0, p1 = a_.lerp(b_, h * 0.5), a_.lerp(b_, h * 0.5 + 0.5)
            r0, r1 = POD[s]; s += 1
            add_bm(bm, tube([p0, p0.lerp(p1, 0.5) + Vector((0, 0, 0.006)), p1], lambda q, r0=r0, r1=r1: (r0 + (r1 - r0) * q) * (1 + 0.1 * math.sin(math.pi * q)), up=(0, 1, 0), sides=10))
            if s < 6: add_bm(bm, uvsphere(r1 * 1.08, T(*p1), 10, 6))
        if k > 0:                                                                          # short spines on the merus / propodus
            for q in range(3):
                p = a_.lerp(b_, 0.25 + 0.25 * q); d = (Vector((0, 0, -1)) + (b_ - a_).normalized() * 0.6).normalized()
                add_bm(bm, xf(needle(POD[2 * k][0] * 0.25, 0.025, (0, 0, 0), 0, 0, 0.1, segs=5), T(*p) @ orient(d)))
    limbs.append(weighted(f"is_leg_{i}_{sx}", bm, M_leg, names + [SEGBONE[i]], top=2))
for sx, (pts, names) in ANT.items():                                                       # long antenna: thick peduncle, annulated flagellum
    bm = tube(pts, lambda q: (0.024 * (1 - q) ** 1.6 + 0.004) * (1 + (0.12 if q < 0.25 else 0.3) * math.sin(q * (60 if q < 0.25 else 260)) ** 8), up=(0, 0, 1), sides=9)
    limbs.append(weighted(f"is_ant_{sx}", bm, M_leg, names))
for sx, (P, names) in CLAW.items():                                                        # maxilliped: flat plate + palp
    bm = tube(catmull([P[0], P[1], P[2]], 4), lambda q: 0.03 * (1 - 0.5 * q), up=(0, 0, 1), sides=10)
    add_bm(bm, xf(uvsphere(1.0, None, 12, 6), T(*P[0].lerp(P[1], 0.5)) @ Matrix.Diagonal((0.06, 0.07, 0.015, 1))))
    limbs.append(weighted(f"is_maxilliped_{sx}", bm, M_leg, names))
body = merge([body] + limbs)
body.data.shade_smooth()

# ---------------- rigid head parts: compound eyes, antennules, mandibles, frontal lamina ----------------
for sx in (-1, 1):
    c = Vector((sx * 0.29, -1.34, ZC + 0.07))
    e = uvsphere(1.0, None, 32, 18)
    for v in e.verts:                                                                       # kidney shape (notch toward the antenna)
        v.co.y -= 0.18 * max(0.0, v.co.x * sx) ** 2 * (1 if v.co.y < 0 else 0)
    xf(e, T(*c) @ RZ(sx * 22) @ RY(-sx * 25) @ Matrix.Diagonal((0.075, 0.16, 0.09, 1)))
    rigid_bm_to_group(body, e, M_eye, "is_head")
    P0 = Vector((sx * 0.06, -1.47, ZC + 0.04))                                             # antennule (short first antenna)
    rigid_bm_to_group(body, tube(catmull([P0, P0 + Vector((sx * 0.03, -0.1, 0.05)), P0 + Vector((sx * 0.09, -0.22, 0.07)), P0 + Vector((sx * 0.16, -0.3, 0.05))], 4),
                                 lambda q: 0.013 * (1 - 0.7 * q) * (1 + 0.25 * math.sin(q * 90) ** 8), up=(0, 0, 1), sides=7), M_leg, "is_head")
    rigid_bm_to_group(body, xf(uvsphere(1.0, None, 12, 6), T(sx * 0.07, -1.42, ZC - 0.1) @ RZ(sx * 20) @ Matrix.Diagonal((0.05, 0.035, 0.03, 1))), M_spine, "is_head")   # mandible
rigid_bm_to_group(body, xf(uvsphere(1.0, None, 14, 6), T(0, -1.5, ZC - 0.02) @ Matrix.Diagonal((0.08, 0.03, 0.025, 1))), M_back, "is_head")                      # frontal lamina
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
            kr(bn, f, bend_q(bn, Z, D(5 + 2 * k) * amp * math.sin(math.tau * t - 0.6 * k + sx)) @ bend_q(bn, X, D(3) * amp * math.sin(math.tau * t * 2 - 0.4 * k)))


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
        swing = D(18) * math.cos(ph); lift = D(14) * max(0.0, math.sin(ph))
        kr(names[0], f + 1, bend_q(names[0], Z, sx * swing) @ bend_q(names[0], Y, -sx * lift))
        kr(names[1], f + 1, bend_q(names[1], Y, -sx * lift * 0.6))
        kr(names[2], f + 1, bend_q(names[2], Y, sx * lift * 0.5))
    antennae(f + 1, t * 2, 0.7)
    mouth(f + 1, 0.15)
    uropods(f + 1, t * 2, 1.0)
    for k, bn in enumerate(BODY_BONES[1:9]):
        kr(bn, f + 1, bend_q(bn, Z, D(1.2) * math.sin(math.tau * t * 2 - k * 0.5)))
    key(rig.pose.bones["is_body"], f + 1, loc=(0, 0, 0.006 * math.sin(math.tau * t * 2)))
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
    a = nb.n("ShaderNodeAttribute", attribute_name="pedge"); edge = a.outputs["Fac"]
    P = nb_warp(nb, 0.01, 8.0)
    sep = nb.n("ShaderNodeSeparateXYZ"); nb.L(nb.obj, sep.inputs[0]); Zc = sep.outputs["Z"]
    mott = nb.noise(4.0, 6, 0.55)
    col_ = nb.ramp(mott.outputs["Fac"], [(0.3, (0.42, 0.38, 0.41)), (0.55, (0.55, 0.5, 0.52)), (0.8, (0.66, 0.6, 0.6))]).outputs[0]   # pale lilac-grey
    col_ = nb.mix(col_, (0.5, 0.42, 0.34), nb.math("MULTIPLY", nb_map(nb, nb.noise(1.5, 3, 0.5).outputs["Fac"], 0.5, 0.7), 0.35))   # tan patches
    col_ = nb.mix(col_, (0.27, 0.22, 0.24), nb.math("MULTIPLY", edge, 0.7))                 # darker rear margins / coxal rims
    low = nb_map(nb, Zc, ZC + 0.02, ZC - 0.12)
    col_ = nb.mix(col_, (0.72, 0.62, 0.58), nb.math("MULTIPLY", low, 0.5))                  # paler toward the edges below
    gran = nb_map(nb, nb.voronoi(140.0, "F1").outputs["Distance"], 0.05, 0.25, 1.0, 0.0)   # fine granulation
    col_ = nb.mix(col_, (0.36, 0.32, 0.34), nb.math("MULTIPLY", gran, 0.35))
    silt = nb_map(nb, nb.noise(7.0, 4, 0.6).outputs["Fac"], 0.58, 0.72)                    # a little sediment
    col_ = nb.mix(col_, (0.4, 0.36, 0.3), nb.math("MULTIPLY", silt, 0.4))
    rough = nb.math("ADD", nb_map(nb, mott.outputs["Fac"], 0.3, 0.7, 0.28, 0.42), nb.math("MULTIPLY", silt, 0.25))
    h = nb.math("ADD", nb.math("MULTIPLY", gran, 0.5), nb.math("MULTIPLY", nb.noise(30.0, 6, 0.6).outputs["Fac"], 0.3), clamp=False)
    growth = nb.noise(25.0, 3, 0.5, vec=nb.mapping(scale=(0.3, 8, 0.3)))                    # growth lines across each segment
    h = nb.math("ADD", h, nb.math("MULTIPLY", growth.outputs["Fac"], 0.35), clamp=False)
    nb_finish_full(nb, col_, rough, h, bump=0.55, dist=0.008, spec=0.55)
    mat.diffuse_color = (0.55, 0.5, 0.52, 1)


def underside(mat):
    nb = NB(mat)
    m = nb.noise(8.0, 5, 0.6)
    col_ = nb.ramp(m.outputs["Fac"], [(0.3, (0.7, 0.58, 0.54)), (0.7, (0.84, 0.74, 0.68))]).outputs[0]   # cream-pink
    rid = nb.noise(20.0, 3, 0.5, vec=nb.mapping(scale=(0.3, 6, 0.3)))
    col_ = nb.mix(col_, (0.6, 0.48, 0.46), nb.math("MULTIPLY", nb_map(nb, rid.outputs["Fac"], 0.5, 0.65), 0.5))
    rough = nb_map(nb, m.outputs["Fac"], 0.3, 0.7, 0.3, 0.45)
    h = nb.math("ADD", nb.math("MULTIPLY", rid.outputs["Fac"], 0.5), nb.math("MULTIPLY", nb.noise(40.0, 5, 0.6).outputs["Fac"], 0.3), clamp=False)
    nb_finish_full(nb, col_, rough, h, bump=0.35, dist=0.006, spec=0.5)
    mat.diffuse_color = (0.78, 0.66, 0.62, 1)


def legs(mat):
    nb = NB(mat)
    m = nb.noise(10.0, 5, 0.6)
    col_ = nb.ramp(m.outputs["Fac"], [(0.3, (0.58, 0.5, 0.5)), (0.7, (0.74, 0.66, 0.63))]).outputs[0]
    rings = nb.noise(60.0, 2, 0.5, vec=nb.mapping(scale=(0.2, 0.2, 6)))
    col_ = nb.mix(col_, (0.42, 0.34, 0.33), nb.math("MULTIPLY", nb_map(nb, rings.outputs["Fac"], 0.55, 0.7), 0.4))
    nb_finish_full(nb, col_, 0.35, m.outputs["Fac"], bump=0.25, dist=0.004, spec=0.55)
    mat.diffuse_color = (0.66, 0.58, 0.56, 1)


def compound_eye(mat):
    nb = NB(mat)
    fac = nb.voronoi(320.0, "DISTANCE_TO_EDGE")
    facet = nb_map(nb, fac.outputs["Distance"], 0.0, 0.05)
    shine = nb.noise(5.0, 3, 0.5)
    base = nb.ramp(shine.outputs["Fac"], [(0.3, (0.012, 0.012, 0.015)), (0.7, (0.05, 0.045, 0.05))]).outputs[0]
    c = nb.mix((0.0, 0.0, 0.0), base, facet)
    glint = nb.mix((0, 0, 0), (0.03, 0.04, 0.035), nb.math("MULTIPLY", facet, nb_map(nb, shine.outputs["Fac"], 0.5, 0.75)))   # eyeshine
    nb_finish_full(nb, c, 0.06, facet, bump=0.3, dist=0.0015, emit=glint, emit_strength=1.0, spec=0.85)
    mat.diffuse_color = (0.03, 0.03, 0.035, 1)


carapace(M_back); underside(M_belly); legs(M_leg); compound_eye(M_eye)
simple_shader(M_spine, (0.5, 0.42, 0.33), 0.3, noise_scale=40, var=0.4, bump=0.2)
for m_ in bpy.data.materials:
    if m_.name.startswith("M_IsR_"): m_.use_fake_user = True
IS_INFO = {"tris": sum(len(p.vertices) - 2 for p in body.data.polygons), "bones": len(rig.data.bones),
           "unweighted": sum(1 for v in body.data.vertices if not v.groups), "mats": [m.name for m in body.data.materials],
           "dims": tuple(round(d, 2) for d in body.dimensions)}
print("IS_INFO", IS_INFO)


def bake_and_export(size=4096):
    """UV-unwrap, bake BaseColor / Normal / Roughness / Emissive in the rest pose, swap to M_GiantIsopod, export SK_GiantIsopod.fbx."""
    import os
    uv_prep(["SK_GiantIsopod_Body"])
    o = bpy.data.objects["SK_GiantIsopod_Body"]; rig.data.pose_position = "REST"
    scn = bpy.context.scene; scn.render.engine = "CYCLES"; scn.cycles.device = "CPU"; scn.cycles.samples = 4
    scn.render.bake.margin = 8; scn.render.bake.use_clear = True
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    out_dir = os.path.join(OUT_DIR, "Textures"); os.makedirs(out_dir, exist_ok=True)
    passes = [("BaseColor", "DIFFUSE", "sRGB"), ("Normal", "NORMAL", "Non-Color"), ("Roughness", "ROUGHNESS", "Non-Color"), ("Emissive", "EMIT", "sRGB")]
    imgs = {l: bpy.data.images.new(f"T_GiantIsopod_{l}", size, size, alpha=False) for l, _, _ in passes}
    for l, _, cs in passes: imgs[l].colorspace_settings.name = cs
    nodes = []
    for s in o.material_slots:
        n = s.material.node_tree.nodes.new("ShaderNodeTexImage"); n.name = "_bake"; s.material.node_tree.nodes.active = n; nodes.append(n)
    for l, bt, _ in passes:
        for n in nodes: n.image = imgs[l]; n.id_data.nodes.active = n
        kw = dict(pass_filter={"COLOR"}) if bt == "DIFFUSE" else (dict(normal_space="TANGENT") if bt == "NORMAL" else {})
        bpy.ops.object.bake(type=bt, **kw)
        p = os.path.join(out_dir, f"T_GiantIsopod_{l}.png"); imgs[l].filepath_raw = p; imgs[l].file_format = "PNG"; imgs[l].save(); print("BAKED", p, flush=True)
    for n in nodes: n.id_data.nodes.remove(n)
    rig.data.pose_position = "POSE"
    return finalize(["SK_GiantIsopod_Body"])
