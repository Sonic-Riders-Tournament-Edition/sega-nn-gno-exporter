from dataclasses import dataclass
import struct
import bpy
import mathutils
import os

@dataclass
class Bounds:
    position: tuple
    scale: float

@dataclass
class Face:
    vertex: list
    normal: list
    texcoord: list

@dataclass
class ObjInfo:
    vertex_count: int
    uv_count: int
    normal_count: int

@dataclass
class VertexSetInfo:
    info_offset: int
    vertices_offset: int
    vertices_count: int
    normals_offset: int = 0
    normals_count: int = 0
    uvs_offset: int = 0
    uvs_count: int = 0
    weights_offset: int = 0
    weights_count: int = 0

@dataclass
class Mesh:
    blender_object: bpy.types.Object # will have data in here
    bounds: Bounds
    bone: int # is also bone visibility
    bone_group: int
    material: int
    vertex_set: int
    face: int

@dataclass
class Material:
    blender_object: bpy.types.Material
    name: str
    color: list[float]
    alpha: float
    texture_count: int
    texture_ids: list[int]
    texture_flags: list[str]

@dataclass
class MeshSetInfo:
    start_offset: int
    flags: int
    count: int

@dataclass
class FaceData:
    flags: int
    offset: int
    length: int

@dataclass
class FaceInfo:
    flags = 0x4
    offset: int

class GNO:
    """Main class that will hold all the necessary info for the file"""
    NOF0_offsets: list # offset table

    all_meshes: list 

    vertex_set_1: VertexSetInfo
    vertex_set_1_meshes: list
    vertex_set_1_uv_indices: list
    vertex_set_1_uv_count: list
    vertex_set_1_flags = 0x101 # set that has vertices, normals and UVs
    
    vertex_set_2: VertexSetInfo
    vertex_set_2_meshes: list
    vertex_set_2_flags = 0x102 # set that has vertices and normals

    vertex_set_3: VertexSetInfo
    vertex_set_3_meshes: list
    vertex_set_3_uv_indices: list
    vertex_set_3_uv_count: list
    vertex_set_3_flags = 0x201 # set that has vertices, normals, UVs and weight painted vertices

    def __init__(self):
        self.NOF0_offsets = []
        self.all_meshes = []

        self.vertex_set_1 = None
        self.vertex_set_1_meshes = []
        self.vertex_set_1_uv_indices = []
        self.vertex_set_1_uv_count = []
        self.vertex_set_1_flags = 0x101
        
        self.vertex_set_2 = None
        self.vertex_set_2_meshes = []
        self.vertex_set_2_flags = 0x102

        self.vertex_set_3 = None
        self.vertex_set_3_meshes = []
        self.vertex_set_3_uv_indices = []
        self.vertex_set_3_uv_count = []
        self.vertex_set_3_flags = 0x201


class MeshData:
    vertices: list
    texcoords: list
    normals: list
    faces: list
    face_flag: int

    @dataclass
    class Face:
        vertex: list # indices
        texcoord: list
        normal: list

