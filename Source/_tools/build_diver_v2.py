# Diver v2 (2026-11-09): technical diver rebuilt on the existing Diver_Rig (UE mannequin bone names, T-pose).
# Drysuit body (voxel-remeshed union of anatomy primitives, bone-heat weights) + integrated gear:
# full-face mask + hood + headlamp, steel tank, backplate/wing/harness, hoses, gauge, computer, knife, pockets, knee pads, fins.
# Faces -Y. exec after mk.py, rig.py, horror.py, horror2.py
random.seed(5)
rig = bpy.data.objects["Diver_Rig"]; col = bpy.data.collections["Diver"]
RIG_LOC = rig.location.copy(); rig.location = (0, 0, 0)
if rig.animation_data: rig.animation_data.action = None
for pb in rig.pose.bones: pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
old = bpy.data.objects.get("SK_Diver_Body")
if old: _om = old.data; bpy.data.objects.remove(old); bpy.data.meshes.remove(_om)
bpy.context.view_layer.update()


def _m(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)
M_suit, M_strap, M_metal, M_tank = _m("M_DvX_Suit"), _m("M_DvX_Strap"), _m("M_DvX_Metal"), _m("M_DvX_Tank")
M_rubber, M_visor, M_fin, M_lamp = _m("M_DvX_Rubber"), _m("M_DvX_Visor"), _m("M_DvX_Fin"), _m("M_DvX_Lamp")
M_screen, M_orange, M_wing = _m("M_DvX_Screen"), _m("M_DvX_Orange"), _m("M_DvX_Wing")


def orient(n):
    return n.to_track_quat("Z", "Y").to_matrix().to_4x4()


def add_bm(dst, src):
    tmp = bpy.data.meshes.new("_t"); src.to_mesh(tmp); src.free(); dst.from_mesh(tmp); bpy.data.meshes.remove(tmp)


def prof_tube(pts_r, sides=20):
    """pts_r: list of (Vector, radius). Capped tube."""
    pts = [p for p, _ in pts_r]; rs = [r for _, r in pts_r]
    return tube(pts, lambda s: rs[min(len(rs) - 1, int(round(s * (len(rs) - 1))))], up=(0, 0, 1), sides=sides)


def smooth_chain(keys, n=6):
    """keys: [(Vector, r)] -> catmull-resampled (Vector, r)."""
    P = catmull([k[0] for k in keys], n)
    R = [k[1] for k in keys]; out = []
    for i, p in enumerate(P):
        u = i / (len(P) - 1) * (len(R) - 1); j = min(int(u), len(R) - 2); t = u - j
        out.append((p, R[j] + (R[j + 1] - R[j]) * smoothstep(0, 1, t)))
    return out


# ---------------- anatomy primitives (unioned by voxel remesh) ----------------
TORSO = [(0.84, 0, 0, 0), (0.85, 0.07, 0.06, 0.0), (0.88, 0.14, 0.095, 0.005), (0.95, 0.172, 0.11, 0.012), (1.02, 0.165, 0.103, 0.005),
         (1.1, 0.148, 0.098, -0.002), (1.2, 0.155, 0.105, -0.008), (1.3, 0.172, 0.115, -0.012), (1.38, 0.185, 0.112, -0.008),
         (1.43, 0.18, 0.095, 0.0), (1.47, 0.11, 0.075, 0.005), (1.5, 0.06, 0.055, 0.005), (1.51, 0, 0, 0.005)]
def torso_at(z):
    for a, b in zip(TORSO, TORSO[1:]):
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0]); return [a[i] + (b[i] - a[i]) * t for i in range(4)]
    return list(TORSO[-1])
