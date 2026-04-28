# -----------------------------------------------------

# --------
# IMPORTS
# --------

import bpy
import bpy.utils.previews
import random
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
    "name": "Legacy of Kain and Tomb Raider Remasters Modding Plugin",
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

# Register custom icons
def register_icons() -> None:
    """Register the custom icon images that our plugin uses!"""
    global custom_icons

    script_dir = os.path.dirname(__file__)
    icon_dir = os.path.join(script_dir, "icons")
    pcoll = bpy.utils.previews.new()

    # Register every image we got
    for icon_name in ["SR3", "SRX", "TRX"]:
        path = os.path.join(icon_dir, icon_name + ".png")
        if os.path.exists(path):
            pcoll.load(icon_name, path, 'IMAGE')

    custom_icons = pcoll

# Unregister custom icons
def unregister_icons() -> None:
    """Unregister the custom icons we've loaded."""
    if (custom_icons):
        bpy.utils.previews.remove(custom_icons)

# Get an icon from our list of custom icons
def get_icon(icon_name):
    """Get an icon from the list of custom icons!"""
    if (not custom_icons):
        return None
    
    if (icon_name in custom_icons):
        return custom_icons[icon_name]
    
    return None

# Get an icon from our list of custom icons by its ID!
def get_icon_by_id(icon_name):
    """Get an icon from the list of custom icons by its ID."""
    if (not custom_icons):
        print(f"Missing icon {out_icon}, icons were not loaded.")
        return 0
    
    out_icon = get_icon(icon_name)

    if (not out_icon):
        print(f"Icon {out_icon} was missing")
        return 0
    
    return out_icon.icon_id

# -------------------------------------------------------------------------

# ==========
# IMPORTERS
# ==========

