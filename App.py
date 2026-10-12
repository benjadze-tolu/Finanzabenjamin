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

# --- MOTOR SANITIZADOR ULTRA-BLINDADO ---
def limpiar_numero(val):
    if pd.isna(val) or val is None or val == '': return 0
    if isinstance(val, (int, float)): return int(val)
    
    val_str = str(val).strip()
    is_negative = val_str.startswith('-') or val_str.startswith('-$')
    val_str = val_str.replace('$', '').replace(' ', '').replace('CLP', '').replace('-', '')
    if not val_str: return 0
    
    # Detección inteligente de formato (Puntos vs Comas)
    if ',' in val_str and val_str.rfind(',') > val_str.rfind('.'):
        parts = val_str.split(',')
        val_str = parts[0].replace('.', '')
    elif '.' in val_str and val_str.rfind('.') > val_str.rfind(','):
        parts = val_str.split('.')
        if len(parts[-1]) <= 2:  # Es un decimal
            val_str = ''.join(parts[:-1]).replace(',', '')
        else: # Es un separador de miles
            val_str = val_str.replace('.', '').replace(',', '')
    else:
        val_str = val_str.replace('.', '').replace(',', '')
        
    try: 
        num = int(val_str)
        return -num if is_negative else num
    except: 
        return 0

def convertir_a_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Plantilla')
    return output.getvalue()

# --- ORDEN CRONOLÓGICO ABSOLUTO ---
meses_lista = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
def mes_a_fecha(llave):
    try:
        m, a = llave.split('_')
        return datetime(int(a), meses_lista.index(m) + 1, 1)
    except:
        return datetime(2000, 1, 1)

mes_actual_idx = datetime.now().month - 1
anio_actual = datetime.now().year
llave_mes_actual = f"{meses_lista[mes_actual_idx]}_{anio_actual}"

nombres_meses_futuros = []
for i in range(1, 7):
    idx = (mes_actual_idx + i) % 12
    a_offset = (mes_actual_idx + i) // 12
    nombres_meses_futuros.append(f"{meses_lista[idx]} {anio_actual + a_offset}")

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
coleccion_historial_bancos = db.collection("historial_bancos")
coleccion_config = db.collection("configuracion")

# --- CARGA Y LIMPIEZA DE CATEGORÍAS ---
doc_config = coleccion_config.document("categorias").get()
categorias = doc_config.to_dict() if doc_config.exists else {
    "Ingresos": ["Sueldo COSAM", "Turnos Extras", "Otros Ingresos"],
    "Gastos Fijos": ["Arriendo / Dividendo", "Gastos Comunes", "Cuentas Básicas", "Supermercado"],
    "Gastos Emergentes": ["Bencina y Transporte", "Gastos del Gato", "Salidas y Ocio", "Salud e Imprevistos"]
}
coleccion_config.document("categorias").set(categorias)

categorias_bancos = {
    "Débito": ["Cta. Corriente Banco Estado", "Cta. Corriente Banco de Chile"], 
    "Crédito": ["TC Banco de Chile Nacional", "TC Banco de Chile Internacional"]
}
coleccion_config.document("categorias_bancos").set(categorias_bancos)

doc_presupuesto = coleccion_config.document("presupuesto_base").get()
presupuesto_base = doc_presupuesto.to_dict() if doc_presupuesto.exists else {}

doc_tarjetas = coleccion_config.document("compras_cuotas").get()
compras_cuotas = doc_tarjetas.to_dict() if doc_tarjetas.exists else {}

docs_hist_bancos = coleccion_historial_bancos.stream()
historial_bancos_data = {doc.id: doc.to_dict() for doc in docs_hist_bancos}

# --- HUD NAVEGACIÓN ---
st.sidebar.title("📈 HUD Financiero")
menu = st.sidebar.radio("Navegación", [
    "📊 Dashboard: Planeado vs Real", 
    "📝 Flujo Mensual (Registro)", 
    "🏦 Cuentas, Bancos y Evolución",
    "🔮 Proyecciones Mensuales Detalladas",
    "⚙️ Configuración y Cargas"
])
st.sidebar.divider()
st.sidebar.markdown("**Estado:** 🟢 Conectado a la Nube")

