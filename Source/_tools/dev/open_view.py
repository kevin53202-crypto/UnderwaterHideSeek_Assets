# Open the Blender GUI looking at one model (Material Preview, so the weathered procedural materials show).
#   blender Source/DiveGear_Scene.blend --python Source/_tools/dev/open_view.py -- <RootName> <cam_x> <cam_y> <cam_z> <look_x> <look_y> <look_z>
#   e.g. ... -- Shipwreck 16 15 10 0 0 1.5      (cam / look in the root's local frame, metres)
# Waits until the UI exists, sets the view, then stops. Nothing is saved.
import bpy, sys
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
ROOT = a[0]; CAM = Vector(map(float, a[1:4])); LOOK = Vector(map(float, a[4:7]))
tries = [0]

def go():
    tries[0] += 1
    r = bpy.data.objects.get(ROOT)
    areas = [ar for w in bpy.context.window_manager.windows for ar in w.screen.areas if ar.type == "VIEW_3D"]
    if not (r and areas):
        return 1.0 if tries[0] < 30 else None
    for ar in areas:
        sp = ar.spaces.active; rv = sp.region_3d
        sp.shading.type = "MATERIAL"; sp.clip_start = 0.01; sp.lens = 24
        rv.view_perspective = "PERSP"
        rv.view_rotation = (CAM - LOOK).to_track_quat("Z", "Y")
        rv.view_distance = (CAM - LOOK).length
        rv.view_location = r.matrix_world @ LOOK
        ar.tag_redraw()
    return 2.0 if tries[0] < 3 else None      # apply again once the file UI has settled

bpy.app.timers.register(go, first_interval=3.0, persistent=True)
