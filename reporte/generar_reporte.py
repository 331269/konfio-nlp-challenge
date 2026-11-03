"""Genera el reporte CRISP-DM en PDF.

Las figuras se buscan en reporte/img/<nombre>.png (o .jpg). Si una imagen no existe,
se dibuja un recuadro con su nombre para saber qué captura falta.

Uso:  .venv/Scripts/python.exe reporte/generar_reporte.py
"""
import re
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

TITULO = 'Konfío Challenge: loan classification'
BASE = Path(__file__).parent
IMG = BASE / 'img'
SALIDA = BASE / 'Konfio_Challenge_loan_classification.pdf'

# ---------------------------------------------------------------- estilo
FUENTES = Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('Sans', FUENTES / 'segoeui.ttf'))
pdfmetrics.registerFont(TTFont('Sans-B', FUENTES / 'segoeuib.ttf'))
pdfmetrics.registerFont(TTFont('Sans-I', FUENTES / 'segoeuii.ttf'))
pdfmetrics.registerFont(TTFont('Sans-BI', FUENTES / 'segoeuiz.ttf'))
pdfmetrics.registerFont(TTFont('Mono', FUENTES / 'consola.ttf'))
pdfmetrics.registerFontFamily('Sans', normal='Sans', bold='Sans-B', italic='Sans-I', boldItalic='Sans-BI')

AZUL = colors.HexColor('#2A6FDB')
AZUL_OSC = colors.HexColor('#1B3A6B')
GRIS = colors.HexColor('#5B6472')
GRIS_CLARO = colors.HexColor('#EEF2F8')
LINEA = colors.HexColor('#C9D3E3')
VERDE = colors.HexColor('#E3F1E6')

ANCHO = letter[0] - 4.4 * cm   # ancho útil

st = {
    'portada_t': ParagraphStyle('pt', fontName='Sans-B', fontSize=26, leading=32, textColor=AZUL_OSC),
    'portada_s': ParagraphStyle('ps', fontName='Sans', fontSize=13, leading=18, textColor=GRIS),
    'h1': ParagraphStyle('h1', fontName='Sans-B', fontSize=17, leading=22, textColor=AZUL_OSC,
                         spaceBefore=4, spaceAfter=8, keepWithNext=1),
    'h2': ParagraphStyle('h2', fontName='Sans-B', fontSize=12.5, leading=16, textColor=AZUL,
                         spaceBefore=10, spaceAfter=4, keepWithNext=1),
    'p': ParagraphStyle('p', fontName='Sans', fontSize=10, leading=14.2, spaceAfter=5),
    'li': ParagraphStyle('li', fontName='Sans', fontSize=10, leading=14),
    'cel': ParagraphStyle('cel', fontName='Sans', fontSize=8.8, leading=11.5),
    'cel_b': ParagraphStyle('celb', fontName='Sans-B', fontSize=8.8, leading=11.5, textColor=colors.white),
    'cap': ParagraphStyle('cap', fontName='Sans-I', fontSize=8.8, leading=11.5, textColor=GRIS,
                          alignment=TA_CENTER, spaceBefore=3, spaceAfter=10),
    'ph': ParagraphStyle('ph', fontName='Sans', fontSize=9, leading=12.5, textColor=GRIS, alignment=TA_CENTER),
    'nota': ParagraphStyle('nota', fontName='Sans', fontSize=9.2, leading=13),
}


def fmt(texto):
    """Mini-markdown: **negrita**, *cursiva* y `código`."""
    texto = texto.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    texto = re.sub(r'`([^`]+)`', r'<font name="Mono" color="#1B3A6B">\1</font>', texto)
    texto = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', texto)
    texto = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', texto)
    return texto


def P(texto, estilo='p'):
    return Paragraph(fmt(texto), st[estilo])


def H1(texto):
    return Paragraph(fmt(texto), st['h1'])


def H2(texto):
    return Paragraph(fmt(texto), st['h2'])


def lista(items, numerada=False):
    return ListFlowable([ListItem(P(i, 'li'), leftIndent=12, value=None) for i in items],
                        bulletType='1' if numerada else 'bullet', start='1' if numerada else '•',
                        leftIndent=14, bulletFontName='Sans', bulletFontSize=9.5, spaceAfter=6)


def tabla(filas, anchos, resaltar=None):
    """Tabla con encabezado azul; `resaltar` = índice de fila (sin contar encabezado) a sombrear."""
    datos = [[Paragraph(fmt(str(c)), st['cel_b']) for c in filas[0]]]
    datos += [[Paragraph(fmt(str(c)), st['cel']) for c in f] for f in filas[1:]]
    t = Table(datos, colWidths=[a * cm for a in anchos], repeatRows=1)
    estilo = [
        ('BACKGROUND', (0, 0), (-1, 0), AZUL_OSC),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRIS_CLARO]),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, LINEA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
    ]
    if resaltar is not None:
        estilo.append(('BACKGROUND', (0, resaltar + 1), (-1, resaltar + 1), VERDE))
    t.setStyle(TableStyle(estilo))
    return t


def nota(texto):
    t = Table([[P(texto, 'nota')]], colWidths=[ANCHO])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), GRIS_CLARO),
                           ('LINEBEFORE', (0, 0), (0, -1), 3, AZUL),
                           ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                           ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
    return t


N_FIG = [0]
FIGURAS = []   # (nombre, descripción, fuente) para el listado final


