# Quick look renders (Workbench) of a model right after building it — the main tool for checking shape problems.
#   blender -b --factory-startup Source/DiveGear_Scene.blend --python Source/_tools/dev/preview_render.py -- <build_script.py> <out_dir> <shots.json>
# shots.json: [{"name": "cave_34", "roots": ["SeaCave"], "cam": [18, -14, 12], "look": [0, 0.5, 1.5], "lens": 22, "host": "SeaCave"}, ...]
#   cam / look are in the host root's local frame (metres). "hide": ["Ceiling", ...] hides objects whose name contains any of these.
# Colours are the flat material colours (not the baked textures) — use verify_fbx.py to see the baked result.
import bpy, sys, os, json
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
script, out_dir, shots_file = args[0], args[1], args[2]
ASSETS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TOOLS = os.path.join(ASSETS, "Source", "_tools"); g = {"__name__": "__main__"}
for f in ("mk.py", os.path.basename(script)):
    exec(open(os.path.join(TOOLS, f), encoding="utf-8").read(), g)
scn = bpy.context.scene; scn.render.engine = "BLENDER_WORKBENCH"
sh = scn.display.shading; sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_shadows = True; sh.show_cavity = True
scn.render.resolution_x, scn.render.resolution_y = 1400, 800
cam = bpy.data.objects.new("_PrevCam", bpy.data.cameras.new("_PrevCam")); scn.collection.objects.link(cam); scn.camera = cam
os.makedirs(out_dir, exist_ok=True)
for s in json.load(open(shots_file, encoding="utf-8")):
    keep = set()
    for rn in s["roots"]:
        r = bpy.data.objects[rn]; keep |= {r, *r.children_recursive}
    for o in scn.objects:
        o.hide_render = (o not in keep and o is not cam) or any(h in o.name for h in s.get("hide", []))
    H = bpy.data.objects[s.get("host", s["roots"][0])].matrix_world
    p, q = H @ Vector(s["cam"]), H @ Vector(s["look"])
    cam.location = p; cam.rotation_euler = (q - p).to_track_quat("-Z", "Y").to_euler(); cam.data.lens = s.get("lens", 24)
    scn.render.filepath = os.path.join(out_dir, s["name"] + ".png"); bpy.ops.render.render(write_still=True)
    print("SHOT", scn.render.filepath, flush=True)