parts = bmesh.new()
tor = loft_fn(smooth_stations([(z, hx, hy, -yc) for z, hx, hy, yc in TORSO], 40), 40, lambda y, a, x, z: 1 + 0.06 * abs(math.sin(2 * a)))
add_bm(parts, xf(tor, RX(90)))
add_bm(parts, prof_tube([(Vector((0, 0.005, 1.44)), 0.058), (Vector((0, 0.0, 1.6)), 0.056)], 16))
add_bm(parts, uvsphere(1.0, T(0, 0.008, 1.675) @ Matrix.Diagonal((0.09, 0.104, 0.118, 1)), 24, 16))
for sx in (-1, 1):
    add_bm(parts, uvsphere(0.072, T(sx * 0.165, 0.0, 1.425), 16, 10))
    arm = [(Vector((sx * x, 0, 1.43 + (0.004 if 0.2 < x < 0.4 else 0))), r) for x, r in
           [(0.12, 0.07), (0.2, 0.062), (0.3, 0.054), (0.4, 0.047), (0.45, 0.043), (0.5, 0.047), (0.56, 0.045), (0.64, 0.036), (0.69, 0.034)]]
    add_bm(parts, prof_tube(smooth_chain(arm, 4), 18))
    palm = loft_fn([(x, hy, hz, 0) for x, hy, hz in [(0.68, 0.0, 0.0), (0.685, 0.03, 0.02), (0.72, 0.043, 0.022), (0.77, 0.046, 0.019), (0.795, 0.04, 0.016), (0.8, 0, 0)]], 16)
    add_bm(parts, xf(palm, T(0, 0, 1.425) @ Matrix(((0, sx, 0, 0), (sx, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))))
    for yo, L in ((-0.014, 0.085), (0.02, 0.078)):                        # three-finger (lobster) drysuit mitt
        add_bm(parts, prof_tube(smooth_chain([(Vector((sx * 0.775, yo, 1.428)), 0.0175), (Vector((sx * (0.775 + L * 0.6), yo, 1.424)), 0.016),
                                               (Vector((sx * (0.775 + L), yo, 1.412)), 0.014)], 4), 12))
        add_bm(parts, uvsphere(0.014, T(sx * (0.775 + L), yo, 1.412), 10, 6))
    add_bm(parts, prof_tube(smooth_chain([(Vector((sx * 0.715, -0.03, 1.425)), 0.016), (Vector((sx * 0.75, -0.06, 1.42)), 0.014), (Vector((sx * 0.785, -0.075, 1.414)), 0.012)], 4), 10))
    add_bm(parts, uvsphere(0.09, T(sx * 0.085, 0.045, 0.9), 16, 10))
    leg = [(Vector((sx * 0.095, 0, 0.96)), 0.095), (Vector((sx * 0.1, -0.008, 0.82)), 0.086), (Vector((sx * 0.105, -0.008, 0.68)), 0.072),
           (Vector((sx * 0.11, 0, 0.56)), 0.058), (Vector((sx * 0.11, 0, 0.52)), 0.056), (Vector((sx * 0.112, 0.012, 0.43)), 0.058),
           (Vector((sx * 0.116, 0.006, 0.33)), 0.05), (Vector((sx * 0.119, 0, 0.2)), 0.039), (Vector((sx * 0.12, 0, 0.11)), 0.037)]
    add_bm(parts, prof_tube(smooth_chain(leg, 4), 18))
    add_bm(parts, uvsphere(0.046, T(sx * 0.12, 0.0, 0.1), 12, 8))
    boot = loft_fn(smooth_stations([(0.065, 0, 0, 0.06), (0.05, 0.042, 0.05, 0.06), (0.0, 0.047, 0.062, 0.065), (-0.08, 0.05, 0.045, 0.05),
                                    (-0.17, 0.046, 0.03, 0.035), (-0.2, 0.032, 0.022, 0.03), (-0.212, 0, 0, 0.03)], 20), 18)
    add_bm(parts, xf(boot, T(sx * 0.12, 0, 0)))
me = bpy.data.meshes.new("SK_Diver_Body"); parts.to_mesh(me); parts.free()
body = bpy.data.objects.new("SK_Diver_Body", me); col.objects.link(body)
body.data.materials.append(M_suit)
for mname, kw in (("Remesh", dict(mode="VOXEL", voxel_size=0.0055)), ("Smooth", dict(factor=0.7, iterations=6))):
    md = body.modifiers.new(mname, "REMESH" if mname == "Remesh" else "SMOOTH")
    for k, v in kw.items(): setattr(md, k, v)
dg = bpy.context.evaluated_depsgraph_get()
me2 = bpy.data.meshes.new_from_object(body.evaluated_get(dg)); body.modifiers.clear(); body.data = me2; bpy.data.meshes.remove(me)
target = 18000
dec = body.modifiers.new("Dec", "DECIMATE"); dec.ratio = min(1.0, target / max(1, len(me2.polygons) * 2))
dg = bpy.context.evaluated_depsgraph_get()
me3 = bpy.data.meshes.new_from_object(body.evaluated_get(dg)); body.modifiers.clear(); body.data = me3; bpy.data.meshes.remove(me2)
me3.name = "SK_Diver_Body"; me3.materials.clear(); me3.materials.append(M_suit); me3.shade_smooth()
body.parent = rig; body.matrix_parent_inverse = Matrix.Identity(4); bpy.context.view_layer.update()
auto_weight(body, rig, exclude=("root",))
body.parent = rig; body.matrix_parent_inverse = Matrix.Identity(4); bpy.context.view_layer.update()


def weighted(name, bm, material, bone_list):
    o_ = finish(col, name, bm, material)
    o_.parent = rig; o_.matrix_parent_inverse = Matrix.Identity(4); bpy.context.view_layer.update()
    distance_weights(o_, rig, bone_list, falloff=3.0, top=2)
    return o_
gear = []

# ---------------- head: hood seal, full-face mask, straps, headlamp ----------------
HEAD = ["head"]
C = Vector((0, 0.008, 1.668))
def ell(u, v, grow=0.0):
    return C + Vector(((0.093 + grow) * math.sin(u) * math.cos(v), -(0.104 + grow) * math.cos(u) * math.cos(v), (0.12 + grow) * math.sin(v)))
def shell(u0, u1, v0, v1, grow, nu=28, nv=20):
    bm = bmesh.new(); g = []
    for i in range(nu + 1):
        row = []
        for j in range(nv + 1):
            u = math.radians(u0 + (u1 - u0) * i / nu); v = math.radians(v0 + (v1 - v0) * j / nv)
            row.append(bm.verts.new(ell(u, v, grow)))
        g.append(row)
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]))
    return bm
