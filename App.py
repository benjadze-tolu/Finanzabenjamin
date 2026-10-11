import streamlit as st
import pandas as pd
import plotly.express as px
import json
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Finanzas Pro", page_icon="📈", layout="wide")

# --- FUNCIÓN DE FORMATO CLP ---
def clp(valor):
    return f"${int(valor):,}".replace(",", ".")

# --- INICIALIZACIÓN DE BASE DE DATOS (EN SESIÓN) ---
if 'historial' not in st.session_state:
    st.session_state['historial'] = {}
if 'bancos' not in st.session_state:
    st.session_state['bancos'] = {'Cuenta RUT': 0, 'Cuenta Corriente': 0, 'Ahorros': 0, 'Tarjeta de Crédito (Deuda)': 0}

# --- BARRA LATERAL (HUD NAVEGACIÓN) ---
st.sidebar.title("📈 HUD Financiero")
menu = st.sidebar.radio("Navegación Principal", [
    "📊 Dashboard y Proyecciones", 
    "📝 Registro Histórico / Mensual", 
    "🏦 Cuentas y Bancos",
    "⚙️ Respaldo de Datos"
])
st.sidebar.divider()
st.sidebar.markdown("**Moneda:** CLP (Pesos Chilenos)")

# --- MÓDULO 1: REGISTRO MENSUAL ---
if menu == "📝 Registro Histórico / Mensual":
    st.title("📝 Registro de Ingresos y Gastos")
    st.markdown("Selecciona un mes y año para ingresar o editar datos.")
    
    col_mes, col_anio = st.columns(2)
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_actual = datetime.now().month - 1
    
    with col_mes:
        mes_seleccionado = st.selectbox("Mes", meses, index=mes_actual)
    with col_anio:
        anio_seleccionado = st.selectbox("Año", [2025, 2026, 2027], index=1)
        
    llave_mes = f"{mes_seleccionado} {anio_seleccionado}"
    
    # Cargar datos existentes o iniciar en cero
    if llave_mes not in st.session_state['historial']:
        st.session_state['historial'][llave_mes] = {
            'Sueldo COSAM': 0, 'Turnos Extras': 0, 'Otros Ingresos': 0,
            'Arriendo': 0, 'Cuentas Básicas': 0, 'Gastos Comunes': 0, 'Supermercado': 0,
            'Bencina': 0, 'TAG y Peajes': 0, 'Seguro Auto': 0, 'Mantención Auto': 0,
            'Gastos del Gato': 0, 'Salidas y Ocio': 0, 'Mantención Hogar': 0, 'Salud': 0
        }
    
    datos = st.session_state['historial'][llave_mes]
    
    t1, t2, t3, t4 = st.tabs(["💰 Ingresos", "🏠 Fijos", "🚗 Auto", "☕ Estilo de Vida"])
    
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
        datos['Mantención Auto'] = st.number_input("Mantención / Estacionamiento", value=datos['Mantención Auto'], step=5000)
    with t4:
        datos['Gastos del Gato'] = st.number_input("Gastos del Gato (Comida, arena, vet)", value=datos['Gastos del Gato'], step=2000)
        datos['Salud'] = st.number_input("Salud / Farmacia", value=datos['Salud'], step=5000)
        datos['Mantención Hogar'] = st.number_input("Decoración / Mantención Hogar", value=datos['Mantención Hogar'], step=5000)
        datos['Salidas y Ocio'] = st.number_input("Salidas, Citas, Ocio", value=datos['Salidas y Ocio'], step=5000)

    st.session_state['historial'][llave_mes] = datos
    st.success(f"Datos de {llave_mes} guardados y actualizados automáticamente.")

# --- MÓDULO 2: BANCOS Y CUENTAS ---
elif menu == "🏦 Cuentas y Bancos":
    st.title("🏦 Estado Patrimonial")
    st.markdown("Actualiza los saldos actuales de tus cuentas para ver tu liquidez real.")
    
    bancos = st.session_state['bancos']
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Liquidez (Dinero a favor)")
        bancos['Cuenta RUT'] = st.number_input("Saldo Cuenta RUT", value=bancos['Cuenta RUT'], step=10000)
        bancos['Cuenta Corriente'] = st.number_input("Saldo Cuenta Corriente", value=bancos['Cuenta Corriente'], step=10000)
        bancos['Ahorros'] = st.number_input("Fondo de Ahorros", value=bancos['Ahorros'], step=10000)
    with col2:
        st.subheader("Pasivos (Deuda)")
        bancos['Tarjeta de Crédito (Deuda)'] = st.number_input("Deuda Total Tarjeta de Crédito", value=bancos['Tarjeta de Crédito (Deuda)'], step=10000)
        
    st.session_state['bancos'] = bancos
    
    liquidez_total = bancos['Cuenta RUT'] + bancos['Cuenta Corriente'] + bancos['Ahorros']
    patrimonio_neto = liquidez_total - bancos['Tarjeta de Crédito (Deuda)']
    
    st.divider()
    st.metric("Liquidez Total Disponible", clp(liquidez_total))
    st.metric("Patrimonio Neto (Liquidez - Deuda)", clp(patrimonio_neto), delta=clp(patrimonio_neto))

