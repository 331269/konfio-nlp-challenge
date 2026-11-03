# Konfío NLP Challenge

Clasificación multietiqueta del uso de los recursos de solicitudes de crédito (`motivos`), siguiendo CRISP-DM.

**Enfoque:** un Transformer multilingüe (`paraphrase-multilingual-mpnet-base-v2`) ajustado con fine-tuning genera features de texto, y una Regresión Logística por etiqueta (Binary Relevance) clasifica.

| Métrica (test) | Baseline Konfío (LASER + LogReg) | Este modelo |
|---|---|---|
| Hamming loss ↓ | 0.0682 | **0.0538** |
| AP macro ↑ | ~0.67 | **0.741** |

Todo el análisis, las decisiones y los resultados están en [`challenge.ipynb`](challenge.ipynb).

## Cómo reproducir

1. Instalar [uv](https://docs.astral.sh/uv/) y crear el entorno (Python 3.12; PyTorch con CUDA 12.8):
   ```bash
   uv sync
   ```
2. Colocar `intent.csv` (proporcionado por Konfío, no incluido en el repo) en la raíz del proyecto.
3. Ejecutar `challenge.ipynb`. El fine-tuning requiere GPU (probado en una RTX 4050 de 6 GB).
