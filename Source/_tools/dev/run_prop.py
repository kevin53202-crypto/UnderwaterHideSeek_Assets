# Build one model from its build script and (optionally) export it, in background Blender.
#   blender -b --factory-startup Source/DiveGear_Scene.blend --python Source/_tools/dev/run_prop.py -- <build_script.py> [--export] [--save OUT.blend]
# - Runs mk.py -> weather_bake.py -> <build_script.py> in one namespace (OUT_DIR/SRC_DIR point at this asset folder).
# - --export : calls the script's export_all() (texture bake + FBX for the map props).
# - --save   : saves the resulting scene to OUT.blend (a copy). The scene you opened is NOT overwritten,
#              so you can check it first and replace Source/DiveGear_Scene.blend yourself (see README "다음 작업자를 위한 안내").
# Prints the root's sockets (root-local, cm) and the export info.
import bpy, sys, os, time

args = sys.argv[sys.argv.index("--") + 1:]
script = args[0]
ASSETS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # .../Source/_tools/dev -> asset root
TOOLS = os.path.join(ASSETS, "Source", "_tools")
g = {"__name__": "__main__"}
exec(open(os.path.join(TOOLS, "mk.py"), encoding="utf-8").read(), g)
g["OUT_DIR"] = ASSETS; g["SRC_DIR"] = os.path.join(ASSETS, "Source"); g["SCENE_FILE"] = os.path.join(ASSETS, "Source", "DiveGear_Scene.blend")
exec(open(os.path.join(TOOLS, "weather_bake.py"), encoding="utf-8").read(), g)
t = time.time()
exec(open(os.path.join(TOOLS, os.path.basename(script)), encoding="utf-8").read(), g)
print("RUN built", script, f"{time.time() - t:.0f}s", flush=True)

root = bpy.data.objects.get(g.get("ROOT", ""))
if root:
    print("RUN sockets", {o.name[4:]: tuple(round(c * 100, 1) for c in o.matrix_local.translation) for o in root.children if o.name.startswith("SKT_")}, flush=True)
if "--export" in args:
    t = time.time(); print("RUN export", g["export_all"](), f"{time.time() - t:.0f}s", flush=True)
if "--save" in args:
    out = args[args.index("--save") + 1]
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True, copy=True); print("RUN saved", out, flush=True)