class File:
    """Main file handling class"""
    def __init__(self, filepath, read_or_write, endianness = '>'):
        self.filepath = filepath
        self.read_or_write = read_or_write
        self.endian = endianness
        self.set_formats()

    def __enter__(self):
        self.fileobject = open(self.filepath, self.read_or_write)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.fileobject.close()
    
    def __del__(self):
        self.fileobject.close()

    def change_endianness(self, endianness):
        """Since the model format has a mix of both endians, this can be used"""
        self.endian = endianness
        self.set_formats()

    def get_filename(self):
        """Used for NFN0 header"""
        return os.path.basename(self.filepath)
    
    def set_formats(self):
        self.sb_format = self.endian + 'b'
        self.sh_format = self.endian + 'h'
        self.si_format = self.endian + 'i'
        self.f_format = self.endian + 'f'
        self.b_format = self.endian + 'B'
        self.h_format = self.endian + 'H'
        self.i_format = self.endian + 'I'

    def tell(self):
        return self.fileobject.tell()

    def seek(self, seek):
        self.fileobject.seek(seek)

    # Main read functions

    def read(self, size = None, offset = None):
        """
        Reads bytes from the file, either from current position or from a specified offset.
        """

        if offset:
            original_pos = self.tell()
            self.seek(offset)
            output = self.fileobject.read(size)
            self.seek(original_pos)
        else:
            if size:
                output = self.fileobject.read(size)
            else:
                output = self.fileobject.read()

        return output

    def read_signed_byte(self):
        return struct.unpack(self.sb_format, self.fileobject.read(1))[0]

    def read_signed_short(self):
        return struct.unpack(self.sh_format, self.fileobject.read(2))[0]

    def read_signed_int(self):
        return struct.unpack(self.si_format, self.fileobject.read(4))[0]

    def read_byte(self):
        return struct.unpack(self.b_format, self.fileobject.read(1))[0]

    def read_short(self):
        return struct.unpack(self.h_format, self.fileobject.read(2))[0]

    def read_int(self):
        return struct.unpack(self.i_format, self.fileobject.read(4))[0]
    
    def read_float(self):
        return struct.unpack(self.f_format, self.fileobject.read(4))[0]



    # Main write functions
    
    def write(self, bytes, offset = None):
        """
        Writes bytes to the file, either starting from current position or from a specified offset.
        """

        if offset:
            original_pos = self.fileobject.tell()
            self.fileobject.seek(offset)
            self.fileobject.write(bytes)
            self.fileobject.seek(original_pos)
        else:
            self.fileobject.write(bytes)

    def write_signed_byte(self, b):
        self.fileobject.write(struct.pack(self.sb_format, b))
    
    def write_signed_short(self, h):
        self.fileobject.write(struct.pack(self.sh_format, h))
    
    def write_signed_int(self, i):
        self.fileobject.write(struct.pack(self.si_format, i))
    
    def write_byte(self, b):
        self.fileobject.write(struct.pack(self.b_format, b))
    
    def write_short(self, h):
        self.fileobject.write(struct.pack(self.h_format, h))
    
    def write_int(self, i):
        self.fileobject.write(struct.pack(self.i_format, i))

    def write_int_NOF0(self, i, gno: GNO):
        """
        Stores a 32-bit integer and also appends the offset to it to the NOF0 offset table.
        """

        gno.NOF0_offsets.append(self.tell())
        self.fileobject.write(struct.pack(self.i_format, i))
        
    def write_float(self, f):
        self.fileobject.write(struct.pack(self.f_format, f))

    def write_short_list(self, l):
        self.fileobject.write(struct.pack('{}{}H'.format(self.endian, len(l)), *l))

    def write_8bit_aligned(self):
        """
        Writes padding up until the current address is at a 8-bit alignment.
        """

        while self.tell() & 0x3:
            self.fileobject.write(b'\x00')

    def write_32bit_aligned(self):
        """
        Writes padding up until the current address is at a 32-bit alignment.
        """

        while self.tell() & 0x1F:
            self.fileobject.write(b'\x00')

# this is not used
default_bounds = Bounds((1.19209e-07, 0.45939, 0), 0.947298)

def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n): 
        yield l[i:i + n]

