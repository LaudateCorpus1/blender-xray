import os, math

import bpy, mathutils

from . import utils as level_utils, create, fmt, shaders, visuals, vb, ib, swi, cform
from .. import xray_io, utils, version_utils
from ..ogf import imp as ogf_imp


class Level(object):
    def __init__(self):
        self.name = None
        self.path = None
        self.xrlc_version = None
        self.xrlc_version_geom = None
        self.materials = None
        self.shaders = None
        self.textures = None
        self.vertex_buffers = None
        self.indices_buffers = None
        self.swis = None
        self.fastpath_vertex_buffers = None
        self.fastpath_indices_buffers = None
        self.fastpath_swis = None
        self.loaded_geometry = {}
        self.loaded_fastpath_geometry = {}
        self.hierrarhy_visuals = []
        self.visuals = []
        self.collections = {}
        self.sectors_objects = {}
        self.visual_keys = set()
        self.stats = ''


def create_sector_object(sector_id, collection, sectors_object):
    object_name = 'sector_{:0>3}'.format(sector_id)
    bpy_object = create.create_object(object_name, None)
    bpy_object.parent = sectors_object
    collection.objects.link(bpy_object)
    return bpy_object


def create_sectors_object(collection):
    object_name = 'sectors'
    bpy_object = create.create_object(object_name, None)
    collection.objects.link(bpy_object)
    return bpy_object


def import_sector_portal(data):
    packed_reader = xray_io.PackedReader(data)
    portal_count = len(data) // fmt.SECTOR_PORTAL_SIZE

    for portal_index in range(portal_count):
        portal = packed_reader.getf('H')[0]


def import_sector_root(data):
    packed_reader = xray_io.PackedReader(data)
    root = packed_reader.getf('I')[0]
    return root


def import_sector(data, level, sector_object):
    chunked_reader = xray_io.ChunkedReader(data)

    for chunk_id, chunk_data in chunked_reader:
        if chunk_id == fmt.SectorChunks.PORTALS:
            import_sector_portal(chunk_data)
        elif chunk_id == fmt.SectorChunks.ROOT:
            root_visual_index = import_sector_root(chunk_data)
            level.visuals[root_visual_index].parent = sector_object
        else:
            print('UNKNOWN LEVEL SECTOR CHUNK: {0:#x}, SIZE = {1}'.format(
                chunk_id, len(chunk_data)
            ))


def import_sectors(data, level, level_object):
    chunked_reader = xray_io.ChunkedReader(data)
    collection = level.collections[create.LEVEL_SECTORS_COLLECTION_NAME]
    sectors_object = create_sectors_object(collection)
    sectors_object.parent = level_object

    for sector_id, sector_data in chunked_reader:
        sector_object = create_sector_object(
            sector_id, collection, sectors_object
        )
        level.sectors_objects[sector_id] = sector_object
        import_sector(sector_data, level, sector_object)


def generate_glow_mesh_data(radius):
    vertices = (
        # XZ-plane
        (radius, 0.0, -radius),
        (radius, 0.0, radius),
        (-radius, 0.0, radius),
        (-radius, 0.0, -radius),
        # YZ-plane
        (0.0, radius, -radius),
        (0.0, radius, radius),
        (0.0, -radius, radius),
        (0.0, -radius, -radius),
        # XY-plane
        (radius, -radius, 0.0),
        (radius, radius, 0.0),
        (-radius, radius, 0.0),
        (-radius, -radius, 0.0)
    )
    faces = (
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (8, 9, 10, 11)
    )
    uv_face = (
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
        (0.0, 0.0),
    )
    uvs = []
    for face_index in range(3):
        uvs.extend(uv_face)
    return vertices, faces, uvs


def create_glow_mesh(name, vertices, faces, uvs):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, (), faces)
    uv_layer = mesh.uv_layers.new(name='Texture')
    for uv_index, data in enumerate(uv_layer.data):
        data.uv = uvs[uv_index]
    return mesh


