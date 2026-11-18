# Submarine variants (2026-11-16): fully WRECKED (__B) and fully REPAIRED (__R) copies of Submarine + SubInterior.
# exec after mk.py in DiveGear_Scene.blend (after build_repair_parts2.py / build_interior_detail.py).
# Same pivot + same sockets as the gameplay versions -> drop-in mesh swaps in Unreal.
#   SM_Submarine_Wrecked / SM_Sub_Interior_Wrecked, SM_Submarine_Repaired / SM_Sub_Interior_Repaired
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

random.seed(7)
BASE = {"Submarine": bpy.data.objects["Submarine"], "SubInterior": bpy.data.objects["SubInterior"]}
OFFS = {"B": Vector((9.0, 0, 0)), "R": Vector((18.0, 0, 0))}
LABEL = {"B": "Wrecked", "R": "Repaired"}

M = bpy.data.materials
m_ok = mat("M_Sub_OK", (0.05, 0.85, 0.2), emit=(0.1, 1.0, 0.3), strength=6.0)
m_dead = mat("M_Sub_LampBroken", (0.03, 0.035, 0.035), metal=0.2, rough=0.35)
m_barn = mat("M_Sub_Barnacle", (0.72, 0.68, 0.58), rough=0.95)
m_algae = mat("M_Sub_Algae", (0.05, 0.11, 0.03), rough=0.8)
m_scr_broken = mat("M_SubIn_ScreenBroken", (0.015, 0.02, 0.025), rough=0.2)
m_light_off = mat("M_SubIn_LightOff", (0.45, 0.45, 0.43), rough=0.4)
m_water = mat("M_SubIn_Water", (0.02, 0.05, 0.07), rough=0.04)
m_crack, m_rust, m_metal = M["M_Sub_Crack"], M["M_Sub_Rust"], M["M_Sub_Metal"]


# ------------------------------------------------------------------ cloning
def clone(base_name, tag):
    base = BASE[base_name]
    colname = f"{base_name}_{LABEL[tag]}"
    col = get_col(colname)
    old = bpy.data.objects.get(colname)                # (get_col already cleared this variant's own objects)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    root = bpy.data.objects.new(colname, None); col.objects.link(root)
    root.matrix_world = Matrix.Translation(OFFS[tag]) @ base.matrix_world
    mp = {base: root}
    for c in base.children_recursive:
        d = c.copy()
        if c.data is not None:
            d.data = c.data.copy()
        d.name = c.name + "__" + tag
        col.objects.link(d); mp[c] = d
    for c, d in mp.items():
        if c is base:
            continue
        d.parent = mp[c.parent]; d.matrix_parent_inverse = c.matrix_parent_inverse.copy()
    return root, col


def restore(root, col, tag, name, mesh_name):
    """Gameplay sub has no dome glass since the dome-shard change; variants get the full dome back."""
    if bpy.data.objects.get(name + "__" + tag) is None and bpy.data.meshes.get(mesh_name):
        o = bpy.data.objects.new(name + "__" + tag, bpy.data.meshes[mesh_name].copy()); col.objects.link(o); o.parent = root


def get(root, name, tag):
    return bpy.data.objects.get(name + "__" + tag)


def kill(tag, *names):
    for n in names:
        o = bpy.data.objects.get(n + "__" + tag)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)


def kill_prefix(tag, prefix):
    for o in [o for o in bpy.data.objects if o.name.startswith(prefix) and o.name.endswith("__" + tag)]:
        bpy.data.objects.remove(o, do_unlink=True)


def swap_mat(o, old, new):
    for s in o.material_slots:
        if s.material and (old is None or s.material.name == old):
            s.material = new


def add(col, root, name, bm, material, smooth=False):
    o = finish(col, name, bm, material, smooth=smooth)
    o.parent = root
    return o