def write_materials(file:File, materials:list[Material], gno:GNO):
    """Formats and writes a list of materials to the file"""
    format_string = '>I12f10I' # for the main body of the material
    texture_format_string = '>4If'
    global material_offsets
    material_offsets = []

    for mat in materials:
        matflags = 0
        if mat.blender_object.gnoSettings.disable_backface_culling:
            matflags |= 2
        if mat.blender_object.gnoSettings.always_on_top:
            matflags |= 0x10000
        if not mat.blender_object.gnoSettings.fullbright:
            matflags |= 0x1000000
        material_data = struct.pack(format_string, matflags, mat.color[0], mat.color[1], mat.color[2], \
        mat.alpha, mat.color[0], mat.color[1], mat.color[2], 0.9, 0.9, 0.9, 2.0, 0.299999982118607, \
        0x1, 0x4, 0x5, 0x5, 0x2, 0x0, 0x6, 0x7, 0x0, 0x0)

        if mat.texture_count > 0:
            texture_data_list = []
            for i, texture_id in enumerate(mat.texture_ids):
                flags = 0x400C0101
                if mat.texture_flags[i] == 'reflective':
                    flags = 0x400C2004
                elif mat.texture_flags[i] == 'emissive':
                    flags = 0x400C0104

                if mat.texture_flags[i] == 'none':
                    texture_data_list.insert(0, struct.pack(texture_format_string, flags, texture_id, \
                    0x80000000, 0x0, 1.0))
                else:
                    texture_data_list.append(struct.pack(texture_format_string, flags, texture_id, \
                    0x80000000, 0x0, 1.0))

            for data in texture_data_list:
                material_data += data

        material_offsets.append(file.tell())
        file.write(material_data)
    
    global material_structs_offset
    material_structs_offset = file.tell()
    for i, mat in enumerate(materials):
        texture_count_int = 1
        for count in range(mat.texture_count):
            texture_count_int += 1 << count + 1
        file.write(struct.pack('>2H', texture_count_int, 0xFFFF))
        file.write_int_NOF0(material_offsets[i], gno)

    file.write_8bit_aligned()

def write_vertices(file:File, mesh:bpy.types.Mesh):
    """Formats and writes a vertex set's vertices to the file"""
    for v in mesh.vertices:
        for p in v.co:
            file.write_float(p)
    
    return len(mesh.vertices)

def write_normals(file:File, normals:list):
    """Formats and writes a vertex set's normals to the file"""
    for n in normals:
        for p in n:
            point = int(round(p * 64))
            file.write_signed_byte(point)

    return len(normals)

def write_uvs(file:File, uvs:list):
    """Formats and writes a vertex set's UVs to the file"""
    for uv in uvs:
        u = round(uv[0] * 256)
        v = round(-(uv[1] - 1) * 256)
        file.write_signed_short(u)
        file.write_signed_short(v)
    
    return len(uvs)

def write_vertex_weights(file:File, weights:list, bones:list):
    """Formats and writes a vertex set's vertex weights to the file"""
    for w, b in zip(weights, bones):
        weight = int(round(w * 16384))
        for bone in b:
            file.write_byte(bone)
        file.write_signed_short(weight)

    file.write_8bit_aligned()

