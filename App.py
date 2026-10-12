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
coleccion_historial_bancos = db.collection("historial_bancos")
coleccion_config = db.collection("configuracion")

# --- CARGAR DATOS DESDE LA NUBE ---
doc_config = coleccion_config.document("categorias").get()
if doc_config.exists:
    categorias = doc_config.to_dict()
else:
    categorias = {
        "Ingresos": ["Sueldo COSAM", "Turnos Extras", "Otros Ingresos"],
        "Fijos": ["Arriendo", "Cuentas Básicas", "Gastos Comunes", "Supermercado"],
        "Auto": ["Bencina", "TAG y Peajes", "Seguro Auto", "Mantención Auto"],
        "Vida": ["Gastos del Gato", "Salud", "Mantención Hogar", "Salidas y Ocio"]
    }
    coleccion_config.document("categorias").set(categorias)

doc_bancos_cat = coleccion_config.document("categorias_bancos").get()
if doc_bancos_cat.exists:
    categorias_bancos = doc_bancos_cat.to_dict()
else:
    # Pre-configurado para 2 cuentas corrientes
    categorias_bancos = {"Débito": ["Cuenta Corriente Banco 1", "Cuenta Corriente Banco 2", "Cuenta RUT", "Ahorros"], "Crédito": ["Tarjeta de Crédito Principal"]}
    coleccion_config.document("categorias_bancos").set(categorias_bancos)

doc_presupuesto = coleccion_config.document("presupuesto_base").get()
presupuesto_base = doc_presupuesto.to_dict() if doc_presupuesto.exists else {}

doc_tarjetas = coleccion_config.document("compras_cuotas").get()
compras_cuotas = doc_tarjetas.to_dict() if doc_tarjetas.exists else {}

# Determinar mes actual para llaves
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
mes_actual = datetime.now().month - 1
anio_actual = datetime.now().year
llave_mes_actual = f"{meses[mes_actual]}_{anio_actual}"

# --- HUD NAVEGACIÓN ---
st.sidebar.title("📈 HUD Financiero")
menu = st.sidebar.radio("Navegación", [
    "📊 Dashboard: Planeado vs Real", 
    "📝 Flujo Mensual (Registro)", 
    "🏦 Cuentas, Bancos y Evolución",
    "🔮 Proyecciones y Cuotas",
    "⚙️ Configuración y Cargas"
])
st.sidebar.divider()
st.sidebar.markdown("**Estado:** 🟢 Conectado a la Nube")

# --- MÓDULO 1: REGISTRO MENSUAL ---
if menu == "📝 Flujo Mensual (Registro)":
    st.title("📝 Flujo Mensual")
    st.markdown("Ingresa tus movimientos reales.")
    
    col_mes, col_anio = st.columns(2)
    with col_mes:
        mes_seleccionado = st.selectbox("Mes", meses, index=mes_actual)
    with col_anio:
        anio_seleccionado = st.selectbox("Año", [2025, 2026, 2027], index=1)
        
    llave_mes = f"{mes_seleccionado}_{anio_seleccionado}"
    doc_ref = coleccion_historial.document(llave_mes)
    doc = doc_ref.get()
    datos = doc.to_dict() if doc.exists else {}
    
    tabs = st.tabs(["💰 Ingresos", "🏠 Fijos", "🚗 Auto", "☕ Vida"])
    for i, (tipo, lista_cats) in enumerate(categorias.items()):
        with tabs[i]:
            for cat in lista_cats:
                valor_actual = float(datos.get(cat, 0.0))
                meta = float(presupuesto_base.get(cat, 0.0))
                label = f"{cat} (Presupuesto: {clp(meta)})" if meta > 0 else cat
                datos[cat] = st.number_input(label, value=valor_actual, step=5000.0, key=f"{llave_mes}_{cat}")
                
                if tipo != "Ingresos" and meta > 0 and datos[cat] > meta:
                    st.error(f"⚠️ Superaste el presupuesto en {clp(datos[cat] - meta)}")
    
    if st.button("💾 Guardar Mes", use_container_width=True):
        doc_ref.set(datos)
        st.success("¡Datos guardados!")

