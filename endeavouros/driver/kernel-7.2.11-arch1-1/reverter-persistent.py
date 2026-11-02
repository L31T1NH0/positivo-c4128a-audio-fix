#!/usr/bin/env python3
"""Restore the original modules for the reviewed kernel, without live unloading."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

KVER = '7.2.11-arch1-1'
STATE = Path('/var/lib/positivo-audio/permanente-' + KVER)
UPDATES = Path('/usr/lib/modules') / KVER / 'updates/positivo-audio'
CONF = Path('/etc/dracut.conf.d/positivo-audio.conf')


def main():
    if os.geteuid() != 0:
        raise SystemExit('Execute com sudo.')
    report = json.loads((STATE / 'manifest.json').read_text())
    sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if sha('/boot/vmlinuz-linux') != report['kernel_sha256']:
        raise SystemExit('O kernel padrão mudou; não restaurar uma imagem antiga sem revisar.')
    for item in report['modules'].values():
        module = UPDATES / item['file']
        if module.exists() and sha(module) != item['sha256']:
            raise SystemExit('A sobreposição foi modificada; revisar antes de remover.')
    if CONF.exists() and 'Positivo audio: version-pinned tested modules' not in CONF.read_text():
        raise SystemExit('A configuração do dracut foi modificada; revisar antes de remover.')
    backup = STATE / 'initramfs-linux.original.img'
    assert sha(backup) == report['normal_initramfs_original_sha256']
    for item in report['modules'].values():
        (UPDATES / item['file']).unlink(missing_ok=True)
    if UPDATES.exists() and not any(UPDATES.iterdir()):
        UPDATES.rmdir()
    CONF.unlink(missing_ok=True)
    subprocess.run(['depmod', '-a', KVER], check=True)
    target = Path('/boot/initramfs-linux.positivo-restore')
    shutil.copy2(backup, target)
    os.replace(target, '/boot/initramfs-linux.img')
    print('Originais restaurados em disco. Reinicie para carregá-los; nenhum módulo foi recarregado agora.')


if __name__ == '__main__':
    main()