mask = shell(-78, 78, -62, 68, 0.012); bmesh.ops.solidify(mask, geom=mask.faces[:], thickness=0.007)
gear.append(weighted("dv_mask", mask, M_rubber, HEAD))
visor = shell(-56, 56, -8, 54, 0.019, 24, 14); bmesh.ops.solidify(visor, geom=visor.faces[:], thickness=0.004)
gear.append(weighted("dv_visor", visor, M_visor, HEAD))
rim = bmesh.new()
pts = [ell(math.radians(-56 + 112 * k / 30), math.radians(-8), 0.02) for k in range(31)] + \
      [ell(math.radians(56), math.radians(-8 + 62 * k / 12), 0.02) for k in range(1, 13)] + \
      [ell(math.radians(56 - 112 * k / 30), math.radians(54), 0.02) for k in range(1, 31)] + \
      [ell(math.radians(-56), math.radians(54 - 62 * k / 12), 0.02) for k in range(1, 12)]
add_bm(rim, tube(pts, 0.006, up=(0, 0, 1), sides=8, closed=True))
gear.append(weighted("dv_visor_rim", rim, M_metal, HEAD))
pod = box((0.075, 0.05, 0.05), (0, -0.118, 1.585))
bmesh.ops.bevel(pod, geom=pod.edges[:], offset=0.014, segments=3, affect="EDGES")
add_bm(pod, xf(cyl(0.017, 0.012, 16), T(0, -0.145, 1.585) @ RX(90)))
gear.append(weighted("dv_mask_pod", pod, M_rubber, HEAD))
gear.append(weighted("dv_comms", xf(cyl(0.012, 0.03, 12), T(0.095, -0.06, 1.6) @ RY(90)), M_orange, HEAD))
straps = bmesh.new()
for zc_, tilt in ((1.735, 0.0), (1.66, 0.0), (1.6, -0.02)):
    loop = []
    for k in range(25):                                                   # back half of the head, side to side
        a = math.radians(-28 + 236 * k / 24)
        loop.append(Vector((0.103 * math.cos(a), 0.008 + 0.115 * math.sin(a), zc_ + tilt * math.sin(a))))
    add_bm(straps, strap(loop, (0, 0, 1), 0.022, 0.004))
gear.append(weighted("dv_mask_straps", straps, M_strap, HEAD))
lamp = cyl(0.026, 0.06, 20); xf(lamp, T(0, -0.05, 1.79) @ RX(90))
gear.append(weighted("dv_headlamp", lamp, M_rubber, HEAD))
gear.append(weighted("dv_headlamp_lens", xf(cyl(0.021, 0.006, 20), T(0, -0.081, 1.79) @ RX(90)), M_lamp, HEAD))
gear.append(weighted("dv_neckseal", torus(0.066, 0.012, 24, 8, T(0, 0.004, 1.5)), M_rubber, ["spine_03", "neck_01"]))

