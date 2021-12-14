# standart modules
import os

# blender modules
import bpy
import bpy_extras

# addon modules
from . import imp
from .. import utils
from .. import contexts
from .. import icons
from .. import log
from .. import ie_props
from .. import version_utils
from .. import obj


class ImportPartContext(obj.imp.utility.ImportObjectContext):
    def __init__(self):
        super().__init__()


def menu_func_import(self, context):
    icon = icons.get_stalker_icon()
    self.layout.operator(
        XRAY_OT_import_part.bl_idname,
        text=utils.build_op_label(XRAY_OT_import_part),
        icon_value=icon
    )


filename_ext = '.part'
op_text = 'Scene Objects'
import_part_props = {
    'directory': bpy.props.StringProperty(subtype="DIR_PATH"),
    'files': bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement
    ),
    'filter_glob': bpy.props.StringProperty(
        default='*'+filename_ext, options={'HIDDEN'}
    ),
    'mesh_split_by_materials': ie_props.PropObjectMeshSplitByMaterials(),
    'fmt_version': ie_props.PropSDKVersion()
}


class XRAY_OT_import_part(ie_props.BaseOperator):
    bl_idname = 'xray_import.part'
    bl_label = 'Import .part'
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    draw_fun = menu_func_import
    text = op_text
    ext = filename_ext
    filename_ext = filename_ext

    if not version_utils.IS_28:
        for prop_name, prop_value in import_part_props.items():
            exec('{0} = import_part_props.get("{0}")'.format(prop_name))

    def draw(self, context):
        layout = self.layout

        row = layout.split()
        row.label(text='Format Version:')
        row.row().prop(self, 'fmt_version', expand=True)

        layout.prop(self, 'mesh_split_by_materials')

    @utils.execute_with_logger
    @utils.set_cursor_state
    def execute(self, context):
        preferences = version_utils.get_preferences()
        textures_folder = preferences.textures_folder_auto
        objects_folder = preferences.objects_folder_auto
        import_context = ImportPartContext()
        import_context.textures_folder=textures_folder
        import_context.soc_sgroups=self.fmt_version == 'soc'
        import_context.split_by_materials=self.mesh_split_by_materials
        import_context.operator=self
        import_context.objects_folder=objects_folder
        import_context.import_motions = False
        for file in self.files:
            file_path = os.path.join(self.directory, file.name)
            try:
                imp.import_file(file_path, import_context)
            except utils.AppError as err:
                import_context.errors.append(err)
        for err in import_context.errors:
            log.err(err)
        return {'FINISHED'}

    def invoke(self, context, event):
        preferences = version_utils.get_preferences()
        self.mesh_split_by_materials = preferences.part_mesh_split_by_mat
        self.fmt_version = preferences.part_sdk_version
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def register():
    version_utils.assign_props([
        (import_part_props, XRAY_OT_import_part),
    ])
    bpy.utils.register_class(XRAY_OT_import_part)


def unregister():
    import_menu, export_menu = version_utils.get_import_export_menus()
    import_menu.remove(menu_func_import)
    bpy.utils.unregister_class(XRAY_OT_import_part)
