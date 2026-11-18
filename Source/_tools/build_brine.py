# Map prop: brine pool, v2 detail pass (2026-11-18). exec after mk.py in DiveGear_Scene.blend.
# A lake of dense brine in a seabed depression. Divers hide by sinking into it (submerged = hidden).
# Rim: mussel bed (smooth-edged dark bed + clumps of ridged mussels), carbonate rocks, methane-hydrate chunks,
# segmented tube worms with red plumes; white film at the shoreline; an overflow notch on +X lets brine run out
# as a short stream. Dead animals (fish, rattail, crab) around the shore and on the floor. Rippled basin floor,
# rippled brine surface with rings around the bubble vents. Two models with the same pivot:
#   BrinePool          -> SM_BrinePool          basin + rim + life + sockets
#   BrinePool_Surface  -> SM_BrinePool_Surface  the brine surface (lake + stream), for a translucent material / trigger
# Frame: pivot = surrounding seabed level (z = 0) at the lake centre. Lake ~7.2 x 4.6 m, 1.7 m deep, patch ~14 x 9.5 m.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise

MT = bpy.data.materials
POS = Vector((0, 60, 0))
RX_, RY_ = 3.6, 2.3            # lake outline semi-axes (s = 1)
ZS = 0.15                      # brine surface height
DEPTH = 1.7
NR, NA = 64, 128
BUBBLES = ((0.35, 0.8), (0.55, 3.3), (0.2, 4.9))   # (s, angle) of the gas vents

C = {}
def mats():
    C["sed"] = MT.get("M_Seabed_Sediment") or mat("M_Seabed_Sediment", (0.33, 0.31, 0.27), rough=0.95)
    C["rock"] = MT.get("M_Seabed_Rock") or mat("M_Seabed_Rock", (0.22, 0.21, 0.2), rough=0.85)
    C["basin"] = mat("M_Brine_Basin", (0.2, 0.21, 0.2), rough=0.8)
    C["bed"] = mat("M_Brine_MusselBed", (0.07, 0.06, 0.05), rough=0.45)
    C["mussel"] = mat("M_Brine_Mussel", (0.05, 0.045, 0.04), metal=0.1, rough=0.3)
    C["mussel2"] = mat("M_Brine_MusselPale", (0.32, 0.26, 0.2), rough=0.5)
    C["carb"] = mat("M_Brine_Carbonate", (0.42, 0.4, 0.34), rough=0.9)
    C["hydrate"] = mat("M_Brine_Hydrate", (0.88, 0.84, 0.66), rough=0.35)
    C["tube"] = mat("M_Brine_WormTube", (0.85, 0.82, 0.72), rough=0.6)
    C["plume"] = mat("M_Brine_WormPlume", (0.8, 0.08, 0.06), rough=0.5)
    C["fish"] = mat("M_Brine_DeadFish", (0.62, 0.6, 0.55), rough=0.6)
    C["crab"] = MT.get("M_Whale_Crab") or mat("M_Whale_Crab", (0.75, 0.32, 0.12), rough=0.5)
    C["hole"] = MT.get("M_Whale_Hole") or mat("M_Whale_Hole", (0.02, 0.015, 0.015), rough=0.9)
    C["brine"] = mat("M_Brine_Surface", (0.05, 0.16, 0.18), metal=0.3, rough=0.05, alpha=0.6)
    C["film"] = mat("M_Brine_EdgeFilm", (0.85, 0.85, 0.8), rough=0.9)
    W = {"sed": dict(rust=0.0, grime=0.5, mold=0.2, scale=0.8, bump=0.6), "rock": dict(rust=0.1, grime=0.55, mold=0.35, scale=1.5),
         "basin": dict(rust=0.15, grime=0.75, mold=0.35, scale=1.0, bump=0.6), "bed": dict(rust=0.1, grime=0.5, mold=0.3, scale=2.0),
         "mussel": dict(rust=0.15, grime=0.3, mold=0.25, scale=5.0, rough=0.4), "mussel2": dict(rust=0.2, grime=0.45, mold=0.3, scale=5.0),
         "carb": dict(rust=0.25, grime=0.6, mold=0.55, pit=0.9, scale=1.5, bump=0.8), "hydrate": dict(rust=0.1, grime=0.3, scale=3.0, rough=0.4),
         "tube": dict(rust=0.15, grime=0.55, mold=0.45, scale=3.0), "plume": dict(rust=0.0, grime=0.2), "fish": dict(rust=0.2, grime=0.7, mold=0.5, scale=3.0),
         "crab": dict(rust=0.1, grime=0.35, scale=4.0), "hole": dict(rust=0.1, grime=0.5), "film": dict(rust=0.05, grime=0.3, mold=0.2, scale=2.0)}
    if "weather" in globals():   # weathered procedural look for the bake (weather_bake.py)
        for k, prm in W.items(): weather(C[k], **prm)


