# EndeavourOS · WirePlumber 0.5

[← Voltar à escolha de ambiente](../README.md)

**Configuração de sessão para alto-falantes e microfone, usando o driver da distribuição.**

O [patch experimental para o kernel 7.2.11](driver/kernel-7.2.11-arch1-1/README.md)
é um caminho separado: compilou, mas ainda aguarda teste de hardware após boot.

Configuração de sessão para **Positivo C4128A-15**, codec **ESSX8326**, placa
`sofessx8336`. Complementa a publicação original com uma alternativa para
EndeavourOS e WirePlumber 0.5. Os arquivos estão em
[`config/`](config/).

## Ambiente e resultado observado

Em **01/11/2026**, no EndeavourOS:

- Kernel `7.2.11-arch1-1`, usando o módulo original da distribuição.
- PipeWire 1.6.10, WirePlumber 0.5.18, ALSA UCM 1.2.16.1.
- Firmware SOF instalado: 2026.09.2-1.
- Perfil ACP com reprodução e captura no PCM 0.
- O usuário confirmou que a onda de captura acompanhava sua voz.
- Os ponteiros de reprodução e captura avançaram simultaneamente a aproximadamente
  48.000 quadros/s, inclusive após encerrar os clientes de teste.

Isso confirmou resposta à voz e transporte simultâneo de áudio naquela sessão.
Em **02/11/2026**, após reiniciar, a saída voltou a ficar silenciosa apesar dos
fluxos em avanço: o amplificador estava desligado fisicamente, enquanto DAPM e
`Speaker` indicavam ligado. O rearme pelo mixer recuperou o som, confirmado pelo
usuário. A captura de voz não foi revalidada nesse reboot. Não houve validação
prolongada de chamadas, qualidade/inteligibilidade ou suspensão.

## Recorrência do amplificador e recuperação

A configuração de sessão é um contorno e não resolveu definitivamente a retomada
do amplificador. O `positivo-audio-init` agora força `Speaker off/on` no login para
gerar uma transição DAPM, mesmo quando o controle já aparece ligado.

Se a reprodução voltar a ficar silenciosa com fluxos em avanço, execute como
usuário normal, na raiz do repositório:

```sh
sh endeavouros/scripts/retomar-audio.sh
```

O comando apenas rearma `Speaker` pelo mixer; não recarrega módulos nem reinicia
os serviços. Isso não corrige a causa no driver nem impede toda recorrência.
O [patch 7.2.11](driver/kernel-7.2.11-arch1-1/README.md) tenta corrigir o ponto de
retomada no driver e usa uma entrada de boot experimental separada. Ele ainda
**não foi validado com o módulo corrigido carregado**.

## O problema e o contorno

Havia dois problemas diferentes: o perfil original oferecia somente reprodução e
desligava o microfone; ao reativar a captura, o PCM compartilhado também pôde travar
depois de fechar e reabrir fluxos. Nesse caso, o sistema exibia `RUNNING`, mas os
ponteiros `hw_ptr` não avançavam. Receber alguns dados PCM, isoladamente, não
comprova que o microfone capte voz.

A configuração mantém o perfil restrito ao PCM 0, ignora a detecção incorreta de
fone para seleção de perfil e aplica **aos dois nós**, saída e entrada:

```ini
session.suspend-timeout-seconds = 0
node.pause-on-idle = false
```

Isso mantém os dispositivos abertos após o uso e evita o ciclo de suspensão e
reabertura. O mixer habilita o microfone interno, desliga a rota de headset e
inicializa `ADC=191,191` e `ADC PGA=0,0` (0 dB nos controles observados), substituindo
níveis que somavam até 40 dB. O nível percebido depende do equipamento/aplicativo.

Não foi isolada a causa no driver. O contorno foi aplicado com reinício dos
serviços da sessão, **sem instalar DKMS, modificar registradores I2C ou aplicar
parâmetro de módulo na inicialização**. Comparações transitórias de rotas feitas
durante a investigação foram revertidas e não fazem parte da instalação publicada.

## Antes de instalar

Use como usuário normal, sem `sudo`, na raiz do repositório. Confirme:

```sh
cat /sys/class/dmi/id/product_name
uname -r
wireplumber --version
cat /proc/asound/cards
```