def figura(nombre, titulo, fuente, alto_cm=6.0):
    """Inserta reporte/img/<nombre>.png si existe; si no, un recuadro con el nombre esperado."""
    N_FIG[0] += 1
    FIGURAS.append((nombre, titulo, fuente))
    pie = Paragraph(f'Figura {N_FIG[0]}. {fmt(titulo)}', st['cap'])
    ruta = next((IMG / f'{nombre}{ext}' for ext in ('.png', '.jpg', '.jpeg') if (IMG / f'{nombre}{ext}').exists()),
                None)
    if ruta:
        w, h = ImageReader(str(ruta)).getSize()
        escala = min(ANCHO / w, 19 * cm / h, 1.0 if w > ANCHO else ANCHO / w)
        cuerpo = Image(str(ruta), width=w * escala, height=h * escala)
    else:
        texto = (f'<font name="Mono" size="10" color="#1B3A6B">{nombre}.png</font><br/>'
                 f'Espacio para imagen: {fmt(fuente)}')
        cuerpo = Table([[Paragraph(texto, st['ph'])]], colWidths=[ANCHO], rowHeights=[alto_cm * cm])
        cuerpo.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 1, AZUL, 1, (5, 3)),
                                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7F9FC')),
                                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    return KeepTogether([cuerpo, pie])


def diagrama_pipeline():
    """Texto, Transformer ajustado, vector de 768, LogReg por etiqueta y probabilidades."""
    w, h = ANCHO, 3.3 * cm
    d = Drawing(w, h)
    cajas = [('Texto', 'motivos', colors.HexColor('#F7F9FC'), AZUL_OSC),
             ('Transformer', 'Fine-Tuning (DL)', AZUL, colors.white),
             ('Vector de 768', 'features', colors.HexColor('#F7F9FC'), AZUL_OSC),
             ('LogReg', 'por etiqueta (ML)', AZUL_OSC, colors.white),
             ('10 probabilidades', 'umbral por etiqueta', colors.HexColor('#F7F9FC'), AZUL_OSC)]
    n, sep = len(cajas), 0.55 * cm
    bw = (w - sep * (n - 1)) / n
    y, bh = 0.55 * cm, 2.1 * cm
    for i, (t1, t2, fondo, tinta) in enumerate(cajas):
        x = i * (bw + sep)
        d.add(Rect(x, y, bw, bh, rx=6, ry=6, fillColor=fondo, strokeColor=AZUL, strokeWidth=1))
        d.add(String(x + bw / 2, y + bh * 0.56, t1, fontName='Sans-B', fontSize=8.6, fillColor=tinta,
                     textAnchor='middle'))
        d.add(String(x + bw / 2, y + bh * 0.28, t2, fontName='Sans', fontSize=7.6, fillColor=tinta,
                     textAnchor='middle'))
        if i < n - 1:
            ax, ay = x + bw + 0.08 * cm, y + bh / 2
            d.add(Polygon([ax, ay - 4, ax + sep - 0.16 * cm, ay, ax, ay + 4], fillColor=GRIS, strokeColor=None))
    return d


def pie_pagina(canvas, doc):
    canvas.saveState()
    canvas.setFont('Sans', 8)
    canvas.setFillColor(GRIS)
    canvas.drawString(2.2 * cm, 1.2 * cm, TITULO)
    canvas.drawRightString(letter[0] - 2.2 * cm, 1.2 * cm, f'{doc.page}')
    canvas.setStrokeColor(LINEA)
    canvas.line(2.2 * cm, 1.55 * cm, letter[0] - 2.2 * cm, 1.55 * cm)
    canvas.restoreState()


# ---------------------------------------------------------------- contenido
h = []

# Portada
h += [Spacer(1, 5 * cm),
      Paragraph(TITULO, st['portada_t']), Spacer(1, 8),
      Paragraph('Clasificación multietiqueta del destino del crédito siguiendo CRISP-DM', st['portada_s']),
      Spacer(1, 14),
      Paragraph('Fine-Tuning de un Transformer multi-lenguaje para generar features y Regresión Logística '
                'como clasificador', st['portada_s']),
      Spacer(1, 3 * cm),
      Paragraph('Christian Luis Clemente Cortés', st['portada_s']),
      Paragraph('Noviembre 2026', st['portada_s']), Spacer(1, 6),
      Paragraph('Código: github.com/331269/konfio-nlp-challenge', st['portada_s']),
      PageBreak()]

# Resumen ejecutivo
h += [H1('Resumen ejecutivo'),
      P('En este documento presentamos el desarrollo del challenge de Konfío, el cual consiste en clasificar el motivo '
        'por el que un cliente solicita un crédito (la columna motivos) en 10 etiquetas que no son excluyentes entre '
        'sí, es decir, un mismo texto puede tener más de una etiqueta. El reto es superar los resultados que se nos '
        'presentan en la descripción del proyecto (LASER y Regresión Logística): un Hamming loss de 0.0682 y un '
        'average precision de 67%.'),
      lista([
          '**Nuestra solución:** hicimos Fine-Tuning de un Transformer multi-lenguaje '
          '(`paraphrase-multilingual-mpnet-base-v2`) para generar las features de cada texto y, con ellas, entrenamos '
          'una Regresión Logística por etiqueta (Binary Relevance), con un umbral de decisión distinto para cada '
          'etiqueta.',
          '**Resultados en test:** nuestro modelo champion obtiene un Hamming loss de **0.0538**, es decir, 21% menos '
          'errores que el baseline de Konfío, un AP_macro de **0.741**, un F1_macro de **0.689** y el 62.5% de los '
          'textos con todas sus etiquetas correctas.',
          '**Hallazgo principal:** la etiqueta temp, la más débil, no falla solo porque tiene pocos registros: en el '
          'dataset se etiquetó con dos criterios distintos ("de temporada" y "temporal"). La mejora con mayor impacto '
          'sería redefinir esta etiqueta y volver a etiquetar sus textos.',
          '**Calidad de los datos:** nos topamos con un registro dañado en el CSV, registros con etiquetas recorridas '
          'y textos duplicados con etiquetas que se contradicen. Todos estos problemas se corrigieron y se validaron '
          'con k-NN y distancia de coseno.',
      ]),
      Spacer(1, 4),
      tabla([['Métrica (test, 1,300 textos)', 'Konfío (LASER y LogReg)', 'TF-IDF y LogReg', 'Modelo champion'],
             ['Hamming loss con umbral 0.5 (menor es mejor)', '0.0682', '0.0652', '**0.0538**'],
             ['AP_macro (mayor es mejor)', '0.67', '0.665', '**0.741**'],
             ['F1_macro con umbrales por etiqueta (mayor es mejor)', 'No reportado', '0.642', '**0.689**'],
             ['Exact match (mayor es mejor)', 'No reportado', '54.0%', '**62.5%**']],
            [6.4, 3.6, 3.1, 3.1]),
      Spacer(1, 4),
      P('*Hay que tomar en cuenta que nuestros datos fueron depurados y que en la descripción del ejercicio no se '
        'especifica si el average precision es macro o micro, por lo que la comparación con Konfío no es exacta.*'),
      PageBreak()]

