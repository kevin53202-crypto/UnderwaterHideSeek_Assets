# Steps around the v2 monster builders (exec in Blender after mk.py, rig.py, horror.py, horror2.py).
#   uv_prep()   - after build_gigantura_v2.py / build_eel_v2.py: unwrap the bodies, then save the scene.
#   (bake)      - blender -b --factory-startup --python bake_textures.py -- DiveGear_Scene.blend SK_Gigantura_Body Gigantura 4096
#                 blender -b --factory-startup --python bake_textures.py -- DiveGear_Scene.blend SK_DeepSeaEel_Body DeepSeaEel 4096
#   finalize()  - swap to the baked materials, triangulate, export SK_*.fbx.
import bpy, bmesh, math

MONSTERS = [("SK_Gigantura_Body", "Gigantura_Rig", "SK_Gigantura", "M_Gigantura", "GigX"),
            ("SK_DeepSeaEel_Body", "DeepSeaEel_Rig", "SK_DeepSeaEel", "M_DeepSeaEel", "EelX"),
            ("SK_Kraken_Body", "Kraken_Rig", "SK_Kraken", "M_Kraken", "KrX"),
            ("SK_GiantIsopod_Body", "GiantIsopod_Rig", "SK_GiantIsopod", "M_GiantIsopod", "IsX"),
            ("SK_Diver_Body", "Diver_Rig", "SK_Diver", "M_Diver", "DvX")]


def uv_prep(only=None):
    for body_name, *_ in MONSTERS:
        if only and body_name not in only: continue
        o = bpy.data.objects[body_name]
        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
        bpy.ops.object.mode_set(mode="OBJECT")
    for m in bpy.data.materials:                      # keep the procedural source materials
        if any(t in m.name for t in ("GigX", "EelX", "KrX", "IsX", "DvX")):
            m.use_fake_user = True


def baked_material(name, prefix):
    """Principled material wired to Textures/T_<prefix>_BaseColor/Normal/Roughness/Emissive.png."""
    import os
    tex = os.path.join(OUT_DIR, "Textures")
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    def img(label, cs):
        p = os.path.join(tex, f"T_{prefix}_{label}.png")
        im = bpy.data.images.load(p, check_existing=True); im.reload(); im.colorspace_settings.name = cs
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = im; return n
    nt.links.new(img("BaseColor", "sRGB").outputs["Color"], b.inputs["Base Color"])
    nt.links.new(img("Roughness", "Non-Color").outputs["Color"], b.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(img("Normal", "Non-Color").outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], b.inputs["Normal"])
    nt.links.new(img("Emissive", "sRGB").outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 1.0
    b.inputs["Specular IOR Level"].default_value = 0.55
    return m


def finalize(only=None):
    out = {}
    for body_name, rig_name, sk, baked, tag in MONSTERS:
        if only and body_name not in only: continue
        o = bpy.data.objects[body_name]
        mat = baked_material(baked, sk[3:])
        o.data.materials.clear(); o.data.materials.append(mat)
        for p in o.data.polygons: p.material_index = 0
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
        bm.to_mesh(o.data); bm.free()
        out[sk] = export_skeletal(bpy.data.objects[rig_name], sk, with_anims=True)
    return out


def bake_monster(body_name, prefix, size=4096, uv_scale=None, rig_name=None):
    """Generic version of build_isopod_v3.bake_and_export (2026-11-20): smart-project UVs, optional per-material texel
    scale (uv_scale = {material name: factor}), bake BaseColor (x baked AO) / Normal / Roughness / Emissive in the rest
    pose into Textures/T_<prefix>_*.png, then finalize (swap to M_<prefix>, export SK_<prefix>.fbx with all actions)."""
    import os, numpy as np
    uv_prep([body_name])
    o = bpy.data.objects[body_name]; rig_ = bpy.data.objects[rig_name] if rig_name else o.parent
    rig_.data.pose_position = "REST"
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    if uv_scale:
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.average_islands_scale()
        bm = bmesh.from_edit_mesh(o.data); uvl = bm.loops.layers.uv.active
        SC = {i: uv_scale.get(m.name, 1.0) for i, m in enumerate(o.data.materials)}
        for f in bm.faces:
            for l in f.loops: l[uvl].uv *= SC[f.material_index]
        bmesh.update_edit_mesh(o.data)
        bpy.ops.uv.pack_islands(rotate=True, margin=0.002)
        bpy.ops.object.mode_set(mode="OBJECT")
    scn = bpy.context.scene; scn.render.engine = "CYCLES"; scn.cycles.device = "CPU"
    scn.render.bake.margin = 8; scn.render.bake.use_clear = True
    if scn.world: scn.world.light_settings.distance = 0.25
    out_dir = os.path.join(OUT_DIR, "Textures"); os.makedirs(out_dir, exist_ok=True)
    passes = [("BaseColor", "DIFFUSE", "sRGB"), ("Normal", "NORMAL", "Non-Color"), ("Roughness", "ROUGHNESS", "Non-Color"),
              ("Emissive", "EMIT", "sRGB"), ("AO", "AO", "Non-Color")]
    imgs = {l: bpy.data.images.new(f"T_{prefix}_{l}", size, size, alpha=False) for l, _, _ in passes}
    for l, _, cs in passes: imgs[l].colorspace_settings.name = cs
    nodes = []
    for s in o.material_slots:
        n = s.material.node_tree.nodes.new("ShaderNodeTexImage"); n.name = "_bake"; s.material.node_tree.nodes.active = n; nodes.append(n)
    for l, bt, _ in passes:
        scn.cycles.samples = 16 if bt == "AO" else 4
        for n in nodes: n.image = imgs[l]; n.id_data.nodes.active = n
        kw = dict(pass_filter={"COLOR"}) if bt == "DIFFUSE" else (dict(normal_space="TANGENT") if bt == "NORMAL" else {})
        bpy.ops.object.bake(type=bt, **kw); print("BAKED", l, flush=True)
    for n in nodes: n.id_data.nodes.remove(n)
    px = size * size * 4
    b = np.empty(px, np.float32); imgs["BaseColor"].pixels.foreach_get(b)
    a = np.empty(px, np.float32); imgs["AO"].pixels.foreach_get(a)
    b = b.reshape(-1, 4); b[:, :3] *= 0.5 + 0.5 * a.reshape(-1, 4)[:, :1]
    imgs["BaseColor"].pixels.foreach_set(b.ravel())
    for l in ("BaseColor", "Normal", "Roughness", "Emissive"):
        p = os.path.join(out_dir, f"T_{prefix}_{l}.png"); imgs[l].filepath_raw = p; imgs[l].file_format = "PNG"; imgs[l].save()
    bpy.data.images.remove(imgs["AO"])
    rig_.data.pose_position = "POSE"
    return finalize([body_name])
