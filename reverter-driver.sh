#!/bin/sh
# Remove the override; the distribution's original module is kept on disk.
set -eu
dkms remove -m positivo-es8336 -v 0.1 --all
update-initramfs -u -k "$(uname -r)"
echo 'Original driver restored on disk. Restart the notebook to load it.'
