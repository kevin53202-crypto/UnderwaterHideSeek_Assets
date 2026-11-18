# Shared modelling + Unreal export helpers for the underwater game assets.
# Usage inside Blender:  exec(open(r"C:\Users\0\Documents\UnderwaterHideSeek_Assets\Source\_tools\mk.py", encoding="utf-8").read())
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

OUT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "UnderwaterHideSeek_Assets")
SRC_DIR = os.path.join(OUT_DIR, "Source")
SCENE_FILE = os.path.join(SRC_DIR, "DiveGear_Scene.blend")


def get_col(name, clear=True):
    scn = bpy.context.scene
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in scn.collection.children:
        scn.collection.children.link(c)
    if clear:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    return c


def mat(name, color, metal=0.0, rough=0.5, emit=None, strength=0.0, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    b.inputs["Alpha"].default_value = alpha
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    m.diffuse_color = (*color, alpha)
    return m


def finish(col, name, bm, material, smooth=True):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    if smooth:
        me.shade_smooth()
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    o.data.materials.append(material)
    return o


def xf(bm, m):
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return bm


T = lambda x=0, y=0, z=0: Matrix.Translation((x, y, z))
RX = lambda d: Matrix.Rotation(math.radians(d), 4, "X")
RY = lambda d: Matrix.Rotation(math.radians(d), 4, "Y")
RZ = lambda d: Matrix.Rotation(math.radians(d), 4, "Z")


def lathe(pts, seg=32, m=None):
    """pts: (radius, z) in metres, revolved around Z."""
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0, z)) for r, z in pts]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, axis=(0, 0, 1), cent=(0, 0, 0), steps=seg, angle=math.tau)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    return xf(bm, m) if m else bm