# ---------------- back: tank, valve, first stage, backplate, wing, cam bands ----------------
BACK = ["spine_03"]
TC = Vector((0, 0.205, 1.2))
tank = lathe([(0, -0.31), (0.06, -0.305), (0.088, -0.28), (0.09, -0.24), (0.09, 0.24), (0.085, 0.28), (0.06, 0.31), (0.025, 0.325), (0.02, 0.35), (0, 0.35)], 28, T(*TC))
gear.append(weighted("dv_tank", tank, M_tank, BACK))
valve = bmesh.new()
add_bm(valve, cyl(0.022, 0.05, 16, (0, 0, 0), T(*(TC + Vector((0, 0, 0.37))))))
add_bm(valve, cyl(0.03, 0.018, 16, (0, 0, 0), T(*(TC + Vector((0, 0, 0.405))))))
add_bm(valve, cyl(0.018, 0.08, 14, (0, 0, 0), T(*(TC + Vector((0, 0, 0.37)))) @ RY(90)))
for sx in (-1, 1):
    add_bm(valve, cyl(0.028, 0.035, 16, (0, 0, 0), T(*(TC + Vector((sx * 0.06, 0, 0.37)))) @ RY(90)))
gear.append(weighted("dv_valve", valve, M_metal, BACK))
plate_ = box((0.27, 0.006, 0.42), (0, 0.128, 1.24))
bmesh.ops.subdivide_edges(plate_, edges=plate_.edges[:], cuts=4, use_grid_fill=True)
for v in plate_.verts: v.co.y += 0.02 * (v.co.x / 0.135) ** 2
gear.append(weighted("dv_backplate", plate_, M_metal, BACK))
wing = loft_fn(smooth_stations([(0.98, 0, 0, 0), (1.0, 0.16, 0.035, 0), (1.1, 0.21, 0.05, 0), (1.3, 0.22, 0.05, 0), (1.42, 0.17, 0.04, 0), (1.45, 0, 0, 0)], 20), 28,
               lambda y, a, x, z: 1 + 0.05 * math.sin(y * 70) ** 2)
xf(wing, T(0, 0.152, 0) @ RX(90) @ Matrix.Diagonal((1, 1, 1, 1)))
for v in wing.verts: v.co.y = 0.152 + (v.co.y - 0.152) * 1.0
gear.append(weighted("dv_wing", wing, M_wing, BACK))
bands = bmesh.new()
for z in (1.05, 1.3):
    loop = [Vector((0.094 * math.cos(a), TC.y + 0.094 * math.sin(a), z)) for a in [k / 24 * math.tau for k in range(24)]]
    add_bm(bands, strap(loop, (0, 0, 1), 0.04, 0.006, closed=True))
    add_bm(bands, box((0.035, 0.02, 0.05), (0.0, TC.y + 0.1, z)))
gear.append(weighted("dv_cambands", bands, M_strap, BACK))

# ---------------- harness, belt, D-rings, crotch strap ----------------
harn = bmesh.new()
for sx in (-1, 1):
    path = [Vector((sx * 0.07, 0.13, 1.4)), Vector((sx * 0.1, 0.09, 1.5)), Vector((sx * 0.105, 0.0, 1.52)), Vector((sx * 0.105, -0.1, 1.45)),
            Vector((sx * 0.11, -0.128, 1.32)), Vector((sx * 0.115, -0.122, 1.15)), Vector((sx * 0.12, -0.115, 1.03))]
    add_bm(harn, strap(catmull(path, 6), (1, 0, 0), 0.05, 0.006))
belt = []
for k in range(40):
    a = k / 40 * math.tau; t = torso_at(1.0)
    belt.append(Vector((t[1] * 1.08 * math.cos(a), t[3] + t[2] * 1.12 * math.sin(a), 1.0)))
