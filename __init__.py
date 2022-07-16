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
from . import nn_general as nnGeneral
from . import nn_model as nnModel
import struct

export_types = (
    ("model", "Character Model", "Exports a character GNO model"),
    ("splines", "Splines", "Exports splines (GameCube version)")
)

rig_types = (
    ("board_only", "Board", "Rig that only has a bone for the board"),

    ("board_sonic", "Sonic (Board)", "Sonic on a board rig"),
    ("bike_sonic", "Sonic (Bike)", "Sonic on a bike rig"),
    ("skate_sonic", "Sonic (Skate)", "Sonic using skates rig"),

    ("board_tails", "Tails (Board)", "Tails on a board rig"),
    ("bike_tails", "Tails (Bike)", "Tails on a bike rig"),
    ("skate_tails", "Tails (Skate)", "Tails using skates rig"),

    ("board_knuckles", "Knuckles (Board)", "Knuckles on a board rig"),
    ("bike_knuckles", "Knuckles (Bike)", "Knuckles on a bike rig"),
    ("skate_knuckles", "Knuckles (Skate)", "Knuckles using skates rig"),

    ("board_amy", "Amy (Board)", "Amy on a board rig"),
    ("bike_amy", "Amy (Bike)", "Amy on a bike rig"),
    ("skate_amy", "Amy (Skate)", "Amy using skates rig"),

    ("board_jet", "Jet (Board)", "Jet on a board rig"),
    ("bike_jet", "Jet (Bike)", "Jet on a bike rig"),
    ("skate_jet", "Jet (Skate)", "Jet using skates rig"),

    ("board_storm", "Storm (Board)", "Storm on a board rig"),
    ("bike_storm", "Storm (Bike)", "Storm on a bike rig"),
    ("skate_storm", "Storm (Skate)", "Storm using skates rig"),

    ("board_wave", "Wave (Board)", "Wave on a board rig"),
    ("bike_wave", "Wave (Bike)", "Wave on a bike rig"),
    ("skate_wave", "Wave (Skate)", "Wave using skates rig"),

    ("bike_eggman", "Eggman (Bike)", "Eggman on a bike rig"),

    ("board_cream", "Cream (Board)", "Cream on a board rig"),
    ("bike_cream", "Cream (Bike)", "Cream on a bike rig"),
    ("skate_cream", "Cream (Skate)", "Cream using skates rig"),

    ("board_rouge", "Rouge (Board)", "Rouge on a board rig"),
    ("bike_rouge", "Rouge (Bike)", "Rouge on a bike rig"),
    ("skate_rouge", "Rouge (Skate)", "Rouge using skates rig"), 

    ("board_shadow", "Shadow (Board)", "Shadow on a board rig"),
    ("bike_shadow", "Shadow (Bike)", "Shadow on a bike rig"),
    ("skate_shadow", "Shadow (Skate)", "Shadow using skates rig"),

    ("board_nights", "Nights (Board)", "Nights on a board rig"),
    ("bike_nights", "Nights (Bike)", "Nights on a bike rig"),
    ("skate_nights", "Nights (Skate)", "Nights using skates rig"),

    ("board_aiai", "AiAi (Board)", "AiAi on a board rig"),
    ("bike_aiai", "AiAi (Bike)", "AiAi on a bike rig"),
    ("skate_aiai", "AiAi (Skate)", "AiAi using skates rig"),

    ("board_ulala", "Ulala (Board)", "Ulala on a board rig"),

    ("board_e10g", "E10G (Board)", "E10G on a board rig"),

    ("board_e10r", "E10R (Board)", "E10R on a board rig"),

    ("board_silver", "Silver (Board)", "Silver on a board rig"),
)

texture_types = (
    ("none", "None", "No extra properties to the texture"),
    ("reflective", "Reflection Texture", "Uses this texture as a reflective texture in-game"),
    ("emissive", "Emission Texture", "Uses this texture as an emissive texture in-game"),
)

def write_model(context, **keywords):
    with nnModel.File(keywords["filepath"], 'wb') as file:
        NGOB_header_offset, offset_to_NOF0, NGOB_size, main_object_data_offset = \
            nn.write_new_gno_file(file, **keywords)

    data = struct.pack('<I', NGOB_size-0x8)
    data += struct.pack('>I', main_object_data_offset)
    with nnModel.File(keywords["filepath"], 'r+b') as file: # replace bytes
        file.seek(NGOB_header_offset + 0x4)
        file.write(data)
        file.seek(0)
        content = file.fileobject.read()

    with nnModel.File(keywords["filepath"], 'wb') as file: # prepend to start
        if keywords["include_texture_list"]:
            NGOB_header_index = 2
        else:
            NGOB_header_index = 1
        
        data = nnGeneral.generate_NGIF_header(offset_to_NOF0 + 0x20, NGOB_header_index)
        file.write(data + content)

