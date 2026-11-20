# Deep-sea eel v3 (2026-11-20): rebuilt to the Kraken's quality bar (replaces v2 = a thin black whip whose details vanished).
#  - model: 1.5x thicker gulper-eel body with sculpted tumours, claw gashes and eye sockets; Kraken-style hooked bony
#    spines down the back, a row of glowing photophores along each flank, 2 big amber eyes + 7 small extra eyes,
#    bigger fangs, pleated jaw pouch, torn fin fringes, glowing eyeball lure at the tail;
#  - skin: Kraken palette (purple-black back, reddish belly, blotches, chromatophores, veins, scars, raw flesh in wounds);
#  - rig: 16 spine bones (was 12) for a smoother wave; EEL_Idle / EEL_Swim / EEL_Bite re-authored with layered motion
#    (head stabilised against the body wave, jaw breathing, coil -> strike -> snap).  EEL_Search / EEL_Hit come from
#    build_monster_anims_extra.py (run it after this file).
# Faces -Y, rig root at the back of the head.  exec after mk.py, rig.py, horror.py, horror2.py, monsters_v2_pipeline.py.
from mathutils import Quaternion
from mathutils.bvhtree import BVHTree
random.seed(29)
S = 1.25
RIG_LOC = (-6.5, -4.5, 1.0)
col = get_col("DeepSeaEel", clear=True)
for nm in ("DeepSeaEel_Rig", "SK_DeepSeaEel_Body"):
    o = bpy.data.objects.get(nm)
    if o: bpy.data.objects.remove(o, do_unlink=True)
for a_ in [a_ for a_ in bpy.data.actions if a_.name.startswith("EEL_")]:
    bpy.data.actions.remove(a_)


def _m(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)
M_skin, M_pouch, M_flesh, M_throat = _m("M_EelX_Skin"), _m("M_EelX_Pouch"), _m("M_EelX_Flesh"), _m("M_EelX_Throat")
M_teeth, M_fin, M_hook, M_photo = _m("M_EelX_Teeth"), _m("M_EelX_Fin"), _m("M_EelX_Hook"), _m("M_EelX_Photo")
M_eye, M_iris, M_pupil = _m("M_EelX_Eye"), _m("M_EelX_Iris"), _m("M_EelX_Pupil")
M_lflesh, M_leye, M_liris = _m("M_EelX_LureFlesh"), _m("M_EelX_LureEye"), _m("M_EelX_LureIris")


def orient(n):
    return Vector(n).to_track_quat("Z", "Y").to_matrix().to_4x4()


# (y, half-width, half-height, centre z) in body units (x S): ~1.5x thicker than v2
KEYS = [(-0.62, 0, 0, 0.004), (-0.605, 0.016, 0.014, 0.004), (-0.56, 0.034, 0.026, 0.007), (-0.42, 0.056, 0.038, 0.011),
        (-0.22, 0.084, 0.055, 0.014), (-0.02, 0.125, 0.095, 0.012), (0.12, 0.16, 0.145, -0.008), (0.3, 0.155, 0.16, -0.015),
        (0.6, 0.125, 0.14, 0.0), (1.0, 0.09, 0.11, 0.0), (1.5, 0.062, 0.085, 0.0), (2.0, 0.04, 0.06, 0.0),
        (2.5, 0.024, 0.036, 0.0), (2.9, 0.012, 0.018, 0.0), (3.04, 0.005, 0.006, 0.0), (3.07, 0, 0, 0)]
DEPTH = [(-0.6, 0.0), (-0.5, 0.05), (-0.35, 0.13), (-0.18, 0.21), (-0.02, 0.19), (0.08, 0.07)]
PAL = -0.006 * S


def prof(keys, y):
    for a, b in zip(keys, keys[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0]); return [a[i] + (b[i] - a[i]) * t for i in range(len(a))]
    return list(keys[0]) if y < keys[0][0] else list(keys[-1])
p_at = lambda y: prof(KEYS, y)


def radial(y, a, x, z):
    yu = y / S; s = 1.0
    if 0.0 < yu < 0.7: s += 0.03 * (0.5 + 0.5 * math.sin(yu * 95)) ** 3 * (1 - yu / 0.7)        # loose neck folds
    if 0.1 < yu < 2.8: s += 0.04 * math.exp(-((a - math.pi / 2) / 0.16) ** 2)                  # spine ridge
    if 0.4 < yu: s *= 1.0 - 0.16 * abs(math.cos(a)) * min(1.0, (yu - 0.4) / 1.0)                # flatter tail
    if 0.2 < yu < 2.9: s += 0.012 * math.sin(yu * 34) ** 2 * max(0.0, math.cos(a)) ** 2         # muscle bands (myomeres) on the flanks
    return s


