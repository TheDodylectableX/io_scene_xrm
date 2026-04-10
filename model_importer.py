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

from mathutils import Vector, Matrix
from itertools import chain
from collections import defaultdict

from .srm_parser import *
from .trm_parser import *
from .chr_parser import *

from .bpy_util_funcs import *

# ------------------------------------------------

# ==================
# SOUL REAVER STUFF
# ==================

# Import a Soul Reaver model!
def import_sr_model(file_path: str, game: str, import_skeleton: bool = True, import_lods: bool = True, use_custom_normals: bool = False, assign_material_colors: bool = True, import_textures: bool = True):
    """Import an SRM model (and its LODs) and construct it in Blender."""
    print(f"\nIMPORTING SOUL REAVER MODEL: {file_path}...\n")

    # Load model using SRM parser
    model = SRM(
        file_path=file_path, 
        game_of_model=game, 
        skeleton_import=import_skeleton, 
        lod_import=import_lods, 
        custom_normals=use_custom_normals, 
        random_material_colors=assign_material_colors, 
        texture_import=import_textures
    )

    base_mesh_name = os.path.splitext(os.path.basename(file_path))[0]
    master_armature = None

    # -- 1. BUILD THE MASTER SKELETON (ONCE) --
    # We only need to build the skeleton one time. We'll use LOD 0's data 
    # since bone coordinates are identical across LODs.
    if import_skeleton and model.mesh_data:
        # Pass the first LOD's data to build the bones
        master_armature = build_sr_skeleton(model_data=model.mesh_data[0])

    # -- 2. BUILD THE MESHES (LOD LOOP) --
    for index, mesh_chunk in enumerate(model.mesh_data):
        
        # Safely grab the lod_level from our parser, fallback to loop index
        lod_level = mesh_chunk.get("lod_level", index)
        mesh_name = f"{base_mesh_name}_LOD_{lod_level}"
        
        print(f"Building geometry for: {mesh_name}...")

        # Extract data for this specific LOD
        model_data = {
            "filepath": model.model_file,
            "vertices": mesh_chunk["vertices"],
            "faces": mesh_chunk["faces"],
            "normals": mesh_chunk["normals"],
            "uv_map": mesh_chunk.get("uv_map", []),
            "bone_indices": mesh_chunk.get("bone_indices", []),
            "bone_weights": mesh_chunk.get("bone_weights", []),
            "textures": mesh_chunk.get("textures", []),
            "material_index": mesh_chunk.get("material_index", []),
            "bone_matrices": mesh_chunk.get("bone_matrices", []),
            "bone_flags": mesh_chunk.get("bone_flags", []),
        }

        # Create mesh and object for Blender
        mesh = bpy.data.meshes.new(name=mesh_name)
        obj = bpy.data.objects.new(mesh_name, mesh)
        bpy.context.scene.collection.objects.link(obj)

        # Build the geometry, UVs, weights, and base materials
        build_mesh_from_data(
            mesh=mesh, 
            obj=obj, 
            model_data=model_data, 
            game=game, 
            use_custom_normals=use_custom_normals, 
            assign_material_colors=assign_material_colors
        )
        
        # Parent this LOD to the master armature
        if master_armature is not None:
            setup_armature_modifier(mesh_obj=obj, arm_obj=master_armature)

        # -- 3. TEXTURE ASSIGNMENT --
        if game == GAME_SR3:
            texture_directory = os.path.join(os.path.dirname(os.path.dirname(file_path)), 'TEX_HD')
        else:
            texture_directory = os.path.join(os.path.dirname(os.path.dirname(file_path)), 'TEX')

        if import_textures and "textures" in model_data:
            for i, texture_name in enumerate(model_data["textures"]):
                # Ensure we don't go out of bounds if the material generation failed or was skipped
                if i < len(obj.data.materials):
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

    # To do: Emissive and wiring gloss

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
    print(f"\nIMPORTING TOMB RAIDER MODEL: {file_path}...\n")

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

    # Build the mesh (vertices, faces, normals, UVs, etc.)
    build_mesh_from_data(mesh=mesh, obj=obj, model_data=model_data, use_custom_normals=use_custom_normals, assign_material_colors=assign_material_colors)

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
    # To do: Use Principled BSDF instead and handle alpha
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

# ========================
# ANGEL OF DARKNESS STUFF
# ========================

# -----------------------------------------------------------------------------------------------------------------------

