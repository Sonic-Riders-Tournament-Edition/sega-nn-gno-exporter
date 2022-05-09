import bpy
import mathutils
import os
import struct
from . import strippifier
from dataclasses import dataclass
import pathlib

@dataclass
class Bounds:
    position: tuple
    scale: float

default_bounds = Bounds((1.19209e-07, 0.45939, 0), 0.947298)




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
    def __init__(self, filepath, read_or_write, endianness = '>'):
        self.filepath = filepath
        self.fileobject = open(filepath, read_or_write)
        self.endian = endianness
        self.set_formats()

    def __del__(self):
        self.fileobject.close()

    def change_endianness(self, endianness):
        self.endian = endianness
        self.set_formats()
    
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

    def read(self, size, offset = None):
        """
        Reads bytes from the file, either from current position or from a specified offset.
        """

        if offset:
            original_pos = self.tell()
            self.seek(offset)
            output = self.fileobject.read(size)
            self.seek(original_pos)
        else:
            output = self.fileobject.read(size)

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

class Vector:
    position: tuple

    def __init__(self, position:tuple):
        self.position = position[:3]

    def write(self, file:File):
        for p in self.position:
            file.write_float(p)



def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n): 
        yield l[i:i + n]

def generate_NGIF_header(offset_to_NOF0, NGOB_header_index):
    data = struct.pack('>6I', NGOB_header_index, 0x20, offset_to_NOF0-0x20, offset_to_NOF0, 0x1C0, 0x1)
    header = struct.pack('<4sI', bytes('NGIF', 'ascii'), len(data))
    return struct.pack('>' + str(len(header)) + 's' + str(len(data)) + 's', header, data)

def calculate_bounding_box(o:bpy.types.Mesh):
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

def write_materials(file:File, materials:list[Material], gno:GNO):
    format_string = '>I12f10I' # for the main body of the material
    texture_format_string = '>4If'
    global material_offsets
    material_offsets = []

    for mat in materials:
        material_data = struct.pack(format_string, 0x1000000, mat.color[0], mat.color[1], mat.color[2], \
        mat.alpha, mat.color[0], mat.color[1], mat.color[2], 0.9, 0.9, 0.9, 2.0, 0.299999982118607, \
        0x1, 0x4, 0x5, 0x5, 0x2, 0x0, 0x6, 0x7, 0x0, 0x0)

        if mat.texture_count > 0:
            for i, texture_id in enumerate(mat.texture_ids):
                flags = 0x400C0101
                if mat.texture_flags[i] == 'reflective':
                    flags = 0x400C2004
                material_data += struct.pack(texture_format_string, flags, texture_id, \
                0x80000000, 0x0, 1.0)

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
    for v in mesh.vertices:
        for p in v.co:
            file.write_float(p)
    
    #file.write_8bit_aligned()
    return len(mesh.vertices)

def write_normals(file:File, normals:list):
    for n in normals:
        for p in n:
            point = int(round(p * 64))
            file.write_signed_byte(point)

    #file.write_8bit_aligned()
    return len(normals)

def write_uvs(file:File, uvs:list):
    for uv in uvs:
        u = round(uv[0] * 256)
        v = round(-(uv[1] - 1) * 256)
        file.write_signed_short(u)
        file.write_signed_short(v)
    
    #file.write_8bit_aligned()
    return len(uvs)

def write_vertex_weights(file:File, weights:list, bones:list):
    for w, b in zip(weights, bones):
        weight = int(round(w * 16384))
        for bone in b:
            file.write_byte(bone)
        file.write_signed_short(weight)

    file.write_8bit_aligned()

