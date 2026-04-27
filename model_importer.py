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
from .tmt_parser import *

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

def calculate_aod_parent(bone_index: int, hierarchy_flags: list[int]) -> int:
    """
    Translates the original C++ flag-based hierarchy logic to Python.
    Calculates the correct parent bone index based on the hierarchy flags.
    """
    if bone_index == 0:
        return 0

    flag = hierarchy_flags[bone_index]
    root_bone = 0
    ignore = 0

    # These values indicate direct dependence on the superior (previous) bone
    if flag in {0xC0, 0xC1, 0x00, 0x28, 0x01, 0x0400, 0x0401}:
        return bone_index - 1

    if flag in {0x03, 0x02}:
        for i in range(bone_index - 1, -1, -1):
            if hierarchy_flags[i] == 0x02:
                ignore += 1
            elif hierarchy_flags[i] == 0x01:
                ignore -= 1
            
            if hierarchy_flags[i] == 0x01 and ignore <= 0:
                return i - 1
        return root_bone

    if flag in {0x403, 0x402}:
        for i in range(bone_index - 1, -1, -1):
            if hierarchy_flags[i] == 0x402:
                ignore += 1
            elif hierarchy_flags[i] == 0x401:
                ignore -= 1
            
            if hierarchy_flags[i] == 0x401 and ignore <= 0:
                return i - 1
        return root_bone

    if flag in {0xC3, 0xC2}:
        for i in range(bone_index - 1, -1, -1):
            if hierarchy_flags[i] == 0xC2:
                ignore += 1
            elif hierarchy_flags[i] == 0xC1:
                ignore -= 1
            
            if hierarchy_flags[i] == 0xC1 and ignore <= 0:
                return i - 1
        return root_bone

    if flag in {0x2A, 0x2B}:
        for i in range(bone_index - 1, -1, -1):
            if hierarchy_flags[i] == 0x01:
                return i - 1
        return root_bone

    # If nothing matches, return HIP (bone 0)
    return 0

def build_aod_skeleton(skeleton_data: list[dict]) -> tuple[bpy.types.Object, list[Vector]]:
    print("\nConstructing Angel of Darkness Armature...")
    
    arm_data = bpy.data.armatures.new("Armature")
    arm_obj = bpy.data.objects.new("Armature", arm_data)
    arm_obj.show_in_front = True
    arm_obj.scale = (0.10, 0.10, 0.10)
    
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    edit_bones = arm_data.edit_bones
    bone_refs = []
    
    hierarchy_flags = [bone.get("flags", 0) for bone in skeleton_data]
    parents = [calculate_aod_parent(i, hierarchy_flags) for i in range(len(skeleton_data))]

    abs_translations = []
    for i, bone_dict in enumerate(skeleton_data):
        local_trans = Vector(bone_dict.get("bind_pose", [[0]*4]*4)[3][:3])
        p_idx = parents[i]
        
        if i != 0 and p_idx < len(abs_translations):
            abs_translations.append(abs_translations[p_idx] + local_trans)
        else:
            abs_translations.append(local_trans)

    for i, bone_dict in enumerate(skeleton_data):
        b_name = bone_dict.get("name", f"bone_{i}")
        bone = edit_bones.new(b_name)
        bone_refs.append(bone)
        
        if i != 0 and parents[i] < len(bone_refs):
            bone.parent = bone_refs[parents[i]]

        # Build in raw space. Object transforms handle the visual fix.
        bone.head = abs_translations[i]
        
        children = [j for j, p in enumerate(parents) if p == i and j != i]
        if children:
            bone.tail = abs_translations[children[0]]
        else:
            bone.tail = bone.head + Vector((0, 5.0, 0))

        if (bone.tail - bone.head).length < 0.01:
            bone.tail = bone.head + Vector((0, 5.0, 0))

    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"Successfully generated {len(bone_refs)} bones.\n")
    
    return arm_obj, abs_translations

