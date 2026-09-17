#!/bin/bash
# Prueba de mejoras post-procesamiento con 10 documentos
# Compara p4 (baseline) vs p8 (con mejoras)

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Test Mejoras Post-Procesamiento          ║${NC}"
echo -e "${BLUE}║  p4 (baseline) vs p8 (con mejoras)        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "scripts/load_test_pipeline.py" ]; then
    echo "❌ Error: Debe ejecutar desde ~/test-ia-local/caso-1-v2-e3"
    exit 1
fi

echo -e "${GREEN}[1/4] Load test con 10 documentos (prefijo p8*)...${NC}"
python scripts/load_test_pipeline.py \
  --dir /data/e3/front/20260812 \
  --n 10 \
  --repeat 1 \
  --concurrency 5 \
  --perfil front \
  --prefix p8 \
  --timeout 600

echo ""
echo -e "${GREEN}[2/4] Comparando contra gold...${NC}"
python scripts/compare_gold.py \
  /data/e3/gold/gold.json \
  /data/e3/resultados.json \
  p8 \
  prueba_mejoras_p8

echo ""
echo -e "${GREEN}[3/4] Extrayendo métricas p4 (baseline)...${NC}"
# Si existe comparación anterior de p4
if [ -f "/data/e3/comparacion-parte4.csv" ]; then
    echo "Baseline p4 existente:"
    awk -F';' 'NR>1 {if($7=="distinto") dist++; if($7=="exacto") exact++; if($7=="casi") casi++} END {total=exact+casi+dist; print "  Exacto:", exact, "("int(exact*100/total)"%)"; print "  Casi:", casi, "("int(casi*100/total)"%)"; print "  Distinto:", dist, "("int(dist*100/total)"%)";}' /data/e3/comparacion-parte4.csv
else
    echo "⚠️  No se encontró comparacion-parte4.csv"
    echo "   Asumir baseline: 77% exacto, 6% casi, 16% distinto"
fi

echo ""
echo -e "${GREEN}[4/4] Comparando p4 vs p8...${NC}"
echo ""
echo "══════════════════════════════════════════════════════════"
echo "  COMPARACIÓN: p4 (baseline) vs p8 (con mejoras)"
echo "══════════════════════════════════════════════════════════"
echo ""

if [ -f "/data/e3/comparacion-prueba_mejoras_p8.csv" ]; then
    echo "Resultados p8 (con mejoras):"
    awk -F';' 'NR>1 {if($7=="distinto") dist++; if($7=="exacto") exact++; if($7=="casi") casi++} END {total=exact+casi+dist; print "  Exacto:", exact, "("int(exact*100/total)"%)"; print "  Casi:", casi, "("int(casi*100/total)"%)"; print "  Distinto:", dist, "("int(dist*100/total)"%)";}' /data/e3/comparacion-prueba_mejoras_p8.csv
    
    echo ""
    echo "Top campos con errores p8:"
    cat /data/e3/comparacion-prueba_mejoras_p8.csv | grep ";distinto;" | cut -d';' -f3 | sort | uniq -c | sort -rn | head -5
    
    echo ""
    echo "Archivos generados:"
    echo "  📄 /data/e3/comparacion-prueba_mejoras_p8.csv"
    echo "  📄 /data/e3/prueba_mejoras_p8-gold.json"
    echo "  📄 /data/e3/prueba_mejoras_p8-gold-docs.json"
fi

echo ""
echo -e "${YELLOW}Siguiente paso:${NC}"
echo "  Si alcanzó 80%+ → Load test completo (1,251 docs)"
echo "  Si no alcanzó → Revisar campos que aún fallan"
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ✅ Prueba completada                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