# ---------------- armature: root, head, jaw, 16 spine bones ----------------
NSP = 16
Y0, Y1 = 0.12, 3.07 * S
SPY = [Y0 + (Y1 - Y0) * i / NSP for i in range(NSP + 1)]
bones = [("eel_root", (0, 0, 0), (0, 0.38, 0), None, False),
         ("eel_head", (0, 0.12, 0), (0, -0.62 * S, 0), "eel_root", True),
         ("eel_jaw", (0, 0.06, -0.05), (0, -0.55 * S, -0.1), "eel_head", True)]
SPINE = []
for i in range(NSP):
    nm = f"eel_spine_{i + 1:02d}"
    bones.append((nm, (0, SPY[i], 0), (0, SPY[i + 1], 0), SPINE[-1] if SPINE else "eel_root", True)); SPINE.append(nm)
rig = make_armature(col, "DeepSeaEel_Rig", bones, (0, 0, 0))

# ---------------- body + sculpt ----------------
ST = [(y * S, hx * S, hz * S, zc * S) for y, hx, hz, zc in smooth_stations(KEYS, 160)]
body = finish(col, "SK_DeepSeaEel_Body", loft_fn(ST, 40, radial), M_skin)
subdivide_displace(body, levels=1, lumps=0.004 * S, lump_scale=6, wrinkle=0.0008 * S, wrinkle_scale=90, seed=5)
me = body.data
for v in me.vertices:                                                       # flat palate under the upper jaw
    if v.co.y < 0.06 * S and v.co.z < PAL:
        w = smoothstep(0.0, 1.0, (0.06 * S - v.co.y) / (0.08 * S)); v.co.z += (PAL - v.co.z) * w
me.update()
bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [p.vertices[:] for p in me.polygons])
def hit(origin, target):
    o_ = Vector(origin); d_ = (Vector(target) - o_).normalized()
    loc, nor, _, _ = bvh.ray_cast(o_, d_)
    return (loc.copy(), nor.normalized()) if loc else (None, None)
def at_angle(yu, ang):
    """Surface point / normal at body station yu (body units) and angle (deg, 90 = top, 0 = +X side)."""
    p = p_at(yu); a = math.radians(ang); c = Vector((0, yu * S, p[3] * S))
    return hit(c + Vector((math.cos(a), 0, math.sin(a))) * 1.0, c)

SCULPT, EYES, MASK = [], [], {"flesh": [], "wound": []}
for sx in (-1, 1):                                                          # main eye sockets + brow ridges
    p, n = at_angle(-0.47, 90 - sx * 55)
    if p is None: continue
    SCULPT += [(p, Vector((0.032, 0.04, 0.03)) * S, -0.016 * S), (p + Vector((0, 0.01, 0.022)) * S, Vector((0.03, 0.035, 0.012)) * S, 0.01 * S)]
    EYES.append((p - n * 0.006 * S, 0.022 * S, (n + Vector((0, -0.6, 0.2))).normalized(), True, n)); MASK["flesh"].append((p, 0.03 * S))
for yu, ang in [(-0.38, 70), (-0.33, 112), (-0.28, 84), (-0.22, 100), (-0.2, 62), (-0.14, 118), (-0.1, 78)]:   # small extra eyes
    p, n = at_angle(yu, ang)
    if p is None: continue
    r = random.uniform(0.008, 0.013) * S
    SCULPT.append((p, Vector((r, r, r)) * 1.5, -r * 0.8))
    look = (n + Vector((random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.3), random.uniform(-0.3, 0.3)))).normalized()
    EYES.append((p - n * r * 0.3, r, look, False, n)); MASK["flesh"].append((p, r * 1.7))
for k in range(16):                                                          # tumour lumps
    yu = random.uniform(0.25, 2.3); ang = random.uniform(20, 160)
    p, n = at_angle(yu, ang)
    if p is None: continue
    r = random.uniform(0.014, 0.034) * S * (1.2 - 0.25 * yu / 2.3)
    SCULPT.append((p, Vector((r, r * 1.4, r)), r * 0.7))
for gy, gang in ((0.75, 40), (1.05, 150), (1.45, 30)):                         # claw gashes (3 parallel cuts each)
    for j in range(3):
        for q in range(5):
            p, n = at_angle(gy + j * 0.035 + q * 0.025, gang + (q - 2) * 9)
            if p is None: continue
            w = 0.006 * S * (1 - abs(q - 2) / 3)
            SCULPT.append((p, Vector((0.01, w * 1.2, 0.012)) * 1.0, -0.006 * S)); MASK["wound"].append((p, Vector((0.012, w * 1.8, 0.016))))