def process_aod_face_data(indices: list[int], submesh_runs: list[dict], local_mat_indices: dict, vertex_offset: int = 0) -> tuple[list[tuple], list[tuple], list[int]]:
    edges = []
    faces = []
    material_indices = []
    
    for run in submesh_runs:
        offset = run.get("indices_start", run.get("offset", 0))
        count = run.get("face_count", run.get("count", 0))
        f_type = run.get("face_type", 5) 
        
        global_mat_idx = run.get("material_index", 0)
        local_mat_idx = local_mat_indices.get(global_mat_idx, 0)
        
        run_indices = indices[offset : offset + count]
        if not run_indices:
            continue

        if f_type == 1:
            continue
        elif f_type == 2:
            for i in range(0, len(run_indices) - 1, 2):
                edges.append((run_indices[i] + vertex_offset, run_indices[i+1] + vertex_offset))
        elif f_type == 3:
            for i in range(len(run_indices) - 1):
                edges.append((run_indices[i] + vertex_offset, run_indices[i+1] + vertex_offset))
        elif f_type == 4:
            for i in range(0, len(run_indices) - 2, 3):
                # Flipped from [i, i+1, i+2] to [i, i+2, i+1] to invert winding
                faces.append((run_indices[i] + vertex_offset, run_indices[i+2] + vertex_offset, run_indices[i+1] + vertex_offset))
                material_indices.append(local_mat_idx)
        elif f_type == 5:
            for i in range(len(run_indices) - 2):
                v1, v2, v3 = run_indices[i], run_indices[i+1], run_indices[i+2]
                if v1 != v2 and v2 != v3 and v1 != v3:
                    # Winding flips inverted from the previous implementation
                    if i % 2 == 0:
                        faces.append((v1 + vertex_offset, v3 + vertex_offset, v2 + vertex_offset))
                    else:
                        faces.append((v1 + vertex_offset, v2 + vertex_offset, v3 + vertex_offset))
                    material_indices.append(local_mat_idx)
        elif f_type == 6:
            v_center = run_indices[0] + vertex_offset
            for i in range(1, len(run_indices) - 1):
                v2, v3 = run_indices[i] + vertex_offset, run_indices[i+1] + vertex_offset
                if v_center != v2 and v2 != v3 and v_center != v3:
                    # Flipped from [v_center, v2, v3] to [v_center, v3, v2]
                    faces.append((v_center, v3, v2))
                    material_indices.append(local_mat_idx)
                    
    return edges, faces, material_indices

