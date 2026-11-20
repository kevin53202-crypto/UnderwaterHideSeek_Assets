# Adds an "Anim" tab to the 3D view sidebar (N): pick a model -> the view jumps to it -> one button per animation;
# clicking a button plays that clip in a loop (Space = stop).
#   blender Source/DiveGear_Scene.blend --python Source/_tools/dev/anim_picker.py [--python Source/_tools/dev/open_view.py -- ...]
# Rigs are found by their current action's prefix (DV_ -> Diver_Rig, IS_ -> GiantIsopod_Rig, ...). Nothing is saved.
# UI text is English on purpose: Korean glyphs render garbled on this PC's old Intel GPU driver.
import bpy


def rigs():
    out = []
    for o in bpy.data.objects:
        ad = o.animation_data if o.type == "ARMATURE" else None
        if ad and ad.action and "_" in ad.action.name:
            pfx = ad.action.name.split("_")[0] + "_"
            out.append((o, sorted(a.name for a in bpy.data.actions if a.name.startswith(pfx))))
    return out


def _rig_items(self, context):
    return [(o.name, o.name.replace("_Rig", ""), "") for o, _ in rigs()] or [("NONE", "(no rigs)", "")]


def _frame_rig(self, context):
    """Select the rig + its meshes and frame them in every 3D view (local view is left first so the model is visible)."""
    o = bpy.data.objects.get(self.animpick_rig)
    if not o:
        return
    for w in context.window_manager.windows:
        for ar in w.screen.areas:
            if ar.type != "VIEW_3D":
                continue
            reg = next(g for g in ar.regions if g.type == "WINDOW")
            with context.temp_override(window=w, area=ar, region=reg):
                if ar.spaces.active.local_view:
                    bpy.ops.view3d.localview(frame_selected=False)
                for x in context.view_layer.objects:
                    x.select_set(False)
                for x in [o] + list(o.children):
                    x.select_set(True)
                context.view_layer.objects.active = o
                bpy.ops.view3d.view_selected()


class ANIMPICK_OT_play(bpy.types.Operator):
    bl_idname = "animpick.play"
    bl_label = "Play animation"
    rig: bpy.props.StringProperty()
    action: bpy.props.StringProperty()

    def execute(self, context):
        o, act = bpy.data.objects[self.rig], bpy.data.actions[self.action]
        o.animation_data.action = act
        if hasattr(o.animation_data, "action_slot") and len(act.slots):
            o.animation_data.action_slot = act.slots[0]
        scn = context.scene; f0, f1 = (int(v) for v in act.frame_range)
        scn.frame_start, scn.frame_end = f0, f1; scn.frame_set(f0)
        if not context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        return {"FINISHED"}


class ANIMPICK_PT_panel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"; bl_region_type = "UI"; bl_category = "Anim"; bl_label = "Animations"

    def draw(self, context):
        lay = self.layout
        lay.label(text="1) Model  2) Click a clip (loops)  Space = stop")
        lay.prop(context.scene, "animpick_rig", text="Model")
        o = bpy.data.objects.get(context.scene.animpick_rig)
        if not o or not o.animation_data:
            return
        acts = dict(rigs()).get(o, [])
        cur = o.animation_data.action.name if o.animation_data.action else ""
        grid = lay.grid_flow(columns=2, even_columns=True, align=True)
        for a in acts:
            op = grid.operator("animpick.play", text=a, depress=(a == cur)); op.rig = o.name; op.action = a


bpy.types.Scene.animpick_rig = bpy.props.EnumProperty(name="Model", items=_rig_items, update=_frame_rig)
for c in (ANIMPICK_OT_play, ANIMPICK_PT_panel):
    bpy.utils.register_class(c)


def _open_sidebar():
    areas = [ar for w in bpy.context.window_manager.windows for ar in w.screen.areas if ar.type == "VIEW_3D"]
    if not areas:
        return 1.0
    for ar in areas:
        ar.spaces.active.show_region_ui = True; ar.tag_redraw()
    return None


bpy.app.timers.register(_open_sidebar, first_interval=3.5)