def write_mesh_faces(file:File, flags:int, meshes:list, meshes_uv_indices = False, weightpaint_normals = False):
    """Converts a list of meshes' faces into triangle strips (it's very unoptimized tho) and writes the data to the file"""
    @dataclass
    class FaceInfo:
        flags: int
        offset: int
        size: int

    @dataclass
    class IndexInfo:
        # info on how much indices need to be incremented
        vertex_increment: int
        normal_increment: int
        texcoord_increment: int

    def swap_f1_f2(face):
        face.vertex[1], face.normal[1], \
        face.vertex[0], face.normal[0] = \
        face.vertex[0], face.normal[0], \
        face.vertex[1], face.normal[1] # f2, f1, f3

        if face.texcoord:
            face.texcoord[1], face.texcoord[0] = face.texcoord[0], face.texcoord[1]

    def strip_faces(faces):

        last_face = faces[0]
        doesUVexist = False
        if last_face.texcoord:
            doesUVexist = True
        swap_f1_f2(last_face)

        face_sets = []
        current_face_set = []
        xor_bool = 0

        current_face_set.append(last_face)

        for x in range(len(faces)-1):
            current_face = faces[x+1]

            if xor_bool & 1:
                swap_f1_f2(current_face)
            
            if doesUVexist:
                if current_face.vertex[0] == last_face.vertex[1] and current_face.vertex[1] == last_face.vertex[2] \
                    and current_face.texcoord[0] == last_face.texcoord[1] and current_face.texcoord[1] == last_face.texcoord[2]:
                        current_face_set.append(current_face)
                else:
                    face_sets.append(current_face_set)
                    current_face_set = []
                    if not xor_bool & 1:
                        swap_f1_f2(current_face)
                    current_face_set.append(current_face)
                    xor_bool = 1 # this will get XORed to 0
            else:
                if current_face.vertex[0] == last_face.vertex[1] and current_face.vertex[1] == last_face.vertex[2]:
                    current_face_set.append(current_face)
                else:
                    face_sets.append(current_face_set)
                    current_face_set = []
                    if not xor_bool & 1:
                        swap_f1_f2(current_face)
                    current_face_set.append(current_face)
                    xor_bool = 1 # this will get XORed to 0
                
            last_face = current_face
            xor_bool ^= 1

        if current_face_set:
            face_sets.append(current_face_set)
        
        return face_sets

    def create_faces(vertices, normals=None, uvs=None, weightpaint_normals=False):
        div_verts = list(divide_chunks(vertices, 3))
        if normals:
            div_normals = list(divide_chunks(normals, 3))
        div_uvs = [[0, 0, 0]] * len(div_verts)
        if uvs:
            div_uvs = list(divide_chunks(uvs, 3))
        all_faces = []

        if weightpaint_normals:
            for vert, uv in zip(div_verts, div_uvs):
                if uvs:
                    all_faces.append(Face(vert, vert, uv))
                else:
                    all_faces.append(Face(vert, vert, []))
            return all_faces

        for vert, norm, uv in zip(div_verts, div_normals, div_uvs):
            if len(vert) < 3:
                continue
            if uvs:
                all_faces.append(Face(vert, norm, uv))
            else:
                all_faces.append(Face(vert, norm, []))

        return all_faces

    def write_face(file:File, face:Face):
        file.write_short(face.vertex[0])
        file.write_short(face.normal[0])
        if face.texcoord:
            file.write_short(face.texcoord[0])

        file.write_short(face.vertex[1])
        file.write_short(face.normal[1])
        if face.texcoord:
            file.write_short(face.texcoord[1])

        file.write_short(face.vertex[2])
        file.write_short(face.normal[2])
        if face.texcoord:
            file.write_short(face.texcoord[2])

    def write_face_partial(file:File, face:Face):
        file.write_short(face.vertex[2])
        file.write_short(face.normal[2])
        if face.texcoord:
            file.write_short(face.texcoord[2])

    info = IndexInfo(0, 0, 0)
    face_data_start = b'\x08\x50\x00\x00\x1E\x00\x08\x60\x00\x00\x00\x03\x10\x00\x00\x10\x08\x00\x00\x00'
    if flags == 0x0009000A:
        face_data_start = b'\x08\x50\x00\x00\x1E\x00\x08\x60\x00\x00\x00\x00\x10\x00\x00\x10\x08\x00\x00\x00'
    face_infos = []

    for i, mesh in enumerate(meshes):
        faceinfo = FaceInfo(flags, 0, 0)
        me = mesh.data

        face_indices = []
        for poly in me.polygons:
            for v in poly.vertices:
                vert = v + info.vertex_increment
                face_indices.append(vert)

        current_normal_indices = list(range(0+info.normal_increment, len(me.loops)+info.normal_increment))

        if meshes_uv_indices:
            all_faces = create_faces(face_indices, current_normal_indices, meshes_uv_indices[i], weightpaint_normals)
        else:
            all_faces = create_faces(face_indices, current_normal_indices, weightpaint_normals=weightpaint_normals)

        face_sets = strip_faces(all_faces)
        

        file.write_32bit_aligned()
        offset = file.tell()
        faceinfo.offset = offset

        file.write(face_data_start)
        if meshes_uv_indices:
            file.write(b'\x14') # flags for faces with normals and UVs
        else:
            file.write(b'\x04') # flags for only normals

        for set in face_sets:
            file.write(b'\x99')
            file.write_short(len(set) + 2)

            for face in set:
                if face.texcoord:
                    for t in range(len(face.texcoord)):
                        face.texcoord[t] = face.texcoord[t] + info.texcoord_increment

            first_face = set[0]
            write_face(file, first_face)

            for x in range(len(set)-1):
                current_face = set[x+1]
                write_face_partial(file, current_face)

        info.vertex_increment += len(me.vertices)
        if weightpaint_normals:
            info.normal_increment += len(me.vertices)
        else:
            info.normal_increment += len(me.loops)
        if meshes_uv_indices:
            uvcount = max(meshes_uv_indices[i]) + 1
            info.texcoord_increment += uvcount

        
        file.write_32bit_aligned()
        size = file.tell() - offset
        faceinfo.size = size

        face_infos.append(faceinfo)

    return face_infos

