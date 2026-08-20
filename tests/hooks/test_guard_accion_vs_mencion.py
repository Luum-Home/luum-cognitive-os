# SCOPE: os-only
"""Actuar sobre una ruta protegida vs mencionarla: la bateria de pares.

Un solo caso no prueba una distincion. Cada test de aqui es un PAR con la misma
forma sintactica sobre el MISMO archivo protegido: la mitad que lee tiene que
pasar y la mitad que escribe tiene que seguir bloqueada. Si un cambio en el
guard afloja de mas, el par se parte por el lado de la escritura y el test lo
dice; si afloja de menos, se parte por el lado de la lectura.

Medido 2026-08-20 sobre los transcripts de sesion con
`scripts/audit_guard_mention_blocks.py`: 66 bloqueos, 50 decididos por el texto
de un comando de Bash. La familia mas grande que quedaba en pie despues del
arreglo de heredocs del 2026-08-19 eran los programas pasados con `-c`, que el
guard nunca miraba: siete bloqueos sobre programas que solo leian.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GUARD = REPO / "hooks" / "protected-config-write-guard.sh"

BLOCK = 2
ALLOW = 0


def veredicto(comando: str) -> int:
    """Codigo de salida del guard para ese comando. Read-only: solo imprime."""
    env = dict(os.environ)
    env.pop("COS_ALLOW_PROTECTED_CONFIG_WRITE", None)
    env["CLAUDE_PROJECT_DIR"] = str(REPO)
    proc = subprocess.run(
        ["/bin/bash", str(GUARD)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": comando}}),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO),
    )
    return proc.returncode


SETTINGS = ".claude/" + "settings.json"
REGLAS = "rules/" + "RULES-COMPACT.md"
GANCHO = "hooks/" + "zzz.sh"

# (etiqueta, comando que LEE, comando que ESCRIBE)
PARES = [
    (
        "python -c con json.load",
        'python3 -c "import json;print(len(json.load(open(%r))))"' % SETTINGS,
        'python3 -c "import json;json.dump({}, open(%r, %s))"' % (SETTINGS, repr("w")),
    ),
    (
        "python -c con pathlib",
        'python3 -c "from pathlib import Path;print(len(Path(%r).read_text()))"' % REGLAS,
        'python3 -c "from pathlib import Path;Path(%r).write_text(%s)"' % (REGLAS, repr("x")),
    ),
    (
        "interprete del venv, no solo python3",
        '.venv/bin/python -c "print(open(%r).read())"' % GANCHO,
        '.venv/bin/python -c "open(%r, %s).write(%s)"' % (GANCHO, repr("a"), repr("x")),
    ),
    (
        "os.path.exists vs os.remove",
        'python3 -c "import os;print(os.path.exists(%r))"' % GANCHO,
        'python3 -c "import os;os.remove(%r)"' % GANCHO,
    ),
    (
        "cp: el protegido como origen vs como destino",
        "cp hooks/destructive-git-blocker.sh /tmp/dgb.sh",
        "cp /tmp/dgb.sh hooks/destructive-git-blocker.sh",
    ),
    (
        "cp con varios origenes, destino directorio",
        "cp hooks/a.sh hooks/b.sh /tmp/",
        "cp /tmp/a.sh /tmp/b.sh hooks/",
    ),
    (
        "install conserva la misma gramatica",
        "install -m 755 hooks/x.sh /tmp/x.sh",
        "install -m 755 /tmp/x.sh hooks/x.sh",
    ),
    (
        "heredoc: leer vs escribir el mismo archivo",
        "python3 - <<%s\nimport json\nprint(json.load(open(%r)))\nPY" % ("<<PY>>".replace("<<", "'").replace(">>", "'"), SETTINGS),
        "python3 - <<%s\nfrom pathlib import Path\nPath(%r).write_text(%s)\nPY" % ("<<PY>>".replace("<<", "'").replace(">>", "'"), GANCHO, repr("evil")),
    ),
]


@pytest.mark.parametrize("etiqueta,lectura,escritura", PARES, ids=[p[0] for p in PARES])
def test_par_lectura_pasa_escritura_bloquea(etiqueta, lectura, escritura):
    assert veredicto(lectura) == ALLOW, "la lectura tendria que pasar: %s" % lectura
    assert veredicto(escritura) == BLOCK, "la escritura tendria que bloquear: %s" % escritura


# --- Los casos que NO se relajaron, con el motivo ----------------------------

NO_SE_RELAJAN = [
    # mv borra su origen, asi que mueve el archivo protegido aunque el destino
    # sea inocente. Los dos lados siguen fallando cerrado.
    ("mv saca el archivo protegido de su lugar", "mv hooks/x.sh /tmp/x.sh"),
    # -m no trae el cuerpo del modulo en el texto del comando: no hay nada
    # chequeable, asi que no hay pase.
    ("python -m es opaco", "python3 -m algunmodulo %s" % REGLAS),
    # Un script en disco tampoco: su texto no esta aca.
    ("un script en disco es opaco", "python3 herramienta.py %s" % REGLAS),
    # El programa lleva una expansion que este scanner no hace, asi que el texto
    # que se juzga no es el que correria.
    ("programa con variable sin expandir", 'python3 -c "$PROG" %s' % REGLAS),
    # La redireccion se juzga aparte del comando, y tiene que seguir haciendolo.
    ("redireccion a ruta protegida", 'python3 -c "print(1)" > %s' % GANCHO),
    # rsync que borra el origen no es una copia.
    ("rsync que borra el origen", "rsync -a --remove-source-files hooks/ /tmp/h/"),
]


@pytest.mark.parametrize("etiqueta,comando", NO_SE_RELAJAN, ids=[c[0] for c in NO_SE_RELAJAN])
def test_lo_que_sigue_bloqueado(etiqueta, comando):
    assert veredicto(comando) == BLOCK, "tendria que seguir bloqueado: %s" % comando


def test_la_redireccion_a_ruta_no_protegida_pasa():
    assert veredicto('python3 -c "print(1)" > /tmp/salida') == ALLOW


# --- La direccion que importa: escrituras que NO pueden colarse --------------
#
# Aflojar el veredicto de un interprete abre una pregunta nueva: que pasa con un
# programa que no escribe EL MISMO, sino que le pasa el trabajo a otro proceso o
# se arma en runtime. Ahi el texto ya no contesta nada, asi que la respuesta es
# escritura. Sin estos casos, el pase de `-c` habria sido un agujero: un
# `os.system` no llevaba ninguna primitiva de escritura de la lista.

FUGAS = [
    ("os.system delega el write", 'python3 -c "import os;os.system(%s)"' % repr("echo x > " + GANCHO)),
    ("subprocess delega el write", 'python3 -c "import subprocess;subprocess.run([%s,%s,%s])"' % (repr("cp"), repr("/tmp/x"), repr(GANCHO))),
    ("shutil.copyfile", 'python3 -c "import shutil;shutil.copyfile(%s,%s)"' % (repr("/tmp/x"), repr(GANCHO))),
    ("exec de codigo armado", 'python3 -c "exec(%s)"' % repr("open('" + GANCHO + "','w')")),
    ("os.open con flags", 'python3 -c "import os;os.open(%s, os.O_WRONLY)"' % repr(GANCHO)),
    ("modo de apertura en variable", 'python3 -c "m=%s;open(%s, m)"' % (repr("w"), repr(GANCHO))),
    ("heredoc que delega en un proceso", "python3 - <<%s\nimport os\nos.system(%s)\nPY" % ("<<PY>>".replace("<<", "'").replace(">>", "'"), repr("echo x > " + GANCHO))),
]


@pytest.mark.parametrize("etiqueta,comando", FUGAS, ids=[c[0] for c in FUGAS])
def test_ninguna_escritura_delegada_se_cuela(etiqueta, comando):
    assert veredicto(comando) == BLOCK, "esta escritura se colo: %s" % comando
