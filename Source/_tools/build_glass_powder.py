# Glass powder pile (2026-11-16): alternative collectable for rebuilding the bow dome (instead of / besides the 6 shards).
# exec after mk.py. A low mound of fine glass powder with visible grains (irregular crystal-like chunks) and a few flat chips.
# Pivot = bottom centre. ~28 cm across, ~9 cm high.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler

random.seed(21)
m_fine = mat("M_GlassPowder_Fine", (0.86, 0.9, 0.92), rough=0.7, alpha=0.95)
m_grain = mat("M_GlassPowder_Grain", (0.42, 0.7, 0.78), metal=0.0, rough=0.04, alpha=0.5)
m_chip = mat("M_GlassPowder_Chip", (0.55, 0.78, 0.82), rough=0.04, alpha=0.35)

RP, HP = 0.13, 0.075                                      # pile radius / height


def height(r, a):
    if r >= RP: return 0.0
    base = HP * (1 - (r / RP) ** 2) ** 1.3
    return base * (1 + 0.12 * math.sin(3 * a + 1) + 0.08 * math.sin(7 * a))


def merged(bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("_t"); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out


# --- fine powder mound (polar grid, bumpy)
bm = bmesh.new(); NR, NA = 14, 40
centre = bm.verts.new((0, 0, height(0, 0)))
rings = []
for i in range(1, NR + 1):
    r = RP * 1.08 * i / NR; ring = []
    for j in range(NA):
        a = j / NA * math.tau
        rr = r * (1 + 0.06 * math.sin(5 * a + i) if i == NR else 1)
        z = height(rr, a) + (random.uniform(-0.003, 0.003) if i < NR else 0.0)
        ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), max(0.0, z))))
    rings.append(ring)
for j in range(NA):
    bm.faces.new((centre, rings[0][j], rings[0][(j + 1) % NA]))
for i in range(NR - 1):
    for j in range(NA):
        bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % NA], rings[i][(j + 1) % NA]))
bot = bm.verts.new((0, 0, 0))
for j in range(NA):                                        # close the bottom
    bm.faces.new((rings[-1][(j + 1) % NA], rings[-1][j], bot))
fine = bm


def grain(size, flat=1.0):
    """Irregular convex crystal: hull of random points on a squashed ellipsoid."""
    b = bmesh.new()
    sx, sy, sz = size * random.uniform(0.7, 1.3), size * random.uniform(0.7, 1.3), size * random.uniform(0.5, 1.0) * flat
    for _ in range(random.randint(7, 10)):
        v = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))).normalized()
        b.verts.new((v.x * sx, v.y * sy, v.z * sz))
    bmesh.ops.convex_hull(b, input=b.verts[:])
    for f in [f for f in b.faces if not f.is_valid]:
        pass
    return b


grains, chips = [], []
# grains sitting on the pile surface
for k in range(320):
    r = RP * math.sqrt(random.random()) * 0.98; a = random.uniform(0, math.tau)
    s = random.choice((0.004, 0.006, 0.008, 0.011, 0.015)) * random.uniform(0.8, 1.2)
    g = grain(s)
    M = Matrix.Translation((r * math.cos(a), r * math.sin(a), height(r, a) + s * 0.25)) @ Euler(
        (random.uniform(0, 6.28), random.uniform(0, 6.28), random.uniform(0, 6.28))).to_matrix().to_4x4()
    bmesh.ops.transform(g, matrix=M, verts=g.verts); grains.append(g)
# grains spilled around the pile
for k in range(70):
    r = random.uniform(RP * 1.0, RP * 1.7); a = random.uniform(0, math.tau)
    s = random.uniform(0.003, 0.009)
    g = grain(s)
    bmesh.ops.transform(g, matrix=Matrix.Translation((r * math.cos(a), r * math.sin(a), s * 0.45)) @ Euler(
        (random.uniform(0, 6.28), random.uniform(0, 6.28), random.uniform(0, 6.28))).to_matrix().to_4x4(), verts=g.verts)
    grains.append(g)
# flat glass chips (crushed pane fragments) poking out of the pile
for k in range(14):
    r = RP * math.sqrt(random.random()) * 0.85; a = random.uniform(0, math.tau)
    s = random.uniform(0.014, 0.026)
    c = grain(s, flat=0.18)
    tilt = Euler((random.uniform(-0.7, 0.7), random.uniform(-0.7, 0.7), random.uniform(0, 6.28))).to_matrix().to_4x4()
    bmesh.ops.transform(c, matrix=Matrix.Translation((r * math.cos(a), r * math.sin(a), height(r, a) + s * 0.2)) @ tilt, verts=c.verts)
    chips.append(c)

for b in grains + chips:                                   # nothing below the ground plane (pivot)
    mn = min(v.co.z for v in b.verts)
    if mn < 0:
        bmesh.ops.translate(b, vec=(0, 0, -mn), verts=b.verts)

col = get_col("GlassPowder")
old = bpy.data.objects.get("GlassPowder")
if old:
    bpy.data.objects.remove(old, do_unlink=True)
o1 = finish(col, "GP_Fine", fine, m_fine, smooth=True)
o2 = finish(col, "GP_Grains", merged(grains), m_grain, smooth=False)
o3 = finish(col, "GP_Chips", merged(chips), m_chip, smooth=False)
root = make_root(col, "GlassPowder", [o1, o2, o3], (2.6, -4.6, 0.0))
bpy.context.view_layer.update()
print("GLASS_POWDER", [(o.name, len(o.data.polygons)) for o in (o1, o2, o3)])
