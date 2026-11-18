# Submarine Mk2 (2026-11-16): a new, higher-detail design in 3 states, built next to the original sub.
#   build_mk2("G") gameplay (repair points empty, no dome glass), ("W") wrecked, ("R") repaired.
# exec after mk.py in DiveGear_Scene.blend (needs the original Submarine for the inner cabin shell, dome ring,
# bay liner / battery cradle, hatch ring and the dome-shard sockets, plus the pickup items for the repaired state).
# Same cabin space as the original -> SM_Sub_Interior* and all interior sockets still fit; repair socket NAMES are the same.
# Root-local frame: hull centre = origin, +X forward, ground (skid bottom) at z = -1.55.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree

BASE = bpy.data.objects["Submarine"]
MT = bpy.data.materials
OFFSET = {"G": Vector((0, 14, 0)), "W": Vector((9, 14, 0)), "R": Vector((18, 14, 0))}
ROOTNAME = {"G": "Submarine2", "W": "Submarine2_Wrecked", "R": "Submarine2_Repaired"}

# ------------------------------------------------------------------ materials
m_white = mat("M_Sub2_PaintWhite", (0.82, 0.84, 0.83), metal=0.1, rough=0.35)
m_orange = mat("M_Sub2_PaintOrange", (0.92, 0.32, 0.04), metal=0.05, rough=0.4)
m_antifoul = mat("M_Sub2_Antifoul", (0.12, 0.13, 0.14), rough=0.6)
m_metal = mat("M_Sub2_Metal", (0.32, 0.34, 0.36), metal=0.9, rough=0.35)
m_dark = mat("M_Sub2_DarkMetal", (0.06, 0.065, 0.07), metal=0.6, rough=0.45)
m_chrome = MT["M_Sub_Chrome"]
m_window = mat("M_Sub2_Window", (0.02, 0.05, 0.07), metal=0.2, rough=0.05)
m_lens = mat("M_Sub2_LampLens", (1.0, 0.95, 0.85), emit=(1.0, 0.92, 0.8), strength=15.0)
m_line = mat("M_Sub2_PanelLine", (0.04, 0.045, 0.05), rough=0.7)
m_rubber = mat("M_Sub2_Rubber", (0.02, 0.02, 0.02), rough=0.85)
m_hazard = mat("M_Sub2_Hazard", (0.95, 0.75, 0.05), rough=0.5)
m_warn, m_ok = MT["M_Sub_Warning"], (MT.get("M_Sub_OK") or mat("M_Sub_OK", (0.05, 0.85, 0.2), emit=(0.1, 1.0, 0.3), strength=6.0))
m_crack = MT["M_Sub_Crack"]


# ------------------------------------------------------------------ helpers
def catmull1(vals, t):
    n = len(vals); i = min(int(t), n - 2); f = t - i
    p0, p1, p2, p3 = vals[max(i - 1, 0)], vals[i], vals[i + 1], vals[min(i + 2, n - 1)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)


def se(theta, ry, rz, n):                              # superellipse point (y, z)
    c, s = math.cos(theta), math.sin(theta)
    return (ry * math.copysign(abs(c) ** (2 / n), c), rz * math.copysign(abs(s) ** (2 / n), s))


