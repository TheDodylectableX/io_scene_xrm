# ------------------------------------------------
#   MODEL EXPORTER
#       Takes Blender objects and exports them
#       into the games' formats.
# ------------------------------------------------
"""Takes Blender objects and exports them into the games' formats"""

import os
import bpy
import time

from .writers import *
from .bpy_util_funcs import *

EXPORTER_SHADER_COUNT = 1

import os
import bpy
import struct
import time
from .writers import Writer
from .bpy_util_funcs import *

def export_sr_model(self, context, file_path: str, reference_srm_path: str) -> set[str]:
    """
    Export Blender objects to the SRM format and copying existing skeleton data from original SRMs
    """
    start_time = time.time()
    print(f"\nStarting Export to: {file_path}...")

    # ---------------------------------------------------------
    # 1. VALIDATION & REFERENCE PARSING
    # ---------------------------------------------------------
    if not os.path.exists(reference_srm_path):
        self.report({'ERROR'}, f"Reference file not found: {reference_srm_path}")
        return {'CANCELLED'}

    # Collect all mesh objects to export
    objects_to_export = [obj for obj in context.scene.objects if obj.type == 'MESH' and not obj.hide_get()]
    if not objects_to_export:
        self.report({'ERROR'}, "No visible Mesh objects found in scene to export.")
        return {'CANCELLED'}

    # Extract the Bone/Matrix Blob from the original file
    blob_data = b""
    try:
        with open(reference_srm_path, 'rb') as ref:
            ref_data = ref.read()
            curr = 4 # Skip Magic 'SRM '
            
            # Skip Shaders
            shaderCount = struct.unpack_from('<I', ref_data, curr)[0]
            curr += 4 + (shaderCount * 44)
            
            # Skip Textures
            textureCount = struct.unpack_from('<I', ref_data, curr)[0]
            curr += 4 + (textureCount * 32)
            
            # Mark start of Bone/Matrix block
            blob_start = curr
            extraBoneCount = struct.unpack_from('<I', ref_data, curr)[0]
            curr += 4
            
            # Matrix count is always 32 + extraBoneCount
            matrixCount = 32 + extraBoneCount
            curr += matrixCount * 48
            
            # Check for the -0.0 Bone Transform (0x80000000)
            sentinel = struct.unpack_from('<I', ref_data, curr)[0]
            if sentinel == 0x80000000:
                curr += 4
            
            # Skip Bone Flags (128 bytes fixed)
            curr += 128
            blob_data = ref_data[blob_start:curr]
            print(f"  Captured Reference Bone Blob: {len(blob_data)} bytes")
            
    except Exception as e:
        self.report({'ERROR'}, f"Failed to parse reference SRM: {str(e)}")
        return {'CANCELLED'}

    # ---------------------------------------------------------
    # 2. DATA AGGREGATION
    # ---------------------------------------------------------

    total_vertices = []
    total_faces = []
    all_materials = []
    
    # Track the global vertex offset as we merge multiple Blender objects
    vert_offset = 0

    for obj_index, obj in enumerate(objects_to_export):
        mesh = obj.data
        
        # Ensure tangents are fresh for the (n*127)+127 packing
        try:
            mesh.calc_tangents()
        except:
            # Fallback for meshes without proper UVs
            mesh.calc_normals_split()

        # Build material list for the entire file
        for mat_slot in obj.material_slots:
            if mat_slot.material not in all_materials:
                all_materials.append(mat_slot.material)

        # Mapping face-materials to vertex IDs
        # Since SRM stores MatID at the vertex level, we'll map based on the 
        # first polygon that uses the vertex (common in game-dev binary packing).
        vert_to_mat = {}
        for poly in mesh.polygons:
            for vert_idx in poly.vertices:
                # SRM uses 1-based indexing for Materials in the vertex block
                vert_to_mat[vert_idx] = poly.material_index + 1

        # Process Vertices
        uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None

        unique_vertices = []
        vert_cache = {} 
        # total_faces is now local to this object loop, we'll extend the global list later
        obj_faces = []

        for poly in mesh.polygons:
            face_indices = []
            
            # 1-based Material ID for this face
            mat_id = poly.material_index + 1

            for loop_idx in poly.loop_indices:
                loop = mesh.loops[loop_idx]
                v = mesh.vertices[loop.vertex_index]
                
                # --- POSITION ---
                world_co = obj.matrix_world @ v.co
                
                # --- NORMALS & TANGENTS ---
                # Use loop-specific tangent to prevent tangent melting
                norm = (obj.matrix_world.to_3x3() @ v.normal).normalized()
                tang = [127, 127, 127]
                if uv_layer:
                    t = loop.tangent
                    tang = [int((t.x * 127) + 127), int((t.y * 127) + 127), int((t.z * 127) + 127)]

                # --- UVs ---
                uv = [uv_layer[loop_idx].uv[0], uv_layer[loop_idx].uv[1]] if uv_layer else [0.0, 0.0]

                # --- BONES & WEIGHTS ---
                b_indices = [0, 0, 0]
                b_weights = [0, 0, 0]
                bone_groups = []
                for g in v.groups:
                    group_name = obj.vertex_groups[g.group].name
                    if group_name.startswith("bone_"):
                        try:
                            bone_id = int(group_name.split("_")[1])
                            bone_groups.append((bone_id, g.weight))
                        except (IndexError, ValueError):
                            print(f"Warning: Group {group_name} format error.")

                sorted_groups = sorted(bone_groups, key=lambda x: x[1], reverse=True)[:3]
                for i, (b_id, weight) in enumerate(sorted_groups):
                    b_indices[i] = b_id
                    b_weights[i] = int(weight * 255)

                # --- VERTEX SPLITTING KEY ---
                # This key identifies unique combinations. If a vertex at a seam 
                # has 2 UVs, it will generate 2 unique entries in the cache.
                vert_key = (
                    tuple(round(c, 6) for c in world_co),
                    tuple(round(c, 4) for c in norm),
                    tuple(round(c, 6) for c in uv),
                    tuple(b_indices),
                    tuple(b_weights),
                    mat_id
                )

                if vert_key not in vert_cache:
                    vert_cache[vert_key] = len(unique_vertices)
                    unique_vertices.append({
                        'pos': world_co,
                        'tangent': tang,
                        'normal': [int((norm.x * 127) + 127), int((norm.y * 127) + 127), int((norm.z * 127) + 127)],
                        'mat_id': mat_id,
                        'bone_idx': b_indices,
                        'bone_weight': b_weights,
                        'uv': uv
                    })

                face_indices.append(vert_cache[vert_key] + vert_offset)

            obj_faces.append(face_indices)

        # Merge this object's data into the global lists
        total_vertices.extend(unique_vertices)
        total_faces.extend(obj_faces)
        
        # Update offset based on the number of unique vertices created (not mesh.vertices!)
        vert_offset += len(unique_vertices)

    # ---------------------------------------------------------
    # 3. BINARY WRITE
    # ---------------------------------------------------------
    try:
        with open(file_path, 'wb') as f:
            writer = Writer(f)
            
            # HEADER
            writer.ascii_string("SRM")
            writer.ubyte(1)
            
            # SHADERS (Single shader for the whole mesh)
            writer.uint32(1) # Shader Count
            writer.uint32(0) # Type
            writer.vec4f([0.0, 0.0, 0.0, 0.0]) # Params
            writer.uint32(0) # Opaque Offset
            writer.uint32(len(total_faces) * 3) # Opaque Length
            writer.uint32(0); writer.uint32(0) # Alpha
            writer.uint32(0); writer.uint32(0) # Additive

            # TEXTURES
            writer.uint32(len(all_materials))
            for mat in all_materials:
                m_name = (mat.name[:31] if mat else "Default").encode('ascii', 'ignore')
                f.write(m_name + b'\x00' * (31 - len(m_name)))
                writer.ubyte(7) # Standard flag

            # INJECT BONE BLOB
            f.write(blob_data)

            # COUNTS
            writer.uint32(len(total_vertices))
            writer.uint32(len(total_faces) * 3)

            # VERTEX BLOCK
            for v in total_vertices:
                writer.vec3f(v['pos'])
                
                # Tangents
                writer.vec3ub(v['tangent'])

                # Constant, Always 2 for some reason
                writer.ubyte(2) 

                # Normals
                writer.vec3ub(v['normal'])

                # Material Index
                writer.ubyte(v['mat_id']) # Calculated per face/vertex

                # Bone Indices
                writer.vec3ub(v['bone_idx'])

                # U
                writer.ubyte(int(v['uv'][0] * 255) % 256)

                # Weights
                writer.vec3ub(v['bone_weight'])

                # V 
                writer.ubyte(int((1.0 - v['uv'][1]) * 255) % 256)

                # Padding
                writer.uint32(0)

            # FACE BLOCK
            for face in total_faces:
                writer.vec3us(reverse_vector(face))

        print(f"Successfully exported {len(total_vertices)} vertices.")
        return {'FINISHED'}

    except Exception as e:
        self.report({'ERROR'}, f"Export failed: {str(e)}")
        return {'CANCELLED'}

