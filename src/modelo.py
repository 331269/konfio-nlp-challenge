"""Carga del modelo de producción y predicción.

Reproduce el mismo pipeline del notebook:
texto -> Transformer ajustado (Fine-Tuning) -> vector de 768 (mean pooling, normalizado) -> LogReg por etiqueta.
"""
import json
import os
from pathlib import Path

import joblib
import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

RUTA_MODELO = Path(__file__).resolve().parent.parent / 'modelo_final'

# En la nube el modelo no está en el repo (pesa ~1 GB), así que lo descargamos de Hugging Face
REPO_HF = os.environ.get('MODELO_HF')

DESCRIPCIONES = {
    'crec': 'Expansión (estrategia de crecimiento)',
    'cred': 'Pago de deudas',
    'equ': 'Compra de equipo',
    'inic': 'Empezar un negocio',
    'inv': 'Inventario',
    'mkt': 'Marketing',
    'no': 'Uso no destinado a capital de trabajo',
    'renta': 'Renta (local e instalaciones)',
    'sueldo': 'Pago de salarios',
    'temp': 'Ventas estacionales',
}


class ClasificadorCreditos:
    """Modelo champion: encoder ajustado, Regresión Logística por etiqueta y umbrales por etiqueta."""

    def __init__(self, ruta=RUTA_MODELO):
        ruta = Path(ruta)
        if not (ruta / 'encoder').exists() and REPO_HF:
            from huggingface_hub import snapshot_download
            print(f'Descargando el modelo de Hugging Face ({REPO_HF})...', flush=True)
            ruta = Path(snapshot_download(REPO_HF))
            print('Modelo descargado', flush=True)
        if not (ruta / 'encoder').exists():
            raise FileNotFoundError(
                f'No se encontró el modelo en {ruta}. Hay que correr la celda del notebook que entrena y guarda '
                'el modelo final (modelo_final/).')
        with open(ruta / 'config.json', encoding='utf-8') as f:
            config = json.load(f)
        self.labels = config['labels']
        self.umbrales = np.array(config['umbrales'])
        self.max_length = config['max_length']

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.tokenizer = AutoTokenizer.from_pretrained(ruta / 'encoder')
        # El encoder se sube en fp16 para que pese la mitad; en CPU lo regresamos a fp32
        print('Cargando el encoder en memoria...', flush=True)
        self.encoder = AutoModel.from_pretrained(ruta / 'encoder', dtype=torch.float32).to(self.device).eval()
        self.clf = joblib.load(ruta / 'logreg.joblib')
        print(f'Modelo listo ({self.device})', flush=True)

    @torch.no_grad()
    def features(self, textos, batch=64):
        """Vector de 768 de cada texto: promedio de sus tokens (sin padding), normalizado."""
        out = []
        for i in range(0, len(textos), batch):
            enc = self.tokenizer(list(textos[i:i + batch]), padding=True, truncation=True,
                                 max_length=self.max_length, return_tensors='pt').to(self.device)
            with torch.autocast(self.device, dtype=torch.float16, enabled=self.device == 'cuda'):
                h = self.encoder(**enc).last_hidden_state
            m = enc['attention_mask'].unsqueeze(-1).float()
            e = (h.float() * m).sum(1) / m.sum(1).clamp(min=1e-9)
            out.append(torch.nn.functional.normalize(e, dim=1).cpu().numpy())
        return np.vstack(out)

    def predecir_proba(self, textos):
        """Probabilidad de cada una de las 10 etiquetas, forma (n_textos, 10)."""
        return self.clf.predict_proba(self.features([str(t) for t in textos]))

    def predecir(self, textos, usar_umbrales=True):
        """Etiquetas asignadas (0/1) usando los umbrales por etiqueta o un umbral de 0.5."""
        umbral = self.umbrales if usar_umbrales else 0.5
        return (self.predecir_proba(textos) >= umbral).astype(int)
