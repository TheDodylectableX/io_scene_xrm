# -----------------------------------------------------
#   WRITER CLASS
#       Class for writing data in files
# -----------------------------------------------------
""" Module with helper classes for writing binary file data. """

import os
import bpy, struct, math
import mathutils

# -----------------------------------------------------

# Base class for writing various data types.
class Writer(object):
    """ Data writer class. Used for writing binary data to a file! """
    def __init__(self, output_file: str | bytearray | None, is_little_endian: bool = True) -> None:
        """ Construct a new Writer object. Input data, and if we want to use little endianness for our writing process. """

        # Initialize the class
        super().__init__()

        # -------------------------------
        # -- CLASS MEMBERS --------------
        # -------------------------------
        
        # -- DATA OFFSET
        self.offset: int = 0
        """ Current position in writing data. """

        # -- FILE CONTENTS
        self.file = bytearray([]) if output_file is None else output_file
        """ The contents of the written file or the written file's location. """

        # -- BUFFER LENGTH
        self.length: int = 0
        """ Length of the current buffer. """

        # -- IS LITTLE ENDIAN
        self.is_LE: bool = is_little_endian
        """ Is this file little endian? """

        # -- IS RAW WRITE
        self.raw = isinstance(self.file, bytearray) or self.file is None
        """ Are we writing to a raw array of bytes? """

    # -------------------------------

    # Closes the file.
    def close(self):
        """ Closes the file. """
        if self.file and not isinstance(self.file, bytearray):
            self.file.close()
            self.file = None

    # Save the file to the given location.
    def save(self, file_path: str) -> None:
        """ Save the data from this object to a file. """
        # Is the file data even valid?
        if self.file:

            # If the folder that the file path given didn't exist then let's make it ourselves
            folder_dir = os.path.dirname(file_path)
            if not os.path.exists(folder_dir):
                os.makedirs(folder_dir)

            # In binary write mode, write our object's data to the file!
            with open(file_path, "wb") as bin_file:
                bin_file.write(self.file)

    # -------------------------------

    # Write a value to the file with a format string and a value.
    def write(self, fmt, *args):
        """ Write a value to the file with a format string and a value. """
        # Packed value based on format string
        packed_val = struct.pack(("" if self.is_LE else ">") + fmt, *args)

        # Write to raw byte array
        if isinstance(self.file, bytearray):  # When we're writing to a bytearray
            self.file.extend(packed_val)

        elif self.raw:  # If we're writing to a raw array or bytearray (in-memory data)
            if self.offset == len(self.file):
                self.file.extend(packed_val)  # Append if we're at the end
            else:
                # Write data at the current offset
                for index, byte in enumerate(packed_val):
                    self.file[self.offset + index] = byte

        else:  # Write directly to a file
            self.file.write(packed_val)

        # Move offset forward by the size of the packed value
        self.offset += struct.calcsize(fmt)

        # Update the length
        if isinstance(self.file, bytearray):
            self.length = len(self.file)
        else:
            self.length = self.offset  # For file, length is tracked by the offset
        
        return packed_val  # Ensure this returns the packed value

    # -------------------------------

    # Where are we in writing?
    def tell(self) -> int:
        """ Where are we currently in writing? """
        return self.offset if self.raw else self.file.tell()
    
    # Move to a specific location.
    def seek(self, position: int) -> None:
        """ Move the write cursor to a specific location. """
        if (self.raw):
            self.offset = position
        else:
            self.file.seek(position)

    # -------------------------------

    # Write an ASCII string.
    def ascii_string(self, text: str) -> None:
        """ Write an ASCII-based text string, and move the position forward by the number of characters in the string. """
        encoded = text.encode('ascii')
        self.write(f"{len(encoded)}s", encoded)

    # Write a string with its length first, then the string afterwards.
    def num_string(self, text: str) -> None:
        """ Write a string but the length of it first then the string afterwards. Moves the position forward by 4 bytes + the length of the text string. """
        self.uint32(len(text))
        self.ascii_string(text)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # ------------------------
    # INTEGER WRITING METHODS
    # ------------------------

    def ubyte(self, value: int) -> int:
        """ Write an unsigned 8 bit integer, and advance the position forward by 1 byte. """
        return self.write("B", value)[0]
        
    def byte(self, value: int) -> int:
        """ Write a signed 8 bit integer, and advance the position forward by 1 byte. """
        return self.write("b", value)[0]
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def ushort(self, value: int) -> int:
        """ Write an unsigned 16 bit integer, and advance the position forward by 2 bytes. """
        return self.write("H", value)[0]
        
    def short(self, value: int) -> int:
        """ Write a signed 16 bit integer, and advance the position forward by 2 bytes. """
        return self.write("h", value)[0]
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def uint32(self, value: int) -> int:
        """ Write an unsigned 32 bit integer, and advance the position forward by 4 bytes. """
        return self.write("I", value)[0]

    def int32(self, value: int) -> int:
        """ Write a signed 32 bit integer, and advance the position forward by 4 bytes. """
        return self.write("i", value)[0]
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def uint64(self, value: int) -> int:
        """ Write an unsigned 64 bit integer, and advance the position forward by 8 bytes. """
        return self.write("Q", value)[0]

    def int64(self, value: int) -> int:
        """ Write a signed 64 bit integer, and advance the position forward by 8 bytes. """
        return self.write("q", value)[0]
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def hfloat16(self, value: float) -> float:
        """ Write a signed 16 bit half-precision floating point value, and advance the position forward by 2 bytes. """
        return self.write("e", value)[0]
        
    def float32(self, value: float) -> float:
        """ Write a signed 32 bit floating point value, and advance the position forward by 4 bytes. """
        return self.write("f", value)[0]
        
    # -------------------------------
    # V E C T O R S
    # -------------------------------

    def vec2hf(self, value: tuple[float, float]) -> tuple[float, float]:
        """ Write two 16 bit half-precision floating point numbers, and return them as a 2-point vector as a tuple. Advances the position forward by 4 bytes. """
        return self.write("2e", *value)

    def vec2f(self, value: tuple[float, float]) -> tuple[float, float]:
        """ Write two 32 bit floating point numbers, and return them as a 2-point vector as a tuple. Advances the position forward by 8 bytes. """
        return self.write("2f", *value)

    def vec2si(self, value: tuple[int, int]) -> tuple[int, int]:
        """ Write two 32 bit signed integers, and return them as a 2-point vector as a tuple. Advances the position forward by 8 bytes. """
        return self.write("2i", *value)
    
    def vec2ui(self, value: tuple[int, int]) -> tuple[int, int]:
        """ Write two 32 bit unsigned integers, and return them as a 2-point vector as a tuple. Advances the position forward by 8 bytes. """
        return self.write("2I", *value)
    
    def vec3si(self, value: tuple[int, int, int]) -> tuple[int, int, int]:
        """ Write three 32 bit signed integers, and return them as a 3-point vector as a tuple. Advances the position forward by 12 bytes. """
        return self.write("3i", *value)
    
    def vec3ui(self, value: tuple[int, int, int]) -> tuple[int, int, int]:
        """ Write three 32 bit unsigned integers, and return them as a 3-point vector as a tuple. Advances the position forward by 12 bytes. """
        return self.write("3I", *value)

    def vec3f(self, value: tuple[float, float, float]) -> tuple[float, float, float]:
        """ Write three 32 bit floating point numbers, and return them as a 3-point vector as a tuple. Advances the position forward by 12 bytes. """
        return self.write("3f", *value)
    
    def vec4f(self, value: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        """ Write four 32 bit floating point numbers, and return them as a 4-point vector as a tuple. Advances the position forward by 16 bytes. """
        return self.write("4f", *value)
    
    def vec3sb(self, value: tuple[int, int, int]) -> tuple[int, int, int]:
        """ Write three signed 8 bit numbers, and return them as a 4-point vector as a tuple. Advances the position forward by 3 bytes. """
        return self.write("3b", *value)
    
    def vec3sb(self, value: tuple[int, int, int]) -> tuple[int, int, int]:
        """ Write three unsigned 8 bit numbers, and return them as a 4-point vector as a tuple. Advances the position forward by 3 bytes. """
        return self.write("3B", *value)
    
    def vec4sb(self, value: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        """ Write four signed 8 bit numbers, and return them as a 4-point vector as a tuple. Advances the position forward by 4 bytes. """
        return self.write("4b", *value)
    
    def vec4ub(self, value: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        """ Write four unsigned 8 bit numbers, and return them as a 4-point vector as a tuple. Advances the position forward by 4 bytes. """
        return self.write("4B", *value)
    
    def vec2ss(self, value: tuple[int, int]) -> tuple[int, int]:
        """ Write two signed 16 bit numbers, and return them as a 2-point vector as a tuple. Advances the position forward by 4 bytes. """
        return self.write("2h", *value)
    
    def vec2us(self, value: tuple[int, int]) -> tuple[int, int]:
        """ Write two unsigned 16 bit numbers, and return them as a 2-point vector as a tuple. Advances the position forward by 4 bytes. """
        return self.write("2H", *value)
        
    def vec3ss(self, value: tuple[int, int, int]) -> tuple[int, int, int]:
        """ Write three signed 16 bit numbers, and return them as a 3-point vector as a tuple. Advances the position forward by 6 bytes. """
        return self.write("3h", *value)
    
    def vec3us(self, value: tuple[int, int, int]) -> tuple[int, int, int]:
        """ Write three unsigned 16 bit numbers, and return them as a 3-point vector as a tuple. Advances the position forward by 6 bytes. """
        return self.write("3H", *value)
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -