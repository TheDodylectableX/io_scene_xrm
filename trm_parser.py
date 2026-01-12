import bpy

from .readers import Reader
from .bpy_util_funcs import *

class TRM():
    """ TRM class. Used for Tomb Raider 1-5 models that use `*.TRM` files. """
    # Class constructor.
    def __init__(self, file_path: str, custom_normals: bool = False, random_material_colors: bool = True, texture_import: bool = True):
        """
        Construct a new instance of `TRM`.

        This model is used in the five Tomb Raider remasters
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
        self.mesh_data: list[dict] = []
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
        master_data_list: list[dict] = []

        # -------
        # HEADER
        # -------

        magic = reader.read_string(4)
        print(f"Magic: {magic}")

        shaderCount = reader.uint32()
        print(f"Shader Count: {shaderCount}")

        for (_) in range(shaderCount):
            shaderType = reader.uint32()
            print(f"Shader Type: {shaderType}")
            shaderParameters = reader.vec4f()
            print(f"Shader Parameters: {shaderParameters}")
            opaqueOffset = reader.uint32()
            print(f"Opaque Offset: {opaqueOffset}")
            opaqueLength = reader.uint32()
            print(f"Opaque Length: {opaqueLength}")
            alphaOffset = reader.uint32()
            print(f"Alpha Offset: {alphaOffset}")
            alphaLength = reader.uint32()
            print(f"Alpha Length: {alphaLength}")
            additiveOffset = reader.uint32()
            print(f"Additive Offset: {additiveOffset}")
            additiveLength = reader.uint32()
            print(f"Additive Length: {additiveLength}")

        textureCount = reader.uint32()
        print(f"\nTexture Count: {textureCount}")

        textures = []

        for (_) in range(textureCount):
            texture_num = reader.ushort()
            print(f"  Texture ID: {texture_num}.DDS")

            textures.append(str(texture_num))

        # Dynamically skip padding made of consecutive zero bytes (up to a safe limit)
        zero_count = 0

        while reader.offset < reader.length:
            if reader.ubyte() != 0:
                reader.seek(reader.tell() - 1)  # Rewind one byte so the next read is correct
                break
            zero_count += 1

        # Armature stuff
        is_head_model = "HEAD" in self.model_file.upper()

        if is_head_model:
            print("Detected head model - Parsing Bone and Animation structure...")

            boneCount = reader.uint32()
            print(f"\nBone Count: {boneCount}")

            for (_) in range(boneCount):
                bone_a = reader.vec3f()
                bone_b = reader.vec3f()
                bone_c = reader.vec3f()
                bone_d = reader.vec3f()

            # REALLY SCUFFED STRUCTURE FOR ANIMATION STUFF I DON'T REALLY CARE ABOUT
            animationRelatedCountA = reader.uint32()
            for (_) in range(animationRelatedCountA):
                animationRelatedValueA = reader.uint32()
                animationRelatedValueB = reader.uint32()
            
            animationFrameCount = reader.uint32()
            for (_) in range(animationFrameCount):
                animationFrame = reader.uint32()

            animationRelatedB = reader.ushort()
            animationRelatedC = reader.ushort()
            if (animationFrameCount * animationRelatedB > 0):
                for (_) in range(animationFrameCount * animationRelatedB):
                    bone_a2 = reader.vec3f()
                    bone_b2 = reader.vec3f()
                    bone_c2 = reader.vec3f()
                    bone_d2 = reader.vec3f()
        else:
            print("Standard model detected - Skipping Bone and Animation structure.")

        faceCount = reader.uint32()
        print(f"Face Count: {faceCount}")

        vertexCount = reader.uint32()
        print(f"Vertex Count: {vertexCount}")

    # --------------------------------------------------------------------------------------------------------

        # ------
        # FACES
        # ------

        faces = []

        for (_) in (range(faceCount // 3)):
            faces.append(reverse_vector(reader.vec3us()))

        # Dynamically skip padding made of consecutive zero bytes (up to a safe limit)
        zero_count_2 = 0

        while reader.offset < reader.length:
            if reader.ubyte() != 0:
                reader.seek(reader.tell() - 1)  # Rewind one byte so the next read is correct
                break
            zero_count_2 += 1

        print(f"Skipped {zero_count_2} padding byte(s)")

        # --------------------------------------------------------------------------------------------------------

        # ------------
        # VERTEX DATA
        # ------------

        vertices = []
        normals = []
        material_index = []
        bone_indices = []
        bone_weights = []
        uv = []

        for (_) in (range(vertexCount)):
            # -- VERTICES --------------------------
            vertices.append(reader.vec3f())

            # -- NORMALS ---------------------------
            normal = reader.vec3ub()
            normal = convert_vertex_normal(normal[0], normal[1], normal[2])
            normals.append(normal)

            id = reader.ubyte()
            material_index.append(id)

            # -- INDICES ---------------------------
            indices = reader.vec3ub()
            bone_indices.append(indices)

            # -- U --------------------------
            u = reader.ubyte() / 255.0

            # -- WEIGHTS ---------------------------
            weights = reader.vec3ub()
            bone_weights.append(weights)

            # -- V --------------------------
            v = 1 - reader.ubyte() / 255.0

            uv.append([u, v])

    # --------------------------------------------------------------------------------------------------------

        mesh_data_dict = {
            "magic": magic,
            "vertex_count": vertexCount,
            "face_count": faceCount,
            "vertices": vertices,
            "uv_map": uv,
            "normals": normals,
            "faces": faces,
            "bone_indices": bone_indices,
            "bone_weights": bone_weights,
            "material_index": material_index,
            "textures": textures,
        }

        master_data_list.append(mesh_data_dict)

        self.mesh_data = master_data_list

    # -------------------------------------------