def build_aod_meshes(model_data, arm_obj: bpy.types.Object, global_matrix: Matrix, abs_translations: list[Vector]):
    print("\nBuilding Angel of Darkness Meshes...")
    
    bone_names = [b.name for b in arm_obj.data.bones]
    SCALE_FIX = 2048.0
    
    scene_materials = {}

    def get_or_create_material(global_mat_idx: int) -> bpy.types.Material:
        if global_mat_idx not in scene_materials:
            mat = bpy.data.materials.new(name=f"Material_{global_mat_idx}")
            scene_materials[global_mat_idx] = mat
        return scene_materials[global_mat_idx]

    # ========================================
    # PROCESS MESH 1 (Dual-Weighted Skinned)
    # ========================================
    if hasattr(model_data, 'mesh1') and model_data.mesh1:
        for m1_idx, m1 in enumerate(model_data.mesh1):
            v_count = m1.get("vertex_count", 0)
            if v_count == 0: continue
                
            master_verts = []
            master_normals = []
            master_uvs = []
            master_weights = defaultdict(list)
                
            p1_list = m1.get("primary_vertices", [])
            p2_list = m1.get("secondary_vertices", [])
            n1_list = m1.get("primary_normals", [])
            n2_list = m1.get("secondary_normals", [])
            bw_list = m1.get("bone_weights", [])
            bi_list = m1.get("bone_indices", [])
            uv_list = m1.get("uv_map", [])
            
            for v_idx in range(v_count):
                p1 = Vector(p1_list[v_idx]) * SCALE_FIX
                p2 = Vector(p2_list[v_idx]) * SCALE_FIX
                
                b1_idx = bi_list[v_idx][0]
                b2_idx = bi_list[v_idx][1]
                w1 = bw_list[v_idx]
                w2 = 1.0 - w1
                
                t1 = abs_translations[b1_idx] if b1_idx < len(abs_translations) else Vector()
                t2 = abs_translations[b2_idx] if b2_idx < len(abs_translations) else Vector()
                
                world_p1 = p1 + t1
                world_p2 = p2 + t2
                
                final_pos = (world_p1 * w1) + (world_p2 * w2)
                master_verts.append(final_pos)
                
                n1 = Vector(n1_list[v_idx])
                n2 = Vector(n2_list[v_idx])
                final_norm = (n1 * w1) + (n2 * w2)
                master_normals.append(final_norm.normalized())
                
                master_uvs.append(uv_list[v_idx] if v_idx < len(uv_list) else (0.0, 0.0))
                
                if w1 > 0 and b1_idx < len(bone_names): master_weights[b1_idx].append((v_idx, w1))
                if w2 > 0 and b2_idx < len(bone_names): master_weights[b2_idx].append((v_idx, w2))

            mesh = bpy.data.meshes.new(f"AoD_SkinnedMesh_{m1_idx}")
            local_mat_indices = {}
            
            submesh_runs = m1.get("submeshes", [])
            for run in submesh_runs:
                mat_idx = run.get("material_index", 0)
                if mat_idx not in local_mat_indices:
                    mat = get_or_create_material(mat_idx)
                    mesh.materials.append(mat)
                    local_mat_indices[mat_idx] = len(mesh.materials) - 1

            faces_data = m1.get("faces", [])
            edges, faces, poly_mat_indices = process_aod_face_data(faces_data, submesh_runs, local_mat_indices)
            
            mesh.from_pydata(master_verts, edges, faces)
            mesh.update()
            
            if len(master_normals) == len(master_verts):
                mesh.normals_split_custom_set_from_vertices(master_normals)
            
            obj = bpy.data.objects.new(f"AoD_SkinnedMesh_{m1_idx}", mesh)
            bpy.context.scene.collection.objects.link(obj)
            
            for poly_idx, poly in enumerate(mesh.polygons):
                if poly_idx < len(poly_mat_indices):
                    poly.material_index = poly_mat_indices[poly_idx]
                    
            if any(master_uvs):
                uv_layer = mesh.uv_layers.new(name="UVMap")
                for loop in mesh.loops:
                    uv_layer.data[loop.index].uv = (master_uvs[loop.vertex_index][0], 1.0 - master_uvs[loop.vertex_index][1])

            for b_idx, weight_list in master_weights.items():
                vg = obj.vertex_groups.new(name=bone_names[b_idx])
                for vert_idx, weight in weight_list:
                    vg.add([vert_idx], weight, 'REPLACE')
            
            # Normalize vertex groups using utility function
            #normalize_vertex_groups(obj)
                    
            obj.parent = arm_obj
            mod = obj.modifiers.new(name="Armature", type='ARMATURE')
            mod.object = arm_obj

    # ========================================
    # PROCESS MESH 2 (Single-Weighted Rigged)
    # Builds EACH submesh as its own distinct object named via its Hash ID
    # ========================================
    if hasattr(model_data, 'mesh2') and model_data.mesh2:
        for m2 in model_data.mesh2:
            v_list = m2.get("vertices", [])
            if not v_list: continue
            
            # Extract Hash/Mesh ID
            mesh_hash = m2.get("mesh_id", 0)
            obj_name = f"{mesh_hash:X}" if isinstance(mesh_hash, int) else str(mesh_hash)

            master_verts = []
            master_normals = []
            master_uvs = []
            master_weights = defaultdict(list)
            
            target_bone = m2.get("parent_bone", 0)
            t1 = abs_translations[target_bone] if target_bone < len(abs_translations) else Vector()
            
            uv_list = m2.get("uv_map", [])
            n_list = m2.get("normals", [])
            
            for v_idx, v in enumerate(v_list):
                local_pos = Vector(v) * SCALE_FIX
                master_verts.append(local_pos + t1)
                
                if v_idx < len(n_list):
                    master_normals.append(Vector(n_list[v_idx]).normalized())
                else:
                    master_normals.append(Vector((0.0, 0.0, 1.0)))
                
                master_uvs.append(uv_list[v_idx] if v_idx < len(uv_list) else (0.0, 0.0))
                
                if target_bone < len(bone_names):
                    master_weights[target_bone].append((v_idx, 1.0))
                
            mesh = bpy.data.meshes.new(f"Mesh_{obj_name}")
            local_mat_indices = {}
            
            submesh_runs = m2.get("submesh_runs", [])
            for run in submesh_runs:
                mat_idx = run.get("material_index", 0)
                if mat_idx not in local_mat_indices:
                    mat = get_or_create_material(mat_idx)
                    mesh.materials.append(mat)
                    local_mat_indices[mat_idx] = len(mesh.materials) - 1