def triangulateMesh(mesh: bpy.types.Mesh):
    """Transforms a mesh into a mesh only consisting
    of triangles, so that it can be stripped"""

    # Thank you to Justin113D on GitHub for this triangulate function!

    # if we use custom normals, we gotta correct them
    # manually, since blenders triangulate is shit
    if mesh.use_auto_smooth:
        # calculate em, so that we can collect the correct normals
        mesh.calc_normals_split()

        # and now store them, together with the vertex indices,
        # since those will be the only identical data after triangulating
        normalData = list()
        for p in mesh.polygons:
            indices = list()
            normals = list()

            for l in p.loop_indices:
                loop = mesh.loops[l]
                nrm = loop.normal
                normals.append((nrm.x, nrm.y, nrm.z))
                indices.append(loop.vertex_index)

            normalData.append((indices, normals))

        # free the split data
        # mesh.free_normals_split()

    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm,
                          faces=bm.faces,
                          quad_method='FIXED',
                          ngon_method='EAR_CLIP')
    bm.to_mesh(mesh)
    bm.free()

    if mesh.use_auto_smooth:
        polygons = list()
        for p in mesh.polygons:
            polygons.append(p)

        splitNormals = [None] * len(mesh.loops)

        for nd in normalData:
            foundTris = 0
            toFind = len(nd[0])-2

            out = False
            toRemove = list()

            for p in polygons:
                found = 0
                for l in p.loop_indices:
                    if mesh.loops[l].vertex_index in nd[0]:
                        found += 1

                if found == 3:
                    foundTris += 1

                    for l in p.loop_indices:
                        splitNormals[l] \
                            = nd[1][nd[0].index(mesh.loops[l].vertex_index)]

                    toRemove.append(p)
                    if foundTris == toFind:
                        break

            for p in toRemove:
                polygons.remove(p)

        if len(polygons) > 0:
            print("\ntriangulating went wrong?", len(polygons))
        else:
            mesh.normals_split_custom_set(splitNormals)

def getNormalData_weightpaint(mesh: bpy.types.Mesh) -> list():
    """Gets the normals of a weight painted mesh"""
    normals = list()
    if mesh.use_auto_smooth:
        mesh.calc_normals_split()
        for v in mesh.vertices:
            normal = mathutils.Vector((0, 0, 0))
            normalCount = 0
            for l in mesh.loops:
                if l.vertex_index == v.index:
                    normal += l.normal
                    normalCount += 1
            if normalCount == 0:
                normals.append(v.normal)
            else:
                normals.append(normal / normalCount)

        mesh.free_normals_split()
    else:
        for v in mesh.vertices:
            normals.append(v.normal)
    return normals

def getNormalData(mesh: bpy.types.Mesh) -> list():
    """Gets the normals of a mesh that isn't weight painted"""
    normals = list()
    normal_indices = list()
    normal_index = 0
    if mesh.use_auto_smooth:
        mesh.calc_normals_split()
        for l in mesh.loops:
            normal = mathutils.Vector((0, 0, 0))
            normal += l.normal
            """
            if normal in normals:
                norm_index = normals.index(normal)
                normal_indices.append(norm_index)
            else:
                normals.append(normal)
                normal_indices.append(normal_index)
                normal_index += 1
            """
            normals.append(normal)

        mesh.free_normals_split()
    else:
        for v in mesh.vertices:
            normals.append(v.normal)
            normal_indices.append(v.index)
    return normals, normal_indices

