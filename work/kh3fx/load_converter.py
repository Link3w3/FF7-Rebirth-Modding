import sys
import unreal
result = {}
result['before'] = hasattr(unreal, 'FXConverterUtilitiesLibrary')
ok = None
try:
    ok = unreal.SystemLibrary.execute_console_command(None, 'Module Load CascadeToNiagaraConverter')
except Exception as e:
    result['cmd_err'] = str(e)
result['after'] = hasattr(unreal, 'FXConverterUtilitiesLibrary')
result['plugin_like'] = [n for n in dir(unreal) if 'Converter' in n or 'FXConverter' in n][:20]