def write_mesh_faces(file:File, flags:int, meshes:list, meshes_uv_indices = False):
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

    def create_faces(vertices, uvs=None):
        div_verts = list(divide_chunks(vertices, 3))
        div_uvs = [[0, 0, 0]] * len(div_verts)
        if uvs:
            div_uvs = list(divide_chunks(uvs, 3))
        all_faces = []

        for vert, uv in zip(div_verts, div_uvs):
            if len(vert) < 3:
                continue
            if uvs:
                all_faces.append(Face(vert, vert, uv))
            else:
                all_faces.append(Face(vert, vert, []))

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

        if meshes_uv_indices:
            all_faces = create_faces(face_indices, meshes_uv_indices[i])
        else:
            all_faces = create_faces(face_indices)

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
        info.normal_increment += len(me.vertices)
        if meshes_uv_indices:
            uvcount = max(meshes_uv_indices[i]) + 1
            info.texcoord_increment += uvcount

        
        file.write_32bit_aligned()
        size = file.tell() - offset
        faceinfo.size = size

        face_infos.append(faceinfo)

        """
        # writes each face seperately, no stripping

        file.write_32bit_aligned()
        offset = file.tell()
        faceinfo.offset = offset

        file.write(face_data_start)
        if meshes_uv_indices:
            file.write(b'\x14') # flags for faces with normals and UVs
        else:
            file.write(b'\x04') # flags for only normals

        for face in all_faces:
            file.write(b'\x99')
            file.write_short(3)

            swap_f1_f2(face)

            if face.texcoord:
                for t in range(len(face.texcoord)):
                    face.texcoord[t] = face.texcoord[t] + info.texcoord_increment

            write_face(file, face)

        info.vertex_increment += len(me.vertices)
        info.normal_increment += len(me.vertices)
        if meshes_uv_indices:
            uvcount = max(meshes_uv_indices[i]) + 1
            info.texcoord_increment += uvcount

        
        file.write_32bit_aligned()
        size = file.tell() - offset
        faceinfo.size = size

        face_infos.append(faceinfo)
        """

    return face_infos




def write_meshdata_faces(file:File, flags:int, meshes:list, meshes_uv_indices = False, uv_counts:list = None):
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

    st = strippifier.Strippifier()
    info = IndexInfo(0, 0, 0)
    face_data_start = b'\x08\x50\x00\x00\x1E\x00\x08\x60\x00\x00\x00\x03\x10\x00\x00\x10\x08\x00\x00\x00'
    if flags == 0x0009000A:
        face_data_start = b'\x08\x50\x00\x00\x1E\x00\x08\x60\x00\x00\x00\x00\x10\x00\x00\x10\x08\x00\x00\x00'
    face_infos = []
    
    if meshes_uv_indices:
        for i, mesh in enumerate(meshes):
            faceinfo = FaceInfo(flags, 0, 0)

            me = mesh.data
            face_indices = []
            for poly in me.polygons:
                for v in poly.vertices:
                    face_indices.append(v)

            strips, normal_strips, uv_strips = st.Strippify(face_indices, meshes_uv_indices[i])
            for index, s in enumerate(strips):
                for x in range(len(s)):
                    strips[index][x] = strips[index][x] + info.vertex_increment
                    normal_strips[index][x] = normal_strips[index][x] + info.normal_increment
                    uv_strips[index][x] = uv_strips[index][x] + info.texcoord_increment

            info.vertex_increment += len(me.vertices)
            info.normal_increment += len(me.vertices) # currently there's as many normals as vertices
            #info.texcoord_increment += uv_counts[i]
            uvcount = max(meshes_uv_indices[i]) + 1
            info.texcoord_increment += uvcount

            file.write_32bit_aligned()
            offset = file.tell()
            faceinfo.offset = offset

            file.write(face_data_start)
            file.write(b'\x14') # flags for faces with normals and UVs
            for index, strip in enumerate(strips):
                full_strip = []
                file.write(b'\x99')
                file.write_short(len(strip))
                for s, n, u in zip(strip, normal_strips[index], uv_strips[index]):
                    full_strip.append(s)
                    #full_strip.append(n)
                    full_strip.append(s)
                    full_strip.append(u)
                file.write_short_list(full_strip)
            
            file.write_32bit_aligned()
            size = file.tell() - offset
            faceinfo.size = size

            face_infos.append(faceinfo)

    else:
        for i, mesh in enumerate(meshes):
            faceinfo = FaceInfo(flags, 0, 0)

            me = mesh.data
            face_indices = []
            for poly in me.polygons:
                for v in poly.vertices:
                    face_indices.append(v)

            strips, normal_strips = st.Strippify(face_indices)
            for index, s in enumerate(strips):
                for x in range(len(s)):
                    strips[index][x] = strips[index][x] + info.vertex_increment
                    normal_strips[index][x] = normal_strips[index][x] + info.normal_increment

            info.vertex_increment += len(me.vertices)
            info.normal_increment += len(me.vertices) # currently there's as many normals as vertices

            file.write_32bit_aligned()
            offset = file.tell()
            faceinfo.offset = offset

            file.write(face_data_start)
            file.write(b'\x04') # flags for faces with only normals
            for index, strip in enumerate(strips):
                full_strip = []
                file.write(b'\x99')
                file.write_short(len(strip))
                for s, n in zip(strip, normal_strips[index]):
                    full_strip.append(s)
                    #full_strip.append(n)
                    full_strip.append(s)
                file.write_short_list(full_strip)
            
            file.write_32bit_aligned()
            size = file.tell() - offset
            faceinfo.size = size
            
            face_infos.append(faceinfo)

    return face_infos