add_bm(harn, strap(belt, (0, 0, 1), 0.05, 0.007, closed=True))
crotch = [Vector((0, -0.118, 1.0)), Vector((0, -0.105, 0.9)), Vector((0, -0.04, 0.85)), Vector((0, 0.06, 0.86)), Vector((0, 0.125, 0.98))]
add_bm(harn, strap(catmull(crotch, 6), (1, 0, 0), 0.04, 0.006))
gear.append(weighted("dv_harness", harn, M_strap, ["spine_03", "spine_02", "spine_01", "pelvis", "clavicle_l", "clavicle_r"]))
hw = bmesh.new()
add_bm(hw, box((0.075, 0.02, 0.05), (0, -0.128, 1.0)))
for sx in (-1, 1):
    add_bm(hw, torus(0.02, 0.004, 16, 6, T(sx * 0.115, -0.135, 1.33) @ RX(90)))
    add_bm(hw, torus(0.02, 0.004, 16, 6, T(sx * 0.17, -0.09, 1.0) @ RX(90) @ RZ(sx * 30)))
gear.append(weighted("dv_hardware", hw, M_metal, ["spine_03", "pelvis"]))

# ---------------- hoses + SPG gauge ----------------
TOP = TC + Vector((0, 0, 0.37))
hoses = bmesh.new()
long_hose = [TOP + Vector((-0.07, 0, 0)), Vector((-0.12, 0.17, 1.6)), Vector((-0.16, 0.06, 1.56)), Vector((-0.14, -0.06, 1.52)), Vector((-0.07, -0.13, 1.56)), Vector((-0.03, -0.13, 1.585))]
add_bm(hoses, tube(catmull(long_hose, 8), 0.0085, up=(0, 0, 1), sides=10))
infl = [TOP + Vector((0.07, 0, 0)), Vector((0.12, 0.16, 1.58)), Vector((0.16, 0.06, 1.53)), Vector((0.15, -0.08, 1.46)), Vector((0.13, -0.135, 1.36)), Vector((0.13, -0.135, 1.3))]
add_bm(hoses, tube(catmull(infl, 8), 0.009, up=(0, 0, 1), sides=10))
gear.append(weighted("dv_hoses", hoses, M_rubber, ["spine_03", "neck_01", "head", "clavicle_l", "clavicle_r"]))
spg = [TOP + Vector((0.07, 0.01, -0.02)), Vector((0.14, 0.2, 1.4)), Vector((0.2, 0.12, 1.15)), Vector((0.19, -0.02, 1.02)), Vector((0.175, -0.08, 0.98))]
spgbm = tube(catmull(spg, 8), 0.0075, up=(0, 0, 1), sides=10)
add_bm(spgbm, cyl(0.035, 0.03, 20, (0, 0, 0), T(0.175, -0.1, 0.96) @ RX(80)))
gear.append(weighted("dv_spg", spgbm, M_rubber, ["spine_03", "spine_02", "spine_01", "pelvis"]))
gear.append(weighted("dv_spg_face", xf(cyl(0.028, 0.004, 20), T(0.175, -0.117, 0.957) @ RX(80)), M_screen, ["pelvis"]))

# ---------------- limbs: computer, knife, pockets, knee pads ----------------
comp = box((0.045, 0.05, 0.016), (0.6, 0, 1.43 + 0.043))
add_bm(comp, torus(1.0, 0.12, 20, 6, T(0.6, 0, 1.43) @ RY(90) @ Matrix.Diagonal((0.043, 0.04, 1, 1))))
gear.append(weighted("dv_computer", comp, M_rubber, ["lowerarm_l"]))
gear.append(weighted("dv_computer_screen", box((0.036, 0.04, 0.003), (0.6, 0, 1.43 + 0.0525)), M_screen, ["lowerarm_l"]))
knife = box((0.035, 0.022, 0.16), (-0.165, 0.0, 0.3)); add_bm(knife, box((0.028, 0.026, 0.06), (-0.165, 0.0, 0.41)))
gear.append(weighted("dv_knife", knife, M_orange, ["calf_r"]))
for sx in (-1, 1):
    pk = box((0.03, 0.15, 0.16), (sx * 0.185, -0.01, 0.73)); bmesh.ops.bevel(pk, geom=pk.edges[:], offset=0.008, segments=2, affect="EDGES")
    gear.append(weighted(f"dv_pocket_{sx}", pk, M_suit, ["thigh_l" if sx > 0 else "thigh_r"]))
    kp = uvsphere(1.0, T(sx * 0.112, -0.05, 0.52) @ Matrix.Diagonal((0.055, 0.022, 0.07, 1)), 16, 10)
    gear.append(weighted(f"dv_kneepad_{sx}", kp, M_orange, ["thigh_l", "calf_l"] if sx > 0 else ["thigh_r", "calf_r"]))

