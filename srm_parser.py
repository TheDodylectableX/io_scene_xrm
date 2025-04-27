import bpy

from .readers import Reader
from .bpy_util_funcs import *

class SRM():
    """ SRM class. Used for Soul Reaver 1 and 2 models that use `*.SRM` files. """
    # Class constructor.
    def __init__(self, file_path: str, custom_normals: bool = False, random_material_colors: bool = True, texture_import: bool = True):
        """
        Construct a new instance of `SRM`.

        This model is a model used in DEATHLOOP or Dishonored 2/DoTO as a static mesh.

        Class contains information about the model, its sub-mesh count, and the mesh data itself.
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

        version = reader.uint32()
        print(f"Model Version: {version}")

        reader.skip(24) # Repeated face counts and reserved

        header_face_count_A = reader.uint32()
        header_face_count_B = reader.uint32()

        header_unk_val = reader.uint32()

        header_face_count_C = reader.uint32()

        reader.skip(4) # Repeated face counts and reserved

        if version == 2:
            print("Model Version is 2, skipping unknown data")
            reader.skip(96)

        if version == 3:
            print("Model Version is 3, skipping unknown data")
            reader.skip(140)

        textureCount = reader.uint32()
        print(f"\nTexture Count: {textureCount}")

        textures = []

        for (_) in range(textureCount):
            # Read the raw string
            texture = reader.read_string(32)
            
            # Remove non-printable characters
            sanitized_texture = ''.join(c for c in texture.strip() if c.isprintable())
            
            # Print the sanitized string
            print(f"  Texture: {sanitized_texture}.DDS")
            
            # Append the sanitized string to the list
            textures.append(sanitized_texture)

        self.texture_data = textures

        reader.skip(4) # Reserved

        header_unk_floats = []

        if header_face_count_A == 88500:
            for (_) in (range(684)):
                header_unk_float = reader.float32()

                header_unk_floats.append(header_unk_float)
        else:
            for (_) in (range(384)):
                header_unk_float = reader.float32()

                header_unk_floats.append(header_unk_float)

        if header_face_count_A == 88500:
            reader.skip(132) # No idea
        else:
            reader.skip(128) # No idea

        vertexCount = reader.uint32()
        print(f"\nVertex Count: {vertexCount}")
        faceCount = reader.uint32()
        print(f"Face Count: {faceCount}")

        # --------------------------------------------------------------------------------------------------------

        # ------------
        # VERTEX DATA
        # ------------

        vertices = []
        normals = []
        material_index = []
        tangents = []
        bone_indices = []
        bone_weights = []
        uv = []

        for (_) in (range(vertexCount)):
            # -- VERTICES ---------------------------
            vertices.append(reader.vec3f())

            # -- TANGENTS ---------------------------
            tangent = reader.vec3ub()
            tangent = convert_vertex_normal(tangent[0], tangent[1], tangent[2])
            tangents.append(tangent)

            # -- CONSTANT (Always 2 for some reason)
            constant = reader.ubyte()

            # -- NORMALS ----------------------------
            normal = reader.vec3ub()
            normal = convert_vertex_normal(normal[0], normal[1], normal[2])
            normals.append(normal)

            # -- MATERIAL INDEX ---------------------
            id = reader.ubyte()
            material_index.append(id)

            # -- INDICES ----------------------------
            indices = reader.vec3ub()
            bone_indices.append(indices)

            # -- U ----------------------------------
            u = reader.ubyte() / 255.0

            # -- WEIGHTS ----------------------------
            weights = reader.vec3ub()
            bone_weights.append(weights)

            # -- V ----------------------------------
            v = 1 - reader.ubyte() / 255.0

            uv.append([u, v])

            reader.skip(4) # Reserved

        # --------------------------------------------------------------------------------------------------------

        # ------
        # FACES
        # ------

        faces = []

        for (_) in (range(faceCount // 3)):
            faces.append(reverse_vector(reader.vec3us()))

        print(f"\nMODEL PARSING COMPLETE!")

        mesh_data_dict = {
            "magic": magic,
            "constant": constant,
            "vertex_count": vertexCount,
            "face_count": faceCount,
            "vertices": vertices,
            "uv_map": uv,
            "normals": normals,
            "tangents": tangents,
            "faces": faces,
            "bone_indices": bone_indices,
            "bone_weights": bone_weights,
            "material_index": material_index,
            "textures": textures,
        }

        master_data_list.append(mesh_data_dict)

        self.mesh_data = master_data_list

    # -------------------------------------------