def merged(bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("_t"); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out


def along(n):
    return Vector(n).to_track_quat("Z", "Y").to_matrix().to_4x4()


def rot_mesh(o, pivot, R):
    o.data.transform(Matrix.Translation(pivot) @ R @ Matrix.Translation(-Vector(pivot)))


def socket_local(base_name, skt):
    base = BASE[base_name]
    return base.matrix_world.inverted() @ bpy.data.objects["SKT_" + skt].matrix_world


def install(item_root, root, col, base_name, skt, tag, extra=Matrix.Identity(4)):
    """Copy a pickup item's meshes onto a socket of the variant root."""
    it = bpy.data.objects[item_root]
    S = socket_local(base_name, skt)
    for c in it.children_recursive:
        if c.type != "MESH":
            continue
        d = c.copy(); d.data = c.data.copy(); d.name = f"SUB_Inst_{c.name}__{tag}"
        col.objects.link(d)
        rel = it.matrix_world.inverted() @ c.matrix_world
        d.parent = root; d.matrix_parent_inverse = Matrix.Identity(4)
        d.matrix_basis = S @ extra @ rel


# hull helpers (hull centre = origin, outer radius 1.15, ang from +Z toward +Y)
R_H = 1.15
DENTS = ((0.35, 48, 0.55, 0.075), (-1.25, -112, 0.45, 0.12), (1.35, 128, 0.4, 0.09), (-0.4, -45, 0.35, 0.08))   # x, ang, radius, depth (wrecked hull)
def hp_raw(x, ang, r=R_H):
    a = math.radians(ang); return Vector((x, r * math.sin(a), r * math.cos(a)))
def hp(x, ang, r=R_H):
    p = hp_raw(x, ang, r)
    for dx, da, rad, depth in DENTS:
        d = (hp_raw(x, ang) - hp_raw(dx, da)).length
        if d < rad:
            p -= hp_raw(0, ang, 1.0) * depth * 0.5 * (1 + math.cos(math.pi * d / rad))
    return p
def hn(ang):
    a = math.radians(ang); return Vector((0, math.sin(a), math.cos(a)))


def crack_bm(x, ang, size, seed):
    rnd = random.Random(seed); bms = []
    def path(x0, a0, dx_dir, n, step, w):
        pts = []; x_, a_ = x0, a0
        for i in range(n):
            pts.append(hp(x_, a_, R_H + 0.004))
            x_ += dx_dir * step * (0.7 + 0.6 * rnd.random()); a_ += math.degrees((rnd.random() - 0.5) * step * 1.4 / R_H)
        bms.append(strap(pts, hn(a0), lambda s, w=w: w * (1 - 0.7 * s), 0.004))
        return pts
    for d in (-1, 1):
        path(x, ang, d, int(6 * size) + 3, 0.05 * size, 0.022 * max(size, 1.0))
    for k in range(2):                                  # branches
        bx = x + (rnd.random() - 0.5) * 0.25 * size; ba = ang + (rnd.random() - 0.5) * 6 * size
        path(bx, ba, rnd.choice((-1, 1)), 3, 0.035 * size, 0.012 * max(size, 1.0))
    return merged(bms)


def stain_bm(x, ang, sx, sa, seed):
    rnd = random.Random(seed); bm = bmesh.new()
    ctr = bm.verts.new(hp(x, ang, R_H + 0.002)); ring = []
    for k in range(24):
        a = k / 24 * math.tau; rr = 1 + 0.25 * math.sin(3 * a + rnd.random() * 6) + 0.12 * math.sin(7 * a)
        ring.append(bm.verts.new(hp(x + sx * rr * math.cos(a), ang + sa * rr * math.sin(a), R_H + 0.002)))
    for k in range(24):
        bm.faces.new((ctr, ring[k], ring[(k + 1) % 24]))
    return bm


def streak_bm(x, ang, length, width):           # rust streak running "down" the hull from (x, ang)
    side = 1 if ang >= 0 else -1; pts = []
    for i in range(8):
        a = ang + side * math.degrees(length * i / 7 / R_H)
        pts.append(hp(x + 0.01 * math.sin(i * 1.7), a, R_H + 0.003))
    return strap(pts, Vector((0, 0, 0)) + hn(ang), lambda s: width * (1 - 0.8 * s), 0.002)


# ===================================================================== REPAIRED
rootR, colR = clone("Submarine", "R")
restore(rootR, colR, "R", "SUB_Dome", "SUB_Dome_full")
kill("R", "SUB_BladeStub", "SUB_HullCrack", "SUB_HullCrackLip", "SUB_HullStain")
kill_prefix("R", "SUB_PropBolt_"); kill_prefix("R", "SUB_LooseCable_")
for o in rootR.children_recursive:
    if o.type == "MESH":
        if o.name.startswith("SUB_Warn_"):
            swap_mat(o, "M_Sub_Warning", m_ok)
        swap_mat(o, "M_Sub_Rust", m_metal)              # cleaned / replaced pipework
install("PropBlade", rootR, colR, "Submarine", "Repair_Prop", "R")
install("HullPatch", rootR, colR, "Submarine", "Repair_Hull", "R")
install("RepairPipe", rootR, colR, "Submarine", "Repair_Pipe", "R")
install("RepairGear", rootR, colR, "Submarine", "Repair_Gear", "R", Matrix.Rotation(math.radians(-90), 4, "X"))
install("FuseModule", rootR, colR, "Submarine", "Repair_Fuse", "R", Matrix.Rotation(math.radians(-90), 4, "X"))
install("Battery", rootR, colR, "Submarine", "Repair_Battery", "R")

rootRI, colRI = clone("SubInterior", "R")
restore(rootRI, colRI, "R", "IN_DomeInner", "IN_DomeInner_full")
kill("R", "IN_Cage_Cover"); kill_prefix("R", "IN_Cage_Wire_")
for o in rootRI.children_recursive:
    if o.type == "MESH" and (o.name.startswith("IN_Warn_") or o.name.startswith("IN_PowerLamp_")):
        swap_mat(o, "M_Sub_Warning", m_ok)
install("ScrubberCartridge", rootRI, colRI, "SubInterior", "Repair_Scrubber", "R")
install("CircuitBoard", rootRI, colRI, "SubInterior", "Repair_Circuit", "R")

# ===================================================================== WRECKED
rootB, colB = clone("Submarine", "B")
restore(rootB, colB, "B", "SUB_Dome", "SUB_Dome_full")
m_hull_w = mat("M_Sub_HullWrecked", (0.6, 0.38, 0.08), metal=0.05, rough=0.75)       # faded, dirty yellow paint (rust only in patches)
m_rust_patch = mat("M_Sub_RustPatch", (0.36, 0.13, 0.04), metal=0.25, rough=0.9)      # orange-brown rust where the paint is gone
m_rust_heavy = mat("M_Sub_RustHeavy", (0.13, 0.05, 0.02), metal=0.2, rough=0.95)       # dark corrosion patches (wrecked only)
m_rust_run = mat("M_Sub_RustStreak", (0.45, 0.17, 0.05), rough=0.9)                     # orange rust runs (wrecked only)
m_metal_w = mat("M_Sub_MetalCorroded", (0.13, 0.11, 0.09), metal=0.5, rough=0.85)
for o in rootB.children_recursive:
    if o.type == "MESH":
        swap_mat(o, "M_Sub_Hull", m_hull_w); swap_mat(o, "M_Sub_Metal", m_metal_w)
        swap_mat(o, "M_Sub_InteriorWall", mat("M_Sub_InteriorWallWrecked", (0.3, 0.28, 0.22), rough=0.9))
# -- dents in the outer hull shell
hull = get(rootB, "SUB_Hull", "B")
bm = bmesh.new(); bm.from_mesh(hull.data)
bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
for (dx, dang, rad, depth) in DENTS:
    c = hp_raw(dx, dang)
    for v in bm.verts:
        r = math.hypot(v.co.y, v.co.z)
        if r < 1.12 or v.co.x < -1.9 or v.co.x > 1.95:
            continue
        d = (v.co - c).length
        if d < rad:
            f = 0.5 * (1 + math.cos(math.pi * d / rad))
            v.co -= Vector((0, v.co.y / r, v.co.z / r)) * depth * f
bm.to_mesh(hull.data); bm.free()
# -- cracks, stains, streaks
CRACKS = ((0.35, 48, 1.8), (-1.25, -112, 1.5), (1.35, 128, 1.3), (-0.4, -45, 1.2), (1.2, -62, 1.4), (-1.5, 75, 1.0), (0.9, 160, 1.1))
for i, (x, a, s) in enumerate(CRACKS):
    add(colB, rootB, f"SUB_WreckCrack_{i}__B", crack_bm(x, a, s * 0.55, 11 + i), m_crack)     # shorter cracks
def rust_spot(x, ang, sx, sa, seed, lift):
    rnd = random.Random(seed); bm = bmesh.new()
    ctr = bm.verts.new(hp(x, ang, R_H + lift)); ring = []; ph = rnd.random() * 6
    for k in range(24):
        a = k / 24 * math.tau; rr = 1 + 0.3 * math.sin(3 * a + ph) + 0.15 * math.sin(7 * a + ph * 2) + 0.08 * math.sin(13 * a)
        ring.append(bm.verts.new(hp(x + sx * rr * math.cos(a), ang + sa * rr * math.sin(a), R_H + lift)))
    for k in range(24):
        bm.faces.new((ctr, ring[k], ring[(k + 1) % 24]))
    return bm


# partial rust: spots only where rust really starts — around cracks, along hull seams, bolts/lamps, and the lower hull.
# each spot = orange rust where the paint flaked off + a dark corroded core
SPOTS = [(x, a, 0.13 * s, 7 * s) for (x, a, s) in CRACKS]                                   # around the cracks
for sx_ in (-1.6, -0.9, 0.6, 1.6):                                                           # along the seam bands
    for _ in range(5):
        SPOTS.append((sx_ + random.uniform(-0.05, 0.05), random.choice((-1, 1)) * random.uniform(30, 160), random.uniform(0.09, 0.18), random.uniform(8, 18)))
for _ in range(14):                                                                           # lower hull (where water sits)
    SPOTS.append((random.uniform(-1.8, 1.9), random.choice((-1, 1)) * random.uniform(110, 170), random.uniform(0.14, 0.28), random.uniform(8, 16)))
for _ in range(12):                                                                           # scattered on the hull sides / top
    SPOTS.append((random.uniform(-1.7, 1.9), random.choice((-1, 1)) * random.uniform(25, 110), random.uniform(0.07, 0.17), random.uniform(5, 12)))
SPOTS += [(2.05, 40, 0.09, 8), (2.05, -140, 0.1, 8), (2.05, 140, 0.08, 7), (-0.5, 18, 0.08, 7), (0.9, -20, 0.07, 6)]   # lamps / sail base
def in_bay(x, a, pad=0.0):                                    # open battery-bay hole on the port side (no hull there)
    return -0.8 - pad < x < 0.4 + pad and -112 - pad * 60 < a < -68 + pad * 60
SPOTS = [sp for sp in SPOTS if not in_bay(sp[0], sp[1], 0.12)]
outer = [rust_spot(x, a, sx, sa, 40 + i, 0.002) for i, (x, a, sx, sa) in enumerate(SPOTS)]
core = [rust_spot(x, a, sx * 0.45, sa * 0.45, 140 + i, 0.003) for i, (x, a, sx, sa) in enumerate(SPOTS)]
add(colB, rootB, "SUB_RustPatches__B", merged(outer), m_rust_patch)
add(colB, rootB, "SUB_RustCores__B", merged(core), m_rust_heavy)
streaks = [streak_bm(x + random.uniform(-0.03, 0.03), s * random.uniform(60, 120), random.uniform(0.2, 0.5), random.uniform(0.015, 0.035))
           for x in (-1.6, -1.25, -0.9, -0.3, 0.6, 1.1, 1.6) for s in (-1, 1, 1)]               # thin rust runs under seams / bolts
add(colB, rootB, "SUB_WreckStreaks__B", merged(streaks), m_rust_run)
slime = [stain_bm(random.uniform(-1.6, 1.8), random.uniform(-25, 25), random.uniform(0.08, 0.18), random.uniform(5, 10), 70 + k) for k in range(4)]
add(colB, rootB, "SUB_WreckSlime__B", merged(slime), m_algae)
# -- breach: torn hole in the deepest dent with jagged metal petals peeled outward
BX, BA = 0.35, 48
bc = hp(BX, BA, R_H + 0.012); bn = hn(BA)
bm = bmesh.new(); ctr = bm.verts.new(bc); ring = []
for k in range(18):
    a = k / 18 * math.tau; rr = 0.17 * (1 + 0.3 * math.sin(4 * a + 1) + 0.15 * math.sin(9 * a))
    ring.append(bm.verts.new(hp(BX + rr * math.cos(a), BA + math.degrees(rr * math.sin(a) / R_H), R_H + 0.012)))
for k in range(18):
    bm.faces.new((ctr, ring[k], ring[(k + 1) % 18]))
add(colB, rootB, "SUB_Breach__B", bm, m_crack)
petals = []
for k in range(9):
    a = k / 9 * math.tau + random.uniform(-0.2, 0.2); rr = 0.17 * (1 + 0.3 * math.sin(4 * a + 1))
    base0 = hp(BX + rr * math.cos(a - 0.25), BA + math.degrees(rr * math.sin(a - 0.25) / R_H), R_H + 0.012)
    base1 = hp(BX + rr * math.cos(a + 0.25), BA + math.degrees(rr * math.sin(a + 0.25) / R_H), R_H + 0.012)
    tip = (base0 + base1) / 2 + (base0 + base1 - 2 * bc).normalized() * random.uniform(0.02, 0.06) + bn * random.uniform(0.05, 0.11)
    pb = bmesh.new(); t = bn * 0.006
    v = [pb.verts.new(p) for p in (base0, base1, tip, base0 - t, base1 - t, tip - t)]
    for f in ((0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)):
        pb.faces.new([v[i] for i in f])
    petals.append(pb)
add(colB, rootB, "SUB_BreachPetals__B", merged(petals), m_hull_w)
# -- one side thruster torn off (stub + dangling cables)
kill("B", "SUB_Thruster_1", "SUB_ThrusterHub_1")
for k in range(3):
    pts = [Vector((1.0 + 0.03 * k, 1.2, 0.25)), Vector((1.05 + 0.04 * k, 1.38, 0.05)), Vector((0.98 + 0.05 * k, 1.42, -0.25 - 0.1 * k))]
    add(colB, rootB, f"SUB_TornCable_{k}__B", tube(catmull(pts, 4), 0.012, sides=6), M["M_Sub_Cable"], smooth=True)
# -- glass dome: impact point + radiating cracks (dome centre x=2.3, r=0.95)
DC = Vector((2.3, 0, 0)); DR = 0.957
def dp(t, p):
    return DC + Vector((math.cos(t), math.sin(t) * math.cos(p), math.sin(t) * math.sin(p))) * DR
t0, p0 = math.radians(48), math.radians(35)
rays = []
for k in range(13):
    ang = k / 13 * math.tau + random.uniform(-0.2, 0.2); pts = []; t, p = t0, p0
    for s in range(10):
        pts.append(dp(t, p)); t += 0.06 * math.cos(ang) + random.uniform(-0.015, 0.015); p += 0.08 * math.sin(ang) + random.uniform(-0.02, 0.02)
    nrm = (pts[0] - DC).normalized()
    rays.append(strap(pts, nrm, lambda s: 0.016 * (1 - 0.7 * s), 0.003))
for ring_r in (0.05, 0.12):
    pts = [dp(t0 + ring_r * math.cos(a), p0 + ring_r * 1.3 * math.sin(a)) for a in (k / 14 * math.tau for k in range(15))]
    rays.append(strap(pts, (dp(t0, p0) - DC).normalized(), 0.01, 0.003))
add(colB, rootB, "SUB_DomeCracks__B", merged(rays), m_crack)
bm = bmesh.new(); ctr = bm.verts.new(dp(t0, p0) + (dp(t0, p0) - DC).normalized() * 0.002); ring = []
for k in range(16):
    a = k / 16 * math.tau; rr = 0.035 * (1 + 0.35 * math.sin(5 * a))
    ring.append(bm.verts.new(dp(t0 + rr * math.cos(a), p0 + rr * 1.3 * math.sin(a)) + (dp(t0, p0) - DC).normalized() * 0.002))
for k in range(16):
    bm.faces.new((ctr, ring[k], ring[(k + 1) % 16]))
add(colB, rootB, "SUB_DomeHole__B", bm, m_crack)
# -- smashed lamps, dead warning lights, one lamp housing knocked askew
for o in rootB.children_recursive:
    if o.type == "MESH" and (o.name.startswith("SUB_Lamp_") or o.name.startswith("SUB_Warn_") or o.name.startswith("SUB_MastLight")):
        swap_mat(o, None, m_dead)
_lh = get(rootB, "SUB_LampHousing_2", "B").data.vertices; _lc = sum((v.co for v in _lh), Vector()) / len(_lh)
for n in ("SUB_LampHousing_2", "SUB_Lamp_2"):
    o = get(rootB, n, "B"); rot_mesh(o, _lc, Matrix.Rotation(math.radians(28), 4, Vector((0.3, 1, 0.4)).normalized()))
# -- bent mast
for n in ("SUB_Mast", "SUB_MastLight"):
    o = get(rootB, n, "B")
    if o:
        mn = min((v.co.z for v in bpy.data.objects["SUB_Mast"].data.vertices))
        mx = sum(v.co.x for v in bpy.data.objects["SUB_Mast"].data.vertices) / len(bpy.data.objects["SUB_Mast"].data.vertices)
        rot_mesh(o, Vector((mx, 0, mn)), Matrix.Rotation(math.radians(-38), 4, "Y") @ Matrix.Rotation(math.radians(12), 4, "X"))
# -- propeller: all blades gone, sheared stubs; one tail fin torn off; bent skid; crushed ballast
kill("B", "SUB_Blade_0", "SUB_Blade_2", "SUB_Blade_3", "SUB_Fin_2")
stub = get(rootB, "SUB_BladeStub", "B")
for k, ang in enumerate((-90, 90, 180)):
    d = stub.copy(); d.data = stub.data.copy(); d.name = f"SUB_BladeStubX_{k}__B"; colB.objects.link(d)
    d.parent = rootB; d.matrix_parent_inverse = stub.matrix_parent_inverse.copy()
    d.data.transform(Matrix.Rotation(math.radians(ang), 4, "X"))
    boss = get(rootB, "SUB_PropBoss", "B"); b2 = boss.copy(); b2.data = boss.data.copy(); b2.name = f"SUB_PropBossX_{k}__B"
    colB.objects.link(b2); b2.parent = rootB; b2.matrix_parent_inverse = boss.matrix_parent_inverse.copy(); b2.data.transform(Matrix.Rotation(math.radians(ang), 4, "X"))
sk = get(rootB, "SUB_Skid_-1", "B")
xs = [v.co.x for v in sk.data.vertices]; zs = [v.co.z for v in sk.data.vertices]
rot_mesh(sk, Vector((min(xs), sum(v.co.y for v in sk.data.vertices) / len(xs), max(zs))), Matrix.Rotation(math.radians(-7), 4, "Y"))
bl = get(rootB, "SUB_Ballast_1", "B")
cy = sum(v.co.y for v in bl.data.vertices) / len(bl.data.vertices); cz = sum(v.co.z for v in bl.data.vertices) / len(bl.data.vertices)
for v in bl.data.vertices:
    if v.co.x > 0.2:
        k = min(1.0, (v.co.x - 0.2) / 0.8)
        v.co.y = cy + (v.co.y - cy) * (1 - 0.35 * k); v.co.z = cz + (v.co.z - cz) * (1 + 0.1 * k) - 0.05 * k
# -- barnacles (lower hull, skids area) and hanging weed
# coloured barnacles: 3 shell tints (purple-grey / pinkish beige / chalky white) + dark opening at the top
BARN_COLS = [mat("M_Sub_BarnaclePurple", (0.36, 0.27, 0.34), rough=0.9),
             mat("M_Sub_BarnaclePink", (0.66, 0.46, 0.4), rough=0.9),
             m_barn]
m_barn_hole = mat("M_Sub_BarnacleOpening", (0.05, 0.03, 0.04), rough=0.6)
barn = [[], [], []]
for cl in range(24):
    cx = random.uniform(-2.0, 1.9); ca = random.choice((-1, 1)) * random.uniform(80, 170)
    tint = random.choice((0, 0, 1, 1, 2))                       # clusters share a tint, with some mixing
    for i in range(random.randint(8, 16)):
        x = cx + random.gauss(0, 0.12); a = ca + random.gauss(0, 8)
        if x < -2.0 or x > 2.0 or in_bay(x, a, 0.03): continue
        r = random.uniform(0.015, 0.045)
        prof = [(0, 0), (r, 0), (0.75 * r, 0.8 * r), (0.4 * r, 0.95 * r), (0.32 * r, 0.6 * r), (0, 0.55 * r)]
        b = lathe(prof, 6)
        for f in b.faces:                                       # crater (inner wall + floor) -> dark opening
            c = f.calc_center_median()
            f.material_index = 1 if (math.hypot(c.x, c.y) < 0.4 * r and c.z > 0.3 * r) else 0
        bmesh.ops.transform(b, matrix=Matrix.Translation(hp(x, a, R_H - 0.004)) @ along(hn(a)), verts=b.verts)
        barn[tint if random.random() > 0.2 else random.randrange(3)].append(b)
for k in range(3):
    if barn[k]:
        o = add(colB, rootB, f"SUB_Barnacles_{k}__B", merged(barn[k]), BARN_COLS[k])
        o.data.materials.append(m_barn_hole)
weed = []
for i in range(70):
    side = random.choice((-1, 1)); x = random.uniform(-1.6, 1.9)
    if i % 3 == 0:                                   # from the hull underside
        a = side * random.uniform(140, 175); top = hp(x, a, R_H - 0.01)
    else:                                            # from the ballast tanks
        top = Vector((x, side * random.uniform(1.0, 1.2), random.uniform(-1.12, -1.0)))
    L = random.uniform(0.3, 1.1); pts = [top]
    for s in range(1, 7):
        q = top + Vector((0.04 * math.sin(s * 1.3 + i), 0.03 * math.cos(s * 0.9 + i), -L * s / 6))
        q.z = max(q.z, -1.5 + 0.02 * s)                 # stays above the skid bottom (pivot) so it never pokes into the seabed
        pts.append(q)
    weed.append(tube(catmull(pts, 3), lambda s: 0.016 * (1 - 0.8 * s), sides=5))
add(colB, rootB, "SUB_Weed__B", merged(weed), m_algae, smooth=True)

# ---------------------------------------------------------------- WRECKED: shattered bow dome (only jagged teeth left in the ring)
m_glass_w = M["M_Sub_Glass"]
m_glass_edge = M.get("M_DomeShard_Edge") or mat("M_DomeShard_Edge", (0.72, 0.88, 0.9), rough=0.25, alpha=0.8)
kill("B", "SUB_Dome", "SUB_DomeCracks", "SUB_DomeHole")
GR_O, GR_I = 0.952, 0.932


def tri_w(x):
    f = x - math.floor(x); return 4 * abs(f - 0.5) - 1


def dsph(t, p, r):
    t, p = math.radians(t), math.radians(p)
    return DC + Vector((math.cos(t), math.sin(t) * math.cos(p), math.sin(t) * math.sin(p))) * r


def glass_patch(tp_rows, closed_ring):
    """Closed 2 cm glass shell over a (t, p) sample grid; faces mat 0 = glass, mat 1 = broken edge."""
    bm = bmesh.new()
    V = [[[bm.verts.new(dsph(t, p, r)) for (t, p) in row] for row in tp_rows] for r in (GR_O, GR_I)]
    nr, nc = len(tp_rows), len(tp_rows[0])
    def face(vs, mi):
        f = bm.faces.new(vs); f.material_index = mi
    jn = nc if closed_ring else nc - 1
    for s in (0, 1):
        for i in range(nr - 1):
            for j in range(jn):
                q = [V[s][i][j], V[s][i][(j + 1) % nc], V[s][i + 1][(j + 1) % nc], V[s][i + 1][j]]
                face(q if s == 0 else q[::-1], 0)
    for i in (0, nr - 1):                                    # edges along the first / last row
        for j in range(jn):
            face([V[0][i][j], V[0][i][(j + 1) % nc], V[1][i][(j + 1) % nc], V[1][i][j]], 1)
    if not closed_ring:
        for j in (0, nc - 1):
            for i in range(nr - 1):
                face([V[0][i][j], V[0][i + 1][j], V[1][i + 1][j], V[1][i][j]], 1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def tooth_edge(p):                                           # where the remaining glass ends (t from the axis, deg)
    return min(87.0, 70 + 9 * tri_w(p / 13.0) + 5 * tri_w(p / 4.7 + 0.3) + 4 * math.sin(math.radians(3 * p)) + (10 if 120 < p < 160 else 0))
NC_ = 180
ring_rows = [[(tooth_edge(360 * j / NC_) + v / 8 * (90 - tooth_edge(360 * j / NC_)), 360 * j / NC_) for j in range(NC_)] for v in range(9)]
o = add(colB, rootB, "SUB_DomeRemnant__B", glass_patch(ring_rows, True), m_glass_w)
o.data.materials.append(m_glass_edge)
# one large piece still attached at the rim, bent outward and hanging
hang_rows = []
for v in range(10):
    row = []
    for u in range(12):
        p = 205 + u * 4.0 + 3 * tri_w(v / 3.0)
        t_top = 38 + 6 * tri_w(p / 7.0)
        row.append((t_top + v / 9 * (tooth_edge(p) - 1 - t_top), p))
    hang_rows.append(row)
bmh = glass_patch(hang_rows, False)
hinge = dsph(tooth_edge(227), 227, GR_O)
axis = Vector((0, -math.sin(math.radians(227)), math.cos(math.radians(227)))).normalized()   # tangent to the rim at p=227
bmesh.ops.transform(bmh, matrix=Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(-55), 4, axis) @ Matrix.Translation(-hinge), verts=bmh.verts)
o = add(colB, rootB, "SUB_DomeHanging__B", bmh, m_glass_w)
o.data.materials.append(m_glass_edge)

# ---------------------------------------------------------------- WRECKED: wrecked propeller (crushed + torn duct, bent shaft/hub, broken blade jammed)
duct = get(rootB, "SUB_Duct", "B")
for v in duct.data.vertices:                                   # crush the upper-starboard quarter of the shroud
    ang = math.degrees(math.atan2(v.co.z, v.co.y))
    d = min(abs(ang - 55), 360 - abs(ang - 55))
    if d < 50:
        f = 0.5 * (1 + math.cos(math.pi * d / 50)); r = math.hypot(v.co.y, v.co.z)
        k = 1 - 0.22 * f
        v.co.y *= k; v.co.z *= k
        v.co.x += 0.06 * f * (1 if v.co.x > -3.3 else 0.3)
# torn gap in the shroud: remove faces in a sector, cap it with jagged torn edges
bm = bmesh.new(); bm.from_mesh(duct.data)
gone = [f for f in bm.faces if 95 < (math.degrees(math.atan2(f.calc_center_median().z, f.calc_center_median().y)) % 360) < 125]
bmesh.ops.delete(bm, geom=gone, context="FACES")
bm.to_mesh(duct.data); bm.free()
tear = []
for a0 in (95, 125):
    pts = [Vector((-3.55 + 0.5 * i / 6, 0, 0)) for i in range(7)]
    pts = [Vector((p.x, 0.70 * math.cos(math.radians(a0 + 2 * tri_w(i / 2.0))), 0.70 * math.sin(math.radians(a0 + 2 * tri_w(i / 2.0))))) for i, p in enumerate(pts)]
    tear.append(strap(pts, Vector((0, math.cos(math.radians(a0)), math.sin(math.radians(a0)))), 0.05, 0.012))
add(colB, rootB, "SUB_DuctTear__B", merged(tear), m_metal_w)
# hub + shaft bent: tilt the whole prop assembly about its root on the hull
PIV = Vector((-3.33, 0, 0)); TILT = Matrix.Rotation(math.radians(14), 4, Vector((0, 0.6, 1)).normalized())
for n in ["SUB_PropHub", "SUB_PropBoss", "SUB_BladeStub", "SUB_PropBolt_0", "SUB_PropBolt_1", "SUB_PropBolt_2"] + \
         [f"SUB_BladeStubX_{k}" for k in range(3)] + [f"SUB_PropBossX_{k}" for k in range(3)]:
    o = get(rootB, n, "B")
    if o:
        rot_mesh(o, PIV, TILT)
shaft = [Vector((-3.0, 0, 0)), Vector((-3.18, 0.0, 0.01)), Vector((-3.33, 0.0, 0.0))]
add(colB, rootB, "SUB_BentShaft__B", tube(catmull(shaft, 4), 0.035, sides=10), m_metal_w, smooth=True)
# a broken blade jammed in the torn shroud, another lying on the aft skid
if bpy.data.meshes.get("SUB_Blade_1_shape"):
    for k, Mx in enumerate((Matrix.Translation((-3.3, -0.25, 0.62)) @ Matrix.Rotation(math.radians(70), 4, "X") @ Matrix.Rotation(math.radians(25), 4, "Y"),
                            Matrix.Translation((-2.2, -0.62, -1.35)) @ Matrix.Rotation(math.radians(90), 4, "Y") @ Matrix.Rotation(math.radians(30), 4, "X"))):
        me = bpy.data.meshes["SUB_Blade_1_shape"].copy()
        me.transform(Matrix.Translation((3.42, 0, -0.30)))       # centre the blade on its own origin
        bm = bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me)
        for vv in bm.verts:                                     # snap it: tip bent over
            if vv.co.z > 0.05: vv.co.x += (vv.co.z - 0.05) * 0.6
        bmesh.ops.transform(bm, matrix=Mx, verts=bm.verts)
        add(colB, rootB, f"SUB_BrokenBlade_{k}__B", bm, m_metal_w)
