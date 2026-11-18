# Background bake of one character into a single texture set (BaseColor / Normal / Roughness / Emissive).
# blender -b --factory-startup --python bake_textures.py -- <scene.blend> <mesh object> <prefix> <size>
# Writes <assets>/Textures/T_<prefix>_<Pass>.png. The scene file is NOT modified.
import bpy, os, sys

argv = sys.argv[sys.argv.index("--") + 1:]
src, obj_name, prefix, size = argv[0], argv[1], argv[2], int(argv[3])
bpy.ops.wm.open_mainfile(filepath=src)
out_dir = os.path.join(os.path.dirname(os.path.dirname(src)), "Textures")
os.makedirs(out_dir, exist_ok=True)

scn = bpy.context.scene
scn.render.engine = "CYCLES"
scn.cycles.device = "CPU"
scn.cycles.samples = 4
scn.render.bake.margin = 8
scn.render.bake.use_clear = True

obj = bpy.data.objects[obj_name]
if obj.parent and obj.parent.type == "ARMATURE":
    obj.parent.data.pose_position = "REST"          # bake the bind pose
for o in bpy.context.view_layer.objects:
    o.select_set(False)
obj.hide_set(False); obj.hide_render = False
obj.select_set(True)
bpy.context.view_layer.objects.active = obj

passes = [("BaseColor", "DIFFUSE", "sRGB"), ("Normal", "NORMAL", "Non-Color"),
          ("Roughness", "ROUGHNESS", "Non-Color"), ("Emissive", "EMIT", "sRGB")]
images = {}
for label, _, cs in passes:
    img = bpy.data.images.new(f"T_{prefix}_{label}", size, size, alpha=False, float_buffer=False)
    img.colorspace_settings.name = cs
    images[label] = img

# one image node per material, all pointing at the pass being baked
nodes = []
for slot in obj.material_slots:
    m = slot.material
    if not m: continue
    m.use_nodes = True
    n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.name = "_bake"
    m.node_tree.nodes.active = n
    nodes.append(n)

for label, btype, _ in passes:
    for n in nodes:
        n.image = images[label]
        n.id_data.nodes.active = n
    kw = {}
    if btype == "DIFFUSE":
        kw = dict(pass_filter={"COLOR"})
    if btype == "NORMAL":
        kw = dict(normal_space="TANGENT")
    bpy.ops.object.bake(type=btype, **kw)
    path = os.path.join(out_dir, f"T_{prefix}_{label}.png")
    images[label].filepath_raw = path
    images[label].file_format = "PNG"
    images[label].save()
    print("BAKED", path)
