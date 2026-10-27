# The End editor runs this at startup (Content/Python/init_unreal.py): the Rebirth FX menu.
import unreal

try:
    import rebirth_fx.editor as _rebirth_fx
    _rebirth_fx.register_menus()
except Exception as _ex:
    import traceback as _tb
    unreal.log_warning('[Rebirth FX] menu not added: ' + _tb.format_exc())