# Build the models!
def build_mesh_from_data(mesh, obj, model_data, game=None, use_custom_normals=False, assign_material_colors=True):
    """
    Build the mesh from parsed data.
    Default arguments (game=None, etc.) ensure compatibility with Tomb Raider importers.
    """

    # -- GEOMETRY & NORMALS ---------------------------------------------------
    # Logic for handling normals varies by Blender version and user preference
    if use_custom_normals is False:
        mesh.from_pydata(model_data["vertices"], [], model_data["faces"])
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        
        # Blender 4.1+ removed 'use_auto_smooth' in favor of a modifier/node setup
        # but we check for older versions to maintain compatibility
        if not is_blender_4_1():
            mesh.use_auto_smooth = True
            
        # Apply the normals parsed from the SRM/TRM file
        if "normals" in model_data and model_data["normals"]:
            mesh.normals_split_custom_set_from_vertices(model_data["normals"])
            print("  Parsed vertices and faces with normals from the model.")
    else:
        # Default Blender calculated normals
        shade_flat = False
        mesh.from_pydata(model_data["vertices"], [], model_data["faces"])
        print("  Parsed vertices and faces with Blender-calculated normals.")

    # -- UV MAPS -------------------------------------------------------------
    if "uv_map" in model_data:
        uv_map = model_data["uv_map"]
        uv_layer = mesh.uv_layers.new(name="UV_01")
        for loop in mesh.loops:
            uv_layer.data[loop.index].uv = uv_map[loop.vertex_index]

    # -- VERTEX WEIGHTS ------------------------------------------------------
    if "bone_indices" in model_data and "bone_weights" in model_data:
        add_model_weights(obj, model_data["bone_indices"], model_data["bone_weights"])

    # -- MATERIALS -----------------------------------------------------------
    if "textures" in model_data:
        materials = []
        for texture_name in model_data["textures"]:
            sanitized_name = ''.join(c for c in texture_name if c.isprintable())
            mat = create_material(sanitized_name, assign_material_colors)
            add_material(mat, obj)
            materials.append(mat)

        # Assign materials to faces based on the material index
        for poly in mesh.polygons:
            first_vertex = poly.vertices[0]
            raw_index = model_data["material_index"][first_vertex]

            if game == GAME_SR3:
                mat_index = raw_index
            else:
                mat_index = raw_index - 1

            # Validation & Assignment
            if 0 <= mat_index < len(materials):
                poly.material_index = mat_index
            else:
                # Fallback to avoid out-of-bounds crashes in Blender
                poly.material_index = 0

    mesh.calc_tangents()
    mesh.update()

# Legacy of Kain: Build the skeleton!
def build_sr_skeleton(model_data):
    print("\nConstructing Armature...")
    arm_data = bpy.data.armatures.new("Armature")
    arm_obj = bpy.data.objects.new("Armature", arm_data)
    arm_obj.show_in_front = True
    bpy.context.scene.collection.objects.link(arm_obj)
    
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    edit_bones = arm_data.edit_bones
    bones_list = []
    
    rot_matrix = Matrix.Rotation(math.radians(-90), 4, 'X')
    
    bone_entries = model_data.get("bone_matrices", [])
    
    # Create all 128 bones (4 per entry) to match the flag block and vertex groups
    for entry_idx, rows in enumerate(bone_entries):
        for row_idx, loc in enumerate(rows):
            abs_idx = (entry_idx * 4) + row_idx
            
            bone_name = f"bone_{abs_idx}"
            bone = edit_bones.new(bone_name)

            # hx = X, hy = Z, hz = -Y
            raw_pos = Vector((float(loc[0]), float(loc[2]), -float(loc[1])))
            
            # Apply the -90 degree X rotation in Edit Mode
            final_pos = rot_matrix @ raw_pos
            bone.head = final_pos
            
            # Handle the tail
            raw_tail = raw_pos + Vector((0, 10, 0))
            bone.tail = rot_matrix @ raw_tail
            
            bones_list.append(bone)

    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"Generated {len(bones_list)} bones at 1:1 scale.")
    
    # Return the armature object so the importer loop can parent LODs to it
    return arm_obj

def setup_armature_modifier(mesh_obj, arm_obj):
    # Add the modifier to the mesh
    mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
    mod.object = arm_obj
    
    # Set the mesh as a child of the armature
    mesh_obj.parent = arm_obj