def loft_x(stations, seg=64, samples=80, cap_front=False, cap_back=True, cy=0.0):
    """stations: [(x, cz, ry, rz, n)] ascending x. Smooth (Catmull-Rom) loft of superellipse sections along X."""
    cols = list(zip(*stations)); bm = bmesh.new(); rings = []
    for k in range(samples + 1):
        t = k / samples * (len(stations) - 1)
        x, cz, ry, rz, n = (catmull1(list(c), t) for c in cols)
        ring = []
        for j in range(seg):
            th = j / seg * math.tau
            y, z = se(th, max(ry, 1e-4), max(rz, 1e-4), max(n, 1.2))
            ring.append(bm.verts.new((x, cy + y, cz + z)))
        rings.append(ring)
    for k in range(samples):
        for j in range(seg):
            bm.faces.new((rings[k][j], rings[k][(j + 1) % seg], rings[k + 1][(j + 1) % seg], rings[k + 1][j]))
    if cap_back:
        bm.faces.new(list(reversed(rings[0])))
    if cap_front:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def merged(bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("_t"); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out


def along(n):
    return Vector(n).normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()


def bvh_of(bm):
    return BVHTree.FromBMesh(bm)


def proj(bvh, x, ang, lift=0.0, cz=0.0):              # ray from outside towards the hull axis at angle ang (deg from +Z to +Y)
    a = math.radians(ang); d = Vector((0, math.sin(a), math.cos(a)))
    hit = bvh.ray_cast(Vector((x, 0, cz)) + d * 4.0, -d)
    if hit[0] is None:
        return None, None
    return hit[0] + hit[1] * lift, hit[1]


def proj_dir(bvh, origin, direction, lift=0.0):
    hit = bvh.ray_cast(Vector(origin), Vector(direction).normalized())
    if hit[0] is None:
        return None, None
    return hit[0] + hit[1] * lift, hit[1]


def decal_strip(bvh, xa_pts, width, lift=0.004, thick=0.003):
    pts, nr = [], Vector()
    for x, a in xa_pts:
        p, n = proj(bvh, x, a, lift)
        if p is not None:
            pts.append(p); nr += n
    if len(pts) < 2:
        return None
    return strap(pts, nr.normalized(), width, thick)


def decal_fan(bvh, x, ang, sx, sa, seed, lift=0.003, n=22):
    rnd = random.Random(seed); bm = bmesh.new(); ph = rnd.random() * 6
    c, _ = proj(bvh, x, ang, lift)
    if c is None:
        return bm
    cv = bm.verts.new(c); ring = []
    for k in range(n):
        a = k / n * math.tau; rr = 1 + 0.3 * math.sin(3 * a + ph) + 0.15 * math.sin(7 * a + 2 * ph) + 0.07 * math.sin(13 * a)
        p, _ = proj(bvh, x + sx * rr * math.cos(a), ang + sa * rr * math.sin(a), lift)
        ring.append(bm.verts.new(p if p is not None else c))
    for k in range(n):
        bm.faces.new((cv, ring[k], ring[(k + 1) % n]))
    return bm


def frame_on(bvh, x, ang):                              # surface frame: X = outward normal, Y = along hull, Z = up the side
    p, n = proj(bvh, x, ang)
    Y = (Vector((1, 0, 0)) - n * n.x).normalized(); Z = n.cross(Y)
    F = Matrix((n, Y, Z)).transposed().to_4x4(); F.translation = p
    return F


def tri_w(x):
    f = x - math.floor(x); return 4 * abs(f - 0.5) - 1


# ------------------------------------------------------------------ fixed design data
BODY_ST = [(-3.95, 0.0, 0.05, 0.05, 2.0), (-3.82, 0.0, 0.2, 0.2, 2.0), (-3.5, 0.0, 0.45, 0.45, 2.0), (-2.9, 0.0, 0.8, 0.78, 2.1),
           (-2.2, 0.0, 1.1, 1.06, 2.3), (-1.4, 0.02, 1.3, 1.26, 2.5), (-0.5, 0.03, 1.36, 1.31, 2.6), (0.5, 0.03, 1.36, 1.31, 2.6),
           (1.5, 0.02, 1.33, 1.29, 2.5), (2.0, 0.0, 1.24, 1.22, 2.3), (2.22, 0.0, 1.13, 1.12, 2.1), (2.29, 0.0, 1.05, 1.05, 2.0)]
SAIL_ST = [(-0.82, 1.2, 0.04, 0.2, 3.0), (-0.7, 1.33, 0.22, 0.33, 3.2), (-0.45, 1.44, 0.37, 0.46, 3.5), (0.15, 1.45, 0.44, 0.45, 3.6),
           (0.6, 1.45, 0.42, 0.45, 3.6), (0.82, 1.36, 0.36, 0.36, 3.2), (1.0, 1.22, 0.24, 0.22, 2.8), (1.1, 1.1, 0.06, 0.1, 2.5)]
SPON_ST = [(-2.6, -0.8, 0.04, 0.05, 2.0), (-2.48, -0.8, 0.2, 0.23, 2.1), (-2.2, -0.8, 0.3, 0.34, 2.2), (1.4, -0.8, 0.3, 0.34, 2.2),
           (1.72, -0.8, 0.22, 0.26, 2.1), (1.88, -0.8, 0.05, 0.06, 2.0)]
HUB_X, HUB_R, NBLADE = -4.28, 0.12, 5
CRACK = (-1.7, 52)                                     # hull crack / patch spot (x, angle)
PIPE_Y, PIPE_GAP = 0.6, (-1.25, -0.85)
GEAR_X = -2.62
FUSE = Vector((0.45, 0.0, 1.5))


def blade_bm(span=0.5):
    """Twisted, tapered propeller blade. Local: root at origin, span along +Z, chord ~ along X."""
    bm = bmesh.new(); rings = []
    NS, NC = 9, 10
    for i in range(NS):
        s = i / (NS - 1); z = s * span
        chord = 0.21 - 0.09 * s + 0.03 * math.sin(math.pi * s); thick = 0.016 - 0.01 * s
        beta = math.radians(48 - 30 * s); ring = []
        for j in range(NC):
            a = j / NC * math.tau
            u, v = 0.5 * chord * math.cos(a), 0.5 * thick * math.sin(a) * (1.3 if math.cos(a) > 0 else 0.8)
            x = u * math.cos(beta) - v * math.sin(beta); y = u * math.sin(beta) + v * math.cos(beta)
            ring.append(bm.verts.new((x + 0.02 * s * s, y, z)))
        rings.append(ring)
    for i in range(NS - 1):
        for j in range(NC):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % NC], rings[i + 1][(j + 1) % NC], rings[i + 1][j]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def blade_matrix(k):
    phi = k / NBLADE * 360.0
    return Matrix.Translation((HUB_X, 0, 0)) @ Matrix.Rotation(math.radians(phi), 4, "X") @ Matrix.Translation((0, 0, HUB_R))