# 1. Business Understanding
h += [H1('1. Business Understanding'),
      P('Como parte del proceso de evaluación de los clientes, Konfío pregunta el motivo por el cual necesitan el '
        'crédito. Conocer ese motivo tiene muchas aplicaciones, por lo que es importante clasificar cada respuesta de '
        'manera automática con la etiqueta que le corresponde. Algo que hay que tomar en cuenta es que un cliente '
        'puede pedir el crédito para varias cosas a la vez (por ejemplo, comprar inventario y pagar la nómina), por lo '
        'que este es un problema de clasificación multietiqueta.'),
      H2('Objetivo'),
      lista(['Superar los resultados presentados por Konfío: un Hamming loss de 0.06821 y un average precision de 67%, '
             'en donde la etiqueta con peor desempeño es temp.',
             'Partir de un modelo de deep learning que genere features a partir de los textos y, después, usar esas '
             'features para entrenar un clasificador de machine learning tradicional.',
             'Documentar cada una de las decisiones que tomamos para que se pueda seguir el proceso.']),
      H2('Etiquetas'),
      tabla([['Etiqueta', 'Significado'],
             ['cred', 'Pago de deudas'],
             ['equ', 'Compra de equipo'],
             ['inic', 'Empezar un negocio'],
             ['mkt', 'Marketing'],
             ['no', 'Uso no destinado a capital de trabajo'],
             ['renta', 'Renta'],
             ['sueldo', 'Pago de salarios'],
             ['temp', 'Ventas estacionales'],
             ['crec', 'Expansión: no se proporcionó un motivo o plan específico, pero se insinuó una estrategia de '
                      'crecimiento'],
             ['inv', 'No se menciona en la descripción del proyecto, pero es la etiqueta con más presencia y '
                     'posiblemente se refiere a **inventario**']],
            [2.5, 13.7]),
      PageBreak()]

# 2. Data Understanding
h += [H1('2. Data Understanding'),
      P('El dataset consiste en una columna de texto (motivos) y 10 columnas de etiquetas con valores de 0 y 1. Desde '
        'el principio notamos algo extraño: se supone que el dataset debería tener 6,726 registros, sin embargo, al '
        'leerlo solo obtenemos **6,679**, lo que significa que puede haber problemas con el archivo. Como veremos en '
        'la sección 3.1, se trata de un problema de comillas y saltos de línea.'),
      H2('Distribución de las etiquetas'),
      P('Como podemos observar, contamos con un dataset totalmente desbalanceado: inv y equ aparecen en '
        'aproximadamente un tercio de los textos, mientras que sueldo y temp no llegan ni al 3.5%. Esto es sumamente '
        'importante, ya que nos obliga a dividir los datos de manera estratificada y a usar métricas que no escondan '
        'el desempeño de las etiquetas con menos presencia.'),
      figura('fig01_distribucion_etiquetas', 'Distribución de valores 0 y 1 por etiqueta.',
             'gráfica "Distribución por columna (0 / 1)"', 6.5),
      figura('fig02_prevalencia_etiquetas', 'Porcentaje de textos con cada etiqueta.',
             'gráfica de barras "% de filas con valor 1"', 6.0),
      H2('Un problema multietiqueta'),
      P('En el dataset ya limpio, el 13.2% de los textos tiene más de una etiqueta, lo que confirma que debemos '
        'tratar el problema como multietiqueta y no como multiclase.'),
      tabla([['Etiquetas por texto', 'Textos', '%'], ['1', '5,672', '86.8%'], ['2', '798', '12.2%'],
             ['3', '63', '1.0%']], [5, 3, 3]),
      H2('Características de los textos'),
      lista(['Son textos cortos: la mitad de ellos tiene 71 caracteres o menos.',
             'Tienen faltas de ortografía, textos completamente en mayúsculas, caracteres repetidos ("Mmmmm", "....") '
             'y textos basura ("-1", "G").',
             'Nos topamos con un texto en inglés, lo cual nos sugiere que la mejor decisión es usar un modelo '
             'multi-lenguaje.',
             'Encontramos problemas de calidad: un registro dañado, 6 registros con nulos en temp y textos repetidos '
             'con etiquetas distintas entre sí. Estos problemas los resolvemos en la siguiente sección.']),
      PageBreak()]

