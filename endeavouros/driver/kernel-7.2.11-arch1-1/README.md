# Drivers de áudio e microfone · kernel 7.2.11-arch1-1

[← Guia EndeavourOS](../../README.md) · [Escolha de ambiente](../../../README.md)

**Estado em 02/11/2026:** o usuário confirmou alto-falantes e microfone funcionando
com os dois módulos corrigidos carregados em boot isolado. Os mesmos módulos foram
instalados para o boot normal, com conferência da imagem, e a entrada de teste foi
removida. **O primeiro reinício normal após a instalação persistente ainda não foi
observado.** Suspensão, uso prolongado e ciclos extensivos de retomada não foram validados.

Esta é uma correção local, específica do Positivo C4128A-15 no kernel indicado.
Os patches não foram aceitos upstream e não são garantia para outros equipamentos.
O [registro de confirmação](hardware-confirmation.json) separa os resultados de
hardware das verificações de compilação.

## 1. Retomada do amplificador

Mesmo com `Speaker=on`, DAPM ligado, saída sem mute e ponteiros PCM em avanço,
o amplificador estava fisicamente desligado. Rearmar Speaker pelo mixer recuperou
o som, confirmado pelo usuário. O driver desliga o GPIO em STOP, mas não o restaurava
explicitamente nos eventos de início/retomada.

O [patch do amplificador](sof-es8336-retomada-7.2.11.patch) adiciona quatro linhas
funcionais: em START/PAUSE_RELEASE/RESUME, somente para reprodução, reagenda
`pcm_pop_work` com os mesmos 70 ms já utilizados pelo driver. O trabalho aplica ao
GPIO o estado lógico DAPM. A versão local é `0.2.0-positivo-7.2.11`.

A lógica de STOP/cancelamento foi preservada. Não se afirma que todas as possíveis
corridas do driver ou falhas de PCM/DSP estejam corrigidas.

## 2. Seleção do microfone digital interno

O sistema detectava um headset P2 inexistente. A rotina do codec mudava as fontes
ADC de `44/66` (entrada digital usada pelo microfone interno) para `00/00`
(analógica). Os ponteiros de captura avançavam, mas não havia resposta à voz.
Restaurar temporariamente a entrada digital recuperou a voz, confirmado pelo usuário.

O [patch do codec](es8326-internal-dmic.patch) acrescenta o controle ALSA
**Internal DMIC Force Switch**:

| Estado | Comportamento |
| --- | --- |
| `off`, padrão | Mantém a escolha automática original de entrada |
| `on` | Fixa `44/66` e impede que o detector de headset substitua essa seleção por `00/00` |

O setter e a rotina de jack compartilham o mesmo mutex. Desligar o controle restaura
as fontes correspondentes ao estado de jack atual. Falhas de regmap são propagadas
pelo setter e a flag anterior é restaurada. A versão local é `0.1.0-positivo-dmic`.

O [script de sessão](../../config/positivo-audio-init) habilita o controle somente
quando ele existe; sem o novo codec, o script continua compatível. Não há escrita
I2C direta nem `sudo` na inicialização da sessão.

O controle **não corrige a detecção física do P2**. Com a entrada digital fixada,
não há troca automática para o microfone analógico de headset. O patch não modifica
GPIO do amplificador, relógios ou topologia. A seleção permanece automática por
padrão para equipamentos que não habilitem o controle explicitamente.

## Fonte e verificações