def get_all_materials():
    """Gets all of the materials in the blend file with all of its properties"""
    texture_id = 0
    untitled_texture_id = 0

    all_materials = []
    texture_names = []
    
    for material in bpy.data.materials:
        if material.node_tree:
            color = [0.7529412508010864, 0.7529412508010864, 0.7529412508010864, 1.0]
            alpha = 1.0
            texture_count = 0
            texture_flag_list = []
            texture_ids = []

            for node in material.node_tree.nodes:
                if node.bl_idname == 'ShaderNodeTexImage':
                    texture_count += 1
                    if node.image:
                        texture_name = node.image.name.split('.')[:-1]
                        texture_name = ''.join(x for x in texture_name)
                        texture_name += ".gvr"
                    else:
                        texture_name = "untitled{}.gvr".format(untitled_texture_id)
                        untitled_texture_id += 1

                    if texture_name in texture_names:
                        tex_id = texture_names.index(texture_name)
                        texture_ids.append(tex_id)
                    else:
                        texture_names.append(texture_name)
                        texture_ids.append(texture_id)
                        texture_id += 1

                    texture_flags = node.gnoSettings.texture_property
                    
                    texture_flag_list.append(texture_flags)

                if node.bl_idname == 'ShaderNodeRGB':
                    rgb_outputs = node.outputs[0]
                    color = rgb_outputs.default_value

                if node.bl_idname == 'ShaderNodeValue':
                    alpha_outputs = node.outputs[0]
                    alpha = alpha_outputs.default_value
            
            color = color[:3]

            new_material = Material(material, material.name, color, alpha, texture_count, texture_ids, texture_flag_list)
            all_materials.append(new_material)

    return all_materials, texture_names

def get_mesh_material(ob):
    """Gets the material of a mesh (currently will halt the export if no material is assigned)"""
    if ob.type != 'MESH':
        raise Exception('input object incorrect')

    if not ob.data.materials:
        raise Exception('mesh {} has no materials'.format(ob.name))

    if ob.data.materials[0] is None:
        raise Exception('mesh {} has no materials'.format(ob.name))

    return ob.data.materials[0]

def get_material_index(all_mats, material) -> int:
    """Gets the index of a material in a list of materials, so it can be assigned to a mesh"""
    index_found = False
    all_material_names = [x.name for x in all_mats]
    material_name = material.name
    for material_index in range(len(all_material_names)):
        if all_material_names[material_index] == material_name:
            index_found = True
            break

    if not index_found:
        raise Exception("Material index calculation failed for {}. Does material not exist?".format(material_name))
        
    return material_index

def get_weight_painted_meshes():
    """Checks all meshes for if they are weight painted, if so, it will format the data and return it"""
    objects = bpy.context.scene.objects
    mesh_names = []
    vert_weights = [] # these go in order of mesh names
    vert_bones = []

    for mesh in objects:
        if not mesh.type == 'MESH':
            continue
        
        # ensure vertex groups are sorted
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = mesh
        mesh.select_set(True)

        bpy.ops.object.vertex_group_sort()

        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = None
        mesh.select_set(False)

        myVertexGroups = {i: [ ] for i in range(len(mesh.data.vertices))}
        
        firstvert = mesh.data.vertices[0]
        if not firstvert.groups:
            continue
        group = firstvert.groups[0]
        if len(mesh.vertex_groups) <= 1:
            continue
        if mesh.vertex_groups[group.group].index == 0:
            if mesh.vertex_groups[group.group].weight(0) == 1.0:
                continue

        mesh_names.append(mesh.name)
        
        for v in mesh.data.vertices:
            for g in v.groups:
                if not len(myVertexGroups[v.index]):
                    myVertexGroups[v.index].append(g.weight)
                myVertexGroups[v.index].append(g.group)
                
        
        for groupIndex, groupVertices in myVertexGroups.items():
            if len(groupVertices) < 3: # check for whether there is only one vertex group assigned to vertex
                groupVertices.append(0) # append whichever bone group, let's use the first one
                groupVertices[0] = 1.0 # make the vertex weigh 100%, this will make the dummy vertex group weight 0%
            vert_weights.append(groupVertices[0])
            vert_bones.append([groupVertices[1], groupVertices[2]])

    return mesh_names, vert_weights, vert_bones  

