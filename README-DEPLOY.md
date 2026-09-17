# 🚀 Deploy Rápido - Caso 1 v2 - Formularios E3 (Servidor AWS IP: 3.17.139.133)

## ⚡ Despliegue en 3 pasos

### 1️⃣ **Clonar / Actualizar Repo**

```bash
cd ~/Documents/APPS/overthere/ia-analisis
git pull origin main
```

### 2️⃣ **Deploy Automático**

```bash
export SSH_KEY="$HOME/Documents/KEYS/llave/OT-IA-SERVER.pem"
./scripts/deploy_completo_aws.sh
```

**Esto instala:**
- ✅ RabbitMQ (colas)
- ✅ vLLM GPU 0: Qwen2.5-VL-7B (Visión) → :8001
- ✅ vLLM GPU 1: Qwen2.5-7B-AWQ (NLP) → :8000
- ✅ 8 OCR workers + 12 NLP workers
- ✅ **POST-PROCESAMIENTO AUTOMÁTICO** (72.6% → 80%+)

**Tiempo:** ~5 minutos (descarga + carga modelos)

### 3️⃣ **Probar**

```bash
ssh -i "$SSH_KEY" ubuntu@3.17.139.133
cd ~/test-ia-local/caso-1-v2-e3/scripts
./test_mejoras.sh
```

**Resultado esperado:** Confianza real ≥80%

---

## 🎯 ¿Qué hay de nuevo?

### ✨ **Mejoras Implementadas**

| Campo | Error Original | Corregido | Impacto |
|-------|----------------|-----------|---------|
| `direccion` | `C11+389-13` | `Cll 73 # 89-13` | **-50% errores** |
| `telefono_movil` | `3222940576` | `3222940` | **-50% errores** |
| `email` | `cutlook.can` | `outlook.com` | **-50% errores** |
| `ciudad` | `Bo50.t3` | `Bogota` | **-50% errores** |
| `nombres` | `Juan1` | `Juan` | **-50% errores** |

**Resultado total:** **72.6% → ≥80%** confianza real

---

## 📊 Verificar Resultados

**RabbitMQ UI:**  
http://3.17.139.133:15672 (guest / guest)

**GPU Utilization:**
```bash
ssh -i "$SSH_KEY" ubuntu@3.17.139.133
nvidia-smi
```

**Logs en Tiempo Real:**
```bash
ssh -i "$SSH_KEY" ubuntu@3.17.139.133
cd ~/test-ia-local/caso-1-v2-e3
sudo docker compose logs -f ocr nlp
```

---

## 📖 Documentación Completa

Ver: [`docs/deploy-completo-aws.md`](docs/deploy-completo-aws.md)

- Arquitectura detallada
- Troubleshooting
- Comparación contra gold
- Métricas y dashboards

---

## 🔧 Archivos Clave

```
ia-analisis/
├── caso-1-v2-e3/
│   ├── docker-compose.yml           ← Servicios (RabbitMQ, vLLM, workers)
│   ├── workers/
│   │   ├── ocr_worker.py            ← Extrae texto con VLM
│   │   ├── nlp_worker.py            ← Extrae campos + POST-PROCESAMIENTO
│   │   ├── postprocess_express.py   ← 🚀 Reglas de corrección
│   │   └── requirements.txt
│   └── scripts/
│       ├── load_test_simple.py      ← Test de carga
│       └── test_mejoras.sh          ← Test rápido (10 docs)
├── scripts/
│   └── deploy_completo_aws.sh       ← 🚀 Deploy automático
└── docs/
    └── deploy-completo-aws.md       ← Documentación completa
```

---

## ⚠️ Notas Importantes

1. **Instance Store:** `/data` se borra al apagar AWS. Guarda resultados en S3 o local.
2. **Costos:** g7e.12xlarge = $6.24/hora. **Apaga cuando no uses.**
3. **Git:** Todo cambio debe commitearse aquí para no perderlo.
4. **Modelos:** Primera carga descarga 42 GB (Hugging Face cache).

---

**Última actualización:** Sep 17, 2026  
**Servidor actual:** 3.17.139.133  
**Configuración:** Parte 4 - 2× RTX PRO 6000 Ada (96 GB VRAM c/u)
