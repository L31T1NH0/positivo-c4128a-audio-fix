#!/usr/bin/env python3
"""Build and compare without root; do not install or reload any module."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

BASE = Path(__file__).resolve().parent
KVER = '7.2.11-arch1-1'


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def info(module, field):
    return subprocess.check_output(['modinfo', '-F', field, str(module)], text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if os.geteuid() == 0:
        raise SystemExit('Compile como usuário normal, sem sudo.')
    if os.uname().release != KVER:
        raise SystemExit('Este candidato é exclusivo do kernel ' + KVER)
    headers = Path('/usr/lib/modules') / KVER / 'build'
    if (headers / 'include/config/kernel.release').read_text().strip() != KVER:
        raise SystemExit('Headers diferentes do kernel em execução.')
    provenance = json.loads((BASE / 'source.json').read_text())
    for name, expected in provenance['files'].items():
        if digest(BASE / 'source' / name) != expected:
            raise SystemExit('Fonte diferente do commit revisado: ' + name)
    build = BASE / '.build'
    build.mkdir(exist_ok=True)
    for name in ('original', 'patched'):
        shutil.copytree(BASE / 'source', build / name, dirs_exist_ok=True)
    run(['patch', '--batch', '--fuzz=0', '-p3', '-d', str(build / 'patched'),
         '-i', str(BASE / 'sof-es8336-retomada-7.2.11.patch')])
    run(['patch', '--batch', '--fuzz=0', '-p3', '-d', str(build / 'patched'),
         '-i', str(BASE / 'es8326-internal-dmic.patch')])
    for name in ('original', 'patched'):
        for folder in ('intel/boards', 'codecs'):
            run(['make', '-C', str(headers), 'M=' + str(build / name / folder), 'W=1', 'modules'])
    # Explicit distribution paths also work after a previous override installation.
    stock_path = Path('/usr/lib/modules') / KVER / 'kernel/sound/soc/intel/boards/snd-soc-sof_es8336.ko.zst'
    stock = build / 'distribution.ko'
    if stock_path.suffix != '.zst':
        raise SystemExit('Compressão do módulo diferente da distribuição revisada.')
    with stock.open('wb') as output:
        run(['zstd', '-d', '-c', str(stock_path)], stdout=output)
    original = build / 'original/intel/boards/snd-soc-sof_es8336.ko'
    patched = build / 'patched/intel/boards/snd-soc-sof_es8336.ko'
    for name, module in (('stock', stock), ('original', original)):
        run(['objcopy', '--dump-section', '.text=' + str(build / (name + '.text')), str(module)])
    if (build / 'stock.text').read_bytes() != (build / 'original.text').read_bytes():
        raise SystemExit('Código executável original não corresponde ao módulo instalado; não instalar.')
    for field in ('alias', 'name', 'license', 'description', 'import_ns', 'depends', 'vermagic'):
        if not info(stock, field) == info(original, field) == info(patched, field):
            raise SystemExit('Metadado de compatibilidade mudou: ' + field)
    if info(patched, 'version') != '0.2.0-positivo-7.2.11':
        raise SystemExit('Identificador de versão local inesperado.')
    compiler = subprocess.check_output(['gcc', '--version'], text=True).splitlines()[0]
    provenance['validation'] = {
        'baseline_text_identical_to_distribution': True,
        'baseline_text_sha256': digest(build / 'stock.text'),
        'distribution_srcversion': info(stock, 'srcversion'),
        'baseline_external_srcversion': info(original, 'srcversion'),
        'patched_srcversion': info(patched, 'srcversion'),
        'patched_version': info(patched, 'version'),
        'vermagic': info(patched, 'vermagic'),
        'depends': info(patched, 'depends'),
        'compiler': compiler,
        'module_sha256': digest(patched),
        'kernel_sha256': digest(Path('/usr/lib/modules') / KVER / 'vmlinuz'),
        'hardware_test': 'this build must be validated; see hardware-confirmation.json for the tested reference',
    }
    codec_stock = build / 'codec-distribution.ko'
    codec_path = Path('/usr/lib/modules') / KVER / 'kernel/sound/soc/codecs/snd-soc-es8326.ko.zst'
    with codec_stock.open('wb') as output:
        run(['zstd', '-d', '-c', str(codec_path)], stdout=output)
    codec_original = build / 'original/codecs/snd-soc-es8326.ko'
    codec_patched = build / 'patched/codecs/snd-soc-es8326.ko'
    for name, module in (('stock', codec_stock), ('original', codec_original)):
        run(['objcopy', '--dump-section', '.text=' + str(build / ('codec-' + name + '.text')), str(module)])
    if (build / 'codec-stock.text').read_bytes() != (build / 'codec-original.text').read_bytes():
        raise SystemExit('Código original do codec difere do módulo da distribuição.')
    for field in ('alias', 'name', 'license', 'description', 'vermagic'):
        if not info(codec_stock, field) == info(codec_original, field) == info(codec_patched, field):
            raise SystemExit('Metadado do codec mudou: ' + field)
    before = set(info(codec_stock, 'depends').split(','))
    after = set(info(codec_patched, 'depends').split(','))
    if not before <= after or after - before - {'snd'}:
        raise SystemExit('Dependência inesperada no codec.')
    if info(codec_patched, 'version') != '0.1.0-positivo-dmic':
        raise SystemExit('Versão inesperada no codec.')
    provenance['codec_validation'] = {
        'baseline_text_identical_to_distribution': True,
        'baseline_text_sha256': digest(build / 'codec-stock.text'),
        'module_sha256': digest(codec_patched),
        'patched_srcversion': info(codec_patched, 'srcversion'),
        'patched_version': info(codec_patched, 'version'),
        'vermagic': info(codec_patched, 'vermagic'),
        'depends': info(codec_patched, 'depends'),
    }
    (build / 'validation.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print('Compilação e comparação concluídas. Nenhum módulo foi instalado ou recarregado.')
    print('Manifesto local:', build / 'validation.json')


if __name__ == '__main__':
    main()
