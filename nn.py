import bpy
import mathutils
import numpy as np
import itertools
import os
import struct
from . import rigLUT
from . import nn_model as nnModel
import pathlib

class Vector:
    position: tuple

    def __init__(self, position:tuple):
        self.position = position[:3]

    def write(self, file:nnModel.File):
        for p in self.position:
            file.write_float(p)

def calculate_bounding_box(o:bpy.types.Mesh):
    """Calculates the bounding box center and scale of a single mesh"""
    local_bbox_center = 0.125 * sum((mathutils.Vector(b) for b in o.bound_box), mathutils.Vector())

    cx = local_bbox_center[0]
    cy = local_bbox_center[1]
    cz = local_bbox_center[2]

    distance = 0
    for v in o.data.vertices:
        tDist = mathutils.Vector((cx - v.co.x,  cy - v.co.y, cz - v.co.z)).length
        if tDist > distance:
            distance = tDist

    return local_bbox_center, distance

def calculate_all_meshes_bounding_box():
    """Calculates the bounding box center and scale of all meshes"""
    # get the local coordinates of all object bounding box corners    
    coords = np.vstack(
        tuple(np.array(o.bound_box)
            for o in  
                bpy.context.scene.objects
                if o.type == 'MESH'
                )
            )
            

    # bottom front left (all the mins)
    bfl = coords.min(axis=0)
    # top back right
    tbr = coords.max(axis=0)
    G  = np.array((bfl, tbr)).T
    # bound box coords ie the 8 combinations of bfl tbr.
    bbc = [i for i in itertools.product(*G)]

    local_bbox = sum((mathutils.Vector(b) for b in bbc), mathutils.Vector()) / 8
    cx = local_bbox[0]
    cy = local_bbox[1]
    cz = local_bbox[2]

    allobj = [o for o in bpy.context.scene.objects if o.type == "MESH"]

    distance = 0
    for o in allobj:
        for v in o.data.vertices:
            tDist = mathutils.Vector((cx - v.co.x,  cy - v.co.y, cz - v.co.z)).length
            if tDist > distance:
                distance = tDist
                
    return local_bbox, distance

def read_original_model(file: nnModel.File, raw_bone_data: bool):
    """Gets a pre-existing rig's data, either from another NN model or from an already exported rig"""
    if raw_bone_data:
        original_bone_data = file.read()
    else:
        start_offset = 0x20
        file.seek(0x8)
        NGOB_header_index = file.read_int()
        file.seek(0)
        file.change_endianness('<')
        for _ in range(NGOB_header_index):
            file.fileobject.seek(4, 1)
            file.fileobject.seek(file.read_int(), 1)
        file.change_endianness('>')

        file.fileobject.seek(8, 1)
        object_data_offset = file.read_int()
        file.seek(object_data_offset + start_offset)
        file.fileobject.seek(0x28, 1)
        bone_count = file.read_int()
        file.fileobject.seek(4, 1)
        file.seek(file.read_int() + start_offset)

        original_bone_data = file.read(bone_count * 0x80)

    return original_bone_data