# 3. Data Preparation
h += [H1('3. Data Preparation'),
      P('Para cada problema que encontramos usamos un criterio claro y, cuando tuvimos que asignar etiquetas, también '
        'validamos qué tan confiable era nuestro método. En la siguiente tabla se resume cada paso:'),
      tabla([['Paso', 'Problema', 'Solución', 'Registros'],
             ['Lectura del CSV', 'Comilla sin cerrar que se "comía" las líneas siguientes', 'Reparar el archivo',
              'De 6,679 a 6,701'],
             ['Null Values Handling', '6 registros con nulos en temp', 'Recorrer las etiquetas una columna (validado con k-NN)',
              '6,701'],
             ['Normalización', 'Caracteres repetidos', 'Limitar las repeticiones', '6,701'],
             ['Textos basura', 'Textos sin contenido', 'Regla de letras y vocales', '6,697'],
             ['Duplicados iguales', 'Copias con las mismas etiquetas', 'Conservar una sola copia', '6,615'],
             ['Duplicados en conflicto', '57 textos (139 registros) con etiquetas distintas', 'k-NN sobre las etiquetas de las copias',
              '**6,533**']],
            [3.3, 4.6, 5.3, 3.0]),
      H2('3.1 El CSV dañado'),
      P('Para entender qué pasaba con los registros faltantes, revisamos la longitud de los textos, cuántos saltos de '
        'línea tenían y si había textos que contenían algo con forma de fila de etiquetas (por ejemplo '
        '",0,0,1,0,0,0,0,0,0,0"). Así encontramos un registro con **1,920 caracteres y 23 saltos de línea** que tenía '
        'dentro filas completas del CSV. Lo que sucede es que el texto "Capital de trabajo abre una comilla que nunca '
        'se cierra (línea 1,135 del archivo), por lo que pandas lee las líneas siguientes como parte del mismo texto. '
        'Después de reparar el archivo recuperamos **22 registros** y llegamos a 6,701. Revisamos el archivo de otras '
        'maneras y no encontramos más problemas de comillas, por lo que los 25 registros que faltan para llegar a '
        '6,726 no se encuentran en el archivo.'),
      figura('fig03_diagnostico_csv', 'Síntomas del registro dañado y línea con la comilla faltante.',
             'tabla de síntomas (registro 1130) y salida "Línea 1135: posible comilla faltante"', 4.5),
      H2('3.2 Null Values Handling: etiquetas recorridas'),
      P('Nos encontramos con 6 registros con nulos, todos en la etiqueta temp. Deshacernos de ellos no era buena idea, '
        'tomando en cuenta que temp tiene muy poca presencia en el dataset. Al revisar el archivo con el módulo csv '
        'vimos que estos registros tienen 9 valores en lugar de 10, lo que nos llevó a la siguiente **hipótesis:** las '
        'etiquetas están corridas una columna a la izquierda.'),
      P('Para contrastarla usamos TF-IDF, distancia de coseno y un algoritmo tipo k-NN (k = 7): calculamos qué tanto '
        'coinciden las etiquetas de cada texto con las de sus 7 textos más parecidos. El puntaje promedio fue de '
        '**0.00** para las etiquetas como se leyeron y de **0.54** para las etiquetas recorridas, lo que da peso a '
        'nuestra hipótesis. Por lo tanto, recorrimos las etiquetas una columna a la derecha. El único registro que '
        'quedó sin ninguna etiqueta se completó con el mismo k-NN (crec).'),
      figura('fig04_filas_desplazadas', 'Etiquetas leídas, recorridas y las que sugiere el k-NN para los 6 registros.',
             'tabla comparativa leídas / recorridas / kNN', 4.5),
      H2('3.3 Limpieza de los textos'),
      P('Hicimos una normalización de los textos limitando las letras repetidas 3 o más veces y los signos repetidos '
        '("Mmmmmm" se convierte en "M"). Después eliminamos 4 textos basura, es decir, textos con menos de 3 letras o '
        'con muy pocas vocales. No lematizamos ni pasamos los textos a minúsculas para el Transformer, ya que su '
        'tokenización por subpalabras y el contexto ya manejan esas variaciones, y lematizar elimina información útil, '
        'como el tiempo verbal.'),
      figura('fig05_textos_basura', 'Textos eliminados por ser basura.',
             'salida "Textos eliminados por basura"', 3.0),
      H2('3.4 Noise handling: textos repetidos con etiquetas distintas'),
      P('Hay textos que aparecen varias veces: algunos con las mismas etiquetas en todas sus copias, de los cuales solo '
        'conservamos una copia, y otros con etiquetas que se contradicen (57 textos y 139 registros). Para estos '
        'últimos usamos de nuevo k-NN y distancia de coseno, pero esta vez el algoritmo solo puede elegir entre las '
        'etiquetas que aparecen en alguna de las copias, y se queda con las que alcanzan un puntaje de al menos 0.4 '
        'entre los 7 textos más parecidos que no tienen conflicto. Para saber qué tan confiable es este método, lo '
        'validamos de dos maneras:'),
      lista(['Con los 66 textos confiables (textos repetidos cuyas copias tienen las mismas etiquetas), sin dejar que '
             'el algoritmo tome en cuenta el propio texto para evitar data leakage: **67%** de coincidencia exacta.',
             'Simulando 1,000 conflictos, es decir, a las etiquetas verdaderas de un texto les agregamos una etiqueta '
             'falsa al azar: **78%** de coincidencia exacta. Si nos quedáramos con todas las etiquetas de las copias, '
             'la coincidencia sería de 0%.']),
      P('También comparamos el resultado contra una votación por mayoría y solo coincidieron en el 23% de los casos. '
        'Esto se debe a que, cuando hay dos copias que no coinciden, cada etiqueta tiene la mitad de los votos y la '
        'votación se queda con todas, por lo que en realidad no resuelve el conflicto.'),
      figura('fig06_conflictos_knn', 'Validación del k-NN y resultado de los conflictos.',
             'salidas de las validaciones 1 y 2 y de "kNN coincide con la votación…"', 3.5),
      H2('3.5 Entrenamiento y prueba'),
      P('Para dividir el dataset en entrenamiento y prueba usamos la función iterative_train_test_split de la librería '
        'skmultilearn, que hace una división estratificada para problemas multietiqueta. Separamos el 20% para test y '
        'obtuvimos **5,233** textos de entrenamiento y **1,300** de test, en donde la proporción de cada etiqueta es '
        'prácticamente la misma en ambos conjuntos. El conjunto de test solo lo usamos una vez, al final.'),
      figura('fig07_split_estratificado', 'Proporción de cada etiqueta en train y test.',
             'tabla de prevalencias train / test', 5.5),
      PageBreak()]

