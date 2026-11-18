# Horror-detail helpers: modulated lofts, distance-based fish weights, displacement, procedural skin shaders.
# exec after mk.py and rig.py.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise


def loft_fn(stations, n, radial=None):
    """Like rig.loft, but radial(y, angle, x, z) -> extra radius scale (1.0 = none).
    stations: (y, hx, hz, zc); angle 0 = +X side, pi/2 = top."""
    bm = bmesh.new(); rings = []
    for (y, hx, hz, zc) in stations:
        if hx < 1e-5 and hz < 1e-5:
            rings.append([bm.verts.new((0, y, zc))]); continue
        ring = []
        for k in range(n):
            a = k / n * math.tau
            x, z = hx * math.cos(a), hz * math.sin(a)
            s = radial(y, a, x, z) if radial else 1.0
            ring.append(bm.verts.new((x * s, y, zc + z * s)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1:
            for k in range(n): bm.faces.new((r0[0], r1[k], r1[(k + 1) % n]))
        elif len(r1) == 1:
            for k in range(n): bm.faces.new((r0[(k + 1) % n], r0[k], r1[0]))
        else:
            for k in range(n): bm.faces.new((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def smooth_stations(key_stations, count):
    """Resample (y, hx, hz, zc) keys with Catmull-Rom into `count` stations (keeps pole ends)."""
    P = [Vector(s) for s in key_stations]
    P2 = [P[0]] + P + [P[-1]]
    out = []
    seg = len(P) - 1
    for i in range(count):
        u = i / (count - 1) * seg
        j = min(int(u), seg - 1); t = u - j
        p0, p1, p2, p3 = P2[j], P2[j + 1], P2[j + 2], P2[j + 3]
        v = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
        out.append((v.x, max(0.0, v.y), max(0.0, v.z), v.w))
    out[0] = key_stations[0]; out[-1] = key_stations[-1]
    return out


def subdivide_displace(obj, levels=1, lumps=0.01, lump_scale=4.0, wrinkle=0.003, wrinkle_scale=40.0, seed=0):
    """Subdivide and push vertices along normals with layered noise (applied into the mesh)."""
    if levels:
        m = obj.modifiers.new("Sub", "SUBSURF"); m.levels = m.render_levels = levels
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
        old = obj.data; obj.modifiers.clear(); obj.data = me
        if old.users == 0: bpy.data.meshes.remove(old)
    me = obj.data
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    for v in me.vertices:
        p = v.co * lump_scale + off
        d = lumps * noise.noise(p) + wrinkle * noise.noise(v.co * wrinkle_scale + off)
        v.co += v.normal * d
    me.update()
    me.shade_smooth()


def distance_weights(mesh_obj, arm_obj, bone_names, falloff=4.0, top=2):
    """Smooth weights from distance to bone segments (robust for tube-like fish bodies)."""
    bones = [arm_obj.data.bones[n] for n in bone_names]
    groups = {n: (mesh_obj.vertex_groups.get(n) or mesh_obj.vertex_groups.new(name=n)) for n in bone_names}
    segs = [(Vector(b.head_local), Vector(b.tail_local)) for b in bones]
    inv = arm_obj.matrix_world.inverted() @ mesh_obj.matrix_world
    for v in mesh_obj.data.vertices:
        p = inv @ v.co
        ds = []
        for (a, b), n in zip(segs, bone_names):
            ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / max(1e-9, ab.dot(ab))))
            ds.append(((p - (a + ab * t)).length + 1e-4, n))
        ds.sort()
        sel = ds[:top]
        ws = [1.0 / d ** falloff for d, _ in sel]; tot = sum(ws)
        for (d, n), w in zip(sel, ws):
            groups[n].add([v.index], w / tot, "REPLACE")


def blend_region(mesh_obj, group_name, test):
    """Blend vertices toward a group by test(co) -> 0..1 (scales other weights down)."""
    g = mesh_obj.vertex_groups.get(group_name) or mesh_obj.vertex_groups.new(name=group_name)
    for v in mesh_obj.data.vertices:
        w = test(v.co)
        if w <= 0: continue
        for gg in list(v.groups):
            if gg.group != g.index:
                mesh_obj.vertex_groups[gg.group].add([v.index], gg.weight * (1 - w), "REPLACE")
        g.add([v.index], w, "REPLACE")


def flesh_shader(mat, base=(0.2, 0.01, 0.02)):
    """Wet, veiny mucous-membrane flesh (mouth lining, wounds)."""
    nb = NB(mat)
    m = nb.noise(18.0, 6, 0.6)
    col = nb.ramp(m.outputs["Fac"], [(0.0, tuple(c * 0.35 for c in base)), (0.55, base), (1.0, tuple(min(1, c * 1.9 + 0.05) for c in base))])
    v = nb.noise(12.0, 4, 0.5, distortion=3.5)
    veins = nb.ramp(v.outputs["Fac"], [(0.47, (0, 0, 0)), (0.5, (1, 1, 1)), (0.53, (0, 0, 0))])
    c = nb.mix(col.outputs[0], (0.03, 0.0, 0.01), nb.math("MULTIPLY", veins.outputs[0], 0.8))
    ridges = nb.noise(60.0, 3, 0.5, vec=nb.mapping(scale=(4, 0.3, 4)))
    h = nb.math("ADD", nb.math("MULTIPLY", ridges.outputs["Fac"], 0.7), nb.math("MULTIPLY", veins.outputs[0], 0.5), clamp=False)
    rough = nb.n("ShaderNodeMapRange", clamp=True); nb.L(m.outputs["Fac"], rough.inputs["Value"])
    rough.inputs["To Min"].default_value = 0.05; rough.inputs["To Max"].default_value = 0.25
    nb.finish(c, rough.outputs[0], h, bump_strength=0.7)
    mat.diffuse_color = (*base, 1)


def gig_skin_shader(mat, S, wound_center, wound_radius):
    """Diseased, veiny, scaled skin with crusted sores and a ragged open wound."""
    nb = NB(mat)
    mott = nb.noise(2.2, 8, 0.6)
    base = nb.ramp(mott.outputs["Fac"], [(0.0, (0.02, 0.018, 0.026)), (0.5, (0.07, 0.055, 0.07)), (0.72, (0.2, 0.17, 0.16)), (0.85, (0.34, 0.3, 0.26))])
    sep = nb.n("ShaderNodeSeparateXYZ"); nb.L(nb.obj, sep.inputs[0])
    belly = nb.n("ShaderNodeMapRange", clamp=True); nb.L(sep.outputs["Z"], belly.inputs["Value"])
    belly.inputs["From Min"].default_value = 0.02; belly.inputs["From Max"].default_value = -0.25
    c = nb.mix(base.outputs[0], (0.36, 0.33, 0.28), belly.outputs[0])
    vn = nb.noise(6.0, 4, 0.5, distortion=3.0)
    veins = nb.ramp(vn.outputs["Fac"], [(0.47, (0, 0, 0)), (0.5, (1, 1, 1)), (0.53, (0, 0, 0))])
    vn2 = nb.noise(16.0, 3, 0.5, distortion=2.0)
    veins2 = nb.ramp(vn2.outputs["Fac"], [(0.485, (0, 0, 0)), (0.5, (1, 1, 1)), (0.515, (0, 0, 0))])
    vmask = nb.math("MAXIMUM", veins.outputs[0], nb.math("MULTIPLY", veins2.outputs[0], 0.6))
    c = nb.mix(c, (0.32, 0.01, 0.03), nb.math("MULTIPLY", vmask, 0.85))
    sc = nb.voronoi(110.0, "DISTANCE_TO_EDGE", vec=nb.mapping(scale=(1, 0.6, 1)))
    scales = nb.ramp(sc.outputs["Distance"], [(0.0, (0.35, 0.35, 0.35)), (0.08, (1, 1, 1))])
    c = nb.mix(c, scales.outputs[0], 1.0, "MULTIPLY")
    sore_v = nb.voronoi(9.0, "F1")
    sores = nb.ramp(sore_v.outputs["Distance"], [(0.0, (1, 1, 1)), (0.07, (1, 1, 1)), (0.1, (0, 0, 0))])
    sore_n = nb.noise(3.0, 2)
    sore_mask = nb.math("MULTIPLY", sores.outputs[0], nb.math("GREATER_THAN", sore_n.outputs["Fac"], 0.55))
    c = nb.mix(c, (0.38, 0.28, 0.08), sore_mask)
    # ragged wound: distance to centre warped by noise
    dist = nb.n("ShaderNodeVectorMath", operation="DISTANCE"); nb.L(nb.obj, dist.inputs[0]); dist.inputs[1].default_value = wound_center
    wn = nb.noise(9.0, 6, 0.7)
    warped = nb.math("ADD", dist.outputs["Value"], nb.math("MULTIPLY", nb.math("SUBTRACT", wn.outputs["Fac"], 0.5, clamp=False), wound_radius * 0.9, clamp=False), clamp=False)
    def band(lo, hi):
        r = nb.n("ShaderNodeMapRange", clamp=True); nb.L(warped, r.inputs["Value"])
        r.inputs["From Min"].default_value = lo; r.inputs["From Max"].default_value = hi
        r.inputs["To Min"].default_value = 1.0; r.inputs["To Max"].default_value = 0.0
        return r.outputs[0]
    wound = band(wound_radius * 0.75, wound_radius)
    wcore = band(wound_radius * 0.3, wound_radius * 0.6)
    bruise = band(wound_radius * 1.0, wound_radius * 1.6)
    c = nb.mix(c, (0.1, 0.03, 0.06), nb.math("MULTIPLY", bruise, 0.7))
    c = nb.mix(nb.mix(c, (0.42, 0.04, 0.04), wound), (0.06, 0.0, 0.0), wcore)
    wet = nb.math("MAXIMUM", nb.math("MAXIMUM", vmask, wound), sore_mask)
    rough = nb.n("ShaderNodeMapRange", clamp=True); nb.L(wet, rough.inputs["Value"])
    rough.inputs["To Min"].default_value = 0.42; rough.inputs["To Max"].default_value = 0.12
    wr = nb.noise(40.0, 6, 0.6, vec=nb.mapping(scale=(1, 0.35, 1)))
    h = nb.math("ADD", nb.math("MULTIPLY", wr.outputs["Fac"], 0.5), nb.math("MULTIPLY", scales.outputs[0], 0.25), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", vmask, 0.6), clamp=False)
    h = nb.math("SUBTRACT", h, nb.math("MULTIPLY", wcore, 0.8), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", sore_mask, 0.5), clamp=False)
    nb.finish(c, rough.outputs[0], h, bump_strength=0.65)
    mat.diffuse_color = (0.08, 0.06, 0.07, 1)


def eel_skin_shader(mat):
    nb = NB(mat)
    mott = nb.noise(3.0, 8, 0.62)
    base = nb.ramp(mott.outputs["Fac"], [(0.0, (0.012, 0.008, 0.016)), (0.55, (0.045, 0.025, 0.045)), (0.75, (0.2, 0.1, 0.12)), (0.88, (0.42, 0.26, 0.26))])
    scar_n = nb.noise(4.0, 3, 0.5, distortion=1.5, vec=nb.mapping(scale=(3, 0.4, 3)))
    scars = nb.ramp(scar_n.outputs["Fac"], [(0.49, (0, 0, 0)), (0.5, (1, 1, 1)), (0.51, (0, 0, 0))])
    c = nb.mix(base.outputs[0], (0.5, 0.36, 0.34), nb.math("MULTIPLY", scars.outputs[0], 0.7))
    vn = nb.noise(9.0, 4, 0.5, distortion=3.0)
    veins = nb.ramp(vn.outputs["Fac"], [(0.48, (0, 0, 0)), (0.5, (1, 1, 1)), (0.52, (0, 0, 0))])
    c = nb.mix(c, (0.28, 0.0, 0.04), nb.math("MULTIPLY", veins.outputs[0], 0.6))
    pores_v = nb.voronoi(140.0, "F1")
    pores = nb.ramp(pores_v.outputs["Distance"], [(0.0, (1, 1, 1)), (0.12, (0, 0, 0))])
    c = nb.mix(c, (0.0, 0.0, 0.0), nb.math("MULTIPLY", pores.outputs[0], 0.8))
    rough = nb.n("ShaderNodeMapRange", clamp=True); nb.L(mott.outputs["Fac"], rough.inputs["Value"])
    rough.inputs["To Min"].default_value = 0.12; rough.inputs["To Max"].default_value = 0.35
    wr = nb.noise(55.0, 6, 0.6, vec=nb.mapping(scale=(1, 0.25, 1)))
    h = nb.math("ADD", nb.math("MULTIPLY", wr.outputs["Fac"], 0.6), nb.math("MULTIPLY", veins.outputs[0], 0.5), clamp=False)
    h = nb.math("SUBTRACT", h, nb.math("MULTIPLY", pores.outputs[0], 0.6), clamp=False)
    h = nb.math("ADD", h, nb.math("MULTIPLY", scars.outputs[0], 0.4), clamp=False)
    nb.finish(c, rough.outputs[0], h, bump_strength=0.6)
    mat.diffuse_color = (0.05, 0.03, 0.05, 1)


def eel_pouch_shader(mat):
    nb = NB(mat)
    mott = nb.noise(5.0, 6, 0.6)
    base = nb.ramp(mott.outputs["Fac"], [(0.0, (0.14, 0.03, 0.05)), (0.6, (0.32, 0.1, 0.12)), (1.0, (0.5, 0.25, 0.25))])
    vn = nb.noise(7.0, 5, 0.55, distortion=4.0)
    veins = nb.ramp(vn.outputs["Fac"], [(0.47, (0, 0, 0)), (0.5, (1, 1, 1)), (0.53, (0, 0, 0))])
    vn2 = nb.noise(20.0, 4, 0.5, distortion=3.0)
    veins2 = nb.ramp(vn2.outputs["Fac"], [(0.49, (0, 0, 0)), (0.5, (1, 1, 1)), (0.51, (0, 0, 0))])
    vm = nb.math("MAXIMUM", veins.outputs[0], nb.math("MULTIPLY", veins2.outputs[0], 0.7))
    c = nb.mix(base.outputs[0], (0.05, 0.0, 0.02), vm)
    folds = nb.noise(30.0, 4, 0.5, vec=nb.mapping(scale=(3, 0.3, 0.3)))
    h = nb.math("ADD", nb.math("MULTIPLY", folds.outputs["Fac"], 0.6), nb.math("MULTIPLY", vm, 0.7), clamp=False)
    nb.finish(c, 0.18, h, bump_strength=0.55)
    mat.diffuse_color = (0.3, 0.08, 0.1, 1)


def sick_eye_shader(mat, base=(0.55, 0.5, 0.36), emit=0.25):
    """Yellowed, blood-shot, cloudy eyeball."""
    nb = NB(mat)
    cl = nb.noise(14.0, 5, 0.6)
    col = nb.ramp(cl.outputs["Fac"], [(0.3, tuple(c * 0.7 for c in base)), (0.7, base), (1.0, tuple(min(1, c * 1.25) for c in base))])
    v = nb.noise(25.0, 4, 0.5, distortion=4.0)
    veins = nb.ramp(v.outputs["Fac"], [(0.485, (0, 0, 0)), (0.5, (1, 1, 1)), (0.515, (0, 0, 0))])
    c = nb.mix(col.outputs[0], (0.45, 0.02, 0.03), veins.outputs[0])
    nb.finish(c, 0.08, veins.outputs[0], bump_strength=0.2, emit=c, emit_strength=emit)
    mat.diffuse_color = (*base, 1)


# ---------------- procedural shader building ----------------
class NB:
    """Tiny node-tree builder."""
    def __init__(self, mat):
        mat.use_nodes = True
        self.nt = mat.node_tree; self.nt.nodes.clear(); self.x = 0
        self.out = self.n("ShaderNodeOutputMaterial")
        self.bsdf = self.n("ShaderNodeBsdfPrincipled")
        self.L(self.bsdf.outputs[0], self.out.inputs["Surface"])
        co = self.n("ShaderNodeTexCoord")
        self.obj = co.outputs["Object"]

    def n(self, t, **kw):
        node = self.nt.nodes.new(t); node.location = (self.x, 0); self.x -= 40
        for k, v in kw.items():
            if k in node.inputs: node.inputs[k].default_value = v
            else: setattr(node, k, v)
        return node

    def L(self, a, b): self.nt.links.new(a, b)

    def noise(self, scale, detail=6, rough=0.55, distortion=0.0, vec=None, w=None):
        t = self.n("ShaderNodeTexNoise", Scale=scale, Detail=detail, Roughness=rough, Distortion=distortion)
        self.L(vec or self.obj, t.inputs["Vector"]); return t

    def voronoi(self, scale, feature="F1", vec=None, rand=1.0):
        t = self.n("ShaderNodeTexVoronoi", Scale=scale, feature=feature, Randomness=rand)
        self.L(vec or self.obj, t.inputs["Vector"]); return t

    def ramp(self, inp, stops):
        r = self.n("ShaderNodeValToRGB"); cr = r.color_ramp
        while len(cr.elements) > len(stops): cr.elements.remove(cr.elements[-1])
        while len(cr.elements) < len(stops): cr.elements.new(0.5)
        for e, (pos, col) in zip(cr.elements, stops):
            e.position = pos; e.color = col if len(col) == 4 else (*col, 1)
        self.L(inp, r.inputs["Fac"]); return r

    def mix(self, a, b, fac, blend="MIX"):
        m = self.n("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        if isinstance(fac, (int, float)): m.inputs[0].default_value = fac
        else: self.L(fac, m.inputs[0])
        if isinstance(a, tuple): m.inputs[6].default_value = (*a, 1) if len(a) == 3 else a
        else: self.L(a, m.inputs[6])
        if isinstance(b, tuple): m.inputs[7].default_value = (*b, 1) if len(b) == 3 else b
        else: self.L(b, m.inputs[7])
        return m.outputs[2]

    def math(self, op, a, b=None, clamp=True):
        m = self.n("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (int, float)): m.inputs[i].default_value = v
            else: self.L(v, m.inputs[i])
        return m.outputs[0]

    def mapping(self, scale=(1, 1, 1), loc=(0, 0, 0)):
        m = self.n("ShaderNodeMapping"); m.inputs["Scale"].default_value = scale; m.inputs["Location"].default_value = loc
        self.L(self.obj, m.inputs["Vector"]); return m.outputs[0]

    def sphere_mask(self, center, radius, soft=0.5):
        """1 inside a sphere around `center` (object space), soft edge."""
        sub = self.n("ShaderNodeVectorMath", operation="DISTANCE")
        self.L(self.obj, sub.inputs[0]); sub.inputs[1].default_value = center
        r = self.n("ShaderNodeMapRange", clamp=True)
        self.L(sub.outputs["Value"], r.inputs["Value"])
        r.inputs["From Min"].default_value = radius * (1 - soft); r.inputs["From Max"].default_value = radius
        r.inputs["To Min"].default_value = 1.0; r.inputs["To Max"].default_value = 0.0
        return r.outputs[0]

    def finish(self, color, rough, height, bump_strength=0.5, emit=None, emit_strength=0.0):
        self.L(color, self.bsdf.inputs["Base Color"])
        if isinstance(rough, float): self.bsdf.inputs["Roughness"].default_value = rough
        else: self.L(rough, self.bsdf.inputs["Roughness"])
        b = self.n("ShaderNodeBump", Strength=bump_strength, Distance=0.02)
        self.L(height, b.inputs["Height"]); self.L(b.outputs[0], self.bsdf.inputs["Normal"])
        if emit is not None:
            self.L(emit, self.bsdf.inputs["Emission Color"]); self.bsdf.inputs["Emission Strength"].default_value = emit_strength
        self.bsdf.inputs["Specular IOR Level"].default_value = 0.6
