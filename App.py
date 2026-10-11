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
        # Lee la llave secreta desde la caja fuerte de Streamlit
        key_dict = json.loads(st.secrets["firebase_key"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = iniciar_firebase()
coleccion_historial = db.collection("historial_meses")
coleccion_bancos = db.collection("bancos")

# --- HUD NAVEGACIÓN ---
st.sidebar.title("📈 HUD Financiero")
menu = st.sidebar.radio("Navegación Principal", [
    "📊 Dashboard y Proyecciones", 
    "📝 Registro Histórico / Mensual", 
    "🏦 Cuentas y Bancos"
])
st.sidebar.divider()
st.sidebar.markdown("**Estado:** 🟢 Conectado a la Nube")

# --- MÓDULO 1: REGISTRO MENSUAL ---
if menu == "📝 Registro Histórico / Mensual":
    st.title("📝 Registro de Ingresos y Gastos")
    st.markdown("Los datos se guardan automáticamente en tu base de datos.")
    
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
    
    if doc.exists:
        datos = doc.to_dict()
    else:
        datos = {
            'Sueldo COSAM': 0, 'Turnos Extras': 0, 'Otros Ingresos': 0,
            'Arriendo': 0, 'Cuentas Básicas': 0, 'Gastos Comunes': 0, 'Supermercado': 0,
            'Bencina': 0, 'TAG y Peajes': 0, 'Seguro Auto': 0, 'Mantención Auto': 0,
            'Gastos del Gato': 0, 'Salidas y Ocio': 0, 'Mantención Hogar': 0, 'Salud': 0
        }
    
    t1, t2, t3, t4 = st.tabs(["💰 Ingresos", "🏠 Fijos", "🚗 Auto", "☕ Vida"])
    
    with t1:
        datos['Sueldo COSAM'] = st.number_input("Sueldo COSAM", value=datos['Sueldo COSAM'], step=10000)
        datos['Turnos Extras'] = st.number_input("Turnos Extras / Horas", value=datos['Turnos Extras'], step=5000)
        datos['Otros Ingresos'] = st.number_input("Otros Ingresos", value=datos['Otros Ingresos'], step=5000)
    with t2:
        datos['Arriendo'] = st.number_input("Arriendo", value=datos['Arriendo'], step=10000)
        datos['Gastos Comunes'] = st.number_input("Gastos Comunes", value=datos['Gastos Comunes'], step=5000)
        datos['Cuentas Básicas'] = st.number_input("Cuentas (Luz, Agua, Gas, Internet)", value=datos['Cuentas Básicas'], step=2000)
        datos['Supermercado'] = st.number_input("Supermercado", value=datos['Supermercado'], step=5000)
    with t3:
        datos['Bencina'] = st.number_input("Bencina", value=datos['Bencina'], step=5000)
        datos['TAG y Peajes'] = st.number_input("TAG y Peajes", value=datos['TAG y Peajes'], step=2000)
        datos['Seguro Auto'] = st.number_input("Seguro Auto", value=datos['Seguro Auto'], step=1000)
        datos['Mantención Auto'] = st.number_input("Fondo Mantención", value=datos['Mantención Auto'], step=5000)
    with t4:
        datos['Gastos del Gato'] = st.number_input("Gato (Comida, arena, vet)", value=datos['Gastos del Gato'], step=2000)
        datos['Salud'] = st.number_input("Salud / Farmacia", value=datos['Salud'], step=5000)
        datos['Mantención Hogar'] = st.number_input("Decoración / Mantención", value=datos['Mantención Hogar'], step=5000)
        datos['Salidas y Ocio'] = st.number_input("Salidas, Citas, Ocio", value=datos['Salidas y Ocio'], step=5000)

    # Guardar cambios en Firestore al presionar botón
    if st.button("💾 Guardar Mes en la Nube", use_container_width=True):
        doc_ref.set(datos)
        st.success("¡Datos guardados exitosamente en Google Cloud!")

# --- MÓDULO 2: BANCOS Y CUENTAS ---
elif menu == "🏦 Cuentas y Bancos":
    st.title("🏦 Estado Patrimonial")
    
    doc_bancos = coleccion_bancos.document("saldos_actuales").get()
    if doc_bancos.exists:
        bancos = doc_bancos.to_dict()
    else:
        bancos = {'Cuenta RUT': 0, 'Cuenta Corriente': 0, 'Ahorros': 0, 'Tarjeta de Crédito (Deuda)': 0}
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Liquidez")
        bancos['Cuenta RUT'] = st.number_input("Saldo Cuenta RUT", value=bancos['Cuenta RUT'], step=10000)
        bancos['Cuenta Corriente'] = st.number_input("Saldo Cuenta Corriente", value=bancos['Cuenta Corriente'], step=10000)
        bancos['Ahorros'] = st.number_input("Fondo de Ahorros", value=bancos['Ahorros'], step=10000)
    with col2:
        st.subheader("Pasivos")
        bancos['Tarjeta de Crédito (Deuda)'] = st.number_input("Deuda Tarjeta de Crédito", value=bancos['Tarjeta de Crédito (Deuda)'], step=10000)
        
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
        for mes_anio, datos in historial.items():
            ingresos = datos.get('Sueldo COSAM', 0) + datos.get('Turnos Extras', 0) + datos.get('Otros Ingresos', 0)
            gastos_fijos = datos.get('Arriendo', 0) + datos.get('Cuentas Básicas', 0) + datos.get('Gastos Comunes', 0) + datos.get('Supermercado', 0)
            gastos_auto = datos.get('Bencina', 0) + datos.get('TAG y Peajes', 0) + datos.get('Seguro Auto', 0) + datos.get('Mantención Auto', 0)
            gastos_vida = datos.get('Gastos del Gato', 0) + datos.get('Salidas y Ocio', 0) + datos.get('Mantención Hogar', 0) + datos.get('Salud', 0)
            
            gastos_totales = gastos_fijos + gastos_auto + gastos_vida
            ahorro = ingresos - gastos_totales
            
            filas.append({
                'Mes': mes_anio, 'Ingresos': ingresos, 'Gastos': gastos_totales, 'Ahorro': ahorro,
                'Fijos': gastos_fijos, 'Auto': gastos_auto, 'Vida': gastos_vida
            })
            
        df = pd.DataFrame(filas)
        
        # Resumen Global
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