# --- MÓDULO 2: BANCOS Y CUENTAS ---
elif menu == "🏦 Cuentas, Bancos y Evolución":
    st.title("🏦 Cuentas y Tarjetas")
    
    # Cargar saldo actual y el historial completo
    doc_bancos = coleccion_bancos.document("saldos_actuales").get()
    bancos = doc_bancos.to_dict() if doc_bancos.exists else {}
    
    docs_hist_bancos = coleccion_historial_bancos.stream()
    historial_bancos_data = {doc.id: doc.to_dict() for doc in docs_hist_bancos}
    
    t_debito, t_credito, t_resumen, t_grafico = st.tabs(["🏦 Liquidez", "💳 Deudas", "⚖️ Balance", "📈 Evolución Histórica"])
    
    with t_debito:
        st.info("Ingresa el saldo disponible HOY en tus cuentas.")
        for cuenta in categorias_bancos["Débito"]:
            bancos[cuenta] = st.number_input(f"Saldo {cuenta}", value=float(bancos.get(cuenta, 0)), step=10000.0)
            
    with t_credito:
        st.warning("Ingresa la deuda facturada HOY en tus tarjetas.")
        for tarjeta in categorias_bancos["Crédito"]:
            bancos[tarjeta] = st.number_input(f"Deuda Total {tarjeta}", value=float(bancos.get(tarjeta, 0)), step=10000.0)
            
    with t_resumen:
        liquidez_total = sum(bancos.get(cta, 0) for cta in categorias_bancos["Débito"])
        deuda_total = sum(bancos.get(tar, 0) for tar in categorias_bancos["Crédito"])
        patrimonio_neto = liquidez_total - deuda_total
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Activos (Líquido)", clp(liquidez_total))
        c2.metric("Pasivos (Deuda)", clp(deuda_total), delta="Deuda", delta_color="inverse")
        c3.metric("Patrimonio Neto", clp(patrimonio_neto))
        
        if st.button("💾 Actualizar Saldos Actuales", use_container_width=True):
            # Guarda el saldo actual y también crea un registro histórico para el mes en curso
            coleccion_bancos.document("saldos_actuales").set(bancos)
            coleccion_historial_bancos.document(llave_mes_actual).set(bancos)
            st.success("Saldos actualizados y guardados en el historial de este mes.")

    with t_grafico:
        st.subheader("Evolución de tus Cuentas Corrientes")
        if not historial_bancos_data:
            st.info("Aún no hay historial suficiente. Guarda tus saldos actuales o carga el Excel histórico.")
        else:
            # Prepara datos para el gráfico
            filas_bancos = []
            for mes_anio, datos_banco in historial_bancos_data.items():
                fila = {'Mes': mes_anio}
                for cuenta in categorias_bancos["Débito"] + categorias_bancos["Crédito"]:
                    fila[cuenta] = datos_banco.get(cuenta, 0)
                filas_bancos.append(fila)
                
            df_bancos = pd.DataFrame(filas_bancos)
            
            # Gráfico solo de las cuentas de débito para ver la liquidez
            cuentas_corrientes = [cta for cta in categorias_bancos["Débito"] if "Cuenta" in cta or "Banco" in cta]
            if cuentas_corrientes:
                fig_bancos = px.line(df_bancos, x='Mes', y=cuentas_corrientes, markers=True,
                                     title="Tendencia de Liquidez en Cuentas Corrientes",
                                     labels={'value': 'Saldo CLP', 'variable': 'Cuenta Bancaria'})
                st.plotly_chart(fig_bancos, use_container_width=True)