def get_mesh_bone(ob):
    """If mesh isn't weight painted, it should contain only one vertex group, which will be the bone the mesh will be assigned to"""
    if ob is None or ob.type != 'MESH':
        raise Exception("input object invalid")
        
    arm = ob.find_armature()
        
    if not arm:
        raise Exception("armature object not found")
        
    all_bones = [x.name for x in arm.data.bones]

    # ensure we got the latest assignments and weights
    ob.update_from_editmode()
    me = ob.data
    
    # create vertex group lookup dictionary for names
    vgroup_names = {vgroup.index: vgroup.name for vgroup in ob.vertex_groups}


    if not vgroup_names[0]:
        raise Exception("no vertex groups")

    if vgroup_names[0] not in all_bones:
        raise Exception("bone not found")

    return all_bones.index(vgroup_names[0]), vgroup_names[0]

def get_bone_group(ob, bone, is_weighted):
    """Get the bone group a bone is related to. If it's a weight painted mesh, there is no bone group assigned"""
    if is_weighted:
        return -1

    if ob is None or ob.type != 'MESH':
        raise Exception("input object invalid")
        
    arm = ob.find_armature()
        
    if not arm:
        raise Exception("armature object not found")

    all_bone_groups = [x.name for x in arm.pose.bone_groups[1:]]
    bone_group = arm.pose.bones[bone].bone_group
    if bone_group.name not in all_bone_groups:
        raise Exception("bone group not found")

    return all_bone_groups.index(bone_group.name)

def get_bone_group_amount(ob):
    """Gets the amount of bone groups of the armature that's related to the passed in mesh"""
    if ob is None or ob.type != 'MESH':
        raise Exception("input object invalid")
        
    arm = ob.find_armature()
        
    if not arm:
        raise Exception("armature object not found")

    return len(arm.pose.bone_groups)

def get_mesh_uvs_with_indices(me):
    """Get's all of the UV coordinates of a mesh with its indices for faces"""
    if not me.uv_layers:
        return False
    uv_layer = me.uv_layers.active.data

    all_uvs = []
    indices_to_uvs_for_loops = []
    new_uv_index = 0

    for poly in me.polygons:
        
        for loop_index in poly.loop_indices:
            vert_uv = uv_layer[loop_index].uv
            vert_uv_arr = [vert_uv[0], vert_uv[1]]
            
            found_existing_uv = False
            for uv in all_uvs:
                uv_arr = [uv[0], uv[1]]
                if vert_uv_arr == uv_arr:
                    indices_to_uvs_for_loops.append(all_uvs.index(uv))
                    found_existing_uv = True
                    break
                
            if not found_existing_uv:
                all_uvs.append(vert_uv)
                indices_to_uvs_for_loops.append(new_uv_index)
                new_uv_index += 1          

    return all_uvs, indices_to_uvs_for_loops, new_uv_index

def write_NFN0_header(file:File):
    """Writes the filename header"""
    file.write_32bit_aligned()

    filename = file.get_filename()

    header_size = len(filename) + 0x11
    header_size = (header_size + 31) & ~31 # 32 bit alignment

    file.write(struct.pack('<4sI8x', bytes('NFN0', 'ascii'), header_size-0x8))
    file.write(struct.pack('>{}s'.format(len(filename)+1), bytes(filename, 'ascii')))       
    
def write_NEND_header(file:File):
    """Writes the end of the file header"""
    file.write_32bit_aligned()
    file.write(struct.pack('<4sI', bytes('NEND', 'ascii'), 0x8))
    file.write_32bit_aligned()