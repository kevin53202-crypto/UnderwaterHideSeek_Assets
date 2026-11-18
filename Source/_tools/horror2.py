# v2 monster helpers: ray fins, needle teeth, body-profile attributes and cleaner deep-sea shaders.
# exec after mk.py, rig.py, horror.py
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(1e-9, ab.dot(ab))))
    return (p - (a + ab * t)).length, t


def surface_slash(points, w0, n=6):
    """points: 3D points along the surface (already on the skin). Returns sub-segments (A, B, w0, t0, t1)."""
    out = []
    for j in range(len(points) - 1):
        out.append((Vector(points[j]), Vector(points[j + 1]), w0, j / (len(points) - 1), (j + 1) / (len(points) - 1)))
    return out


def gash_mask_py(p, slashes):
    """slashes: list of (A, B, width, t0, t1). Returns 0..1 (1 = centre of a cut)."""
    best = 0.0
    for a, b, w0, t0, t1 in slashes:
        d, t = seg_dist(p, a, b)
        t = t0 + (t1 - t0) * t
        w = w0 * math.sqrt(max(0.0, 4 * t * (1 - t)))
        if w < 1e-6:
            continue
        best = max(best, 1.0 - smoothstep(0.35, 1.0, d / w))
    return best


def wrinkle_bm(bm, amp=0.002, sc=60, seed=1):
    """Push bmesh verts along their normals by noise."""
    bm.normal_update(); off = Vector((seed, seed * 2, seed * 3))
    for v in bm.verts:
        v.co += v.normal * amp * noise.noise(v.co * sc + off)
    return bm


def uvsphere(r, m=None, u=16, v=10):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    return xf(bm, m) if m else bm