def box(size, center=(0, 0, 0), m=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    return xf(bm, m) if m else bm


def cyl(r, depth, seg=24, center=(0, 0, 0), m=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=depth)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    return xf(bm, m) if m else bm


def torus(R, r, seg=32, rseg=10, m=None):
    pts = [(R + r * math.cos(a), r * math.sin(a)) for a in (k / rseg * math.tau for k in range(rseg + 1))]
    return lathe(pts, seg, m)


def gear(r_out, r_root, r_hole, thick, teeth, m=None):
    """Spur gear along Z, centred at z=0, with a centre hole."""
    bm = bmesh.new()
    n = teeth * 4
    outer, inner = [], []
    for i in range(n):
        a = i / n * math.tau
        r = r_out if (i % 4) in (1, 2) else r_root
        outer.append(Vector((r * math.cos(a), r * math.sin(a), -thick / 2)))
        inner.append(Vector((r_hole * math.cos(a), r_hole * math.sin(a), -thick / 2)))
    ob = [bm.verts.new(p) for p in outer]
    ib = [bm.verts.new(p) for p in inner]
    ot = [bm.verts.new(p + Vector((0, 0, thick))) for p in outer]
    it = [bm.verts.new(p + Vector((0, 0, thick))) for p in inner]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((ob[i], ob[j], ot[j], ot[i]))      # outer wall
        bm.faces.new((ib[j], ib[i], it[i], it[j]))      # hole wall
        bm.faces.new((ot[i], ot[j], it[j], it[i]))      # top
        bm.faces.new((ob[j], ob[i], ib[i], ib[j]))      # bottom
    return xf(bm, m) if m else bm


def catmull(pts, n=8):
    P = [Vector(p) for p in pts]
    P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def tube(poly, radius, up=(0, 0, 1), sides=10, closed=False):
    R = radius if callable(radius) else (lambda s: radius)
    bm = bmesh.new(); up = Vector(up); n = len(poly); rings = []
    for i, p in enumerate(poly):
        a = poly[(i - 1) % n] if (closed or i > 0) else p
        b = poly[(i + 1) % n] if (closed or i < n - 1) else p
        t = (b - a).normalized()
        w = (up - t * up.dot(t))
        if w.length < 1e-6:
            w = t.orthogonal()
        w.normalize(); nn = t.cross(w); r = R(i / max(1, n - 1))
        rings.append([bm.verts.new(p + (w * math.cos(k / sides * math.tau) + nn * math.sin(k / sides * math.tau)) * r)
                      for k in range(sides)])
    segs = n if closed else n - 1
    for i in range(segs):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for k in range(sides):
            bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
    if not closed:
        bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    return bm


def strap(poly, up, width, thick, closed=False):
    W = width if callable(width) else (lambda s: width)
    Tk = thick if callable(thick) else (lambda s: thick)
    bm = bmesh.new(); up = Vector(up); n = len(poly); rings = []
    for i, p in enumerate(poly):
        a = poly[(i - 1) % n] if (closed or i > 0) else p
        b = poly[(i + 1) % n] if (closed or i < n - 1) else p
        t = (b - a).normalized()
        w = (up - t * up.dot(t)).normalized(); nn = t.cross(w)
        s = i / max(1, n - 1); hw, ht = W(s) / 2, Tk(s) / 2
        rings.append([bm.verts.new(p + w * x + nn * y) for x, y in ((-hw, -ht), (hw, -ht), (hw, ht), (-hw, ht))])
    segs = n if closed else n - 1
    for i in range(segs):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for k in range(4):
            bm.faces.new((r0[k], r0[(k + 1) % 4], r1[(k + 1) % 4], r1[k]))
    if not closed:
        bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    return bm


def bevel(o, w=0.003, seg=2):
    b = o.modifiers.new("Bevel", "BEVEL"); b.width = w; b.segments = seg; b.limit_method = "ANGLE"
    return o


def socket(col, root, name, loc_local, rot_deg=(0, 0, 0)):
    """Add an Unreal socket marker (empty SKT_<name>) under a model root, in the root's local space."""
    e = bpy.data.objects.get("SKT_" + name)
    if e is None:
        e = bpy.data.objects.new("SKT_" + name, None)
        col.objects.link(e)
    e.empty_display_type = "ARROWS"; e.empty_display_size = 0.08
    e.parent = root
    e.matrix_parent_inverse = Matrix.Identity(4)
    e.location = loc_local
    e.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    return e


def make_root(col, name, parts, location):
    root = bpy.data.objects.new(name, None)
    col.objects.link(root)
    for p in parts:
        p.parent = root
    root.location = location
    return root


def export_unreal(root_name, sm_name, pivot=(0, 0, 0), keep_rotation=False):
    """Join a model (root empty + mesh children) on a temp copy and write SM_<name>.fbx. Scene stays untouched.
    keep_rotation: bake the root's rotation into the mesh (pivot is then in that rotated frame)."""
    root = bpy.data.objects[root_name]
    # scene placement scale is always removed so the FBX is real-world size
    s = root.matrix_world.to_scale().x
    rot = root.matrix_world.to_quaternion().to_matrix().to_4x4() if not keep_rotation else Matrix.Identity(4)
    frame = Matrix.Translation(root.matrix_world.translation) @ rot @ Matrix.Scale(s, 4)
    tmp = bpy.data.collections.new("_ExportTmp"); bpy.context.scene.collection.children.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get(); dups = []
    for o in root.children_recursive:
        if o.type != "MESH":
            continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        me.transform(frame.inverted() @ o.matrix_world)
        d = bpy.data.objects.new(o.name + "_x", me); tmp.objects.link(d); dups.append(d)
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for d in dups:
        d.select_set(True)
    bpy.context.view_layer.objects.active = dups[0]
    bpy.ops.object.join()
    sm = bpy.context.active_object; sm.name = sm_name; sm.data.name = sm_name
    sm.data.transform(Matrix.Translation(-Vector(pivot))); sm.matrix_world = Matrix.Identity(4)
    bm = bmesh.new(); bm.from_mesh(sm.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(sm.data); bm.free()
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.01)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    sm.data.uv_layers.new(name="Lightmap")
    me = sm.data
    # Unreal sockets: every empty named SKT_<name> under the root becomes SOCKET_<name> on the static mesh
    sockets = []
    for o in root.children_recursive:
        if o.type == "EMPTY" and o.name.startswith("SKT_"):
            e = bpy.data.objects.new("SOCKET_" + o.name[4:], None)
            tmp.objects.link(e)
            e.parent = sm
            m = frame.inverted() @ o.matrix_world
            e.location = m.translation - Vector(pivot)
            e.rotation_euler = m.to_euler()
            sockets.append(e)
    for e in sockets:
        e.select_set(True)
    info = {"tris": sum(len(p.vertices) - 2 for p in me.polygons),
            "mats": len(me.materials),
            "size_cm": tuple(round(x * 100, 1) for x in sm.dimensions)}
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, sm_name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH", "EMPTY"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Z", axis_up="Y", use_mesh_modifiers=True,
                             mesh_smooth_type="FACE", use_tspace=True, add_leaf_bones=False, bake_anim=False)
    for e in sockets:
        bpy.data.objects.remove(e)
    bpy.data.objects.remove(sm); bpy.data.meshes.remove(me); bpy.data.collections.remove(tmp)
    info["file"] = os.path.basename(path)
    info["sockets"] = {e_name: tuple(round(c * 100, 1) for c in loc) for e_name, loc in
                       ((o.name[4:], (frame.inverted() @ o.matrix_world).translation - Vector(pivot))
                        for o in root.children_recursive if o.type == "EMPTY" and o.name.startswith("SKT_"))}
    return info


def save_scene():
    """Save the working scene (Ctrl+S equivalent) so per-model .blend files can be split off safely."""
    os.makedirs(SRC_DIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=SCENE_FILE, compress=True)
    return SCENE_FILE