def write_new_gno_file(output_file: nnModel.File, **keywords):
    """Main function for exporting a model file"""
    def write_vertex_struct(file:nnModel.File, info:nnModel.VertexSetInfo, gno:nnModel.GNO):
        """Writes the struct that contains the info of a vertex set to file"""
        format = '>2h'
        if info.vertices_offset:
            file.write(struct.pack(format, 0x1, info.vertices_count))
            file.write_int_NOF0(info.vertices_offset, gno)
        else:
            file.write(struct.pack('8x'))
        
        if info.normals_offset:
            file.write(struct.pack(format, 0x3, info.normals_count))
            file.write_int_NOF0(info.normals_offset, gno)
        else:
            file.write(struct.pack('8x'))

        file.write(struct.pack('8x'))

        if info.uvs_offset:
            file.write(struct.pack(format, 0x2, info.uvs_count))
            file.write_int_NOF0(info.uvs_offset, gno)
        else:
            file.write(struct.pack('8x'))
        
        file.write(struct.pack('8x'))

        if info.weights_offset:
            file.write(struct.pack(format, 0x1, info.weights_count))
            file.write_int_NOF0(info.weights_offset, gno)
        else:
            file.write(struct.pack('8x'))

        file.write(struct.pack('8x'))

    def get_mesh_data(ob:bpy.types.Object, vertex_set, face_index, LUTkey, is_weighted = False):
        """Gets all the necessary data of a mesh"""
        LUT = rigLUT.retrieve_bone_LUT(LUTkey)
        bone_index, bone_name = nnModel.get_mesh_bone(ob)
        bone_group = nnModel.get_bone_group(ob, bone_name, is_weighted)
        if bone_group not in LUT:
            print("Index {} bone not found in LUT.".format(bone_group))
            bone_visibility = 0x46 # default to visible always
        else:
            bone_visibility = LUT[bone_group]
        firstmat = nnModel.get_mesh_material(ob)
        mat_index = nnModel.get_material_index(materials, firstmat)
        bounds_position, bounds_scale = calculate_bounding_box(ob)
        bounds = nnModel.Bounds(bounds_position, bounds_scale)

        mesh = nnModel.Mesh(ob, bounds, bone_visibility, bone_group, mat_index, vertex_set, face_index)
        return mesh

    def calculate_NGTL_header_size(current_size, texture_names):
        """Calculates the texture list header size"""
        string_table_size = 0
        for name in texture_names:
            string_table_size += len(name) + 1 # +1 for string eliminator byte
        
        final_size = current_size + string_table_size + 0x8
        return (final_size + 31) & 0xFFFFFFE0 # align 32 bit
    
    def write_NGTL(file:nnModel.File, texture_names, texture_name_offsets, gno:nnModel.GNO):
        """Formats and writes the texture list to file"""
        for offset in texture_name_offsets:
            file.write(struct.pack('>4x'))
            file.write_int_NOF0(offset, gno)
            file.write(struct.pack('>I8x', 0x00050001))
        
        file.write_int(len(texture_names))
        file.write_int_NOF0(0x10, gno)

        for name in texture_names:
            file.write(struct.pack('>' + str(len(name) + 1) + 's', bytes(name, 'ascii')))

        file.write_32bit_aligned()

    def generate_dummy_NGOB_header():
        """Generates a "padding" object header, it is updated after the fact"""
        return struct.pack('>4s12x', bytes('NGOB', 'ascii'))

    def write_NOF0_header(file:nnModel.File, gno:nnModel.GNO):
        """Writes out every offset in the offset list to file"""
        file.write_32bit_aligned()
        offset_count = len(gno.NOF0_offsets)
        start_offset = file.tell() + 0x10
        estimated_size = start_offset + len(gno.NOF0_offsets) * 4
        estimated_size = (estimated_size + 0x1F) & 0xFFFFFFE0 # 32 bit align
        final_size = estimated_size - start_offset + 0x8
        header = struct.pack('<4sI', bytes('NOF0', 'ascii'), final_size)
        header += struct.pack('>I4x', offset_count)

        file.write(header)
        for offset in gno.NOF0_offsets:
            file.write_int(offset)
        
    # instantiate main class
    gno = nnModel.GNO()

    weighted_mesh_names, weighted_vertices_weights, weighted_vertices_bones = nnModel.get_weight_painted_meshes()

    # use a different rig if needed
    if keywords["original_model_bool"]:
        path = "{}\\{}".format(os.path.dirname(keywords["filepath"]), keywords["original_model"])
        with nnModel.File(path, "rb") as extbonefile:
            original_bone_data = read_original_model(extbonefile, keywords["raw_bone_data"])
    else:
        rigfile = keywords["rig_type"] + ".bin"
        path = str(pathlib.Path(__file__).parent.absolute()) + "\\rigs\\{}".format(rigfile)
        extbonefile = open(path, "rb")
        original_bone_data = extbonefile.read()
        extbonefile.close()
    
    # categorize all meshes
    for m in bpy.context.scene.objects:
        if not m.type == 'MESH':
            continue
        nnModel.triangulateMesh(m.data)
        is_weight_painted = False

        if not m.data.uv_layers: # no UVs
            gno.vertex_set_2_meshes.append(m)
        else:
            for mesh in weighted_mesh_names:
                if m.name == mesh:
                    is_weight_painted = True
            
            if is_weight_painted:
                gno.vertex_set_3_meshes.append(m)
            else:
                gno.vertex_set_1_meshes.append(m)

    gno.vertex_set_1_uv_count = [0] * len(gno.vertex_set_1_meshes)
    gno.vertex_set_3_uv_count = [0] * len(gno.vertex_set_3_meshes)
    

    # NGTL (texture list header)

    global materials
    materials, texture_names = nnModel.get_all_materials()
    texture_count = len(texture_names)

    offset_to_texture_count_and_offsets = texture_count * 0x14 + 0x10
    header_size = calculate_NGTL_header_size(offset_to_texture_count_and_offsets, texture_names)
    header = struct.pack('<4sI', bytes('NGTL', 'ascii'), header_size - 0x8)
    header += struct.pack('>I4x', offset_to_texture_count_and_offsets)

    string_table_offset = offset_to_texture_count_and_offsets + 0x8
    string_table_offsets = []
    for name in texture_names:
        string_table_offsets.append(string_table_offset)
        string_table_offset += len(name) + 1 # string eliminator byte
    
    if keywords["include_texture_list"]:
        output_file.write(header)
        write_NGTL(output_file, texture_names, string_table_offsets, gno)

    NGOB_header_offset = output_file.tell()
    output_file.write(generate_dummy_NGOB_header())

    
    # NGOB (object data header)

    bone_offset = output_file.tell()

    output_file.write(original_bone_data)

    nnModel.write_materials(output_file, materials, gno)

    # write out all of the vertex sets' data
    if gno.vertex_set_1_meshes:
        vertexset1_vertex_count = 0
        vertexset1_normal_count = 0
        vertexset1_uv_count = 0

        vertex_set_with_uvs_normals_offset = output_file.tell()
        for m in gno.vertex_set_1_meshes:
            vertexset1_vertex_count += nnModel.write_vertices(output_file, m.data)
        output_file.write_8bit_aligned()

        normal_set_with_uvs_normals_offset = output_file.tell()
        vertexset1_normal_indices = []
        for m in gno.vertex_set_1_meshes:
            normals, normal_indices = nnModel.getNormalData(m.data)
            vertexset1_normal_indices.append(normal_indices)
            vertexset1_normal_count += nnModel.write_normals(output_file, normals)
        output_file.write_8bit_aligned()

        uv_set_with_uvs_normals_offset = output_file.tell()
        for uv_i, m in enumerate(gno.vertex_set_1_meshes):
            all_uvs, uv_indices, uv_count = nnModel.get_mesh_uvs_with_indices(m.data)
            gno.vertex_set_1_uv_indices.append(uv_indices)
            vertexset1_uv_count += nnModel.write_uvs(output_file, all_uvs)
        output_file.write_8bit_aligned()
        
    if gno.vertex_set_2_meshes:
        vertexset2_vertex_count = 0
        vertexset2_normal_count = 0

        vertex_set_with_normals_offset = output_file.tell()
        for m in gno.vertex_set_2_meshes:
            vertexset2_vertex_count += nnModel.write_vertices(output_file, m.data)
        output_file.write_8bit_aligned()

        normal_set_with_normals_offset = output_file.tell()
        vertexset2_normal_indices = []
        for m in gno.vertex_set_2_meshes:
            normals, normal_indices = nnModel.getNormalData(m.data)
            vertexset2_normal_indices.append(normal_indices)
            vertexset2_normal_count += nnModel.write_normals(output_file, normals)
        output_file.write_8bit_aligned()

    if gno.vertex_set_3_meshes:
        vertexset3_vertex_count = 0
        vertexset3_normal_count = 0
        vertexset3_uv_count = 0

        vertex_set_with_uvs_normals_weights_offset = output_file.tell()
        for m in gno.vertex_set_3_meshes:
            vertexset3_vertex_count += nnModel.write_vertices(output_file, m.data)
        output_file.write_8bit_aligned()
        
        normal_set_with_uvs_normals_weights_offset = output_file.tell()
        for m in gno.vertex_set_3_meshes:
            normals = nnModel.getNormalData_weightpaint(m.data)
            vertexset3_normal_count += nnModel.write_normals(output_file, normals)
        output_file.write_8bit_aligned()
        
        uv_set_with_uvs_normals_weights_offset = output_file.tell()
        for uv_i, m in enumerate(gno.vertex_set_3_meshes):
            all_uvs, uv_indices, uv_count = nnModel.get_mesh_uvs_with_indices(m.data)
            gno.vertex_set_3_uv_indices.append(uv_indices)
            vertexset3_uv_count += nnModel.write_uvs(output_file, all_uvs)
        output_file.write_8bit_aligned()
        
        weighted_bones_vertices_offset = output_file.tell()
        vertexset3_weight_count = vertexset3_vertex_count
        nnModel.write_vertex_weights(output_file, weighted_vertices_weights, weighted_vertices_bones)

    # write out all of the vertex sets' info structs
    if gno.vertex_set_1_meshes:
        vertex_set_1_offset = output_file.tell()

        vertexset1_info = nnModel.VertexSetInfo( \
        vertex_set_1_offset, \
        vertex_set_with_uvs_normals_offset, vertexset1_vertex_count, \
        normal_set_with_uvs_normals_offset, vertexset1_normal_count, \
        uv_set_with_uvs_normals_offset, vertexset1_uv_count)

        write_vertex_struct(output_file, vertexset1_info, gno)

    if gno.vertex_set_2_meshes:
        vertex_set_2_offset = output_file.tell()

        vertexset2_info = nnModel.VertexSetInfo( \
        vertex_set_2_offset, \
        vertex_set_with_normals_offset, vertexset2_vertex_count, \
        normal_set_with_normals_offset, vertexset2_normal_count)

        write_vertex_struct(output_file, vertexset2_info, gno)

    if gno.vertex_set_3_meshes:
        vertex_set_3_offset = output_file.tell()

        vertexset3_info = nnModel.VertexSetInfo( \
        vertex_set_3_offset, \
        vertex_set_with_uvs_normals_weights_offset, vertexset3_vertex_count, \
        normal_set_with_uvs_normals_weights_offset, vertexset3_normal_count, \
        uv_set_with_uvs_normals_weights_offset, vertexset3_uv_count, \
        weighted_bones_vertices_offset, vertexset3_weight_count)

        write_vertex_struct(output_file, vertexset3_info, gno)

    offset_to_vertex_sets_offset = output_file.tell()

    if gno.vertex_set_1_meshes:
        output_file.write_int(0x1)
        output_file.write_int_NOF0(vertexset1_info.info_offset, gno)

    if gno.vertex_set_2_meshes:
        output_file.write_int(0x1)
        output_file.write_int_NOF0(vertexset2_info.info_offset, gno)

    if gno.vertex_set_3_meshes:
        output_file.write_int(0x1)
        output_file.write_int_NOF0(vertexset3_info.info_offset, gno)


    # write out the face data of all the meshes
    facedata_list = []

    if gno.vertex_set_1_meshes:
        vertexset1_faceoffsets = nnModel.write_mesh_faces(output_file, 0x00C9002A, \
            gno.vertex_set_1_meshes, gno.vertex_set_1_uv_indices, weightpaint_normals=False)
        facedata_list.append(vertexset1_faceoffsets)
    if gno.vertex_set_2_meshes:
        vertexset2_faceoffsets = nnModel.write_mesh_faces(output_file, 0x0009000A, gno.vertex_set_2_meshes, \
            weightpaint_normals=False)
        facedata_list.append(vertexset2_faceoffsets)
    if gno.vertex_set_3_meshes:
        vertexset3_faceoffsets = nnModel.write_mesh_faces(output_file, 0x1085000A, \
            gno.vertex_set_3_meshes, gno.vertex_set_3_uv_indices, weightpaint_normals=True)
        facedata_list.append(vertexset3_faceoffsets)

    # write out face data info structs
    face_info_struct_offsets = []
    for data in facedata_list:
        for face in data:
            face_info_struct_offsets.append(output_file.tell())
            output_file.write_int(face.flags)
            output_file.write_int_NOF0(face.offset, gno)
            output_file.write_int(face.size)
            output_file.write_int(0)
    
    face_info_offset = output_file.tell()
    for offset in face_info_struct_offsets:
        output_file.write_int(0x4)
        output_file.write_int_NOF0(offset, gno)

    meshset_info = []
    faceindex = 0
    vertex_index = 0

    # write out all the mesh set data
    if gno.vertex_set_1_meshes:
        v1_meshes_start = output_file.tell()
        for me in gno.vertex_set_1_meshes:
            mesh_data = get_mesh_data(me, vertex_index, faceindex, keywords['rig_type'])
            for f in mesh_data.bounds.position:
                output_file.write_float(f)
            output_file.write_float(mesh_data.bounds.scale)
            output_file.write_int(mesh_data.bone)
            output_file.write_int(mesh_data.bone_group)
            output_file.write_int(mesh_data.material)
            output_file.write_int(mesh_data.vertex_set)
            output_file.write_int(mesh_data.face)
            faceindex += 1
        vertex_index += 1

    if gno.vertex_set_2_meshes:
        v2_meshes_start = output_file.tell()
        for me in gno.vertex_set_2_meshes:
            mesh_data = get_mesh_data(me, vertex_index, faceindex, keywords['rig_type'])
            for f in mesh_data.bounds.position:
                output_file.write_float(f)
            output_file.write_float(mesh_data.bounds.scale)
            output_file.write_int(mesh_data.bone)
            output_file.write_int(mesh_data.bone_group)
            output_file.write_int(mesh_data.material)
            output_file.write_int(mesh_data.vertex_set)
            output_file.write_int(mesh_data.face)
            faceindex += 1
        vertex_index += 1

    if gno.vertex_set_3_meshes:
        v3_meshes_start = output_file.tell()
        for me in gno.vertex_set_3_meshes:
            mesh_data = get_mesh_data(me, vertex_index, faceindex, keywords['rig_type'], True)
            for f in mesh_data.bounds.position:
                output_file.write_float(f)
            output_file.write_float(mesh_data.bounds.scale)
            output_file.write_int(mesh_data.bone)
            output_file.write_signed_int(mesh_data.bone_group)
            output_file.write_int(mesh_data.material)
            output_file.write_int(mesh_data.vertex_set)
            output_file.write_int(mesh_data.face)
            faceindex += 1
        vertex_index += 1

    # write out all the mesh set info structs, 
    # they have to be written out in this specific order for some reason lmao
    if gno.vertex_set_1_meshes:
        meshset_info.append(nnModel.MeshSetInfo(v1_meshes_start, gno.vertex_set_1_flags, len(gno.vertex_set_1_meshes)))

    if gno.vertex_set_3_meshes:
        meshset_info.append(nnModel.MeshSetInfo(v3_meshes_start, gno.vertex_set_3_flags, len(gno.vertex_set_3_meshes)))

    if gno.vertex_set_2_meshes:
        meshset_info.append(nnModel.MeshSetInfo(v2_meshes_start, gno.vertex_set_2_flags, len(gno.vertex_set_2_meshes)))


    mesh_set_info_offset = output_file.tell()
    for info in meshset_info:
        output_file.write_int(info.flags)
        output_file.write_int(info.count)
        output_file.write_int_NOF0(info.start_offset, gno)
        output_file.write(struct.pack('8x'))

    # write out all of the object data infos
    main_object_data_offset = output_file.tell()

    model_bounds_center, model_bounds_distance = calculate_all_meshes_bounding_box()
    model_bounds = nnModel.Bounds(model_bounds_center, model_bounds_distance)
    for f in model_bounds.position:
        output_file.write_float(f)
    output_file.write_float(model_bounds.scale)

    output_file.write_int(len(materials))
    output_file.write_int_NOF0(nnModel.material_structs_offset, gno)

    output_file.write_int(vertex_index) # amount of vertex sets
    output_file.write_int_NOF0(offset_to_vertex_sets_offset, gno)

    output_file.write_int(len(face_info_struct_offsets))
    output_file.write_int_NOF0(face_info_offset, gno)

    output_file.write_int(len(original_bone_data) // 0x80)

    output_file.write_int(0xC)
    output_file.write_int_NOF0(bone_offset, gno)

    # subtracted 1 is to not count for the null bone group
    if gno.vertex_set_1_meshes:
        bone_group_amount = nnModel.get_bone_group_amount(gno.vertex_set_1_meshes[0])-1 
    elif gno.vertex_set_2_meshes:
        bone_group_amount = nnModel.get_bone_group_amount(gno.vertex_set_2_meshes[0])-1
    elif gno.vertex_set_3_meshes:
        bone_group_amount = nnModel.get_bone_group_amount(gno.vertex_set_3_meshes[0])-1

    output_file.write_int(bone_group_amount) 

    output_file.write_int(len(meshset_info))
    output_file.write_int_NOF0(mesh_set_info_offset, gno)

    output_file.write_int(0x4)

    output_file.write_32bit_aligned()
    offset_to_NOF0 = output_file.tell()
    write_NOF0_header(output_file, gno)
    nnModel.write_NFN0_header(output_file)
    nnModel.write_NEND_header(output_file)

    # return all the required info so the exported file can be updated with it
    NGOB_size = offset_to_NOF0 - NGOB_header_offset
    return NGOB_header_offset, offset_to_NOF0, NGOB_size, main_object_data_offset



def write_new_spline_file(file:nnModel.File):
    """Main function for exporting a splines file"""
    default_length = [0.130168]
    spline_count = 0
    spline_data = {}
    for m in bpy.context.selected_objects:
        if not m.type == 'MESH':
            continue
        spline_info = {}
        spline_info["vertex_count"] = len(m.data.vertices)
        spline_info["vertices"] = [v.co for v in m.data.vertices]
        spline_info["character_orientations"] = [Vector((0, 1, 0)) for _ in range(len(m.data.vertices))] # default
        spline_info["bounding_box_position"], spline_info["bounding_box_scale"] = calculate_bounding_box(m)
        
        hitbox = []
        vertex_range = range(len(m.data.vertices))
        for vindex in vertex_range:
            if vindex == vertex_range[-1]:
                break
            curr_hitbox = []
            vertex = spline_info["vertices"][vindex]
            next_vertex = spline_info["vertices"][vindex+1]
            curr_hitbox.append(vertex)
            curr_hitbox.append(next_vertex)
            curr_hitbox.append(default_length)
            hitbox.append(curr_hitbox)
        
        spline_info["hitbox"] = hitbox
        spline_data[spline_count] = spline_info
        spline_count += 1

    
    header = struct.pack('>2B2s4x', 0x1, 0x2, bytes('GC', 'ascii'))
    file.write(header)
    file.write_int(spline_count)
    file.write(struct.pack('>{}x'.format(4*spline_count))) # will write the offsets later

    spline_info_offsets = {}
    spline_data_offsets = {}
    
    for key in spline_data:
        spline_info_offsets[key] = file.tell()
        spline_info = spline_data[key]
        data_offsets = [] # in order of struct

        file.write(struct.pack('>12x')) # will write the offsets later
        for p in spline_info["bounding_box_position"]:
            file.write_float(p)
        
        file.write_float(spline_info["bounding_box_scale"])
        file.write_short(spline_info["vertex_count"])
        file.write(struct.pack('>18x'))

        data_offsets.append(file.tell()) # hitbox
        for hbox in spline_info["hitbox"]:
            for data in hbox:
                for p in data:
                    file.write_float(p)

        data_offsets.append(file.tell()) # vertices
        for vert in spline_info["vertices"]:
            for p in vert:
                file.write_float(p)

        data_offsets.append(file.tell()) # character orientation
        for orientation in spline_info["character_orientations"]:
            orientation.write(file)

        spline_data_offsets[key] = data_offsets

    file.write_32bit_aligned()
    return spline_info_offsets, spline_data_offsets