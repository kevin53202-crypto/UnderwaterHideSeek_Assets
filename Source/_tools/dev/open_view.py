# Open the Blender GUI looking at one model (Material Preview, so the weathered procedural materials show).
#   blender Source/DiveGear_Scene.blend --python Source/_tools/dev/open_view.py -- <RootName> <cam_x> <cam_y> <cam_z> <look_x> <look_y> <look_z>
#   e.g. ... -- Shipwreck 16 15 10 0 0 1.5      (cam / look in the root's local frame, metres)
#   ... -- ALL                                    (every model visible, framed)
# Waits until the UI exists, isolates the model in local view (bones hidden), sets the view, then stops. Nothing is saved.
import bpy, sys
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
tries = [0]

def go_all():                                              # "-- ALL": every model visible, Material Preview, framed
    tries[0] += 1
    areas = [(w, ar) for w in bpy.context.window_manager.windows for ar in w.screen.areas if ar.type == "VIEW_3D"]
    if not areas:
        return 1.0 if tries[0] < 30 else None
    for w, ar in areas:
        sp = ar.spaces.active; sp.shading.type = "MATERIAL"; sp.clip_start = 0.01; sp.clip_end = 2000; sp.overlay.show_bones = False
        reg = next(g for g in ar.regions if g.type == "WINDOW")
        with bpy.context.temp_override(window=w, area=ar, region=reg):
            bpy.ops.view3d.view_all()
    return 2.0 if tries[0] < 3 else None

ROOT = a[0]
if ROOT != "ALL":
    CAM = Vector(map(float, a[1:4])); LOOK = Vector(map(float, a[4:7]))

def go():
    tries[0] += 1
    r = bpy.data.objects.get(ROOT)
    areas = [ar for w in bpy.context.window_manager.windows for ar in w.screen.areas if ar.type == "VIEW_3D"]
    if not (r and areas):
        return 1.0 if tries[0] < 30 else None
    for ar in areas:
        sp = ar.spaces.active; rv = sp.region_3d
        if not sp.local_view:          # show only this model (local view, "/" to leave), bones hidden
            for o in bpy.context.view_layer.objects: o.select_set(False)
            for o in [r] + list(r.children_recursive):
                if o.visible_get(): o.select_set(True)
            win = next(w for w in bpy.context.window_manager.windows if ar in w.screen.areas[:])
            reg = next(g for g in ar.regions if g.type == "WINDOW")
            with bpy.context.temp_override(window=win, area=ar, region=reg):
                if not sp.local_view: bpy.ops.view3d.localview(frame_selected=False)
            sp.overlay.show_bones = False
        sp.shading.type = "MATERIAL"; sp.clip_start = 0.01; sp.lens = 24
        rv.view_perspective = "PERSP"
        rv.view_rotation = (CAM - LOOK).to_track_quat("Z", "Y")
        rv.view_distance = (CAM - LOOK).length
        rv.view_location = r.matrix_world @ LOOK
        ar.tag_redraw()
    return 2.0 if tries[0] < 3 else None      # apply again once the file UI has settled

bpy.app.timers.register(go_all if ROOT == "ALL" else go, first_interval=3.0, persistent=True)
