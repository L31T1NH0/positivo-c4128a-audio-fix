#!/bin/sh
# Rearma o amplificador pelo mixer, sem reiniciar serviços ou módulos.
set -eu
[ "$(cat /sys/class/dmi/id/product_name)" = "C4128A-15" ] || {
    echo 'Este comando é específico do Positivo C4128A-15.' >&2
    exit 1
}
amixer -c sofessx8336 sget Speaker >/dev/null
amixer -q -c sofessx8336 sset Speaker off
amixer -q -c sofessx8336 sset Speaker on