def create_glow_object(glow_index, position, radius, shader_index, materials):
    object_name = 'glow_{:0>3}'.format(glow_index)
    vertices, faces, uvs = generate_glow_mesh_data(radius)
    mesh = create_glow_mesh(object_name, vertices, faces, uvs)
    material = materials[shader_index]
    material.use_backface_culling = False
    material.blend_method = 'BLEND'
    mesh.materials.append(material)
    glow_object = create.create_object(object_name, mesh)
    glow_object.location = position[0], position[2], position[1]
    return glow_object


def create_glow_object_v5(
        level, glow_index, position,
        radius, shader_index, texture_index,
        materials, shaders, textures
    ):
    object_name = 'glow_{:0>3}'.format(glow_index)
    vertices, faces, uvs = generate_glow_mesh_data(radius)
    mesh = create_glow_mesh(object_name, vertices, faces, uvs)
    material = ogf_imp.get_material(level, shader_index, texture_index)
    material.use_backface_culling = False
    material.blend_method = 'BLEND'
    mesh.materials.append(material)
    glow_object = create.create_object(object_name, mesh)
    glow_object.location = position[0], position[2], position[1]
    return glow_object


def import_glow(packed_reader, glow_index, materials):
    position = packed_reader.getf('3f')
    radius = packed_reader.getf('f')[0]
    shader_index = packed_reader.getf('H')[0]
    glow_object = create_glow_object(
        glow_index, position, radius, shader_index, materials
    )
    return glow_object


def import_glow_v5(
        level, packed_reader, glow_index, materials, shaders, textures
    ):
    position = packed_reader.getf('3f')
    radius = packed_reader.getf('f')[0]
    texture_index = packed_reader.getf('I')[0]
    shader_index = packed_reader.getf('I')[0]
    glow_object = create_glow_object_v5(
        level, glow_index, position, radius,
        shader_index, texture_index,
        materials, shaders, textures
    )
    return glow_object


def create_glows_object(collection):
    object_name = 'glows'
    bpy_object = create.create_object(object_name, None)
    collection.objects.link(bpy_object)
    return bpy_object


def import_glows(data, level):
    packed_reader = xray_io.PackedReader(data)
    glows_count = len(data) // fmt.GLOW_SIZE
    collection = level.collections[create.LEVEL_GLOWS_COLLECTION_NAME]
    glows_object = create_glows_object(collection)
    materials = level.materials

    for glow_index in range(glows_count):
        glow_object = import_glow(packed_reader, glow_index, materials)
        glow_object.parent = glows_object
        collection.objects.link(glow_object)

    return glows_object


def import_glows_v5(data, level):
    packed_reader = xray_io.PackedReader(data)
    glows_count = len(data) // fmt.GLOW_SIZE_V5
    collection = level.collections[create.LEVEL_GLOWS_COLLECTION_NAME]
    glows_object = create_glows_object(collection)

    if level.xrlc_version <= fmt.VERSION_5:
        shaders = level.shaders
        textures = level.textures
    else:
        shaders = level.shaders_or_textures
        textures = None

    for glow_index in range(glows_count):
        glow_object = import_glow_v5(
            level, packed_reader, glow_index,
            level.materials, shaders, textures
        )
        glow_object.parent = glows_object
        collection.objects.link(glow_object)

    return glows_object


INT_MAX = 2 ** 31 - 1


def import_light_dynamic(packed_reader, light_object):
    data = light_object.xray.level
    data.object_type = 'LIGHT_DYNAMIC'
    light_object.xray.is_level = True

    # controller id
    controller_id = packed_reader.getf('I')[0] # ???
    if controller_id > INT_MAX:
        controller_id = -1
    data.controller_id = controller_id

    # light type
    light_type = packed_reader.getf('I')[0] # ???
    if light_type > INT_MAX:
        light_type = -1
    data.light_type = light_type

    data.diffuse = packed_reader.getf('4f')
    data.specular = packed_reader.getf('4f')
    data.ambient = packed_reader.getf('4f')
    position = packed_reader.getf('3f')
    direction = packed_reader.getf('3f')
    data.range_ = packed_reader.getf('f')[0]
    data.falloff = packed_reader.getf('f')[0]
    data.attenuation_0 = packed_reader.getf('f')[0]
    data.attenuation_1 = packed_reader.getf('f')[0]
    data.attenuation_2 = packed_reader.getf('f')[0]
    data.theta = packed_reader.getf('f')[0]
    data.phi = packed_reader.getf('f')[0]

    euler = mathutils.Vector((direction[0], direction[2], direction[1])).to_track_quat('Y', 'Z').to_euler('XYZ')
    light_object.location = position[0], position[2], position[1]
    light_object.rotation_euler = euler[0], euler[1], euler[2]


