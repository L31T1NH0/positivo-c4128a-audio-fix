# Linux Mint 22.3 · WirePlumber 0.4

[← Voltar à escolha de ambiente](../README.md)

**Somente alto-falantes. O microfone interno fica desativado nesta configuração.**

**Estado documentado em 18/10/2026 para o Mint:** a reprodução voltou a funcionar. O microfone interno foi desativado para contornar uma segunda falha de reprodução/captura simultâneas. Esta publicação não representa uma solução completa de áudio e microfone.

## Ambiente em que foi testado

- Linux Mint 22.3; kernel `7.0.0-28-generic` (Ubuntu 7.0.12).
- PipeWire 1.0.5; WirePlumber 0.4.17.
- Módulo DKMS `positivo-es8336/0.1`.

Não aplique automaticamente em outros modelos ou kernels. As regras Lua são para WirePlumber 0.4; precisam de adaptação para 0.5.

## O que o patch corrige

No driver observado, STOP/PAUSE_PUSH/SUSPEND desligavam o amplificador por GPIO sem atualizar o estado lógico DAPM. START/PAUSE_RELEASE/RESUME não restauravam esse GPIO, podendo deixar o alto-falante silencioso na reprodução seguinte.

O patch agenda o trabalho existente `pcm_pop_work` no início ou retomada da reprodução, usando o atraso de 70 ms já presente no driver. Veja [o patch](driver/sof-es8336-retomada.patch) e os [fontes DKMS](driver/dkms-source/).

O módulo corrigido foi carregado, e houve confirmação de som físico em vídeos, VLC e retomadas, inclusive após dois reinícios. Mais tarde houve nova falha com ponteiros de reprodução e captura congelados, mesmo com o patch carregado. Desativar a captura recuperou a reprodução. A causa dessa segunda falha não foi isolada.

## Instalar o driver no ambiente testado

Revise o código antes de executar. Os comandos abaixo alteram módulos do kernel; tenha acesso a um terminal para reverter. Com Secure Boot ativo, o módulo precisa de assinatura e chave aceita pelo sistema.

Na raiz deste repositório, com `dkms`, ferramentas de compilação e headers do kernel instalados:

```sh
test "$(uname -r)" = 7.0.0-28-generic
test "$(cat /sys/class/dmi/id/product_name)" = C4128A-15
sudo apt install dkms build-essential "linux-headers-$(uname -r)"
# Se este destino já existir, revise a instalação existente antes de continuar.
sudo test ! -e /usr/src/positivo-es8336-0.1
sudo cp -a linux-mint/driver/dkms-source /usr/src/positivo-es8336-0.1
sudo dkms add -m positivo-es8336 -v 0.1
sudo dkms build -m positivo-es8336 -v 0.1 -k "$(uname -r)"
sudo dkms install -m positivo-es8336 -v 0.1 -k "$(uname -r)"
sudo update-initramfs -u -k "$(uname -r)"
```

Execute cada comando separadamente e pare se qualquer um falhar. Reinicie o notebook depois da instalação. O módulo da distribuição permanece no disco; o DKMS instala uma sobreposição em `updates/dkms`.

```sh
dkms status -m positivo-es8336
modinfo -n snd_soc_sof_es8336
modinfo -F srcversion snd_soc_sof_es8336
cat /sys/module/snd_soc_sof_es8336/srcversion
```

Na compilação originalmente testada, o `srcversion` instalado e carregado era `C39F57C1811A19F2CB2F848`. O DKMS aceita apenas a série 7.0, mas a validação foi feita somente no kernel indicado acima.

## Configuração complementar: somente alto-falantes

Os arquivos em [`config/`](config/) contornam a falsa detecção de fone, limitam o perfil ao PCM 0, mantêm a saída aberta e inicializam as rotas do mixer com espera de até 30 segundos pela placa. O microfone interno fica desligado. Os níveis do mixer são os usados no equipamento testado; comece com o volume de reprodução baixo.

Faça backup de arquivos existentes nos destinos antes de substituí-los. Execute como seu usuário, na raiz do repositório:

```sh
mkdir -p "$HOME/.config/positivo-audio" "$HOME/.config/wireplumber/main.lua.d" "$HOME/.config/systemd/user/wireplumber.service.d" "$HOME/.local/bin"
cp linux-mint/config/profile.conf "$HOME/.config/positivo-audio/profile.conf"
python3 - <<'CONFIG'
from pathlib import Path
home = Path.home()
for source, target in [
    ('linux-mint/config/51-disable-broken-sof-hdmi.lua', '.config/wireplumber/main.lua.d/51-disable-broken-sof-hdmi.lua'),
    ('linux-mint/config/positivo-audio.conf', '.config/systemd/user/wireplumber.service.d/positivo-audio.conf'),
]:
    (home / target).write_text(Path(source).read_text().replace('@HOME@', str(home)))
CONFIG
install -m 755 linux-mint/config/positivo-audio-init "$HOME/.local/bin/positivo-audio-init"
systemctl --user daemon-reload
systemctl --user restart pipewire pipewire-pulse wireplumber
```

Essa substituição pressupõe um caminho de usuário convencional, sem aspas ou caracteres especiais. O reinício interrompe os fluxos de áudio; reabra ou recarregue a mídia depois. Se necessário, selecione “Alto-falantes internos” nas configurações de som.

## Reverter

Para remover o driver DKMS e atualizar o initramfs do kernel em uso:

```sh
sudo sh linux-mint/scripts/reverter-driver.sh
```

Reinicie para carregar o módulo original. Para desfazer a configuração de sessão, restaure seus backups dos quatro arquivos instalados acima, ou remova apenas os arquivos que esta instalação criou se não havia versões anteriores. Depois execute `systemctl --user daemon-reload` e reinicie os três serviços de áudio.

## Limites conhecidos

- No ambiente Mint/WirePlumber 0.4 desta seção, o bloqueio de reprodução/captura simultâneas não foi corrigido; o [perfil deste ambiente](config/profile.conf) oferece apenas reprodução. O contorno para WirePlumber 0.5 está [na seção EndeavourOS](../endeavouros/README.md).
- A configuração final sem captura teve confirmação de reprodução de voz e mídia com som, mas não passou por outro reboot nem por teste prolongado naquela etapa.
- Suspensão do notebook, fone P2 e Bluetooth não foram validados. Não há troca automática para fone P2 neste perfil.
- Manter a saída aberta pode aumentar o consumo de energia; isso não foi medido.
- Novas versões de kernel e WirePlumber precisam de revisão e novos testes.

