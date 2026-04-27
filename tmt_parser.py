import bpy

from .readers import Reader
from .bpy_util_funcs import *

class TMT():
    """ TMT class. Used for Angel of Darkness morph targets that use `*.TMT` files. """
    # Class constructor.
    def __init__(self, file_path: str):
        """
        Construct a new instance of `TMT`.

        This format is used to store morph targets for characters in both the Angel of Darkness original and remaster versions
        """

        # Class init stuff
        super().__init__()

        # -------------------------------
        # -- CLASS MEMBERS --------------
        # -------------------------------

        # -- MORPH FILE
        self.morph_file: str = file_path
        """The path to the morph file."""

        # -- MASTER MORPH DATA
        self.morph_data: list[dict] = []
        """Master list of all morph data."""

        # -------------------------------
        # -- PARSE THE DATA -------------
        # -------------------------------

        # Parse our morph file here!
        self.parse_morph_file()
        
    # Main morph parser!
    def parse_morph_file(self):
        """ Parse the morph file itself! """
        print(f"Parsing morph data...\n")

        # Initialize the reader
        reader = Reader(open(self.morph_file, "rb").read())

        # -------
        # HEADER
        # -------

        magic = reader.read_string(4)
        print(f"Magic: {magic}")

        headerSize = reader.ubyte()
        unusedVertexCount = reader.ushort()
        unknown = reader.ubyte()
        
        headerHash = reader.uint32()

        linkedSubMeshHash = reader.uint32()
        print(f"Linked Submesh Hash: {linkedSubMeshHash:X}")
        morphTargetCount = reader.uint32()
        print(f"Morph Target Count: {morphTargetCount}")
        vertexCount = reader.uint32()
        print(f"Vertex Count: {vertexCount}")

        unknown2 = reader.uint32()
        unknown3 = reader.uint32()

        # -----------
        # MORPH DATA
        # -----------

        # Total morphs = morphTargetCount (the morphs) + 1 (the base mesh)
        total_morphs = morphTargetCount + 1
        
        # Pre-allocate dictionaries for every shape
        morph_data = [{"vertices": [], "normals": [], "uvs": []} for _ in range(total_morphs)]

        # Read interleaved data: For every vertex, read its Base position, then Morph 1, Morph 2, etc.
        for (_) in range(vertexCount):
            for shape_idx in range(total_morphs):
                morph_data[shape_idx]["vertices"].append(reader.vec3f())
                morph_data[shape_idx]["normals"].append(reader.vec3f())
                morph_data[shape_idx]["uvs"].append(reader.vec2f())

    # --------------------------------------------------------------------------------------------------------

        morph_data_dict = {
            "magic": magic,
            "linked_submesh_hash": linkedSubMeshHash,
            "morph_target_count": morphTargetCount,
            "vertex_count": vertexCount,
            "base_mesh": morph_data[0],
            "morph_targets": morph_data[1:]
        }
        
        self.morph_data.append(morph_data_dict)
        
        print(f"Successfully parsed Base Mesh and {len(morph_data[1:])} Morph Targets.")

    # --------------------------------------------------------------------------------------------------------