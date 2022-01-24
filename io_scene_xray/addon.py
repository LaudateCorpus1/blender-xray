from . import plugins
from . import ui
from . import menus
from . import panels
from . import prefs
from . import hotkeys
from . import ops
from . import rig
from . import props
from . import icons
from . import handlers
from . import viewport
from . import skls_browser
from . import edit_helpers
from . import viewer
from . import xrlc
from . import translate
from . import tests


modules = (
    icons,
    prefs,
    skls_browser,
    viewer,
    xrlc,
    props,
    plugins,
    handlers,
    ui,
    panels,
    menus,
    hotkeys,
    ops,
    rig,
    edit_helpers,
    viewport,
    translate,
    tests
)


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
