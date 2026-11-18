# Map prop: single tetrapod (2026-11-18). exec after mk.py (+ weather_bake.py for the baked export) in DiveGear_Scene.blend.
# A standalone concrete tetrapod for hand placement / scattering in Unreal. Four tapered legs at tetrahedral angles,
# unioned with the hub into one clean closed mesh (exact boolean). Resting pose: three legs on the ground, one up.
# Weathering: chipped edges, pitting, a crack, one leg tip snapped off with rusty rebar sticking out,
# barnacles / mussels / algae on the lower (sea-bed) side.
# Frame: pivot = hub centre (good for random rotations when scattering); the resting legs touch z = GROUND_Z.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

MT = bpy.data.materials
ROOT, POS, SFX, SM_NAME = "Tetrapod", Vector((0, 145, 0)), "__TP", "SM_Tetrapod"
L, R0, R1 = 1.25, 0.38, 0.22          # leg length (hub centre -> tip), base / tip radius
UP = Vector((0, 0, 1))
DOWN = [Vector((math.sqrt(8) / 3 * math.cos(a), math.sqrt(8) / 3 * math.sin(a), -1 / 3)) for a in (0.3, 0.3 + 2.094, 0.3 + 4.189)]
BROKEN_LEG = 1                         # index into DOWN: its tip is snapped off

C = {}
def mats():
    C["conc"] = mat("M_Tp_Concrete", (0.45, 0.44, 0.41), rough=0.9)
    C["rebar"] = mat("M_Tp_Rebar", (0.28, 0.13, 0.06), rough=0.9)
    C["crack"] = mat("M_Tp_Crack", (0.04, 0.035, 0.03), rough=0.9)
    C["barn"] = MT.get("M_Bw_Barnacle") or mat("M_Bw_Barnacle", (0.68, 0.65, 0.58), rough=0.85)
    C["mussel"] = MT.get("M_Bw_Mussel") or mat("M_Bw_Mussel", (0.06, 0.055, 0.05), metal=0.1, rough=0.35)
    C["algae"] = MT.get("M_Bw_Algae") or mat("M_Bw_Algae", (0.16, 0.22, 0.12), rough=0.95)
    W = {"conc": dict(rust=0.15, grime=0.7, streak=0.35, mold=0.55, pit=1.0, scale=2.0, bump=0.9), "rebar": dict(rust=0.8, grime=0.5, pit=1.0, scale=6.0), "crack": dict(rust=0.2, grime=0.5),
         "barn": dict(rust=0.1, grime=0.4, scale=6.0), "mussel": dict(rust=0.1, grime=0.3, scale=8.0, rough=0.4), "algae": dict(rust=0.0, grime=0.4, mold=0.6, scale=4.0)}
    if "weather" in globals():
        for k, prm in W.items(): weather(C[k], **prm)