def merged(bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("_t"); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out


def nz(p, sc):
    return noise.noise(Vector(p) * sc)


def outline(ph):
    return 1.0 + 0.12 * nz((math.cos(ph), math.sin(ph), 4.0), 1.3)


def to_sp(x, y):
    ph = math.atan2(y / RY_, x / RX_)
    return math.hypot(x / RX_, y / RY_) / outline(ph), ph


def from_sp(s, ph):
    k = s * outline(ph); return RX_ * k * math.cos(ph), RY_ * k * math.sin(ph)


def channel(x, y):
    """Overflow stream bed along +X: returns (inside 0..1, bed height) or (0, None)."""
    if x < RX_ * 0.85: return 0.0, None
    w = 0.38 + 0.05 * nz((x, 1, 1), 1.0); yc = 0.25 * math.sin(x * 0.9)
    t = max(0.0, 1.0 - abs(y - yc) / w)
    if t <= 0: return 0.0, None
    return t, ZS - 0.04 - 0.12 * max(0.0, (x - RX_) / RX_)


def terrain_z(x, y):
    s, ph = to_sp(x, y)
    if s < 1.0:
        z = ZS - DEPTH * (1.0 - s ** 2.5)
        z += 0.022 * math.sin(x * 5.0 + 1.5 * nz((x, y, 6.0), 0.6)) * min(1.0, (1 - s) * 4)     # sediment ripples on the floor
    elif s < 1.15:
        z = ZS + 0.30 * math.sin((s - 1.0) / 0.15 * math.pi / 2)
    elif s < 2.0:
        z = 0.45 * (1.0 - (s - 1.15) / 0.85) ** 2
    else:
        z = 0.0
    rim = min(1.0, max(0.0, 2.0 - s) * 3)
    z += (0.035 * nz((x, y, 2.0), 1.1) + 0.01 * nz((x, y, 9.0), 5.0)) * rim
    t, bed = channel(x, y)
    if bed is not None and s >= 0.97:
        z = z + (min(z, bed - 0.04) - z) * min(1.0, t * 1.6)
    return z


def grid_terrain():
    bm = bmesh.new(); rings = []
    center = bm.verts.new((0, 0, terrain_z(0, 0)))
    for r in range(1, NR + 1):
        s = 2.0 * (r / NR) ** 1.15; ring = []
        for a in range(NA):
            ph = a / NA * math.tau; x, y = from_sp(s, ph)
            ring.append(bm.verts.new((x, y, terrain_z(x, y) if r < NR else 0.0)))
        rings.append(ring)
    for a in range(NA):
        bm.faces.new((center, rings[0][a], rings[0][(a + 1) % NA])).material_index = 1
    for r in range(NR - 1):
        for a in range(NA):
            f = bm.faces.new((rings[r][a], rings[r + 1][a], rings[r + 1][(a + 1) % NA], rings[r][(a + 1) % NA]))
            f.material_index = 1 if 2.0 * ((r + 1.5) / NR) ** 1.15 < 1.0 else 0
    return bm


def bed_outer(ph):
    return 1.24 + 0.07 * nz((math.cos(ph), math.sin(ph), 9.0), 2.0)


def mussel_bed():
    """Dark bed draped on the rim with a smooth, wobbly outer edge; gap at the overflow channel."""
    bm = bmesh.new(); NB, SEG = 5, 220; ph0 = 0.42; rows = []
    for k in range(NB + 1):
        row = []
        for a in range(SEG + 1):
            ph = ph0 + (math.tau - 2 * ph0) * a / SEG; s = 0.995 + (bed_outer(ph) - 0.995) * k / NB
            x, y = from_sp(s, ph); row.append(bm.verts.new((x, y, terrain_z(x, y) + 0.012)))
        rows.append(row)
    for k in range(NB):
        for a in range(SEG):
            bm.faces.new((rows[k][a], rows[k + 1][a], rows[k + 1][a + 1], rows[k][a + 1]))
    return bm


def mussel(p, up, yaw, sc):
    """Ridged teardrop shell (umbo end narrow), standing partly upright along 'up'."""
    b = bmesh.new(); bmesh.ops.create_uvsphere(b, u_segments=7, v_segments=4, radius=1.0)
    for v in b.verts:
        x, y, z = v.co; taper = 0.5 + 0.5 * (x + 1) / 2
        ridge = 1.0 + 0.06 * math.sin((x + 1) * 9)
        v.co = Vector((x * 0.07, y * 0.032 * taper * ridge, z * 0.026 * taper * ridge))
    M = Matrix.Translation(p) @ Vector(up).to_track_quat("X", "Z").to_matrix().to_4x4() @ Matrix.Rotation(yaw, 4, "X") @ Matrix.Diagonal((sc, sc, sc, 1)) @ Matrix.Translation((0.05, 0, 0))
    bmesh.ops.transform(b, matrix=M, verts=b.verts); return b


def rock(center, size, seed, sub=2, amp=0.35):
    b = bmesh.new(); bmesh.ops.create_icosphere(b, subdivisions=sub, radius=1.0)
    for v in b.verts:
        v.co *= 1.0 + amp * nz(v.co + Vector((seed, 0, 0)), 1.4) + 0.08 * nz(v.co * 3 + Vector((0, seed, 0)), 2.0)
    bmesh.ops.transform(b, matrix=Matrix.Translation(center) @ Matrix.Diagonal((*size, 1)), verts=b.verts); return b


def tube_worm(p, h, lean, rnd):
    M = Matrix.Translation(p) @ lean.to_track_quat("Z", "Y").to_matrix().to_4x4()
    pts = [M @ Vector((0.02 * math.sin(k * 0.9), 0, h * k / 8)) for k in range(9)]
    t = tube(pts, lambda q: 0.017 + 0.004 * q + 0.003 * (math.sin(q * 50) > 0.6), sides=8)       # growth rings
    plume = []
    for k in range(8):
        a = k / 8 * math.tau + rnd.uniform(0, 0.4)
        fr = bmesh.new(); bmesh.ops.create_cone(fr, cap_ends=True, segments=4, radius1=0.01, radius2=0.002, depth=0.07)
        bmesh.ops.transform(fr, matrix=Matrix.Translation(pts[-1]) @ M.to_3x3().to_4x4() @ Matrix.Rotation(a, 4, "Z") @ Matrix.Rotation(math.radians(35), 4, "X") @ Matrix.Translation((0, 0, 0.035)), verts=fr.verts)
        plume.append(fr)
    return t, merged(plume)


def fish(p, yaw, L, seed):
    """Dead fish lying on its side: lofted body, tail fork, dorsal/pectoral fins, eye socket."""
    rnd = random.Random(seed); bm = bmesh.new(); rings = []
    sec = [(0.5, 0.0, 0.0), (0.42, 0.07, 0.12), (0.2, 0.09, 0.17), (-0.05, 0.08, 0.15), (-0.3, 0.05, 0.08), (-0.45, 0.025, 0.035)]   # x, half-thick, half-height (/L)
    for x, ht, hh in sec:
        ring = [bm.verts.new((x * L, ht * L * math.cos(a), hh * L * math.sin(a))) for a in (k / 10 * math.tau for k in range(10))]
        rings.append(ring)
    for k in range(len(rings) - 1):
        for j in range(10):
            bm.faces.new((rings[k][j], rings[k + 1][j], rings[k + 1][(j + 1) % 10], rings[k][(j + 1) % 10]))
    bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    fins = bmesh.new()
    for tri in (((-0.44, 0.0), (-0.68, 0.2), (-0.6, 0.0), (-0.68, -0.2)),          # forked tail
                ((0.1, 0.16), (-0.12, 0.27), (-0.22, 0.14)),                       # dorsal
                ((0.25, -0.06), (0.05, -0.2), (0.1, -0.04))):                      # pectoral
        vs = [fins.verts.new((x * L, 0.0, z * L)) for x, z in tri]; fins.faces.new(vs)
    bmesh.ops.solidify(fins, geom=fins.faces[:], thickness=0.004)
    out = merged([bm, fins])
    M = Matrix.Translation(p) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(math.radians(88 + rnd.uniform(-6, 6)), 4, "X")
    bmesh.ops.transform(out, matrix=M, verts=out.verts)
    eye = cyl(0.025 * L * 4, 0.01, 10, (0, 0, 0), M @ Matrix.Translation((0.38 * L, 0.075 * L, 0.03 * L)) @ Matrix.Rotation(math.radians(90), 4, "X"))
    return out, eye


def rattail(p, yaw, L):
    pts = [p + Matrix.Rotation(yaw, 3, "Z") @ Vector((-L * t, 0.08 * math.sin(t * 7), 0.04 * (1 - t))) for t in (k / 12 for k in range(13))]
    return tube(pts, lambda t: 0.05 * (1 - t) ** 1.4 + 0.004, sides=8)


def dead_crab(p, yaw):
    parts = [rock(p + Vector((0, 0, 0.035)), (0.11, 0.09, 0.04), 5, sub=1, amp=0.15)]          # upside down carapace
    Mz = Matrix.Rotation(yaw, 4, "Z")
    for s in (-1, 1):
        for k in range(4):
            a = math.radians(-50 + 30 * k)
            b0 = p + Mz @ Vector((0.05 * math.cos(a), s * 0.07, 0.06)); b1 = b0 + Mz @ Vector((0.06 * math.cos(a), s * 0.07, 0.07))
            b2 = b1 + Mz @ Vector((0.05 * math.cos(a), s * 0.02, 0.05))
            parts.append(tube([b0, b1, b2], 0.008, sides=5))        # legs curled up in the air
    return merged(parts)


def surface_bm():
    """Brine lake surface: rippled polar grid, rings around the gas vents, flat at the shore."""
    sb = bmesh.new(); NRs, NAs = 26, 128
    vents = [Vector(from_sp(s, ph)) for s, ph in BUBBLES]
    def zs(x, y, s):
        z = ZS + 0.004 * nz((x, y, 1.0), 2.5)
        for v in vents:
            d = math.hypot(x - v[0], y - v[1]); z += 0.012 * math.sin(d * 22) * math.exp(-d * 1.6)
        return ZS + (z - ZS) * min(1.0, (1.01 - s) * 6)
    c0 = sb.verts.new((0, 0, zs(0, 0, 0)))
    rings = []
    for r in range(1, NRs + 1):
        s = 1.01 * r / NRs; ring = []
        for a in range(NAs):
            x, y = from_sp(s, a / NAs * math.tau); ring.append(sb.verts.new((x, y, zs(x, y, s))))
        rings.append(ring)
    for a in range(NAs):
        sb.faces.new((c0, rings[0][a], rings[0][(a + 1) % NAs]))
    for r in range(NRs - 1):
        for a in range(NAs):
            sb.faces.new((rings[r][a], rings[r + 1][a], rings[r + 1][(a + 1) % NAs], rings[r][(a + 1) % NAs]))
    left, right = [], []
    for k in range(41):   # overflow stream, ends inside the patch, tapering out
        x = RX_ * 0.92 + k * (RX_ * 0.9) / 40; yc = 0.25 * math.sin(x * 0.9); w = 0.3 * (1 - 0.85 * (k / 40) ** 1.5)
        bed = channel(x, yc)[1] or ZS; z = min(ZS, bed + 0.01) + 0.006 * math.sin(k * 1.7)
        left.append(sb.verts.new((x, yc - w, z))); right.append(sb.verts.new((x, yc + w, z)))
    for k in range(40):
        sb.faces.new((left[k], left[k + 1], right[k + 1], right[k]))
    return sb


def build():
    rnd = random.Random(31)
    for nm in ("BrinePool", "BrinePool_Surface"):
        get_col(nm); old = bpy.data.objects.get(nm)
        if old: bpy.data.objects.remove(old, do_unlink=True)
    col = get_col("BrinePool", clear=False); scol = get_col("BrinePool_Surface", clear=False)
    root = bpy.data.objects.new("BrinePool", None); col.objects.link(root); root.location = POS
    sroot = bpy.data.objects.new("BrinePool_Surface", None); scol.objects.link(sroot); sroot.location = POS

    def put(name, bm, mats_, r=root, c=col, smooth=True):
        mats_ = mats_ if isinstance(mats_, (list, tuple)) else [mats_]
        o = finish(c, "BP_" + name, bm, mats_[0], smooth=smooth)
        for m in mats_[1:]: o.data.materials.append(m)
        o.parent = r; return o

    put("Terrain", grid_terrain(), [C["sed"], C["basin"]])
    put("MusselBed", mussel_bed(), C["bed"])

    # mussel clumps on the bed (dense near the shore), a few pale ones
    dark, pale = [], []
    for c in range(70):
        ph = rnd.uniform(0.45, math.tau - 0.45); s = 1.0 + (bed_outer(ph) - 1.0) * rnd.random() ** 1.3
        cx, cy = from_sp(s, ph)
        for _ in range(rnd.randint(9, 16)):
            x, y = cx + rnd.gauss(0, 0.07), cy + rnd.gauss(0, 0.07)
            if channel(x, y)[0] > 0.05: continue
            z = terrain_z(x, y) + 0.008
            up = Vector((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), 1.0))
            (pale if rnd.random() < 0.1 else dark).append(mussel(Vector((x, y, z)), up, rnd.uniform(0, math.tau), rnd.uniform(0.75, 1.25)))
    put("Mussels", merged(dark), C["mussel"])
    put("MusselsPale", merged(pale), C["mussel2"])

    # carbonate rocks on the outer rim, hydrate chunks at the shore
    rocks = []
    for i in range(9):
        ph = rnd.uniform(0.5, math.tau - 0.5); s = rnd.uniform(1.3, 1.7); x, y = from_sp(s, ph); sz = rnd.uniform(0.25, 0.6)
        rocks.append(rock(Vector((x, y, terrain_z(x, y) + sz * 0.15)), (sz, sz * rnd.uniform(0.6, 0.9), sz * 0.45), 40 + i))
    put("Carbonate", merged(rocks), C["carb"])
    hyd = []
    for i in range(12):
        ph = rnd.uniform(0.5, math.tau - 0.5); s = rnd.uniform(0.92, 1.08); x, y = from_sp(s, ph); sz = rnd.uniform(0.06, 0.16)
        hyd.append(rock(Vector((x, y, max(terrain_z(x, y), ZS - 0.1) + sz * 0.1)), (sz * 1.4, sz, sz * 0.6), 70 + i, sub=1, amp=0.3))
    put("Hydrate", merged(hyd), C["hydrate"])

    # tube-worm clumps
    tubes, plumes = [], []
    for k in range(7):
        ph = k / 7 * math.tau + 0.45; cx, cy = from_sp(1.3, ph)
        if channel(cx, cy)[0] > 0: continue
        for _ in range(16):
            x, y = cx + rnd.uniform(-0.25, 0.25), cy + rnd.uniform(-0.25, 0.25)
            lean = Vector((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), 1)).normalized()
            t, pl = tube_worm(Vector((x, y, terrain_z(x, y) - 0.02)), rnd.uniform(0.25, 0.75), lean, rnd)
            tubes.append(t); plumes.append(pl)
    put("WormTubes", merged(tubes), C["tube"])
    put("WormPlumes", merged(plumes), C["plume"])

    # dead animals
    fs, eyes = [], []
    for i, (s, ph, L) in enumerate(((1.05, 0.9, 0.42), (1.1, 2.6, 0.35), (0.85, 4.2, 0.5), (1.08, 5.4, 0.3), (0.7, 1.8, 0.38), (0.5, 3.0, 0.45))):
        x, y = from_sp(s, ph); f_, e_ = fish(Vector((x, y, terrain_z(x, y) + 0.03)), rnd.uniform(0, math.tau), L, i); fs.append(f_); eyes.append(e_)
    x, y = from_sp(0.6, 5.9); fs.append(rattail(Vector((x, y, terrain_z(x, y) + 0.04)), 0.7, 0.7))
    put("DeadFish", merged(fs), C["fish"])
    put("DeadFishEyes", merged(eyes), C["hole"])
    x, y = from_sp(1.02, 3.9); put("DeadCrab", dead_crab(Vector((x, y, terrain_z(x, y))), 1.1), C["crab"])

    # white film where the brine meets the shore
    film = bmesh.new(); inner, outer = [], []
    for a in range(NA):
        ph = a / NA * math.tau
        for lst, s in ((inner, 0.985), (outer, 1.03 + 0.012 * nz((math.cos(ph), math.sin(ph), 12.0), 3.0))):
            x, y = from_sp(s, ph); lst.append(film.verts.new((x, y, max(terrain_z(x, y), ZS) + 0.004)))
    for a in range(NA):
        film.faces.new((inner[a], outer[a], outer[(a + 1) % NA], inner[(a + 1) % NA]))
    put("EdgeFilm", film, C["film"], smooth=False)

    put("Surface", surface_bm(), C["brine"], r=sroot, c=scol)

    # sockets (root-local)
    def sock(name, loc):
        e = bpy.data.objects.new("SKT_" + name + "__BP", None); col.objects.link(e)
        e.empty_display_type = "ARROWS"; e.empty_display_size = 0.3; e.parent = root; e.location = loc
    sock("Hide_Brine", (0, 0, terrain_z(0, 0) + 0.1))
    sock("Surface_Center", (0, 0, ZS))
    x, y = from_sp(1.12, math.pi / 2 + 0.3); sock("Interact_Enter", (x, y, terrain_z(x, y) + 0.3))
    sock("Overflow", (RX_ * 1.05, 0.25 * math.sin(RX_ * 1.05 * 0.9), ZS))
    for i, (s, ph) in enumerate(BUBBLES):
        x, y = from_sp(s, ph); sock(f"Bubbles_{i + 1}", (x, y, terrain_z(x, y)))
    bpy.context.view_layer.update()


def export_all():
    """Socket names carry a scene-only suffix; strip it while exporting."""
    root = bpy.data.objects["BrinePool"]; mine = [o for o in root.children if o.name.startswith("SKT_")]
    parked = []
    for o in mine:
        plain = o.name[:-4]; other = bpy.data.objects.get(plain)
        if other: other.name = plain + "__park"; parked.append((other, plain))
        o.name = plain
    try:
        terrain = bake_export("BrinePool", "SM_BrinePool", "BrinePool", size=4096) if "bake_export" in globals() else export_unreal("BrinePool", "SM_BrinePool", (0, 0, 0))
        return [terrain, export_unreal("BrinePool_Surface", "SM_BrinePool_Surface", (0, 0, 0))]   # translucent surface: not baked
    finally:
        for o in mine: o.name = o.name + "__BP"
        for other, plain in parked: other.name = plain


mats()
build()
print("BRINE built")