def needle(r, L, at, tilt_x, tilt_y, bend=0.3, segs=8):
    """Thin curved needle tooth growing along +Z, then rotated and moved to `at`."""
    bm = bmesh.new()
    rings = []
    n = 7
    for i in range(n + 1):
        t = i / n
        rad = r * (1 - t) ** 0.8 + r * 0.03
        z = L * t
        yo = bend * L * t * t
        rings.append([bm.verts.new((rad * math.cos(k / segs * math.tau), yo + rad * math.sin(k / segs * math.tau), z)) for k in range(segs)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(segs):
            bm.faces.new((r0[k], r0[(k + 1) % segs], r1[(k + 1) % segs], r1[k]))
    bm.faces.new(list(reversed(rings[0])))
    tip = bm.verts.new((0, bend * L * 1.02, L * 1.02))
    for k in range(segs):
        bm.faces.new((rings[-1][k], rings[-1][(k + 1) % segs], tip))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return xf(bm, T(*at) @ RX(tilt_x) @ RY(tilt_y))


def ray_fin(base, tips, thick, m, rows=6, ray_every=2, scallop=0.07, tears=(), ray_r=None):
    """Membrane fin in the local (u, v) plane at x = 0 (normal = local X), mapped with matrix m.
    base, tips: equal-length lists of (u, v). Returns (membrane_bm, rays_bm)."""
    N = len(base)
    tips = [Vector(t) for t in tips]; base = [Vector(b) for b in base]
    tip2 = []
    for i in range(N):
        t = tips[i]
        if i % ray_every and 0 < i < N - 1:                 # membrane sags between rays
            t = base[i] + (t - base[i]) * (1 - scallop)
        for c, depth in tears:                              # torn notches
            if abs(i - c) <= 1:
                t = base[i] + (t - base[i]) * (1 - depth * (1 - 0.5 * abs(i - c)))
        tip2.append(t)
    bm = bmesh.new()
    grid_t, grid_b = [], []
    for i in range(N):
        ct, cb = [], []
        for r in range(rows + 1):
            s = r / rows
            p = base[i] + (tip2[i] - base[i]) * s
            th = thick * (1 - 0.8 * s) / 2
            ct.append(bm.verts.new((th, p.x, p.y))); cb.append(bm.verts.new((-th, p.x, p.y)))
        grid_t.append(ct); grid_b.append(cb)
    for i in range(N - 1):
        for r in range(rows):
            bm.faces.new((grid_t[i][r], grid_t[i + 1][r], grid_t[i + 1][r + 1], grid_t[i][r + 1]))
            bm.faces.new((grid_b[i][r + 1], grid_b[i + 1][r + 1], grid_b[i + 1][r], grid_b[i][r]))
    for i in range(N - 1):                                   # base + tip edges
        bm.faces.new((grid_b[i][0], grid_b[i + 1][0], grid_t[i + 1][0], grid_t[i][0]))
        bm.faces.new((grid_t[i][rows], grid_t[i + 1][rows], grid_b[i + 1][rows], grid_b[i][rows]))
    for r in range(rows):                                    # first/last columns
        bm.faces.new((grid_t[0][r], grid_t[0][r + 1], grid_b[0][r + 1], grid_b[0][r]))
        bm.faces.new((grid_b[N - 1][r], grid_b[N - 1][r + 1], grid_t[N - 1][r + 1], grid_t[N - 1][r]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    xf(bm, m)
    rays = bmesh.new()
    rr = ray_r or thick * 0.75
    for i in range(0, N, ray_every):
        pts = [Vector((0, (base[i] + (tip2[i] - base[i]) * s).x, (base[i] + (tip2[i] - base[i]) * s).y)) for s in (0, 0.33, 0.66, 0.97)]
        part = tube(pts, lambda s: rr * (1 - 0.8 * s), up=(1, 0, 0), sides=5)
        tmp = bpy.data.meshes.new("_ray"); part.to_mesh(tmp); part.free(); rays.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    xf(rays, m)
    return bm, rays


def resample(poly, n):
    """Resample a 2D polyline to n evenly spaced points."""
    P = [Vector(p) for p in poly]
    L = [0.0]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + (b - a).length)
    out = []
    for k in range(n):
        d = L[-1] * k / (n - 1)
        for j in range(len(P) - 1):
            if L[j] <= d <= L[j + 1] + 1e-9:
                t = (d - L[j]) / max(1e-9, L[j + 1] - L[j]); out.append(P[j] + (P[j + 1] - P[j]) * t); break
    return out


def set_profile_attr(obj, name, fn):
    """Store a per-vertex FLOAT_VECTOR attribute computed by fn(co) -> (x, y, z)."""
    me = obj.data
    a = me.attributes.get(name) or me.attributes.new(name, "FLOAT_VECTOR", "POINT")
    for v in me.vertices:
        a.data[v.index].vector = fn(v.co)


# ---------------- shader node helpers on top of horror.NB ----------------
def nb_attr(nb, name):
    a = nb.n("ShaderNodeAttribute", attribute_name=name)
    sep = nb.n("ShaderNodeSeparateXYZ"); nb.L(a.outputs["Vector"], sep.inputs[0])
    return sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]


def nb_map(nb, x, a, b, c=0.0, d=1.0, clamp=True):
    r = nb.n("ShaderNodeMapRange", clamp=clamp); nb.L(x, r.inputs["Value"])
    r.inputs["From Min"].default_value = a; r.inputs["From Max"].default_value = b
    r.inputs["To Min"].default_value = c; r.inputs["To Max"].default_value = d
    return r.outputs[0]


def nb_seg_mask(nb, P, a, b, w0, t0=0.0, t1=1.0):
    """1 at the centre of a tapered cut from a to b (object space), 0 outside."""
    a = Vector(a); b = Vector(b); ab = b - a
    sub = nb.n("ShaderNodeVectorMath", operation="SUBTRACT"); nb.L(P, sub.inputs[0]); sub.inputs[1].default_value = a
    dot = nb.n("ShaderNodeVectorMath", operation="DOT_PRODUCT"); nb.L(sub.outputs[0], dot.inputs[0]); dot.inputs[1].default_value = ab
    t = nb.math("MULTIPLY", dot.outputs["Value"], 1.0 / ab.dot(ab))          # clamped 0..1
    sc = nb.n("ShaderNodeVectorMath", operation="SCALE"); sc.inputs[0].default_value = ab; nb.L(t, sc.inputs["Scale"])
    q = nb.n("ShaderNodeVectorMath", operation="ADD"); nb.L(sc.outputs[0], q.inputs[0]); q.inputs[1].default_value = a
    dist = nb.n("ShaderNodeVectorMath", operation="DISTANCE"); nb.L(P, dist.inputs[0]); nb.L(q.outputs[0], dist.inputs[1])
    t = nb.math("ADD", nb.math("MULTIPLY", t, t1 - t0, clamp=False), t0)
    tt = nb.math("MULTIPLY", nb.math("MULTIPLY", t, nb.math("SUBTRACT", 1.0, t)), 4.0)
    w = nb.math("MULTIPLY", nb.math("POWER", tt, 0.5), w0, clamp=False)
    ratio = nb.math("DIVIDE", dist.outputs["Value"], nb.math("MAXIMUM", w, 1e-5, clamp=False), clamp=False)
    return nb_map(nb, ratio, 0.35, 1.0, 1.0, 0.0)


def nb_warp(nb, amount, scale=30.0):
    """Object coordinates jittered by noise (ragged edges)."""
    n = nb.noise(scale, 3, 0.6)
    off = nb.n("ShaderNodeVectorMath", operation="SUBTRACT"); nb.L(n.outputs["Color"], off.inputs[0]); off.inputs[1].default_value = (0.5, 0.5, 0.5)
    sc = nb.n("ShaderNodeVectorMath", operation="SCALE"); nb.L(off.outputs[0], sc.inputs[0]); sc.inputs["Scale"].default_value = amount
    add = nb.n("ShaderNodeVectorMath", operation="ADD"); nb.L(nb.obj, add.inputs[0]); nb.L(sc.outputs[0], add.inputs[1])
    return add.outputs[0]


def nb_dot_row(nb, s, y, s_row, spacing, radius, s_scale, y_lo, y_hi, phase=0.0):
    """Row of round spots along y at body-angle sin = s_row (photophores / pores)."""
    fy = nb.math("FRACT", nb.math("ADD", nb.math("MULTIPLY", y, 1.0 / spacing, clamp=False), phase, clamp=False), clamp=False)
    dy = nb.math("SUBTRACT", fy, 0.5, clamp=False)
    ds = nb.math("DIVIDE", nb.math("SUBTRACT", s, s_row, clamp=False), s_scale, clamp=False)
    d = nb.math("SQRT", nb.math("ADD", nb.math("MULTIPLY", dy, dy, clamp=False), nb.math("MULTIPLY", ds, ds, clamp=False), clamp=False), clamp=False)
    spot = nb_map(nb, d, radius * 0.55, radius, 1.0, 0.0)
    rng = nb.math("MULTIPLY", nb.math("GREATER_THAN", y, y_lo), nb.math("LESS_THAN", y, y_hi))
    return nb.math("MULTIPLY", spot, rng)


def nb_finish_full(nb, color, rough, height, bump=0.4, dist=0.01, emit=None, emit_strength=1.0, spec=0.5):
    nb.L(color, nb.bsdf.inputs["Base Color"])
    if isinstance(rough, float): nb.bsdf.inputs["Roughness"].default_value = rough
    else: nb.L(rough, nb.bsdf.inputs["Roughness"])
    if height is not None:
        b = nb.n("ShaderNodeBump", Strength=bump, Distance=dist); nb.L(height, b.inputs["Height"]); nb.L(b.outputs[0], nb.bsdf.inputs["Normal"])
    if emit is not None:
        if isinstance(emit, tuple): nb.bsdf.inputs["Emission Color"].default_value = (*emit, 1)
        else: nb.L(emit, nb.bsdf.inputs["Emission Color"])
        nb.bsdf.inputs["Emission Strength"].default_value = emit_strength
    nb.bsdf.inputs["Specular IOR Level"].default_value = spec


def simple_shader(mat, color, rough, noise_scale=20.0, var=0.25, bump=0.2, emit=None, emit_strength=0.0, veins=None):
    """Solid colour with soft variation (+ optional dark veins)."""
    nb = NB(mat)
    n = nb.noise(noise_scale, 5, 0.6)
    lo = tuple(c * (1 - var) for c in color); hi = tuple(min(1.0, c * (1 + var)) for c in color)
    c = nb.ramp(n.outputs["Fac"], [(0.25, lo), (0.75, hi)]).outputs[0]
    h = n.outputs["Fac"]
    if veins:
        v = nb.noise(veins[0], 4, 0.5, distortion=3.0)
        vm = nb.ramp(v.outputs["Fac"], [(0.485, (0, 0, 0)), (0.5, (1, 1, 1)), (0.515, (0, 0, 0))]).outputs[0]
        c = nb.mix(c, veins[1], nb.math("MULTIPLY", vm, veins[2]))
        h = nb.math("ADD", h, nb.math("MULTIPLY", vm, 0.4), clamp=False)
    nb_finish_full(nb, c, rough, h, bump=bump, dist=0.005, emit=emit, emit_strength=emit_strength)
    mat.diffuse_color = (*color, 1)
