# -----------------------------------------------------

# --------
# IMPORTS
# --------

import bpy, random
from typing import cast
import math
import os
import struct

from .readers import Reader
from .bpy_util_funcs import *
from .srm_parser import *
from .trm_parser import *
from .model_importer import *
from .model_exporter import *

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

# -----------------------------------------------------

# Plugin Information / Metadata
bl_info = {
    "name": "Aspyr | Saber Remasters Modding Plugin",
    "description": "Import and export models from/to the Tomb Raider and Soul Reaver remasters",
    "author": "Dodylectable",
    "blender": (4, 0, 0),
    "version": (0, 0, 1),
    "location": "File > Import-Export",
    "support": "COMMUNITY",
    "category": "Import-Export"
}

# -----------------------------------------------------

# --------------
# ICONS
# Oooh, fancy!
# --------------

# """The master list of custom icons the plugin uses."""

# # Register custom icons
# def register_icons() -> None:
#     """Register the custom icon images that our plugin uses!"""
#     global custom_icons
#     import os, bpy.utils.previews

#     script_dir = os.path.dirname(__file__)
#     icon_dir = os.path.join(script_dir, "icons")

#     pcoll = bpy.utils.previews.new()

#     # Read all icons in the folder
#     image_file_list = os.listdir(icon_dir)

#     # Register every image we got
#     for (image) in (image_file_list):
#         shorthand = image.split(".")[0]
#         pcoll.load(shorthand, os.path.join(icon_dir, shorthand + ".png"), 'IMAGE')

#     custom_icons = pcoll

# # Unregister custom icons
# def unregister_icons() -> None:
#     """Unregister the custom icons we've loaded."""
#     if (custom_icons):
#         bpy.utils.previews.remove(custom_icons)

# # Get an icon from our list of custom icons
# def get_icon(icon_name):
#     """Get an icon from the list of custom icons!"""
#     if (not custom_icons):
#         return None
    
#     if (icon_name in custom_icons):
#         return custom_icons[icon_name]
    
#     return None

# # Get an icon from our list of custom icons by its ID!
# def get_icon_by_id(icon_name):
#     """Get an icon from the list of custom icons by its ID."""
#     if (not custom_icons):
#         print(f"Missing icon {out_icon}, icons were not loaded.")
#         return 0
    
#     out_icon = get_icon(icon_name)

#     if (not out_icon):
#         print(f"Icon {out_icon} was missing")
#         return 0
    
#     return out_icon.icon_id

# -------------------------------------------------------------------------

# ==========
# IMPORTERS
# ==========

class ImportSRRMesh(Operator, ImportHelper):
    bl_idname = "import_srr.mesh"
    bl_label = "Soul Reaver I-II Remastered Mesh (.SRM)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".SRM"

    filter_glob: StringProperty(
        default="*.SRM",
        options={'HIDDEN'},
        maxlen=1024,
    ) # type: ignore

    custom_normals: BoolProperty(
        name="Custom Normals",
        description="Rather than using the original normals, re-calculate them when the meshes are created. (Looks smoother)",
        default=False,
    ) # type: ignore

    assign_material_colors: BoolProperty(
        name="Assign Material Colors",
        description="Assign random colors to the model's materials to help with distingushing submeshes.",
        default=True,
    ) # type: ignore

    import_textures: BoolProperty(
        name="Import Textures",
        description="Import the model's textures while we're at it. IMPORTANT: You must be importing from the game's directory for it to work properly.",
        default=True,
    ) # type: ignore

    def execute(self, context):
        return import_sr_model(self.filepath, self.custom_normals, self.assign_material_colors, self.import_textures)

# -------------------------------------------------------------------------