# bend the remaining stabiliser fins
for n, ang in (("SUB_Fin_0", 18), ("SUB_Fin_3", -12)):
    o = get(rootB, n, "B")
    if o:
        vs = o.data.vertices; c = sum((v.co for v in vs), Vector()) / len(vs)
        rot_mesh(o, Vector((-2.75, c.y, c.z)), Matrix.Rotation(math.radians(ang), 4, "X"))

rootBI, colBI = clone("SubInterior", "B")
restore(rootBI, colBI, "B", "IN_DomeInner", "IN_DomeInner_full")
m_panel_w = mat("M_SubIn_PanelWrecked", (0.2, 0.2, 0.18), rough=0.85)
m_floor_w = mat("M_SubIn_FloorWrecked", (0.16, 0.15, 0.12), rough=0.9)
for o in rootBI.children_recursive:
    if o.type != "MESH":
        continue
    swap_mat(o, "M_SubIn_Panel", m_panel_w); swap_mat(o, "M_SubIn_Floor", m_floor_w); swap_mat(o, "M_Sub_Metal", m_metal_w)
    if o.name.startswith("IN_Screen_"):
        swap_mat(o, None, m_scr_broken)
    if o.name.startswith("IN_CeilingLight_"):
        swap_mat(o, None, m_light_off)
    if o.name.startswith(("IN_Warn_", "IN_PowerLamp_")):
        swap_mat(o, None, m_dead)
