# Weathered procedural materials + texture-baked Unreal export for static props (2026-11-18).
# exec after mk.py (uses OUT_DIR, socket conventions of export_unreal).
#   weather(mat, rust=, grime=, streak=, mold=, pit=, scale=, rough=, bump=)
#       rebuilds the material's node tree: base colour + rust blooms + pitting + vertical rust runs + grime + mould,
#       roughness and bump from the same masks. Object-space coordinates -> patterns run continuously across parts.
#   bake_export(root_name, sm_name, prefix, nobake=(), size=4096, sfx="")
#       joins the model like export_unreal, gives the baked faces one packed UV atlas, bakes BaseColor / Roughness /
#       Normal with Cycles into <OUT_DIR>/Textures/T_<prefix>_*.png, swaps those faces to one material M_<prefix>
#       wired to the textures, and writes SM_<name>.fbx (sockets included; scene-only socket suffix stripped).
#       Materials in 'nobake' (e.g. tiling seabed, translucent glass) keep their own slots and get a world-XY UV.
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

RUST_A, RUST_B = (0.42, 0.18, 0.06), (0.17, 0.075, 0.035)
MOLD = (0.16, 0.18, 0.1)


def weather(m, rust=0.5, grime=0.4, streak=0.3, mold=0.0, pit=0.5, scale=1.0, rough=0.85, bump=0.4):
    base = tuple(m.diffuse_color[:3])
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    N = nt.nodes.new; Lk = nt.links.new
    out = N("ShaderNodeOutputMaterial"); bsdf = N("ShaderNodeBsdfPrincipled"); Lk(bsdf.outputs[0], out.inputs[0])
    tc = N("ShaderNodeTexCoord"); mp = N("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale, scale, scale)
    Lk(tc.outputs["Object"], mp.inputs["Vector"]); co = mp.outputs[0]

    def noise(sc, det=6.0, rgh=0.6):
        n = N("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = sc; n.inputs["Detail"].default_value = det
        n.inputs["Roughness"].default_value = rgh; Lk(co, n.inputs["Vector"]); return n.outputs["Fac"]

    def ramp(sock, a, b):
        r = N("ShaderNodeMapRange"); r.inputs["From Min"].default_value = a; r.inputs["From Max"].default_value = b
        Lk(sock, r.inputs["Value"]); return r.outputs["Result"]

    def feed(sock, v):          # constant or link
        if isinstance(v, (int, float)): sock.default_value = v
        elif isinstance(v, tuple): sock.default_value = (*v, 1.0)
        else: Lk(v, sock)

    def mul(a, b):
        n = N("ShaderNodeMath"); n.operation = "MULTIPLY"; feed(n.inputs[0], a); feed(n.inputs[1], b); return n.outputs[0]

    def mix(fac, a, b):
        n = N("ShaderNodeMix"); n.data_type = "RGBA"   # inputs: 0 factor, 6 A colour, 7 B colour; output 2 colour
        feed(n.inputs[0], fac); feed(n.inputs[6], a); feed(n.inputs[7], b); return n.outputs[2]

    bloom = ramp(noise(1.1, 6, 0.62), 0.47, 0.62)                     # large rust blooms
    pits = ramp(noise(9.0, 8, 0.7), 0.56, 0.7)                         # small pitting spots
    wv = N("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "X"
    wv.inputs["Scale"].default_value = 3.0; wv.inputs["Distortion"].default_value = 9.0; wv.inputs["Detail"].default_value = 4.0
    rot = N("ShaderNodeMapping"); rot.inputs["Rotation"].default_value = (0.0, math.radians(90), 0.0); rot.inputs["Scale"].default_value = (1.0, 6.0, 1.0)
    Lk(co, rot.inputs["Vector"]); Lk(rot.outputs[0], wv.inputs["Vector"])
    runs = mul(ramp(wv.outputs["Fac"], 0.72, 0.95), ramp(noise(2.0, 3, 0.5), 0.45, 0.65))   # vertical rust runs, broken up
    grim = ramp(noise(3.2, 5, 0.55), 0.35, 0.75)
    mld = ramp(noise(1.8, 6, 0.6), 0.55, 0.7)
    rust_col = mix(ramp(noise(5.0, 4, 0.5), 0.3, 0.7), RUST_A, RUST_B)
    rmask = N("ShaderNodeMath"); rmask.operation = "MAXIMUM"; Lk(mul(bloom, rust), rmask.inputs[0]); Lk(mul(pits, rust * pit), rmask.inputs[1])
    c = mix(rmask.outputs[0], base, rust_col)
    c = mix(mul(runs, streak), c, RUST_A)
    c = mix(mul(grim, grime * 0.8), c, (0.05, 0.045, 0.04))          # grime darkening
    c = mix(mul(mld, mold), c, MOLD)
    Lk(c, bsdf.inputs["Base Color"])
    rr = N("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = rough; rr.inputs["To Max"].default_value = 0.97
    Lk(rmask.outputs[0], rr.inputs["Value"]); Lk(rr.outputs["Result"], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 0.0
    if bump > 0:
        hb = N("ShaderNodeMath"); hb.operation = "ADD"; Lk(pits, hb.inputs[0]); Lk(mul(bloom, 0.6), hb.inputs[1])
        bp = N("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35 * bump; bp.inputs["Distance"].default_value = 0.01
        Lk(hb.outputs[0], bp.inputs["Height"]); Lk(bp.outputs["Normal"], bsdf.inputs["Normal"])
    m.diffuse_color = (*base, 1.0)           # keep the flat viewport colour
    return m


def bake_export(root_name, sm_name, prefix, nobake=(), size=4096, sfx=""):
    root = bpy.data.objects[root_name]
    s = root.matrix_world.to_scale().x
    frame = Matrix.Translation(root.matrix_world.translation) @ root.matrix_world.to_quaternion().to_matrix().to_4x4() @ Matrix.Scale(s, 4)
    tmp = bpy.data.collections.new("_BakeTmp"); bpy.context.scene.collection.children.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get(); dups = []
    for o in root.children_recursive:
        if o.type != "MESH": continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); me.transform(frame.inverted() @ o.matrix_world)
        d = bpy.data.objects.new(o.name + "_x", me); tmp.objects.link(d); dups.append(d)
    if bpy.context.object and bpy.context.object.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for d in dups: d.select_set(True)
    bpy.context.view_layer.objects.active = dups[0]; bpy.ops.object.join()
    sm = bpy.context.active_object; sm.name = sm_name; sm.data.name = sm_name; me = sm.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    nob = {i for i, m in enumerate(me.materials) if m and m.name in nobake}
    # UV: one packed atlas for the baked faces, world-XY tiling UV for the rest
    bpy.ops.object.mode_set(mode="EDIT"); ebm = bmesh.from_edit_mesh(me)
    for f in ebm.faces: f.select_set(f.material_index not in nob)
    bmesh.update_edit_mesh(me)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.002)
    ebm = bmesh.from_edit_mesh(me); uv = ebm.loops.layers.uv.active
    for f in ebm.faces:
        if f.material_index in nob:
            for l in f.loops: l[uv].uv = (l.vert.co.x * 0.5, l.vert.co.y * 0.5)
    bmesh.update_edit_mesh(me); bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    # bake
    scn = bpy.context.scene; prev_engine = scn.render.engine
    scn.render.engine = "CYCLES"; scn.cycles.device = "CPU"; scn.cycles.samples = 1
    scn.render.bake.margin = 6; scn.render.bake.use_clear = True
    tex_dir = os.path.join(OUT_DIR, "Textures"); os.makedirs(tex_dir, exist_ok=True)
    dummy = bpy.data.images.new("_bake_dummy", 8, 8)
    imgs = {}
    for label, cs in (("BaseColor", "sRGB"), ("Roughness", "Non-Color"), ("Normal", "Non-Color")):
        im = bpy.data.images.new(f"T_{prefix}_{label}", size, size, alpha=False); im.colorspace_settings.name = cs; imgs[label] = im
    nodes = []
    for i, m in enumerate(me.materials):
        n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.name = "_bake"; m.node_tree.nodes.active = n
        nodes.append((i in nob, n))
    for label, btype in (("BaseColor", "DIFFUSE"), ("Roughness", "ROUGHNESS"), ("Normal", "NORMAL")):
        for is_nob, n in nodes:
            n.image = dummy if is_nob else imgs[label]; n.id_data.nodes.active = n
        kw = dict(pass_filter={"COLOR"}) if btype == "DIFFUSE" else (dict(normal_space="TANGENT") if btype == "NORMAL" else {})
        bpy.ops.object.bake(type=btype, **kw)
        p = os.path.join(tex_dir, f"T_{prefix}_{label}.png"); imgs[label].filepath_raw = p; imgs[label].file_format = "PNG"; imgs[label].save()
        print("BAKED", p, flush=True)
    for _, n in nodes: n.id_data.nodes.remove(n)
    bpy.data.images.remove(dummy); scn.render.engine = prev_engine
    # one baked material for the baked faces, keep the nobake slots
    bm_ = bpy.data.materials.get(f"M_{prefix}") or bpy.data.materials.new(f"M_{prefix}")
    bm_.use_nodes = True; nt = bm_.node_tree; nt.nodes.clear()
    o_ = nt.nodes.new("ShaderNodeOutputMaterial"); b_ = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b_.outputs[0], o_.inputs[0])
    def tex(label):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = imgs[label]; return n
    nt.links.new(tex("BaseColor").outputs["Color"], b_.inputs["Base Color"])
    nt.links.new(tex("Roughness").outputs["Color"], b_.inputs["Roughness"])
    nmap = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tex("Normal").outputs["Color"], nmap.inputs["Color"]); nt.links.new(nmap.outputs[0], b_.inputs["Normal"])
    b_.inputs["Metallic"].default_value = 0.0
    old = list(me.materials); keep = [old[i] for i in sorted(nob)]
    remap = {i: (0 if i not in nob else 1 + sorted(nob).index(i)) for i in range(len(old))}
    idx = [remap[p.material_index] for p in me.polygons]
    me.materials.clear(); me.materials.append(bm_)
    for m in keep: me.materials.append(m)
    for p, k in zip(me.polygons, idx): p.material_index = k
    me.uv_layers.new(name="Lightmap")
    # sockets (scene names may carry a suffix)
    socks = []
    for o in root.children_recursive:
        if o.type == "EMPTY" and o.name.startswith("SKT_"):
            nm = o.name[4:]; nm = nm[:-len(sfx)] if sfx and nm.endswith(sfx) else nm
            e = bpy.data.objects.new("SOCKET_" + nm, None); tmp.objects.link(e); e.parent = sm
            M = frame.inverted() @ o.matrix_world; e.location = M.translation; e.rotation_euler = M.to_euler(); socks.append(e)
    bpy.ops.object.select_all(action="DESELECT"); sm.select_set(True)
    for e in socks: e.select_set(True)
    path = os.path.join(OUT_DIR, sm_name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH", "EMPTY"}, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Z", axis_up="Y", use_mesh_modifiers=True,
                             mesh_smooth_type="FACE", use_tspace=True, add_leaf_bones=False, bake_anim=False, path_mode="RELATIVE")
    info = {"file": os.path.basename(path), "tris": sum(len(p.vertices) - 2 for p in me.polygons), "mats": len(me.materials),
            "size_cm": tuple(round(x * 100, 1) for x in sm.dimensions), "sockets": len(socks)}
    for e in socks: bpy.data.objects.remove(e)
    bpy.data.objects.remove(sm); bpy.data.meshes.remove(me); bpy.data.collections.remove(tmp)
    return info
