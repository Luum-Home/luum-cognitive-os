"""ADR-cos-lib: workflows/ must never import cos_lib modules (RISKY-edge gate)."""
import ast, pathlib, sys
sys.path.insert(0, 'scripts')
from cos_lib_rename_codemod import load_allowlist

def test_workflows_have_no_cos_lib_imports():
    allowlist = load_allowlist(pathlib.Path('.'), 'lib', 'cos_lib')
    for py in pathlib.Path('workflows').rglob('*.py'):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('lib.'):
                mod = node.module.split('.', 1)[1]
                assert mod not in allowlist, f"{py}: workflows/ imports cos_lib module '{mod}'"