# 4. Modeling
h += [H1('4. Modeling'),
      P('Para transformar los textos en datos numéricos comparamos tres representaciones, todas con el mismo '
        'procedimiento y con una Regresión Logística por etiqueta (Binary Relevance), que fue el modelo con el que '
        'Konfío obtuvo sus mejores resultados:'),
      lista(['**TF-IDF** con palabras únicas y pares de palabras, como benchmark a superar.',
             '**Embeddings preentrenados** del Transformer, sin ajustar.',
             '**Embeddings después de hacer Fine-Tuning**, que es nuestra propuesta.']),
      H2('4.1 Cross-Validation'),
      P('Usamos Cross-Validation con 5 folds y un IterativeStratification para que la distribución de las etiquetas se '
        'mantenga en cada fold. Para cada texto de entrenamiento obtenemos una probabilidad out-of-fold (OOF), es '
        'decir, una predicción hecha por un modelo que no vio ese texto al entrenar. Con estas probabilidades elegimos '
        'los hiperparámetros (C y class_weight) y los umbrales. Las mejores configuraciones fueron TF-IDF con C = 3 '
        '(AP_macro de 0.699) y embeddings preentrenados con C = 10 (AP_macro de 0.670).'),
      P('Inesperadamente, los embeddings preentrenados quedaron por debajo del TF-IDF. Esto puede deberse a que el '
        'modelo preentrenado agrupa los textos según qué tan parecido es su significado en general, lo cual no '
        'coincide con las etiquetas de Konfío: por ejemplo, "comprar mercancía" y "comprar mercancía para la temporada '
        'navideña" significan casi lo mismo, pero deberían tener etiquetas distintas. Esto nos llevó a hacer '
        'Fine-Tuning.'),
      figura('fig08_resultados_cv', 'AP_macro y AP_micro en Cross-Validation por representación, C y class_weight.',
             'tabla_cv', 7.0),
      H2('4.2 Umbrales por etiqueta'),
      P('El umbral de 0.5 no es la mejor opción para las etiquetas con poca presencia, ya que el modelo casi nunca les '
        'asigna probabilidades tan altas. Por eso, para cada etiqueta buscamos el umbral (entre 0.05 y 0.95) que '
        'maximiza su F1 usando las probabilidades OOF. Con TF-IDF, el F1_macro pasó de 0.48 a 0.68, mientras que el '
        'AP_macro no cambió, ya que no depende del umbral.'),
      figura('fig09_umbrales_cv', 'Mejores umbrales y métricas con umbral de 0.5 y con umbrales por etiqueta (OOF).',
             'salida de mejores_umbrales y su tabla', 5.5),
      H2('4.3 Modelo base'),
      P('Para hacer el Fine-Tuning usamos el mismo modelo con el que creamos los embeddings, '
        '`paraphrase-multilingual-mpnet-base-v2` de la librería sentence-transformers. Es un Transformer con '
        'arquitectura XLM-RoBERTa base: 12 capas, vectores de 768 dimensiones y aproximadamente 278 millones de '
        'parámetros. Fue entrenado a partir de un modelo de paráfrasis para que frases con el mismo significado, en '
        'más de 50 idiomas, tengan vectores parecidos. Lo elegimos porque está entrenado para similitud semántica, '
        'conserva el soporte multi-lenguaje que Konfío valoró en LASER, su tokenización por subpalabras tolera las '
        'faltas de ortografía y, a diferencia de LASER, permite hacer Fine-Tuning de manera estándar en una GPU de '
        '6 GB.'),
      H2('4.4 Arquitectura: deep learning para las features y machine learning para clasificar'),
      diagrama_pipeline(),
      Spacer(1, 6),
      P('Para hacer el Fine-Tuning le agregamos al Transformer una cabeza lineal con 10 salidas, una por etiqueta, cada '
        'una con su propia función sigmoide para que las etiquetas sean independientes, y usamos la entropía cruzada '
        'binaria como función de pérdida. Al entrenar, el error ajusta las capas del Transformer, de tal manera que '
        'los textos con las mismas etiquetas quedan más cerca entre sí. La cabeza es temporal: después del '
        'entrenamiento se descarta y nos quedamos con el vector de 768 dimensiones de cada texto (el promedio de sus '
        'tokens, normalizado). Estos vectores son las features con las que entrenamos la Regresión Logística.'),
      tabla([['Decisión', 'Valor', 'Por qué'],
             ['Capa de vocabulario', 'Congelada (192 de 278 millones de parámetros)',
              'Ahorra memoria en la GPU y evita overfitting'],
             ['Learning rate', '3e-5 para el Transformer y 1e-3 para la cabeza',
              'La cabeza empieza desde cero y necesita aprender más rápido; el Transformer ya fue entrenado y no debe '
              'perder lo que aprendió'],
             ['Cambio del learning rate', 'Warmup en el primer 10% de los pasos y después baja hasta 0',
              'El entrenamiento empieza de manera estable y termina con ajustes pequeños'],
             ['Regularización', 'AdamW con weight decay de 0.01 y dropout de 0.1', 'Evitan overfitting'],
             ['Entrenamiento', '6 epochs, batch de 32 y precisión mixta (fp16)',
              'Con 4 epochs y un solo learning rate el modelo no alcanzaba a aprender'],
             ['Longitud máxima', '128 tokens', 'Los textos son cortos, por lo que no se pierde información']],
            [3.4, 5.2, 7.6]),
      H2('4.5 Cross-Fitting'),
      P('Si hacemos el Fine-Tuning con todo el conjunto de entrenamiento y después predecimos esos mismos textos, las '
        'probabilidades salen infladas, ya que el modelo prácticamente se los aprendió. Por eso hicimos cross-fitting, '
        'que consiste en repetir todo el proceso (Fine-Tuning, extracción de features y Regresión Logística) dentro de '
        'cada uno de los 5 folds, usando solo los textos de entrenamiento de cada fold. De esta manera, todas las '
        'probabilidades que usamos para elegir hiperparámetros y umbrales provienen de textos que el modelo no vio. '
        'Cada fold genera features distintas, por lo que cada uno entrena su propia Regresión Logística, y la '
        'predicción final sobre test es el promedio de los 5 modelos.'),
      figura('fig10_perdida_finetuning', 'Pérdida en cada epoch del Fine-Tuning para cada fold.',
             'salida del ciclo de cross-fitting', 5.0),
      H2('4.6 Comparación de todas las representaciones'),
      tabla([['Modelo', 'AP_macro (OOF)'],
             ['**Fine-Tuning, extracción de features y LogReg (C = 0.3)**', '**0.7537**'],
             ['Fine-Tuning, extracción de features y LogReg (C = 1)', '0.7526'],
             ['Fine-Tuning, extracción de features y LogReg (C = 3)', '0.7503'],
             ['Fine-Tuning, extracción de features y LogReg (C = 10)', '0.7471'],
             ['Fine-Tuning usando la cabeza del modelo', '0.7446'],
             ['TF-IDF y LogReg', '0.6994'],
             ['Embeddings preentrenados y LogReg', '0.6695']],
            [11.0, 4.0], resaltar=0),
      Spacer(1, 6),
      P('Como podemos observar, el Fine-Tuning es lo que hace la diferencia: mejora el AP_macro en 5.4 puntos con '
        'respecto al TF-IDF y en 8.4 puntos con respecto a los mismos embeddings sin ajustar. Además, la Regresión '
        'Logística sobre las features supera a la cabeza del propio Transformer, ya que se entrena con features que ya '
        'no cambian, encuentra su mejor solución y usa la regularización que elegimos con Cross-Validation.'),
      PageBreak()]

