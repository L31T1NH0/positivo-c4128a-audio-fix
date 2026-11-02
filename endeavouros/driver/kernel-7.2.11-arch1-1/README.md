# Patch experimental · kernel 7.2.11-arch1-1

[← Guia EndeavourOS](../../README.md) · [Escolha de ambiente](../../../README.md)

**Estado em 02/11/2026: compilado sem avisos e imagem de teste preparada no
equipamento investigado. O módulo corrigido ainda não foi validado após boot.**

Este candidato trata a retomada do amplificador dos alto-falantes. Não é uma
correção upstream nem uma garantia para outros kernels ou equipamentos. A
configuração de sessão e os problemas de microfone/PCM são assuntos distintos.

## Falha observada

Após reiniciar o notebook, os serviços de áudio estavam ativos, a saída não estava
silenciada e os ponteiros de reprodução/captura avançavam. Mesmo assim não havia
som: `Speaker=on` e DAPM `Speaker Power=On`, mas o GPIO `speakers-enable` estava
`out lo ACTIVE LOW`. Reativar `Speaker` pelo mixer mudou o GPIO para `out hi` e
o usuário confirmou que o som voltou.

O driver desliga o amplificador em STOP/PAUSE_PUSH/SUSPEND sem atualizar o estado
lógico DAPM. START/PAUSE_RELEASE/RESUME não restauravam explicitamente esse GPIO.
Essa divergência é compatível com a falha observada. O rearme pelo mixer é um
contorno; este patch tenta corrigir a retomada dentro do driver.

## Alteração e procedência

O [patch](sof-es8336-retomada-7.2.11.patch) adiciona quatro linhas funcionais a
`sof_8336_trigger`: nos eventos de início/retomada, somente para reprodução,
reagenda `pcm_pop_work` com o atraso de 70 ms que já existia no driver.
O trabalho existente aplica ao GPIO o estado lógico DAPM atual.

Também é adicionado o identificador `MODULE_VERSION("0.2.0-positivo-7.2.11")` para
identificar o módulo carregado. Não foram alterados codec, captura, topologia,
detecção de jack ou parâmetros de quirk. A lógica existente de STOP/cancelamento
permanece; não se afirma que todas as possíveis corridas do driver foram corrigidas.