def triangulateMesh(mesh: bpy.types.Mesh):
    """Transforms a mesh into a mesh only consisting
    of triangles, so that it can be stripped"""

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
            
def getNormalData(mesh: bpy.types.Mesh) -> list():
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

def get_normals(mesh: bpy.types.Mesh) -> list():
    normals = list()
    """
    if mesh.use_auto_smooth:
        mesh.calc_normals_split()
        for v in mesh.vertices:
            for l in mesh.loops:
                if l.vertex_index == v.index:
                    normal = mathutils.Vector((0, 0, 0))
                    normal += l.normal
                    normals.append(normal)
                    break
        
        mesh.free_normals_split()
    else:
        for v in mesh.vertices:
            normals.append(v.normal)
    """

    for v in mesh.vertices:
        shared_polys = []
        for p in mesh.polygons:
            if v.index in p.vertices:
                shared_polys.append(p)

        normal = mathutils.Vector((0, 0, 0))
        for poly in shared_polys:
            normal += poly.normal
        
        normal = normal / len(shared_polys)
        normals.append(normal)

    return normals

def get_all_materials():
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

                    texture_flags = "none"
                    if node.inputs[0].links:
                        texture_flags = "reflective"
                    
                    texture_flag_list.append(texture_flags)

                if node.bl_idname == 'ShaderNodeRGB':
                    rgb_outputs = node.outputs[0]
                    color = rgb_outputs.default_value

                if node.bl_idname == 'ShaderNodeValue':
                    alpha_outputs = node.outputs[0]
                    alpha = alpha_outputs.default_value
            
            color = color[:3]

            new_material = Material(material.name, color, alpha, texture_count, texture_ids, texture_flag_list)
            all_materials.append(new_material)

    return all_materials, texture_names

def get_mesh_material(ob):
    if ob.type != 'MESH':
        raise Exception('input object incorrect')

    if not ob.data.materials:
        raise Exception('mesh {} has no materials'.format(ob.name))

    if ob.data.materials[0] is None:
        raise Exception('mesh {} has no materials'.format(ob.name))

    return ob.data.materials[0]

def get_material_index(all_mats, material) -> int:
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
    objects = bpy.context.scene.objects
    mesh_names = []
    vert_weights = [] # these go in order of mesh names
    vert_bones = []

    for mesh in objects:
        if not mesh.type == 'MESH':
            continue
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
    if ob is None or ob.type != 'MESH':
        raise Exception("input object invalid")
        
    arm = None
    for o in bpy.context.scene.objects:
        if o.type == 'ARMATURE':
            if ob.parent == o:
                arm = o
                break
        
    if not arm:
        raise Exception("armature object not found")
        
    all_bones = [x.name for x in arm.data.bones]

    # ensure we got the latest assignments and weights
    ob.update_from_editmode()
    me = ob.data
    
    # create vertex group lookup dictionary for names
    vgroup_names = {vgroup.index: vgroup.name for vgroup in ob.vertex_groups}


    """
    # create dictionary of vertex group assignments per vertex
    vgroups = {v.index: [vgroup_names[g.group] for g in v.groups] for v in me.vertices}

    if not vgroups[0]:
        raise Exception("incorrect vertex groups")
    
    if vgroups[0][0] not in all_bones:
        raise Exception("bone not found")
        
    return all_bones.index(vgroups[0][0]), vgroups[0][0]
    """

    if not vgroup_names[0]:
        raise Exception("no vertex groups")

    if vgroup_names[0] not in all_bones:
        raise Exception("bone not found")

    return all_bones.index(vgroup_names[0]), vgroup_names[0]

