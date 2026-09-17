#!/bin/bash
# Deploy de mejoras de post-procesamiento a servidor AWS
# Para mejorar Parte 4 de 77% → 80%+

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Deploy Mejoras Post-Procesamiento        ║${NC}"
echo -e "${GREEN}║  Objetivo: 77% → 80%+                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""

# Variables (ajustar según tu setup)
SERVER_IP="${AWS_SERVER_IP:-}"
SSH_KEY="${SSH_KEY:-$HOME/Documents/KEYS/llave/OT-IA-SERVER.pem}"
REMOTE_DIR="~/test-ia-local/caso-1-v2-e3"

if [ -z "$SERVER_IP" ]; then
    echo -e "${YELLOW}¿IP del servidor AWS?${NC}"
    read -p "IP: " SERVER_IP
fi

echo ""
echo -e "${GREEN}[1/6] Verificando archivos locales...${NC}"
if [ ! -f "workers/postprocess_express.py" ]; then
    echo "❌ Error: workers/postprocess_express.py no existe"
    exit 1
fi
echo "✅ postprocess_express.py encontrado"

echo ""
echo -e "${GREEN}[2/6] Verificando conexión SSH...${NC}"
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=5 ubuntu@$SERVER_IP "echo OK" &>/dev/null; then
    echo "❌ Error: No se puede conectar a $SERVER_IP"
    exit 1
fi
echo "✅ Conectado a $SERVER_IP"

echo ""
echo -e "${GREEN}[3/6] Copiando archivos al servidor...${NC}"
scp -i "$SSH_KEY" workers/postprocess_express.py ubuntu@$SERVER_IP:$REMOTE_DIR/workers/
echo "✅ postprocess_express.py copiado"

echo ""
echo -e "${GREEN}[4/6] Modificando nlp_worker.py...${NC}"
ssh -i "$SSH_KEY" ubuntu@$SERVER_IP << 'EOF'
cd ~/test-ia-local/caso-1-v2-e3

# Backup del worker original
if [ ! -f workers/nlp_worker.py.bak ]; then
    cp workers/nlp_worker.py workers/nlp_worker.py.bak
    echo "✅ Backup creado: nlp_worker.py.bak"
fi

# Agregar import si no existe
if ! grep -q "from workers.postprocess_express import postprocesar_campos_express" workers/nlp_worker.py; then
    # Buscar la línea con otros imports y agregar después
    sed -i '/^import json/a from workers.postprocess_express import postprocesar_campos_express' workers/nlp_worker.py
    echo "✅ Import agregado a nlp_worker.py"
else
    echo "⚠️  Import ya existe en nlp_worker.py"
fi

# Mostrar las líneas relevantes
echo ""
echo "Verificando imports:"
grep "postprocess" workers/nlp_worker.py || echo "⚠️  No se encontró el import"
EOF

echo ""
echo -e "${GREEN}[5/6] Reiniciando NLP worker...${NC}"
ssh -i "$SSH_KEY" ubuntu@$SERVER_IP << 'EOF'
cd ~/test-ia-local/caso-1-v2-e3
sudo docker compose --profile gpu restart nlp
echo "✅ NLP worker reiniciado"

# Esperar que levante
sleep 5

# Verificar logs
echo ""
echo "Últimas líneas del log:"
sudo docker compose --profile gpu logs nlp | tail -10
EOF

echo ""
echo -e "${GREEN}[6/6] Probando con documento de prueba...${NC}"
echo "Comando de prueba:"
echo "  curl -X POST http://$SERVER_IP:8080/procesar \\"
echo "    -H 'content-type: application/json' \\"
echo "    -d '{\"ruta\":\"/data/e3/front/20260812/6000000006.tif\",\"perfil\":\"front\"}'"
echo ""
echo -e "${YELLOW}Ejecuta este comando manualmente y verifica el resultado en el visor${NC}"
echo -e "${YELLOW}http://$SERVER_IP:8080${NC}"
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Deploy completado                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
