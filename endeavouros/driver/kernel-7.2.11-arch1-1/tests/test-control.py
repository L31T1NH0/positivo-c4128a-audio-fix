#!/usr/bin/env python3
"""Exercise the actual patched C functions using small ALSA/regmap test doubles."""
from pathlib import Path
import subprocess

base = Path(__file__).resolve().parent.parent
source = base / '.build/patched/codecs/es8326.c'
if not source.exists():
    raise SystemExit('Execute build.py primeiro.')
text = source.read_text()
start = text.index('/* Caller holds es8326->lock, including the jack worker and control put. */')
end = text.index('static const struct snd_kcontrol_new es8326_snd_controls[]', start)
functions = text[start:end]
test = base / '.build/test-control.c'
test.write_text((base / 'tests/test-control-prefix.c').read_text()
                + functions + (base / 'tests/test-control-main.c').read_text())
binary = base / '.build/test-control'
subprocess.run(['gcc', '-Wall', '-Wextra', '-Werror', '-O2', str(test), '-o', str(binary)], check=True)
subprocess.run([str(binary)], check=True)
