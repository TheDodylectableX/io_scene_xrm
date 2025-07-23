# ------------------------------------------------
#   MODEL IMPORTER / BUILDER
#       Takes the parsed model data and
#       builds it into Blender's scene as objects
# ------------------------------------------------
"""
Takes the parsed model data and builds it into Blender's scene as objects.
"""

import os
import bpy
import math

from .srm_parser import *
from .trm_parser import *

from .bpy_util_funcs import *

from itertools import chain
from collections import defaultdict

# ------------------------------------------------


# ==================
# SOUL REAVER STUFF
# ==================

# Import a Soul Reaver model!
def import_sr_model(file_path: str, use_custom_normals: bool = False, assign_material_colors: bool = True, import_textures: bool = True):
    """Import an SRM model and construct it in Blender."""
    print(f"\nIMPORTING SRM MODEL: {file_path}...\n")

    # Load model using SRM parser
    model = SRM(file_path)

    # Extract data from the SRM parser
    model_data = {
        "filepath": model.model_file,
        "vertices": model.mesh_data[0]["vertices"],
        "faces": model.mesh_data[0]["faces"],
        "normals": model.mesh_data[0]["normals"],
        "uv_map": model.mesh_data[0]["uv_map"],
        "bone_indices": model.mesh_data[0].get("bone_indices", []),
        "bone_weights": model.mesh_data[0].get("bone_weights", []),
        "textures": model.mesh_data[0]["textures"],
        "material_index": model.mesh_data[0]["material_index"]
    }

    # Create mesh and object for Blender
    mesh_name = os.path.splitext(os.path.basename(file_path))[0]
    mesh = bpy.data.meshes.new(name=mesh_name)
    obj = bpy.data.objects.new(mesh_name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    # obj.scale = (0.10, 0.10, 0.10)

    # Build the mesh (vertices, faces, normals, UVs, etc.)
    build_mesh_from_data(mesh, obj, model_data, use_custom_normals, assign_material_colors)

    # Add textures to the materials
    texture_directory = os.path.join(os.path.dirname(os.path.dirname(file_path)), 'TEX')

    if import_textures and "textures" in model_data:
        for i, texture_name in enumerate(model_data["textures"]):
            sanitized_name = ''.join(c for c in texture_name if c.isprintable())
            mat = obj.data.materials[i]
            import_sr_textures(mat, texture_directory, sanitized_name)

    print("\nMODEL IMPORT COMPLETE!")
    return {'FINISHED'}

# Import (a) Soul Reaver texture(s)!
def import_sr_textures(mat: bpy.types.Material, tex_dir: str, base_name: str):
    mat.use_nodes = True

    for node in mat.node_tree.nodes:
        mat.node_tree.nodes.remove(node)

   # Add Principled BSDF if it doesn't exist
    bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    output = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(output.inputs['Surface'], bsdf.outputs['BSDF'])

   # Diffuse Map
    d_path = os.path.join(tex_dir, base_name + "_D.DDS")
    if os.path.exists(d_path):
        print(f"Diffuse texture found: {d_path}")
        patch_dds_flags(d_path)
        tex_d = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex_d.image = bpy.data.images.load(d_path)
        mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_d.outputs['Color'])
        mat.node_tree.links.new(bsdf.inputs['Alpha'], tex_d.outputs['Alpha'])
    else:
        print(f"Diffuse texture not found for {base_name}")

    # Normal Map
    n_path = os.path.join(tex_dir, base_name + "_N.DDS")
    if os.path.exists(n_path):
        print(f"Normal texture found: {n_path}")
        patch_dds_flags(n_path)
        tex_n = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex_n.image = bpy.data.images.load(n_path)
        tex_n.image.colorspace_settings.name = 'Non-Color'
        # TODO: Rebuild the Z axis
        normal_map = mat.node_tree.nodes.new("ShaderNodeNormalMap")
        mat.node_tree.links.new(normal_map.inputs['Color'], tex_n.outputs['Color'])
        mat.node_tree.links.new(bsdf.inputs['Normal'], normal_map.outputs['Normal'])
    else:
        print(f"Normal texture not found for {base_name}")

    # Specular Map
    s_path = os.path.join(tex_dir, base_name + "_S.DDS")
    if os.path.exists(s_path):
        print(f"Specular texture found: {s_path}")
        patch_dds_flags(s_path)
        tex_s = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex_s.image = bpy.data.images.load(s_path)
        tex_s.image.colorspace_settings.name = 'Non-Color'

        if is_blender_4():  # Handle Blender 4.0+ specular inputs
            mat.node_tree.links.new(bsdf.inputs['Specular Tint'], tex_s.outputs['Color'])
            # mat.node_tree.links.new(bsdf.inputs['IOR'], tex_s.outputs['Alpha']) # Connect the alpha properly to Specular IOR Level
        else:
            mat.node_tree.links.new(bsdf.inputs['Specular'], tex_s.outputs['Color'])
            mat.node_tree.links.new(bsdf.inputs['Specular Tint'], tex_s.outputs['Alpha'])

