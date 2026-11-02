#!/usr/bin/env python3
"""Persist only the two exact modules verified in the isolated boot."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

KVER = '7.2.11-arch1-1'
TEST = Path('/var/lib/positivo-audio/driver-test-' + KVER)
STATE = Path('/var/lib/positivo-audio/permanente-' + KVER)
UPDATES = Path('/usr/lib/modules') / KVER / 'updates/positivo-audio'
CONF = Path('/etc/dracut.conf.d/positivo-audio.conf')
NORMAL = Path('/boot/initramfs-linux.img')
STAGED = Path('/boot/initramfs-linux-positivo-staged.img')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    if os.geteuid() != 0 or os.uname().release != KVER:
        raise SystemExit('Exige root e o kernel revisado ' + KVER)
    if Path('/sys/class/dmi/id/product_name').read_text().strip() != 'C4128A-15':
        raise SystemExit('Modelo diferente.')
    for path in (STATE, UPDATES, CONF, STAGED):
        if path.exists() or path.is_symlink():
            raise SystemExit('Destino já existe; revisar antes de repetir: ' + str(path))
    modules = [
        ('snd_soc_sof_es8336', 'intel/boards/snd-soc-sof_es8336.ko.zst', '0.2.0-positivo-7.2.11'),
        ('snd_soc_es8326', 'codecs/snd-soc-es8326.ko.zst', '0.1.0-positivo-dmic'),
    ]
    originals = {}
    validated = {}
    for name, relative, version in modules:
        source = TEST / 'overlay/usr/lib/modules' / KVER / 'kernel/sound/soc' / relative
        assert Path('/sys/module', name, 'version').read_text().strip() == version
        disk_version = subprocess.check_output(['modinfo', '-F', 'version', str(source)], text=True).strip()
        srcversion = subprocess.check_output(['modinfo', '-F', 'srcversion', str(source)], text=True).strip()
        assert disk_version == version
        assert srcversion == Path('/sys/module', name, 'srcversion').read_text().strip()
        original = Path(subprocess.check_output(['modinfo', '-n', name], text=True).strip())
        assert '/kernel/sound/soc/' in str(original)
        originals[str(original)] = sha(original)
        validated[name] = {'version': version, 'srcversion': srcversion, 'file': Path(relative).name, 'sha256': sha(source)}
    STATE.mkdir(parents=True, mode=0o700)
    report = {'kernel': KVER, 'kernel_sha256': sha('/boot/vmlinuz-linux'),
              'modules': validated, 'original_modules': originals,
              'normal_initramfs_original_sha256': sha(NORMAL)}
    (STATE / 'manifest.json').write_text(json.dumps(report, indent=2))
    shutil.copy2(NORMAL, STATE / 'initramfs-linux.original.img')
    shutil.copy2('/boot/grub/grub.cfg', STATE / 'grub.cfg.before')
    shutil.copy2(Path(__file__).parent / 'reverter-persistent.py', STATE / 'reverter.py')
    UPDATES.mkdir(parents=True)
    for name, relative, version in modules:
        source = TEST / 'overlay/usr/lib/modules' / KVER / 'kernel/sound/soc' / relative
        shutil.copy2(source, UPDATES / Path(relative).name)
    run(['depmod', '-a', KVER])
    for name, relative, version in modules:
        selected = Path(subprocess.check_output(['modinfo', '-n', name], text=True).strip()).resolve()
        assert selected == (UPDATES / Path(relative).name).resolve()
        assert sha(selected) == validated[name]['sha256']
    CONF.write_text('# Positivo audio: version-pinned tested modules; original modules kept on disk.\nforce_drivers+=" snd_soc_es8326 snd_soc_sof_es8336 "\n')
    print('Gerando a imagem de boot normal com os dois módulos já testados.', flush=True)
    with (STATE / 'dracut.log').open('w') as log:
        run(['dracut', '--kver', KVER, '--nostrip', '--nohardlink', str(STAGED)], stdout=log, stderr=subprocess.STDOUT)
    for name, relative, version in modules:
        internal = Path('usr/lib/modules') / KVER / 'updates/positivo-audio' / Path(relative).name
        data = subprocess.check_output(['lsinitrd', '-f', str(internal), str(STAGED)])
        assert hashlib.sha256(data).hexdigest() == validated[name]['sha256']
    for path, digest in originals.items():
        assert sha(path) == digest, 'Módulo original alterado: ' + path
    assert sha('/boot/vmlinuz-linux') == report['kernel_sha256']
    os.replace(STAGED, NORMAL)
    print('Boot normal preparado e verificado; módulos originais preservados.', flush=True)
    # This existing remover only deletes the isolated menu/images; it never unloads drivers.
    with (STATE / 'remove-test.log').open('w') as log:
        run(['python3', str(TEST / 'remove-test.py')], stdout=log, stderr=subprocess.STDOUT)
    run(['grub-script-check', '/boot/grub/grub.cfg'])
    assert '--id positivo-audio-test' not in Path('/boot/grub/grub.cfg').read_text()
    print('Entrada experimental removida. Reversão: sudo python3 ' + str(STATE / 'reverter.py'), flush=True)


if __name__ == '__main__':
    main()