for n in ("IN_CeilingLight_1", "IN_CeilingLightFrame_1"):        # ceiling light torn loose at the front end
    rot_mesh(get(rootBI, n, "B"), Vector((0.49, 0, 1.0)), Matrix.Rotation(math.radians(58), 4, "Y"))
for k, y in enumerate((-0.04, 0.05)):
    pts = [Vector((0.95, y, 1.0)), Vector((0.85, y * 1.5, 0.75)), Vector((0.78, y, 0.58))]
    add(colBI, rootBI, f"IN_WreckWire_{k}__B", tube(catmull(pts, 4), 0.005, sides=6), M["M_Sub_Cable"], smooth=True)
cr = get(rootBI, "IN_Crate_1", "B")                                # crate tipped over
rot_mesh(cr, Vector((-0.7, -0.42, -0.7)), Matrix.Rotation(math.radians(62), 4, "Y"))
FLOOR = -0.70

for grp, xy, rz, tilt in ((("IN_D_Toolbox", "IN_D_Toolbox_Lid", "IN_D_Toolbox_Handle", "IN_D_Toolbox_Latch"), (0.05, -0.38), 25, Matrix.Rotation(math.radians(90), 4, "X")),
                         (("IN_D_Logbook", "IN_D_Logbook_Pages"), (0.35, 0.2), -40, None),
                         (("IN_D_Torch", "IN_D_Torch_Head"), (0.55, -0.15), 70, None),
                         (("IN_D_Mug", "IN_D_Mug_Handle"), (-0.25, 0.1), 15, Matrix.Rotation(math.radians(90), 4, "Y"))):
    objs = [get(rootBI, n, "B") for n in grp]; objs = [o for o in objs if o]
    if not objs: continue
    allv = [v.co.copy() for o in objs for v in o.data.vertices]; c = sum(allv, Vector()) / len(allv)
    R = Matrix.Rotation(math.radians(rz), 4, "Z") @ (tilt or Matrix.Identity(4))
    for o in objs: o.data.transform(R @ Matrix.Translation(-c))
    mn = min(v.co.z for o in objs for v in o.data.vertices)
    for o in objs: o.data.transform(Matrix.Translation((xy[0], xy[1], FLOOR - mn + 0.001)))