# --- MÓDULO 3: DASHBOARD ---
elif menu == "📊 Dashboard: Planeado vs Real":
    st.title("📊 Análisis: Planeado vs Real")
    docs = coleccion_historial.stream()
    historial = {doc.id: doc.to_dict() for doc in docs}
    
    if not historial:
        st.info("No hay datos históricos.")
    else:
        mes_analisis = st.selectbox("Selecciona un mes para analizar", list(historial.keys()), index=len(historial)-1)
        datos_mes = historial[mes_analisis]
        ing_real = sum(datos_mes.get(c, 0) for c in categorias["Ingresos"])
        gas_real = sum(datos_mes.get(c, 0) for c in categorias["Fijos"] + categorias["Auto"] + categorias["Vida"])
        ing_plan = sum(float(presupuesto_base.get(c, 0)) for c in categorias["Ingresos"])
        gas_plan = sum(float(presupuesto_base.get(c, 0)) for c in categorias["Fijos"] + categorias["Auto"] + categorias["Vida"])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos Reales", clp(ing_real), delta=f"Proyectado: {clp(ing_plan)}")
        c2.metric("Gastos Reales", clp(gas_real), delta=f"Límite: {clp(gas_plan)}", delta_color="inverse" if gas_real > gas_plan else "normal")
        c3.metric("Ahorro Neto Real", clp(ing_real - gas_real))