for v in me.vertices:
    dd = 0.0
    for c, rad, amt in SCULPT:
        q = v.co - c; e = (q.x / rad.x) ** 2 + (q.y / rad.y) ** 2 + (q.z / rad.z) ** 2
        if e < 9: dd += amt * math.exp(-e)
    if dd: v.co += v.normal * dd
me.update()
me.materials.append(M_flesh)
for f in me.polygons:
    if f.center.y < 0.04 * S and abs(f.center.z - PAL) < 0.002 * S and f.normal.z < -0.5: f.material_index = 1

extras = []
def add(name, bm, material):
    o = finish(col, name, bm, material); extras.append(o); return o
SC = Matrix.Scale(S, 4)
for sgn, nm, y0, y1 in ((1, "dorsal", 1.3, 2.95), (-1, "anal", 0.6, 2.95)):         # torn fin fringes
    N = 40
    base, tips = [], []
    for i in range(N):
        t = i / (N - 1); y = y0 + (y1 - y0) * t; p = p_at(y)
        h = 0.006 + 0.034 * math.sin(math.pi * min(1.0, t * 1.15)) ** 0.6
        base.append((y, p[3] + sgn * p[2] * 0.97)); tips.append((y + 0.025, p[3] + sgn * (p[2] + h)))
    mb, rb = ray_fin(base, tips, 0.005, SC, rows=3, ray_every=2, scallop=0.16, tears=((11, 0.55), (27, 0.4)) if sgn > 0 else ((9, 0.45), (30, 0.5)), ray_r=0.0022)
    add(f"ex_{nm}", mb, M_fin); add(f"ex_{nm}_rays", rb, M_fin)
bvh2 = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [p.vertices[:] for p in me.polygons])
for k in range(26):                                                           # hooked bony spines down the back
    yu = 0.12 + k * 0.05
    if yu > 1.35: break
    for off in ((0.0,) if k % 2 else (-0.35, 0.35)):
        a = math.pi / 2 + off; pr = p_at(yu); c = Vector((0, yu * S, pr[3] * S))
        loc, n, _, _ = bvh2.ray_cast(c + Vector((math.cos(a), 0, math.sin(a))), -Vector((math.cos(a), 0, math.sin(a))))
        if loc is None: continue
        env = math.sin(math.pi * min(1.0, (yu - 0.05) / 1.4))
        L = (0.025 + 0.06 * env) * S * random.uniform(0.75, 1.2) * (1.0 if off == 0 else 0.6)
        add(f"ex_spine_{k}_{off}", xf(needle((0.006 + 0.006 * env) * S, L, (0, 0, 0), 0, 0, 0.35, segs=7),
                                      T(*(loc - n * 0.004)) @ orient((n + Vector((0, 0.9, 0))).normalized())), M_hook)
        MASK["flesh"].append((loc.copy(), (0.012 + 0.008 * env) * S))
for sx in (-1, 1):                                                            # glowing photophores along the lower flanks
    for k in range(22):
        yu = 0.2 + k * 0.11
        if yu > 2.6: break
        p, n = at_angle(yu, -25 if sx > 0 else 205)
        if p is None: continue
        r = (0.014 - 0.004 * yu / 2.6) * S
        add(f"ex_photo_{sx}_{k}", uvsphere(r, T(*(p - n * r * 0.15)) @ orient(n) @ Matrix.Diagonal((1, 1.3, 0.7, 1)), 12, 8), M_photo)
# tail lure: swollen bulb studded with glowing eyeballs + trailing filaments
tip = Vector((0, 3.07 * S, 0))
bulb = bmesh.new(); bmesh.ops.create_uvsphere(bulb, u_segments=20, v_segments=12, radius=1.0)
for v in bulb.verts:
    v.co = Vector((v.co.x * 0.034, v.co.y * 0.055, v.co.z * 0.034)) * S
    v.co += v.co.normalized() * 0.003 * noise.noise(v.co * 60)