class ImportSRRMesh(Operator, ImportHelper):
    bl_idname = "import_srr.mesh"
    bl_label = "Legacy of Kain: Soul Reaver I-II Remastered Mesh (.SRM)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".SRM"

    filter_glob: StringProperty(
        default="*.SRM",
        options={'HIDDEN'},
        maxlen=1024,
    ) # type: ignore

    import_skeleton: BoolProperty(
        name="Import Skeleton",
        description="Import the model's skeleton.",
        default=True,
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
        return import_sr_model(self.filepath, GAME_SRX, self.import_skeleton, True, self.custom_normals, self.assign_material_colors, self.import_textures)

# -------------------------------------------------------------------------

class ImportSR3RMesh(Operator, ImportHelper):
    bl_idname = "import_sr3r.mesh"
    bl_label = "Legacy of Kain: Defiance Remastered Mesh (.SRM)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".SRM"

    filter_glob: StringProperty(
        default="*.SRM",
        options={'HIDDEN'},
        maxlen=1024,
    ) # type: ignore
    
    import_skeleton: BoolProperty(
        name="Import Skeleton",
        description="Import the model's skeleton.",
        default=True,
    ) # type: ignore

    import_lods: BoolProperty(
        name="Import LODs",
        description="Import the model's LODs. (If it has any)",
        default=True,
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
        return import_sr_model(self.filepath, GAME_SR3, self.import_skeleton, self.import_lods, self.custom_normals, self.assign_material_colors, self.import_textures)

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

class ImportAoDRMesh(Operator, ImportHelper):
    bl_idname = "import_aodr.mesh"
    bl_label = "Tomb Raider: Angel of Darkness (Remastered) Mesh (.CHR)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".CHR"

    filter_glob: StringProperty(
        default="*.CHR",
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
       return import_aodr_model(self.filepath, self.custom_normals, self.assign_material_colors, self.import_textures)

class ImportAoDRMorph(Operator, ImportHelper):
    bl_idname = "import_aodr.morph"
    bl_label = "Tomb Raider: Angel of Darkness (Remastered) Morph Target (.TMT)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".TMT"

    filter_glob: StringProperty(
        default="*.TMT",
        options={'HIDDEN'},
        maxlen=1024,
    ) # type: ignore

    def execute(self, context):
       return import_aodr_morph(self.filepath)

# --------------------------------------------------------------------------------------------------------

# ==========
# EXPORTERS
# ==========

class ExportSRRMesh(Operator, ImportHelper):
    bl_idname = "export_srr.mesh"
    bl_label = "Legacy of Kain: Soul Reaver I-II Remastered Mesh (.SRM)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".SRM"

    filter_glob: StringProperty(
        default="*.SRM",
        options={'HIDDEN'},
        maxlen=1024,
    ) # type: ignore

    def execute(self, context):
        # The 'filepath' from ImportHelper is the REFERENCE file the user picked
        reference_path = self.filepath
        
        # Get the active object to determine the new filename
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object selected to export.")
            return {'CANCELLED'}

        # Derive the directory and create the new filename, We take the folder from the reference but the name from the Blender object
        output_dir = os.path.dirname(reference_path)
        
        # Sanitize the object's name (Remove special characters that the OS might hate)
        clean_obj_name = "".join([c for c in obj.name if c.isalnum() or c in (' ', '_', '-')]).rstrip()
        output_filename = f"{clean_obj_name}.SRM"
        
        # Combine into the final export path
        final_export_path = os.path.join(output_dir, output_filename)

        print(f"Reference SRM: {reference_path}")
        print(f"Exporting To: {final_export_path}")

        return export_sr_model(self, context, final_export_path, reference_path, GAME_SRX)

# -------------------------------------------------------------------------

class ExportSR3RMesh(Operator, ImportHelper):
    bl_idname = "export_sr3r.mesh"
    bl_label = "Legacy of Kain: Defiance Remastered Mesh (.SRM)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".SRM"

    filter_glob: StringProperty(
        default="*.SRM",
        options={'HIDDEN'},
        maxlen=1024,
    ) # type: ignore

    export_lods: BoolProperty(
        name="Export LODs",
        description="Export LODs for the model. (All meshes in the scene will be exported!)",
        default=True,
    ) # type: ignore

    def execute(self, context):
        # The 'filepath' from ImportHelper is the REFERENCE file the user picked
        reference_path = self.filepath
        
        # Get the active object to determine the new filename
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object selected to export.")
            return {'CANCELLED'}

        # Derive the directory and create the new filename, We take the folder from the reference but the name from the Blender object
        output_dir = os.path.dirname(reference_path)
        
        # Sanitize the object's name (Remove special characters that the OS might hate)
        clean_obj_name = "".join([c for c in obj.name if c.isalnum() or c in (' ', '_', '-')]).rstrip()
        output_filename = f"{clean_obj_name}.SRM"
        
        # Combine into the final export path
        final_export_path = os.path.join(output_dir, output_filename)

        print(f"Reference SRM: {reference_path}")
        print(f"Exporting To: {final_export_path}")

        return export_sr3_model(self, context, final_export_path, reference_path, GAME_SR3, self.export_lods)

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
        default="*.TRM",
        options={'HIDDEN'},
        maxlen=1024,
    ) # type: ignore

    head_model: BoolProperty(
        name="Head Model",
        description="Export as a head model instead.",
        default=False,
    ) # type: ignore

    hd_model: BoolProperty(
        name="HD Model",
        description="Export as a Magic Media HD model instead.",
        default=False,
    ) # type: ignore

    def execute(self, context):
        return export_tr_model(self, context, self.filepath, self.head_model, self.hd_model)

# -------------------------------------------------------------------------

class ExportAoDRMesh(Operator, ImportHelper):
    bl_idname = "export_aodr.mesh"
    bl_label = "Tomb Raider: Angel of Darkness (Remastered) Mesh (.CHR)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".CHR"

    filter_glob: StringProperty(
        default="*.CHR",
        options={'HIDDEN'},
        maxlen=1024,
    ) # type: ignore

    filter_glob: StringProperty(
        default="*.CHR",
        options={'HIDDEN'},
        maxlen=1024,
    ) # type: ignore

    def execute(self, context):
        return export_tr_model(self, context, self.filepath)

# --------------------------------------------------------------------------------------------------------
        
# ========================
# SUBMENU CREATION
# ========================

# --- IMPORT MENUS ---
class IMPORT_MT_lok_remasters(bpy.types.Menu):
    bl_idname = "IMPORT_MT_lok_remasters"
    bl_label = "Legacy of Kain Remasters"

    def draw(self, context):
        layout = self.layout
        layout.operator(ImportSRRMesh.bl_idname, text="Soul Reaver I-II Mesh (.SRM)", icon_value=get_icon_by_id("SRX"))
        layout.operator(ImportSR3RMesh.bl_idname, text="Defiance Mesh (.SRM)", icon_value=get_icon_by_id("SR3"))
class IMPORT_MT_tr_remasters(bpy.types.Menu):
    bl_idname = "IMPORT_MT_tr_remasters"
    bl_label = "Tomb Raider Remasters"

    def draw(self, context):
        layout = self.layout
        layout.operator(ImportTRRMesh.bl_idname, text="Tomb Raider I-V Mesh (.TRM)", icon_value=get_icon_by_id("TRX"))
        layout.operator(ImportAoDRMesh.bl_idname, text="Angel of Darkness Mesh (.CHR)", icon_value=get_icon_by_id("TRX"))
        layout.operator(ImportAoDRMorph.bl_idname, text="Angel of Darkness Morph Target (.TMT)", icon_value=get_icon_by_id("TRX"))

# --- EXPORT MENUS ---
class EXPORT_MT_lok_remasters(bpy.types.Menu):
    bl_idname = "EXPORT_MT_lok_remasters"
    bl_label = "Legacy of Kain Remasters"

    def draw(self, context):
        layout = self.layout
        layout.operator(ExportSRRMesh.bl_idname, text="Soul Reaver I-II Mesh (.SRM)", icon_value=get_icon_by_id("SRX"))
        layout.operator(ExportSR3RMesh.bl_idname, text="Defiance Mesh (.SRM)", icon_value=get_icon_by_id("SR3"))
class EXPORT_MT_tr_remasters(bpy.types.Menu):
    bl_idname = "EXPORT_MT_tr_remasters"
    bl_label = "Tomb Raider Remasters"

    def draw(self, context):
        layout = self.layout
        layout.operator(ExportTRRMesh.bl_idname, text="Tomb Raider I-V Mesh (.TRM)", icon_value=get_icon_by_id("TRX"))
        layout.operator(ExportAoDRMesh.bl_idname, text="Angel of Darkness Mesh (.CHR)", icon_value=get_icon_by_id("TRX"))

# ========================
# MENU APPEND FUNCTIONS
# ========================
def menu_func_import_lok(self, context):
    self.layout.menu(IMPORT_MT_lok_remasters.bl_idname, icon_value=get_icon_by_id("SRX"))
def menu_func_import_tr(self, context):
    self.layout.menu(IMPORT_MT_tr_remasters.bl_idname, icon_value=get_icon_by_id("TRX"))

def menu_func_export_lok(self, context):
    self.layout.menu(EXPORT_MT_lok_remasters.bl_idname, icon_value=get_icon_by_id("SRX"))
def menu_func_export_tr(self, context):
    self.layout.menu(EXPORT_MT_tr_remasters.bl_idname, icon_value=get_icon_by_id("TRX"))

# ========================
# CLASS REGISTRATION TUPLE
# ========================
# Add all new Operators, Menus, and Panels here. 
# They will automatically be registered and unregistered.
classes = (
    ImportSRRMesh,
    ImportSR3RMesh,
    ImportTRRMesh,
    ImportAoDRMesh,
    ImportAoDRMorph,

    ExportSRRMesh,
    ExportSR3RMesh,
    ExportTRRMesh,
    ExportAoDRMesh,

    IMPORT_MT_lok_remasters,
    IMPORT_MT_tr_remasters,
    EXPORT_MT_lok_remasters,
    EXPORT_MT_tr_remasters,
)

# ========================
# REGISTRATION
# ========================
def register():
    register_icons()

    # Dynamically register all classes in the tuple
    for cls in classes:
        bpy.utils.register_class(cls)

    # Append custom submenus to Blender's native File > Import/Export menus
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_lok)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_tr)
    
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export_lok)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export_tr)


def unregister():
    # Remove custom submenus from Blender's native menus first
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_lok)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_tr)
    
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export_lok)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export_tr)

    # Dynamically unregister all classes in reverse order to prevent dependency conflicts
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    unregister_icons()

    # --------------------------------------------------------------------------------------------------------
