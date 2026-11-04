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
| **KPI oficial (Parte 15)** | **95,7 %** conf_real vs gold (267 docs, 21 campos) |
| **Baseline Parte 14** | 92,4 % (Qwen2.5-VL-7B) |
| **Throughput Parte 15** | ~934 docs/h (Qwen3.6-27B-FP8 dual) |
| **Hardware** | 2× RTX PRO 6000 Blackwell (96 GB VRAM c/u) |

Detalle: [`pruebas/lote2-e3v2/parte-15/resultados.md`](pruebas/lote2-e3v2/parte-15/resultados.md). Visor: https://shell931.github.io/e3-pages/

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

- **[Índice de pruebas](pruebas/README.md)**: todas las Partes por lote, con su KPI y su entrada en el visor.
- [Planteamientos de infraestructura](planteamientos/README.md), por ejemplo el [Dell RTX 8000](planteamientos/rtx-8000/README.md).
- **[Despliegue oficial — Parte 15](pruebas/lote2-e3v2/parte-15/servidor/DESPLIEGUE.md)**: bundle completo con compose fijado, workers y scripts de operación.
- [Despliegue Parte 14](pruebas/lote2-e3v2/parte-14/servidor/DESPLIEGUE.md) (7B, 92,4 %).
- [Deploy Rápido](README-DEPLOY.md)

```
pruebas/
  lote1-1251/parte-NN/     ← 1.251 frentes, gold / gold_v2 (Partes 4, 8–12)
  lote2-e3v2/parte-NN/     ← 267 frentes E3V2, gold_e3 (Partes 10a–e, 14, 15, 16)
planteamientos/
  rtx-8000/                ← Dell R740xd, 2× Quadro RTX 8000
```

---

**Última actualización**: Sep 17, 2026  
**Servidor AWS**: IP configurable en scripts
