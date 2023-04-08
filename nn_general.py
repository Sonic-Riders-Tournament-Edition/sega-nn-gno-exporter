import struct, bpy

def generate_NGIF_header(offset_to_NOF0, NGOB_header_index):
    """Generates NN's info header"""
    data = struct.pack('>6I', NGOB_header_index, 0x20, offset_to_NOF0-0x20, offset_to_NOF0, 0x1C0, 0x1)
    header = struct.pack('<4sI', bytes('NGIF', 'ascii'), len(data))
    return struct.pack('>' + str(len(header)) + 's' + str(len(data)) + 's', header, data)

def message_box(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)