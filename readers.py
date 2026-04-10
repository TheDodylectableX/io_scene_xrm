# -----------------------------------------------------
#   READER CLASS
#       Class for reading data in files
# -----------------------------------------------------
""" Module with helper classes for reading binary file data. """

import os
import bpy, struct, math
import mathutils

# -----------------------------------------------------

# Base class for reading various data types.
class Reader():
    """ Data parser class. Used for reading binary data from a file! """
    # Reader object constructor.
    def __init__(self, buf: bytes, is_little_endian: bool = True):
        """ Construct a new `Reader` object. Input data, and if we want to use little endianness for our reading process. """

        # -------------------------------
        # -- CLASS MEMBERS --------------
        # -------------------------------

        # -- DATA READ OFFSET
        self.offset: int = 0
        """ The offset or position we are currently at in reading the file. """

        # -- DATA BYTES
        self.data: bytes = buf
        """ The bytes that the current instance of Reader is currently pulling from. """

        # -- IS LITTLE ENDIAN
        self.LE: bool = is_little_endian
        """ Is this file being read in little endian? """

        # -- LENGTH OF THE FILE
        self.length: int = len(buf)
        """ Total number of bytes in the data buffer provided. """
    
    # - - - - - - - - - - - - - - -

    # Return the data offset.
    def tell(self) -> int:
        """ Where are we in our data buffer? Returns the offset. """
        return self.offset
    
    # Move the byte buffer forward by `x` amount of bytes.
    def skip(self, skip_by: int):
        """ Move the offset forward by the given number of bytes. """
        self.offset += skip_by

    # Manually set the read position offset at the given position.
    def seek(self, position: int):
        """ Manually set the read position offset at the given position. """
        self.offset = position

    def align(self, boundary: int = 4, strict: bool = False):
            """
            Advances the reader's cursor to the next byte boundary to skip structural padding.
            
            Parameters:
            - boundary (int): The byte alignment to reach (usually 4, 8, or 16). Default is 4.
            - strict (bool): If True, reads the skipped bytes and warns if they aren't nulls (0x00).
                            Useful for debugging unknown file formats.
            """
            current_pos = self.tell()
            
            # Calculate exactly how many bytes we need to jump to hit the next boundary.
            # Example: if pos is 13, and boundary is 4.
            # (4 - (13 % 4)) % 4  ->  (4 - 1) % 4  ->  3 bytes of padding needed.
            padding_needed = (boundary - (current_pos % boundary)) % boundary
            
            if padding_needed > 0:
                if strict:
                    # Read the bytes to ensure we aren't skipping actual data
                    padding_bytes = self.read_bytes(padding_needed)
                    
                    # If any byte in the sequence is not 0x00, throw a warning
                    if any(b != 0 for b in padding_bytes):
                        print(f"[WARNING] Alignment skipped non-null data at offset {current_pos}! Expected {padding_needed} null bytes, got: {padding_bytes}")
                else:
                    # Fast path: simply fast-forward the cursor over the padding
                    self.seek(current_pos + padding_needed)

    # - - - - - - - - - - - - - - -
    
    def read(self, fmt) -> tuple:
        """ Using `struct.unpack_from()`, return the needed value, and advance the position forward by the number of bytes the desired type occupies. """
        result = struct.unpack_from(("" if self.LE else ">") + fmt, self.data, self.offset)
        self.offset += struct.calcsize(fmt)
        return result
    
    def read_string(self, length: int) -> str:
        """ Read a string from `x` amount of bytes. """
        result = self.read_bytes(length)
        return result.tobytes().decode()
    
    def read_bytes(self, length: int) -> memoryview:
        """ Read a series of `x` bytes. """
        result = self.read_bytes_at(0, length)
        self.offset += length
        return result
    
    def read_bytes_at(self, offset: int, length: int) -> memoryview:
        """ Read raw bytes from the given offset for the given number of bytes forward. """
        return memoryview(self.data)[self.offset + offset:self.offset + offset + length]

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # ------------------------
    # INTEGER WRITING METHODS
    # ------------------------

    def ubyte(self) -> int:
        """ Read an unsigned 8 bit integer, and advance the position forward by 1 byte. """
        return self.read("B")[0]
        
    def byte(self) -> int:
        """ Read a signed 8 bit integer, and advance the position forward by 1 byte. """
        return self.read("b")[0]
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def ushort(self) -> int:
        """ Read an unsigned 16 bit integer, and advance the position forward by 2 bytes. """
        return self.read("H")[0]
        
    def short(self) -> int:
        """ Read a signed 16 bit integer, and advance the position forward by 2 bytes. """
        return self.read("h")[0]
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def uint32(self) -> int:
        """ Read an unsigned 32 bit integer, and advance the position forward by 4 bytes. """
        return self.read("I")[0]

    def int32(self) -> int:
        """ Read a signed 32 bit integer, and advance the position forward by 4 bytes. """
        return self.read("i")[0]
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def uint64(self) -> int:
        """ Read an unsigned 64 bit integer, and advance the position forward by 8 bytes. """
        return self.read("Q")[0]

    def int64(self) -> int:
        """ Read a signed 64 bit integer, and advance the position forward by 8 bytes. """
        return self.read("q")[0]
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def hfloat16(self) -> float:
        """ Read a signed 16 bit half-precision floating point value, and advance the position forward by 2 bytes. """
        return self.read("e")[0]
        
    def float32(self) -> float:
        """ Read a signed 32 bit floating point value, and advance the position forward by 4 bytes. """
        return self.read("f")[0]
        
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # -------------------------------
    # V E C T O R S
    # -------------------------------

    def vec2hf(self) -> tuple[float, float]:
        """ Read two 16 bit half-precision floating point numbers, and return them as a 2-point vector as a tuple. Advances the position forward by 4 bytes. """
        return self.read("2e")
    
    def vec2f(self) -> tuple[float, float]:
        """ Read two 32 bit floating point numbers, and return them as a 2-point vector as a tuple. Advances the position forward by 8 bytes. """
        return self.read("2f")
    
    def vec2si(self) -> tuple[int, int]:
        """ Read two 32 bit signed integers, and return them as a 2-point vector as a tuple. Advances the position forward by 8 bytes. """
        return self.read("2i")
    
    def vec2ui(self) -> tuple[int, int]:
        """ Read two 32 bit unsigned integers, and return them as a 2-point vector as a tuple. Advances the position forward by 8 bytes. """
        return self.read("2I")
    
    def vec3si(self) -> tuple[int, int, int]:
        """ Read three 32 bit signed integers, and return them as a 3-point vector as a tuple. Advances the position forward by 12 bytes. """
        return self.read("3i")
    
    def vec3ui(self) -> tuple[int, int, int]:
        """ Read three 32 bit unsigned integers, and return them as a 3-point vector as a tuple. Advances the position forward by 12 bytes. """
        return self.read("3I")

    def vec3f(self) -> tuple[float, float, float]:
        """ Read three 32 bit floating point numbers, and return them as a 3-point vector as a tuple. Advances the position forward by 12 bytes. """
        return self.read("3f")
    
    def vec4f(self) -> tuple[float, float, float, float]:
        """ Read four 32 bit floating point numbers, and return them as a 4-point vector as a tuple. Advances the position forward by 16 bytes. """
        return self.read("4f")
    
    def vec3sb(self) -> tuple[int, int, int]:
        """ Read three signed 8 bit numbers, and return them as a 4-point vector as a tuple. Advances the position forward by 3 bytes. """
        return self.read("3b")
    
    def vec3ub(self) -> tuple[int, int, int]:
        """ Read three unsigned 8 bit numbers, and return them as a 4-point vector as a tuple. Advances the position forward by 3 bytes. """
        return self.read("3B")
    
    def vec4sb(self) -> tuple[int, int, int, int]:
        """ Read four signed 8 bit numbers, and return them as a 4-point vector as a tuple. Advances the position forward by 4 bytes. """
        return self.read("4b")
    
    def vec4ub(self) -> tuple[int, int, int, int]:
        """ Read four unsigned 8 bit numbers, and return them as a 4-point vector as a tuple. Advances the position forward by 4 bytes. """
        return self.read("4B")
    
    def vec2ss(self) -> tuple[int, int]:
        """ Read two signed 16 bit numbers, and return them as a 2-point vector as a tuple. Advances the position forward by 4 bytes. """
        return self.read("2h")
    
    def vec2us(self) -> tuple[int, int]:
        """ Read two unsigned 16 bit numbers, and return them as a 2-point vector as a tuple. Advances the position forward by 4 bytes. """
        return self.read("2H")
        
    def vec3ss(self) -> tuple[int, int, int]:
        """ Read three signed 16 bit numbers, and return them as a 3-point vector as a tuple. Advances the position forward by 6 bytes. """
        return self.read("3h")
    
    def vec3us(self) -> tuple[int, int, int]:
        """ Read three unsigned 16 bit numbers, and return them as a 3-point vector as a tuple. Advances the position forward by 6 bytes. """
        return self.read("3H")
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
