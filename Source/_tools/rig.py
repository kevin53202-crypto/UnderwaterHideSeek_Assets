# Character helpers: lofted bodies, skin-modifier bodies, armatures, weights, procedural animation, skeletal FBX export.
# Usage inside Blender (after mk.py):
#   exec(open(r"C:\Users\0\Documents\UnderwaterHideSeek_Assets\Source\_tools\rig.py", encoding="utf-8").read())
# Skeletal characters face -Y in Blender (same convention as the UE mannequin; rotate the mesh -90 yaw in the Character BP).
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

OUT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "UnderwaterHideSeek_Assets")


def loft(stations, n=20, power=2.0):
    """stations: list of (y, half_width_x, half_height_z, z_center). Closed body along +Y with pole caps.
    power: superellipse exponent of the cross-section (2 = ellipse)."""
    bm = bmesh.new()
    rings = []
    for (y, hx, hz, zc) in stations:
        if hx < 1e-5 and hz < 1e-5:
            rings.append([bm.verts.new((0, y, zc))])
            continue
        ring = []
        for k in range(n):
            a = k / n * math.tau
            c, s = math.cos(a), math.sin(a)
            x = hx * math.copysign(abs(c) ** (2 / power), c)
            z = hz * math.copysign(abs(s) ** (2 / power), s)
            ring.append(bm.verts.new((x, y, zc + z)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        if len(r0) == 1:
            for k in range(n):
                bm.faces.new((r0[0], r1[k], r1[(k + 1) % n]))
        elif len(r1) == 1:
            for k in range(n):
                bm.faces.new((r0[(k + 1) % n], r0[k], r1[0]))
        else:
            for k in range(n):
                bm.faces.new((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]))
    if len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def skin_body(col, name, verts, edges, radii, root_index=0, subdiv=2):
    """Skin-modifier body from a joint graph; returns an applied mesh object."""
    me = bpy.data.meshes.new(name + "_graph")
    me.from_pydata([Vector(v) for v in verts], edges, [])
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    sk = o.modifiers.new("Skin", "SKIN")
    sk.use_smooth_shade = True
    for i, r in enumerate(radii):
        me.skin_vertices[0].data[i].radius = r
        me.skin_vertices[0].data[i].use_root = (i == root_index)
    ss = o.modifiers.new("Sub", "SUBSURF"); ss.levels = ss.render_levels = subdiv
    dg = bpy.context.evaluated_depsgraph_get()
    newme = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    o.modifiers.clear()
    o.data = newme; newme.name = name
    bpy.data.meshes.remove(me)
    newme.shade_smooth()
    return o


def make_armature(col, name, bones, location=(0, 0, 0)):
    """bones: list of (name, head, tail, parent_or_None, deform:bool, roll_deg)."""
    arm = bpy.data.armatures.new(name)
    ao = bpy.data.objects.new(name, arm)
    col.objects.link(ao)
    ao.show_in_front = True
    bpy.context.view_layer.objects.active = ao
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ao.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.edit_bones
    for b in bones:
        bn, head, tail, parent, deform = b[:5]
        roll = b[5] if len(b) > 5 else 0
        e = eb.new(bn)
        e.head = head; e.tail = tail; e.roll = math.radians(roll)
        e.use_deform = deform
        if parent:
            e.parent = eb[parent]
            e.use_connect = (Vector(eb[parent].tail) - Vector(head)).length < 1e-5
    bpy.ops.object.mode_set(mode="OBJECT")
    ao.location = location
    return ao


def auto_weight(mesh_obj, arm_obj, exclude=()):
    """Bone-heat weights; bones in `exclude` are temporarily non-deforming."""
    saved = {}
    for b in arm_obj.data.bones:
        if b.name in exclude:
            saved[b.name] = b.use_deform
            b.use_deform = False
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True); arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    for n, v in saved.items():
        arm_obj.data.bones[n].use_deform = v
    return len(mesh_obj.vertex_groups)


def rigid_bm_to_group(mesh_obj, bm_part, material, bone_name):
    """Append a bmesh part to an already-skinned mesh, fully weighted to one bone."""
    me = mesh_obj.data
    if material.name not in [m.name for m in me.materials if m]:
        me.materials.append(material)
    mi = [m.name for m in me.materials].index(material.name)
    tmp = bpy.data.meshes.new("_part")
    bm_part.to_mesh(tmp); bm_part.free()
    for p in tmp.polygons:
        p.material_index = mi
        p.use_smooth = True
    base = len(me.vertices)
    bm = bmesh.new(); bm.from_mesh(me); bm.from_mesh(tmp); bm.to_mesh(me); bm.free()
    bpy.data.meshes.remove(tmp)
    g = mesh_obj.vertex_groups.get(bone_name) or mesh_obj.vertex_groups.new(name=bone_name)
    g.add(list(range(base, len(me.vertices))), 1.0, "REPLACE")


def new_action(arm_obj, name):
    arm_obj.animation_data_create()
    act = bpy.data.actions.get(name)
    if act:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm_obj.animation_data.action = act
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
    return act


def key(pb, frame, rot=None, loc=None):
    if rot is not None:
        pb.rotation_euler = rot
        pb.keyframe_insert("rotation_euler", frame=frame)
    if loc is not None:
        pb.location = loc
        pb.keyframe_insert("location", frame=frame)


def wave_action(arm_obj, name, chain, frames=32, amp=8.0, grow=1.0, waves=1.0, extra=None):
    """Side-to-side swim wave along a bone chain (rotation about local Z, degrees)."""
    new_action(arm_obj, name)
    n = len(chain)
    for f in range(frames + 1):
        t = f / frames
        for i, bn in enumerate(chain):
            pb = arm_obj.pose.bones[bn]
            a = amp * (0.3 + grow * i / max(1, n - 1)) * math.sin(math.tau * (t - waves * i / n))
            key(pb, f + 1, rot=(0, 0, math.radians(a)))
        if extra:
            extra(arm_obj, f + 1, t)
    act = arm_obj.animation_data.action
    act.frame_range = (1, frames + 1)
    return act


def export_skeletal(arm_obj, sk_name, with_anims=True):
    """Export armature + its child meshes as SK_<name>.fbx (+ all its actions as separate takes)."""
    meshes = [c for c in arm_obj.children if c.type == "MESH"]
    old_loc = arm_obj.location.copy(); old_name = arm_obj.name
    other = bpy.data.objects.get("Armature")
    if other and other != arm_obj:
        other.name = "Armature_tmp_rename"
    arm_obj.location = (0, 0, 0)
    arm_obj.name = "Armature"          # Unreal skips an armature node named exactly "Armature"
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    prev_action = arm_obj.animation_data.action if arm_obj.animation_data else None
    path = os.path.join(OUT_DIR, sk_name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE", "MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL",
                             axis_forward="-Z", axis_up="Y", use_mesh_modifiers=True,
                             mesh_smooth_type="FACE", use_tspace=True,
                             add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
                             armature_nodetype="NULL",
                             bake_anim=with_anims, bake_anim_use_all_actions=with_anims,
                             bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
                             bake_anim_simplify_factor=0.0)
    arm_obj.name = old_name; arm_obj.location = old_loc
    if other and other.name == "Armature_tmp_rename":
        other.name = "Armature"
    if arm_obj.animation_data:
        arm_obj.animation_data.action = prev_action
    tris = sum(sum(len(p.vertices) - 2 for p in m.data.polygons) for m in meshes)
    return {"file": os.path.basename(path), "bones": len(arm_obj.data.bones), "tris": tris,
            "mats": sorted({s.material.name for m in meshes for s in m.material_slots if s.material})}
