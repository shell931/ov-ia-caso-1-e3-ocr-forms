# 📋 Caso 1: OCR de Formularios E3/E4

Sistema de extracción automática de datos de formularios electorales colombianos E3 y E4 usando Vision Language Models (VLM) y NLP.

## 🎯 Objetivo

Extraer campos estructurados de formularios E3/E4 escaneados con **≥80% de confianza real** mediante:
- **Vision OCR**: Qwen2.5-VL-7B (GPU 0)
- **NLP Extraction**: Qwen2.5-7B-AWQ (GPU 1)
- **Post-procesamiento**: Reglas de corrección automática

## 📊 Resultados Actuales

| Métrica | Valor |
|---------|-------|
| **Confianza Real** | ≥80% (antes: 72.6%) |
| **Throughput** | ~1,700 docs/h |
| **Latency (p95)** | ~3.5s/doc |
| **Hardware** | 2× RTX PRO 6000 Ada (96 GB VRAM c/u) |

## 🚀 Deploy Rápido

```bash
git clone https://github.com/shell931/caso-1-e3-ocr-forms.git
cd caso-1-e3-ocr-forms
export SSH_KEY="$HOME/Documents/KEYS/llave/OT-IA-SERVER.pem"
./scripts/deploy_completo_aws.sh
```

Ver [`README-DEPLOY.md`](README-DEPLOY.md) para instrucciones completas.

## 📁 Estructura

```
caso-1-v2-e3/
├── docker-compose.yml          ← 2 GPUs + RabbitMQ + Workers
├── workers/
│   ├── ocr_worker.py           ← VLM (GPU 0)
│   ├── nlp_worker.py           ← NLP + POST-PROCESAMIENTO
│   ├── postprocess_express.py  ← Reglas de corrección
│   └── requirements.txt
└── scripts/
    ├── load_test_simple.py     ← Test de carga
    └── test_mejoras.sh         ← Test rápido
```

## 🔧 Tecnologías

- **VLM**: Qwen/Qwen2.5-VL-7B-Instruct
- **NLP**: Qwen/Qwen2.5-7B-Instruct-AWQ
- **Inference**: vLLM (OpenAI-compatible API)
- **Queue**: RabbitMQ
- **Deploy**: Docker Compose + AWS EC2 (g7e.12xlarge)

## 📖 Documentación

- [Parte 8 — resultados, modelos y handoff](docs/parte8-resultados.md) (fuente de la corrida publicada en el visor)
- [Parte 9 — gold_v2 teléfonos + discapacidad](docs/parte9-resultados.md)
- [Backup para reinstalar en un servidor físico](backup/parte8-servidor-fisico/LEEME.md) (incluye [PARTE9.md](backup/parte8-servidor-fisico/PARTE9.md))
- [Deploy Completo](docs/deploy-completo-aws.md)
- [Arquitectura](docs/arquitectura-parte4.txt)
- [Deploy Rápido](README-DEPLOY.md)

---

**Última actualización**: Sep 17, 2026  
**Servidor AWS**: IP configurable en scripts