xf(bulb, T(0, 3.12 * S, 0)); add("ex_bulb", bulb, M_lflesh)
add("ex_bulb_stalk", tube([tip - Vector((0, 0.06, 0)), tip, Vector((0, 3.08 * S, 0))], lambda s: 0.008, up=(1, 0, 0), sides=8), M_lflesh)
for k, (dx, dy, dz, r) in enumerate([(1, -0.2, 0.3, 0.02), (-1, 0.1, 0.4, 0.017), (0.2, 0.3, -1, 0.019), (-0.5, 0.6, -0.6, 0.014), (0.6, 0.7, 0.7, 0.013)]):
    d = Vector((dx, dy, dz)).normalized()
    ctr = Vector((0, 3.12 * S, 0)) + Vector((d.x * 0.034, d.y * 0.055, d.z * 0.034)) * S * 0.9
    look = (d + Vector((random.uniform(-0.5, 0.5), random.uniform(-0.3, 0.3), random.uniform(-0.5, 0.5)))).normalized()
    rot = orient(look)
    add(f"ex_leye_{k}", uvsphere(r, T(*ctr), 16, 10), M_leye)
    add(f"ex_liris_{k}", uvsphere(r * 0.6, T(*(ctr + look * r * 0.84)) @ rot @ Matrix.Diagonal((1, 1, 0.32, 1)), 14, 8), M_liris)
    add(f"ex_lpup_{k}", uvsphere(r * 0.28, T(*(ctr + look * r * 1.0)) @ rot @ Matrix.Diagonal((0.55 if k % 2 else 1, 1, 0.3, 1)), 10, 6), M_pupil)
for k in range(5):
    a = k / 5 * math.tau + 0.4
    pts = [Vector((0, 3.17 * S, 0))]
    for i in range(1, 6):
        t = i / 5
        pts.append(Vector((0.025 * math.cos(a) * t + 0.012 * math.sin(i * 1.7 + k), 3.17 * S + 0.16 * t, 0.025 * math.sin(a) * t)))
    add(f"ex_fil_{k}", tube(catmull(pts, 3), lambda s: 0.0032 * (1 - 0.7 * s), up=(1, 0, 0), sides=5), M_lflesh)

bpy.ops.object.select_all(action="DESELECT")
for o in [body] + extras: o.select_set(True)
bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
body.parent = rig; body.matrix_parent_inverse = Matrix.Identity(4); bpy.context.view_layer.update()
body.data.shade_smooth()
distance_weights(body, rig, SPINE, falloff=3.0, top=2)
blend_region(body, "eel_head", lambda c: max(0.0, min(1.0, (0.12 * S - c.y) / (0.15 * S))))

# ---------------- jaws + pleated pouch (rigid to the jaw) ----------------
d_at = lambda y: prof(DEPTH, y)[1]
def rim(y, sx):
    p = p_at(y); return Vector((sx * p[1] * 0.92 * S, y * S, PAL - 0.005 * S))
NY, NT = 44, 44
grid = []; pb = bmesh.new()
for i in range(NY):
    y = -0.585 + (0.08 + 0.585) * i / (NY - 1)
    p = p_at(y); w = p[1] * 0.92; d = d_at(y); bw = max(w, 0.48 * d); zr = PAL / S - 0.005
    row = []
    for j in range(NT):
        th = math.pi * j / (NT - 1); sn = math.sin(th)
        x = math.cos(th) * (w * (1 - sn) + bw * sn); z = -d * sn ** 0.9
        pleat = 1 + 0.05 * math.sin(th * 18 + y * 8) * sn * min(1.0, d / 0.06)
        row.append(pb.verts.new((x * pleat * S, y * S, (zr + z * pleat) * S)))
    grid.append(row)
for i in range(NY - 1):
    for j in range(NT - 1):
        pb.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
bmesh.ops.remove_doubles(pb, verts=pb.verts, dist=1e-6)
for v in pb.verts:
    v.co += Vector((noise.noise(v.co * 25), 0, noise.noise(v.co * 25 + Vector((3, 3, 3))))) * 0.004
bmesh.ops.recalc_face_normals(pb, faces=pb.faces); pb.normal_update()
bmesh.ops.solidify(pb, geom=pb.faces[:], thickness=0.004 * S); pb.normal_update()
inner = pb.copy()
def facing_in(f):
    c = f.calc_center_median(); yu = c.y / S
    axis = Vector((0, c.y, PAL - d_at(yu) * S * 0.5))
    return f.normal.dot(axis - c) > 0
bmesh.ops.delete(pb, geom=[f for f in pb.faces if facing_in(f)], context="FACES")
bmesh.ops.delete(inner, geom=[f for f in inner.faces if not facing_in(f)], context="FACES")
rigid_bm_to_group(body, pb, M_pouch, "eel_jaw")
rigid_bm_to_group(body, inner, M_flesh, "eel_jaw")
for sx in (-1, 1):
    pts = [rim(-0.6 + 0.66 * k / 10, sx) for k in range(11)]
    rigid_bm_to_group(body, tube(catmull(pts, 3), lambda s: (0.0045 + 0.004 * s) * S, up=(0, 0, 1), sides=8), M_skin, "eel_jaw")