# ---------------- fins ----------------
for sx in (-1, 1):
    s = "l" if sx > 0 else "r"
    pocket = loft_fn(smooth_stations([(0.0, 0.055, 0.066, 0.06), (-0.08, 0.058, 0.052, 0.05), (-0.17, 0.054, 0.037, 0.035), (-0.215, 0.04, 0.028, 0.03), (-0.23, 0, 0, 0.03)], 14), 20)
    bmesh.ops.delete(pocket, geom=[f for f in pocket.faces if f.calc_center_median().z > 0.075 and f.calc_center_median().y > -0.06], context="FACES")
    bmesh.ops.solidify(pocket, geom=pocket.faces[:], thickness=0.006)
    xf(pocket, T(sx * 0.12, 0, 0))
    add_bm(pocket, torus(1.0, 0.1, 20, 6, T(sx * 0.12, 0.03, 0.08) @ Matrix.Diagonal((0.05, 0.06, 0.06, 1))))
    gear.append(weighted(f"dv_finpocket_{s}", pocket, M_rubber, [f"foot_{s}", f"ball_{s}"]))
    blade = bmesh.new(); N = 16; rows = []
    for k in range(N + 1):
        t = k / N; y = -0.19 - 0.44 * t; w = 0.05 + 0.075 * t + 0.02 * t * t; z = 0.03 + 0.02 * t * t
        th = 0.008 * (1 - 0.6 * t)
        row = []
        for xx, zz in ((-w, th * 2.2), (-w * 0.85, th), (0, th * 0.7), (w * 0.85, th), (w, th * 2.2), (w, -th * 2.2), (w * 0.85, -th), (0, -th * 0.7), (-w * 0.85, -th), (-w, -th * 2.2)):
            notch = -0.04 * math.exp(-(xx / 0.03) ** 2) * smoothstep(0.85, 1.0, t)        # split-fin notch at the tip
            row.append(blade.verts.new((sx * 0.12 + xx, y - notch, z + zz)))
        rows.append(row)
    for a_, b_ in zip(rows, rows[1:]):
        for c in range(10): blade.faces.new((a_[c], a_[(c + 1) % 10], b_[(c + 1) % 10], b_[c]))
    blade.faces.new(list(reversed(rows[0]))); blade.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(blade, faces=blade.faces)
    gear.append(weighted(f"dv_finblade_{s}", blade, M_fin, [f"ball_{s}"]))

bpy.ops.object.select_all(action="DESELECT")
for o_ in [body] + gear: o_.select_set(True)
bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
mod = body.modifiers.get("Armature") or body.modifiers.new("Armature", "ARMATURE"); mod.object = rig
rig.location = RIG_LOC