Fontes do [kernel Arch Linux](https://github.com/archlinux/linux/tree/64a90897d3c539033f24105968e3513957e70819),
tag `v7.2.11-arch1`, commit `64a90897d3c539033f24105968e3513957e70819`.
[source.json](source.json) registra hashes SHA-256. Copyright e SPDX foram preservados.

Verificações realizadas:

- Compilação dos módulos originais e corrigidos com headers `7.2.11-arch1-1`,
  GCC 16.2.1 20260810 e `W=1`, sem avisos.
- As seções executáveis `.text` das compilações originais foram idênticas, byte a
  byte, às dos respectivos módulos da distribuição.
- Nome, aliases, licença e vermagic preservados. No amplificador, dependências e
  namespace também permaneceram iguais.
- No codec, a dependência direta adicional `snd` fornece o descritor booleano ALSA;
  esse módulo já era dependência indireta do núcleo de áudio.
- Testes C das funções reais do controle, com ALSA/regmap/mutex simulados: seleção,
  sobrescrita solicitada pelo detector, modo automático, valores inválidos,
  controle repetido, ausência de jack e erro I2C.
- Os módulos embutidos nas imagens de teste e persistente foram conferidos por hash.
- Após o teste confirmado pelo usuário, originais em disco foram preservados e a
  entrada experimental foi removida. O GRUB gerado passou por verificação de sintaxe.

[validation-reference.json](validation-reference.json) e
[codec-validation-reference.json](codec-validation-reference.json) são registros de
compilação de referência. Hash e srcversion podem variar conforme o ambiente de
compilação; os instaladores usam o manifesto da **compilação local**. Esses registros
não certificam funcionamento em outra máquina.

## Requisitos

- Positivo `C4128A-15`, kernel e headers exatamente `7.2.11-arch1-1`.
- EndeavourOS/Arch com GRUB e dracut no layout reconhecido pelos scripts.
- Python 3, GCC, make, binutils, patch, zstd, kmod, dracut e ferramentas GRUB.
- Secure Boot desativado no equipamento testado; os módulos externos não são
  assinados. Sistemas que exigem assinatura precisam de revisão específica.

Não use os instaladores em outro bootloader, modelo ou kernel. Eles recusam destinos
existentes para não sobrescrever uma instalação sem revisão. **Não descarregue os
módulos nem use unbind/rebind do controlador**: a investigação anterior atingiu
falha no kernel ao tentar esse caminho.

## Etapa A · Compilar e testar a lógica, sem instalar

Todos os comandos abaixo partem da raiz do repositório:

```sh
python3 endeavouros/driver/kernel-7.2.11-arch1-1/build.py
python3 endeavouros/driver/kernel-7.2.11-arch1-1/tests/test-control.py
```

O build verifica os hashes dos fontes, aplica os dois patches com `--fuzz=0`,
compila e compara as versões originais com os módulos da distribuição. Os caminhos
dos originais são explícitos, permitindo a comparação mesmo quando já existe uma
sobreposição instalada. Uma divergência interrompe o processo.

O resultado fica em `.build/`, ignorada pelo Git: fontes de compilação, módulos,
seções de comparação e `validation.json`. Nenhum módulo é instalado ou carregado.
Testes de lógica não substituem confirmação de voz e som no hardware.

## Etapa B · Boot isolado de validação

Leia [install-test.py](install-test.py) e execute:

```sh
sudo python3 endeavouros/driver/kernel-7.2.11-arch1-1/install-test.py
```

O script mantém intactos `/usr/lib/modules` e as imagens normais. Cria:

| Destino | Finalidade |
| --- | --- |
| `/boot/positivo-audio-7.2.11-arch1-1/vmlinuz` | Cópia do kernel da distribuição |
| `/boot/positivo-audio-7.2.11-arch1-1/initramfs.img` | Imagem com os dois módulos corrigidos |
| `/etc/grub.d/42_positivo_audio_test` | Entrada do experimento |
| `/var/lib/positivo-audio/driver-test-7.2.11-arch1-1/` | Backup, hashes, overlay usado na imagem, logs e reversão |

A subpasta em `/boot` evita que o gerador do GRUB confunda o kernel experimental
com o padrão. O script confere a imagem, o pré-carregamento dos dois módulos, a
sintaxe do menu e a preservação da entrada normal antes de publicar o menu local.
Não seleciona a entrada de teste automaticamente.

Para testar uma única inicialização:

```sh
sudo grub-reboot positivo-audio-test
```

Salve seu trabalho e reinicie normalmente. Escolha, se necessário,
**EndeavourOS - teste audio Positivo (7.2.11)**. A seleção vale uma vez; o boot
seguinte volta ao padrão se você ainda não fez a instalação persistente.

Depois, confira os módulos **carregados** e o controle:

```sh
uname -r
cat /sys/module/snd_soc_sof_es8336/version
cat /sys/module/snd_soc_es8326/version
amixer -c sofessx8336 cget "name='Internal DMIC Force Switch'"
```

Esperado: kernel `7.2.11-arch1-1`, versões `0.2.0-positivo-7.2.11` e
`0.1.0-positivo-dmic`, controle `on` após aplicar a configuração de sessão atual.
Os srcversions em `/sys/module/.../srcversion` devem corresponder ao manifesto
local. Nesta etapa, `modinfo` sem caminho ainda pode apontar para os originais em
disco; ele não identifica sozinho o módulo carregado.

Confirme voz real, reprodução, fechamento/reabertura dos aplicativos e uso
simultâneo. Uma onda de ruído ou apenas ponteiros em avanço não comprovam voz.
Manter o PCM aberto no WirePlumber pode impedir que uma pausa da mídia exercite
STOP/START reais; testes da retomada precisam observar essas transições e o GPIO.

## Etapa C · Tornar persistente e remover o teste

**Faça somente depois de confirmar os dois módulos carregados e o funcionamento
no boot isolado.** Leia [install-persistent.py](install-persistent.py):

```sh
sudo python3 endeavouros/driver/kernel-7.2.11-arch1-1/install-persistent.py
```

O script usa os arquivos que foram incluídos no teste e compara versão/srcversion
com os módulos em execução. Ele:

1. Salva a imagem normal anterior e um manifesto de reversão.
2. Instala cópias em `/usr/lib/modules/7.2.11-arch1-1/updates/positivo-audio/`,
   preservando os originais em `kernel/sound/soc/`.
3. Executa `depmod` e confere que os módulos corrigidos são selecionados.
4. Adiciona o pré-carregamento em `/etc/dracut.conf.d/positivo-audio.conf`.
5. Gera uma imagem normal temporária e confere os dois módulos por hash antes de
   substituir `/boot/initramfs-linux.img`.
6. Remove a entrada e as imagens experimentais, sem descarregar módulos em uso.

Backup, manifesto, logs e reversão ficam em:
`/var/lib/positivo-audio/permanente-7.2.11-arch1-1/`.

Essa instalação foi realizada no equipamento investigado. A imagem normal foi
verificada, mas o primeiro reinício por ela ainda não foi observado. A confirmação
física anterior ocorreu no boot isolado com os mesmos módulos.

## Reverter

### Antes da instalação persistente

Reinicie pela entrada normal **EndeavourOS Linux** para usar os originais. Para
cancelar uma seleção de teste pendente:

```sh
sudo grub-editenv /boot/grub/grubenv unset next_entry
```

Para remover o experimento sem promover os módulos:

```sh
sudo python3 /var/lib/positivo-audio/driver-test-7.2.11-arch1-1/remove-test.py
```

Se a instalação parcial ainda não copiou esse script, use
`sudo python3 endeavouros/driver/kernel-7.2.11-arch1-1/remove-test.py` na raiz do
repositório. Não repita instalações por cima de destinos existentes sem revisar logs.

### Depois da instalação persistente

A entrada normal já usa os corrigidos. Para restaurar os originais:

```sh
sudo python3 /var/lib/positivo-audio/permanente-7.2.11-arch1-1/reverter.py
```

O script confere o kernel padrão, os hashes das sobreposições e o backup; remove
somente as cópias e a configuração criadas por esse procedimento, executa `depmod`
e restaura a imagem anterior. Reinicie depois para carregar os originais. Não há
recarga de driver durante a reversão. Se o kernel padrão já mudou, a reversão para
uma imagem antiga é recusada e exige revisão.

## Atualizações e limites

- **Fixado no kernel 7.2.11-arch1-1.** Não há DKMS nem reconstrução automática.
  Um kernel diferente exige adaptação, compilação e nova validação. A configuração
  de pré-carregamento não transforma os módulos originais de um kernel novo em
  versões corrigidas.
- Não se comprova correção definitiva de todos os problemas do driver/firmware.
- O controle digital não corrige o detector físico do conector P2. Headset P2,
  Bluetooth, suspensão, retomadas extensivas e uso prolongado não foram validados.
- Os contornos de sessão, inclusive manter os PCM abertos, foram preservados.
- Não há binários, kernels, imagens de boot, UUIDs de disco, credenciais, logs
  pessoais ou gravações neste repositório. Fontes, patches e scripts são revisáveis.