def import_light_dynamic_v8(packed_reader, light_object):
    data = light_object.xray.level
    data.object_type = 'LIGHT_DYNAMIC'
    light_object.xray.is_level = True
    data.light_type = packed_reader.getf('I')[0] # ???
    data.diffuse = packed_reader.getf('4f')
    data.specular = packed_reader.getf('4f')
    data.ambient = packed_reader.getf('4f')
    position = packed_reader.getf('3f')
    direction = packed_reader.getf('3f')
    data.range_ = packed_reader.getf('f')[0]
    data.falloff = packed_reader.getf('f')[0]
    data.attenuation_0 = packed_reader.getf('f')[0]
    data.attenuation_1 = packed_reader.getf('f')[0]
    data.attenuation_2 = packed_reader.getf('f')[0]
    data.theta = packed_reader.getf('f')[0]
    data.phi = packed_reader.getf('f')[0]
    unknown = packed_reader.getf('2I')
    name = packed_reader.getf('{}s'.format(fmt.B_LIGHT_V8_NAME_LEN))

    if data.light_type == fmt.D3D_LIGHT_POINT:
        data.controller_id = 2
    elif data.light_type == fmt.D3D_LIGHT_DIRECTIONAL:
        data.controller_id = 1

    euler = mathutils.Vector((direction[0], direction[2], direction[1])).to_track_quat('Y', 'Z').to_euler('XYZ')
    light_object.location = position[0], position[2], position[1]
    light_object.rotation_euler = euler[0], euler[1], euler[2]


def import_light_dynamic_v5(packed_reader, light_object):
    data = light_object.xray.level
    data.object_type = 'LIGHT_DYNAMIC'
    light_object.xray.is_level = True
    data.light_type = packed_reader.getf('I')[0] # ???
    data.diffuse = packed_reader.getf('4f')
    data.specular = packed_reader.getf('4f')
    data.ambient = packed_reader.getf('4f')
    position = packed_reader.getf('3f')
    direction = packed_reader.getf('3f')
    data.range_ = packed_reader.getf('f')[0]
    data.falloff = packed_reader.getf('f')[0]
    data.attenuation_0 = packed_reader.getf('f')[0]
    data.attenuation_1 = packed_reader.getf('f')[0]
    data.attenuation_2 = packed_reader.getf('f')[0]
    data.theta = packed_reader.getf('f')[0]
    data.phi = packed_reader.getf('f')[0]
    unknown = packed_reader.getf('5I')

    if data.light_type == fmt.D3D_LIGHT_POINT:
        data.controller_id = 2
    elif data.light_type == fmt.D3D_LIGHT_DIRECTIONAL:
        data.controller_id = 1

    euler = mathutils.Vector((direction[0], direction[2], direction[1])).to_track_quat('Y', 'Z').to_euler('XYZ')
    light_object.location = position[0], position[2], position[1]
    light_object.rotation_euler = euler[0], euler[1], euler[2]


def create_light_object(light_index, collection):
    object_name = 'light_dynamic_{:0>3}'.format(light_index)
    light = bpy.data.lights.new(object_name, 'SPOT')
    bpy_object = create.create_object(object_name, light)
    collection.objects.link(bpy_object)
    return bpy_object


def create_lights_object(collection):
    object_name = 'light dynamic'
    bpy_object = create.create_object(object_name, None)
    collection.objects.link(bpy_object)
    return bpy_object


