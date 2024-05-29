import glob
import importlib
from os.path import basename, dirname, isfile, join

def auto_import():
    modules = glob.glob(join(dirname(__file__), "..", "*.py"))
    python_files_to_import = [basename(f)
                              for f in modules if isfile(f) and not f.startswith('__') and f != 'main.py']
    for py_file in python_files_to_import:
        module_name = py_file.removesuffix('.py')
        try:
            importlib.import_module(module_name)
        except Exception as e:
            print(f'ignore {module_name} ({py_file}), error:\n{e}')
            with open(f'{py_file}.error', 'w') as f:
                f.write(str(e))