def merged(bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("_t"); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out


def nz(p, sc):
    return noise.noise(Vector(p) * sc)


def leg_bm(d, broken=False):
    """Tapered leg with a chamfered tip; a broken leg ends early in a jagged cap."""
    ln = L * (0.78 if broken else 1.0); r_end = R0 + (R1 - R0) * (ln / L)
    prof = [(0.0, -0.1), (R0 + 0.02, -0.1), (R0, 0.15)] + [(R0 + (R1 - R0) * t, ln * t) for t in (0.4, 0.7, 0.9, 1.0)]
    prof += ([(r_end * 0.8, ln + 0.05), (0.0, ln + 0.07)] if not broken else [(r_end * 0.5, ln + 0.02), (0.0, ln - 0.04)])
    b = lathe(prof, 28, d.to_track_quat("Z", "Y").to_matrix().to_4x4())
    return b, d * ln, r_end


def build():
    rnd = random.Random(41)
    for o in [o for o in bpy.data.objects if o.name.endswith(SFX)]:
        bpy.data.objects.remove(o, do_unlink=True)
    col = get_col(ROOT)
    old = bpy.data.objects.get(ROOT)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    root = bpy.data.objects.new(ROOT, None); col.objects.link(root); root.location = POS

    def put(name, bm, mats_, smooth=True):
        mats_ = mats_ if isinstance(mats_, (list, tuple)) else [mats_]
        o = finish(col, "TP_" + name + SFX, bm, mats_[0], smooth=smooth)
        for m in mats_[1:]: o.data.materials.append(m)
        o.parent = root; return o

    # ---- body: hub + 4 overlapping legs -> voxel remesh = one clean closed shell with cast-like fillets
    parts = [bmesh.new()]; bmesh.ops.create_icosphere(parts[0], subdivisions=4, radius=R0 * 1.12)
    tip_broken = None
    for i, d in enumerate([UP] + DOWN):
        b, tip, r_end = leg_bm(d.normalized(), broken=(i - 1 == BROKEN_LEG)); parts.append(b)
        if i - 1 == BROKEN_LEG: tip_broken = (tip, d.normalized(), r_end)
    body = put("Body", merged(parts), C["conc"])
    rm = body.modifiers.new("Remesh", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = 0.028; rm.adaptivity = 0.0
    sm_ = body.modifiers.new("Smooth", "SMOOTH"); sm_.factor = 0.5; sm_.iterations = 4
    new_me = bpy.data.meshes.new_from_object(body.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    old_me = body.data; body.modifiers.clear(); body.data = new_me; bpy.data.meshes.remove(old_me)
    if not body.data.materials: body.data.materials.append(C["conc"])
    # surface: pitting + shallow chips; the snapped leg end gets a jagged fracture face
    tip, dd, r_end = tip_broken
    bm = bmesh.new(); bm.from_mesh(body.data); bm.normal_update()
    for v in bm.verts:
        p = v.co; n = v.normal
        d = 0.008 * nz(p * 3.0, 1.0) + 0.004 * nz(p * 10.0, 1.0)
        chip = max(0.0, nz(p * 2.2 + Vector((7, 0, 0)), 1.0) - 0.55) * 0.08                    # shallow chipped patches
        q = p + n * (d - chip)
        if (p - tip).dot(dd) > -0.12:                                                        # fracture face
            q += dd * 0.06 * nz(p * 6.0 + Vector((0, 3, 0)), 1.0)
        v.co = q
    bm.to_mesh(body.data); bm.free(); body.data.shade_smooth()
    bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    def on_surface(p, lift):                                       # snap a point onto the shell
        co, n, _, _ = bvh.find_nearest(Vector(p)); return co + n * lift, n
    zmin = min(v.co.z for v in body.data.vertices)

    # ---- crack (thin dark strip along the up leg), rebar out of the broken tip
    crack = []                                                    # wanders down the surface of the upright leg
    for k in range(9):
        z = 1.05 - 0.09 * k; a = 0.3 + 0.35 * math.sin(k * 1.3); r = R0 + (R1 - R0) * (z / L) + 0.006
        crack.append(on_surface((r * math.cos(a), r * math.sin(a), z), 0.002)[0])
    cn = on_surface(crack[4], 0.0)[1]
    put("Crack", strap(catmull(crack, 3), cn, 0.014, 0.003), C["crack"])     # thin dark hairline on the surface
    tip, dd, r_end = tip_broken
    side = dd.orthogonal().normalized(); side2 = dd.cross(side)
    bars = []
    for k in range(5):
        a = k / 5 * math.tau + 0.4; base = tip + (side * math.cos(a) + side2 * math.sin(a)) * r_end * 0.55 - dd * 0.15
        bend = (side * math.cos(a) + side2 * math.sin(a)) * rnd.uniform(0.02, 0.12)
        bars.append(tube(catmull([base, base + dd * 0.22, base + dd * rnd.uniform(0.3, 0.45) + bend], 4), 0.014, sides=6))
    put("Rebar", merged(bars), C["rebar"])

    # ---- marine growth on the lower side (faces looking down / sideways near the resting legs)
    barn, mus, alg = [], [], []
    verts = [(v.co.copy(), v.normal.copy()) for v in body.data.vertices]
    for k in range(260):
        p, n = verts[rnd.randrange(len(verts))]
        if p.z > 0.15 or n.z > 0.4: continue
        h = rnd.uniform(0.012, 0.035); b = bmesh.new(); bmesh.ops.create_cone(b, cap_ends=True, segments=6, radius1=h * 1.1, radius2=h * 0.35, depth=h)
        bmesh.ops.transform(b, matrix=Matrix.Translation(p + n * (h / 2 - 0.004)) @ n.to_track_quat("Z", "Y").to_matrix().to_4x4(), verts=b.verts); barn.append(b)
    for k in range(5):
        p0, n0 = verts[rnd.randrange(len(verts))]
        while p0.z > -0.2: p0, n0 = verts[rnd.randrange(len(verts))]
        for _ in range(rnd.randint(7, 12)):
            p, n1 = on_surface(p0 + Vector((rnd.gauss(0, 0.06), rnd.gauss(0, 0.06), rnd.gauss(0, 0.04))), 0.015)
            b = bmesh.new(); bmesh.ops.create_uvsphere(b, u_segments=6, v_segments=4, radius=1.0)
            bmesh.ops.transform(b, matrix=Matrix.Translation(p) @ n1.to_track_quat("X", "Z").to_matrix().to_4x4() @ Matrix.Rotation(rnd.uniform(0, 6.3), 4, "X") @ Matrix.Diagonal((0.055, 0.025, 0.022, 1)), verts=b.verts)
            mus.append(b)
    for k in range(30):
        p, n = verts[rnd.randrange(len(verts))]
        if p.z > 0.2 or p.length < 0.7 or len(alg) >= 9: continue                              # on the legs, away from the hub
        t1 = n.orthogonal().normalized(); t2 = n.cross(t1); r = rnd.uniform(0.08, 0.2)
        pts = [p + n * 0.006 + (t1 * math.cos(a) + t2 * math.sin(a)) * r * (1 + 0.35 * nz((a, k, 1), 2)) for a in (q / 12 * math.tau for q in range(12))]
        b = bmesh.new(); vs = [b.verts.new(v) for v in pts]; b.faces.new(vs); alg.append(b)
    put("Barnacles", merged(barn), C["barn"], smooth=False)
    put("Mussels", merged(mus), C["mussel"])
    put("Algae", merged(alg), C["algae"], smooth=False)

    # ---- sockets: ground contact (for placement) and the top leg tip
    for nm, loc in (("Ground", Vector((0, 0, zmin))), ("TopTip", UP * (L + 0.07))):
        e = bpy.data.objects.new("SKT_" + nm + SFX, None); col.objects.link(e); e.empty_display_type = "ARROWS"; e.empty_display_size = 0.3
        e.parent = root; e.location = loc
    bpy.context.view_layer.update()
    print("TETRAPOD zmin", round(zmin, 3))
    return root


def export_all():
    root = bpy.data.objects[ROOT]
    mine = [o for o in root.children if o.name.startswith("SKT_") and o.name.endswith(SFX)]
    parked = []
    for o in mine:
        plain = o.name[:-len(SFX)]; other = bpy.data.objects.get(plain)
        if other: other.name = plain + "__park"; parked.append((other, plain))
        o.name = plain
    try:
        if "bake_export" in globals():
            return bake_export(ROOT, SM_NAME, "Tetrapod", size=2048)
        return export_unreal(ROOT, SM_NAME, (0, 0, 0))
    finally:
        for o in mine: o.name = o.name + SFX
        for other, plain in parked: other.name = plain


mats()
build()
print("TETRAPOD built")
