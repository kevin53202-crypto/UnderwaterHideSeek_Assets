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