O modelo deve ser `C4128A-15`, o WirePlumber deve ser 0.5 e a placa deve incluir
`sofessx8336`. No EndeavourOS/Arch, os comandos usados pertencem aos pacotes
`alsa-utils`, `libpulse`, `pipewire`, `pipewire-pulse`, `wireplumber` e `python`.
Instale dependências ausentes pelo gerenciador da distribuição. Não execute os
comandos `apt`, DKMS ou `update-initramfs` da seção antiga no EndeavourOS.

Revise configurações ALSA/PipeWire personalizadas existentes que possam conflitar.
O procedimento abaixo recusa links simbólicos nos arquivos que precisa substituir.
Ele pressupõe um caminho de usuário convencional, sem espaços, aspas ou caracteres
especiais, e não instala nada fora da pasta do usuário.

## Instalar com backup

O trecho salva as versões anteriores dos quatro arquivos e, quando possível, o
estado do mixer. **Guarde o caminho do backup impresso ao final.** A configuração
original para WirePlumber 0.4 permanece no repositório; não a copie neste ambiente.

```sh
python3 - <<'INSTALL'
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

if os.geteuid() == 0:
    raise SystemExit('Execute como usuário normal, sem sudo.')
home = Path.home()
if not re.fullmatch(r'/[A-Za-z0-9_./-]+', str(home)):
    raise SystemExit('Adapte os templates para o seu caminho de usuário.')
if Path('/sys/class/dmi/id/product_name').read_text().strip() != 'C4128A-15':
    raise SystemExit('Modelo diferente do equipamento testado.')
version = subprocess.check_output(['wireplumber', '--version'], text=True)
if not re.search(r'libwireplumber 0[.]5[.]', version):
    raise SystemExit('Esta configuração exige WirePlumber 0.5.')
source = Path('endeavouros/config')
files = {
    '.config/positivo-audio/profile.conf': 'profile.conf',
    '.config/wireplumber/wireplumber.conf.d/51-positivo-audio.conf': '51-positivo-audio.conf',
    '.config/systemd/user/wireplumber.service.d/positivo-audio.conf': 'positivo-audio.conf',
    '.local/bin/positivo-audio-init': 'positivo-audio-init',
}
contents = {rel: (source / name).read_text().replace('@HOME@', str(home))
            for rel, name in files.items()}
for rel in files:
    if (home / rel).is_symlink():
        raise SystemExit(f'Revise o link simbólico antes de instalar: {rel}')
state = home / '.local/state/positivo-audio'
state.mkdir(parents=True, exist_ok=True)
backup = Path(tempfile.mkdtemp(prefix='wp05-', dir=state))
manifest = {}
for rel in files:
    target = home / rel
    manifest[rel] = target.exists()
    if target.exists():
        copy = backup / rel
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, copy)
(backup / 'manifest.json').write_text(json.dumps(manifest, indent=2))
subprocess.run(['alsactl', '-f', str(backup / 'mixer.state'), 'store', 'sofessx8336'], check=True)
for rel, content in contents.items():
    target = home / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
(home / '.local/bin/positivo-audio-init').chmod(0o755)
print('Backup:', backup)
INSTALL
```

Pare se o trecho acima falhar. O próximo comando interrompe os fluxos de áudio;
reabra a mídia e reconecte os aplicativos de captura depois:

```sh
systemctl --user daemon-reload
systemctl --user restart pipewire pipewire-pulse wireplumber
```

Depois que a placa aparecer em `wpctl status`, selecione o perfil e a entrada:

```sh
pactl set-card-profile alsa_card.pci-0000_00_0e.0-platform-sof-essx8336 positivo-duplex
pactl set-default-source alsa_input.pci-0000_00_0e.0-platform-sof-essx8336.positivo-mic
```

O segundo comando muda a entrada padrão da sessão. Aplicativos que já estavam
abertos podem precisar que você selecione o microfone novamente. Comece os testes
de reprodução com volume baixo. Não é necessário descarregar módulos do kernel.

## Validar com voz e mídia

1. Abra um gravador, visualizador de entrada ou aplicativo de chamada. Selecione
   **Microfone interno (Positivo)** e fale perto do notebook, sem música tocando.
