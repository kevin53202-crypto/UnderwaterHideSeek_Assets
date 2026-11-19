# Re-link images whose file is missing (e.g. absolute paths from another PC) to <project>/Textures/<same name>, as relative paths.
#   blender -b --factory-startup <file.blend> --python Source/_tools/dev/fix_texture_paths.py
# Saves the .blend only if something changed. Prints FIXED/MISSING counts.
import bpy, os

tex = os.path.normpath(os.path.join(os.path.dirname(bpy.data.filepath), "..", "Textures"))
fixed, missing = 0, []
for im in bpy.data.images:
    if im.source != "FILE" or os.path.exists(bpy.path.abspath(im.filepath)):
        continue
    cand = os.path.join(tex, os.path.basename(im.filepath.replace("\\", "/")))
    if os.path.exists(cand):
        im.filepath = bpy.path.relpath(cand); im.reload(); fixed += 1
    else:
        missing.append(im.filepath)
print("FIXED", os.path.basename(bpy.data.filepath), fixed, "MISSING", missing, flush=True)
if fixed:
    bpy.ops.wm.save_mainfile(compress=True)
