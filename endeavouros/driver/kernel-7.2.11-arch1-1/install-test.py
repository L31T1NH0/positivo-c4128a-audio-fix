#!/usr/bin/env python3
"""Prepare a separate, version-pinned GRUB experiment; never reload audio modules."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

KVER = '7.2.11-arch1-1'
ENTRY_ID = 'positivo-audio-test'
BASE = Path(__file__).resolve().parent
STATE = Path('/var/lib/positivo-audio/driver-test-' + KVER)
SCRIPT = Path('/etc/grub.d/42_positivo_audio_test')
BOOT = Path('/boot/positivo-audio-' + KVER)
KERNEL = BOOT / 'vmlinuz'
IMAGE = Path('/boot/positivo-audio-' + KVER) / 'initramfs.img'
CFG = Path('/boot/grub/grub.cfg')
MODULE_REL = Path('usr/lib/modules') / KVER / 'kernel/sound/soc/intel/boards/snd-soc-sof_es8336.ko.zst'


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if os.geteuid() != 0:
        raise SystemExit('Execute com sudo.')
    if os.uname().release != KVER:
        raise SystemExit('O kernel em execução não é o kernel revisado.')
    if Path('/sys/class/dmi/id/product_name').read_text().strip() != 'C4128A-15':
        raise SystemExit('Modelo diferente do equipamento revisado.')
    for target in (STATE, SCRIPT, BOOT, KERNEL, IMAGE):
        if target.exists() or target.is_symlink():
            raise SystemExit('Destino já existe; revise antes de repetir: ' + str(target))
    validation = json.loads((BASE / '.build/validation.json').read_text())['validation']
    module = BASE / '.build/patched/intel/boards/snd-soc-sof_es8336.ko'
    kernel_source = Path('/usr/lib/modules') / KVER / 'vmlinuz'
    if sha(module) != validation['module_sha256'] or sha(kernel_source) != validation['kernel_sha256']:
        raise SystemExit('O módulo/kernel mudou desde a validação.')
    stock_module = Path(subprocess.check_output(['modinfo', '-n', 'snd_soc_sof_es8336'], text=True).strip())
    original_paths = [Path('/boot/vmlinuz-linux'), Path('/boot/initramfs-linux.img'),
                      Path('/boot/initramfs-linux-fallback.img'), stock_module]
    original_hashes = {str(p): sha(p) for p in original_paths}
    content = CFG.read_text()
    match = re.search(r"^menuentry 'EndeavourOS Linux'.*?^}", content, re.M | re.S)
    if not match:
        raise SystemExit('Entrada padrão do GRUB diferente da revisada.')
    block = match.group()
    if not re.search(r'^\s*linux\s+/boot/vmlinuz-linux\s', block, re.M):
        raise SystemExit('Caminho do kernel no GRUB diferente do revisado.')
    if block.count('/boot/initramfs-linux.img') != 1:
        raise SystemExit('Imagem de inicialização padrão diferente da revisada.')
    lines = block.splitlines()
    lines[0] = "menuentry 'EndeavourOS - teste audio Positivo (7.2.11)' --id positivo-audio-test {"
    block = '\n'.join(lines)
    block = re.sub(r'(^\s*linux\s+)/boot/vmlinuz-linux(?=\s)',
                   lambda m: m.group(1) + str(KERNEL), block, flags=re.M)
    block = block.replace('/boot/initramfs-linux.img', str(IMAGE))
    STATE.mkdir(parents=True, mode=0o700)
    shutil.copy2(BASE / 'remove-test.py', STATE / 'remove-test.py')
    BOOT.mkdir(mode=0o755)
    shutil.copy2(CFG, STATE / 'grub.cfg.before')
    shutil.copy2('/boot/grub/grubenv', STATE / 'grubenv.before')
    (STATE / 'original-hashes.json').write_text(json.dumps(original_hashes, indent=2))
    shutil.copy2(BASE / '.build/validation.json', STATE / 'validation.json')
    overlay = STATE / 'overlay'
    bundled_module = overlay / MODULE_REL
    bundled_module.parent.mkdir(parents=True)
    run(['zstd', '-q', '-f', str(module), '-o', str(bundled_module)])
    print('Gerando imagem de teste separada; os arquivos do boot normal serão preservados.', flush=True)
    with (STATE / 'dracut.log').open('w') as log:
        run(['dracut', '--kver', KVER, '--nostrip', '--nohardlink',
             '--force-drivers', 'snd_soc_sof_es8336', '--include', str(overlay), '/',
             str(IMAGE)], stdout=log, stderr=subprocess.STDOUT)
    extracted = subprocess.check_output(['lsinitrd', '-f', str(MODULE_REL), str(IMAGE)])
    if hashlib.sha256(extracted).hexdigest() != sha(bundled_module):
        raise RuntimeError('O módulo dentro da imagem não corresponde ao módulo compilado.')
    pre = subprocess.check_output(['lsinitrd', '-f', 'etc/cmdline.d/20-force_drivers.conf', str(IMAGE)], text=True)
    if 'rd.driver.pre=snd_soc_sof_es8336' not in pre:
        raise RuntimeError('A imagem não garante o carregamento antecipado do módulo de teste.')
    print('Imagem conferida: módulo corrigido incluído e pré-carregamento configurado.', flush=True)
    shutil.copy2(kernel_source, KERNEL)
    script = "#!/bin/sh\n# Positivo audio: isolated test, original boot remains available.\ncat <<'POSITIVO_GRUB_ENTRY'\n" + block + "\nPOSITIVO_GRUB_ENTRY\n"
    SCRIPT.write_text(script)
    SCRIPT.chmod(0o755)
    new_cfg = Path('/boot/grub/grub.cfg.positivo-new')
    with (STATE / 'grub-mkconfig.log').open('w') as log:
        run(['grub-mkconfig', '-o', str(new_cfg)], stdout=log, stderr=subprocess.STDOUT)
    run(['grub-script-check', str(new_cfg)])
    standard = re.search(r"^menuentry 'EndeavourOS Linux'.*?^}", new_cfg.read_text(), re.M | re.S)
    if not standard or standard.group() != match.group():
        raise RuntimeError('A entrada padrão foi alterada pelo gerador do GRUB.')
    if ENTRY_ID not in new_cfg.read_text():
        raise RuntimeError('Entrada de teste não foi incluída no GRUB.')
    for path, expected in original_hashes.items():
        if sha(Path(path)) != expected:
            raise RuntimeError('Arquivo do sistema original mudou: ' + path)
    os.replace(new_cfg, CFG)
    shutil.copy2(BASE / 'remove-test.py', STATE / 'remove-test.py')
    print('Entrada de teste instalada. O boot padrão NÃO foi alterado.', flush=True)
    print('Para testar uma única inicialização: sudo grub-reboot positivo-audio-test', flush=True)
    print('Reversão: sudo python3 ' + str(STATE / 'remove-test.py'), flush=True)


if __name__ == '__main__':
    main()
