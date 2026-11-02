# Áudio e microfone no Positivo C4128A-15

Correções e contornos para o notebook **Positivo C4128A-15**, codec **ESSX8326**,
placa ALSA `sofessx8336`. O repositório contém **duas configurações independentes**,
organizadas por ambiente. Escolha uma delas antes de seguir os comandos.

## 1. EndeavourOS · WirePlumber 0.5

**Configuração de sessão para alto-falantes e microfone; dois patches locais do driver, específicos do kernel 7.2.11.**

- Ambiente testado: kernel `7.2.11-arch1-1`, PipeWire 1.6.10 e WirePlumber 0.5.18.
- Usa o driver original da distribuição, perfil de reprodução/captura no PCM 0 e
  configuração de sessão que mantém entrada e saída abertas após o uso.
- Resposta à voz e fluxos simultâneos confirmados em 01/11/2026. Em 02/11,
  o reinício expôs recorrência do amplificador desligado; o som voltou pelo mixer.
- Os [dois patches para o kernel 7.2.11](endeavouros/driver/kernel-7.2.11-arch1-1/README.md)
  corrigem a retomada do amplificador e permitem fixar o microfone digital. O usuário
  confirmou ambos no boot isolado; a instalação persistente foi preparada e o teste
  removido do GRUB. **O primeiro reinício normal ainda não foi observado.**

**→ [Guia EndeavourOS: instalação, backup, validação e reversão](endeavouros/README.md)**

Arquivos deste caminho: [`endeavouros/config/`](endeavouros/config/).

## 2. Linux Mint 22.3 · WirePlumber 0.4

**Somente alto-falantes; o microfone interno fica desativado.**

- Ambiente testado: kernel `7.0.0-28-generic` (Ubuntu 7.0.12), PipeWire 1.0.5 e
  WirePlumber 0.4.17.
- Inclui o patch de retomada do amplificador, os fontes DKMS e regras Lua 0.4.
- Reprodução confirmada no ambiente original; captura simultânea apresentou
  travamento e foi desabilitada nesse perfil.

**→ [Guia Linux Mint: driver, configuração e reversão](linux-mint/README.md)**

Arquivos deste caminho: [`linux-mint/config/`](linux-mint/config/),
[`linux-mint/driver/`](linux-mint/driver/) e
[`linux-mint/scripts/`](linux-mint/scripts/).

## Qual caminho usar?

| Seu ambiente | Pasta e guia | Reprodução | Microfone |
| --- | --- | --- | --- |
| EndeavourOS com WirePlumber 0.5, no kernel testado | [`endeavouros/`](endeavouros/README.md) | Confirmada | Resposta à voz confirmada |
| Mint 22.3 com WirePlumber 0.4, no kernel testado | [`linux-mint/`](linux-mint/README.md) | Confirmada | Desativado pelo perfil |
| Outro modelo, distribuição, kernel ou versão do WirePlumber | Revise a compatibilidade antes de instalar | Não validada | Não validado |

Consulte sua versão com `wireplumber --version` e o kernel com `uname -r`.
As configurações são específicas dos ambientes documentados: **não misture os
dois caminhos**, não instale as regras Lua 0.4 no WirePlumber 0.5 e não use o DKMS
do Mint no kernel 7.2.

Os comandos dos dois guias devem ser executados **na raiz do repositório**.
Cada guia informa os limites e os passos de reversão correspondentes ao seu ambiente.

## Organização dos arquivos

```text
.
├── README.md                         # Escolha do ambiente e visão geral
├── endeavouros/
│   ├── README.md                     # Guia de áudio e microfone / WirePlumber 0.5
│   ├── config/                       # Perfil duplex, regras .conf e mixer
│   ├── scripts/                      # Rearme manual do amplificador
│   └── driver/
│       └── kernel-7.2.11-arch1-1/      # Dois patches, teste isolado, persistência e reversão
└── linux-mint/
    ├── README.md                     # Guia de reprodução / WirePlumber 0.4
    ├── config/                       # Perfil sem captura, regras Lua e mixer
    ├── driver/
    │   ├── dkms-source/              # Fontes do módulo para a série 7.0
    │   └── sof-es8336-retomada.patch  # Patch de retomada do amplificador
    └── scripts/
        └── reverter-driver.sh        # Remoção da sobreposição DKMS no Mint
```

Os arquivos antigos da raiz e de `config/wireplumber-0.5/` foram movidos para as
pastas acima. Use os comandos atualizados dos guias, pois os caminhos mudaram.

## Limites e origem dos fontes

São resultados em um equipamento específico, não uma garantia para outros modelos.
O contorno do EndeavourOS não comprova uma correção definitiva do driver; houve
recorrência após reboot. Os módulos 7.2.11 tiveram som e voz confirmados em boot isolado. A primeira
inicialização normal após a instalação persistente ainda precisa ser observada. Fone P2,
Bluetooth, suspensão e retomada não foram validados nas configurações finais.
Manter dispositivos abertos pode afetar consumo de energia.

Os [fontes do módulo e cabeçalhos](linux-mint/driver/dkms-source/) foram preservados
da investigação baseada no kernel Linux/Ubuntu 7.0.12. Os avisos de copyright e
identificadores SPDX foram mantidos; consulte cada arquivo para sua licença.
O driver `sof_es8336.c` declara `GPL-2.0-only`.

Logs pessoais, conversas, gravações, credenciais, dumps de sessão e módulos binários
não fazem parte deste repositório.