# ---------------- shaders ----------------
def suit_shader(mat):
    nb = NB(mat)
    sep = nb.n("ShaderNodeSeparateXYZ"); nb.L(nb.obj, sep.inputs[0])
    X, Y, Z = sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]
    AX = nb.math("ABSOLUTE", X)
    def band(v, lo, hi, soft=0.004):
        return nb.math("MULTIPLY", nb_map(nb, v, lo - soft, lo), nb_map(nb, v, hi + soft, hi))
    weave = nb.noise(380.0, 2, 0.5, vec=nb.mapping(scale=(1, 1, 3)))
    folds = nb.noise(9.0, 4, 0.6, vec=nb.mapping(scale=(1, 1, 0.35)))
    base = nb.ramp(nb.noise(5.0, 4, 0.6).outputs["Fac"], [(0.3, (0.018, 0.019, 0.022)), (0.7, (0.034, 0.035, 0.04))]).outputs[0]
    col_ = base
    hood = nb.math("MULTIPLY", nb_map(nb, Z, 1.5, 1.53), nb.math("LESS_THAN", AX, 0.13))
    glove = nb_map(nb, AX, 0.655, 0.665)
    cuff = band(AX, 0.655, 0.68)
    boot = nb_map(nb, Z, 0.17, 0.15)
    orange_sh = nb.math("MULTIPLY", nb.math("MULTIPLY", nb_map(nb, Z, 1.33, 1.345), band(AX, 0.1, 0.3)), nb.math("LESS_THAN", Z, 1.5))
    side = nb.math("MULTIPLY", band(nb.math("ABSOLUTE", Y), -0.1, 0.028), nb.math("MULTIPLY", band(Z, 0.95, 1.33), nb.math("GREATER_THAN", AX, 0.12)))
    side = nb.math("MULTIPLY", side, nb.math("LESS_THAN", AX, 0.3))
    orange = nb.math("MAXIMUM", orange_sh, side)
    tape = nb.math("MAXIMUM", band(AX, 0.36, 0.385), nb.math("MULTIPLY", band(Z, 0.3, 0.325), nb.math("LESS_THAN", AX, 0.25)))
    tape = nb.math("MULTIPLY", tape, nb.math("SUBTRACT", 1.0, glove))
    seams = nb.math("MAXIMUM", band(Z, 1.098, 1.104, 0.002), band(AX, 0.298, 0.303, 0.002))
    seams = nb.math("MAXIMUM", seams, band(Z, 0.615, 0.62, 0.002))
    # diagonal front zipper (right shoulder -> left hip)
    zl = nb.math("ABSOLUTE", nb.math("SUBTRACT", nb.math("ADD", nb.math("MULTIPLY", X, -1.35, clamp=False), 1.24, clamp=False), Z, clamp=False), clamp=False)
    zip_ = nb.math("MULTIPLY", nb.math("MULTIPLY", nb_map(nb, zl, 0.012, 0.006), nb.math("LESS_THAN", Y, -0.04)), band(Z, 1.03, 1.44))
    zteeth = nb.math("GREATER_THAN", nb.math("SINE", nb.math("MULTIPLY", Z, 900.0, clamp=False), clamp=False), 0.0)
    wear = nb_map(nb, nb.noise(7.0, 5, 0.6).outputs["Fac"], 0.55, 0.7)
    knees = nb.math("MAXIMUM", nb.math("MULTIPLY", band(Z, 0.45, 0.6), nb.math("LESS_THAN", Y, -0.03)), nb.math("MULTIPLY", band(AX, 0.4, 0.5), nb.math("GREATER_THAN", Z, 1.43)))
    salt = nb.math("MULTIPLY", nb_map(nb, nb.noise(3.0, 6, 0.65).outputs["Fac"], 0.6, 0.72), 0.35)
    col_ = nb.mix(col_, (0.85, 0.32, 0.03), orange)
    col_ = nb.mix(col_, (0.55, 0.57, 0.58), tape)
    col_ = nb.mix(col_, (0.012, 0.012, 0.013), hood)
    col_ = nb.mix(col_, (0.015, 0.014, 0.014), glove)
    col_ = nb.mix(col_, (0.06, 0.06, 0.065), cuff)
    col_ = nb.mix(col_, (0.014, 0.013, 0.012), boot)
    col_ = nb.mix(col_, (0.005, 0.005, 0.006), seams)
    col_ = nb.mix(col_, nb.mix((0.05, 0.05, 0.055), (0.35, 0.35, 0.36), zteeth), zip_)
    col_ = nb.mix(col_, (0.12, 0.115, 0.11), nb.math("MULTIPLY", nb.math("MULTIPLY", wear, knees), 0.6))
    col_ = nb.mix(col_, (0.3, 0.3, 0.28), salt)
    rough = nb.mix((0.62, 0.62, 0.62), (0.35, 0.35, 0.35), nb.math("MAXIMUM", nb.math("MAXIMUM", hood, glove), boot))
    rough = nb.mix(rough, (0.25, 0.25, 0.25), tape)
    rough = nb.mix(rough, (0.3, 0.3, 0.3), zip_)
    grip = nb_map(nb, nb.voronoi(160.0, "F1").outputs["Distance"], 0.1, 0.25, 1.0, 0.0)
    tread = nb.math("GREATER_THAN", nb.math("SINE", nb.math("MULTIPLY", Y, 250.0, clamp=False), clamp=False), 0.3)
    h = nb.math("ADD", nb.math("MULTIPLY", weave.outputs["Fac"], 0.25), nb.math("MULTIPLY", folds.outputs["Fac"], 1.2), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", nb.math("MULTIPLY", grip, glove), 0.6), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", nb.math("MULTIPLY", tread, boot), 0.5), clamp=False)
    h = nb.math("SUBTRACT", h, nb.math("MULTIPLY", seams, 0.8), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", nb.math("MULTIPLY", zteeth, zip_), 0.6), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", tape, 0.3), clamp=False)
    emit = nb.mix((0, 0, 0), (0.12, 0.12, 0.12), tape)
    nb_finish_full(nb, col_, rough, h, bump=0.35, dist=0.004, emit=emit, emit_strength=1.0, spec=0.45)
    mat.diffuse_color = (0.03, 0.03, 0.035, 1)


