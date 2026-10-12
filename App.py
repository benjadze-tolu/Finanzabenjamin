import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json
import firebase_admin
from firebase_admin import credentials, firestore
from io import BytesIO

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Finanzas Pro", page_icon="📈", layout="wide")

def clp(valor):
    try:
        return f"${int(float(valor)):,}".replace(",", ".")
    except:
        return "$0"

def limpiar_numero(val):
    if pd.isna(val) or val is None or val == '': return 0.0
    if isinstance(val, (int, float)): return float(val)
    val_str = str(val).replace('$', '').replace(' ', '').strip()
    if not val_str: return 0.0
    if ',' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    elif val_str.count('.') > 1 or ('.' in val_str and len(val_str.split('.')[-1]) == 3):
        val_str = val_str.replace('.', '')
    try: return float(val_str)
    except: return 0.0

def convertir_a_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Plantilla')
    return output.getvalue()

meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
def mes_a_fecha(llave):
    try:
        m, a = llave.split('_')
        return datetime(int(a), meses.index(m) + 1, 1)
    except:
        return datetime(2000, 1, 1)

# --- CONEXIÓN A FIRESTORE ---
@st.cache_resource
def iniciar_firebase():
    if not firebase_admin._apps:
        key_dict = json.loads(st.secrets["firebase_key"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = iniciar_firebase()
coleccion_historial = db.collection("historial_meses")
coleccion_bancos = db.collection("bancos") # Ya no se usa para saldos estáticos, pero se mantiene por compatibilidad
coleccion_historial_bancos = db.collection("historial_bancos")
coleccion_config = db.collection("configuracion")

# --- CARGA Y LIMPIEZA DE CATEGORÍAS ---
doc_config = coleccion_config.document("categorias").get()
categorias = doc_config.to_dict() if doc_config.exists else {
    "Ingresos": ["Sueldo COSAM", "Turnos Extras", "Bonos Institucionales / Aguinaldos", "Otros Ingresos"],
    "Gastos Fijos": ["Arriendo / Dividendo", "Gastos Comunes", "Cuentas Básicas (Luz, Agua, Gas, Internet)", "Supermercado (Alimentación Base)", "Seguro Auto", "Suscripciones (Gym, Streaming)"],
    "Gastos Emergentes": ["Bencina y Transporte", "TAG y Peajes", "Gastos del Gato (Comida, arena, vet)", "Salidas, Citas y Ocio", "Salud y Farmacia", "Decoración y Mantención Hogar", "Mantención Auto (Repuestos, mecánicos)", "Cuidado Personal (Ropa, Barbería)", "Imprevistos y Emergencias"]
}
for k in categorias: categorias[k] = list(dict.fromkeys(categorias[k]))
coleccion_config.document("categorias").set(categorias)

doc_bancos_cat = coleccion_config.document("categorias_bancos").get()
categorias_bancos = doc_bancos_cat.to_dict() if doc_bancos_cat.exists else {
    "Débito": ["Cta. Corriente Banco de Chile", "Cta. RUT Banco Estado", "Cta. Corriente Banco Estado"], 
    "Crédito": ["TC Banco de Chile", "TC Banco Estado"]
}
for k in categorias_bancos: categorias_bancos[k] = list(dict.fromkeys(categorias_bancos[k]))
coleccion_config.document("categorias_bancos").set(categorias_bancos)

doc_presupuesto = coleccion_config.document("presupuesto_base").get()
presupuesto_base = doc_presupuesto.to_dict() if doc_presupuesto.exists else {}

doc_tarjetas = coleccion_config.document("compras_cuotas").get()
compras_cuotas = doc_tarjetas.to_dict() if doc_tarjetas.exists else {}

# --- CÁLCULO DE SALDOS AUTOMÁTICOS ---
docs_hist_bancos = coleccion_historial_bancos.stream()
historial_bancos_data = {doc.id: doc.to_dict() for doc in docs_hist_bancos}

saldos_calculados = {}
for cuenta in categorias_bancos["Débito"]:
    ingresos_totales = sum(limpiar_numero(mes.get(f"{cuenta}_ingresos", 0)) for mes in historial_bancos_data.values())
    egresos_totales = sum(limpiar_numero(mes.get(f"{cuenta}_egresos", 0)) for mes in historial_bancos_data.values())
    saldos_calculados[cuenta] = ingresos_totales - egresos_totales

for tarjeta in categorias_bancos["Crédito"]:
    pagos_totales = sum(limpiar_numero(mes.get(f"{tarjeta}_ingresos", 0)) for mes in historial_bancos_data.values())
    compras_totales = sum(limpiar_numero(mes.get(f"{tarjeta}_egresos", 0)) for mes in historial_bancos_data.values())
    saldos_calculados[tarjeta] = compras_totales - pagos_totales

mes_actual = datetime.now().month - 1
anio_actual = datetime.now().year

# --- HUD NAVEGACIÓN ---
st.sidebar.title("📈 HUD Financiero")
menu = st.sidebar.radio("Navegación", [
    "📊 Dashboard: Planeado vs Real", 
    "📝 Flujo Mensual (Registro)", 
    "🏦 Cuentas, Bancos y Evolución",
    "🔮 Proyecciones y Tarjetas",
    "⚙️ Configuración y Cargas"
])
st.sidebar.divider()
st.sidebar.markdown("**Estado:** 🟢 Conectado a la Nube")

# --- MÓDULO 1: REGISTRO MENSUAL ---
if menu == "📝 Flujo Mensual (Registro)":
    st.title("📝 Flujo Mensual")
    
    col_mes, col_anio = st.columns(2)
    with col_mes: mes_seleccionado = st.selectbox("Mes", meses, index=mes_actual)
    with col_anio: anio_seleccionado = st.selectbox("Año", [2025, 2026, 2027], index=1)
        
    llave_mes = f"{mes_seleccionado}_{anio_seleccionado}"
    doc_ref = coleccion_historial.document(llave_mes)
    doc = doc_ref.get()
    datos = doc.to_dict() if doc.exists else {}
    
    tabs = st.tabs(["💰 Ingresos", "🏠 Gastos Fijos", "🚨 Gastos Emergentes"])
    for i, (tipo, lista_cats) in enumerate(categorias.items()):
        with tabs[i]:
            for cat in lista_cats:
                valor_actual = limpiar_numero(datos.get(cat, 0.0))
                meta = limpiar_numero(presupuesto_base.get(cat, 0.0))
                label = f"{cat} (Presupuesto: {clp(meta)})" if meta > 0 else cat
                datos[cat] = st.number_input(label, value=valor_actual, step=5000.0, format="%.0f", key=f"{llave_mes}_{cat}")
                
                if tipo != "Ingresos" and meta > 0 and datos[cat] > meta:
                    st.error(f"⚠️ Superaste el presupuesto planificado en {clp(datos[cat] - meta)}")
    
    if st.button("💾 Guardar Mes", use_container_width=True):
        coleccion_historial.document(llave_mes).set(datos)
        st.success("¡Datos guardados con éxito!")

# --- MÓDULO 2: BANCOS Y CUENTAS ---
elif menu == "🏦 Cuentas, Bancos y Evolución":
    st.title("🏦 Análisis de Patrimonio por Institución")
    
    t_reg, t_bal, t_graf = st.tabs(["📝 Registrar Ingresos/Egresos", "⚖️ Balance Calculado", "📈 Evolución Histórica"])
    
    with t_reg:
        st.info("No escribas tu saldo final. Anota cuánto dinero ENTRO y SALIÓ de cada cuenta este mes. El sistema calculará tu saldo.")
        col_m_b, col_a_b = st.columns(2)
        with col_m_b: m_sel = st.selectbox("Mes", meses, index=mes_actual, key="mb")
        with col_a_b: a_sel = st.selectbox("Año", [2025, 2026, 2027], index=1, key="ab")
        llave_b = f"{m_sel}_{a_sel}"
        
        datos_mes_banco = historial_bancos_data.get(llave_b, {})
        
        st.subheader("Cuentas de Débito (Líquido)")
        for cuenta in categorias_bancos["Débito"]:
            st.markdown(f"**{cuenta}**")
            c1, c2 = st.columns(2)
            with c1: datos_mes_banco[f"{cuenta}_ingresos"] = st.number_input(f"Ingresos / Abonos", value=limpiar_numero(datos_mes_banco.get(f"{cuenta}_ingresos", 0)), step=10000.0, format="%.0f", key=f"{llave_b}_{cuenta}_i")
            with c2: datos_mes_banco[f"{cuenta}_egresos"] = st.number_input(f"Egresos / Gastos", value=limpiar_numero(datos_mes_banco.get(f"{cuenta}_egresos", 0)), step=10000.0, format="%.0f", key=f"{llave_b}_{cuenta}_e")

        st.subheader("Tarjetas de Crédito (Deuda)")
        for tarjeta in categorias_bancos["Crédito"]:
            st.markdown(f"**{tarjeta}**")
            c1, c2 = st.columns(2)
            with c1: datos_mes_banco[f"{tarjeta}_ingresos"] = st.number_input(f"Pagos a la Tarjeta", value=limpiar_numero(datos_mes_banco.get(f"{tarjeta}_ingresos", 0)), step=10000.0, format="%.0f", key=f"{llave_b}_{tarjeta}_i")
            with c2: datos_mes_banco[f"{tarjeta}_egresos"] = st.number_input(f"Nuevas Compras", value=limpiar_numero(datos_mes_banco.get(f"{tarjeta}_egresos", 0)), step=10000.0, format="%.0f", key=f"{llave_b}_{tarjeta}_e")
            
        if st.button("💾 Guardar Movimientos Bancarios", use_container_width=True):
            coleccion_historial_bancos.document(llave_b).set(datos_mes_banco)
            st.success("¡Movimientos guardados! Ve a la pestaña 'Balance Calculado' para ver tu nuevo saldo.")
            st.rerun()

    with t_bal:
        st.subheader("Desglose Institucional Automático")
        chile_liq = sum(saldos_calculados[k] for k in categorias_bancos["Débito"] if "chile" in k.lower())
        chile_deuda = sum(saldos_calculados[k] for k in categorias_bancos["Crédito"] if "chile" in k.lower())
        estado_liq = sum(saldos_calculados[k] for k in categorias_bancos["Débito"] if "estado" in k.lower())
        estado_deuda = sum(saldos_calculados[k] for k in categorias_bancos["Crédito"] if "estado" in k.lower())
        otros_liq = sum(saldos_calculados[k] for k in categorias_bancos["Débito"] if "chile" not in k.lower() and "estado" not in k.lower())
        otros_deuda = sum(saldos_calculados[k] for k in categorias_bancos["Crédito"] if "chile" not in k.lower() and "estado" not in k.lower())
        
        col_chile, col_estado, col_otros = st.columns(3)
        with col_chile: st.info(f"**🏦 Banco de Chile**\n\nLiquidez: {clp(chile_liq)}\n\nDeuda TC: {clp(chile_deuda)}\n\n**Neto: {clp(chile_liq - chile_deuda)}**")
        with col_estado: st.success(f"**🏦 Banco Estado**\n\nLiquidez: {clp(estado_liq)}\n\nDeuda TC: {clp(estado_deuda)}\n\n**Neto: {clp(estado_liq - estado_deuda)}**")
        with col_otros: st.warning(f"**🏦 Otras Cuentas**\n\nLiquidez: {clp(otros_liq)}\n\nDeuda TC: {clp(otros_deuda)}\n\n**Neto: {clp(otros_liq - otros_deuda)}**")
            
        st.divider()
        liquidez_total = chile_liq + estado_liq + otros_liq
        deuda_total = chile_deuda + estado_deuda + otros_deuda
        c1, c2, c3 = st.columns(3)
        c1.metric("Activos Totales", clp(liquidez_total))
        c2.metric("Pasivos Totales", clp(deuda_total), delta="Deuda", delta_color="inverse")
        c3.metric("PATRIMONIO NETO", clp(liquidez_total - deuda_total))

    with t_graf:
        if historial_bancos_data:
            meses_ordenados = sorted(historial_bancos_data.keys(), key=mes_a_fecha)
            filas_bancos = []
            acumulados = {cta: 0.0 for cta in categorias_bancos["Débito"]}

            for llave in meses_ordenados:
                datos_banco = historial_bancos_data[llave]
                fila = {'Mes': llave}
                for cuenta in categorias_bancos["Débito"]:
                    ing = limpiar_numero(datos_banco.get(f"{cuenta}_ingresos", 0))
                    egr = limpiar_numero(datos_banco.get(f"{cuenta}_egresos", 0))
                    acumulados[cuenta] += (ing - egr)
                    fila[cuenta] = acumulados[cuenta]
                filas_bancos.append(fila)
            
            df_bancos = pd.DataFrame(filas_bancos)
            fig_bancos = px.line(df_bancos, x='Mes', y=categorias_bancos["Débito"], markers=True, title="Evolución Acumulada de tus Cuentas")
            st.plotly_chart(fig_bancos, use_container_width=True)

# --- MÓDULO 3: DASHBOARD ---
elif menu == "📊 Dashboard: Planeado vs Real":
    st.title("📊 Análisis: Planeado vs Real")
    docs = coleccion_historial.stream()
    historial = {doc.id: doc.to_dict() for doc in docs}
    
    if not historial: st.info("No hay datos históricos.")
    else:
        mes_analisis = st.selectbox("Selecciona un mes para analizar", list(historial.keys()), index=len(historial)-1)
        datos_mes = historial[mes_analisis]
        ing_real = sum(limpiar_numero(datos_mes.get(c, 0)) for c in categorias["Ingresos"])
        gas_fijo_real = sum(limpiar_numero(datos_mes.get(c, 0)) for c in categorias["Gastos Fijos"])
        gas_emergente_real = sum(limpiar_numero(datos_mes.get(c, 0)) for c in categorias["Gastos Emergentes"])
        gas_total_real = gas_fijo_real + gas_emergente_real
        
        ing_plan = sum(limpiar_numero(presupuesto_base.get(c, 0)) for c in categorias["Ingresos"])
        gas_plan = sum(limpiar_numero(presupuesto_base.get(c, 0)) for c in categorias["Gastos Fijos"] + categorias["Gastos Emergentes"])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos Reales", clp(ing_real), delta=f"Proyectado: {clp(ing_plan)}")
        c2.metric("Gastos Reales", clp(gas_total_real), delta=f"Límite: {clp(gas_plan)}", delta_color="inverse" if gas_total_real > gas_plan else "normal")
        c3.metric("Ahorro Neto Real", clp(ing_real - gas_total_real))
        
        st.divider()
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            df_torta = pd.DataFrame({'Categoría': ['Gastos Fijos', 'Gastos Emergentes'], 'Monto': [gas_fijo_real, gas_emergente_real]})
            fig_pie = px.pie(df_torta, values='Monto', names='Categoría', hole=0.4, title="Estructura de Gastos", color_discrete_sequence=['#1f77b4', '#d62728'])
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_graf2:
            st.subheader("Estado del Presupuesto")
            st.markdown(f"**Límite de Gasto Total:** {clp(gas_plan)}")
            st.markdown(f"**Gastado hasta ahora:** {clp(gas_total_real)}")
            if gas_plan > 0:
                porcentaje = min((gas_total_real / gas_plan) * 100, 100)
                st.progress(porcentaje / 100, text=f"Has consumido el {porcentaje:.1f}% de tu presupuesto mensual.")

# --- MÓDULO 4: PROYECCIONES Y TARJETAS ---
elif menu == "🔮 Proyecciones y Tarjetas":
    st.title("🔮 Proyección y Vencimiento de Cuotas")
    cuotas_vencer_proximo_mes = {k: v for k, v in compras_cuotas.items() if limpiar_numero(v['restantes']) > 0}
    pago_inmediato = sum(limpiar_numero(det['cuota']) for det in cuotas_vencer_proximo_mes.values())
    st.error(f"🚨 **FACTURACIÓN PROYECTADA TC:** El próximo mes deberás desembolsar **{clp(pago_inmediato)}** líquidos para cubrir las cuotas activas de tus tarjetas.")
    
    t_vencimientos, t_simulador = st.tabs(["📅 Detalle de Próximos Vencimientos", "🔭 Simulador a 6 Meses"])
    
    with t_vencimientos:
        st.subheader("Desglose de Cuotas a Pagar (Próximo Mes)")
        if cuotas_vencer_proximo_mes:
            df_vencimientos = pd.DataFrame([{"Concepto / Compra": item, "Valor Cuota": clp(det['cuota']), "Estado": f"Cuota {int(det['totales'] - det['restantes'] + 1)} de {int(det['totales'])}", "Faltan": int(det['restantes'])} for item, det in cuotas_vencer_proximo_mes.items()])
            st.dataframe(df_vencimientos, use_container_width=True, hide_index=True)
        else:
            st.success("No tienes cuotas pendientes para el próximo mes.")
            
        with st.expander("➕ Agregar nueva compra manual", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            with c1: nueva_compra = st.text_input("Concepto")
            with c2: valor_cuota = st.number_input("Valor Cuota ($)", step=5000.0, format="%.0f")
            with c3: cuotas_totales = st.number_input("Total Cuotas", min_value=1, step=1)
            with c4: cuotas_faltantes = st.number_input("Faltan por pagar", min_value=1, step=1)
            if st.button("Agregar a la tarjeta"):
                if nueva_compra:
                    compras_cuotas[nueva_compra] = {"cuota": float(valor_cuota), "totales": int(cuotas_totales), "restantes": int(cuotas_faltantes)}
                    coleccion_config.document("compras_cuotas").set(compras_cuotas)
                    st.rerun()
                    
        st.subheader("Gestión de Deudas Activas")
        for item, det in list(compras_cuotas.items()):
            tot = int(limpiar_numero(det['totales']))
            rest = int(limpiar_numero(det['restantes']))
            cuota = limpiar_numero(det['cuota'])
            c_info, c_btn = st.columns([5, 1])
            c_info.markdown(f"**{item}** — {clp(cuota)} / mes (Restan: {rest})")
            if c_btn.button("Eliminar", key=f"del_{item}"):
                del compras_cuotas[item]
                coleccion_config.document("compras_cuotas").set(compras_cuotas)
                st.rerun()

    with t_simulador:
        gas_fijo_plan = sum(limpiar_numero(presupuesto_base.get(c, 0)) for c in categorias["Gastos Fijos"])
        ing_plan = sum(limpiar_numero(presupuesto_base.get(c, 0)) for c in categorias["Ingresos"])
        proy_datos = []
        for mes in range(1, 7):
            pago_tarjeta_mes = sum(limpiar_numero(det['cuota']) for det in compras_cuotas.values() if limpiar_numero(det['restantes']) >= mes)
            proy_datos.append({'Mes Futuro': f"Mes {mes}", 'Gastos Base (Supervivencia)': gas_fijo_plan, 'Cuotas Tarjeta': pago_tarjeta_mes, 'Ingresos': ing_plan})
        df_proy = pd.DataFrame(proy_datos)
        fig_proy = px.bar(df_proy, x='Mes Futuro', y=['Gastos Base (Supervivencia)', 'Cuotas Tarjeta'], title="Proyección: Cuánto de tu ingreso fijo estará comprometido", color_discrete_map={'Gastos Base (Supervivencia)': '#1f77b4', 'Cuotas Tarjeta': '#ff7f0e'})
        fig_proy.add_scatter(x=df_proy['Mes Futuro'], y=df_proy['Ingresos'], mode='lines+markers', name='Ingresos Proy.', marker=dict(color='green', size=10))
        st.plotly_chart(fig_proy, use_container_width=True)

# --- MÓDULO 5: CONFIGURACIÓN Y CARGAS ---
elif menu == "⚙️ Configuración y Cargas":
    st.title("⚙️ Configuración y Cargas Masivas")
    
    st.subheader("🎯 1. Presupuesto Base Mensual")
    with st.expander("Modificar Presupuesto", expanded=False):
        nuevo_presupuesto = presupuesto_base.copy()
        for tipo, lista_cats in categorias.items():
            cols = st.columns(2)
            for idx, cat in enumerate(lista_cats):
                with cols[idx % 2]: nuevo_presupuesto[cat] = st.number_input(f"Meta/Límite de {cat}", value=limpiar_numero(nuevo_presupuesto.get(cat, 0)), step=5000.0, format="%.0f", key=f"p_{cat}")
        if st.button("Guardar Presupuesto", use_container_width=True):
            coleccion_config.document("presupuesto_base").set(nuevo_presupuesto)
            st.success("¡Presupuesto actualizado!")
            
    st.divider()
    st.subheader("➕ 2. Crear Apartados de Flujo Mensual")
    col_tipo_g, col_nombre_g = st.columns(2)
    with col_tipo_g: nueva_cat_tipo = st.selectbox("¿En qué pilar irá?", ["Ingresos", "Gastos Fijos", "Gastos Emergentes"])
    with col_nombre_g: nueva_cat_nombre = st.text_input("Nombre (Ej: Gimnasio, Restaurantes)")
    if st.button("Crear Nueva Categoría"):
        if nueva_cat_nombre and nueva_cat_nombre not in categorias[nueva_cat_tipo]:
            categorias[nueva_cat_tipo].append(nueva_cat_nombre)
            coleccion_config.document("categorias").set(categorias)
            st.rerun()

    st.divider()
    st.subheader("🏦 3. Personalizar Cuentas y Tarjetas")
    col_tipo_banco, col_nom_banco = st.columns(2)
    with col_tipo_banco: tipo_banco = st.selectbox("Tipo", ["Débito", "Crédito"])
    with col_nom_banco: nombre_banco = st.text_input("Nombre (Ej: TC Scotiabank)")
    if st.button("Agregar Producto Bancario"):
        if nombre_banco and nombre_banco not in categorias_bancos[tipo_banco]:
            categorias_bancos[tipo_banco].append(nombre_banco)
            coleccion_config.document("categorias_bancos").set(categorias_bancos)
            st.rerun()
            
    st.divider()
    st.subheader("📥 4. Cargas Masivas de Excel (.xlsx)")
    tab_hist, tab_deuda, tab_bancos = st.tabs(["1️⃣ Flujo (Ingresos y Gastos)", "2️⃣ Deudas en Cuotas", "3️⃣ Ingresos/Egresos de Bancos"])
    
    with tab_hist:
        todas_columnas = ["Mes_Anio"] + categorias["Ingresos"] + categorias["Gastos Fijos"] + categorias["Gastos Emergentes"]
        df_plantilla = pd.DataFrame(columns=todas_columnas)
        st.download_button("Descargar Plantilla Flujo (Excel)", data=convertir_a_excel(df_plantilla), file_name="Flujo_Separado.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        arch_hist = st.file_uploader("Subir Excel de Flujo", type=["xlsx", "xls", "csv"], key="hist")
        if arch_hist:
            try:
                df_subido = pd.read_csv(arch_hist) if arch_hist.name.endswith('.csv') else pd.read_excel(arch_hist, engine='openpyxl')
                for _, row in df_subido.iterrows():
                    if str(row['Mes_Anio']) != 'nan':
                        datos_limpios = {k: limpiar_numero(v) for k, v in row.drop('Mes_Anio').fillna(0).to_dict().items()}
                        coleccion_historial.document(str(row['Mes_Anio'])).set(datos_limpios)
                st.success("¡Flujo histórico cargado correctamente!")
            except Exception as e: st.error(f"Error al leer: {e}")

    with tab_deuda:
        df_plantilla_deudas = pd.DataFrame(columns=["Concepto", "Cuota_Mensual", "Totales", "Restantes"])
        st.download_button("Descargar Plantilla Deudas (Excel)", data=convertir_a_excel(df_plantilla_deudas), file_name="Deudas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        arch_deuda = st.file_uploader("Subir Excel de Deudas", type=["xlsx", "xls", "csv"], key="deuda")
        if arch_deuda:
            try:
                df_deudas = pd.read_csv(arch_deuda) if arch_deuda.name.endswith('.csv') else pd.read_excel(arch_deuda, engine='openpyxl')
                for _, row in df_deudas.iterrows():
                    if str(row['Concepto']) != 'nan':
                        compras_cuotas[str(row['Concepto'])] = {"cuota": limpiar_numero(row['Cuota_Mensual']), "totales": int(limpiar_numero(row['Totales'])), "restantes": int(limpiar_numero(row['Restantes']))}
                coleccion_config.document("compras_cuotas").set(compras_cuotas)
                st.success("¡Deudas importadas!")
            except Exception as e: st.error(f"Error al leer: {e}")
            
    with tab_bancos:
        columnas_bancos = ["Mes_Anio"]
        for cta in categorias_bancos["Débito"]: columnas_bancos.extend([f"{cta}_Ingresos", f"{cta}_Egresos"])
        for tar in categorias_bancos["Crédito"]: columnas_bancos.extend([f"{tar}_Pagos", f"{tar}_Compras"])
        
        df_plantilla_bancos = pd.DataFrame(columns=columnas_bancos)
        st.download_button("Descargar Plantilla Bancos (Excel)", data=convertir_a_excel(df_plantilla_bancos), file_name="Historial_Bancos_Calculado.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        arch_bancos = st.file_uploader("Subir Excel de Bancos", type=["xlsx", "xls", "csv"], key="arch_bancos")
        if arch_bancos:
            try:
                df_subido_b = pd.read_csv(arch_bancos) if arch_bancos.name.endswith('.csv') else pd.read_excel(arch_bancos, engine='openpyxl')
                for _, row in df_subido_b.iterrows():
                    if str(row['Mes_Anio']) != 'nan':
                        datos_bancos_limpios = {}
                        for cta in categorias_bancos["Débito"]:
                            datos_bancos_limpios[f"{cta}_ingresos"] = limpiar_numero(row.get(f"{cta}_Ingresos", 0))
                            datos_bancos_limpios[f"{cta}_egresos"] = limpiar_numero(row.get(f"{cta}_Egresos", 0))
                        for tar in categorias_bancos["Crédito"]:
                            datos_bancos_limpios[f"{tar}_ingresos"] = limpiar_numero(row.get(f"{tar}_Pagos", 0))
                            datos_bancos_limpios[f"{tar}_egresos"] = limpiar_numero(row.get(f"{tar}_Compras", 0))
                        coleccion_historial_bancos.document(str(row['Mes_Anio'])).set(datos_bancos_limpios)
                st.success("¡Historial de bancos cargado! Se han recalculado todos tus saldos.")
            except Exception as e: st.error(f"Error al leer: {e}")