rigid_bm_to_group(body, xf(lathe([(0, 0), (0.06 * S, 0.0), (0.065 * S, 0.06 * S), (0.0, 0.09 * S)], 14), T(0, 0.06 * S, PAL - 0.09 * S)), M_throat, "eel_head")
for y in [-0.585 + i * 0.022 for i in range(29)]:                              # fangs on both jaws (bigger than v2)
    p = p_at(y)
    for sx in (-1, 1):
        big = random.random() < 0.18
        L = random.uniform(0.016, 0.034) * S * (1.9 if big else 1.0)
        up = Vector((sx * p[1] * 0.85 * S, y * S, PAL))
        rigid_bm_to_group(body, needle((0.0045 if big else 0.0034) * S, L, up.to_tuple(), 180 + random.uniform(-12, 12), sx * random.uniform(0, 14), -0.25, segs=5), M_teeth, "eel_head")
        lo = rim(y, sx) + Vector((-sx * 0.002 * S, 0, 0.003 * S))
        L2 = random.uniform(0.014, 0.03) * S * (1.8 if random.random() < 0.15 else 1.0)
        rigid_bm_to_group(body, needle(0.0032 * S, L2, lo.to_tuple(), random.uniform(-12, 12), sx * random.uniform(0, 14), 0.25, segs=5), M_teeth, "eel_jaw")
for k, (ctr, r, look, main, n) in enumerate(EYES):                            # Kraken-style eyes: ball, slit iris, pupil, eyelid ring
    rigid_bm_to_group(body, uvsphere(r, T(*ctr), 24 if main else 14, 12 if main else 8), M_eye, "eel_head")
    rot = orient(look)
    rigid_bm_to_group(body, uvsphere(r * 0.66, T(*(ctr + look * r * 0.82)) @ rot @ Matrix.Diagonal((1, 1, 0.3, 1)), 18, 8), M_iris, "eel_head")
    rigid_bm_to_group(body, uvsphere(r * 0.6, T(*(ctr + look * r * 0.9)) @ rot @ Matrix.Diagonal((0.95, 0.2, 0.22, 1) if main else (0.5, 0.5, 0.22, 1)), 14, 6), M_pupil, "eel_head")
    rigid_bm_to_group(body, wrinkle_bm(torus(r * 0.98, r * 0.17, 24 if main else 14, 8, T(*(ctr + n * r * 0.5)) @ orient(n)), r * 0.05, 90, k), M_skin, "eel_head")
mod = body.modifiers.new("Armature", "ARMATURE"); mod.object = rig


def _eprof(co):
    p = p_at(max(-0.619, min(3.069, co.y / S)))
    hx = max(1e-3, p[1] * S); hz = max(1e-3, p[2] * S)
    a = math.atan2((co.z - p[3] * S) / hz, co.x / hx)
    return (math.sin(a), co.y, abs(math.cos(a)))
set_profile_attr(body, "eprof", _eprof)


# ---------------- animation (Euler; spine yaw = local Z, head/jaw pitch = local X, jaw opens +X) ----------------
D = math.radians; TAU = math.tau
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
K6 = 6.0 / NSP                                                                # per-bone scale -> same whole-body curve as a 6-bone chain


def body_wave(f, t, cyc, amp0, amp1, waves, extra=None):
    """Travelling S-wave head -> tail; returns the summed yaw of the first 3 bones (to stabilise the head)."""
    front = 0.0
    for i, bn in enumerate(SPINE):
        u = i / (NSP - 1)
        a = D(amp0 + (amp1 - amp0) * u ** 1.3) * K6 * math.sin(TAU * (cyc * t - waves * u))
        if extra: a += extra(i, u)
        if i < 3: front += a
        key(rig.pose.bones[bn], f, rot=(D(1.2) * K6 * math.sin(TAU * (cyc * t - waves * u) + 1.3), 0, a))
    return front


bpy.context.view_layer.objects.active = rig
new_action(rig, "EEL_Idle")                     # slow drifting S, head scanning, jaw breathing, lure twitch
F = 96
for f in range(F + 1):
    t = f / F
    front = body_wave(f + 1, t, 1, 3, 9, 0.9)
    key(rig.pose.bones["eel_head"], f + 1, rot=(D(3) * math.sin(TAU * t * 2 + 0.7), 0, -front * 0.7 + D(9) * math.sin(TAU * t + 0.4)))
    key(rig.pose.bones["eel_jaw"], f + 1, rot=(D(4) + D(9) * (0.5 + 0.5 * math.sin(TAU * t * 2 - 1.0)) ** 2, 0, 0))
    key(rig.pose.bones["eel_root"], f + 1, rot=(0, 0, 0), loc=(0, 0, 0.03 * math.sin(TAU * t * 2)))