# 5. Evaluation
h += [H1('5. Evaluation'),
      H2('5.1 Métricas'),
      P('En la descripción del ejercicio se menciona el average precision, pero no se especifica si es el AP macro o '
        'micro, por lo que revisamos varias métricas. Nuestro enfoque está en el Hamming loss, el AP_macro y el '
        'F1_macro, ya que son las que mejor funcionan para problemas multietiqueta desbalanceados.'),
      tabla([['Métrica', 'Qué mide', 'Por qué la usamos'],
             ['Hamming loss', 'Proporción de decisiones incorrectas (texto y etiqueta)', 'Es la métrica que optimizó Konfío'],
             ['**AP_macro** (principal)', 'Qué tan bien ordena el modelo los textos en cada etiqueta, dando el mismo '
                                          'peso a todas',
              'No depende del umbral y le da la misma importancia a las etiquetas con poca presencia, como temp'],
             ['AP_micro', 'Lo mismo, pero tomando todas las etiquetas juntas',
              'Da una visión general, aunque la dominan las etiquetas más frecuentes'],
             ['F1_macro y F1_micro', 'Balance entre precision y recall de las decisiones finales',
              'Nos dice el efecto de los umbrales'],
             ['Exact match', 'Porcentaje de textos con sus 10 etiquetas correctas',
              'Es la métrica más estricta y es fácil de comunicar']],
            [3.4, 6.2, 6.6]),
      H2('5.2 Resultados en test'),
      P('Evaluamos los cuatro modelos en test una sola vez, tanto con un umbral de 0.5 como con los umbrales por '
        'etiqueta que encontramos en Cross-Validation.'),
      figura('fig11_resultados_test', 'Resultados en test de los cuatro modelos.',
             'tabla de la evaluación final en test', 7.0),
      lista(['Nuestro modelo champion es el que hace Fine-Tuning, extracción de features y Regresión Logística: obtiene '
             'el mejor Hamming loss (0.0538) y el mejor AP_macro (0.741).',
             'Los resultados de Cross-Validation (AP_macro de 0.754) y de test (0.741) coinciden, por lo que no hay '
             'señales de overfitting.',
             'Los umbrales por etiqueta mejoran el F1_macro (de 0.647 a 0.689), pero empeoran un poco el Hamming loss '
             '(de 0.054 a 0.058), ya que detectan más casos de las etiquetas con poca presencia a cambio de algunas '
             'falsas alarmas. Cuál conviene más depende de para qué se vaya a usar el modelo en el negocio.']),
      H2('5.3 Resultados por etiqueta'),
      figura('fig12_metricas_por_etiqueta', 'Proporción, umbral, precision, recall, F1 y AP de cada etiqueta.',
             'tabla por etiqueta del modelo final y su coincidencia exacta', 6.0),
      P('En esta tabla podemos observar los umbrales de cada etiqueta de nuestro modelo champion y su comportamiento en '
        'cada métrica. Algo interesante es que tener poca presencia no significa que una etiqueta sea difícil de '
        'predecir: mkt (5%) y sueldo (3%) obtienen un F1 de 0.82 y 0.77, ya que usan palabras muy claras. Tomemos, por '
        'ejemplo, el caso de temp:'),
      lista(['Precision de 0.26: de cada 4 textos que el modelo marca como temp, solo 1 lo es.',
             'Recall de 0.36: encuentra aproximadamente 1 de cada 3 textos temp reales.',
             'AP de 0.23: es bajo, pero es 8 veces mejor que el azar (0.028).']),
      P('Por su parte, inic es la segunda etiqueta con peor desempeño (F1 de 0.55).'),
      H2('5.4 Análisis de errores'),
      P('Como complemento, hicimos una especie de matriz de confusión para problemas multietiqueta: contamos cuántas '
        'veces el modelo dejó fuera una etiqueta y puso otra en su lugar. Las confusiones más frecuentes son: el '
        'modelo puso equ en lugar de inv (29 veces), inv en lugar de equ (24), crec en lugar de inv (15), inv en lugar '
        'de temp (13) y temp en lugar de cred (10). El caso de equ e inv es entendible, ya que se usan palabras muy '
        'parecidas para ambas etiquetas (por ejemplo, "mercancía y equipo"). Más aún, sigue ocurriendo algo muy '
        'extraño entre temp e inv.'),
      figura('fig13_errores_por_etiqueta', 'Aciertos, falsos negativos y falsos positivos de cada etiqueta.',
             'tabla de errores por etiqueta', 5.5),
      figura('fig14_sustituciones', 'Etiqueta que el modelo dejó fuera (filas) y la que puso en su lugar (columnas).',
             'matriz "omitió / puso en su lugar"', 6.0),
      H2('5.5 El caso de temp'),
      P('Al revisar los textos mal clasificados de temp, nos encontramos con algo que parece al revés: los textos que '
        'claramente hablan de temporada ("Inventario de textil para ventas navideñas") reciben una probabilidad de temp '
        'de apenas 0.01, mientras que los textos sobre clientes que pagan a 60 o 120 días o contratos ganados reciben '
        'las probabilidades más altas.'),
      figura('fig15_ejemplos_temp', 'Falsos negativos y falsos positivos de temp.',
             'tablas de ejemplos FN y FP de temp', 6.5),
      P('Pero... ¿esto es un error del modelo? Para descubrirlo, buscamos en todo el dataset palabras relacionadas con '
        'temporada (navidad, diciembre, regreso a clases, temporada, etc.):'),
      lista(['142 de los 182 textos con temp (**78%**) no incluyen ninguna palabra de temporada; en realidad hablan de '
             'necesidades **temporales** de dinero: proyectos, contratos y clientes que pagan tarde.',
             '103 de los 143 textos que sí hablan de temporada (**72%**) no tienen la etiqueta temp; la mayoría tienen '
             'inv.',
             'Hay palabras que se usan mucho más en temp que en el resto del dataset: "cliente" aparece en el 26% de '
             'los textos temp contra el 7% en general, y "proyecto" en el 20% contra el 5%.']),
      figura('fig16_analisis_temp', 'Relación entre las palabras de temporada y la etiqueta temp.',
             'salida del análisis de palabras de temporada', 5.5),
      nota('**Conclusión:** posiblemente el etiquetado de temp no se está haciendo del todo correctamente, ya que mezcla '
           'dos conceptos: "de temporada" y "temporal". El modelo aprendió exactamente lo que hay en los datos, por lo '
           'que, aunque tuviéramos más textos etiquetados con el mismo criterio, el problema seguiría ahí.'),
      H2('5.6 Posible ruido en el etiquetado'),
      P('Tomando en cuenta lo que ocurrió con temp, revisamos los casos en los que el modelo está casi seguro y aun así '
        'se equivoca (probabilidad menor a 0.05 cuando la etiqueta real es 1, o mayor a 0.95 cuando es 0). Estos casos '
        'son el 19% de los errores (143 de 746) y en varios de ellos la etiqueta no tiene relación con el texto, por '
        'ejemplo, sueldo en "Adquisición de productos para introducir una nueva línea de medicamentos". Esto quiere '
        'decir que parte de los errores que medimos vienen de las etiquetas y no del modelo.'),
      figura('fig17_confianza_extrema', 'Errores en los que el modelo estaba casi seguro.',
             'tabla de errores con P < 0.05 o P > 0.95', 6.0),
      H2('5.7 Interpretabilidad con SHAP'),
      P('Como las 768 features no se pueden interpretar por sí solas, usamos la librería SHAP sobre todo el proceso '
        '(texto, Transformer, features y Regresión Logística) para saber cuáles son las palabras que más intervienen '
        'en las decisiones del modelo. Para cada palabra, SHAP nos dice cuánto sube o baja la probabilidad de cada '
        'etiqueta.'),
      figura('fig18_shap_temp', 'Cuánto aporta cada palabra a la probabilidad de temp.',
             'gráfica SHAP de texto para temp', 5.0),
      figura('fig19_shap_inv', 'Cuánto aporta cada palabra a la probabilidad de inv.',
             'gráfica SHAP de texto para inv', 5.0),
      figura('fig20_shap_global', 'Palabras con más peso en cada etiqueta (300 textos de test).',
             'tabla de las 6 palabras principales por etiqueta', 6.0),
      lista(['**El modelo aprendió palabras que tienen sentido.** En 8 de las 10 etiquetas, las palabras con más peso '
             'coinciden con su definición, por ejemplo, equ: maquinaria y equipo; mkt: publicidad y marketing; cred: '
             'deudas y liquidar; inv: inventario, stock y mercancía.',
             '**SHAP confirma lo que vimos con temp.** En "Inventario de textil para ventas navideñas", la palabra '
             'navideñas es la que más sube la probabilidad de inv (0.40) y no aporta nada a temp. En general, la '
             'palabra temporada pesa en temp lo mismo que contratos, clientes y proyectos, y la palabra con más peso en '
             'temp tiene 5 veces menos peso que la de equ.',
             '**Nos encontramos con otro insight: renta en realidad se usa para el local y las instalaciones.** Las '
             'palabras con más peso son mobiliario, instalaciones, oficina, remodelación y local, y solo el 11% de los '
             'textos con renta mencionan renta o alquiler. A diferencia de temp, este criterio se usó de la misma '
             'manera en todo el dataset, por lo que el modelo lo aprende bien (F1 de 0.74).']),
      PageBreak()]

