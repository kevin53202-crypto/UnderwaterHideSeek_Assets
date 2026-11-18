import bpy, os, sys
from mathutils import Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
src, out_dir, mode = argv[0], argv[1], argv[2]   # mode: model root name, or "SCENE"

bpy.ops.wm.open_mainfile(filepath=src)

if mode == "SCENE":
    path = os.path.join(out_dir, "DiveGear_Scene.blend")
else:
    root = bpy.data.objects[mode]
    keep = {root} | {o for o in root.children_recursive
                     if o.type == "MESH" or (o.type == "EMPTY" and o.name.startswith("SKT_"))}
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    root.location = (0, 0, 0)   # model at origin; keep its rotation
    root.scale = (1, 1, 1)      # real-world size
    for c in list(bpy.data.collections):
        if not c.all_objects:
            bpy.data.collections.remove(c)
    # keep only this character's animations (actions use fake users, so purge alone would keep them all)
    prefix = {"Gigantura_Rig": "GT_", "DeepSeaEel_Rig": "EEL_", "Kraken_Rig": "KR_", "GiantIsopod_Rig": "IS_", "Diver_Rig": "DV_"}.get(mode)
    for act in list(bpy.data.actions):
        if not (prefix and act.name.startswith(prefix)):
            bpy.data.actions.remove(act)
    bpy.data.orphans_purge(do_recursive=True)
    name = "TankBand" if mode.startswith("TankBand") else mode
    path = os.path.join(out_dir, name + ".blend")

bpy.ops.wm.save_as_mainfile(filepath=path, compress=True, copy=True)
print("SAVED", path, os.path.getsize(path), "objects:", len(bpy.data.objects))