# --- MÓDULO 1: REGISTRO MENSUAL ---
if menu == "📝 Flujo Mensual (Registro)":
    st.title("📝 Flujo Mensual")
    
    col_mes, col_anio = st.columns(2)
    with col_mes: mes_seleccionado = st.selectbox("Mes", meses_lista, index=mes_actual_idx)
    with col_anio: anio_seleccionado = st.selectbox("Año", [2025, 2026, 2027], index=1)
        
    llave_mes = f"{mes_seleccionado}_{anio_seleccionado}"
    doc_ref = coleccion_historial.document(llave_mes)
    doc = doc_ref.get()
    datos = doc.to_dict() if doc.exists else {}
    
    tabs = st.tabs(["💰 Ingresos", "🏠 Gastos Fijos", "🚨 Gastos Emergentes"])
    for i, (tipo, lista_cats) in enumerate(categorias.items()):
        with tabs[i]:
            for cat in lista_cats:
                valor_actual = limpiar_numero(datos.get(cat, 0))
                meta = limpiar_numero(presupuesto_base.get(cat, 0))
                label = f"{cat} (Meta: {clp(meta)})" if meta > 0 else cat
                datos[cat] = st.number_input(label, value=valor_actual, step=5000, key=f"{llave_mes}_{cat}")
                
    if st.button("💾 Guardar Mes", use_container_width=True):
        coleccion_historial.document(llave_mes).set(datos)
        st.success("¡Datos guardados con éxito!")

# --- MÓDULO 2: BANCOS Y CUENTAS ---
elif menu == "🏦 Cuentas, Bancos y Evolución":
    st.title("🏦 Análisis de Patrimonio")
    t_reg, t_bal, t_graf = st.tabs(["📝 Registrar Movimientos", "⚖️ Balance Calculado", "📈 Evolución Cronológica"])
    
    with t_reg:
        st.info("Anota el dinero que ENTRÓ y SALIÓ. El sistema calculará tu saldo real histórico.")
        col_m_b, col_a_b = st.columns(2)
        with col_m_b: m_sel = st.selectbox("Mes", meses_lista, index=mes_actual_idx, key="mb")
        with col_a_b: a_sel = st.selectbox("Año", [2025, 2026, 2027], index=1, key="ab")
        llave_b = f"{m_sel}_{a_sel}"
        
        datos_mes_banco = historial_bancos_data.get(llave_b, {})
        
        st.subheader("Cuentas Corrientes (Liquidez)")
        for cuenta in categorias_bancos["Débito"]:
            st.markdown(f"**{cuenta}**")
            c1, c2 = st.columns(2)
            with c1: datos_mes_banco[f"{cuenta}_ingresos"] = st.number_input(f"Ingresos / Abonos", value=limpiar_numero(datos_mes_banco.get(f"{cuenta}_ingresos", 0)), step=10000, key=f"{llave_b}_{cuenta}_i")
            with c2: datos_mes_banco[f"{cuenta}_egresos"] = st.number_input(f"Egresos / Gastos", value=limpiar_numero(datos_mes_banco.get(f"{cuenta}_egresos", 0)), step=10000, key=f"{llave_b}_{cuenta}_e")

        st.subheader("Tarjetas de Crédito (Deuda)")
        for tarjeta in categorias_bancos["Crédito"]:
            st.markdown(f"**{tarjeta}**")
            c1, c2 = st.columns(2)
            with c1: datos_mes_banco[f"{tarjeta}_ingresos"] = st.number_input(f"Abonos (Pago a la Tarjeta)", value=limpiar_numero(datos_mes_banco.get(f"{tarjeta}_ingresos", 0)), step=10000, key=f"{llave_b}_{tarjeta}_i")
            with c2: datos_mes_banco[f"{tarjeta}_egresos"] = st.number_input(f"Nuevas Compras (Uso TC)", value=limpiar_numero(datos_mes_banco.get(f"{tarjeta}_egresos", 0)), step=10000, key=f"{llave_b}_{tarjeta}_e")
            
        if st.button("💾 Guardar Movimientos Bancarios", use_container_width=True):
            coleccion_historial_bancos.document(llave_b).set(datos_mes_banco)
            st.success("¡Movimientos guardados!")
            st.rerun()

    with t_bal:
        saldos_calculados = {}
        for cta in categorias_bancos["Débito"]:
            saldos_calculados[cta] = sum(limpiar_numero(mes.get(f"{cta}_ingresos", 0)) for mes in historial_bancos_data.values()) - sum(limpiar_numero(mes.get(f"{cta}_egresos", 0)) for mes in historial_bancos_data.values())
        for tar in categorias_bancos["Crédito"]:
            saldos_calculados[tar] = sum(limpiar_numero(mes.get(f"{tar}_egresos", 0)) for mes in historial_bancos_data.values()) - sum(limpiar_numero(mes.get(f"{tar}_ingresos", 0)) for mes in historial_bancos_data.values())

        estado_liq = saldos_calculados.get("Cta. Corriente Banco Estado", 0)
        chile_liq = saldos_calculados.get("Cta. Corriente Banco de Chile", 0)
        chile_deuda_nac = saldos_calculados.get("TC Banco de Chile Nacional", 0)
        chile_deuda_int = saldos_calculados.get("TC Banco de Chile Internacional", 0)
        
        col_est, col_chi = st.columns(2)
        with col_est: st.success(f"**🏦 Banco Estado**\n\nLíquido Total: {clp(estado_liq)}")
        with col_chi: st.info(f"**🏦 Banco de Chile**\n\nLíquido: {clp(chile_liq)}\n\nDeuda TC Nac: {clp(chile_deuda_nac)}\n\nDeuda TC Int: {clp(chile_deuda_int)}\n\n**Neto: {clp(chile_liq - (chile_deuda_nac + chile_deuda_int))}**")

    with t_graf:
        if historial_bancos_data:
            meses_ordenados_b = sorted(historial_bancos_data.keys(), key=mes_a_fecha)
            filas_b = []
            acum = {c: 0 for c in categorias_bancos["Débito"]}
            for ll in meses_ordenados_b:
                d = historial_bancos_data[ll]
                fila = {'Mes': ll.replace("_", " ")}
                for c in categorias_bancos["Débito"]:
                    acum[c] += limpiar_numero(d.get(f"{c}_ingresos", 0)) - limpiar_numero(d.get(f"{c}_egresos", 0))
                    fila[c] = acum[c]
                filas_b.append(fila)
            st.plotly_chart(px.line(pd.DataFrame(filas_b), x='Mes', y=categorias_bancos["Débito"], markers=True, title="Liquidez en el Tiempo"), use_container_width=True)