def import_lights_dynamic(data, level):
    packed_reader = xray_io.PackedReader(data)
    collection = level.collections[create.LEVEL_LIGHTS_COLLECTION_NAME]
    lights_dynamic_object = create_lights_object(collection)

    if level.xrlc_version >= fmt.VERSION_8:
        light_count = len(data) // fmt.LIGHT_DYNAMIC_SIZE
        for light_index in range(light_count):
            light_object = create_light_object(light_index, collection)
            import_light_dynamic(packed_reader, light_object)
            light_object.parent = lights_dynamic_object
    elif level.xrlc_version == fmt.VERSION_8:
        light_count = len(data) // fmt.LIGHT_DYNAMIC_SIZE_V8
        for light_index in range(light_count):
            light_object = create_light_object(light_index, collection)
            import_light_dynamic_v8(packed_reader, light_object)
            light_object.parent = lights_dynamic_object
    else:
        light_count = len(data) // fmt.LIGHT_DYNAMIC_SIZE_V5
        for light_index in range(light_count):
            light_object = create_light_object(light_index, collection)
            import_light_dynamic_v5(packed_reader, light_object)
            light_object.parent = lights_dynamic_object

    return lights_dynamic_object


def generate_portal_face(vertices):
    face = list(range(len(vertices)))
    return [face, ]


def create_portal_mesh(object_name, vertices):
    faces = generate_portal_face(vertices)
    mesh = bpy.data.meshes.new(object_name)
    mesh.from_pydata(vertices, (), faces)
    return mesh


def create_portal(portal_index, vertices, collection):
    object_name = 'portal_{:0>3}'.format(portal_index)
    object_data = create_portal_mesh(object_name, vertices)
    portal_object = create.create_object(object_name, object_data)
    collection.objects.link(portal_object)
    return portal_object


def import_portal(packed_reader, portal_index, collection, level):
    sector_front = packed_reader.getf('H')[0]
    sector_back = packed_reader.getf('H')[0]
    if level.xrlc_version <= fmt.VERSION_5:
        used_vertices_count = packed_reader.getf('I')[0]
    vertices = []

    for vertex_index in range(fmt.PORTAL_VERTEX_COUNT):
        coord_x, coord_y, coord_z = packed_reader.getf('fff')
        vertices.append((coord_x, coord_z, coord_y))

    if level.xrlc_version >= fmt.VERSION_8:
        used_vertices_count = packed_reader.getf('I')[0]
    vertices = vertices[ : used_vertices_count]
    portal_object = create_portal(portal_index, vertices, collection)
    portal_object.xray.is_level = True
    portal_object.xray.level.object_type = 'PORTAL'
    portal_object.xray.level.sector_front = level.sectors_objects[sector_front].name
    portal_object.xray.level.sector_back = level.sectors_objects[sector_back].name
    return portal_object


def import_portals(data, level):
    packed_reader = xray_io.PackedReader(data)
    portals_count = len(data) // fmt.PORTAL_SIZE
    portals_object = create.create_object('portals', None)
    collection = level.collections[create.LEVEL_PORTALS_COLLECTION_NAME]
    collection.objects.link(portals_object)

    for portal_index in range(portals_count):
        portal_object = import_portal(
            packed_reader, portal_index, collection, level
        )
        portal_object.parent = portals_object

    return portals_object


def check_version(xrlc_version):
    if xrlc_version not in fmt.SUPPORTED_VERSIONS:
        raise utils.AppError('Unsupported level version: {}'.format(
            xrlc_version
        ))


def import_header(data):
    packed_reader = xray_io.PackedReader(data)
    xrlc_version = packed_reader.getf('H')[0]
    check_version(xrlc_version)
    xrlc_quality = packed_reader.getf('H')[0]
    return xrlc_version


def get_chunks(chunked_reader):
    chunks = {}
    for chunk_id, chunk_data in chunked_reader:
        chunks[chunk_id] = chunk_data
    return chunks


def get_version(header_chunk_data):
    xrlc_version = import_header(header_chunk_data)
    return xrlc_version


