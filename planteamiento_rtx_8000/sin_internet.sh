#!/usr/bin/env bash
# Tarea B7b.6 · Corta la salida a internet de los contenedores y cuenta los intentos.
# Deja pasar redes privadas (RabbitMQ del cliente, recurso compartido, red de Docker)
# y conexiones ya establecidas; todo lo demás se registra en el kernel y se rechaza.
#
#   bash planteamiento_rtx_8000/sin_internet.sh on       # bloquear y poner contadores en cero
#   bash planteamiento_rtx_8000/sin_internet.sh estado   # intentos bloqueados y destinos
#   bash planteamiento_rtx_8000/sin_internet.sh off      # quitar el bloqueo
#
# Solo afecta a contenedores (cadena DOCKER-USER); el host sigue con su red. En
# producción el corte definitivo lo hace el firewall de la entidad; esto es la
# prueba de aceptación. Verificado en g4dn.metal: 20/20 formularios, 0 intentos.
set -euo pipefail
case "${1:-estado}" in
  on)
    sudo iptables -N E3OFF 2>/dev/null || sudo iptables -F E3OFF
    sudo iptables -A E3OFF -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
    for n in 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 127.0.0.0/8; do sudo iptables -A E3OFF -d "$n" -j RETURN; done
    sudo iptables -A E3OFF -j LOG --log-prefix "E3OFF " --log-level 4
    sudo iptables -A E3OFF -j REJECT
    sudo iptables -C DOCKER-USER -j E3OFF 2>/dev/null || sudo iptables -I DOCKER-USER 1 -j E3OFF
    echo "bloqueo activo desde $(date '+%F %T'); contadores en cero" ;;
  estado)
    n=$(sudo iptables -L E3OFF -v -n -x 2>/dev/null | awk '$3 == "REJECT" {print $1}')
    [ -z "$n" ] && { echo "bloqueo inactivo"; exit 0; }
    echo "intentos de salida rechazados: $n"
    echo "(el historial de abajo puede incluir intentos anteriores al último 'on'; lo que cuenta es el número de arriba)"
    sudo dmesg -T | grep 'E3OFF ' | sed -E 's/^\[([^]]*)\].*SRC=([0-9.]*).*DST=([0-9.]*).*DPT=([0-9]*).*/\1  \2 -> \3:\4/' | tail -20 ;;
  off)
    sudo iptables -D DOCKER-USER -j E3OFF 2>/dev/null || true
    sudo iptables -F E3OFF 2>/dev/null || true; sudo iptables -X E3OFF 2>/dev/null || true
    echo "bloqueo quitado" ;;
  *) echo "uso: $0 on|estado|off"; exit 1 ;;
esac