# --- MÓDULO 3: DASHBOARD ---
elif menu == "📊 Dashboard: Planeado vs Real":
    st.title("📊 Dashboard Financiero")
    docs = coleccion_historial.stream()
    historial = {doc.id: doc.to_dict() for doc in docs}
    
    if not historial: st.info("Sube información histórica o registra un mes para ver el Dashboard.")
    else:
        # Se filtra historial corrupto por Excel headers y se ordena cronológicamente
        meses_validos = [m for m in historial.keys() if "Mes" not in m]
        meses_ordenados = sorted(meses_validos, key=mes_a_fecha)
        
        mes_analisis = st.selectbox("Mes a Analizar:", meses_ordenados, index=len(meses_ordenados)-1)
        datos_mes = historial[mes_analisis]
        
        # GASTOS GLOBALES: Aquí estaba el error. Ahora sumamos lo que pagaste a la TC ese mes.
        datos_banco_mes = historial_bancos_data.get(mes_analisis, {})
        tc_pagos_real = sum(limpiar_numero(datos_banco_mes.get(f"{tarjeta}_ingresos", 0)) for tarjeta in categorias_bancos["Crédito"])
        
        ing_real = sum(limpiar_numero(datos_mes.get(c, 0)) for c in categorias["Ingresos"])
        gas_fijo_real = sum(limpiar_numero(datos_mes.get(c, 0)) for c in categorias["Gastos Fijos"])
        gas_emergente_real = sum(limpiar_numero(datos_mes.get(c, 0)) for c in categorias["Gastos Emergentes"])
        
        # El Total Real AHORA SÍ incluye las fugas de dinero por deudas
        gas_total_real = gas_fijo_real + gas_emergente_real + tc_pagos_real
        
        # Proyecciones Base + Proyección de deuda
        ing_plan = sum(limpiar_numero(presupuesto_base.get(c, 0)) for c in categorias["Ingresos"])
        tc_pagos_plan = sum(limpiar_numero(det['cuota']) for det in compras_cuotas.values() if limpiar_numero(det['restantes']) > 0)
        gas_plan = sum(limpiar_numero(presupuesto_base.get(c, 0)) for c in categorias["Gastos Fijos"] + categorias["Gastos Emergentes"]) + tc_pagos_plan
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Dinero Real que Entró", clp(ing_real), delta=f"Proyectado: {clp(ing_plan)}")
        c2.metric("Salida Total Real (Incluye TC)", clp(gas_total_real), delta=f"Límite: {clp(gas_plan)}", delta_color="inverse" if gas_total_real > gas_plan else "normal")
        c3.metric("Ahorro Neto Real", clp(ing_real - gas_total_real))
        
        st.divider()
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            df_torta = pd.DataFrame({'Categoría': ['Gastos Fijos', 'Gastos Emergentes', 'Pago a Tarjetas'], 'Monto': [gas_fijo_real, gas_emergente_real, tc_pagos_real]})
            st.plotly_chart(px.pie(df_torta, values='Monto', names='Categoría', hole=0.4, title="¿A dónde se fue tu dinero?", color_discrete_sequence=['#1f77b4', '#d62728', '#ff7f0e']), use_container_width=True)
            
        with col_graf2:
            # Gráfico de barras cronológico de todos los meses
            st.subheader("Evolución de Ingresos y Gastos")
            hist_bar_data = []
            for m in meses_ordenados:
                d_m = historial[m]
                d_b_m = historial_bancos_data.get(m, {})
                i_tot = sum(limpiar_numero(d_m.get(c, 0)) for c in categorias["Ingresos"])
                g_tot = sum(limpiar_numero(d_m.get(c, 0)) for c in categorias["Gastos Fijos"] + categorias["Gastos Emergentes"])
                g_tot += sum(limpiar_numero(d_b_m.get(f"{tarjeta}_ingresos", 0)) for tarjeta in categorias_bancos["Crédito"])
                hist_bar_data.append({"Mes": m.replace("_", " "), "Ingresos": i_tot, "Egresos Totales": g_tot})
            
            st.plotly_chart(px.bar(pd.DataFrame(hist_bar_data), x="Mes", y=["Ingresos", "Egresos Totales"], barmode="group", color_discrete_map={"Ingresos": "green", "Egresos Totales": "red"}), use_container_width=True)