def build_aod_meshes(model_data, arm_obj: bpy.types.Object, abs_translations: list[Vector], use_custom_normals: bool = False):
    print("\nBuilding Angel of Darkness Meshes...")
    
    bone_names = [b.name for b in arm_obj.data.bones]
    SCALE_FIX = 2048.0

    def finalize_materials_and_bones(mesh, obj, poly_mat_indices, local_mats_map):
        """ Handles the per-polygon material assignment and renames the vertex groups 
            created by add_model_weights back to their actual string names. """
        sorted_mat_indices = sorted(local_mats_map.keys())
        mat_idx_to_slot = {}
        
        for g_idx in sorted_mat_indices:
            mat_name = f"Material_{g_idx}"
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                mat = bpy.data.materials.new(name=mat_name)
            mesh.materials.append(mat)
            mat_idx_to_slot[g_idx] = len(mesh.materials) - 1
            
        for poly_idx, poly in enumerate(mesh.polygons):
            if poly_idx < len(poly_mat_indices):
                poly.material_index = mat_idx_to_slot.get(poly_mat_indices[poly_idx], 0)
                
        for vg in obj.vertex_groups:
            if vg.name.startswith("bone_"):
                try:
                    b_idx = int(vg.name.split("_")[1])
                    if b_idx < len(bone_names):
                        vg.name = bone_names[b_idx]
                except ValueError:
                    pass

    # ========================================
    # PROCESS MESH 1 (Dual-Weighted Skinned)
    # ========================================
    if hasattr(model_data, 'mesh1') and model_data.mesh1:
        for m1_idx, m1 in enumerate(model_data.mesh1):
            v_count = m1.get("vertex_count", 0)
            if v_count == 0: continue
                
            master_dict = {
                "vertices": [], "normals": [], "uv_map": [], 
                "bone_indices": [], "bone_weights": [], "faces": []
            }
                
            p1_list = m1.get("primary_vertices", [])
            p2_list = m1.get("secondary_vertices", [])
            n1_list = m1.get("primary_normals", [])
            n2_list = m1.get("secondary_normals", [])
            bw_list = m1.get("bone_weights", [])
            bi_list = m1.get("bone_indices", [])
            uv_list = m1.get("uv_map", [])
            
            for v_idx in range(v_count):
                p1 = Vector(p1_list[v_idx]) * SCALE_FIX
                p2 = Vector(p2_list[v_idx]) * SCALE_FIX
                
                b1_idx = bi_list[v_idx][0]
                b2_idx = bi_list[v_idx][1]
                w1 = bw_list[v_idx]
                w2 = 1.0 - w1
                
                t1 = abs_translations[b1_idx] if b1_idx < len(abs_translations) else Vector()
                t2 = abs_translations[b2_idx] if b2_idx < len(abs_translations) else Vector()
                
                final_pos = ((p1 + t1) * w1) + ((p2 + t2) * w2)
                master_dict["vertices"].append(final_pos)
                
                n1 = Vector(n1_list[v_idx])
                n2 = Vector(n2_list[v_idx])
                master_dict["normals"].append((n1 * w1) + (n2 * w2))
                
                master_dict["uv_map"].append(uv_list[v_idx] if v_idx < len(uv_list) else (0.0, 0.0))
                
                # Format for add_model_weights (expects integers mapped to 255)
                master_dict["bone_indices"].append([b1_idx, b2_idx])
                master_dict["bone_weights"].append([int(w1 * 255.0), int(w2 * 255.0)])

            submesh_runs = m1.get("submeshes", [])
            run_local_mats = {run.get("material_index", 0): run.get("material_index", 0) for run in submesh_runs}
            
            edges, faces, poly_mat_indices = process_aod_face_data(m1.get("faces", []), submesh_runs, run_local_mats)
            master_dict["faces"] = faces
            
            mesh = bpy.data.meshes.new(f"AoD_SkinnedMesh_{m1_idx}")
            obj = bpy.data.objects.new(f"AoD_SkinnedMesh_{m1_idx}", mesh)
            bpy.context.scene.collection.objects.link(obj)
            
            # Delegate entirely to your global utility
            build_mesh_from_data(mesh, obj, master_dict, use_custom_normals=use_custom_normals)
            finalize_materials_and_bones(mesh, obj, poly_mat_indices, run_local_mats)
                    
            obj.parent = arm_obj
            mod = obj.modifiers.new(name="Armature", type='ARMATURE')
            mod.object = arm_obj

    # ========================================
    # PROCESS MESH 2 (Single-Weighted Rigged)
    # Builds EACH submesh as its own distinct object named via its Hash ID
    # ========================================
    if hasattr(model_data, 'mesh2') and model_data.mesh2:
        for m2 in model_data.mesh2:
            v_list = m2.get("vertices", [])
            if not v_list: continue
            
            mesh_hash = m2.get("mesh_id", 0)
            obj_name = f"{mesh_hash:X}" if isinstance(mesh_hash, int) else str(mesh_hash)

            master_dict = {
                "vertices": [], "normals": [], "uv_map": [], 
                "bone_indices": [], "bone_weights": [], "faces": []
            }
            
            target_bone = m2.get("parent_bone", 0)
            t1 = abs_translations[target_bone] if target_bone < len(abs_translations) else Vector()
            
            uv_list = m2.get("uv_map", [])
            n_list = m2.get("normals", [])
            
            for v_idx, v in enumerate(v_list):
                local_pos = Vector(v) * SCALE_FIX
                master_dict["vertices"].append(local_pos + t1)
                
                if v_idx < len(n_list):
                    master_dict["normals"].append(Vector(n_list[v_idx]))
                else:
                    master_dict["normals"].append(Vector((0.0, 0.0, 1.0)))
                
                master_dict["uv_map"].append(uv_list[v_idx] if v_idx < len(uv_list) else (0.0, 0.0))
                
                master_dict["bone_indices"].append([target_bone])
                master_dict["bone_weights"].append([255])
                
            submesh_runs = m2.get("submesh_runs", [])
            run_local_mats = {run.get("material_index", 0): run.get("material_index", 0) for run in submesh_runs}
            
            edges, faces, poly_mat_indices = process_aod_face_data(m2.get("faces", []), submesh_runs, run_local_mats)
            master_dict["faces"] = faces
            
            mesh = bpy.data.meshes.new(f"Mesh_{obj_name}")
            obj = bpy.data.objects.new(f"Mesh_{obj_name}", mesh)
            bpy.context.scene.collection.objects.link(obj)
            
            build_mesh_from_data(mesh, obj, master_dict, use_custom_normals=use_custom_normals)
            finalize_materials_and_bones(mesh, obj, poly_mat_indices, run_local_mats)
                    
            obj.parent = arm_obj
            mod = obj.modifiers.new(name="Armature", type='ARMATURE')
            mod.object = arm_obj

    print("Master Mesh generation complete.")