# ==================
# TOMB RAIDER STUFF
# ==================

# Import a Tomb Raider model!
def import_tr_model(file_path: str, use_custom_normals: bool = False, assign_material_colors: bool = True, import_textures: bool = True):
    """Import a TRM model and construct it in Blender."""
    print(f"\nIMPORTING TRM MODEL: {file_path}...\n")

    # Load model using TRM parser
    model = TRM(file_path)

    # Extract data from the TRM parser
    model_data = {
        "filepath": model.model_file,
        "vertices": model.mesh_data[0]["vertices"],
        "faces": model.mesh_data[0]["faces"],
        "normals": model.mesh_data[0]["normals"],
        "uv_map": model.mesh_data[0]["uv_map"],
        "bone_indices": model.mesh_data[0].get("bone_indices", []),
        "bone_weights": model.mesh_data[0].get("bone_weights", []),
        "textures": model.mesh_data[0]["textures"],
        "material_index": model.mesh_data[0]["material_index"]
    }

    # Create mesh and object for Blender
    mesh_name = os.path.splitext(os.path.basename(file_path))[0]
    mesh = bpy.data.meshes.new(name=mesh_name)
    obj = bpy.data.objects.new(mesh_name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    # obj.rotation_euler[0] += math.radians(-90)
    # obj.scale = (0.10, 0.10, 0.10)

    # Build the mesh (vertices, faces, normals, UVs, etc.)
    build_mesh_from_data(mesh, obj, model_data, use_custom_normals, assign_material_colors)

    # Add textures to the materials
    texture_directory = os.path.join(os.path.dirname(os.path.dirname(file_path)), 'TEX')

    if import_textures and "textures" in model_data:
        for i, texture_name in enumerate(model_data["textures"]):
            sanitized_name = ''.join(c for c in texture_name if c.isprintable())
            mat = obj.data.materials[i]
            import_tr_textures(mat, texture_directory, sanitized_name)

    print("\nMODEL IMPORT COMPLETE!")
    return {'FINISHED'}

# Import (a) Tomb Raider texture(s)!
def import_tr_textures(mat: bpy.types.Material, tex_dir: str, base_name: str):
    mat.use_nodes = True

    # Remove Principled BSDF
    for node in mat.node_tree.nodes:
        mat.node_tree.nodes.remove(node)

    # Add Diffuse BSDF
    diffuse_bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfDiffuse")
    output = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(output.inputs['Surface'], diffuse_bsdf.outputs['BSDF'])

    # Diffuse Map
    tex_path = os.path.join(tex_dir, base_name + ".DDS")
    if os.path.exists(tex_path):
        print(f"Texture found: {tex_path}")
        patch_dds_flags(tex_path)
        tex_image = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex_image.image = bpy.data.images.load(tex_path)
        mat.node_tree.links.new(diffuse_bsdf.inputs['Color'], tex_image.outputs['Color'])
    else:
        print(f"Texture not found for {base_name}")

# Build the models!
def build_mesh_from_data(mesh, obj, model_data, use_custom_normals, assign_material_colors):
    """Build the mesh from parsed data."""
    # Handle vertices, faces, normals, and materials
    if use_custom_normals is False:
        mesh.from_pydata(model_data["vertices"], [], model_data["faces"])
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        if not is_blender_4_1():    # Blender 4.1 removed "use_auto_smooth" which was used on previous versions of the program.
            mesh.use_auto_smooth = True
        mesh.normals_split_custom_set_from_vertices(model_data["normals"])
        print("  Parsed vertices and faces with normals from the model.")
    else:
        shade_flat = False
        mesh.from_pydata(model_data["vertices"], [], model_data["faces"], shade_flat)
        print("  Parsed vertices and faces with custom normals.")

    # Add the UV map
    if "uv_map" in model_data:
        uv_map = model_data["uv_map"]
        uv_layer = mesh.uv_layers.new(name="UV_01")
        for loop in mesh.loops:
            uv_layer.data[loop.index].uv = uv_map[loop.vertex_index]

    # Handle weights
    if "bone_indices" in model_data and "bone_weights" in model_data:
        add_model_weights(obj, model_data["bone_indices"], model_data["bone_weights"])

    # Handle materials
    if "textures" in model_data:
        # Create materials and add them to the object
        materials = []
        for texture_name in model_data["textures"]:
            sanitized_name = ''.join(c for c in texture_name if c.isprintable())
            mat = create_material(sanitized_name, assign_material_colors)
            add_material(mat, obj)
            materials.append(mat)

        # Now assign materials to the faces based on the material index
        for poly in mesh.polygons:
            # Find material index for the current face
            first_vertex = poly.vertices[0]
            mat_index = model_data["material_index"][first_vertex] - 1
            if mat_index < 0 or mat_index >= len(materials):
                print(f"Warning: Material index {mat_index + 1} is invalid at face {poly.index}.")
                mat_index = 0  # Assign to the first material if invalid
            poly.material_index = mat_index

    mesh.calc_tangents()
    mesh.update()