def tank_shader(mat):
    nb = NB(mat)
    sep = nb.n("ShaderNodeSeparateXYZ"); nb.L(nb.obj, sep.inputs[0]); Z = sep.outputs["Z"]
    c = nb.ramp(nb.noise(8.0, 4, 0.6).outputs["Fac"], [(0.3, (0.62, 0.38, 0.03)), (0.7, (0.75, 0.48, 0.05))]).outputs[0]
    stripe = nb.math("MULTIPLY", nb_map(nb, Z, 1.42, 1.43), nb_map(nb, Z, 1.5, 1.49))
    c = nb.mix(c, (0.85, 0.85, 0.82), stripe)
    sc = nb.noise(40.0, 3, 0.5, distortion=2.0, vec=nb.mapping(scale=(3, 3, 0.3)))
    scratch = nb.ramp(sc.outputs["Fac"], [(0.49, (0, 0, 0)), (0.5, (1, 1, 1)), (0.51, (0, 0, 0))]).outputs[0]
    c = nb.mix(c, (0.3, 0.3, 0.3), nb.math("MULTIPLY", scratch, 0.7))
    rust = nb_map(nb, nb.noise(6.0, 5, 0.6).outputs["Fac"], 0.62, 0.72)
    c = nb.mix(c, (0.18, 0.06, 0.02), nb.math("MULTIPLY", rust, nb_map(nb, Z, 1.0, 0.9)))
    nb_finish_full(nb, c, 0.32, scratch, bump=0.2, dist=0.003, spec=0.6)
    mat.diffuse_color = (0.7, 0.45, 0.05, 1)


def fin_shader(mat):
    nb = NB(mat)
    sep = nb.n("ShaderNodeSeparateXYZ"); nb.L(nb.obj, sep.inputs[0]); Y = sep.outputs["Y"]
    tip = nb_map(nb, Y, -0.5, -0.52)
    c = nb.mix((0.015, 0.015, 0.016), (0.9, 0.55, 0.02), tip)
    ribs = nb.math("GREATER_THAN", nb.math("SINE", nb.math("MULTIPLY", Y, 120.0, clamp=False), clamp=False), 0.6)
    nb_finish_full(nb, c, 0.4, ribs, bump=0.15, dist=0.003, spec=0.5)
    mat.diffuse_color = (0.02, 0.02, 0.02, 1)


suit_shader(M_suit); tank_shader(M_tank); fin_shader(M_fin)
simple_shader(M_strap, (0.012, 0.012, 0.013), 0.7, noise_scale=300, var=0.4, bump=0.3)
simple_shader(M_metal, (0.42, 0.43, 0.45), 0.25, noise_scale=60, var=0.3, bump=0.1, veins=(30.0, (0.2, 0.2, 0.21), 0.5))
simple_shader(M_rubber, (0.018, 0.018, 0.02), 0.45, noise_scale=80, var=0.3, bump=0.15)
simple_shader(M_visor, (0.008, 0.01, 0.014), 0.03, noise_scale=10, var=0.6, bump=0.02)
simple_shader(M_lamp, (0.9, 0.9, 0.85), 0.05, var=0.05, emit=(1.0, 0.95, 0.85), emit_strength=1.0)
simple_shader(M_screen, (0.02, 0.15, 0.18), 0.05, noise_scale=200, var=0.3, emit=(0.1, 0.6, 0.7), emit_strength=0.6)
simple_shader(M_orange, (0.85, 0.32, 0.03), 0.45, noise_scale=40, var=0.25, bump=0.2)
simple_shader(M_wing, (0.02, 0.02, 0.022), 0.6, noise_scale=250, var=0.35, bump=0.3)
for m_ in bpy.data.materials:
    if m_.name.startswith("M_DvX_"): m_.use_fake_user = True
DV_INFO = {"tris": sum(len(p.vertices) - 2 for p in body.data.polygons), "unweighted": sum(1 for v in body.data.vertices if not v.groups),
           "mats": [m.name for m in body.data.materials], "dims": tuple(round(d, 3) for d in body.dimensions)}
print("DV_INFO", DV_INFO)
