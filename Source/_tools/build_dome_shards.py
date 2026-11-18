# Bow-dome glass as collectable shards (2026-11-16). exec after mk.py in DiveGear_Scene.blend.
#  - splits the dome (centre (2.3,0,0) in Submarine-root space, axis +X, r 0.95) into N_SHARDS jagged pieces
#    (1 crown cap + 5 side pieces), each a closed 2 cm acrylic shell
#  - pickups SM_DomeShard_1..6: pivot = centre of the shard's outer surface, local +Z = inward (shard rests bowl-up)
#  - gameplay SM_Submarine / SM_Sub_Interior lose their dome glass (kept as fake-user meshes SUB_Dome_full /
#    IN_DomeInner_full); Submarine gets SOCKET_DomeShard_1..6 -> attaching shard k at socket k rebuilds the dome
import bpy, bmesh, math
from mathutils import Vector, Matrix

SUB = bpy.data.objects["Submarine"]; INT = bpy.data.objects["SubInterior"]
DC = Vector((2.3, 0, 0)); RO, RI = 0.952, 0.932
NT, NP = 36, 120                                   # grid: 2.5 deg in t (from axis), 3 deg around
N_SHARDS = 6

g_glass = bpy.data.materials.get("M_DomeGlass_Acrylic") or mat("M_DomeGlass_Acrylic", (0.55, 0.75, 0.8), rough=0.03, alpha=0.35)
g_edge = mat("M_DomeShard_Edge", (0.72, 0.88, 0.9), rough=0.25, alpha=0.8)


def tri(x):                                         # triangle wave in [-1, 1] -> sharp zig-zag like a fracture
    f = x - math.floor(x); return 4 * abs(f - 0.5) - 1


def bound(k, t):                                    # jagged meridian boundary k (degrees), k = 0..5 (5 = 0 + 360)
    kk = k % 5
    return (k * 72 + 6 * math.sin(math.radians(t * 5 + 40 * kk)) + 3.5 * tri(t / 9.0 + 0.37 * kk)
            + 1.5 * tri(t / 3.7 + 0.61 * kk))


def capb(p):                                        # jagged crown boundary (t in degrees) as a function of p
    return 27 + 3 * math.sin(math.radians(5 * p)) + 2.5 * tri(p / 14.0) + 1.0 * tri(p / 5.3 + 0.2)


def sph(t, p, r):
    t, p = math.radians(t), math.radians(p)
    return DC + Vector((math.cos(t), math.sin(t) * math.cos(p), math.sin(t) * math.sin(p))) * r


def tp_grid(pid, NU=22, NV=26, NC=120, NW=9):
    """(t, p) samples per shard on a param grid. Neighbouring shards evaluate the very same boundary curves -> seamless."""
    if pid == 1:
        rows = [[(0.0, 0.0)] * NC]
        for w in range(1, NW + 1):
            rows.append([(capb(360 * j / NC) * w / NW, 360 * j / NC) for j in range(NC)])
        return rows, True
    k = pid - 2; rows = []
    for vi in range(NV + 1):
        v = vi / NV; row = []
        for ui in range(NU + 1):
            u = ui / NU; t = 60.0
            for _ in range(4):
                p = bound(k, t) + u * (bound(k + 1, t) - bound(k, t))
                t0 = capb(p); t = t0 + v * (90 - t0)
            row.append((t, p))
        rows.append(row)
    return rows, False


def build(pid):
    """Closed acrylic shell: outer + inner surface (material 0), broken edge faces (material 1)."""
    rows, cap = tp_grid(pid)
    bm = bmesh.new()
    V = [[[bm.verts.new(sph(t, p, r)) for (t, p) in row] for row in rows] for r in (RO, RI)]
    nr = len(rows)
    def face(vs, mi, flip):
        f = bm.faces.new(list(reversed(vs)) if flip else vs); f.material_index = mi
    if cap:
        NC = len(rows[1])
        for s in (0, 1):
            pole = V[s][0][0]
            for j in range(NC):
                face([pole, V[s][1][j], V[s][1][(j + 1) % NC]], 0, s == 1)
            for i in range(1, nr - 1):
                for j in range(NC):
                    face([V[s][i][j], V[s][i + 1][j], V[s][i + 1][(j + 1) % NC], V[s][i][(j + 1) % NC]], 0, s == 1)
        for j in range(NC):                         # edge wall around the crown
            a, b = V[0][-1][j], V[0][-1][(j + 1) % NC]; c, d = V[1][-1][(j + 1) % NC], V[1][-1][j]
            face([a, c, b][:0] + [b, a, d, c], 1, False)
    else:
        nc = len(rows[0])
        for s in (0, 1):
            for i in range(nr - 1):
                for j in range(nc - 1):
                    face([V[s][i][j], V[s][i][j + 1], V[s][i + 1][j + 1], V[s][i + 1][j]], 0, s == 1)
        ring = [(0, j) for j in range(nc)] + [(i, nc - 1) for i in range(1, nr)] + \
               [(nr - 1, j) for j in range(nc - 2, -1, -1)] + [(i, 0) for i in range(nr - 2, 0, -1)]
        for q in range(len(ring)):
            (i0, j0), (i1, j1) = ring[q], ring[(q + 1) % len(ring)]
            face([V[0][i1][j1], V[0][i0][j0], V[1][i0][j0], V[1][i1][j1]], 1, False)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm

def frame_for(pid):
    rows, cap = tp_grid(pid)
    pts = [sph(t, p, 1.0) - DC for row in rows for (t, p) in row]
    c = sum(pts, Vector()).normalized()
    Z = -c
    ref = Vector((1, 0, 0)) if abs(c.x) < 0.95 else Vector((0, 0, 1))
    X = (ref - ref.dot(c) * c).normalized()
    Y = Z.cross(X)
    F = Matrix((X, Y, Z)).transposed().to_4x4(); F.translation = DC + c * RO
    return F                                          # shard frame in Submarine-root space

# ---------------------------------------------------------------- gameplay submarine: remove dome glass, add sockets
for name, keep in (("SUB_Dome", "SUB_Dome_full"), ("IN_DomeInner", "IN_DomeInner_full")):
    o = bpy.data.objects.get(name)
    if o:
        o.data.name = keep; o.data.use_fake_user = True
        bpy.data.objects.remove(o, do_unlink=True)
COL_SUB = SUB.users_collection[0]
frames = {}
for pid in range(1, N_SHARDS + 1):
    F = frame_for(pid); frames[pid] = F
    socket(COL_SUB, SUB, f"DomeShard_{pid}", F.translation, tuple(math.degrees(a) for a in F.to_euler()))

# ---------------------------------------------------------------- pickups
roots = []
for pid in range(1, N_SHARDS + 1):
    name = f"DomeShard_{pid}"
    col = get_col(name)
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    bm = build(pid)
    bmesh.ops.transform(bm, matrix=frames[pid].inverted(), verts=bm.verts)
    o1 = finish(col, f"DS{pid}_Glass", bm, g_glass, smooth=True)
    o1.data.materials.append(g_edge)
    mn = min(v.co.z for v in o1.data.vertices)
    roots.append(make_root(col, name, [o1], (-4.4 + (pid - 1) * 1.15, -4.6, -mn)))

# ---------------------------------------------------------------- whole-dome check copy (hidden): all shards at their sockets
bpy.context.view_layer.update()
print("SHARDS", [(r.name, len(r.children[0].data.polygons)) for r in roots])