# ------------------------------------------------------------------ the builder
def build_mk2(state):
    rnd = random.Random(5 if state == "W" else 1); random.seed(5)
    rn = ROOTNAME[state]; col = get_col(rn); sfx = {"G": "__G2", "W": "__W2", "R": "__R2"}[state]
    for o in [o for o in bpy.data.objects if o.name.endswith(sfx)]:
        bpy.data.objects.remove(o, do_unlink=True)
    old = bpy.data.objects.get(rn)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    root = bpy.data.objects.new(rn, None); col.objects.link(root)
    root.matrix_world = Matrix.Translation(OFFSET[state]) @ BASE.matrix_world
    W = state == "W"; R = state == "R"
    made = {}

    def put(name, bm, material, smooth=False, extra=()):
        o = finish(col, name + sfx, bm, material, smooth=smooth)
        o.parent = root
        for m in extra:
            o.data.materials.append(m)
        made[name] = o
        return o

    def sock(name, loc, rot=(0, 0, 0)):
        e = bpy.data.objects.new("SKT_" + name + sfx, None); col.objects.link(e)
        e.empty_display_type = "ARROWS"; e.empty_display_size = 0.08
        e.parent = root; e.location = loc
        e.rotation_euler = rot if isinstance(rot, Euler) else Euler(tuple(math.radians(a) for a in rot))
        return e

    def lamp(name, pos, normal, broken=False):
        n = Vector(normal).normalized()
        put(name + "Base", cyl(0.03, 0.02, 16, (0, 0, 0.01), Matrix.Translation(pos) @ along(n)), m_dark)
        mm = m_ok if R else (MT.get("M_Sub_LampBroken") if (W and MT.get("M_Sub_LampBroken")) else m_warn)
        put(name, lathe([(0.0, 0.035), (0.018, 0.03), (0.022, 0.02), (0.022, 0.0)], 16, Matrix.Translation(pos) @ along(n) @ Matrix.Translation((0, 0, 0.02))), mm, smooth=True)

    # ============ inner cabin shell from the original hull (cabin walls, hatch-hole rim, bay walls)
    src = bpy.data.objects["SUB_Hull"].data
    bm = bmesh.new(); bm.from_mesh(src)
    outer_idx = [i for i, m in enumerate(src.materials) if m and m.name == "M_Sub_Hull"]
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in outer_idx], context="FACES")
    shell = put("S2_CabinShell", bm, MT["M_Sub_InteriorWall"])
    shell.data.materials.clear()
    for m in src.materials:
        shell.data.materials.append(m)
    for n in ("SUB_DomeRing", "SUB_BayLiner", "SUB_BatteryCradle", "SUB_HatchRing"):
        o = bpy.data.objects[n]; d = o.copy(); d.data = o.data.copy(); d.name = "S2_" + n[4:] + sfx
        col.objects.link(d); d.parent = root; d.matrix_parent_inverse = o.matrix_parent_inverse.copy()
    # dome glass: gameplay = none (collect shards), repaired = full, wrecked = shattered teeth (below)
    if R and bpy.data.meshes.get("SUB_Dome_full"):
        d = bpy.data.objects.new("S2_Dome" + sfx, bpy.data.meshes["SUB_Dome_full"].copy()); col.objects.link(d); d.parent = root
    # extra bolt ring on the dome flange (detail)
    put("S2_DomeBolts", merged([cyl(0.016, 0.02, 6, (0, 0, 0), Matrix.Translation((2.36, 1.0 * math.cos(a), 1.0 * math.sin(a))) @ RY(90))
                                for a in (k / 28 * math.tau for k in range(28))]), m_chrome)

    # ============ main body (streamlined fairing around the cabin)
    body_bm = loft_x(BODY_ST, seg=72, samples=96, cap_front=False, cap_back=True)
    if W:                                                     # dents
        for (dx, dang, rad, depth) in ((0.4, 50, 0.55, 0.09), (-1.2, -115, 0.45, 0.08), (1.3, 125, 0.4, 0.07), (-2.4, 70, 0.35, 0.06)):
            a = math.radians(dang); c = Vector((dx, 1.33 * math.sin(a), 1.29 * math.cos(a)))
            for v in body_bm.verts:
                d = (v.co - c).length
                if d < rad:
                    f = 0.5 * (1 + math.cos(math.pi * d / rad)); r = Vector((0, v.co.y, v.co.z))
                    if r.length > 0.5:
                        v.co -= r.normalized() * depth * f
    bvh = bvh_of(body_bm)
    # paint split: antifouling below the waterline
    for f in body_bm.faces:
        f.material_index = 1 if f.calc_center_median().z < -0.5 else 0
    # openings: battery bay (port), hatch trunk (top)
    cut = [f for f in body_bm.faces if (-0.76 < f.calc_center_median().x < 0.36 and abs(f.calc_center_median().z) < 0.39 and f.calc_center_median().y < -0.8)
           or ((Vector((f.calc_center_median().x - 0.15, f.calc_center_median().y, 0)).length < 0.3) and f.calc_center_median().z > 0.6)]
    bmesh.ops.delete(body_bm, geom=cut, context="FACES")
    put("S2_Body", body_bm, m_white, smooth=True, extra=(m_antifoul,))
    # bay frame on the body surface
    frame = []
    for (x, z) in [(-0.78, -0.41), (0.38, -0.41), (0.38, 0.41), (-0.78, 0.41)]:
        p, n = proj_dir(bvh, (x, -3, z), (0, 1, 0), 0.01); frame.append(p)
    put("S2_BayFrame", strap(catmull(frame + [frame[0]], 6)[:-1], Vector((0, -1, 0)), 0.07, 0.03, closed=True), m_dark)
    # orange side stripe + panel lines + rivets
    stripes = [decal_strip(bvh, [(x / 10, s * 63) for x in range(-30, 22)], 0.09) for s in (-1, 1)]
    put("S2_Stripe", merged([b for b in stripes if b]), m_orange)
    lines, rivets = [], []
    for xs in (-2.65, -1.9, -1.05, 1.0, 1.85):
        pts = [(xs, a) for a in range(-180, 181, 6) if not (xs == 1.0 and abs(a) < 30) and not (-0.85 < xs < 0.45 and -115 < a < -65)]
        b = decal_strip(bvh, pts, 0.012)
        if b: lines.append(b)
        for a in range(-180, 180, 12):
            if xs == 1.0 and abs(a) < 30: continue
            for dx in (-0.025, 0.025):
                p, n = proj(bvh, xs + dx, a, 0.0)
                if p is not None:
                    rivets.append(lathe([(0.0, 0.009), (0.007, 0.006), (0.009, 0.0)], 6, Matrix.Translation(p) @ along(n)))
    for s in (-1, 1):
        b = decal_strip(bvh, [(x / 10, s * 75) for x in range(-28, 21)], 0.012)
        if b: lines.append(b)
    put("S2_PanelLines", merged(lines), m_line)
    put("S2_Rivets", merged(rivets), m_metal, smooth=True)

    # ============ sail (conning tower)
    sail_bm = loft_x(SAIL_ST, seg=48, samples=60, cap_front=True, cap_back=True)
    sail_bvh = bvh_of(sail_bm)
    top = [f for f in sail_bm.faces if Vector((f.calc_center_median().x - 0.15, f.calc_center_median().y, 0)).length < 0.31 and f.calc_center_median().z > 1.7]
    bmesh.ops.delete(sail_bm, geom=top, context="FACES")
    if W:
        for v in sail_bm.verts:                               # bashed front edge
            if v.co.x > 0.8 and v.co.z > 1.4:
                v.co.x -= 0.05 * (v.co.z - 1.4) / 0.5
    put("S2_Sail", sail_bm, m_orange, smooth=True)
    put("S2_Trunk", lathe([(0.3, 0.9), (0.33, 0.9), (0.33, 1.9), (0.3, 1.9), (0.3, 0.9)], 32, Matrix.Translation((0.15, 0, 0))), m_dark, smooth=True)
    put("S2_SailCap", lathe([(0.38, 1.895), (0.46, 1.895), (0.46, 1.91), (0.38, 1.91), (0.38, 1.895)], 32, Matrix.Translation((0.15, 0, 0))), m_dark)
    win, wfr = [], []
    for yc in (-0.2, 0.0, 0.2):
        quad = []
        for (dy, z) in ((-0.075, 1.48), (0.075, 1.48), (0.075, 1.72), (-0.075, 1.72)):
            p, n = proj_dir(sail_bvh, (3, yc + dy, z), (-1, 0, 0), 0.006); quad.append(p)
        b = bmesh.new(); b.faces.new([b.verts.new(p) for p in quad]); win.append(b)
        p2 = [proj_dir(sail_bvh, (3, yc + dy, z), (-1, 0, 0), 0.01)[0] for (dy, z) in ((-0.09, 1.465), (0.09, 1.465), (0.09, 1.735), (-0.09, 1.735))]
        wfr.append(strap(p2, Vector((1, 0, 0.6)), 0.025, 0.02, closed=True))
    put("S2_Windows", merged(win), m_window)
    put("S2_WindowFrames", merged(wfr), m_dark)
    rails = []
    for s in (-1, 1):
        pts = [proj_dir(sail_bvh, (x, s * 3, 1.62), (0, -s, 0), 0.06)[0] for x in (-0.45, -0.1, 0.25, 0.6)]
        rails.append(tube(catmull(pts, 5), 0.015, sides=8))
        for p in pts[::3]:
            rails.append(cyl(0.012, 0.07, 8, (0, 0, 0), Matrix.Translation(p - Vector((0, s * 0.035, 0))) @ RX(90)))
    put("S2_SailRails", merged(rails), m_chrome, smooth=True)
    mast_tilt = Matrix.Rotation(math.radians(-35), 4, "Y") if W else Matrix.Identity(4)
    MP = Vector((-0.42, 0, 1.9))
    put("S2_Mast", cyl(0.025, 0.55, 10, (0, 0, 0.275), Matrix.Translation(MP) @ mast_tilt), m_metal, smooth=True)
    put("S2_Radome", lathe([(0.0, 0.0), (0.09, 0.0), (0.09, 0.05), (0.06, 0.1), (0.0, 0.12)], 20, Matrix.Translation(MP + Vector((0.18, 0, 0)))), m_white, smooth=True)
    put("S2_Strobe", cyl(0.03, 0.05, 12, (0, 0, 0.575), Matrix.Translation(MP) @ mast_tilt), MT.get("M_Sub_LampBroken") if W else m_warn)
    # fuse box (starboard side of the sail)
    p, n = proj_dir(sail_bvh, (FUSE.x, 3, FUSE.z), (0, -1, 0))
    fb = p + Vector((0, 0.04, 0))
    put("S2_FuseBox", box((0.3, 0.08, 0.26), fb), m_dark)
    put("S2_FuseSlot", box((0.2, 0.01, 0.12), fb + Vector((0, 0.041, 0))), m_line)
    lamp("S2_Warn_Fuse", fb + Vector((0.12, 0.042, 0.1)), (0, 1, 0))
    sock("Repair_Fuse", fb + Vector((0, 0.045, -0.06)), (-90, 0, 0))
    if R:
        install_item("FuseModule", root, col, "Repair_Fuse", sfx)
    # hatch / escape (same hinge as the original -> SM_Sub_HatchLid fits)
    for nm in ("HatchHinge", "Escape", "BayDoorHinge", "Repair_Battery") + tuple(f"DomeShard_{i}" for i in range(1, 7)):
        b = bpy.data.objects["SKT_" + nm]
        e = sock(nm, (0, 0, 0)); e.matrix_parent_inverse = Matrix.Identity(4)
        e.matrix_basis = BASE.matrix_world.inverted() @ b.matrix_world
    if R:
        install_item("Battery", root, col, "Repair_Battery", sfx)
    lamp("S2_Warn_Bay", Vector((-0.7, -1.38, 0.3)), (0, -1, 0))

    # ============ sponsons, thrusters, skids
    spon, sponlamps, thr, skid = [], [], [], []
    for s in (-1, 1):
        b = loft_x([(x, cz, ry, rz, n) for (x, cz, ry, rz, n) in SPON_ST], seg=40, samples=50, cap_front=True, cap_back=True, cy=s * 1.42)
        spon.append(b)
        nose = Vector((1.86, s * 1.42, -0.8))
        sponlamps.append(cyl(0.06, 0.05, 16, (0, 0, 0), Matrix.Translation(nose + Vector((0.02, 0, 0))) @ RY(90)))
        if not (W and s > 0):                                  # wrecked: starboard thruster torn off
            tp = Vector((-1.85, s * 1.42, -0.47))
            thr.append(lathe([(0.15, 0.0), (0.18, 0.0), (0.18, 0.1), (0.15, 0.1), (0.15, 0.0)], 24, Matrix.Translation(tp)))
            thr.append(cyl(0.035, 0.08, 12, (0, 0, 0.05), Matrix.Translation(tp)))
            for k in range(4):
                thr.append(box((0.3, 0.012, 0.015), (0, 0, 0.05), Matrix.Translation(tp) @ RZ(k * 45)))
        rail = [Vector((2.15, s * 1.42, -1.22)), Vector((2.0, s * 1.42, -1.44)), Vector((1.7, s * 1.42, -1.505)), Vector((-2.3, s * 1.42, -1.505)), Vector((-2.45, s * 1.42, -1.45))]
        if W and s < 0:
            rail = [p + Vector((0, 0, 0.22 * max(0.0, (p.x - 0.5) / 1.7))) for p in rail]   # bent skid
        skid.append(tube(catmull(rail, 6), 0.045, sides=10))
        for x in (1.3, -0.3, -1.8):
            skid.append(box((0.07, 0.06, 0.38), (x, s * 1.42, -1.32)))
    sp_bm = merged(spon)
    for f in sp_bm.faces:                                       # dark metal nose / tail caps
        cx = f.calc_center_median().x
        f.material_index = 1 if (cx > 1.6 or cx < -2.38) else 0
    put("S2_Sponsons", sp_bm, m_orange, smooth=True, extra=(m_dark,))
    det = []
    for s in (-1, 1):
        for x in (-1.75, -0.2, 1.15):                            # seam bands
            det.append(torus(0.312, 0.012, 32, 6, Matrix.Translation((x, s * 1.42, -0.8)) @ RY(90) @ Matrix.Diagonal((1.13, 1.0, 1.0, 1.0))))
        for k in range(5):                                       # vent grille on the outboard side
            det.append(box((0.18, 0.01, 0.018), (0.55, s * (1.42 + 0.305), -0.9 + k * 0.04)))
        det.append(box((0.22, 0.008, 0.2), (0.55, s * (1.42 + 0.3), -0.82)))
    put("S2_SponsonDetail", merged(det), m_dark, smooth=False)
    put("S2_SponsonLamps", merged(sponlamps), MT.get("M_Sub_LampBroken") if W else m_lens, smooth=True)
    if thr:
        put("S2_Thrusters", merged(thr), m_dark, smooth=False)
    put("S2_Skids", merged(skid), m_metal, smooth=True)
    hz = [box((0.012, 0.05, 0.3), (0, 0, 0), Matrix.Translation((1.83, s * 1.42 + o, -0.8)) @ RX(35)) for s in (-1, 1) for o in (-0.1, 0.0, 0.1)]
    put("S2_HazardBars", merged(hz), m_hazard)

    # ============ stern: X fins, duct, hub, blades
    fins = []
    for k, phi in enumerate((45, 135, 225, 315)):
        a = math.radians(phi); d = Vector((0, math.sin(a), math.cos(a))); nrm = Vector((0, math.cos(a), -math.sin(a)))
        def rb(x):
            t = max(0.0, min(1.0, (x + 3.95) / 1.75)); return 0.05 + t * 0.95 - 0.08
        quad = [Vector((-2.55, 0, 0)) + d * rb(-2.55), Vector((-3.35, 0, 0)) + d * rb(-3.35), Vector((-3.6, 0, 0)) + d * 1.2, Vector((-3.15, 0, 0)) + d * 1.2]
        if W and k == 1:
            quad[2] += Vector((0.1, 0, 0)) - d * 0.25; quad[3] += -d * 0.3
        b = bmesh.new()
        vs = [b.verts.new(p + nrm * 0.022) for p in quad] + [b.verts.new(p - nrm * 0.022) for p in quad]
        for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            b.faces.new([vs[i] for i in f])
        fins.append(b)
    put("S2_Fins", merged(fins), m_white)
    duct = lathe([(0.64, -0.25), (0.70, -0.24), (0.75, -0.12), (0.75, 0.1), (0.71, 0.25), (0.66, 0.25), (0.64, -0.25)], 48,
                 Matrix.Translation((HUB_X - 0.02, 0, 0)) @ RY(90))
    if W:                                                     # crushed + torn duct
        for v in duct.verts:
            ang = math.degrees(math.atan2(v.co.z, v.co.y)); dd = min(abs(ang - 50), 360 - abs(ang - 50))
            if dd < 50:
                f = 0.5 * (1 + math.cos(math.pi * dd / 50)); v.co.y *= 1 - 0.2 * f; v.co.z *= 1 - 0.2 * f; v.co.x += 0.06 * f
        gone = [f for f in duct.faces if 100 < (math.degrees(math.atan2(f.calc_center_median().z, f.calc_center_median().y)) % 360) < 128]
        bmesh.ops.delete(duct, geom=gone, context="FACES")
    put("S2_Duct", duct, m_dark, smooth=True)
    stat = [box((0.03, 0.012, 0.54), (0, 0, 0.39), Matrix.Translation((HUB_X + 0.18, 0, 0)) @ RX(45 + 90 * k)) for k in range(4)]
    put("S2_Stators", merged(stat), m_dark)
    hub_tilt = Matrix.Translation((-3.95, 0, 0)) @ Matrix.Rotation(math.radians(13), 4, Vector((0, 0.5, 1)).normalized()) @ Matrix.Translation((3.95, 0, 0)) if W else Matrix.Identity(4)
    put("S2_Hub", lathe([(0.0, 0.34), (0.07, 0.33), (0.12, 0.22), (0.125, 0.0), (0.12, -0.2), (0.07, -0.33), (0.0, -0.38)], 32,
                        hub_tilt @ Matrix.Translation((HUB_X, 0, 0)) @ RY(90)), m_chrome, smooth=True)
    put("S2_Shaft", cyl(0.06, 0.12, 16, (0, 0, 0), Matrix.Translation((-3.93, 0, 0)) @ RY(90)), m_metal, smooth=True)
    blades = []
    keep = range(NBLADE) if R else (range(1, NBLADE) if state == "G" else ())
    for k in keep:
        b = blade_bm(); bmesh.ops.transform(b, matrix=hub_tilt @ blade_matrix(k), verts=b.verts); blades.append(b)
    stubs = []
    for k in range(NBLADE):
        if (state == "G" and k == 0) or W:
            b = bmesh.new()
            pts = [(-0.05, 0.0), (0.05, 0.0), (0.045, 0.04), (0.02, 0.06), (0.0, 0.045), (-0.025, 0.07), (-0.05, 0.05)]
            v0 = [b.verts.new((x, -0.01, z)) for x, z in pts]; v1 = [b.verts.new((x, 0.01, z)) for x, z in pts]
            b.faces.new(v0); b.faces.new(list(reversed(v1)))
            for i in range(len(pts)):
                j = (i + 1) % len(pts); b.faces.new((v0[i], v0[j], v1[j], v1[i]))
            bmesh.ops.transform(b, matrix=hub_tilt @ blade_matrix(k) @ RZ(45), verts=b.verts); stubs.append(b)
    if blades:
        put("S2_Blades", merged(blades), m_chrome, smooth=True)
    if stubs:
        put("S2_BladeStubs", merged(stubs), MT["M_Sub_Rust"])
    sock("Repair_Prop", blade_matrix(0).translation, (0, 0, 0))
    lamp("S2_Warn_Prop", Vector((-3.3, 0, 0.5)), (0, 0, 1))
    if W and bpy.data.objects.get("Sub2PropBlade"):           # one broken blade jammed in the torn duct
        src_o = bpy.data.objects["S2PB_Blade"]; b = bmesh.new(); b.from_mesh(src_o.data)
        for vv in b.verts:
            if vv.co.z > 0.25: vv.co.x += (vv.co.z - 0.25) * 0.8
        bmesh.ops.transform(b, matrix=Matrix.Translation((HUB_X + 0.05, -0.3, 0.62)) @ RX(70) @ RY(20), verts=b.verts)
        put("S2_BrokenBlade", b, m_chrome)

    # ============ bow: floodlight bar (headlights), manipulator arm
    bar = [Vector((2.16, 1.2 * math.sin(math.radians(a)), 1.2 * math.cos(math.radians(a)))) for a in range(-64, 65, 8)]
    put("S2_LightBar", tube(bar, 0.03, sides=10), m_dark, smooth=True)
    housings, lenses = [], []
    for i, a in enumerate((-48, -16, 16, 48)):
        p = Vector((2.2, 1.2 * math.sin(math.radians(a)), 1.2 * math.cos(math.radians(a))))
        Mh = Matrix.Translation(p) @ RY(90)
        if W and i == 2:
            Mh = Matrix.Translation(p + Vector((0.02, 0, -0.12))) @ RY(90) @ RX(55)       # knocked loose, hanging
        housings.append(cyl(0.075, 0.16, 20, (0, 0, 0), Mh))
        housings.append(torus(0.075, 0.01, 20, 6, Mh @ Matrix.Translation((0, 0, 0.08))))
        lenses.append(cyl(0.065, 0.01, 20, (0, 0, 0.081), Mh))
        sock(f"Headlight_{i + 1}", (Mh @ Vector((0, 0, 0.09))), (0, 0, 0))
    put("S2_LampHousings", merged(housings), m_dark, smooth=True)
    put("S2_LampLenses", merged(lenses), MT.get("M_Sub_LampBroken") if W else m_lens)
    arm_bend = Matrix.Rotation(math.radians(25), 4, "Z") if W else Matrix.Identity(4)
    J0, J1, J2 = Vector((1.98, 0, -1.2)), Vector((2.42, 0.0, -1.12)), Vector((2.3, 0.05, -1.36))
    if W:
        J2 = Vector((2.55, -0.25, -1.4))
    arm = [cyl(0.13, 0.1, 20, (0, 0, 0), Matrix.Translation(Vector((1.98, 0, -1.1)))),
           tube([J0, J1], 0.045, sides=10), tube([J1, J2], 0.035, sides=10)]
    for J in (J0, J1, J2):
        arm.append(cyl(0.055, 0.09, 14, (0, 0, 0), Matrix.Translation(J) @ RX(90)))
    claw = []
    for k in range(3):
        a = k / 3 * 360
        claw.append(box((0.02, 0.02, 0.13), (0, 0, 0.065), Matrix.Translation(J2) @ along(J2 - J1) @ RZ(a) @ Matrix.Translation((0.03, 0, 0)) @ RY(-15 if not W or k else 40)))
    put("S2_Arm", merged(arm), m_metal, smooth=True)
    put("S2_Claw", merged(claw), m_dark)

    # ============ deck: railings + deck pipe (repair point)
    deck = []
    for s in (-1, 1):
        posts = []
        for x in (-2.15, -1.8, -1.45, -1.1, -0.85):
            p, n = proj(bvh, x, s * 20)
            if p is None: continue
            posts.append(p); deck.append(cyl(0.012, 0.32, 8, (0, 0, 0.16), Matrix.Translation(p)))
        deck.append(tube([p + Vector((0, 0, 0.32)) for p in posts], 0.014, sides=8))
    put("S2_Railings", merged(deck), m_chrome, smooth=True)
    pz = proj(bvh, -1.05, math.degrees(math.atan2(PIPE_Y, 1.2)))[0].z + 0.08
    pipe = []
    for (x0, x1) in ((-2.3, PIPE_GAP[0]), (PIPE_GAP[1], -0.35)):
        pipe.append(cyl(0.055, x1 - x0, 20, (0, 0, 0), Matrix.Translation(((x0 + x1) / 2, PIPE_Y, pz)) @ RY(90)))
    for x in PIPE_GAP:
        pipe.append(cyl(0.09, 0.03, 20, (0, 0, 0), Matrix.Translation((x, PIPE_Y, pz)) @ RY(90)))
    for x in (-2.0, -1.6, -0.6):
        p, n = proj(bvh, x, math.degrees(math.atan2(PIPE_Y, 1.2)))
        pipe.append(box((0.05, 0.13, pz - p.z + 0.03), (x, PIPE_Y, (pz + p.z) / 2)))
    put("S2_DeckPipe", merged(pipe), MT["M_Sub_Rust"] if W else m_metal, smooth=True)
    sock("Repair_Pipe", ((PIPE_GAP[0] + PIPE_GAP[1]) / 2, PIPE_Y, pz), (0, 0, 0))
    lamp("S2_Warn_Pipe", Vector((-1.05, PIPE_Y + 0.15, pz - 0.02)), (0, 0.3, 1))
    if R:
        install_item("RepairPipe", root, col, "Repair_Pipe", sfx)

    # ============ stern gearbox (port), repair point for the gear
    p, n = proj(bvh, GEAR_X, -88)
    gb = p + Vector((0, -0.07, 0))
    put("S2_GearBox", box((0.46, 0.16, 0.46), gb), m_dark)
    put("S2_GearRecess", box((0.36, 0.012, 0.36), gb + Vector((0, -0.08, 0))), m_line)
    put("S2_GearAxle", cyl(0.025, 0.08, 12, (0, 0, 0), Matrix.Translation(gb + Vector((0, -0.12, 0))) @ RX(90)), m_chrome)
    sock("Repair_Gear", gb + Vector((0, -0.086, 0)), (90, 0, 0))
    lamp("S2_Warn_Gear", gb + Vector((0.18, -0.082, 0.18)), (0, -1, 0))
    if R:
        install_item("RepairGear", root, col, "Repair_Gear", sfx)

    # ============ hull crack (gameplay/wrecked) / patch (repaired)
    Fc = frame_on(bvh, *CRACK)
    e = sock("Repair_Hull", (0, 0, 0)); e.matrix_parent_inverse = Matrix.Identity(4); e.matrix_basis = Fc
    lamp("S2_Warn_Hull", proj(bvh, CRACK[0], CRACK[1] - 14)[0], proj(bvh, CRACK[0], CRACK[1] - 14)[1])
    if R:
        install_item("Sub2HullPatch", root, col, "Repair_Hull", sfx)
    else:
        cr = []
        for dsign in (-1, 1):
            pts = []; x, a = CRACK
            for i in range(6):
                pts.append((x, a)); x += dsign * 0.04 * (0.8 + 0.4 * random.random()); a += random.uniform(-2.5, 2.5)
            b = decal_strip(bvh, pts, 0.016, lift=0.005)
            if b: cr.append(b)
        put("S2_HullCrack", merged(cr), m_crack)
        put("S2_HullCrackStain", decal_fan(bvh, CRACK[0], CRACK[1], 0.12, 6, 3), MT["M_Sub_Rust"])

    # ============ WRECKED extras
    if W:
        m_rust_patch = MT.get("M_Sub_RustPatch") or mat("M_Sub_RustPatch", (0.36, 0.13, 0.04), rough=0.9)
        m_rust_core = MT.get("M_Sub_RustHeavy") or mat("M_Sub_RustHeavy", (0.13, 0.05, 0.02), rough=0.95)
        m_run = MT.get("M_Sub_RustStreak") or mat("M_Sub_RustStreak", (0.45, 0.17, 0.05), rough=0.9)
        for o in (made["S2_Body"], made["S2_Sail"], made["S2_Sponsons"], made["S2_Fins"]):
            for sl in o.material_slots:
                if sl.material in (m_white, m_orange):
                    sl.material = mat("M_Sub2_PaintFaded" if sl.material == m_white else "M_Sub2_OrangeFaded",
                                      (0.62, 0.62, 0.58) if sl.material == m_white else (0.62, 0.28, 0.08), rough=0.75)
        spots = []
        for xs in (-2.65, -1.9, -1.05, 1.0, 1.85):                      # along panel lines
            for _ in range(5):
                spots.append((xs + random.uniform(-0.05, 0.05), random.choice((-1, 1)) * random.uniform(30, 165), random.uniform(0.08, 0.17), random.uniform(5, 12)))
        for _ in range(16):                                               # lower body
            spots.append((random.uniform(-3.0, 2.0), random.choice((-1, 1)) * random.uniform(110, 175), random.uniform(0.12, 0.26), random.uniform(6, 12)))
        for _ in range(12):
            spots.append((random.uniform(-3.0, 2.0), random.choice((-1, 1)) * random.uniform(25, 110), random.uniform(0.07, 0.15), random.uniform(4, 9)))
        spots = [sp for sp in spots if not (-0.9 < sp[0] < 0.5 and -120 < sp[1] < -60)]
        put("S2_RustPatches", merged([decal_fan(bvh, x, a, sx, sa, 40 + i, 0.004) for i, (x, a, sx, sa) in enumerate(spots)]), m_rust_patch)
        put("S2_RustCores", merged([decal_fan(bvh, x, a, sx * 0.45, sa * 0.45, 140 + i, 0.005) for i, (x, a, sx, sa) in enumerate(spots)]), m_rust_core)
        runs = [decal_strip(bvh, [(x + 0.01 * math.sin(i), s * (a0 + i * 6)) for i in range(7)], 0.03, lift=0.006)
                for x in (-2.65, -1.9, -1.05, 1.0, 1.85, -0.4, 0.6) for s in (-1, 1) for a0 in (random.uniform(40, 90),)]
        put("S2_RustRuns", merged([b for b in runs if b]), m_run)
        crk = []
        for (cx, ca) in ((0.4, 50), (-1.2, -115), (1.3, 125), (-2.4, 70), (0.9, -40)):
            for dsign in (-1, 1):
                pts = []; x, a = cx, ca
                for i in range(5):
                    pts.append((x, a)); x += dsign * 0.045; a += random.uniform(-3, 3)
                b = decal_strip(bvh, pts, 0.016, lift=0.006)
                if b: crk.append(b)
        put("S2_WreckCracks", merged(crk), m_crack)
        # breach in the deepest dent
        put("S2_Breach", decal_fan(bvh, 0.4, 50, 0.16, 7.5, 9, 0.008), m_crack)
        pet = []
        for k in range(8):
            a = k / 8 * math.tau
            b0 = proj(bvh, 0.4 + 0.16 * math.cos(a - 0.3), 50 + 7.5 * math.sin(a - 0.3), 0.008)[0]
            b1 = proj(bvh, 0.4 + 0.16 * math.cos(a + 0.3), 50 + 7.5 * math.sin(a + 0.3), 0.008)[0]
            c0, n0 = proj(bvh, 0.4, 50, 0.008)
            tip = (b0 + b1) / 2 + ((b0 + b1) / 2 - c0).normalized() * 0.04 + n0 * random.uniform(0.05, 0.1)
            bb = bmesh.new(); t = n0 * 0.006
            v = [bb.verts.new(q) for q in (b0, b1, tip, b0 - t, b1 - t, tip - t)]
            for f in ((0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)):
                bb.faces.new([v[i] for i in f])
            pet.append(bb)
        put("S2_BreachPetals", merged(pet), made["S2_Body"].material_slots[0].material)
        # shattered dome: jagged teeth left in the ring + one hanging piece
        DC = Vector((2.3, 0, 0))
        def dsph(t, p, r):
            t, p = math.radians(t), math.radians(p)
            return DC + Vector((math.cos(t), math.sin(t) * math.cos(p), math.sin(t) * math.sin(p))) * r
        def tooth(p):
            return min(87.0, 71 + 9 * tri_w(p / 12.0) + 5 * tri_w(p / 4.3 + 0.3) + 4 * math.sin(math.radians(3 * p)) + (9 if 200 < p < 240 else 0))
        rows = [[(tooth(2 * j) + v / 7 * (90 - tooth(2 * j)), 2 * j) for j in range(180)] for v in range(8)]
        gb_ = bmesh.new()
        VV = [[[gb_.verts.new(dsph(t, p, r)) for (t, p) in row] for row in rows] for r in (0.952, 0.932)]
        for s_ in (0, 1):
            for i in range(len(rows) - 1):
                for j in range(180):
                    q = [VV[s_][i][j], VV[s_][i][(j + 1) % 180], VV[s_][i + 1][(j + 1) % 180], VV[s_][i + 1][j]]
                    f = gb_.faces.new(q if s_ == 0 else q[::-1]); f.material_index = 0
        for i in (0, len(rows) - 1):
            for j in range(180):
                f = gb_.faces.new([VV[0][i][j], VV[0][i][(j + 1) % 180], VV[1][i][(j + 1) % 180], VV[1][i][j]]); f.material_index = 1
        bmesh.ops.recalc_face_normals(gb_, faces=gb_.faces)
        put("S2_DomeRemnant", gb_, MT["M_Sub_Glass"], extra=(MT.get("M_DomeShard_Edge") or m_window,))
        # barnacles (coloured) on the lower body and sponsons, weed from sponsons/skids
        cols_b = [MT.get("M_Sub_BarnaclePurple") or mat("M_Sub_BarnaclePurple", (0.36, 0.27, 0.34), rough=0.9),
                  MT.get("M_Sub_BarnaclePink") or mat("M_Sub_BarnaclePink", (0.66, 0.46, 0.4), rough=0.9),
                  MT.get("M_Sub_Barnacle") or mat("M_Sub_Barnacle", (0.72, 0.68, 0.58), rough=0.95)]
        hole = MT.get("M_Sub_BarnacleOpening") or mat("M_Sub_BarnacleOpening", (0.05, 0.03, 0.04), rough=0.6)
        groups = [[], [], []]
        for cl in range(22):
            cx = random.uniform(-2.8, 1.9); ca = random.choice((-1, 1)) * random.uniform(100, 170); tint = random.choice((0, 0, 1, 1, 2))
            for i in range(random.randint(8, 15)):
                x = cx + random.gauss(0, 0.12); a = ca + random.gauss(0, 7)
                if -0.85 < x < 0.45 and -120 < a < -60: continue
                p, n = proj(bvh, x, a, -0.003)
                if p is None: continue
                r = random.uniform(0.015, 0.045)
                b = lathe([(0, 0), (r, 0), (0.75 * r, 0.8 * r), (0.4 * r, 0.95 * r), (0.32 * r, 0.6 * r), (0, 0.55 * r)], 6)
                for f in b.faces:
                    c = f.calc_center_median(); f.material_index = 1 if (math.hypot(c.x, c.y) < 0.4 * r and c.z > 0.3 * r) else 0
                bmesh.ops.transform(b, matrix=Matrix.Translation(p) @ along(n), verts=b.verts)
                groups[tint if random.random() > 0.2 else random.randrange(3)].append(b)
        for k in range(3):
            if groups[k]:
                put(f"S2_Barnacles_{k}", merged(groups[k]), cols_b[k], extra=(hole,))
        weed = []
        for i in range(60):
            s = random.choice((-1, 1)); x = random.uniform(-2.3, 1.6)
            top = Vector((x, s * (1.42 + random.uniform(-0.2, 0.2)), -1.1)); L = random.uniform(0.15, 0.38); pts = [top]
            for k in range(1, 6):
                q = top + Vector((0.03 * math.sin(k * 1.3 + i), 0.03 * math.cos(k + i), -L * k / 5)); q.z = max(q.z, -1.5); pts.append(q)
            weed.append(tube(catmull(pts, 3), lambda u: 0.014 * (1 - 0.8 * u), sides=5))
        put("S2_Weed", merged(weed), MT.get("M_Sub_Algae") or mat("M_Sub_Algae", (0.05, 0.11, 0.03), rough=0.8), smooth=True)
        lamps_dead = MT.get("M_Sub_LampBroken")
        for nm in ("S2_Windows",):
            for sl in made[nm].material_slots: sl.material = MT["M_Sub_Crack"]

    bpy.context.view_layer.update()
    return root


