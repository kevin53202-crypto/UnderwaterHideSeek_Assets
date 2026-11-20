# Build one monster from its script (+ the extra Search / Hit clips), then preview renders or bake + export.
#   blender -b --factory-startup Source/DiveGear_Scene.blend --python Source/_tools/dev/run_monster.py -- \
#       <assets_dir> <out_dir> <build_script> <Rig> <Body> <Prefix> [--export <new_scene.blend>]
#   e.g. ... -- . C:/temp build_eel_v3.py DeepSeaEel_Rig SK_DeepSeaEel_Body DeepSeaEel --export C:/temp/scene_new.blend
# Preview: set env SHOTS="name|cam_x,y,z|look_x,y,z|lens|action_or_-|frame;..." (rig-local metres) -> Workbench PNGs in out_dir.
# Export: env BAKE_SIZE (default 4096); bakes Textures/T_<Prefix>_*.png, writes SK_<Prefix>.fbx, saves the scene COPY.
# After swapping the copy in as Source/DiveGear_Scene.blend run dev/fix_texture_paths.py, then split_models.py.
import bpy, sys, os
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]; A, OUT, SCRIPT, RIG, BODY, PFX = a[:6]
A = os.path.abspath(A)
T = os.path.join(A, "Source", "_tools"); g = {"__name__": "__main__"}
exec(open(os.path.join(T, "mk.py"), encoding="utf-8").read(), g)
for f in ("rig.py", "horror.py", "horror2.py", "monsters_v2_pipeline.py", SCRIPT, "build_monster_anims_extra.py"):
    g["OUT_DIR"] = A; g["SRC_DIR"] = os.path.join(A, "Source")          # rig.py resets these to ~/Documents
    exec(open(os.path.join(T, f), encoding="utf-8").read(), g)
g["OUT_DIR"] = A; g["SRC_DIR"] = os.path.join(A, "Source")
rig = bpy.data.objects[RIG]; body = bpy.data.objects[BODY]; scn = bpy.context.scene
if "--export" in a:
    size = int(os.environ.get("BAKE_SIZE", "4096"))
    uvs = {m.name: 2.0 for m in body.data.materials if any(k in m.name for k in ("Eye", "Iris", "Carapace"))}   # more texels where players look
    uvs.update({m.name: 0.7 for m in body.data.materials if "Underside" in m.name})
    print("EXPORT", g["bake_monster"](BODY, PFX, size, uv_scale=uvs or None), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=a[a.index("--export") + 1], compress=True); print("SAVED_NEW", flush=True)
else:
    scn.render.engine = "BLENDER_WORKBENCH"
    sh = scn.display.shading; sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_shadows = True; sh.show_cavity = True
    scn.render.resolution_x, scn.render.resolution_y = 1200, 700
    cam = bpy.data.objects.new("_cam", bpy.data.cameras.new("_cam")); scn.collection.objects.link(cam); scn.camera = cam
    for o in scn.objects: o.hide_render = o not in (rig, body, cam)
    bpy.context.view_layer.update(); H = rig.matrix_world.copy()
    for nm, c, l, lens, act, fr in (s.split("|") for s in os.environ.get("SHOTS", "front|3,-3,1.5|0,0,0|30|-|1").split(";")):
        rig.data.pose_position = "REST" if act == "-" else "POSE"
        if act != "-":
            ac = bpy.data.actions[act]; rig.animation_data.action = ac
            if len(ac.slots): rig.animation_data.action_slot = ac.slots[0]
        scn.frame_set(int(fr))
        p, q = H @ Vector(map(float, c.split(","))), H @ Vector(map(float, l.split(",")))
        cam.location = p; cam.rotation_euler = (q - p).to_track_quat("-Z", "Y").to_euler(); cam.data.lens = float(lens)
        scn.render.filepath = os.path.join(OUT, nm + ".png"); bpy.ops.render.render(write_still=True); print("SHOT", nm, flush=True)
print("INFO", {k: v for k, v in g.items() if k.endswith("_INFO")}, flush=True)