# --- MÓDULO 4: PROYECCIONES Y TARJETAS ---
elif menu == "🔮 Proyecciones Mensuales Detalladas":
    st.title("🔮 Cronograma de Deudas y Flujo")
    
    t_det, t_gest = st.tabs(["📅 Línea de Tiempo (6 Meses)", "💳 Ingresar Nuevas Deudas"])
    
    with t_det:
        st.info("Despliega los meses para ver exactamente qué cuotas te van a facturar.")
        gas_fijo_plan = sum(limpiar_numero(presupuesto_base.get(c, 0)) for c in categorias["Gastos Fijos"])
        ing_plan = sum(limpiar_numero(presupuesto_base.get(c, 0)) for c in categorias["Ingresos"])
        
        proy_datos = []
        for idx, mes_offset in enumerate(range(1, 7)):
            nombre_m = nombres_meses_futuros[idx]
            compras_mes = {k: v for k, v in compras_cuotas.items() if limpiar_numero(v['restantes']) >= mes_offset}
            total_tc_mes = sum(limpiar_numero(det['cuota']) for det in compras_mes.values())
            
            proy_datos.append({'Mes': nombre_m, 'Supervivencia Fija': gas_fijo_plan, 'Carga de Tarjetas': total_tc_mes, 'Ingresos': ing_plan})
            
            with st.expander(f"📌 {nombre_m} | Deuda TC a pagar: {clp(total_tc_mes)}", expanded=(idx==0)):
                if not compras_mes: st.success("Mes libre de cuotas.")
                else:
                    st.table(pd.DataFrame([{"Compra": k, "Valor": clp(v['cuota']), "Detalle": f"Cuota {(int(v['totales']) - int(v['restantes'])) + mes_offset} de {int(v['totales'])}"} for k, v in compras_mes.items()]))
                st.markdown(f"**Flujo Libre Estimado:** **{clp(ing_plan - (gas_fijo_plan + total_tc_mes))}**")
                
        st.divider()
        df_proy = pd.DataFrame(proy_datos)
        fig_proy = px.bar(df_proy, x='Mes', y=['Supervivencia Fija', 'Carga de Tarjetas'], title="Ingresos vs Carga Financiera a 6 meses", color_discrete_map={'Supervivencia Fija': '#1f77b4', 'Carga de Tarjetas': '#ff7f0e'})
        fig_proy.add_scatter(x=df_proy['Mes'], y=df_proy['Ingresos'], mode='lines+markers', name='Ingresos Proy.', marker=dict(color='green', size=10))
        st.plotly_chart(fig_proy, use_container_width=True)

    with t_gest:
        with st.expander("➕ Cargar Nueva Compra a la Tarjeta", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1: nueva_compra = st.text_input("Concepto / Producto")
            with c2: valor_cuota = st.number_input("Valor Cuota ($)", step=5000)
            with c3: cuotas_totales = st.number_input("Total Cuotas", min_value=1, step=1)
            with c4: cuotas_faltantes = st.number_input("Faltan por pagar", min_value=1, step=1)
            if st.button("Agregar al Cronograma"):
                if nueva_compra:
                    compras_cuotas[nueva_compra] = {"cuota": limpiar_numero(valor_cuota), "totales": int(cuotas_totales), "restantes": int(cuotas_faltantes)}
                    coleccion_config.document("compras_cuotas").set(compras_cuotas)
                    st.success("Compra ingresada.")
                    st.rerun()
                    
        st.subheader("Eliminar o Corregir Deudas")
        for item, det in list(compras_cuotas.items()):
            c_info, c_btn = st.columns([5, 1])
            c_info.markdown(f"**{item}** — {clp(det['cuota'])} / mes (Restan: {det['restantes']})")
            if c_btn.button("Eliminar", key=f"del_{item}"):
                del compras_cuotas[item]
                coleccion_config.document("compras_cuotas").set(compras_cuotas)
                st.rerun()

# --- MÓDULO 5: CONFIGURACIÓN Y CARGAS ---
elif menu == "⚙️ Configuración y Cargas":
    st.title("⚙️ Configuración y Cargas Masivas")
    
    st.subheader("🎯 1. Presupuesto Base Mensual")
    with st.expander("Modificar Presupuesto", expanded=False):
        nuevo_presupuesto = presupuesto_base.copy()
        for tipo, lista_cats in categorias.items():
            cols = st.columns(2)
            for idx, cat in enumerate(lista_cats):
                with cols[idx % 2]: nuevo_presupuesto[cat] = st.number_input(f"Límite {cat}", value=limpiar_numero(nuevo_presupuesto.get(cat, 0)), step=5000, key=f"p_{cat}")
        if st.button("Guardar Presupuesto", use_container_width=True):
            coleccion_config.document("presupuesto_base").set(nuevo_presupuesto)
            st.success("¡Presupuesto actualizado!")
            
    st.divider()
    st.subheader("➕ 2. Crear Apartados de Flujo Mensual")
    col_tipo_g, col_nombre_g = st.columns(2)
    with col_tipo_g: nueva_cat_tipo = st.selectbox("¿En qué pilar irá?", ["Ingresos", "Gastos Fijos", "Gastos Emergentes"])
    with col_nombre_g: nueva_cat_nombre = st.text_input("Nombre (Ej: Gimnasio)")
    if st.button("Crear Nueva Categoría"):
        if nueva_cat_nombre and nueva_cat_nombre not in categorias[nueva_cat_tipo]:
            categorias[nueva_cat_tipo].append(nueva_cat_nombre)
            coleccion_config.document("categorias").set(categorias)
            st.rerun()
            
    st.divider()
    st.subheader("📥 3. Cargas Masivas de Excel (.xlsx)")
    tab_hist, tab_deuda, tab_bancos = st.tabs(["1️⃣ Flujo Mensual", "2️⃣ Deudas en Cuotas", "3️⃣ Ingresos/Egresos de Bancos"])
    
    with tab_hist:
        todas_columnas = ["Mes_Anio"] + categorias["Ingresos"] + categorias["Gastos Fijos"] + categorias["Gastos Emergentes"]
        df_plantilla = pd.DataFrame(columns=todas_columnas)
        st.download_button("Descargar Plantilla Flujo", data=convertir_a_excel(df_plantilla), file_name="Flujo.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        arch_hist = st.file_uploader("Subir Flujo", type=["xlsx", "xls", "csv"], key="hist")
        if arch_hist:
            try:
                df_subido = pd.read_csv(arch_hist) if arch_hist.name.endswith('.csv') else pd.read_excel(arch_hist, engine='openpyxl')
                for _, row in df_subido.iterrows():
                    llave_csv = str(row.get('Mes_Anio', '')).strip()
                    if llave_csv and llave_csv.lower() != 'nan' and llave_csv != 'Mes_Anio':
                        datos_limpios = {k: limpiar_numero(v) for k, v in row.to_dict().items() if k != 'Mes_Anio'}
                        coleccion_historial.document(llave_csv).set(datos_limpios)
                st.success("¡Flujo cargado! Los errores anteriores han sido limpiados.")
            except Exception as e: st.error(f"Error al leer: {e}")

    with tab_deuda:
        df_plantilla_deudas = pd.DataFrame(columns=["Concepto", "Cuota_Mensual", "Totales", "Restantes"])
        st.download_button("Descargar Plantilla Deudas", data=convertir_a_excel(df_plantilla_deudas), file_name="Deudas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        arch_deuda = st.file_uploader("Subir Deudas", type=["xlsx", "xls", "csv"], key="deuda")
        if arch_deuda:
            try:
                df_deudas = pd.read_csv(arch_deuda) if arch_deuda.name.endswith('.csv') else pd.read_excel(arch_deuda, engine='openpyxl')
                for _, row in df_deudas.iterrows():
                    concepto_csv = str(row.get('Concepto', '')).strip()
                    if concepto_csv and concepto_csv.lower() != 'nan' and concepto_csv != 'Concepto':
                        compras_cuotas[concepto_csv] = {"cuota": limpiar_numero(row['Cuota_Mensual']), "totales": int(limpiar_numero(row['Totales'])), "restantes": int(limpiar_numero(row['Restantes']))}
                coleccion_config.document("compras_cuotas").set(compras_cuotas)
                st.success("¡Deudas importadas!")
            except Exception as e: st.error(f"Error al leer: {e}")
            
    with tab_bancos:
        columnas_bancos = ["Mes_Anio"]
        for cta in categorias_bancos["Débito"]: columnas_bancos.extend([f"{cta}_Ingresos", f"{cta}_Egresos"])
        for tar in categorias_bancos["Crédito"]: columnas_bancos.extend([f"{tar}_ingresos", f"{tar}_egresos"])
        
        df_plantilla_bancos = pd.DataFrame(columns=columnas_bancos)
        st.download_button("Descargar Plantilla Bancos", data=convertir_a_excel(df_plantilla_bancos), file_name="Historial_Bancos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        arch_bancos = st.file_uploader("Subir Bancos", type=["xlsx", "xls", "csv"], key="arch_bancos")
        if arch_bancos:
            try:
                df_subido_b = pd.read_csv(arch_bancos) if arch_bancos.name.endswith('.csv') else pd.read_excel(arch_bancos, engine='openpyxl')
                for _, row in df_subido_b.iterrows():
                    llave_csv = str(row.get('Mes_Anio', '')).strip()
                    if llave_csv and llave_csv.lower() != 'nan' and llave_csv != 'Mes_Anio':
                        datos_bancos_limpios = {}
                        for cta in categorias_bancos["Débito"]:
                            datos_bancos_limpios[f"{cta}_ingresos"] = limpiar_numero(row.get(f"{cta}_Ingresos", 0))
                            datos_bancos_limpios[f"{cta}_egresos"] = limpiar_numero(row.get(f"{cta}_Egresos", 0))
                        for tar in categorias_bancos["Crédito"]:
                            datos_bancos_limpios[f"{tar}_ingresos"] = limpiar_numero(row.get(f"{tar}_ingresos", 0))
                            datos_bancos_limpios[f"{tar}_egresos"] = limpiar_numero(row.get(f"{tar}_egresos", 0))
                        coleccion_historial_bancos.document(llave_csv).set(datos_bancos_limpios)
                st.success("¡Historial de bancos cargado y balance recalculado!")
            except Exception as e: st.error(f"Error al leer: {e}")