def get_bone_group(ob, bone, is_weighted):
    if is_weighted:
        return -1

    if ob is None or ob.type != 'MESH':
        raise Exception("input object invalid")
        
    arm = None
    for o in bpy.context.scene.objects:
        if o.type == 'ARMATURE':
            if ob.parent == o:
                arm = o
                break
        
    if not arm:
        raise Exception("armature object not found")

    all_bone_groups = [x.name for x in arm.pose.bone_groups[1:]]
    bone_group = arm.pose.bones[bone].bone_group
    if bone_group.name not in all_bone_groups:
        raise Exception("bone group not found")

    return all_bone_groups.index(bone_group.name)

def get_mesh_uvs_with_indices_old(me):
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

def get_mesh_uvs_with_indices(me):
    if not me.uv_layers:
        return False
    uv_layer = me.uv_layers.active.data

    all_uvs = []
    indices_to_uvs_for_loops = []
    new_uv_index = 0
    vert_dict = {}

    for poly in me.polygons:
        
        for loop_index in poly.loop_indices:
            vert_uv = uv_layer[loop_index].uv
            vert_uv_arr = vert_uv[0], vert_uv[1]
            uv_key = me.loops[loop_index].vertex_index, vert_uv_arr

            get_index = vert_dict.get(uv_key)
            if get_index is None:
                vert_dict[uv_key] = new_uv_index
                indices_to_uvs_for_loops.append(new_uv_index)
                all_uvs.append(vert_uv)
                new_uv_index += 1
            else:
                indices_to_uvs_for_loops.append(get_index)       

    return all_uvs, indices_to_uvs_for_loops, new_uv_index

def read_original_model(file: File):
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

