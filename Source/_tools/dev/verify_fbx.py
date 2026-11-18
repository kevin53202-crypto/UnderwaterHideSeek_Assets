# Re-import exported FBX files into an empty scene and check them (what Unreal will actually get).
#   blender -b --factory-startup --python Source/_tools/dev/verify_fbx.py -- <file.fbx> [<file2.fbx> ...] [--render <out_dir> <shots.json>]
# Prints per file: materials, images (baked textures found?), triangle count, socket names (no scene suffix left?),
# lowest Z (cm). With --render, renders the imported meshes with their textures (Workbench, texture colour);
# shots.json uses the same format as preview_render.py but cam/look are in FBX space (= the model's root frame).
import bpy, sys, os, json
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
render = None
if "--render" in args:
    i = args.index("--render"); render = (args[i + 1], args[i + 2]); args = args[:i]
bpy.ops.wm.read_factory_settings(use_empty=True)
for f in args:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=f)
    new = [o for o in bpy.data.objects if o not in before]
    ms = [o for o in new if o.type == "MESH"]; socks = sorted(o.name for o in new if o.type == "EMPTY")
    zs = [(o.matrix_world @ v.co).z for o in ms for v in o.data.vertices]
    print("VERIFY", os.path.basename(f),
          "| mats", [m.name for o in ms for m in o.data.materials],
          "| tris", sum(len(p.vertices) - 2 for o in ms for p in o.data.polygons),
          "| minZ_cm", round(min(zs) * 100, 1) if zs else None,
          "| sockets", len(socks), [s for s in socks if "__" in s] or "ok", flush=True)
print("IMAGES", [im.name for im in bpy.data.images if im.name not in ("Render Result",)])
if render:
    out_dir, shots_file = render
    scn = bpy.context.scene; scn.render.engine = "BLENDER_WORKBENCH"
    sh = scn.display.shading; sh.light = "STUDIO"; sh.color_type = "TEXTURE"; sh.show_shadows = True; sh.show_cavity = True
    scn.render.resolution_x, scn.render.resolution_y = 1400, 800
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scn.collection.objects.link(cam); scn.camera = cam
    os.makedirs(out_dir, exist_ok=True)
    for s in json.load(open(shots_file, encoding="utf-8")):
        p, q = Vector(s["cam"]), Vector(s["look"])
        cam.location = p; cam.rotation_euler = (q - p).to_track_quat("-Z", "Y").to_euler(); cam.data.lens = s.get("lens", 24)
        scn.render.filepath = os.path.join(out_dir, s["name"] + ".png"); bpy.ops.render.render(write_still=True)
        print("SHOT", scn.render.filepath, flush=True)