Os [fontes originais](source/) vêm do [kernel Arch Linux](https://github.com/archlinux/linux/tree/64a90897d3c539033f24105968e3513957e70819),
tag `v7.2.11-arch1`, commit `64a90897d3c539033f24105968e3513957e70819`.
[source.json](source.json) registra os hashes SHA-256 dos três arquivos de origem.
Os avisos de copyright e SPDX foram preservados.

## Verificações já realizadas

- Compilação original e corrigida com GCC 16.2.1 20260810, headers da versão
  `7.2.11-arch1-1` e `W=1`, sem avisos.
- A seção executável `.text` da compilação original foi idêntica, byte a byte,
  à do módulo da distribuição instalado no equipamento.
- Nome, aliases, licença, namespace, dependências e vermagic foram preservados.
- O módulo dentro da imagem experimental foi conferido por hash com `lsinitrd`;
  o pré-carregamento `rd.driver.pre` foi verificado.
- A sintaxe do GRUB e a preservação da entrada normal foram verificadas.

O [relatório de referência](validation-reference.json) registra essa compilação.
Compilações externas podem ter srcversion ou hash de módulo diferentes por causa
do ambiente de compilação. O instalador usa o manifesto gerado **na sua compilação**,
não trata o relatório de referência como certificado de funcionamento.

**Não concluído:** teste físico com o candidato carregado, repetidas paradas e
retomadas reais do PCM, microfone simultâneo, suspensão e uso prolongado.

## Requisitos e escopo

- Positivo `C4128A-15`, kernel e headers exatamente `7.2.11-arch1-1`.
- Ambiente EndeavourOS/Arch com GRUB e dracut no layout documentado abaixo.
- Python 3, GCC, make, binutils, patch, zstd, kmod, dracut e ferramentas do GRUB.
- Secure Boot desativado no equipamento testado. O módulo externo não é assinado;
  sistemas que exigem assinatura precisam de uma revisão específica.

Não execute este instalador com outro gerenciador de boot. Ele recusa modelos,
kernels, caminhos de GRUB ou destinos existentes que não correspondam ao teste.
Não remova nem recarregue módulos de áudio e não use unbind/rebind do controlador.

## 1. Compilar sem instalar

Na raiz do repositório, como usuário normal:

```sh
python3 endeavouros/driver/kernel-7.2.11-arch1-1/build.py
```

O script verifica os hashes dos fontes, aplica o patch com `--fuzz=0` e compila
as versões original e corrigida. Compara `.text` com o módulo instalado e confere
metadados de compatibilidade. Qualquer divergência impede a etapa seguinte.

Os resultados ficam em `.build/`, ignorada pelo Git:

- `original/` e `patched/`: árvores de compilação;
- `distribution.ko`: cópia descomprimida do módulo instalado para comparação;
- `validation.json`: hashes e identificadores da compilação local.

Nenhum módulo é instalado ou carregado nesta etapa. A compilação bem-sucedida não
substitui o teste do hardware.

## 2. Preparar uma entrada de boot separada

Leia [install-test.py](install-test.py) antes de executar:

```sh
sudo python3 endeavouros/driver/kernel-7.2.11-arch1-1/install-test.py
```

O instalador não altera `/usr/lib/modules` nem as imagens normais. Ele cria:

| Destino | Finalidade |
| --- | --- |
| `/boot/positivo-audio-7.2.11-arch1-1/vmlinuz` | Cópia do kernel da distribuição |
| `/boot/positivo-audio-7.2.11-arch1-1/initramfs.img` | Imagem com o módulo corrigido pré-carregado |
| `/etc/grub.d/42_positivo_audio_test` | Entrada exclusiva do experimento |
| `/var/lib/positivo-audio/driver-test-7.2.11-arch1-1/` | Backup do menu, hashes dos originais, logs e reversão |

Os arquivos experimentais ficam em uma **subpasta de `/boot`** para não serem
confundidos pelo gerador do GRUB com o kernel padrão. Antes de publicar o novo
menu local, o script confere sua sintaxe e compara a entrada normal à anterior.

Ele **não seleciona o teste automaticamente** nem altera permanentemente o padrão
do GRUB. Se a instalação falhar, não repita por cima dos destinos existentes:
consulte os logs e a reversão. Mesmo uma tentativa parcial pode deixar arquivos
experimentais, mas o menu normal só é substituído após as verificações.

## 3. Testar uma única inicialização

```sh
sudo grub-reboot positivo-audio-test
```

Salve o trabalho e reinicie normalmente. A entrada será
**EndeavourOS - teste audio Positivo (7.2.11)**. A seleção vale apenas uma vez;
a inicialização seguinte volta ao padrão normal. Também é possível escolher
manualmente essa entrada no menu do GRUB.

Depois, confira o módulo **carregado**:

```sh
uname -r
cat /sys/module/snd_soc_sof_es8336/version
cat /sys/module/snd_soc_sof_es8336/srcversion
```

O kernel deve ser `7.2.11-arch1-1`, a versão deve ser
`0.2.0-positivo-7.2.11` e o srcversion deve corresponder a
`.build/validation.json`. `modinfo` sem caminho continua mostrando o módulo
original em disco, por projeto; o sysfs identifica o módulo que está em uso.

Valide som físico, pausas/retomadas, fechamento e reabertura de aplicativos, voz no
microfone e captura simultânea. Manter o PCM aberto no WirePlumber pode impedir
que uma simples pausa da mídia exercite STOP/START reais do driver. O teste da
correção precisa confirmar as transições do PCM e o GPIO, não só o estado da TUI.
O rearme de Speaker no login acontece uma vez e também não prova a correção.

Os contornos de sessão foram mantidos para não mudar várias variáveis ao mesmo
tempo. Não use esta entrada depois de remover os módulos desse kernel em uma
atualização. O candidato não tem reconstrução automática via DKMS.

## Reversão

Para voltar ao original, reinicie pela entrada normal **EndeavourOS Linux**.
Se o teste não iniciar corretamente, reinicie e escolha essa entrada normal.

Para cancelar uma seleção de teste pendente:

```sh
sudo grub-editenv /boot/grub/grubenv unset next_entry
```

Para remover também o menu e as imagens experimentais:

```sh
sudo python3 /var/lib/positivo-audio/driver-test-7.2.11-arch1-1/remove-test.py
```

Se a instalação falhou antes de copiar o script de reversão, use a cópia do
repositório, na raiz dele:

```sh
sudo python3 endeavouros/driver/kernel-7.2.11-arch1-1/remove-test.py
```

A reversão não descarrega módulos em uso. Se o candidato já estiver carregado,
reinicie depois para carregar o original. O backup anterior do GRUB fica em
`/var/lib/positivo-audio/driver-test-7.2.11-arch1-1/grub.cfg.before` para recuperação
manual, se necessária.

## Arquivos publicados

São publicados fontes, patch, scripts e relatórios de compilação sem dados locais.
Não são incluídos módulos `.ko`, kernels, imagens de boot, logs de sessão, UUIDs de
disco, credenciais ou gravações. O patch continua experimental até a validação
física com o módulo corrigido em execução.