2. Confirme que o sinal acompanha a voz e diminui no silêncio. Uma onda constante
   de ruído ou um nó listado como ativo não confirma funcionamento.
3. Se quiser avaliar inteligibilidade, grave uma frase localmente e ouça a gravação.
4. Teste reprodução junto com captura, feche e reabra os aplicativos e verifique
   se os alto-falantes continuam funcionando. Valide também após o próximo reboot.

Para diagnóstico, leia os arquivos abaixo duas vezes, com um segundo de intervalo,
**enquanto os fluxos estiverem ativos**, e compare `hw_ptr`:

```sh
cat /proc/asound/card0/pcm0p/sub0/status
cat /proc/asound/card0/pcm0c/sub0/status
```

Adapte `card0` se a numeração da placa mudar. Se os ponteiros congelarem, tente
reiniciar os três serviços de áudio e reconecte os clientes. Se não recuperar,
salve seu trabalho e reinicie o computador.

**Não use remoção/reinserção do módulo nem unbind/rebind do controlador PCI como
rotina de recuperação.** Na investigação deste kernel, a recarga da placa falhou
com erro de topologia e uma tentativa posterior de unbind atingiu uma falha no
kernel SOF, exigindo reboot. Nenhum desses comandos é necessário para instalar
esta configuração de sessão.

## Reverter

Use o caminho de backup impresso na instalação. O trecho restaura versões
anteriores e remove apenas arquivos que não existiam antes. Ele também confere os
destinos registrados no manifesto antes de modificar a configuração.

```sh
python3 - /CAMINHO/DO/BACKUP <<'RESTORE'
import json
from pathlib import Path
import shutil
import sys

home = Path.home()
backup = Path(sys.argv[1])
manifest = json.loads((backup / 'manifest.json').read_text())
expected = {
    '.config/positivo-audio/profile.conf',
    '.config/wireplumber/wireplumber.conf.d/51-positivo-audio.conf',
    '.config/systemd/user/wireplumber.service.d/positivo-audio.conf',
    '.local/bin/positivo-audio-init',
}
if set(manifest) != expected or not all(type(value) is bool for value in manifest.values()):
    raise SystemExit('Manifesto de backup inválido.')
for rel, existed in manifest.items():
    if (home / rel).is_symlink() or (existed and not (backup / rel).is_file()):
        raise SystemExit(f'Revise o destino/backup: {rel}')
for rel, existed in manifest.items():
    target = home / rel
    if existed:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup / rel, target)
    else:
        target.unlink(missing_ok=True)
RESTORE
systemctl --user daemon-reload
systemctl --user restart pipewire pipewire-pulse wireplumber
```

Se necessário, selecione novamente seu perfil/entrada anterior nas configurações
de som e restaure o mixer com a placa disponível:

```sh
alsactl -f /CAMINHO/DO/BACKUP/mixer.state restore sofessx8336
```

Essa reversão não modifica o driver: nenhum módulo foi instalado por estes passos.

## Limites conhecidos

- É um contorno de sessão, não uma correção comprovada da causa no kernel/firmware.
- Entrada e saída permanecem abertas após o uso. Consumo de energia e efeitos de
  privacidade/indicadores de microfone não foram medidos; o procedimento não grava
  áudio em arquivos, mas mantém a rota de captura disponível no servidor de áudio.
- O perfil não oferece HDMI nem troca automática para fone P2. Headset P2,
  Bluetooth, suspensão e retomada não foram validados nesta configuração.
- A detecção física incorreta de jack não foi corrigida no driver; o perfil evita
  depender dela para selecionar entrada/saída. Novas detecções podem exigir revisão.
- Houve recorrência do amplificador após reboot. O rearme no login e o comando
  manual são contornos; a persistência e a captura de voz ainda exigem novos testes.
  O patch experimental precisa do primeiro teste após boot com o candidato carregado.
- Os nomes e limites dos controles de mixer são específicos do codec observado.
  O script confere os controles antes de aplicar os ajustes; erros ficam no journal
  do WirePlumber, sem impedir a inicialização do gerenciador de áudio.

Esta publicação inclui apenas configuração e documentação. Não inclui gravações,
logs pessoais, credenciais, ferramentas de escrita I2C ou dumps da investigação.
