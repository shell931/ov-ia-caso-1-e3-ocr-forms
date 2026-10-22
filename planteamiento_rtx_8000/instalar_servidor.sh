#!/usr/bin/env bash
# Tarea B3 · Base del servidor para el stack E3 en GPUs Turing (Dell R740xd con
# 2× RTX 8000; validado en AWS g4dn.metal con Ubuntu 24.04).
#
# Instala, solo si falta: driver NVIDIA 580-server con DKMS, Docker + Compose v2
# con rotación de logs, NVIDIA Container Toolkit, modo persistencia y AWS CLI v2.
# Se puede correr más de una vez: lo que ya está bien no se toca.
#
# Uso: bash planteamiento_rtx_8000/instalar_servidor.sh
# Si instala el driver por primera vez pide reiniciar; después volver a correrlo.
#
# Lecciones del g4dn.metal (ver DESPLIEGUE_DELL.md):
#   - NO usar linux-modules-nvidia-580-server-<flavor>: arrastró un kernel nuevo con
#     módulos rotos y una versión de módulo distinta a la de las librerías.
#   - DKMS compila el módulo para el kernel que corre; necesita Secure Boot apagado
#     (o firmar el módulo con una MOK).
#   - El kernel queda congelado (apt-mark hold) para que un upgrade no lo cambie.
set -euo pipefail
# con pipefail, "cmd | grep -q" puede fallar por SIGPIPE si grep corta antes: usar grep -c

DRIVER=${DRIVER:-580-server}
USUARIO=${SUDO_USER:-$USER}
export DEBIAN_FRONTEND=noninteractive
ok()  { echo "  ok    $*"; }
hago(){ echo "  ...   $*"; }
mal() { echo "  ERROR $*" >&2; exit 1; }

. /etc/os-release
echo "== Sistema: $PRETTY_NAME · kernel $(uname -r)"
[ "$ID" = ubuntu ] || mal "probado solo en Ubuntu (22.04/24.04)"
lspci | grep -ci nvidia >/dev/null || mal "no hay GPUs NVIDIA en el bus PCI"
echo "  GPUs en PCI: $(lspci | grep -ci nvidia)"

echo "== Secure Boot"
if command -v mokutil >/dev/null && mokutil --sb-state 2>/dev/null | grep -ci enabled >/dev/null; then
  mal "Secure Boot activo: apagarlo en la BIOS/UEFI (o firmar el módulo DKMS) y volver a correr"
fi
ok "apagado o no aplica ($( [ -d /sys/firmware/efi ] && echo UEFI || echo BIOS))"

echo "== Driver NVIDIA $DRIVER (DKMS)"
REINICIAR=0
if nvidia-smi -L >/dev/null 2>&1; then
  ok "$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1) · $(nvidia-smi -L | wc -l) GPUs"
else
  if dpkg -l | grep -c '^ii  linux-modules-nvidia' >/dev/null; then
    hago "quitando módulos precompilados (versión distinta a las librerías)"
    sudo apt-get purge -y -qq $(dpkg -l | awk '/^ii  linux-(modules|objects)-nvidia/ {print $2}') >/dev/null
  fi
  hago "instalando headers + nvidia-dkms-$DRIVER"
  sudo apt-get update -qq
  sudo apt-get install -y -qq "linux-headers-$(uname -r)" "nvidia-dkms-$DRIVER" \
    "nvidia-utils-$DRIVER" "nvidia-compute-utils-$DRIVER" "libnvidia-compute-${DRIVER%-server}-server" >/dev/null
  dkms status | grep -c "$(uname -r).*installed" >/dev/null || mal "DKMS no compiló el módulo para $(uname -r)"
  REINICIAR=1
fi
for m in linux-generic linux-image-generic linux-headers-generic linux-generic-hwe-24.04 \
         linux-image-generic-hwe-24.04 linux-aws linux-image-aws linux-headers-aws; do
  dpkg -l "$m" 2>/dev/null | grep -c '^[ih]i' >/dev/null && sudo apt-mark hold "$m" >/dev/null && ok "kernel congelado: $m"
done
if [ "$REINICIAR" = 1 ]; then
  echo
  echo ">> Driver instalado. Reiniciar (sudo reboot) y volver a correr este script."
  exit 0
fi
sudo systemctl enable -q --now nvidia-persistenced 2>/dev/null && ok "modo persistencia" || sudo nvidia-smi -pm 1 >/dev/null

echo "== Docker + Compose"
sudo install -m 0755 -d /etc/apt/keyrings
if ! command -v docker >/dev/null; then
  hago "repositorio oficial de Docker"
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null
fi
ok "$(docker --version)"; ok "$(docker compose version)"
# rotación de logs (los de vLLM crecen rápido); se mezcla con lo que ya tenga daemon.json
sudo python3 - <<'PY'
import json, os
p = "/etc/docker/daemon.json"
d = json.load(open(p)) if os.path.exists(p) and os.path.getsize(p) else {}
d.setdefault("log-driver", "json-file")
d.setdefault("log-opts", {}).update({"max-size": "100m", "max-file": "5"})
json.dump(d, open(p, "w"), indent=2)
PY
ok "rotación de logs (100m × 5)"

echo "== NVIDIA Container Toolkit"
if ! command -v nvidia-ctk >/dev/null; then
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor --yes -o /etc/apt/keyrings/nvidia-container-toolkit.gpg
  curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/etc/apt/keyrings/nvidia-container-toolkit.gpg] https://#' \
    | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
  sudo apt-get update -qq && sudo apt-get install -y -qq nvidia-container-toolkit >/dev/null
fi
sudo nvidia-ctk runtime configure --runtime=docker >/dev/null 2>&1   # el compose usa runtime: nvidia
sudo systemctl restart docker && sudo systemctl enable -q docker
id -nG "$USUARIO" | grep -cw docker >/dev/null || { sudo usermod -aG docker "$USUARIO"; echo "  nota  $USUARIO agregado al grupo docker: volver a entrar por SSH"; }
ok "$(nvidia-ctk --version | head -1)"

echo "== AWS CLI v2"
if ! command -v aws >/dev/null; then
  command -v unzip >/dev/null || sudo apt-get install -y -qq unzip >/dev/null
  t=$(mktemp -d); curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o "$t/a.zip"
  unzip -q "$t/a.zip" -d "$t" && sudo "$t/aws/install" --update >/dev/null; rm -rf "$t"
fi
ok "$(aws --version)"

echo "== Verificación"
sudo docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi -L | sed 's/^/  /'
echo
echo ">> Base lista. Siguiente: bash planteamiento_rtx_8000/preparar_datos.sh (tarea B4)."