def write_splines(context, **keywords):
    with nnModel.File(keywords["filepath"], 'wb') as file:
        spline_info_offsets, spline_data_offsets = nn.write_new_spline_file(file)

    with nnModel.File(keywords["filepath"], 'r+b') as file: # replace bytes
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

    raw_bone_data: BoolProperty(
        name = "Raw bone data",
        description = "Use this if the supplied file isn't a GNO model, but rather a file only consisting of bone data",
        default = False
    )
    
    original_model: StringProperty(
        name = "Filename",
        description = "Note, the file must be in the same directory as the export path!",
        subtype = "FILE_NAME"
    )

    rig_type: EnumProperty(
        name = "Rig",
        description = "Rig to use upon exporting",
        items = rig_types,
        default = rig_types[0][0],
    )
    
    def execute(self, context):
        keywords = self.as_keywords()
        return write_file(context, **keywords)
    
    def draw(self, context):
        layout = self.layout
        layout.alignment = 'RIGHT'
        
        layout.prop(self, "format")
        layout.prop(self, "rig_type")
        layout.prop(self, "include_texture_list")

        box = layout.box()
        box.row().prop(self, "original_model_bool")
        row1 = box.row()
        row1.prop(self, "raw_bone_data")
        row1.enabled = self.original_model_bool
        row2 = box.row()
        row2.prop(self, "original_model")
        row2.enabled = self.original_model_bool

class GnoVertexGroups(bpy.types.Operator):
    bl_idname = "vertex_groups.gno"
    bl_label = "Create Vertex Groups"

    def execute(self, context):
        mesh = context.active_object
        arm = mesh.find_armature()
        if not arm:
            return {"CANCELLED"}
        
        for bone in arm.pose.bones:
            if bone.name not in mesh.vertex_groups and bone.bone_group.name != "Null_Bone_Group":
                print("{} vertex group created".format(bone.name))
                mesh.vertex_groups.new(name=bone.name)
        
        # ensure vertex groups are sorted
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = mesh
        mesh.select_set(True)

        bpy.ops.object.vertex_group_sort()
        
        return {"FINISHED"}

class GnoMaterialSettings(bpy.types.PropertyGroup):
    disable_backface_culling: BoolProperty(
        name = "Disable backface culling",
        description = "Turns off backface culling for this material",
        default = False
    )

    always_on_top: BoolProperty(
        name = "Always on top",
        description = "Makes it so that the material always renders on top of every other mesh",
        default = False
    )

    fullbright: BoolProperty(
        name = "Fullbright",
        description = "Shades the material a little brighter than usual",
        default = False
    )

class GnoTextureSettings(bpy.types.PropertyGroup):
    texture_property: EnumProperty(
        name = "",
        description = "Extra texture properties",
        items = texture_types,
        default = texture_types[0][0]
    )

class GnoNodePanel(bpy.types.Panel):
    
    bl_label = "Texture Properties"
    bl_idname = "GNO_PT_Panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "GNO Properties"
    
    
    @classmethod
    def poll(self, context):
        return context.area.ui_type == "ShaderNodeTree" and context.active_object.active_material.node_tree.nodes.active.type == "TEX_IMAGE"

    def draw(self,context):
        layout = self.layout
        properties = context.active_object.active_material.node_tree.nodes.active.gnoSettings
        layout.prop(properties, "texture_property")

class MaterialProperties(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    bl_idname = "MATERIAL_PT_gno"
    bl_label = "GNO Material Properties"

    @classmethod
    def poll(cls, context):
        return context.active_object.type == 'MESH' and context.active_object.active_material is not None

    def draw(self, context):
        layout = self.layout
        properties = context.active_object.active_material.gnoSettings

        row = layout.row()
        row.alignment = "LEFT"
        row.label(text="Disable backface culling")
        row.prop(properties, "disable_backface_culling", text="")

        row = layout.row()
        row.alignment = "LEFT"
        row.label(text="Always on top")
        row.prop(properties, "always_on_top", text="")

        row = layout.row()
        row.alignment = "LEFT"
        row.label(text="Fullbright")
        row.prop(properties, "fullbright", text="")

class MeshProperties(bpy.types.Panel):
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"

    bl_idname = "DATA_PT_gno"
    bl_label = "GNO Mesh Properties"

    @classmethod
    def poll(cls, context):
        return context.active_object.type == 'MESH'

    def draw(self, context):
        self.layout.operator("vertex_groups.gno")

def menu_export_func(self, context):
    self.layout.operator(ExportGNO.bl_idname, text="Sonic Riders GNO Model (.gno)")

classes = (
    ExportGNO,
    GnoMaterialSettings,
    MaterialProperties,
    GnoNodePanel,
    GnoTextureSettings,
    GnoVertexGroups,
    MeshProperties,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_export.append(menu_export_func)
    bpy.types.Material.gnoSettings = bpy.props.PointerProperty(type=GnoMaterialSettings)
    bpy.types.ShaderNodeTexImage.gnoSettings = bpy.props.PointerProperty(type=GnoTextureSettings)

def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_export_func)
    
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
if __name__ == "__main__":
    register()