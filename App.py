import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Finanzas Pro", page_icon="📈", layout="wide")

def clp(valor):
    return f"${int(valor):,}".replace(",", ".")

# --- CONEXIÓN A GOOGLE CLOUD FIRESTORE ---
@st.cache_resource
def iniciar_firebase():
    if not firebase_admin._apps:
        key_dict = json.loads(st.secrets["firebase_key"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = iniciar_firebase()
coleccion_historial = db.collection("historial_meses")
coleccion_bancos = db.collection("bancos")
coleccion_config = db.collection("configuracion")

# --- CARGAR CATEGORÍAS DINÁMICAS DESDE LA NUBE ---
doc_config = coleccion_config.document("categorias").get()
if doc_config.exists:
    categorias = doc_config.to_dict()
else:
    # Si es la primera vez, crea las categorías base
    categorias = {
        "Ingresos": ["Sueldo COSAM", "Turnos Extras", "Otros Ingresos"],
        "Fijos": ["Arriendo", "Cuentas Básicas", "Gastos Comunes", "Supermercado"],
        "Auto": ["Bencina", "TAG y Peajes", "Seguro Auto", "Mantención Auto"],
        "Vida": ["Gastos del Gato", "Salud", "Mantención Hogar", "Salidas y Ocio"]
    }
    coleccion_config.document("categorias").set(categorias)

# --- HUD NAVEGACIÓN ---
st.sidebar.title("📈 HUD Financiero")
menu = st.sidebar.radio("Navegación Principal", [
    "📊 Dashboard y Proyecciones", 
    "📝 Registro Histórico / Mensual", 
    "🏦 Cuentas y Bancos",
    "⚙️ Configuración y Datos"
])
st.sidebar.divider()
st.sidebar.markdown("**Estado:** 🟢 Conectado a la Nube")

# --- MÓDULO 1: REGISTRO MENSUAL ---
if menu == "📝 Registro Histórico / Mensual":
    st.title("📝 Registro de Ingresos y Gastos")
    st.markdown("Los datos ingresados se guardan automáticamente en tu base de datos.")
    
    col_mes, col_anio = st.columns(2)
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_actual = datetime.now().month - 1
    
    with col_mes:
        mes_seleccionado = st.selectbox("Mes", meses, index=mes_actual)
    with col_anio:
        anio_seleccionado = st.selectbox("Año", [2025, 2026, 2027], index=1)
        
    llave_mes = f"{mes_seleccionado}_{anio_seleccionado}"
    
    # Obtener datos de Firestore
    doc_ref = coleccion_historial.document(llave_mes)
    doc = doc_ref.get()
    datos = doc.to_dict() if doc.exists else {}
    
    # Generar las pestañas dinámicamente según la configuración
    tabs = st.tabs(["💰 Ingresos", "🏠 Fijos", "🚗 Auto", "☕ Vida"])
    
    for i, (tipo, lista_cats) in enumerate(categorias.items()):
        with tabs[i]:
            for cat in lista_cats:
                # Se asegura de que el valor sea un número y usa una llave única para que Streamlit no se confunda al cambiar de mes
                valor_actual = float(datos.get(cat, 0.0))
                datos[cat] = st.number_input(cat, value=valor_actual, step=5000.0, key=f"{llave_mes}_{cat}")
    
    # Guardar cambios
    if st.button("💾 Guardar Mes en la Nube", use_container_width=True):
        doc_ref.set(datos)
        st.success(f"¡Datos de {mes_seleccionado} guardados exitosamente en Google Cloud!")

# --- MÓDULO 2: BANCOS Y CUENTAS ---
elif menu == "🏦 Cuentas y Bancos":
    st.title("🏦 Estado Patrimonial")
    
    doc_bancos = coleccion_bancos.document("saldos_actuales").get()
    bancos = doc_bancos.to_dict() if doc_bancos.exists else {'Cuenta RUT': 0, 'Cuenta Corriente': 0, 'Ahorros': 0, 'Tarjeta de Crédito (Deuda)': 0}
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Liquidez")
        bancos['Cuenta RUT'] = st.number_input("Saldo Cuenta RUT", value=float(bancos.get('Cuenta RUT', 0)), step=10000.0)
        bancos['Cuenta Corriente'] = st.number_input("Saldo Cuenta Corriente", value=float(bancos.get('Cuenta Corriente', 0)), step=10000.0)
        bancos['Ahorros'] = st.number_input("Fondo de Ahorros", value=float(bancos.get('Ahorros', 0)), step=10000.0)
    with col2:
        st.subheader("Pasivos")
        bancos['Tarjeta de Crédito (Deuda)'] = st.number_input("Deuda Tarjeta de Crédito", value=float(bancos.get('Tarjeta de Crédito (Deuda)', 0)), step=10000.0)
        
    liquidez_total = bancos['Cuenta RUT'] + bancos['Cuenta Corriente'] + bancos['Ahorros']
    patrimonio_neto = liquidez_total - bancos['Tarjeta de Crédito (Deuda)']
    
    st.divider()
    st.metric("Liquidez Total Disponible", clp(liquidez_total))
    st.metric("Patrimonio Neto", clp(patrimonio_neto), delta=clp(patrimonio_neto))

    if st.button("💾 Actualizar Saldos", use_container_width=True):
        coleccion_bancos.document("saldos_actuales").set(bancos)
        st.success("Saldos bancarios actualizados en la nube.")

# --- MÓDULO 3: DASHBOARD Y PROYECCIONES ---
elif menu == "📊 Dashboard y Proyecciones":
    st.title("📊 Dashboard Analítico")
    
    docs = coleccion_historial.stream()
    historial = {doc.id: doc.to_dict() for doc in docs}
    
    if not historial:
        st.warning("No hay datos históricos. Ve a 'Registro Histórico' y guarda al menos un mes.")
    else:
        filas = []
        for mes_anio, datos_mes in historial.items():
            ingresos = sum(datos_mes.get(cat, 0) for cat in categorias["Ingresos"])
            gastos_fijos = sum(datos_mes.get(cat, 0) for cat in categorias["Fijos"])
            gastos_auto = sum(datos_mes.get(cat, 0) for cat in categorias["Auto"])
            gastos_vida = sum(datos_mes.get(cat, 0) for cat in categorias["Vida"])
            
            gastos_totales = gastos_fijos + gastos_auto + gastos_vida
            ahorro = ingresos - gastos_totales
            
            filas.append({
                'Mes': mes_anio, 'Ingresos': ingresos, 'Gastos': gastos_totales, 'Ahorro': ahorro,
                'Fijos': gastos_fijos, 'Auto': gastos_auto, 'Vida': gastos_vida
            })
            
        df = pd.DataFrame(filas)
        
        st.subheader("Rendimiento Promedio Mensual")
        c1, c2, c3 = st.columns(3)
        c1.metric("Promedio Ingresos", clp(df['Ingresos'].mean()))
        c2.metric("Promedio Gastos", clp(df['Gastos'].mean()))
        c3.metric("Promedio Flujo Neto", clp(df['Ahorro'].mean()), delta="Positivo" if df['Ahorro'].mean() >= 0 else "Negativo")
        
        st.divider()
        
        st.subheader("📈 Tendencia en el Tiempo")
        fig = px.line(df, x='Mes', y=['Ingresos', 'Gastos'], markers=True, 
                      title="Evolución de Ingresos y Gastos",
                      color_discrete_map={"Ingresos": "#2E8B57", "Gastos": "#DC143C"})
        st.plotly_chart(fig, use_container_width=True)

# --- MÓDULO 4: CONFIGURACIÓN Y CARGA MASIVA ---
elif menu == "⚙️ Configuración y Datos":
    st.title("⚙️ Personalización y Carga de Datos")
    
    # SECCIÓN 1: CREAR CATEGORÍAS
    st.subheader("➕ Agregar Nueva Categoría")
    st.markdown("Crea nuevos apartados que aparecerán automáticamente en tu registro mensual.")
    
    col_tipo, col_nombre = st.columns(2)
    with col_tipo:
        nueva_cat_tipo = st.selectbox("¿En qué pestaña irá?", ["Ingresos", "Fijos", "Auto", "Vida"])
    with col_nombre:
        nueva_cat_nombre = st.text_input("Nombre de la opción (Ej: Gimnasio, Farmacia, etc.)")
        
    if st.button("Crear Categoría"):
        if nueva_cat_nombre:
            if nueva_cat_nombre not in categorias[nueva_cat_tipo]:
                categorias[nueva_cat_tipo].append(nueva_cat_nombre)
                coleccion_config.document("categorias").set(categorias)
                st.success(f"¡Opción '{nueva_cat_nombre}' agregada con éxito! Revisa la pestaña de Registro.")
            else:
                st.warning("Esta opción ya existe.")
        else:
            st.error("Debes escribir un nombre válido.")
            
    st.divider()
    
    # SECCIÓN 2: CARGA MASIVA (EXCEL/CSV)
    st.subheader("📤 Cargar Historial Completo")
    st.markdown("¿Tienes meses anteriores anotados en otra parte? Descarga la plantilla, llénala en Excel, guárdala como **CSV delimitado por comas** y súbela aquí para importar todo de golpe.")
    
    # 1. Botón para generar y descargar plantilla
    todas_columnas = ["Mes_Anio"] + categorias["Ingresos"] + categorias["Fijos"] + categorias["Auto"] + categorias["Vida"]
    df_plantilla = pd.DataFrame(columns=todas_columnas)
    df_plantilla.loc[0] = ["Enero_2026"] + [0] * (len(todas_columnas) - 1)
    
    csv_plantilla = df_plantilla.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 1. Descargar Plantilla",
        data=csv_plantilla,
        file_name="Plantilla_Historial.csv",
        mime="text/csv"
    )
    
    # 2. Subir archivo con datos
    archivo_subido = st.file_uploader("📤 2. Subir Archivo Lleno (Formato CSV)", type=["csv"])
    if archivo_subido is not None:
        try:
            df_subido = pd.read_csv(archivo_subido)
            # Iterar por las filas del archivo y subirlas a Google Cloud
            for index, row in df_subido.iterrows():
                llave_mes = str(row['Mes_Anio'])
                if llave_mes and llave_mes != 'nan':
                    datos_mes = row.drop('Mes_Anio').fillna(0).to_dict()
                    coleccion_historial.document(llave_mes).set(datos_mes)
            st.success("¡Historial cargado con éxito en Google Cloud! Ve al Dashboard para ver los gráficos actualizados.")
        except Exception as e:
            st.error(f"Error al leer el archivo. Asegúrate de guardarlo como CSV. Detalle del error: {e}")
