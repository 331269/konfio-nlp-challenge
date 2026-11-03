"""App de Streamlit para clasificar el motivo de un crédito con el modelo champion.

Uso (desde la carpeta del proyecto):
    uv run streamlit run src/app.py
"""
print('Iniciando la app...', flush=True)
from pathlib import Path

import pandas as pd
import shap
import streamlit as st

from modelo import DESCRIPCIONES, ClasificadorCreditos

st.set_page_config(page_title='Konfío Challenge: loan classification', page_icon='💳', layout='centered')

EJEMPLOS = [
    'Compra de mercancía para la temporada navideña',
    'Pago de nómina y renta del local',
    'Necesito comprar maquinaria nueva y hacer publicidad en redes sociales',
    'Liquidar deudas con proveedores y tarjetas de crédito',
    'Quiero abrir mi primera cafetería',
]


# Cargamos el modelo una sola vez y lo reutilizamos en cada interacción
@st.cache_resource(show_spinner='Cargando el modelo...')
def cargar_modelo():
    return ClasificadorCreditos()


@st.cache_resource
def cargar_explainer(_modelo):
    # Usamos palabras completas como unidad de la explicación (no subpalabras)
    return shap.Explainer(_modelo.predecir_proba, shap.maskers.Text(r'\W+'), output_names=_modelo.labels)


def tabla_resultados(modelo, proba, umbral):
    tabla = pd.DataFrame({
        'etiqueta': modelo.labels,
        'descripción': [DESCRIPCIONES[l] for l in modelo.labels],
        'probabilidad': proba,
        'umbral': umbral,
    })
    tabla['asignada'] = tabla['probabilidad'] >= tabla['umbral']
    return tabla.sort_values('probabilidad', ascending=False).reset_index(drop=True)


try:
    modelo = cargar_modelo()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

# ---------------------------------------------------------------- barra lateral
with st.sidebar:
    st.header('Configuración')
    modo = st.radio('Umbral de decisión', ['Umbrales por etiqueta', 'Umbral de 0.5'],
                    help='Los umbrales por etiqueta detectan más casos de las etiquetas con poca presencia (mejor '
                         'F1_macro). El umbral de 0.5 comete menos errores en total (mejor Hamming loss).')
    usar_umbrales = modo == 'Umbrales por etiqueta'
    umbral = modelo.umbrales if usar_umbrales else [0.5] * len(modelo.labels)
    st.divider()
    st.caption(f'Modelo: Fine-Tuning de paraphrase-multilingual-mpnet-base-v2, extracción de features y '
               f'Regresión Logística por etiqueta. Corriendo en **{modelo.device.upper()}**.')

st.image(str(Path(__file__).parent / 'img' / 'konfio_logo.png'), width=220)
st.title('Konfío Challenge: loan classification')
st.write('Escribe el motivo por el que el cliente solicita el crédito y el modelo le asignará una o varias etiquetas.')

tab_uno, tab_varios = st.tabs(['Un texto', 'Varios textos (CSV)'])

# ---------------------------------------------------------------- un texto
with tab_uno:
    ejemplo = st.selectbox('Puedes probar con un ejemplo:', ['(escribir mi propio texto)'] + EJEMPLOS)
    texto = st.text_area('Motivo del crédito', value='' if ejemplo.startswith('(') else ejemplo, height=110)

    if st.button('Clasificar', type='primary', disabled=not texto.strip()):
        st.session_state['texto'] = texto.strip()

    if st.session_state.get('texto'):
        texto_actual = st.session_state['texto']
        proba = modelo.predecir_proba([texto_actual])[0]
        tabla = tabla_resultados(modelo, proba, umbral)
        asignadas = tabla[tabla['asignada']]

        st.subheader('Resultado')
        if len(asignadas):
            st.success('Etiquetas asignadas: ' + ', '.join(f"**{e}** ({DESCRIPCIONES[e].lower()})"
                                                           for e in asignadas['etiqueta']))
        else:
            # Ninguna etiqueta supera su umbral: es un caso para revisión humana
            mejor = tabla.iloc[0]
            st.warning(f"Ninguna etiqueta supera su umbral, por lo que se recomienda una revisión humana. "
                       f"La más probable es **{mejor['etiqueta']}** ({mejor['probabilidad']:.0%}).")

        st.dataframe(
            tabla, hide_index=True, width='stretch',
            column_config={
                'probabilidad': st.column_config.ProgressColumn('probabilidad', format='%.2f',
                                                                min_value=0, max_value=1),
                'umbral': st.column_config.NumberColumn('umbral', format='%.2f'),
                'asignada': st.column_config.CheckboxColumn('asignada'),
            })

        # Explicación con SHAP: cuánto sube o baja cada palabra la probabilidad de una etiqueta
        with st.expander('¿Por qué? Ver qué palabras influyeron (SHAP)'):
            etiqueta = st.selectbox('Etiqueta a explicar', list(tabla['etiqueta']))
            if st.button('Calcular explicación'):
                with st.spinner('Calculando SHAP...'):
                    valores = cargar_explainer(modelo)([texto_actual])
                    html = shap.plots.text(valores[:, :, etiqueta], display=False)
                st.caption('En rojo, las palabras que suben la probabilidad; en azul, las que la bajan.')
                st.iframe(html, height=200)

# ---------------------------------------------------------------- varios textos
with tab_varios:
    st.write('Sube un CSV con una columna llamada **motivos** para clasificar todos los textos a la vez.')
    archivo = st.file_uploader('Archivo CSV', type='csv')
    if archivo is not None:
        datos = pd.read_csv(archivo)
        if 'motivos' not in datos.columns:
            st.error('El archivo debe tener una columna llamada "motivos".')
        else:
            textos = datos['motivos'].fillna('').astype(str).tolist()
            with st.spinner(f'Clasificando {len(textos):,} textos...'):
                proba = modelo.predecir_proba(textos)
            pred = proba >= umbral
            resultado = pd.DataFrame({
                'motivos': textos,
                'etiquetas': [', '.join(l for l, v in zip(modelo.labels, fila) if v) or '(revisión humana)'
                              for fila in pred],
            })
            resultado = pd.concat([resultado, pd.DataFrame(proba.round(3), columns=[f'p_{l}' for l in modelo.labels])],
                                  axis=1)
            st.dataframe(resultado, hide_index=True, width='stretch')
            st.download_button('Descargar resultados', resultado.to_csv(index=False).encode('utf-8'),
                               file_name='clasificacion_motivos.csv', mime='text/csv')