def install_item(item_root, root, col, skt, sfx):
    it = bpy.data.objects[item_root]
    S = bpy.data.objects["SKT_" + skt + sfx].matrix_basis.copy()
    for c in it.children_recursive:
        if c.type != "MESH":
            continue
        d = c.copy(); d.data = c.data.copy(); d.name = f"S2_Inst_{c.name}{sfx}"
        col.objects.link(d)
        rel = it.matrix_world.inverted() @ c.matrix_world
        d.parent = root; d.matrix_parent_inverse = Matrix.Identity(4); d.matrix_basis = S @ rel


# ------------------------------------------------------------------ Mk2-specific pickups (blade + conforming hull patch)
def build_mk2_items():
    # blade
    col = get_col("Sub2PropBlade")
    old = bpy.data.objects.get("Sub2PropBlade")
    if old: bpy.data.objects.remove(old, do_unlink=True)
    b = blade_bm()
    o1 = finish(col, "S2PB_Blade", b, m_chrome, smooth=True)
    o2 = finish(col, "S2PB_Root", merged([cyl(0.045, 0.03, 20, (0, 0, -0.015)), cyl(0.03, 0.03, 16, (0, 0, 0.015))]), m_metal, smooth=True)
    make_root(col, "Sub2PropBlade", [o1, o2], (3.6, -4.6, 0.03))
    # hull patch: grid projected onto the Mk2 body at the crack spot -> exact fit
    body_bm = loft_x(BODY_ST, seg=72, samples=96)
    bvh = bvh_of(body_bm)
    F = frame_on(bvh, *CRACK); Fi = F.inverted(); n0 = F.col[0].to_3d(); Y = F.col[1].to_3d(); Z = F.col[2].to_3d(); P = F.translation
    NU, NV, TH = 10, 8, 0.012
    bm = bmesh.new(); grid = [[], []]
    for s in (0, 1):
        for i in range(NV + 1):
            row = []
            for j in range(NU + 1):
                g = P + Y * (-0.22 + 0.44 * j / NU) + Z * (-0.17 + 0.34 * i / NV)
                p, n = proj_dir(bvh, g + n0 * 0.5, -n0, 0.002 + s * TH)
                row.append(bm.verts.new(Fi @ (p if p is not None else g)))
            grid[s].append(row)
    for s in (0, 1):
        for i in range(NV):
            for j in range(NU):
                q = [grid[s][i][j], grid[s][i][j + 1], grid[s][i + 1][j + 1], grid[s][i + 1][j]]
                bm.faces.new(q if s else q[::-1])
    ring = [(0, j) for j in range(NU + 1)] + [(i, NU) for i in range(1, NV + 1)] + [(NV, j) for j in range(NU - 1, -1, -1)] + [(i, 0) for i in range(NV - 1, 0, -1)]
    for k in range(len(ring)):
        (i0, j0), (i1, j1) = ring[k], ring[(k + 1) % len(ring)]
        bm.faces.new((grid[0][i0][j0], grid[0][i1][j1], grid[1][i1][j1], grid[1][i0][j0]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    col = get_col("Sub2HullPatch")
    old = bpy.data.objects.get("Sub2HullPatch")
    if old: bpy.data.objects.remove(old, do_unlink=True)
    o1 = finish(col, "S2HP_Plate", bm, MT.get("M_Part_Steel") or m_metal, smooth=True)
    extra = []
    for (u, v) in ((-0.19, -0.14), (0.19, -0.14), (-0.19, 0.14), (0.19, 0.14), (0, -0.14), (0, 0.14)):
        g = P + Y * u + Z * v; p, n = proj_dir(bvh, g + n0 * 0.5, -n0, TH + 0.004)
        extra.append(cyl(0.015, 0.012, 6, (0, 0, 0.006), Matrix(Fi) @ Matrix.Translation(p) @ along(n)))
    o2 = finish(col, "S2HP_Bolts", merged(extra), MT.get("M_Part_Dark") or m_dark)
    hz = []
    for v in (-0.06, 0.06):
        g = P + Z * v; p, n = proj_dir(bvh, g + n0 * 0.5, -n0, TH + 0.002)
        hz.append(box((0.003, 0.44, 0.03), Fi @ p))
    o3 = finish(col, "S2HP_Stripe", merged(hz), MT.get("M_Part_Yellow") or m_hazard)
    make_root(col, "Sub2HullPatch", [o1, o2, o3], (4.4, -4.6, 0.2))


build_mk2_items()
for st in ("G", "R", "W"):
    build_mk2(st)
print("MK2", [ROOTNAME[s] for s in ("G", "W", "R")])