# --- MÓDULO 4: PROYECCIONES Y TARJETAS ---
elif menu == "🔮 Proyecciones y Cuotas":
    st.title("🔮 Proyección y Gestión de Tarjetas")
    pago_inmediato = sum(det['cuota'] for det in compras_cuotas.values() if det['restantes'] > 0)
    st.info(f"🚨 **PREVISIÓN PRÓXIMO MES:** Necesitarás **{clp(pago_inmediato)}** líquidos para cubrir la facturación de tu tarjeta.")
    
    with st.expander("➕ Agregar nueva compra manual", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1: nueva_compra = st.text_input("Concepto")
        with c2: valor_cuota = st.number_input("Valor Cuota ($)", step=5000.0)
        with c3: cuotas_totales = st.number_input("Total Cuotas", min_value=1, step=1)
        with c4: cuotas_faltantes = st.number_input("Faltan", min_value=1, step=1)
            
        if st.button("Agregar a proyección"):
            if nueva_compra:
                compras_cuotas[nueva_compra] = {"cuota": valor_cuota, "totales": int(cuotas_totales), "restantes": int(cuotas_faltantes)}
                coleccion_config.document("compras_cuotas").set(compras_cuotas)
                st.rerun()

    if compras_cuotas:
        for item, det in list(compras_cuotas.items()):
            cuota_actual = det['totales'] - det['restantes'] + 1
            if det['restantes'] > 0:
                porcentaje = (cuota_actual - 1) / det['totales']
                c_info, c_btn = st.columns([5, 1])
                c_info.markdown(f"**{item}** — {clp(det['cuota'])} / mes")
                c_info.progress(porcentaje, text=f"Cuota {cuota_actual - 1} de {det['totales']} (Faltan {det['restantes']})")
                if c_btn.button("🗑️", key=f"del_{item}"):
                    del compras_cuotas[item]
                    coleccion_config.document("compras_cuotas").set(compras_cuotas)
                    st.rerun()

# --- MÓDULO 5: CONFIGURACIÓN Y CARGAS ---
elif menu == "⚙️ Configuración y Cargas":
    st.title("⚙️ Configuración y Cargas Masivas")
    
    st.subheader("🏦 Personalizar Cuentas y Tarjetas")
    st.markdown("Añade tus cuentas corrientes específicas antes de bajar las plantillas.")
    col_tipo_banco, col_nom_banco = st.columns(2)
    with col_tipo_banco:
        tipo_banco = st.selectbox("Tipo", ["Débito", "Crédito"])
    with col_nom_banco:
        nombre_banco = st.text_input("Nombre (Ej: Cuenta Corriente Falabella)")
    if st.button("Agregar Producto Bancario"):
        if nombre_banco and nombre_banco not in categorias_bancos[tipo_banco]:
            categorias_bancos[tipo_banco].append(nombre_banco)
            coleccion_config.document("categorias_bancos").set(categorias_bancos)
            st.success("¡Producto agregado!")
            st.rerun()
            
    st.divider()
    
    st.subheader("📥 Cargas Masivas desde Excel (CSV)")
    tab_hist, tab_deuda, tab_bancos = st.tabs(["1️⃣ Flujo (Ingresos/Gastos)", "2️⃣ Deudas en Cuotas", "3️⃣ Saldos de Bancos"])
    
    with tab_hist:
        todas_columnas = ["Mes_Anio"] + categorias["Ingresos"] + categorias["Fijos"] + categorias["Auto"] + categorias["Vida"]
        df_plantilla = pd.DataFrame(columns=todas_columnas)
        df_plantilla.loc[0] = ["Enero_2026"] + [0] * (len(todas_columnas) - 1)
        st.download_button("Descargar Plantilla Flujo", data=df_plantilla.to_csv(index=False).encode('utf-8'), file_name="Flujo.csv", mime="text/csv")
        arch_hist = st.file_uploader("Subir Flujo CSV", type=["csv"], key="hist")
        if arch_hist:
            df_subido = pd.read_csv(arch_hist)
            for _, row in df_subido.iterrows():
                if str(row['Mes_Anio']) != 'nan':
                    coleccion_historial.document(str(row['Mes_Anio'])).set(row.drop('Mes_Anio').fillna(0).to_dict())
            st.success("¡Flujo cargado!")

    with tab_deuda:
        df_plantilla_deudas = pd.DataFrame(columns=["Concepto", "Cuota_Mensual", "Totales", "Restantes"])
        df_plantilla_deudas.loc[0] = ["Ej: Notebook", 25000, 12, 5]
        st.download_button("Descargar Plantilla Deudas", data=df_plantilla_deudas.to_csv(index=False).encode('utf-8'), file_name="Deudas.csv", mime="text/csv")
        arch_deuda = st.file_uploader("Subir Deudas CSV", type=["csv"], key="deuda")
        if arch_deuda:
            df_deudas = pd.read_csv(arch_deuda)
            for _, row in df_deudas.iterrows():
                if str(row['Concepto']) != 'nan':
                    compras_cuotas[str(row['Concepto'])] = {"cuota": float(row['Cuota_Mensual']), "totales": int(row['Totales']), "restantes": int(row['Restantes'])}
            coleccion_config.document("compras_cuotas").set(compras_cuotas)
            st.success("¡Deudas importadas!")
            
    with tab_bancos:
        st.markdown("Sube el historial mensual del saldo que tenías en tus cuentas.")
        columnas_bancos = ["Mes_Anio"] + categorias_bancos["Débito"] + categorias_bancos["Crédito"]
        df_plantilla_bancos = pd.DataFrame(columns=columnas_bancos)
        df_plantilla_bancos.loc[0] = ["Enero_2026"] + [0] * (len(columnas_bancos) - 1)
        st.download_button("Descargar Plantilla Bancos", data=df_plantilla_bancos.to_csv(index=False).encode('utf-8'), file_name="Historial_Bancos.csv", mime="text/csv")
        arch_bancos = st.file_uploader("Subir Bancos CSV", type=["csv"], key="arch_bancos")
        if arch_bancos:
            df_subido_b = pd.read_csv(arch_bancos)
            for _, row in df_subido_b.iterrows():
                if str(row['Mes_Anio']) != 'nan':
                    coleccion_historial_bancos.document(str(row['Mes_Anio'])).set(row.drop('Mes_Anio').fillna(0).to_dict())
            st.success("¡Historial de bancos cargado! Revisa el gráfico en la pestaña de Cuentas.")
