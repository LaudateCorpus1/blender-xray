# blender modules
import bpy

# addon modules
from .. import utils
from .. import version_utils


class XRAY_OT_verify_uv(bpy.types.Operator):
    bl_idname = 'io_scene_xray.verify_uv'
    bl_label = 'Verify UV'
    bl_description = 'Find UV-maps errors in selected objects'

    MINIMUM_VALUE = -32.0
    MAXIMUM_VALUE = 32.0
    BAD_UV = True
    CORRECT_UV = False

    @utils.set_cursor_state
    def execute(self, context):
        # set object mode
        if context.object:
            bpy.ops.object.mode_set(mode='OBJECT')
        objects = context.selected_objects
        if not objects:
            self.report({'WARNING'}, 'No objects selected')
            return {'CANCELLED'}
        bad_objects = []
        for bpy_object in objects:
            uv_status = self.verify_uv(context, bpy_object)
            if uv_status == self.BAD_UV:
                bad_objects.append(bpy_object.name)
        bpy.ops.object.select_all(action='DESELECT')
        for bad_object_name in bad_objects:
            bad_object = bpy.data.objects[bad_object_name]
            version_utils.select_object(bad_object)
        version_utils.set_active_object(None)
        return {'FINISHED'}

    def verify_uv(self, context, bpy_object):
        if bpy_object.type != 'MESH':
            return self.CORRECT_UV
        version_utils.set_active_object(bpy_object)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.reveal()
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        mesh = bpy_object.data
        has_bad_uv = False
        for uv_layer in mesh.uv_layers:
            for polygon in mesh.polygons:
                for loop in polygon.loop_indices:
                    uv = uv_layer.data[loop].uv
                    if not (self.MINIMUM_VALUE < uv.x < self.MAXIMUM_VALUE):
                        polygon.select = True
                        has_bad_uv = True
                    if not (self.MINIMUM_VALUE < uv.y < self.MAXIMUM_VALUE):
                        polygon.select = True
                        has_bad_uv = True
        if has_bad_uv:
            return self.BAD_UV
        else:
            return self.CORRECT_UV


def register():
    bpy.utils.register_class(XRAY_OT_verify_uv)


def unregister():
    bpy.utils.unregister_class(XRAY_OT_verify_uv)
