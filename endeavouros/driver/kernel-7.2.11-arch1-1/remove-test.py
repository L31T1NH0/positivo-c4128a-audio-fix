#!/usr/bin/env python3
"""Remove only this experiment; never unload an active sound module."""
import os
from pathlib import Path
import subprocess

KVER = '7.2.11-arch1-1'
SCRIPT = Path('/etc/grub.d/42_positivo_audio_test')
IMAGE = Path('/boot/positivo-audio-' + KVER) / 'initramfs.img'
BOOT = Path('/boot/positivo-audio-' + KVER)
KERNEL = BOOT / 'vmlinuz'
CFG = Path('/boot/grub/grub.cfg')


def main():
    if os.geteuid() != 0:
        raise SystemExit('Execute com sudo.')
    if SCRIPT.is_symlink() or (SCRIPT.exists() and 'Positivo audio: isolated test' not in SCRIPT.read_text()):
        raise SystemExit('O script do GRUB foi substituído; revise antes de remover.')
    env = subprocess.check_output(['grub-editenv', '/boot/grub/grubenv', 'list'], text=True)
    if 'next_entry=positivo-audio-test' in env.splitlines():
        subprocess.run(['grub-editenv', '/boot/grub/grubenv', 'unset', 'next_entry'], check=True)
    SCRIPT.unlink(missing_ok=True)
    new_cfg = Path('/boot/grub/grub.cfg.positivo-remove')
    subprocess.run(['grub-mkconfig', '-o', str(new_cfg)], check=True)
    subprocess.run(['grub-script-check', str(new_cfg)], check=True)
    os.replace(new_cfg, CFG)
    IMAGE.unlink(missing_ok=True)
    KERNEL.unlink(missing_ok=True)
    if BOOT.exists() and not any(BOOT.iterdir()):
        BOOT.rmdir()
    print('Entrada e imagens de teste removidas. O driver original em disco permanece intacto.')
    print('Se esta sessão usa o módulo de teste, reinicie para carregar o original.')


if __name__ == '__main__':
    main()