# 6. Deployment
h += [H1('6. Deployment'),
      H2('6.1 Modelo para producción'),
      P('El modelo que evaluamos en realidad son 5 modelos, uno por cada fold, cuyas predicciones se promedian. Para '
        'producción entrenamos un solo modelo con todo el conjunto de entrenamiento, usando los mismos '
        'hiperparámetros y umbrales. Este modelo es 5 veces más ligero (aproximadamente 1.1 GB) y obtiene en test un '
        'AP_macro de **0.734** y un Hamming loss de **0.056**: pierde 0.7 puntos de AP_macro con respecto a los 5 '
        'modelos, pero sigue estando por encima del baseline de Konfío.'),
      H2('6.2 Recomendaciones'),
      P('**Datos y etiquetado (es donde esperamos el mayor impacto)**'),
      lista(['**Redefinir temp:** decidir si significa "de temporada" o "temporal", o separarla en dos etiquetas, y '
             'volver a etiquetar los 285 textos involucrados (182 con temp y 103 textos de temporada sin temp).',
             '**Actualizar el codebook:** describir renta como "local e instalaciones" y agregar inv (inventario).',
             '**Guía de etiquetado:** incluir ejemplos de los casos que más se confunden (inv contra equ, crec contra '
             'inic) y pedir que dos personas etiqueten una muestra para medir qué tanto coinciden.',
             '**Revisión guiada por el modelo:** revisar primero los textos en los que el modelo está muy seguro y no '
             'coincide con la etiqueta.',
             '**Corregir la exportación del CSV:** posiblemente se exportó de manera incorrecta, dando paso a problemas '
             'con las comillas y los saltos de línea.']),
      P('**Modelado**'),
      lista(['Probar modelos multi-lenguaje más grandes o más recientes, como los de las familias E5 o XLM-R large.',
             'Ayudar a las etiquetas con poca presencia generando más ejemplos (por ejemplo, con paráfrasis) y '
             'dándoles más peso en la función de pérdida.',
             'Tomar en cuenta la relación entre etiquetas (classifier chains), ya que el 13% de los textos tiene más '
             'de una.']),
      P('**Operación**'),
      lista(['**Elegir el umbral según el uso en el negocio:** el umbral de 0.5 comete menos errores en total (Hamming '
             'loss), mientras que los umbrales por etiqueta detectan más casos de las etiquetas con poca presencia '
             '(F1_macro).',
             '**Revisión humana:** mandar a revisión los textos en los que el modelo tiene poca confianza o no asigna '
             'ninguna etiqueta, mostrando las palabras que llevaron a la predicción (SHAP).',
             '**Monitoreo:** vigilar la distribución de las etiquetas predichas y la confianza promedio del modelo para '
             'detectar drift (por ejemplo, por la temporada real de las solicitudes) y volver a entrenar el modelo con '
             'etiquetas revisadas.']),
      H2('6.3 API'),
      nota('**Sección en construcción.** Aquí vamos a documentar el API que usa el modelo de producción: endpoint, '
           'formato de entrada y salida, y un ejemplo de uso.'),
      H2('6.4 Limitaciones'),
      lista(['Solo usamos una división de test (1,300 textos), por lo que en etiquetas con poca presencia, como temp '
             '(36 textos en test), las métricas por etiqueta pueden variar bastante.',
             'La Regresión Logística de cada fold se entrena con features de textos que su Transformer ya vio. La '
             'evaluación sigue siendo adecuada, ya que validación y test son textos que no vio, y este efecto lo '
             'controlamos con una regularización fuerte (C = 0.3).',
             'El análisis con SHAP lo hicimos sobre el modelo de producción y con una muestra de 300 textos de test.',
             'Entrenamos con una sola semilla; usar varias nos permitiría tener intervalos de confianza.']),
      H2('Reproducibilidad'),
      P('El código y el notebook están en github.com/331269/konfio-nlp-challenge. El entorno se crea con `uv sync` '
        '(Python 3.12 y PyTorch con CUDA 12.8) y el archivo intent.csv se coloca en la carpeta principal del proyecto. '
        'Para el Fine-Tuning se necesita una GPU (lo probamos en una RTX 4050 de 6 GB).')]


doc = SimpleDocTemplate(str(SALIDA), pagesize=letter, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                        topMargin=2.0 * cm, bottomMargin=2.2 * cm,
                        title=TITULO, author='Christian Luis Clemente Cortés')
doc.build(h, onLaterPages=pie_pagina)

faltantes = [f for f in FIGURAS if not any((IMG / f'{f[0]}{e}').exists() for e in ('.png', '.jpg', '.jpeg'))]
print(f'PDF generado: {SALIDA}')
print(f'Figuras: {len(FIGURAS)} | pendientes: {len(faltantes)}')
for nombre, titulo, fuente in faltantes:
    print(f'  {nombre}.png  <-  {fuente}')
