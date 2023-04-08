bl_info = {
    "name": "Sega GNO Model Exporter",
    "description": "Exports a Sega GNO model for the GameCube version of Sonic Riders.",
    "author": "Exortile",
    "version": (1, 5),
    "blender": (3, 1, 0),
    "location": "File > Export",
    "warning": "",
    "support": "COMMUNITY",
    "category": "Import-Export",
}

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import IntProperty, BoolProperty, StringProperty, EnumProperty
from . import nn
from . import nn_general as nnGeneral
from . import nn_model as nnModel
import struct, os

export_types = (
    ("model", "Character Model", "Exports a character GNO model"),
    ("splines", "Splines", "Exports splines (GameCube version)")
)

rig_types = (
    ("no_rig", "No Rig", "Exported model file doesn't contain a rig. All bone visibility values will default to 0. Use this in tandem with external bone data (which means the exported model may require manual editing)"),
    ("board_only", "Board", "Exported model file doesn't contain a rig. All bone visibility values default to that of a extreme gear. No rig needs to be present in the Blender file to export this rig type"),
    ("character", "Character", "Character rig export. Make sure you use this rig type on characters as it guarantees full compatibility in-game"),
    ("character_eggman", "Character (Eggman Only)", "Character rig export, although this one's for Eggman only, as his rig is special"),
    ("general", "General", "General rig export. Doesn't apply any fancy exceptions that it normally does on character exports. Use this on any model that isn't a character model"),
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

    if NGOB_header_offset is None:
        return False
    
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

    return True

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

    return True

def write_file(context, **keywords):
    success = False
    if keywords["format"] == "model":
        success = write_model(context, **keywords)
    elif keywords["format"] == "splines":
        success = write_splines(context, **keywords)
    
    if success:
        filename = os.path.basename(keywords["filepath"])
        nnGeneral.message_box("File {} exported successfully!".format(filename), "Success!")

        return {'FINISHED'}
    else:
        return {'CANCELLED'}
    
def rename_mesh_groups(context, all_meshes: bool):
    """
    Renames all of the vertex groups of a mesh with the given prefix.
    """
    prefix = context.scene.gnoVGroupHelperSettings.prefix
    mesh_list = [obj for obj in context.scene.objects if obj.type == "MESH"] if all_meshes \
        else [context.active_object]

    for obj in mesh_list:
        for vgroup in obj.vertex_groups:
            prefix_end = vgroup.name.index("_")
            newname = prefix + vgroup.name[prefix_end:]
            vgroup.name = newname

def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start

def rename_remove_leading_zeroes(context, all_meshes: bool):
    """
    Renames all of the vertex groups of a mesh in a way that removes leading zeroes from the bone number
    """

    mesh_list = [obj for obj in context.scene.objects if obj.type == "MESH"] if all_meshes \
        else [context.active_object]

    for mesh in mesh_list:
        for vgroup in mesh.vertex_groups:
            number_start = find_nth(vgroup.name, "_", 2)
            if number_start == -1:
                continue
            number_start += 1
            number = vgroup.name[number_start:].lstrip("0")
            newname = vgroup.name[:number_start] + number
            vgroup.name = newname

def rename_add_leading_zeroes(context, all_meshes: bool):
    """
    Renames all of the vertex groups of a mesh in a way that adds leading zeroes to the bone number
    """
    
    mesh_list = [obj for obj in context.scene.objects if obj.type == "MESH"] if all_meshes \
        else [context.active_object]
    
    for mesh in mesh_list:
        for vgroup in mesh.vertex_groups:
            number_start = find_nth(vgroup.name, "_", 2)
            if number_start == -1:
                continue
            number_start += 1
            number = vgroup.name[number_start:].zfill(4)
            newname = vgroup.name[:number_start] + number
            vgroup.name = newname

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
        name = "Model Type",
        description = "Model type to use upon exporting",
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
        nnModel.create_vertex_groups(mesh)
        
        return {"FINISHED"}
    
class GnoVertexGroupSettings(bpy.types.PropertyGroup):
    prefix: StringProperty(
        name = "Prefix",
        description = "Prefix to be used to rename all of the vertex group names with",
        default = "snc07"
    )

class RenameCurrentVertexGroups(bpy.types.Operator):
    bl_idname = "rename_current_vertex_groups.gno"
    bl_label = "Rename Current Mesh Vertex Groups (Prefix)"
    bl_description = "Renames all vertex groups on this mesh with the given prefix (replaces the prefix before the underscore on the group names)"


    def execute(self, context):
        rename_mesh_groups(context, False)
        return {'FINISHED'}

class RenameAllVertexGroups(bpy.types.Operator):
    bl_idname = "rename_all_vertex_groups.gno"
    bl_label = "Rename All Vertex Groups (Prefix)"
    bl_description = "Renames all vertex groups on all meshes in the scene with the given prefix (replaces the prefix before the underscore on the group names)"

    def execute(self, context):
        rename_mesh_groups(context, True)
        return {'FINISHED'}
    
class RenameAllAddLeadingZeroes(bpy.types.Operator):
    bl_idname = "rename_all_add_leading.gno"
    bl_label = "Rename All Vertex Groups (Add Leading Zeroes)"
    bl_description = "Renames all vertex groups on all meshes in the scene where the bone number at the end of the group name has leading zeroes added"

    def execute(self, context):
        rename_add_leading_zeroes(context, True)
        return {'FINISHED'}
    
class RenameCurrentAddLeadingZeroes(bpy.types.Operator):
    bl_idname = "rename_current_add_leading.gno"
    bl_label = "Rename Current Mesh Vertex Groups (Add Leading Zeroes)"
    bl_description = "Renames all vertex groups on the current mesh where the bone number at the end of the group name has leading zeroes added"

    def execute(self, context):
        rename_add_leading_zeroes(context, False)
        return {'FINISHED'}
    
class RenameAllRemoveLeadingZeroes(bpy.types.Operator):
    bl_idname = "rename_all_remove_leading.gno"
    bl_label = "Rename All Vertex Groups (Remove Leading Zeroes)"
    bl_description = "Renames all vertex groups on all meshes in the scene where the bone number at the end of the group name has leading zeroes removed"

    def execute(self, context):
        rename_remove_leading_zeroes(context, True)
        return {'FINISHED'}
    
class RenameCurrentRemoveLeadingZeroes(bpy.types.Operator):
    bl_idname = "rename_current_remove_leading.gno"
    bl_label = "Rename Current Mesh Vertex Groups (Remove Leading Zeroes)"
    bl_description = "Renames all vertex groups on the current mesh where the bone number at the end of the group name has leading zeroes removed"

    def execute(self, context):
        rename_remove_leading_zeroes(context, False)
        return {'FINISHED'}

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

class GnoMeshSettings(bpy.types.PropertyGroup):
    use_custom_bone_visibility: BoolProperty(
        name = "Use custom bone visibility",
        description = "Enables the use of custom bone visibility integers on this mesh",
        default = False
    )

    bone_visibility: IntProperty(
        name = "Custom bone visibility",
        description = "Sets a custom bone visibility integer for a mesh",
        default = 0,
        min = 0
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
        layout = self.layout
        properties = context.active_object.data.gnoSettings
        vgroup_properties = context.scene.gnoVGroupHelperSettings

        layout.operator("vertex_groups.gno")

        row = layout.row()
        row.alignment = "LEFT"
        row.label(text="Use custom bone visibility")
        row.prop(properties, "use_custom_bone_visibility", text="")

        row = layout.row()
        row.alignment = "LEFT"
        row.label(text="Custom bone visibility")
        row.prop(properties, "bone_visibility", text="")
        row.enabled = properties.use_custom_bone_visibility

        box = layout.box()
        box.alignment = "LEFT"
        box.prop(vgroup_properties, "prefix")
        box.operator("rename_current_vertex_groups.gno")
        box.operator("rename_all_vertex_groups.gno")

        box = layout.box()
        box.alignment = "LEFT"
        box.operator("rename_current_add_leading.gno")
        box.operator("rename_all_add_leading.gno")
        box.operator("rename_current_remove_leading.gno")
        box.operator("rename_all_remove_leading.gno")

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
    GnoMeshSettings,
    GnoVertexGroupSettings,
    RenameCurrentVertexGroups,
    RenameAllVertexGroups,
    RenameCurrentAddLeadingZeroes,
    RenameAllAddLeadingZeroes,
    RenameCurrentRemoveLeadingZeroes,
    RenameAllRemoveLeadingZeroes
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_export.append(menu_export_func)
    bpy.types.Material.gnoSettings = bpy.props.PointerProperty(type=GnoMaterialSettings)
    bpy.types.ShaderNodeTexImage.gnoSettings = bpy.props.PointerProperty(type=GnoTextureSettings)
    bpy.types.Mesh.gnoSettings = bpy.props.PointerProperty(type=GnoMeshSettings)
    bpy.types.Scene.gnoVGroupHelperSettings = bpy.props.PointerProperty(type=GnoVertexGroupSettings)

def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_export_func)
    
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
if __name__ == "__main__":
    register()