# ----------------------------------------
#   BLENDER PYTHON UTILITY FUNCTIONS
#       Various utility scripts for the
#       Blender Python (bpy) module to
#       allow for ease of implementing
#       other various features!
# ----------------------------------------
"""
Module with various utility scripts for the Blender Python (`bpy`) module to allow for ease of implementing other various features!
"""

import bpy, random, struct, os
from typing import cast

# ------------------------

# -------------------------------------------------------
# DETERMINE BLENDER VERSION TO HANDLE THINGS DIFFERENTLY
# Credit: REDxEYE
# -------------------------------------------------------

# Blender 3.6
def is_blender_3_6():
    return bpy.app.version >= (3, 6, 0)

# Blender 4.0
def is_blender_4():
    return bpy.app.version >= (4, 0, 0)

# Blender 4.1
def is_blender_4_1():
    return bpy.app.version >= (4, 1, 0)

# --------------------------------------------

# ------------------------------
# DATA CONVERSIONS / INVERSIONS
# ------------------------------

# UV Map inverter for import and export purposes
def invert_v(uv_set: int) -> list[float]:
    """Invert the V component of a UV Map."""
    return (1 - uv_set)

# Take the RGBA values of a mesh's vertex colors and divide them by 255
def convert_uv(uv: int) -> list[float]:
    """Takes the RGBA of the vertex colors and divides them by 255 to convert them from signed bytes to floats so Blender can parse them."""
    uv_conv = uv / 255

    return [uv_conv]

# Reverse an n-point vector's values.
def reverse_vector(vector: list | tuple) -> tuple:
    """Reverse an n-point vector's values."""
    return tuple(reversed(vector))

# Take the XYZ of a mesh's normals and divide them by 127 (Their maximum range)
def convert_vertex_normal(nx: int, ny: int, nz: int) -> tuple[float, float, float]:
    """Takes the XYZ of the normals and subtracts them by 127 to convert them from signed bytes to floats so Blender can parse them."""
    nx_conv = nx - 127
    ny_conv = ny - 127
    nz_conv = nz - 127

    return (nx_conv, ny_conv, nz_conv)

# Take the RGBA values of a mesh's vertex colors and divide them by 255
def convert_vertex_color(r: int, g: int, b: int, a: int) -> list[float, float, float, float]:
    """Takes the RGBA of the vertex colors and divides them by 255 to convert them from signed bytes to floats so Blender can parse them."""
    r_conv = r / 255
    g_conv = g / 255
    b_conv = b / 255
    a_conv = a / 255

    return [r_conv, g_conv, b_conv, a_conv]

# Convert a single color channel from Linear to sRGB Color Space.
def linear_to_srgb(value: float) -> float:
    """Convert a single color channel from Linear to sRGB Color Space."""
    if value <= 0.0031308:
        return value * 12.92
    else:
        return 1.055 * pow(value, 1.0 / 2.4) - 0.055

# -------------------------------------------------------------------------------------------------------------------------------------------------

# ----------
# MATERIALS
# ----------

# Create a material that can be placed on an object. Credit: REDxEYE, Modified by Dodylectable
def create_material(material_name: str, assign_material_colors: bool = True) -> bpy.types.Material:
    """Create a material that can be placed on an object."""
    mat = bpy.data.materials.get(material_name, None)
    if mat is None:
        mat = bpy.data.materials.new(material_name)

        # Assign random colors on a material to help with distinguishing submeshes
        if assign_material_colors:
            mat.diffuse_color = [random.uniform(.4, 1) for (_) in range(3)] + [1.0]
    return mat

# Quickly add a material to a Blender object. Credit: REDxEYE
def add_material(mat: bpy.types.Material, model_obj: bpy.types.Object) -> int:
    """Quickly add a material to a Blender mesh object."""
    model_data: bpy.types.Mesh = cast(bpy.types.Mesh, model_obj.data)
    if model_data.materials.get(mat.name, None) is not None:
        return list(model_data.materials).index(mat)
    else:
        model_data.materials.append(mat)
        return len(model_data.materials) - 1

# ---------------------------------------------------------------------------------------------

# Add weights to a model
def add_model_weights(obj: bpy.types.Object, bone_indices: list[list[int]], bone_weights: list[list[int]]):
    """Add vertex group weights to the object."""
    print("Adding vertex weights...")
    vertex_groups = {}

    # Loop through vertices and assign weights
    for vertex_index, (vertex_bone_ids, vertex_bone_weights) in enumerate(zip(bone_indices, bone_weights)):
        for bone_index, weight in zip(vertex_bone_ids, vertex_bone_weights):
            # Ignore zero weights
            if weight == 0:
                continue

            group_name = f"bone_{bone_index}"

            # Create the vertex group if it doesn't exist
            if group_name not in vertex_groups:
                vertex_groups[group_name] = obj.vertex_groups.new(name=group_name)

            # Normalize weight
            normalized_weight = weight / 255.0
            vertex_groups[group_name].add([vertex_index], normalized_weight, 'REPLACE')

# ---------------------------------------------------------------------------------------------

# Patch DDS flags so it has DDSD_CAPS and the user won't have to go through extra hoops to get them to work on Blender directly
def patch_dds_flags(path):
    try:
        with open(path, "r+b") as f:
            f.seek(8)  # Flags' offset
            f.write(struct.pack("<I", 659463))  # DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_MIPMAPCOUNT | DDSD_LINEARSIZE
        print(f"Patched DDS flags for: {os.path.basename(path)}")
    except Exception as e:
        print(f"Failed to patch DDS: {path} ({e})")

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