def import_geomx(level, context):
    if level.xrlc_version == fmt.VERSION_14:
        geomx_path = context.filepath + os.extsep + 'geomx'
        if os.path.exists(geomx_path):
            geomx_chunks = {}
            geomx_chunked_reader = level_utils.get_level_reader(geomx_path)
            chunks = get_chunks(geomx_chunked_reader)
            del geomx_chunked_reader
            level.xrlc_version_geom = get_version(chunks.pop(fmt.HEADER))
            geomx_chunks.update(chunks)
            del chunks
            return geomx_chunks


def import_geom(level, chunks, context):
    if level.xrlc_version < fmt.VERSION_13:
        return
    if level.xrlc_version in fmt.SUPPORTED_VERSIONS:
        geom_chunked_reader = level_utils.get_level_reader(
            context.filepath + os.extsep + 'geom'
        )
        geom_chunks = get_chunks(geom_chunked_reader)
        del geom_chunked_reader
        level.xrlc_version_geom = get_version(geom_chunks.pop(fmt.HEADER))
        chunks.update(geom_chunks)
        del geom_chunks


def import_level(level, context, chunks, geomx_chunks):
    if level.xrlc_version >= fmt.VERSION_13:
        chunks_ids = fmt.Chunks13
    elif level.xrlc_version == fmt.VERSION_12:
        chunks_ids = fmt.Chunks12
    elif level.xrlc_version in (fmt.VERSION_11, fmt.VERSION_10):
        chunks_ids = fmt.Chunks10
    elif level.xrlc_version == fmt.VERSION_9:
        chunks_ids = fmt.Chunks9
    elif level.xrlc_version == fmt.VERSION_8:
        chunks_ids = fmt.Chunks8
    elif level.xrlc_version == fmt.VERSION_5:
        chunks_ids = fmt.Chunks5
    elif level.xrlc_version == fmt.VERSION_4:
        chunks_ids = fmt.Chunks4
    shaders_chunk_data = chunks.pop(chunks_ids.SHADERS)
    level.materials = shaders.import_shaders(level, context, shaders_chunk_data)
    del shaders_chunk_data

    if level.xrlc_version <= fmt.VERSION_5:
        textures_chunk_data = chunks.pop(chunks_ids.TEXTURES)
        shaders.import_textures(level, context, textures_chunk_data)
        del textures_chunk_data

    # geometry
    vb_chunk_data = chunks.pop(chunks_ids.VB, None)
    directx_3d_7_mode = False
    if level.xrlc_version <= fmt.VERSION_8:
        directx_3d_7_mode = True
    if not vb_chunk_data and level.xrlc_version == fmt.VERSION_9:
        directx_3d_7_mode = True
        vb_chunk_data = chunks.pop(chunks_ids.VB_OLD)
    level.vertex_buffers, stats = vb.import_vertex_buffers(
        vb_chunk_data, level, fast=False, d3d7=directx_3d_7_mode
    )
    level.stats += stats
    del vb_chunk_data

    if level.xrlc_version >= fmt.VERSION_9:
        ib_chunk_data = chunks.pop(chunks_ids.IB)
        level.indices_buffers = ib.import_indices_buffers(ib_chunk_data)
        del ib_chunk_data

    if level.xrlc_version >= fmt.VERSION_12:
        swis_chunk_data = chunks.pop(chunks_ids.SWIS, None)
        if swis_chunk_data:
            level.swis = swi.import_slide_window_items(swis_chunk_data)
            del swis_chunk_data

    # fastpath geometry
    if level.xrlc_version == fmt.VERSION_14 and geomx_chunks:
        fastpath_vb_chunk_data = geomx_chunks.pop(chunks_ids.VB)
        level.fastpath_vertex_buffers, stats = vb.import_vertex_buffers(
            fastpath_vb_chunk_data, level, fast=True
        )
        level.stats += stats
        del fastpath_vb_chunk_data

        fastpath_ib_chunk_data = geomx_chunks.pop(chunks_ids.IB)
        level.fastpath_indices_buffers = ib.import_indices_buffers(fastpath_ib_chunk_data)
        del fastpath_ib_chunk_data

        fastpath_swis_chunk_data = geomx_chunks.pop(chunks_ids.SWIS)
        level.fastpath_swis = swi.import_slide_window_items(fastpath_swis_chunk_data)
        del fastpath_swis_chunk_data

    level_collection = create.create_level_collections(level)
    level_object = create.create_level_objects(level, level_collection)

    visuals_chunk_data = chunks.pop(chunks_ids.VISUALS)
    visuals.import_visuals(visuals_chunk_data, level)
    visuals.import_hierrarhy_visuals(level)
    del visuals_chunk_data

    sectors_chunk_data = chunks.pop(chunks_ids.SECTORS)
    import_sectors(sectors_chunk_data, level, level_object)
    del sectors_chunk_data

    portals_chunk_data = chunks.pop(chunks_ids.PORTALS)
    portals_object = import_portals(portals_chunk_data, level)
    del portals_chunk_data

    portals_object.parent = level_object

    glows_chunk_data = chunks.pop(chunks_ids.GLOWS)
    if level.xrlc_version >= fmt.VERSION_12:
        glows_object = import_glows(
            glows_chunk_data, level
        )
    else:
        glows_object = import_glows_v5(
            glows_chunk_data, level
        )
    del glows_chunk_data
    glows_object.parent = level_object

    light_chunk_data = chunks.pop(chunks_ids.LIGHT_DYNAMIC)
    lights_dynamic_object = import_lights_dynamic(
        light_chunk_data, level
    )
    lights_dynamic_object.parent = level_object
    del light_chunk_data

    cform_data_v2 = None
    if level.xrlc_version <= fmt.VERSION_9:
        cform_data_v2 = chunks.pop(chunks_ids.CFORM)

    for chunk_id, chunk_data in chunks.items():
        print('UNKNOWN LEVEL CHUNK: {0:#x}, SIZE = {1}'.format(
            chunk_id, len(chunk_data)
        ))
    return cform_data_v2


