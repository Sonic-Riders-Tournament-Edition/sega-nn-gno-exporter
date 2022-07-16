import argparse
import struct

parser = argparse.ArgumentParser()
parser.add_argument("file")
parser.add_argument("output")
parsedargs = parser.parse_args()

with open(parsedargs.file, "rb") as file:
    if file.read(4).decode('ascii') != 'NGIF':
        raise Exception("invalid model")

    # seek to model info section
    file.seek(0x8)
    ngob_index = struct.unpack('>I', file.read(4))[0]

    file.seek(0x4)
    for _ in range(ngob_index):
        file.seek(struct.unpack('<I', file.read(4))[0], 1)
        file.seek(4, 1)

    file.seek(4, 1)
    file.seek(struct.unpack('>I', file.read(4))[0] + 0x20)

    # get bone info, seek to bone data
    file.seek(0x28, 1)
    bone_count = struct.unpack('>I', file.read(4))[0]
    file.seek(4, 1)
    file.seek(struct.unpack('>I', file.read(4))[0] + 0x20)
    bone_data = file.read(bone_count * 0x80)

with open(parsedargs.output, "wb") as file:
    file.write(bone_data)