rig.animation_data.action.frame_range = (1, F + 1)

new_action(rig, "EEL_Swim")                     # strong anguilliform wave, amplitude growing to the tail, head kept steady
F = 48
for f in range(F + 1):
    t = f / F
    front = body_wave(f + 1, t, 1, 5, 28, 1.25)
    key(rig.pose.bones["eel_head"], f + 1, rot=(D(2) * math.sin(TAU * t * 2), 0, -front * 0.85))
    key(rig.pose.bones["eel_jaw"], f + 1, rot=(D(5) + D(3) * math.sin(TAU * t * 2), 0, 0))
    key(rig.pose.bones["eel_root"], f + 1, rot=(0, 0, 0), loc=(0, 0, 0))
rig.animation_data.action.frame_range = (1, F + 1)

new_action(rig, "EEL_Bite")                     # coil into an S (1-10), strike ~95 cm (10-16) with the jaw gaping, snap shut (16), settle
F = 36
for f in range(F + 1):
    coil = ease(f / 9) * (1 - ease((f - 10) / 4))
    strike = ease((f - 9) / 6)
    gape = ease((f - 7) / 5) * (1 - ease((f - 15) / 2))
    settle = ease((f - 17) / 18)
    def ex(i, u):
        s_ = D(26) * K6 * coil * math.sin(TAU * (1.4 * u) + 0.4) * (1 - 0.6 * u)                     # S-coil, strongest at the neck
        w_ = D(10) * K6 * u * math.sin(TAU * (f / 12 - 1.1 * u)) * (strike * (1 - settle * 0.6))     # tail thrust during the strike
        return s_ + w_
    front = body_wave(f + 1, f / F, 0, 0, 0, 1.0, ex)
    key(rig.pose.bones["eel_head"], f + 1, rot=(D(-6) * coil + D(10) * gape, 0, -front * 0.6))
    key(rig.pose.bones["eel_jaw"], f + 1, rot=(D(4) + D(70) * gape, 0, 0))
    lunge = 0.22 * coil - 0.95 * strike
    key(rig.pose.bones["eel_root"], f + 1, rot=(0, 0, 0), loc=(0, lunge, 0))
rig.animation_data.action.frame_range = (1, F + 1)
_act = bpy.data.actions["EEL_Swim"]; rig.animation_data.action = _act
if hasattr(rig.animation_data, "action_slot") and len(_act.slots): rig.animation_data.action_slot = _act.slots[0]
rig.location = RIG_LOC