def export_tr_model(self, context, is_head_model: bool, file_path: str) -> set[str]:
    """Export Blender objects into TRR's model format."""
    start_time = time.time()

    # Initialize the writer
    with open(file_path, "wb") as f:
        writer = Writer(f)

        # Collect all valid meshes to export
        objects_to_export = [obj for obj in context.scene.objects if obj.type == "MESH"]
        print(f"\nExporting {len(objects_to_export)} meshes to {file_path}...")

    # ---------------------------------------------------------
    # 2. DATA AGGREGATION
    # ---------------------------------------------------------

    total_vertices = []
    total_faces = []
    all_materials = []
    
    # Track the global vertex offset as we merge multiple Blender objects
    vert_offset = 0

    for obj_index, obj in enumerate(objects_to_export):
        mesh = obj.data
        
        # Ensure tangents are fresh for the (n*127)+127 packing
        try:
            mesh.calc_tangents()
        except:
            # Fallback for meshes without proper UVs
            mesh.calc_normals_split()

        # Build material list for the entire file
        for mat_slot in obj.material_slots:
            if mat_slot.material not in all_materials:
                all_materials.append(mat_slot.material)

        # Mapping face-materials to vertex IDs
        # Since SRM stores MatID at the vertex level, we'll map based on the 
        # first polygon that uses the vertex (common in game-dev binary packing).
        vert_to_mat = {}
        for poly in mesh.polygons:
            for vert_idx in poly.vertices:
                # SRM uses 1-based indexing for Materials in the vertex block
                vert_to_mat[vert_idx] = poly.material_index + 1

        # Process Vertices
        uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None

        unique_vertices = []
        vert_cache = {} 
        # total_faces is now local to this object loop, we'll extend the global list later
        obj_faces = []

        for poly in mesh.polygons:
            face_indices = []
            
            # 1-based Material ID for this face
            mat_id = poly.material_index + 1

            for loop_idx in poly.loop_indices:
                loop = mesh.loops[loop_idx]
                v = mesh.vertices[loop.vertex_index]
                
                # --- POSITION ---
                world_co = obj.matrix_world @ v.co
                
                # --- NORMALS & TANGENTS ---
                # Use loop-specific tangent to prevent tangent melting
                norm = (obj.matrix_world.to_3x3() @ v.normal).normalized()
                tang = [127, 127, 127]
                if uv_layer:
                    t = loop.tangent
                    tang = [int((t.x * 127) + 127), int((t.y * 127) + 127), int((t.z * 127) + 127)]

                # --- UVs ---
                uv = [uv_layer[loop_idx].uv[0], uv_layer[loop_idx].uv[1]] if uv_layer else [0.0, 0.0]

                # --- BONES & WEIGHTS ---
                b_indices = [0, 0, 0]
                b_weights = [0, 0, 0]
                bone_groups = []
                for g in v.groups:
                    group_name = obj.vertex_groups[g.group].name
                    if group_name.startswith("bone_"):
                        try:
                            bone_id = int(group_name.split("_")[1])
                            bone_groups.append((bone_id, g.weight))
                        except (IndexError, ValueError):
                            print(f"Warning: Group {group_name} format error.")

                sorted_groups = sorted(bone_groups, key=lambda x: x[1], reverse=True)[:3]
                for i, (b_id, weight) in enumerate(sorted_groups):
                    b_indices[i] = b_id
                    b_weights[i] = int(weight * 255)

                # --- VERTEX SPLITTING KEY ---
                # This key identifies unique combinations. If a vertex at a seam 
                # has 2 UVs, it will generate 2 unique entries in the cache.
                vert_key = (
                    tuple(round(c, 6) for c in world_co),
                    tuple(round(c, 4) for c in norm),
                    tuple(round(c, 6) for c in uv),
                    tuple(b_indices),
                    tuple(b_weights),
                    mat_id
                )

                if vert_key not in vert_cache:
                    vert_cache[vert_key] = len(unique_vertices)
                    unique_vertices.append({
                        'pos': world_co,
                        'tangent': tang,
                        'normal': [int((norm.x * 127) + 127), int((norm.y * 127) + 127), int((norm.z * 127) + 127)],
                        'mat_id': mat_id,
                        'bone_idx': b_indices,
                        'bone_weight': b_weights,
                        'uv': uv
                    })

                face_indices.append(vert_cache[vert_key] + vert_offset)

            obj_faces.append(face_indices)

        # Merge this object's data into the global lists
        total_vertices.extend(unique_vertices)
        total_faces.extend(obj_faces)
        
        # Update offset based on the number of unique vertices created
        vert_offset += len(unique_vertices)

    # ----------------
    # 2. BINARY WRITE
    # ----------------
    try:
        with open(file_path, "wb") as f:
            writer = Writer(f)
            writer.ascii_string("TRM")
            writer.ubyte(2)

            # SHADERS (Single shader for the whole mesh)
            writer.uint32(1) # Shader Count
            writer.uint32(0) # Type
            writer.vec4f([0.0, 0.0, 0.0, 0.0]) # Params
            writer.uint32(0) # Opaque Offset
            writer.uint32(len(total_faces) * 3) # Opaque Length
            writer.uint32(0); writer.uint32(0) # Alpha
            writer.uint32(0); writer.uint32(0) # Additive

            # TEXTURES
            writer.uint32(len(all_materials))
            for mat in all_materials:
                try: m_id = int(mat.name.split('_')[-1]) if mat else 8000
                except: m_id = 8000
                writer.ushort(m_id)

            # Padding stuff
            writer.align(4)

            # --- ARMATURE BLOCK (Only for HEAD models) ---
            # if is_head_model:
            #     # Logic derived from your 010 template port
            #     # We write a dummy 0 for now unless you have armature data to inject
            writer.uint32(0) # BoneCount

            # COUNTS
            writer.uint32(len(total_faces) * 3)
            writer.uint32(len(total_vertices))

            # FACE BLOCK
            for face in total_faces:
                writer.vec3us(reverse_vector(face))

            # VERTEX BLOCK
            for v in total_vertices:
                writer.vec3f(v['pos'])
                
                # Normals
                writer.vec3ub(v['normal'])

                # Material Index
                writer.ubyte(v['mat_id'])

                # Bone Indices
                writer.vec3ub(v['bone_idx'])

                # U
                writer.ubyte(int(v['uv'][0] * 255) % 256)

                # Weights
                writer.vec3ub(v['bone_weight'])

                # V
                writer.ubyte(int((1.0 - v['uv'][1]) * 255) % 256)

        print(f"Successfully exported {len(total_vertices)} vertices.")
        return {'FINISHED'}
    
    except Exception as e:
        self.report({'ERROR'}, f"Export failed: {str(e)}")
        import traceback; traceback.print_exc()
        return {'CANCELLED'}