kill("B", "IN_D_Bungee")
puddles = []                                                       # water on the floor
for (px, py, s) in ((-0.3, -0.2, 0.35), (0.7, 0.25, 0.28), (1.45, -0.1, 0.2), (-1.2, 0.1, 0.25)):
    bm = bmesh.new(); ctr = bm.verts.new((px, py, FLOOR + 0.002)); ring = []
    for k in range(20):
        a = k / 20 * math.tau; rr = s * (1 + 0.3 * math.sin(3 * a + px * 5) + 0.15 * math.sin(7 * a))
        ring.append(bm.verts.new((px + rr * math.cos(a), max(-0.72, min(0.72, py + 0.7 * rr * math.sin(a))), FLOOR + 0.002)))
    for k in range(20):
        bm.faces.new((ctr, ring[k], ring[(k + 1) % 20]))
    puddles.append(bm)
add(colBI, rootBI, "IN_WreckPuddles__B", merged(puddles), m_water)
papers = [box((0.21, 0.297, 0.001), (0, 0, 0), Matrix.Translation((random.uniform(-1.0, 1.4), random.uniform(-0.6, 0.6), FLOOR + 0.004)) @ Matrix.Rotation(random.uniform(0, 6.28), 4, "Z"))
          for _ in range(7)]
add(colBI, rootBI, "IN_WreckPapers__B", merged(papers), M["M_SubIn_White"])
sag = [Vector((0.15, -0.71, 0.64)), Vector((0.35, -0.6, 0.1)), Vector((0.6, -0.5, -0.25)), Vector((0.85, -0.6, 0.15)), Vector((1.05, -0.71, 0.64))]
add(colBI, rootBI, "IN_WreckCable__B", tube(catmull(sag, 6), 0.02, sides=8), M["M_SubIn_Black"], smooth=True)

