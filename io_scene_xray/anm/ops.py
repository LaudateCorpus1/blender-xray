# standart modules
import os

# blender modules
import bpy
import bpy_extras

# addon modules
from . import imp
from . import exp
from .. import icons
from .. import log
from .. import utils
from .. import text
from .. import version_utils
from .. import ie_props


filename_ext = '.anm'
op_text = 'Animation Paths'

op_import_anm_props = {
    'filter_glob': bpy.props.StringProperty(
        default='*'+filename_ext,
        options={'HIDDEN'}
    ),
    'directory': bpy.props.StringProperty(subtype='DIR_PATH'),
    'files': bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement
    ),
    'camera_animation': ie_props.PropAnmCameraAnimation()
}


class XRAY_OT_import_anm(
        ie_props.BaseOperator,
        bpy_extras.io_utils.ImportHelper
    ):
    bl_idname = 'xray_import.anm'
    bl_label = 'Import .anm'
    bl_description = 'Imports X-Ray animation'
    bl_options = {'UNDO', 'PRESET'}

    text = op_text
    ext = filename_ext
    filename_ext = filename_ext

    if not version_utils.IS_28:
        for prop_name, prop_value in op_import_anm_props.items():
            exec('{0} = op_import_anm_props.get("{0}")'.format(prop_name))

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.enabled = False
        files_count = len(self.files)
        if files_count == 1:
            if not self.files[0].name:
                files_count = 0
        row.label(text='{} items'.format(files_count))
        layout.prop(self, 'camera_animation')

    @utils.execute_with_logger
    @utils.set_cursor_state
    def execute(self, context):
        if not self.files[0].name:
            self.report({'ERROR'}, 'No files selected!')
            return {'CANCELLED'}
        import_context = imp.ImportAnmContext()
        import_context.camera_animation = self.camera_animation
        for file in self.files:
            import_context.filepath = os.path.join(self.directory, file.name)
            try:
                imp.import_file(import_context)
            except utils.AppError as err:
                import_context.errors.append(err)
        for err in import_context.errors:
            log.err(err)
        return {'FINISHED'}

    def invoke(self, context, event):
        preferences = version_utils.get_preferences()
        self.camera_animation = preferences.anm_create_camera
        return super().invoke(context, event)


op_export_anm_props = {
    'filter_glob': bpy.props.StringProperty(
        default='*'+filename_ext,
        options={'HIDDEN'}
    ),
    'format_version': ie_props.prop_anm_format_version()
}


class XRAY_OT_export_anm(
        ie_props.BaseOperator,
        bpy_extras.io_utils.ExportHelper
    ):
    bl_idname = 'xray_export.anm'
    bl_label = 'Export .anm'
    bl_description = 'Exports X-Ray animation'
    bl_options = {'UNDO', 'PRESET'}

    text = op_text
    ext = filename_ext
    filename_ext = filename_ext

    if not version_utils.IS_28:
        for prop_name, prop_value in op_export_anm_props.items():
            exec('{0} = op_export_anm_props.get("{0}")'.format(prop_name))

    def draw(self, context):
        layout = self.layout
        utils.draw_fmt_ver_prop(layout, self, 'format_version')

    @utils.execute_with_logger
    @utils.set_cursor_state
    def execute(self, context):
        export_context = exp.ExportAnmContext()
        export_context.format_version = self.format_version
        export_context.active_object = context.active_object
        export_context.filepath = self.filepath
        try:
            exp.export_file(export_context)
        except utils.AppError as err:
            export_context.errors.append(err)
        for err in export_context.errors:
            log.err(err)
        return {'FINISHED'}

    def invoke(self, context, event):
        obj = context.active_object
        if obj:
            self.filepath = obj.name
            if not self.filepath.lower().endswith(self.filename_ext):
                self.filepath += self.filename_ext
        else:
            self.report({'ERROR'}, 'No active objects!')
            return {'CANCELLED'}
        if not obj.animation_data:
            self.report(
                {'ERROR'},
                'Object "{}" has no animation data.'.format(obj.name)
            )
            return {'CANCELLED'}
        preferences = version_utils.get_preferences()
        self.format_version = preferences.anm_format_version
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


classes = (
    (XRAY_OT_import_anm, op_import_anm_props),
    (XRAY_OT_export_anm, op_export_anm_props)
)


def register():
    for operator, properties in classes:
        version_utils.assign_props([(properties, operator), ])
        bpy.utils.register_class(operator)


def unregister():
    for operator, properties in reversed(classes):
        bpy.utils.unregister_class(operator)