# ---------------- shaders (Kraken palette) ----------------
def eel_skin_v3(mat):
    nb = NB(mat)
    s, y, c = nb_attr(nb, "eprof")
    side = nb_map(nb, s, 0.15, -0.85)                                          # 0 back .. 1 belly
    P = nb_warp(nb, 0.02, 8.0)
    col_ = nb.mix((0.03, 0.01, 0.016), (0.2, 0.09, 0.09), side)
    blot = nb.noise(3.5, 6, 0.6, distortion=0.5)
    col_ = nb.mix(col_, (0.08, 0.012, 0.04), nb.math("MULTIPLY", nb_map(nb, blot.outputs["Fac"], 0.5, 0.66), nb.math("SUBTRACT", 1.0, side)))
    mott = nb.noise(12.0, 6, 0.65)
    col_ = nb.mix(col_, nb.ramp(mott.outputs["Fac"], [(0.3, (0.6, 0.6, 0.6)), (0.7, (1, 1, 1))]).outputs[0], 1.0, "MULTIPLY")
    chrom = nb.voronoi(70.0, "F1")                                             # chromatophores: dark + rusty red dots
    cd = nb_map(nb, chrom.outputs["Distance"], 0.12, 0.28, 1.0, 0.0)
    cr = nb.n("ShaderNodeSeparateColor"); nb.L(chrom.outputs["Color"], cr.inputs[0])
    col_ = nb.mix(col_, (0.005, 0.002, 0.003), nb.math("MULTIPLY", cd, nb.math("GREATER_THAN", cr.outputs[0], 0.45)))
    col_ = nb.mix(col_, (0.24, 0.035, 0.02), nb.math("MULTIPLY", nb.math("MULTIPLY", cd, nb.math("LESS_THAN", cr.outputs[0], 0.2)), 0.8))
    vn = nb.noise(7.0, 4, 0.5, distortion=3.2)
    veins = nb.ramp(vn.outputs["Fac"], [(0.487, (0, 0, 0)), (0.5, (1, 1, 1)), (0.513, (0, 0, 0))]).outputs[0]
    col_ = nb.mix(col_, (0.26, 0.0, 0.04), nb.math("MULTIPLY", veins, nb.math("ADD", 0.25, nb.math("MULTIPLY", side, 0.6))))
    sc_n = nb.noise(3.5, 3, 0.5, distortion=1.4, vec=nb.mapping(scale=(4, 0.6, 4)))
    scars = nb.ramp(sc_n.outputs["Fac"], [(0.496, (0, 0, 0)), (0.5, (1, 1, 1)), (0.504, (0, 0, 0))]).outputs[0]
    scars = nb.math("MULTIPLY", scars, nb_map(nb, nb.noise(1.8, 2).outputs["Fac"], 0.48, 0.58))
    col_ = nb.mix(col_, (0.22, 0.14, 0.13), nb.math("MULTIPLY", scars, 0.5))
    fl = None
    for cc, r in MASK["flesh"]:
        dist = nb.n("ShaderNodeVectorMath", operation="DISTANCE"); nb.L(P, dist.inputs[0]); dist.inputs[1].default_value = tuple(cc)
        m_ = nb_map(nb, dist.outputs["Value"], r * 0.5, r, 1.0, 0.0)
        fl = m_ if fl is None else nb.math("MAXIMUM", fl, m_)
    wd = None
    for cc, rv in MASK["wound"]:
        sub = nb.n("ShaderNodeVectorMath", operation="SUBTRACT"); nb.L(P, sub.inputs[0]); sub.inputs[1].default_value = tuple(cc)
        mul = nb.n("ShaderNodeVectorMath", operation="MULTIPLY"); nb.L(sub.outputs[0], mul.inputs[0]); mul.inputs[1].default_value = (1 / rv.x, 1 / rv.y, 1 / rv.z)
        ln = nb.n("ShaderNodeVectorMath", operation="LENGTH"); nb.L(mul.outputs[0], ln.inputs[0])
        m_ = nb_map(nb, ln.outputs["Value"], 0.6, 1.0, 1.0, 0.0)
        wd = m_ if wd is None else nb.math("MAXIMUM", wd, m_)
    fib = nb.noise(80.0, 3, 0.5, vec=nb.mapping(scale=(1, 0.2, 1)))
    raw = nb.ramp(fib.outputs["Fac"], [(0.3, (0.09, 0.004, 0.01)), (0.7, (0.38, 0.03, 0.04))]).outputs[0]
    rawm = nb.math("MAXIMUM", fl, wd)
    col_ = nb.mix(col_, raw, rawm)
    col_ = nb.mix(col_, (0.03, 0.0, 0.004), nb_map(nb, wd, 0.7, 0.95))
    slime = nb.noise(14.0, 4, 0.6)
    rough = nb.math("SUBTRACT", nb_map(nb, slime.outputs["Fac"], 0.3, 0.7, 0.1, 0.3), nb.math("MULTIPLY", rawm, 0.08))
    wr = nb.noise(55.0, 6, 0.65, vec=nb.mapping(scale=(1, 0.4, 1)))
    h = nb.math("ADD", nb.math("MULTIPLY", wr.outputs["Fac"], 0.6), nb.math("MULTIPLY", veins, 0.5), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", cd, 0.25), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", scars, 0.4), clamp=False)
    h = nb.math("SUBTRACT", h, nb.math("MULTIPLY", wd, 1.0), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", nb.math("MULTIPLY", fib.outputs["Fac"], rawm), 0.5), clamp=False)
    nb_finish_full(nb, col_, rough, h, bump=0.45, dist=0.008, spec=0.6)
    mat.diffuse_color = (0.06, 0.025, 0.03, 1)


def pouch_v3(mat):
    nb = NB(mat)
    mott = nb.noise(6.0, 5, 0.6)
    col_ = nb.ramp(mott.outputs["Fac"], [(0.3, (0.03, 0.01, 0.015)), (0.7, (0.12, 0.04, 0.05))]).outputs[0]
    vn = nb.noise(6.0, 5, 0.55, distortion=4.0)
    veins = nb.ramp(vn.outputs["Fac"], [(0.47, (0, 0, 0)), (0.5, (1, 1, 1)), (0.53, (0, 0, 0))]).outputs[0]
    vn2 = nb.noise(18.0, 4, 0.5, distortion=3.0)
    veins2 = nb.ramp(vn2.outputs["Fac"], [(0.49, (0, 0, 0)), (0.5, (1, 1, 1)), (0.51, (0, 0, 0))]).outputs[0]
    vm = nb.math("MAXIMUM", veins, nb.math("MULTIPLY", veins2, 0.6))
    col_ = nb.mix(col_, (0.3, 0.01, 0.04), nb.math("MULTIPLY", vm, 0.55))
    folds = nb.noise(28.0, 4, 0.5, vec=nb.mapping(scale=(3, 0.3, 0.3)))
    h = nb.math("ADD", nb.math("MULTIPLY", folds.outputs["Fac"], 0.5), nb.math("MULTIPLY", vm, 0.6), clamp=False)
    nb_finish_full(nb, col_, 0.2, h, bump=0.4, dist=0.006, spec=0.6)
    mat.diffuse_color = (0.08, 0.03, 0.035, 1)


def iris_e(mat):
    nb = NB(mat)
    rays = nb.noise(60.0, 4, 0.6, vec=nb.mapping(scale=(1, 1, 8)))
    c = nb.ramp(rays.outputs["Fac"], [(0.3, (0.3, 0.1, 0.005)), (0.7, (0.75, 0.42, 0.06))]).outputs[0]
    nb_finish_full(nb, c, 0.05, rays.outputs["Fac"], bump=0.1, dist=0.002, emit=c, emit_strength=1.0, spec=0.9)
    mat.diffuse_color = (0.8, 0.55, 0.1, 1)


eel_skin_v3(M_skin); pouch_v3(M_pouch); iris_e(M_iris)
flesh_shader(M_flesh, (0.2, 0.008, 0.02))
simple_shader(M_throat, (0.01, 0.0, 0.002), 0.25)
simple_shader(M_teeth, (0.62, 0.56, 0.42), 0.2, noise_scale=80, var=0.2, bump=0.12, veins=(30.0, (0.3, 0.2, 0.1), 0.4))
simple_shader(M_fin, (0.05, 0.015, 0.025), 0.28, noise_scale=10, var=0.45, bump=0.3, veins=(9.0, (0.24, 0.0, 0.035), 0.7))
simple_shader(M_hook, (0.34, 0.27, 0.17), 0.22, noise_scale=70, var=0.4, bump=0.15, veins=(30.0, (0.14, 0.07, 0.03), 0.6))
simple_shader(M_photo, (0.2, 0.55, 0.7), 0.1, noise_scale=60, var=0.2, emit=(0.25, 0.75, 1.0), emit_strength=1.2)
simple_shader(M_eye, (0.04, 0.02, 0.015), 0.04, noise_scale=20, var=0.5, bump=0.1, veins=(22.0, (0.25, 0.01, 0.02), 0.7))
simple_shader(M_pupil, (0.003, 0.002, 0.002), 0.04, var=0.0)
simple_shader(M_lflesh, (0.5, 0.12, 0.2), 0.15, noise_scale=40, var=0.35, bump=0.2, emit=(0.9, 0.12, 0.35), emit_strength=0.45, veins=(25.0, (0.25, 0.0, 0.05), 0.7))
simple_shader(M_leye, (0.85, 0.62, 0.6), 0.08, noise_scale=50, var=0.15, bump=0.1, emit=(1.0, 0.4, 0.45), emit_strength=0.5, veins=(30.0, (0.6, 0.02, 0.05), 0.9))
simple_shader(M_liris, (0.7, 0.05, 0.08), 0.1, noise_scale=90, var=0.3, emit=(1.0, 0.12, 0.18), emit_strength=1.0)
for m_, dc in ((M_teeth, (0.62, 0.56, 0.42)), (M_hook, (0.34, 0.27, 0.17)), (M_photo, (0.3, 0.75, 1.0)), (M_fin, (0.08, 0.03, 0.04)),
               (M_flesh, (0.3, 0.02, 0.04)), (M_lflesh, (0.6, 0.15, 0.25)), (M_leye, (0.85, 0.62, 0.6)), (M_eye, (0.05, 0.03, 0.02))):
    m_.diffuse_color = (*dc, 1)
for m_ in bpy.data.materials:
    if m_.name.startswith("M_EelX_"): m_.use_fake_user = True
EEL_INFO = {"tris": sum(len(p.vertices) - 2 for p in body.data.polygons), "bones": len(rig.data.bones),
            "unweighted": sum(1 for v in body.data.vertices if not v.groups), "mats": [m.name for m in body.data.materials],
            "dims": tuple(round(d, 2) for d in body.dimensions)}
print("EEL_INFO", EEL_INFO)