# --- MÓDULO 3: DASHBOARD Y PROYECCIONES ---
elif menu == "📊 Dashboard y Proyecciones":
    st.title("📊 Dashboard Analítico")
    
    if not st.session_state['historial']:
        st.warning("No hay datos históricos. Ve a 'Registro Histórico' e ingresa datos de al menos un mes.")
    else:
        # Preparar DataFrame
        filas = []
        for mes_anio, datos in st.session_state['historial'].items():
            ingresos = datos['Sueldo COSAM'] + datos['Turnos Extras'] + datos['Otros Ingresos']
            gastos_fijos = datos['Arriendo'] + datos['Cuentas Básicas'] + datos['Gastos Comunes'] + datos['Supermercado']
            gastos_auto = datos['Bencina'] + datos['TAG y Peajes'] + datos['Seguro Auto'] + datos['Mantención Auto']
            gastos_vida = datos['Gastos del Gato'] + datos['Salidas y Ocio'] + datos['Mantención Hogar'] + datos['Salud']
            
            gastos_totales = gastos_fijos + gastos_auto + gastos_vida
            ahorro = ingresos - gastos_totales
            
            filas.append({
                'Mes': mes_anio, 'Ingresos': ingresos, 'Gastos Totales': gastos_totales, 'Ahorro': ahorro,
                'Fijos': gastos_fijos, 'Auto': gastos_auto, 'Vida': gastos_vida
            })
            
        df = pd.DataFrame(filas)
        
        # KPIs del último mes registrado
        ultimo_mes = df.iloc[-1]
        st.subheader(f"Resumen Último Mes Registrado: {ultimo_mes['Mes']}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos", clp(ultimo_mes['Ingresos']))
        c2.metric("Gastos", clp(ultimo_mes['Gastos Totales']))
        c3.metric("Flujo Neto (Ahorro)", clp(ultimo_mes['Ahorro']), delta="Positivo" if ultimo_mes['Ahorro'] >= 0 else "Negativo")
        
        st.divider()
        
        # Gráficos de Proyección y Tendencia
        st.subheader("📈 Tendencia en el Tiempo")
        fig = px.line(df, x='Mes', y=['Ingresos', 'Gastos Totales'], markers=True, 
                      title="Comparativa Ingresos vs Gastos",
                      color_discrete_map={"Ingresos": "#2E8B57", "Gastos Totales": "#DC143C"})
        st.plotly_chart(fig, use_container_width=True)
        
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.subheader("Distribución de Gastos (Último Mes)")
            datos_torta = pd.DataFrame({
                'Categoría': ['Fijos', 'Auto', 'Estilo de Vida'],
                'Monto': [ultimo_mes['Fijos'], ultimo_mes['Auto'], ultimo_mes['Vida']]
            })
            fig_pie = px.pie(datos_torta, values='Monto', names='Categoría', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_graf2:
            st.subheader("Proyección a 6 meses")
            promedio_ahorro = df['Ahorro'].mean()
            proyeccion = promedio_ahorro * 6
            st.info(f"Basado en tu historial, tu capacidad de ahorro promedio mensual es de **{clp(promedio_ahorro)}**.")
            if promedio_ahorro > 0:
                st.success(f"Proyección: En 6 meses podrías aumentar tu patrimonio en **{clp(proyeccion)}**.")
            else:
                st.error("Proyección: Tu promedio de ahorro es negativo. Revisa tus gastos de Estilo de Vida y Auto.")

# --- MÓDULO 4: RESPALDO DE DATOS ---
elif menu == "⚙️ Respaldo de Datos":
    st.title("⚙️ Configuración y Respaldo")
    st.markdown("Streamlit Cloud reinicia la memoria si la app no se usa en varios días. **Descarga tu archivo de respaldo** a fin de mes para no perder tu historial, y cárgalo aquí mismo cuando vuelvas a entrar.")
    
    # Exportar
    datos_completos = {'historial': st.session_state['historial'], 'bancos': st.session_state['bancos']}
    json_datos = json.dumps(datos_completos)
    
    st.download_button(
        label="📥 Descargar Respaldo (Archivo JSON)",
        data=json_datos,
        file_name=f"respaldo_finanzas_{datetime.now().strftime('%Y-%m-%d')}.json",
        mime="application/json"
    )
    
    st.divider()
    # Importar
    st.markdown("### 📤 Cargar Respaldo")
    archivo_subido = st.file_uploader("Sube tu archivo de respaldo (.json)", type="json")
    if archivo_subido is not None:
        datos_cargados = json.load(archivo_subido)
        st.session_state['historial'] = datos_cargados.get('historial', {})
        st.session_state['bancos'] = datos_cargados.get('bancos', {})
        st.success("¡Datos cargados correctamente! Ve al Dashboard para ver tu historial.")
