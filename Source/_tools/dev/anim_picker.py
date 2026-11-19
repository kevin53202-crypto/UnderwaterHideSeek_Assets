# Adds a "동작" tab to the 3D view sidebar: one button per animation of each rig; clicking plays it in a loop.
#   blender Source/DiveGear_Scene.blend --python Source/_tools/dev/anim_picker.py [--python Source/_tools/dev/open_view.py -- ...]
# Rigs are found by their current action's prefix (DV_ -> Diver_Rig, IS_ -> GiantIsopod_Rig, ...). Nothing is saved.
import bpy


def rigs():
    out = []
    for o in bpy.data.objects:
        ad = o.animation_data if o.type == "ARMATURE" else None
        if ad and ad.action and "_" in ad.action.name:
            pfx = ad.action.name.split("_")[0] + "_"
            acts = sorted(a.name for a in bpy.data.actions if a.name.startswith(pfx))
            out.append((o, acts))
    return out


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
    bl_space_type = "VIEW_3D"; bl_region_type = "UI"; bl_category = "동작"; bl_label = "애니메이션 보기"

    def draw(self, context):
        lay = self.layout
        lay.label(text="버튼 클릭 = 반복 재생, 스페이스바 = 멈춤")
        for o, acts in rigs():
            box = lay.box(); box.label(text=o.name, icon="ARMATURE_DATA")
            cur = o.animation_data.action.name
            col = box.column(align=True)
            for a in acts:
                op = col.operator("animpick.play", text=a, depress=(a == cur)); op.rig = o.name; op.action = a


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
