import bpy
from enum import IntEnum

from .readers import Reader
from .bpy_util_funcs import *

class FaceType(IntEnum):
    DRAWPT_POINTLIST     = 0x1
    DRAWPT_LINELIST      = 0x2
    DRAWPT_LINESTRIP     = 0x3
    DRAWPT_TRIANGLELIST  = 0x4
    DRAWPT_TRIANGLESTRIP = 0x5
    DRAWPT_TRIANGLEFAN   = 0x6

class CHR():
    """ CHR class. Used for Angel of Darkness models that use `*.CHR` files. """
    # Class constructor.
    def __init__(self, file_path: str, custom_normals: bool = False, random_material_colors: bool = True, texture_import: bool = True):
        """
        Construct a new instance of `CHR`.

        This model is used in both the Angel of Darkness original and remaster versions
        """

        # Class init stuff
        super().__init__()

        # -------------------------------
        # -- CLASS MEMBERS --------------
        # -------------------------------

        # -- MODEL FILE
        self.model_file: str = file_path
        """The path to the model file."""

        # -- MASTER MESH DATA
        self.mesh1: list[dict] = []
        """Master list of all mesh data."""

        # -- TEXTURE COUNT
        self.texture_count: int = 0
        """The number of textures this model has."""

        # -- USE CUSTOM NORMALS
        self.use_custom_normals: bool = custom_normals
        """When the model is created, this will re-calculate the normals instead of using the original ones."""

        # -- ASSIGN MATERIAL COLORS
        self.assign_material_colors: bool = random_material_colors
        """This determines if the user wants random material colors on the model's generated materials or not."""

        # -- IMPORT TEXTURES
        self.import_textures: bool = texture_import
        """This determines if the user wants to import the model's textures or not."""

        # -------------------------------
        # -- PARSE THE DATA -------------
        # -------------------------------

        # Parse our model file here!
        self.parse_model_file()
        
    # Main model parser!
    def parse_model_file(self):
        """ Parse the model file itself! """
        print(f"Parsing model data...\n")

        # Initialize the reader
        reader = Reader(open(self.model_file, "rb").read())

        # Dictionaries of data lists
        mesh_master_data_list: list[dict] = []
        skeleton_master_data_list: list[dict] = []
        material_master_data_list: list[dict] = []

        # -------
        # HEADER
        # -------

        magic = reader.uint32() # Always 0

        textureArrayOffset = reader.uint32()
        print(f"Texture Array Offset: {textureArrayOffset}")
        skeletonOffset = reader.uint32()
        print(f"Skeleton Offset: {skeletonOffset}")
        headerUnk = reader.uint32()
        meshDataOffset = reader.uint32()
        print(f"Mesh Data Offset: {meshDataOffset}")
        boneCount = reader.uint32()
        print(f"Bone Count: {boneCount}\n")

        # =========
        # SKELETON
        # =========

        reader.seek(skeletonOffset)
        for (i) in (range(boneCount)):
            bone_data = {
                "flags": reader.uint32(),
                "name": reader.read_string(64).split('\0')[0],
                "id": reader.uint32(),
                "index": reader.uint32(),
                "matrix_index": reader.uint32(),
                "bind_pose": [reader.vec4f() for _ in range(4)],
                "absolute_bind": [reader.vec4f() for _ in range(4)],
                "pre_transform": [reader.vec4f() for _ in range(4)],
                "post_transform": [reader.vec4f() for _ in range(4)],
                "sphere": {"origin": reader.vec4f(), "radius": reader.float32()},
                "physics_flags": (reader.skip(12), reader.uint32())[1],
                "parent": reader.uint32(),
                "padding": reader.skip(72) # Essential to hit the next bone start
            }
            skeleton_master_data_list.append(bone_data)
        
        self.skeleton = skeleton_master_data_list

        # =======
        # MESH 1
        # =======
        reader.seek(meshDataOffset)
        meshDataUnk = reader.uint32()
        skinDataUnk = reader.uint32()
        skinID = reader.uint32()

        vertexCount = reader.uint32()
        primaryVertices = []
        secondaryVertices = []
        primaryNormals = []
        secondaryNormals = []
        primaryTangents = []
        primaryBinormals = []
        secondaryTangents = []
        secondaryBinormals = []
        bone_weights = []
        bone_indices = []
        primaryUV = []
        
        for (_) in (range(vertexCount)):
            primaryVertices.append(tuple(v / 32768.0 for v in reader.vec3ss()))
            secondaryVertices.append(tuple(v / 32768.0 for v in reader.vec3ss()))
            primaryNormals.append(tuple(n / 127.0 for n in reader.vec3sb()))
            secondaryNormals.append(tuple(n / 127.0 for n in reader.vec3sb()))
            primaryTangents.append(tuple(t / 127.0 for t in reader.vec3sb()))
            primaryBinormals.append(tuple(b / 127.0 for b in reader.vec3sb()))
            secondaryTangents.append(tuple(t / 127.0 for t in reader.vec3sb()))
            secondaryBinormals.append(tuple(b / 127.0 for b in reader.vec3sb()))
            bone_weights.append(reader.ushort() / 65535.0)
            bone_indices.append(list(reader.read_bytes(2)))
            primaryUV.append(tuple(u / 32768.0 for u in reader.vec2ss()))

        faceCount = reader.uint32()
        faces = [reader.ushort() for _ in range(faceCount)]

        subMeshCount = reader.uint32()
        mesh1_submesh_runs = []
        for (_) in (range(subMeshCount)):
            run = {
                "primitive_count": reader.ushort(),
                "face_count": reader.ushort(),
                "indices_start": reader.ushort(),
                "material_index": reader.ushort(),
                "bump_index": reader.ushort(),
                "face_type": reader.ushort()
            }
            mesh1_submesh_runs.append(run)

        # Build Mesh 1 dictionary once after all data is parsed
        mesh1_data_dict = {
            "vertex_count": vertexCount,
            "skin_id": skinID,
            "primary_vertices": primaryVertices,
            "secondary_vertices": secondaryVertices,
            "primary_normals": primaryNormals,
            "secondary_normals": secondaryNormals,
            "primary_tangents": primaryTangents,
            "primary_binormals": primaryBinormals,
            "secondary_tangents": secondaryTangents,
            "secondary_binormals": secondaryBinormals,
            "bone_weights": bone_weights,
            "bone_indices": bone_indices,
            "uv_map": primaryUV,
            "face_count": faceCount,
            "faces": faces,
            "submeshes": mesh1_submesh_runs
        }
        self.mesh1 = [mesh1_data_dict]

        # =======
        # MESH 2
        # =======
        riggedDataCount = reader.uint32()
        for (_) in (range(riggedDataCount)):
            vertices = []
            normals = []
            tangents = []
            binormals = []
            uv = []
            faces_2 = []
            submesh_runs = []

            riggedDataUnk = reader.uint32()
            riggedDataFlags = reader.uint32()
            riggedDataMeshID = reader.uint32()
            riggedDataIndexBone = reader.uint32()
            riggedDataIndexAnimationBone = reader.uint32()
            
            riggedDataVertexCount = reader.uint32()
            for (_) in (range(riggedDataVertexCount)):
                vertices.append(tuple(v / 32768.0 for v in reader.vec3ss()))
                normals.append(tuple(n / 127.0 for n in reader.vec3sb()))
                tangents.append(tuple(t / 127.0 for t in reader.vec3sb()))
                binormals.append(tuple(b / 127.0 for b in reader.vec3sb()))
                uv.append(tuple(u / 32768.0 for u in reader.vec2ss()))

            riggedDataFaceCount = reader.uint32()
            for (_) in (range(riggedDataFaceCount)):
                faces_2.append(reader.ushort())

            subMeshCount = reader.uint32()
            for (_) in (range(subMeshCount)):
                run = {
                    "primitive_count": reader.ushort(),
                    "face_count": reader.ushort(),
                    "indices_start": reader.ushort(),
                    "material_index": reader.ushort(),
                    "bump_texture_index": reader.ushort(),
                    "face_type": reader.ushort()
                }
                submesh_runs.append(run)

            # Store this specific rigged block
            mesh2_data_dict = {
                "flags": riggedDataFlags,
                "mesh_id": riggedDataMeshID,
                "parent_bone": riggedDataIndexBone,
                "anim_bone": riggedDataIndexAnimationBone,
                "vertices": vertices,
                "normals": normals,
                "tangents": tangents,
                "binormals": binormals,
                "uv_map": uv,
                "faces": faces_2,
                "submesh_runs": submesh_runs
            }
            mesh_master_data_list.append(mesh2_data_dict)

        self.mesh2 = mesh_master_data_list

        # =========
        # TEXTURES
        # =========
        reader.seek(textureArrayOffset)
        materialCount = reader.uint32()
        for (_) in (range(materialCount)):
            m_flags = reader.uint32()
            m_tex_count = reader.uint32()
            m_indices = [reader.uint32() for _ in range(m_tex_count)]
            material_master_data_list.append({
                "flags": m_flags,
                "texture_count": m_tex_count,
                "texture_indices": m_indices
            })
        
        self.materials = material_master_data_list

    # -------------------------------------------