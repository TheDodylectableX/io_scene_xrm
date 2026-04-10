import bpy

from .readers import Reader
from .bpy_util_funcs import *

class SRM():
    """ SRM class. Used for Soul Reaver I-II and Defiance models that use `*.SRM` files. """
    # Class constructor.
    def __init__(self, file_path: str, game_of_model: str, skeleton_import: bool = True, lod_import: bool = True, custom_normals: bool = False, random_material_colors: bool = True, texture_import: bool = True):
        """
        Construct a new instance of `SRM`.

        This model format is used in the three Legacy of Kain remasters.
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

        # -- MODEL FROM GAME
        self.model_from_game: bool = game_of_model
        """What game is this model from? This determines the way parsing logic will be executed next."""

        # -- USE CUSTOM NORMALS
        self.use_custom_normals: bool = custom_normals
        """When the model is created, this will re-calculate the normals instead of using the original ones."""

        # -- ASSIGN MATERIAL COLORS
        self.assign_material_colors: bool = random_material_colors
        """This determines if the user wants random material colors on the model's generated materials or not."""

        # -- IMPORT TEXTURES
        self.import_textures: bool = texture_import
        """This determines if the user wants to import the model's textures or not."""

        # -- IMPORT SKELETON
        self.import_skeleton: bool = skeleton_import
        """This determines if the user wants to import the model's skeleton or not."""

        # -- DEFIANCE: IMPORT LODS
        self.import_lods: bool = lod_import
        """This determines if the user wants to import the model's LODs or not."""

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

        # -- LOD NORMALIZATION -----------
        # We default to 1 LOD for Soul Reaver I-II so we can use a single unified parsing loop as this prevents us from having to write the entire parsing block twice.
        lodCount = 1

        magic = reader.read_string(4)
        print(f"Magic: {magic}")

        if (self.model_from_game == GAME_SR3):
            lodCount = reader.uint32()
            print(f"LOD Count: {lodCount}")
            bounds = reader.vec4f()
            print(f"Mesh Bounds: {bounds}\n")

        for currentLOD in range(lodCount):
            print(f"\n--- Parsing Mesh Chunk (LOD {currentLOD}) ---")

            shaderCount = reader.uint32()
            print(f"Shader Count: {shaderCount}")

            for (_) in range(shaderCount):
                shaderType = reader.uint32()
                print(f"\nShader Type: {shaderType}")
                if (self.model_from_game == GAME_SRX):
                    shaderParameters = reader.vec4f()
                    print(f"Shader Parameters: {shaderParameters}")
                else:
                    shaderBuffer = reader.read_bytes(88)
                opaqueOffset = reader.uint32()
                print(f"Opaque Offset: {opaqueOffset}")
                opaqueLength = reader.uint32()
                print(f"Opaque Length: {opaqueLength}\n")
                alphaOffset = reader.uint32()
                print(f"Alpha Offset: {alphaOffset}")
                alphaLength = reader.uint32()
                print(f"Alpha Length: {alphaLength}\n")
                additiveOffset = reader.uint32()
                print(f"Additive Offset: {additiveOffset}")
                additiveLength = reader.uint32()
                print(f"Additive Length: {additiveLength}")

            textureCount = reader.uint32()
            print(f"\nMaterial Count: {textureCount}")

            textures = []
            for (_) in range(textureCount):
                # Read the raw string
                texture = reader.read_string(31)
                textureFlag = reader.ubyte()
                
                # Remove non-printable characters
                sanitized_texture = ''.join(c for c in texture.strip() if c.isprintable())
                
                # Print the sanitized string
                print(f"  Material: {sanitized_texture}")
                print(f"  Material Flag: {textureFlag}\n")
                
                # Append the sanitized string to the list
                textures.append(sanitized_texture)

            if currentLOD == 0:
                self.texture_data = textures

            extraBoneCount = reader.uint32()
            print(f"\nBone Count: {32 + extraBoneCount}")

            # ==========================================================================================================================================================
            # I have no idea what this section is supposed to be but it seems like it's possibly something for collisions or hit detection?
            # I don't know how it works at the moment but the floating point values seem to represent the outline of a model, Not sure what the bytes are supposed to be
            # And this is not on Tomb Raider Remastered, It's only on this game
            #
            # THIS IS ACTUALLY BONE DATA OF THE OLD MODEL SKELETON + HD MODEL SKELETON BUT I HAVE NO IDEA HOW ITS PROPERLY STRUCTURED SO I'LL JUST SKIP OVER IT
            # SUPPOSEDLY ONLY CARRIES LOCATION VECTORS
            # ==========================================================================================================================================================

            bone_matrices = []
            for (_) in (range(32 + extraBoneCount)):
                row_1 = reader.vec3f()
                row_2 = reader.vec3f()
                row_3 = reader.vec3f()
                row_4 = reader.vec3f()

                bone_matrices.append([row_1, row_2, row_3, row_4])

            # --- FINAL BONE TRANSFORM CHECK ---
            # Peek at the next 4 bytes without permanently moving the cursor, really hacky solution
            current_pos = reader.tell()
            next_uint = reader.uint32()

            if next_uint == 2147483648: # 0x80000000 / -0.0
                print(f"Found bone transform at {current_pos}, skipping...")
                # Cursor is already moved forward 4 bytes by uint32(), so do nothing
            else:
                # If it's NOT the bone transform, rewind so we don't skip the first boneFlag
                reader.seek(current_pos)

            bone_flags = []
            for (_) in (range(128)):
                boneFlag = reader.ubyte()

                bone_flags.append(boneFlag)

            # ==============================================================================================================================

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
                # -- VERTICES ----------------------------
                vertices.append(reader.vec3f())

                # -- TANGENTS ------------------------------
                if self.model_from_game == GAME_SR3:
                    tangent_raw = reader.vec4sb()
                    tangents.append(tangent_raw)
                else:
                    tangent_raw = reader.vec3ub()
                    constant = reader.ubyte() # Always 2 for some reason

                tangents.append(convert_vertex_normal(tangent_raw[0], tangent_raw[1], tangent_raw[2]))

                # -- NORMALS -------------------------------
                if self.model_from_game == GAME_SR3:
                    normal_raw = reader.vec3sb()
                    normals.append(normal_raw)
                else:
                    normal_raw = reader.vec3ub()
                    normals.append(convert_vertex_normal(normal_raw[0], normal_raw[1], normal_raw[2]))

                # -- MATERIAL INDEX (1 byte) -------------------------
                material_index.append(reader.ubyte())

                # -- BONE INDICES ---------------
                if self.model_from_game == GAME_SR3:
                    indices = reader.vec4ub()
                else:
                    indices = reader.vec3ub()
                bone_indices.append(indices)

                # -- BONE WEIGHTS AND UVS ----
                if self.model_from_game == GAME_SR3:
                    weights = reader.vec4ub()
                    bone_weights.append(weights)

                    uv_coords = invert_uv_map(reader.vec2f())
                    
                    uv.append(uv_coords)
                else:
                    u = reader.ubyte() / 255.0
                    
                    weights = reader.vec3ub()
                    bone_weights.append(weights)
                    
                    v = invert_v(reader.ubyte() / 255.0)
                    uv.append([u, v])

                    reader.skip(4)

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
                "bone_matrices": bone_matrices,
                "bone_flags": bone_flags,
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

            # If the user toggled LODs off in the UI we still had to parse them to keep the binary reader offset correct but we only save LOD 0 to the master list.
            if self.import_lods or currentLOD == 0:
                master_data_list.append(mesh_data_dict)

            self.mesh_data = master_data_list

    # -------------------------------------------