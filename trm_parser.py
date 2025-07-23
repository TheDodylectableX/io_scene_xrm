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

        Hand/Head models are currently unsupported.
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

        # We'll scan ahead until we find a non-zero byte
        while reader.offset < reader.length:
            if reader.ubyte() != 0:
                reader.seek(reader.tell() - 1)  # Rewind one byte so the next read is correct
                break
            zero_count += 1

        print(f"Skipped {zero_count} padding byte(s)")

        faceCount = reader.uint32()
        print(f"\nFace Count: {faceCount}")

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