def write_new_gno_file_2(output_file: File, **keywords):

    def write_vertex_struct(file:File, info:VertexSetInfo, gno:GNO):
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

    def get_mesh_data(ob:bpy.types.Object, vertex_set, face_index, is_weighted = False):
        bone_index, bone_name = get_mesh_bone(ob)
        bone_group = get_bone_group(ob, bone_name, is_weighted)
        firstmat = get_mesh_material(ob)
        mat_index = get_material_index(materials, firstmat)
        bounds_position, bounds_scale = calculate_bounding_box(ob)
        bounds = Bounds(bounds_position, bounds_scale)

        # currently don't know how getting the correct bone automatically works
        # so i'm gonna give it a bone that is always visible in the game (0x46)
        mesh = Mesh(ob, bounds, 0x46, bone_group, mat_index, vertex_set, face_index)
        return mesh

    def calculate_NGTL_header_size(current_size, texture_names):
        string_table_size = 0
        for name in texture_names:
            string_table_size += len(name) + 1 # +1 for string eliminator byte
        
        final_size = current_size + string_table_size + 0x8
        return (final_size + 31) & 0xFFFFFFE0 # align 32 bit
    
    def write_NGTL(file:File, texture_names, texture_name_offsets, gno:GNO):
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
        return struct.pack('>4s12x', bytes('NGOB', 'ascii'))

    def write_NOF0_header(file:File, gno:GNO):
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

    def write_NFN0_header(file:File):
        file.write_32bit_aligned()

        filename = bpy.path.basename(bpy.context.blend_data.filepath)
        if not filename:
            filename = 'untitled.blend'
        filename = filename[:-5]
        filename += 'gno'

        header_size = len(filename) + 0x11
        header_size = (header_size + 31) & ~31 # 32 bit alignment

        file.write(struct.pack('<4sI8x', bytes('NFN0', 'ascii'), header_size-0x8))
        file.write(struct.pack('>{}s'.format(len(filename)+1), bytes(filename, 'ascii')))
    
    def write_NEND_header(file:File):
        file.write_32bit_aligned()
        file.write(struct.pack('<4sI', bytes('NEND', 'ascii'), 0x8))
        file.write_32bit_aligned()
        
    
    gno = GNO()

    weighted_mesh_names, weighted_vertices_weights, weighted_vertices_bones = get_weight_painted_meshes()

    if keywords["original_model_bool"]:
        path = "{}\\{}".format(os.path.dirname(keywords["filepath"]), keywords["original_model"])
        extbonefile = File(path, "rb")
        original_bone_data = read_original_model(extbonefile)
        del extbonefile
    else:
        path = str(pathlib.Path(__file__).parent.absolute()) + "\\extbones.bin"
        extbonefile = open(path, "rb")
        original_bone_data = extbonefile.read()
        extbonefile.close()
    
    # categorize all meshes
    for m in bpy.context.scene.objects:
        if not m.type == 'MESH':
            continue
        triangulateMesh(m.data)
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
    

    # NGTL

    global materials
    materials, texture_names = get_all_materials()
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

    
    # NGOB

    bone_offset = output_file.tell()

    output_file.write(original_bone_data)
    

    write_materials(output_file, materials, gno)

    if gno.vertex_set_1_meshes:
        print('vertex 1')
        vertexset1_vertex_count = 0
        vertexset1_normal_count = 0
        vertexset1_uv_count = 0

        vertex_set_with_uvs_normals_offset = output_file.tell()
        for m in gno.vertex_set_1_meshes:
            vertexset1_vertex_count += write_vertices(output_file, m.data)
        output_file.write_8bit_aligned()

        normal_set_with_uvs_normals_offset = output_file.tell()
        for m in gno.vertex_set_1_meshes:
            normals = getNormalData(m.data)
            vertexset1_normal_count += write_normals(output_file, normals)
        output_file.write_8bit_aligned()

        uv_set_with_uvs_normals_offset = output_file.tell()
        for uv_i, m in enumerate(gno.vertex_set_1_meshes):
            all_uvs, uv_indices, uv_count = get_mesh_uvs_with_indices_old(m.data)
            gno.vertex_set_1_uv_indices.append(uv_indices)
            #gno.vertex_set_1_uv_count[uv_i] = uv_count
            vertexset1_uv_count += write_uvs(output_file, all_uvs)
        output_file.write_8bit_aligned()
        
    if gno.vertex_set_2_meshes:
        print('vertex 2')
        vertexset2_vertex_count = 0
        vertexset2_normal_count = 0

        vertex_set_with_normals_offset = output_file.tell()
        for m in gno.vertex_set_2_meshes:
            vertexset2_vertex_count += write_vertices(output_file, m.data)
        output_file.write_8bit_aligned()

        normal_set_with_normals_offset = output_file.tell()
        for m in gno.vertex_set_2_meshes:
            normals = getNormalData(m.data)
            vertexset2_normal_count += write_normals(output_file, normals)
        output_file.write_8bit_aligned()

    if gno.vertex_set_3_meshes:
        print('vertex 3')
        vertexset3_vertex_count = 0
        vertexset3_normal_count = 0
        vertexset3_uv_count = 0

        vertex_set_with_uvs_normals_weights_offset = output_file.tell()
        for m in gno.vertex_set_3_meshes:
            vertexset3_vertex_count += write_vertices(output_file, m.data)
        output_file.write_8bit_aligned()
        
        normal_set_with_uvs_normals_weights_offset = output_file.tell()
        for m in gno.vertex_set_3_meshes:
            normals = getNormalData(m.data)
            vertexset3_normal_count += write_normals(output_file, normals)
        output_file.write_8bit_aligned()
        
        uv_set_with_uvs_normals_weights_offset = output_file.tell()
        for uv_i, m in enumerate(gno.vertex_set_3_meshes):
            all_uvs, uv_indices, uv_count = get_mesh_uvs_with_indices_old(m.data)
            gno.vertex_set_3_uv_indices.append(uv_indices)
            #gno.vertex_set_3_uv_count[uv_i] = uv_count
            vertexset3_uv_count += write_uvs(output_file, all_uvs)
        output_file.write_8bit_aligned()
        
        weighted_bones_vertices_offset = output_file.tell()
        vertexset3_weight_count = vertexset3_vertex_count
        write_vertex_weights(output_file, weighted_vertices_weights, weighted_vertices_bones)

    if gno.vertex_set_1_meshes:
        vertex_set_1_offset = output_file.tell()

        vertexset1_info = VertexSetInfo( \
        vertex_set_1_offset, \
        vertex_set_with_uvs_normals_offset, vertexset1_vertex_count, \
        normal_set_with_uvs_normals_offset, vertexset1_normal_count, \
        uv_set_with_uvs_normals_offset, vertexset1_uv_count)

        write_vertex_struct(output_file, vertexset1_info, gno)

    if gno.vertex_set_2_meshes:
        vertex_set_2_offset = output_file.tell()

        vertexset2_info = VertexSetInfo( \
        vertex_set_2_offset, \
        vertex_set_with_normals_offset, vertexset2_vertex_count, \
        normal_set_with_normals_offset, vertexset2_normal_count)

        write_vertex_struct(output_file, vertexset2_info, gno)

    if gno.vertex_set_3_meshes:
        vertex_set_3_offset = output_file.tell()

        vertexset3_info = VertexSetInfo( \
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

    facedata_list = []

    if gno.vertex_set_1_meshes:
        vertexset1_faceoffsets = write_mesh_faces(output_file, 0x00C9002A, \
            gno.vertex_set_1_meshes, gno.vertex_set_1_uv_indices)
        facedata_list.append(vertexset1_faceoffsets)
    if gno.vertex_set_2_meshes:
        vertexset2_faceoffsets = write_mesh_faces(output_file, 0x0009000A, gno.vertex_set_2_meshes)
        facedata_list.append(vertexset2_faceoffsets)
    if gno.vertex_set_3_meshes:
        vertexset3_faceoffsets = write_mesh_faces(output_file, 0x1085000A, \
            gno.vertex_set_3_meshes, gno.vertex_set_3_uv_indices)
        facedata_list.append(vertexset3_faceoffsets)

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

    if gno.vertex_set_1_meshes:
        meshset_info.append(MeshSetInfo(output_file.tell(), gno.vertex_set_1_flags, len(gno.vertex_set_1_meshes)))
        for me in gno.vertex_set_1_meshes:
            mesh_data = get_mesh_data(me, vertex_index, faceindex)
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
        meshset_info.append(MeshSetInfo(output_file.tell(), gno.vertex_set_2_flags, len(gno.vertex_set_2_meshes)))
        for me in gno.vertex_set_2_meshes:
            mesh_data = get_mesh_data(me, vertex_index, faceindex)
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
        meshset_info.append(MeshSetInfo(output_file.tell(), gno.vertex_set_3_flags, len(gno.vertex_set_3_meshes)))
        for me in gno.vertex_set_3_meshes:
            mesh_data = get_mesh_data(me, vertex_index, faceindex, True)
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


    mesh_set_info_offset = output_file.tell()
    for info in meshset_info:
        output_file.write_int(info.flags)
        output_file.write_int(info.count)
        output_file.write_int_NOF0(info.start_offset, gno)
        output_file.write(struct.pack('8x'))

    main_object_data_offset = output_file.tell()
    for f in default_bounds.position:
        output_file.write_float(f)
    output_file.write_float(default_bounds.scale)

    output_file.write_int(len(materials))
    output_file.write_int_NOF0(material_structs_offset, gno)

    output_file.write_int(vertex_index)
    output_file.write_int_NOF0(offset_to_vertex_sets_offset, gno)

    output_file.write_int(len(face_info_struct_offsets))
    output_file.write_int_NOF0(face_info_offset, gno)

    output_file.write_int(len(original_bone_data) // 0x80)

    output_file.write_int(0xC)
    output_file.write_int_NOF0(bone_offset, gno)
    output_file.write_int(0x24) # this is the amount of bone groups, needs to be changed

    output_file.write_int(len(meshset_info))
    output_file.write_int_NOF0(mesh_set_info_offset, gno)

    output_file.write_int(0x4)

    output_file.write_32bit_aligned()
    offset_to_NOF0 = output_file.tell()
    write_NOF0_header(output_file, gno)
    write_NFN0_header(output_file)
    write_NEND_header(output_file)
    NGOB_size = offset_to_NOF0 - NGOB_header_offset
    return NGOB_header_offset, offset_to_NOF0, NGOB_size, main_object_data_offset



def write_new_spline_file(file:File):
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