def import_main(context, chunked_reader, level):
    chunks = get_chunks(chunked_reader)
    del chunked_reader
    import_geom(level, chunks, context)
    geomx_chunks = import_geomx(level, context)
    cform_data_v2 = import_level(level, context, chunks, geomx_chunks)
    if level.xrlc_version >= fmt.VERSION_10:
        cform.import_main(context, level)
    else:
        cform.import_main(context, level, data=cform_data_v2)


TEST_MODE = False
MAX_LEVEL_SIZE = 1024 * 1024 * 32    # 32 MB


def import_file(context, operator):
    build = context.filepath[48 : 48 + 4]
    index = context.filepath[36 : 36 + 2]
    level = Level()
    level.context = context
    level.usage_list = set()
    level.vertex_format_list = set()
    chunked_reader = level_utils.get_level_reader(context.filepath)
    level.name = level_utils.get_level_name(context.filepath)
    level.xrlc_version = get_version(chunked_reader.next(fmt.HEADER))
    temp_folder = 'E:\\stalker\\_TEMP\\utils\\level_format_stats\\'
    stats_name = '{0:0>2}_{1}_{2}_{3}.txt'.format(
        level.xrlc_version, build, level.name, index
    )
    if len(chunked_reader._ChunkedReader__data) > MAX_LEVEL_SIZE and TEST_MODE:
        print('skip big level:', stats_name)
        return
    stats_path = os.path.join(temp_folder, stats_name)
    if os.path.exists(stats_path) and TEST_MODE:
        print('skip:', stats_name)
        return
    if TEST_MODE:
        print(build, index, level.name)
    level.path = os.path.dirname(context.filepath)
    import_main(context, chunked_reader, level)
    if TEST_MODE:
        stats = '\nOGFs Info:\n'
        for key in level.visual_keys:
            stats += '  ' + key[0] + ': ' + ' '.join(key[1:]) + '\n'
        level.stats += stats
        with open(stats_path, 'w') as stats_file:
            stats_file.write(level.stats)
        print('\t\t', level.name)