# ---------------------------------------------------------------- WRECKED INTERIOR: heavy damage pass
m_foam = mat("M_SubIn_Foam", (0.72, 0.6, 0.32), rough=0.95)
m_soot = mat("M_SubIn_Soot", (0.015, 0.013, 0.012), rough=1.0)
m_silt = mat("M_SubIn_Silt", (0.23, 0.18, 0.11), rough=1.0)
m_mold = mat("M_SubIn_Mold", (0.09, 0.12, 0.05), rough=0.95)
m_wline = mat("M_SubIn_WaterLine", (0.17, 0.12, 0.06), rough=0.95)
IR = 1.025                                                    # inner hull wall radius (stains sit just in front of it)


def objs_b(prefixes):
    return [o for o in rootBI.children_recursive if o.type == "MESH" and o.name.endswith("__B") and o.name[:-3].startswith(prefixes)]


def xform_group(objs, M_):
    for o in objs:
        o.data.transform(M_)


def drop_group(objs, xy, rz, tilt=None):
    if not objs: return
    allv = [v.co.copy() for o in objs for v in o.data.vertices]; c = sum(allv, Vector()) / len(allv)
    R = Matrix.Rotation(math.radians(rz), 4, "Z") @ (tilt or Matrix.Identity(4))
    xform_group(objs, R @ Matrix.Translation(-c))
    mn = min(v.co.z for o in objs for v in o.data.vertices)
    xform_group(objs, Matrix.Translation((xy[0], xy[1], FLOOR - mn + 0.001)))


def about(pivot, R):
    return Matrix.Translation(pivot) @ R @ Matrix.Translation(-Vector(pivot))


def flat_fan(center, normal, radius, seed, n=20, stretch=(1.0, 1.0)):
    rnd = random.Random(seed); nrm = Vector(normal).normalized()
    u = nrm.orthogonal().normalized(); v = nrm.cross(u)
    bm = bmesh.new(); c = bm.verts.new(center); ring = []
    ph = rnd.random() * 6
    for k in range(n):
        a = k / n * math.tau; rr = radius * (1 + 0.3 * math.sin(3 * a + ph) + 0.15 * math.sin(7 * a + ph))
        ring.append(bm.verts.new(Vector(center) + u * rr * math.cos(a) * stretch[0] + v * rr * math.sin(a) * stretch[1]))
    for k in range(n):
        bm.faces.new((c, ring[k], ring[(k + 1) % n]))
    return bm


def wall_fan(x, ang, sx, sa, seed, r=IR):                   # irregular patch conforming to the inner hull wall
    rnd = random.Random(seed); bm = bmesh.new(); c = bm.verts.new(hp_raw(x, ang, r)); ring = []
    ph = rnd.random() * 6
    for k in range(20):
        a = k / 20 * math.tau; rr = 1 + 0.3 * math.sin(3 * a + ph) + 0.15 * math.sin(7 * a)
        ring.append(bm.verts.new(hp_raw(x + sx * rr * math.cos(a), ang + sa * rr * math.sin(a), r)))
    for k in range(20):
        bm.faces.new((c, ring[k], ring[(k + 1) % 20]))
    return bm