def import_aodr_model(file_path: str, custom_normals: bool = False, random_material_colors: bool = True, texture_import: bool = True):
    print(f"\nIMPORTING ANGEL OF DARKNESS CHR: {file_path}...\n")

    model = CHR(file_path=file_path, custom_normals=custom_normals, random_material_colors=random_material_colors, texture_import=texture_import)

    if not hasattr(model, 'skeleton') or not model.skeleton:
        print("ERROR: No skeleton data found in the parsed CHR file!")
        return {'CANCELLED'}

    armature_obj, abs_translations = build_aod_skeleton(skeleton_data=model.skeleton)
    build_aod_meshes(model, armature_obj, abs_translations, use_custom_normals=custom_normals)

    print("MODEL IMPORT COMPLETE!")
    return {'FINISHED'}

def import_aodr_morph(file_path: str):
    """
    Imports a TMT morph file, validates the linked submesh by its hash and vertex count,
    and applies the delta offsets as Blender Shape Keys.
    """
    print(f"\nIMPORTING ANGEL OF DARKNESS MORPH: {file_path}...\n")
    
    # Parse the TMT
    tmt = TMT(file_path=file_path)
    
    if not tmt.morph_data:
        print("[!] ERROR: No morph data parsed.")
        return {'CANCELLED'}
        
    data = tmt.morph_data[0]
    mesh_hash = data["linked_submesh_hash"]
    target_name = f"Mesh_{mesh_hash:X}"
    v_count = data["vertex_count"]
    
    # 1. Lookup the object in the current scene
    obj = bpy.data.objects.get(target_name)
    
    if not obj:
        print(f"[!] ERROR: Linked submesh '{target_name}' not found in the scene.")
        print(f"    Ensure the .CHR model is imported before importing its morphs.")
        return {'CANCELLED'}
        
    if obj.type != 'MESH':
        print(f"[!] ERROR: Object '{target_name}' is not a Mesh.")
        return {'CANCELLED'}
        
    mesh = obj.data
    
    # 2. Strict Vertex Count Validation
    if len(mesh.vertices) != v_count:
        print(f"[!] ERROR: Vertex count mismatch!")
        print(f"    TMT expects: {v_count}")
        print(f"    '{target_name}' has: {len(mesh.vertices)}")
        return {'CANCELLED'}
        
    # 3. Apply Shape Keys
    print(f"Applying {data['morph_target_count']} morph targets to '{target_name}'...")
    
    # Ensure there is a 'Basis' shape key to anchor the morphs
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis")
        
    basis_block = obj.data.shape_keys.key_blocks["Basis"]
    
    # Iterate through the delta shapes and apply them
    for morph_idx, morph in enumerate(data["morph_targets"]):
        # Create a new shape key for this morph
        key_name = f"Key {morph_idx + 1}"
        
        # If the user imports the same TMT twice, avoid duplicating keys infinitely
        if key_name in obj.data.shape_keys.key_blocks:
            sk = obj.data.shape_keys.key_blocks[key_name]
        else:
            sk = obj.shape_key_add(name=key_name)
        
        # Apply the delta offsets to the basis coordinates
        for i in range(v_count):
            delta = Vector(morph["vertices"][i])
            
            # shape_key.data[i].co takes absolute local coordinates, not deltas. 
            # So we add the scaled delta to the basis coordinate.
            sk.data[i].co = basis_block.data[i].co + delta
            
    print("MORPH IMPORT COMPLETE!")
    return {'FINISHED'}

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