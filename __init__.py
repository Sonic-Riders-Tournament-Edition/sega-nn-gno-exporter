bl_info = {
    "name": "Sega GNO Model Exporter",
    "description": "Exports a Sega GNO model for the GameCube version of Sonic Riders.",
    "author": "Exortile",
    "version": (1, 0),
    "blender": (3, 1, 0),
    "location": "File > Export",
    "warning": "",
    "support": "COMMUNITY",
    "category": "Import-Export",
}

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import BoolProperty, StringProperty, EnumProperty
from . import nn
import struct

export_types = (
    ("model", "Character Model", "Exports a character GNO model"),
    ("splines", "Splines", "Exports splines (GameCube version)")
)

def write_model(context, **keywords):
    file = nn.File(keywords["filepath"], 'wb')
    NGOB_header_offset, offset_to_NOF0, NGOB_size, main_object_data_offset = \
        nn.write_new_gno_file_2(file, **keywords)
    del file

    data = struct.pack('<I', NGOB_size-0x8)
    data += struct.pack('>I', main_object_data_offset)
    file = nn.File(keywords["filepath"], 'r+b') # replace bytes
    file.seek(NGOB_header_offset + 0x4)
    file.write(data)
    file.seek(0)
    content = file.fileobject.read()
    del file

    file = nn.File(keywords["filepath"], 'wb') # prepend to start
    if keywords["include_texture_list"]:
        NGOB_header_index = 2
    else:
        NGOB_header_index = 1
    
    data = nn.generate_NGIF_header(offset_to_NOF0 + 0x20, NGOB_header_index)
    file.write(data + content)
    del file

def write_splines(context, **keywords):
    file = nn.File(keywords["filepath"], 'wb')
    spline_info_offsets, spline_data_offsets = nn.write_new_spline_file(file)
    del file

    file = nn.File(keywords["filepath"], 'r+b') # replace bytes
    file.seek(0xC)
    for key in spline_info_offsets:
        offset = spline_info_offsets[key]
        file.write_int(offset)

    for key in spline_info_offsets:
        offset = spline_info_offsets[key]
        data = spline_data_offsets[key]
        file.seek(offset)
        for off in data:
            file.write_int(off)

    del file

def write_file(context, **keywords):
    if keywords["format"] == "model":
        write_model(context, **keywords)
    elif keywords["format"] == "splines":
        write_splines(context, **keywords)
    

    return {'FINISHED'}

class ExportGNO(bpy.types.Operator, ExportHelper):
    """Exports a Sega GNO model for the GameCube version of Sonic Riders"""
    bl_idname = "export_scene.gno"
    bl_label = "Export GNO"
    
    filename_ext = ".gno"
    filter_glob: StringProperty(
        default="*.gno",
        options={'HIDDEN'},
    )
    
    format: EnumProperty(
        name = "Format",
        description = "Export format type",
        items = export_types,
        default = export_types[0][0]
    )

    include_texture_list: BoolProperty(
        name = "Include texture list",
        description = "Includes a texture list section in the exported GNO model",
        default = True
    )

    original_model_bool: BoolProperty(
        name = "Use bone data from other model",
        description = "Imports bone data from another GNO model",
        default = False,
    )
    
    original_model: StringProperty(
        name = "Filename",
        description = "Note, the file must be in the same directory as the export path!",
        subtype = "FILE_NAME"
    )
    
    def execute(self, context):
        keywords = self.as_keywords()
        return write_file(context, **keywords)
    
    def draw(self, context):
        layout = self.layout
        layout.alignment = 'RIGHT'
        
        layout.prop(self, "format")
        layout.prop(self, "include_texture_list")

        box = layout.box()
        box.row().prop(self, "original_model_bool")
        row = box.row()
        row.prop(self, "original_model")
        row.enabled = self.original_model_bool
    
def menu_export_func(self, context):
    self.layout.operator(ExportGNO.bl_idname, text="Sonic Riders GNO Model (.gno)")

def register():
    bpy.utils.register_class(ExportGNO)
    bpy.types.TOPBAR_MT_file_export.append(menu_export_func)
def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_export_func)
    bpy.utils.unregister_class(ExportGNO)
    
if __name__ == "__main__":
    register()