def wall_streak(x, ang, length, width, r=IR):
    side = 1 if ang >= 0 else -1; pts = []
    for i in range(8):
        a = ang + side * math.degrees(length * i / 7 / r)
        if abs(a) > 130: break
        pts.append(hp_raw(x + 0.008 * math.sin(i * 1.9), a, r))
    if len(pts) < 2: return bmesh.new()
    return strap(pts, -hn(ang), lambda s: width * (1 - 0.75 * s), 0.002)


# -- starboard pilot seat ripped off its post, lying on the floor; port seat cushion torn open
drop_group(objs_b(("IN_SeatBack_1", "IN_SeatCushion_1")), (0.78, 0.33), 65, Matrix.Rotation(math.radians(80), 4, "X"))
foam = []
for k in range(14):
    p = Vector((random.uniform(1.15, 1.55), random.uniform(-0.55, -0.18), -0.24)) if k < 8 else Vector((random.uniform(1.0, 1.7), random.uniform(-0.6, 0.0), FLOOR + 0.02))
    s = random.uniform(0.025, 0.06)
    foam.append(box((s, s * random.uniform(0.6, 1.3), s * 0.7), (0, 0, 0), Matrix.Translation(p) @ Matrix.Rotation(random.uniform(0, 6), 4, Vector((random.random(), random.random(), 1)).normalized())))
add(colBI, rootBI, "IN_WreckFoam__B", merged(foam), m_foam)
# -- oxygen tank and fire extinguisher torn from their racks
kill("B", "IN_O2Strap_1")
drop_group(objs_b(("IN_O2Tank_1", "IN_O2TankBand_1", "IN_O2Valve_1")), (0.5, -0.5), 8, Matrix.Rotation(math.radians(90), 4, "Y"))
drop_group(objs_b(("IN_D_Ext_Body", "IN_D_Ext_Label", "IN_D_Ext_Valve", "IN_D_Ext_Lever", "IN_D_Ext_Hose", "IN_D_Ext_Nozzle", "IN_D_Ext_Band")),
           (1.65, 0.45), 75, Matrix.Rotation(math.radians(90), 4, "X"))
# -- medkit knocked off the wall, bandages spilled
drop_group(objs_b(("IN_Medkit", "IN_MedCross")), (-1.0, -0.08), 20, Matrix.Rotation(math.radians(-90), 4, "X"))
band = [cyl(0.025, 0.05, 10, (0, 0, 0), Matrix.Translation((-0.9 + random.uniform(-0.15, 0.25), random.uniform(-0.25, 0.15), FLOOR + 0.025)) @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Rotation(random.uniform(0, 3), 4, "Y"))
        for _ in range(4)]
add(colBI, rootBI, "IN_WreckBandages__B", merged(band), M["M_SubIn_White"])
# -- second ceiling light fallen to the floor, joystick snapped off, card-cage cover on the floor
drop_group(objs_b(("IN_CeilingLight_2", "IN_CeilingLightFrame_2")), (1.15, -0.03), 12, Matrix.Rotation(math.radians(8), 4, "X"))
drop_group(objs_b(("IN_JoystickStick_1", "IN_JoystickKnob_1")), (1.68, -0.32), 40, Matrix.Rotation(math.radians(90), 4, "Y"))
drop_group(objs_b(("IN_Cage_Cover",)), (1.6, -0.5), 5, Matrix.Rotation(math.radians(-25), 4, "Z"))
# -- bilge hatch thrown open, black hole under it
xform_group(objs_b(("IN_D_Bilge_",)), about((-0.8, 0.28, -0.69), Matrix.Rotation(math.radians(-105), 4, "Y")))
add(colBI, rootBI, "IN_BilgeHole__B", box((0.48, 0.38, 0.002), (-0.55, 0.28, FLOOR + 0.001)), m_crack)
# -- aft crate tipped as well, cargo straps snapped
kill("B", *[f"IN_D_CargoStrap_{i}" for i in range(3)], *[f"IN_D_CargoBuckle_{i}" for i in range(3)])
xform_group(objs_b(("IN_Crate_0",)), about((-1.11, -0.38, -0.7), Matrix.Rotation(math.radians(48), 4, "Y")))
# -- port cable tray collapsed at the front, scrubber fan hanging off
xform_group(objs_b(("IN_D_Tray_-1", "IN_D_TrayLip_-1_", "IN_D_Cable_-1_", "IN_D_TrayClamp_-1_")),
            about((-1.45, -0.71, 0.64), Matrix.Rotation(math.radians(7), 4, "Y")))
xform_group(objs_b(("IN_Scrub_Fan",)), about((0.73, -0.80, 0.21), Matrix.Rotation(math.radians(55), 4, "X")))
# -- burst ceiling pipe branch hanging down
burst = [Vector((0.25, 0.6, 0.8)), Vector((0.3, 0.58, 0.62)), Vector((0.45, 0.48, 0.3)), Vector((0.52, 0.42, 0.08))]
add(colBI, rootBI, "IN_BurstPipe__B", tube(catmull(burst, 6), 0.028, sides=10), m_metal_w, smooth=True)
add(colBI, rootBI, "IN_BurstPipeEnd__B", torus(0.032, 0.008, 12, 6, Matrix.Translation(burst[-1]) @ along(burst[-1] - burst[-2])), m_rust, smooth=True)
add(colBI, rootBI, "IN_BurstCollar__B", torus(0.05, 0.012, 14, 6, Matrix.Translation((0.25, 0.6, 0.8)) @ Matrix.Rotation(math.radians(90), 4, "Y")), m_rust, smooth=True)
# -- shattered screens, scorched console and power panel
scr = []
for k, yc in enumerate((-0.415, 0.0, 0.415)):
    c0 = Vector((1.947, yc + random.uniform(-0.06, 0.06), 0.155 + random.uniform(-0.03, 0.03)))
    for r_ in range(7):
        a = r_ / 7 * math.tau + random.uniform(-0.3, 0.3); pts = [c0]
        for s in range(1, 5):
            pts.append(c0 + Vector((0, math.cos(a) * 0.04 * s + random.uniform(-0.008, 0.008), math.sin(a) * 0.025 * s + random.uniform(-0.006, 0.006))))
        pts = [Vector((p.x, max(yc - 0.15, min(yc + 0.15, p.y)), max(0.075, min(0.235, p.z)))) for p in pts]
        scr.append(strap(pts, (-1, 0, 0), lambda s: 0.006 * (1 - 0.6 * s), 0.001))