class ImportTRRMesh(Operator, ImportHelper):
    bl_idname = "import_trr.mesh"
    bl_label = "Tomb Raider I-V Remastered Mesh (.TRM)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".TRM"

    filter_glob: StringProperty(
        default="*.TRM",
        options={'HIDDEN'},
        maxlen=1024,
    ) # type: ignore

    custom_normals: BoolProperty(
        name="Custom Normals",
        description="Rather than using the original normals, re-calculate them when the meshes are created. (Looks smoother)",
        default=False,
    ) # type: ignore

    assign_material_colors: BoolProperty(
        name="Assign Material Colors",
        description="Assign random colors to the model's materials to help with distingushing submeshes.",
        default=True,
    ) # type: ignore

    import_textures: BoolProperty(
        name="Import Textures",
        description="Import the model's textures while we're at it. IMPORTANT: You must be importing from the game's directory for it to work properly.",
        default=True,
    ) # type: ignore

    def execute(self, context):
       return import_tr_model(self.filepath, self.custom_normals, self.assign_material_colors, self.import_textures)

# --------------------------------------------------------------------------------------------------------

# ==========
# EXPORTERS
# ==========

class ExportSRRMesh(Operator, ImportHelper):
    bl_idname = "export_srr.mesh"
    bl_label = "Soul Reaver I-II Remastered Mesh (.SRM)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".SRM"

    filter_glob: StringProperty(
        default="*.SRM",
        options={'HIDDEN'},
        maxlen=1024,
    ) # type: ignore

    version: EnumProperty(
        name="Version",
        description="Choose the version of the format to export in, Set to V1 by Default",
        items=(
            ('V1', "Version 1", "Export your texture(s) in R8_UNORM format"),
            ('V2', "Version 2", "Export your texture(s) in R16_FLOAT format"),
            ('V3', "Version 3", "Export your texture(s) in R32_FLOAT format"),
        ),
        default='V1',
    ) # type: ignore

    def execute(self, context):
        return export_sr_model(self.filepath, self.version)

# -------------------------------------------------------------------------

class ExportTRRMesh(Operator, ImportHelper):
    bl_idname = "export_trr.mesh"
    bl_label = "Tomb Raider I-V Remastered Mesh (.TRM)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".TRM"

    filter_glob: StringProperty(
        default="*.TRM",
        options={'HIDDEN'},
        maxlen=1024,
    ) # type: ignore

    filter_glob: StringProperty(
        default="*.SRM",
        options={'HIDDEN'},
        maxlen=1024,
    ) # type: ignore

    version: EnumProperty(
        name="Version",
        description="Choose the version of the format to export in, Set to V1 by Default",
        items=(
            ('V1', "Version 1", "Export your texture(s) in R8_UNORM format"),
            ('V2', "Version 2", "Export your texture(s) in R16_FLOAT format"),
            ('V3', "Version 3", "Export your texture(s) in R32_FLOAT format"),
        ),
        default='V1',
    ) # type: ignore

    def execute(self, context):
        return export_tr_model(self.filepath, self.version)

# --------------------------------------------------------------------------------------------------------
        
def menu_func_import(self, context):
    self.layout.operator(ImportSRRMesh.bl_idname, text="Soul Reaver I-II Remastered Mesh (.SRM)")
    self.layout.operator(ImportTRRMesh.bl_idname, text="Tomb Raider I-V Remastered Mesh (.TRM)")

def menu_func_export(self, context):
    self.layout.operator(ExportSRRMesh.bl_idname, text="Soul Reaver I-II Remastered Mesh (.SRM)")
    self.layout.operator(ExportTRRMesh.bl_idname, text="Tomb Raider I-V Remastered Mesh (.TRM)")

# -------------------------------------------------------------------------

def register():
    bpy.utils.register_class(ImportSRRMesh)
    bpy.utils.register_class(ImportTRRMesh)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.utils.register_class(ExportSRRMesh)
    bpy.utils.register_class(ExportTRRMesh)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(ImportSRRMesh)
    bpy.utils.unregister_class(ImportTRRMesh)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.utils.unregister_class(ExportSRRMesh)
    bpy.utils.unregister_class(ExportTRRMesh)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    # --------------------------------------------------------------------------------------------------------