add(colBI, rootBI, "IN_ScreenCracks__B", merged(scr), M["M_SubIn_White"])
add(colBI, rootBI, "IN_SootConsole__B", flat_fan((1.786, 0.0, -0.25), (-1, 0, 0), 0.22, 3, stretch=(1.0, 1.4)), m_soot)
add(colBI, rootBI, "IN_SootPower__B", flat_fan((-1.526, -0.28, 0.15), (1, 0, 0), 0.24, 4, stretch=(1.2, 1.0)), m_soot)
# -- the hull breach seen from inside (same spot as outside: x 0.35, starboard upper), water streak + weed
bc_in = hp_raw(0.35, 48, IR)
add(colBI, rootBI, "IN_BreachHole__B", wall_fan(0.35, 48, 0.15, 7.5, 5), m_crack)
pet = []
for k in range(8):
    a = k / 8 * math.tau + random.uniform(-0.2, 0.2)
    b0 = hp_raw(0.35 + 0.15 * math.cos(a - 0.3), 48 + 7.5 * math.sin(a - 0.3), IR - 0.002)
    b1 = hp_raw(0.35 + 0.15 * math.cos(a + 0.3), 48 + 7.5 * math.sin(a + 0.3), IR - 0.002)
    tip = (b0 + b1) / 2 + ((b0 + b1) / 2 - bc_in).normalized() * 0.03 - hn(48) * random.uniform(0.06, 0.12)
    pb = bmesh.new(); t = hn(48) * 0.005
    v = [pb.verts.new(p) for p in (b0, b1, tip, b0 + t, b1 + t, tip + t)]
    for f in ((0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)):
        pb.faces.new([v[i] for i in f])
    pet.append(pb)
add(colBI, rootBI, "IN_BreachPetals__B", merged(pet), m_metal_w)
add(colBI, rootBI, "IN_BreachStreak__B", merged([wall_streak(0.35 + dx, 56, 1.4, 0.07) for dx in (-0.08, 0.0, 0.07)]), m_wline)
wd = []
for i in range(12):
    top = hp_raw(0.35 + random.uniform(-0.12, 0.12), 48 + random.uniform(-6, 6), IR - 0.01); L = random.uniform(0.2, 0.55); pts = [top]
    for s in range(1, 6):
        pts.append(top + Vector((0.03 * math.sin(s + i), -0.04 * s / 5 - 0.02 * math.cos(s * 0.7 + i), -L * s / 5)))
    wd.append(tube(catmull(pts, 3), lambda s: 0.012 * (1 - 0.8 * s), sides=5))
add(colBI, rootBI, "IN_BreachWeed__B", merged(wd), m_algae, smooth=True)
# -- flooding line, mould, rust runs on the walls
WZ = -0.28
wl = []
for side in (-1, 1):
    ang = side * math.degrees(math.acos(WZ / IR))
    pts = [hp_raw(-1.5 + 3.5 * i / 10, ang, IR) for i in range(11)]
    wl.append(strap(pts, -hn(ang), 0.05, 0.002))
add(colBI, rootBI, "IN_WaterLine__B", merged(wl), m_wline)
mold = [wall_fan(random.uniform(-1.2, 1.8), random.choice((-1, 1)) * random.uniform(95, 125), random.uniform(0.1, 0.3), random.uniform(5, 12), 90 + k) for k in range(14)]
mold += [wall_fan(random.uniform(-1.2, 1.8), random.uniform(-40, 40), random.uniform(0.08, 0.2), random.uniform(4, 9), 120 + k) for k in range(6)]
add(colBI, rootBI, "IN_Mold__B", merged(mold), m_mold)
runs = [wall_streak(x + random.uniform(-0.04, 0.04), s * random.uniform(35, 70), random.uniform(0.4, 1.1), random.uniform(0.02, 0.05))
        for x in (-0.9, 0.47, 0.95, 1.6, -1.3, 0.1) for s in (-1, 1)]
add(colBI, rootBI, "IN_RustRuns__B", merged(runs), m_rust)
# -- silt banked along the floor edges, a few weeds growing out of it
silt = []
for k in range(22):
    sx, sy = random.uniform(0.15, 0.4), random.uniform(0.08, 0.16)
    x = random.uniform(-1.52 + sx, 1.7 - sx); y = random.choice((-1, 1)) * random.uniform(0.5, 0.7)   # stays inside the cabin
    silt.append(lathe([(0, 0.04), (0.5, 0.03), (0.85, 0.012), (1.0, 0)], 10,
                      Matrix.Translation((x, y, FLOOR + 0.001)) @ Matrix.Rotation(random.uniform(-0.3, 0.3), 4, "Z") @ Matrix.Diagonal((sx, sy, random.uniform(0.6, 1.4), 1))))
add(colBI, rootBI, "IN_Silt__B", merged(silt), m_silt, smooth=True)
gw = []
for i in range(10):
    base = Vector((random.uniform(-1.4, 1.6), random.choice((-1, 1)) * random.uniform(0.55, 0.68), FLOOR + 0.02)); L = random.uniform(0.12, 0.3)
    pts = [base + Vector((0.02 * math.sin(s * 1.4 + i), 0.015 * math.cos(s + i), L * s / 4)) for s in range(5)]
    gw.append(tube(catmull(pts, 3), lambda s: 0.01 * (1 - 0.8 * s), sides=5))
add(colBI, rootBI, "IN_FloorWeed__B", merged(gw), m_algae, smooth=True)
# -- dome glass cracked on the inside too
rays_in = []; DRi = 0.935
def dpi(t, p):
    return DC + Vector((math.cos(t), math.sin(t) * math.cos(p), math.sin(t) * math.sin(p))) * DRi
for k in range(11):
    ang = k / 11 * math.tau + random.uniform(-0.2, 0.2); pts = []; t, p = t0, p0
    for s in range(9):
        pts.append(dpi(t, p)); t += 0.06 * math.cos(ang) + random.uniform(-0.015, 0.015); p += 0.08 * math.sin(ang) + random.uniform(-0.02, 0.02)
    rays_in.append(strap(pts, (pts[0] - DC).normalized(), lambda s: 0.014 * (1 - 0.7 * s), 0.003))
add(colBI, rootBI, "IN_DomeCracks__B", merged(rays_in), m_crack)

# -- dome shattered: no inner glass face, glass fragments all over the front of the cabin
kill("B", "IN_DomeInner", "IN_DomeCracks")
frag = []
for k in range(70):
    x = random.uniform(1.15, 2.25); y = random.uniform(-0.65, 0.65)
    if 1.79 < x < 2.11 and abs(y) < 0.62:
        z = 0.012                                          # on top of the console desk
    elif 1.12 < x < 1.58 and 0.14 < abs(y) < 0.59 and y < 0:
        z = -0.25 + 0.002                                  # on the remaining (port) seat cushion
    else:
        z = FLOOR + 0.002
    s = random.uniform(0.015, 0.06) if k % 5 else random.uniform(0.07, 0.12)
    b = bmesh.new()
    for _ in range(random.randint(5, 8)):
        a = random.uniform(0, math.tau); rr = s * random.uniform(0.5, 1.0)
        b.verts.new((rr * math.cos(a), rr * math.sin(a), random.uniform(0, 0.006)))
    bmesh.ops.convex_hull(b, input=b.verts[:])
    bmesh.ops.transform(b, matrix=Matrix.Translation((x, y, z)) @ Matrix.Rotation(random.uniform(-0.25, 0.25), 4, Vector((random.random(), random.random(), 0.2)).normalized()), verts=b.verts)
    mn = min(v.co.z for v in b.verts)
    if mn < z: bmesh.ops.translate(b, vec=(0, 0, z - mn), verts=b.verts)
    frag.append(b)
add(colBI, rootBI, "IN_GlassFragments__B", merged(frag), m_glass_w)

bpy.context.view_layer.update()
print("VARIANTS", [r.name for r in (rootR, rootRI, rootB, rootBI)])
