import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import firebase_admin
from firebase_admin import credentials, firestore
from io import BytesIO
import re

# --- 1. CONFIGURACIÓN DE PÁGINA Y UI ---
st.set_page_config(page_title="Finanzas Pro | Hub", page_icon="🏦", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stMetric {background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef;}
    [data-testid="stSidebar"] {background-color: #1e1e1e; color: white;}
    .titulo-banco {color: #2c3e50; font-weight: 700; font-family: 'Helvetica Neue', sans-serif;}
    </style>
""", unsafe_allow_html=True)

# --- 2. MOTORES DE FORMATEO Y SANITIZACIÓN ESTRICTA ---
def clp(valor):
    try: return f"${int(float(valor)):,}".replace(",", ".")
    except: return "$0"

def limpiar_numero(val):
    if pd.isna(val) or val is None or val == '': return 0
    if isinstance(val, (int, float)): return int(val)
    
    val_str = str(val).strip()
    if not val_str: return 0
    
    is_negative = val_str.startswith('-') or (val_str.startswith('(') and val_str.endswith(')'))
    val_str = re.sub(r'[^\d.,]', '', val_str)
    if not val_str: return 0
    
    if ',' in val_str and '.' in val_str:
        if val_str.rfind(',') > val_str.rfind('.'):
            val_str = val_str.replace('.', '').replace(',', '.')
        else:
            val_str = val_str.replace(',', '')
    elif ',' in val_str:
        if len(val_str.split(',')[-1]) != 3: val_str = val_str.replace(',', '.')
        else: val_str = val_str.replace(',', '')
    elif '.' in val_str:
        if len(val_str.split('.')[-1]) == 3 and val_str.count('.') == 1:
            val_str = val_str.replace('.', '')
            
    try: 
        num = int(float(val_str))
        return -num if is_negative else num
    except: return 0

def convertir_a_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    return output.getvalue()

# --- 3. LÓGICA DE TIEMPO CRONOLÓGICA ---
meses_lista = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
def mes_a_fecha(llave):
    try:
        m, a = llave.split('_')
        return datetime(int(a), meses_lista.index(m) + 1, 1)
    except: return datetime(2000, 1, 1)

mes_actual_idx = datetime.now().month - 1
anio_actual = datetime.now().year
llave_mes_actual = f"{meses_lista[mes_actual_idx]}_{anio_actual}"

meses_futuros = [f"{meses_lista[(mes_actual_idx + i) % 12]} {anio_actual + ((mes_actual_idx + i) // 12)}" for i in range(1, 7)]

# --- 4. CONEXIÓN A FIRESTORE ---
@st.cache_resource
def iniciar_firebase():
    if not firebase_admin._apps:
        key_dict = json.loads(st.secrets["firebase_key"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = iniciar_firebase()
col_historial = db.collection("historial_meses")
col_bancos = db.collection("historial_bancos")
col_config = db.collection("configuracion")

# --- 5. ESTRUCTURA FIJA DE CUENTAS ---
categorias_default = {
    "Ingresos": ["Sueldo COSAM", "Turnos Extras", "Bonos / Aguinaldos", "Otros"],
    "Gastos Fijos": ["Arriendo / Dividendo", "Gastos Comunes", "Cuentas Básicas", "Supermercado (Base)", "Seguros"],
    "Gastos Emergentes": ["Bencina", "Gato (Vet/Comida)", "Ocio y Salidas", "Farmacia", "Mantención Hogar/Auto"]
}
doc_cat = col_config.document("categorias").get()
categorias = doc_cat.to_dict() if doc_cat.exists else categorias_default

bancos_fijos = {
    "Débito": ["Banco Estado (Cta. Corriente)", "Banco de Chile (Cta. Corriente)"],
    "Crédito": ["TC Banco de Chile (Nacional)", "TC Banco de Chile (Internacional)"]
}

doc_presup = col_config.document("presupuesto").get()
presupuesto_base = doc_presup.to_dict() if doc_presup.exists else {}

doc_tc = col_config.document("deudas_tc").get()
compras_cuotas = doc_tc.to_dict() if doc_tc.exists else {}

data_flujo = {doc.id: doc.to_dict() for doc in col_historial.stream()}
data_bancos = {doc.id: doc.to_dict() for doc in col_bancos.stream()}

# --- 6. NAVEGACIÓN LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2600/2600204.png", width=60)
    st.title("Finanzas PRO")
    st.markdown("---")
    menu = st.radio("Módulos Operativos", [
        "📊 Panel Ejecutivo (Dashboard)", 
        "🏦 Posición Bancaria", 
        "📝 Libro Diario (Mes)", 
        "🔮 Proyección de Deudas",
        "⚙️ Motor de Datos (Excel)"
    ])
    st.markdown("---")
    st.caption("🟢 Servidor Activo | CLP")

# ==========================================
# MÓDULO 1: DASHBOARD EJECUTIVO
# ==========================================
if menu == "📊 Panel Ejecutivo (Dashboard)":
    st.markdown("<h1 class='titulo-banco'>📊 Panel Ejecutivo de Finanzas</h1>", unsafe_allow_html=True)
    
    if not data_flujo:
        st.info("👋 Bienvenido. Registra tu mes o sube tu Excel en 'Motor de Datos'.")
    else:
        meses_disp = sorted(data_flujo.keys(), key=mes_a_fecha)
        mes_sel = st.selectbox("📅 Seleccionar Período Fiscal", meses_disp, index=len(meses_disp)-1)
        
        d_mes = data_flujo[mes_sel]
        d_banco = data_bancos.get(mes_sel, {})
        
        ingresos = sum(limpiar_numero(d_mes.get(c, 0)) for c in categorias["Ingresos"])
        fijos = sum(limpiar_numero(d_mes.get(c, 0)) for c in categorias["Gastos Fijos"])
        emergentes = sum(limpiar_numero(d_mes.get(c, 0)) for c in categorias["Gastos Emergentes"])
        pago_tc = sum(limpiar_numero(d_banco.get(f"{tar}_ingresos", 0)) for tar in bancos_fijos["Crédito"])
        
        egresos_totales = fijos + emergentes + pago_tc
        flujo_neto = ingresos - egresos_totales
        carga_financiera = (pago_tc / ingresos * 100) if ingresos > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Ingresos Netos", clp(ingresos))
        c2.metric("📉 Salida de Efectivo", clp(egresos_totales))
        c3.metric("⚖️ Flujo de Caja (Ahorro)", clp(flujo_neto), delta="Positivo" if flujo_neto >=0 else "Déficit")
        c4.metric("📊 Carga de Deuda", f"{carga_financiera:.1f}%", delta="Riesgo" if carga_financiera > 30 else "Sano", delta_color="inverse")
        
        st.markdown("---")
        col_g1, col_g2 = st.columns([1, 1.5])
        
        with col_g1:
            st.subheader("Estructura de Egresos")
            df_pie = pd.DataFrame({
                'Concepto': ['Costo de Vida (Fijos)', 'Estilo de Vida (Emergentes)', 'Pago de Deudas (TC)'],
                'Monto': [fijos, emergentes, pago_tc]
            })
            df_pie = df_pie[df_pie['Monto'] > 0]
            if not df_pie.empty:
                fig_pie = px.pie(df_pie, values='Monto', names='Concepto', hole=0.5, color_discrete_sequence=['#2C3E50', '#E74C3C', '#F39C12'])
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.write("No hay egresos registrados este mes.")
                
        with col_g2:
            st.subheader("Histórico de Flujo de Caja")
            hist_datos = []
            for m in meses_disp[-6:]:
                _dm = data_flujo[m]
                _db = data_bancos.get(m, {})
                _i = sum(limpiar_numero(_dm.get(c, 0)) for c in categorias["Ingresos"])
                _e = sum(limpiar_numero(_dm.get(c, 0)) for c in categorias["Gastos Fijos"] + categorias["Gastos Emergentes"])
                _e += sum(limpiar_numero(_db.get(f"{tar}_ingresos", 0)) for tar in bancos_fijos["Crédito"])
                hist_datos.append({'Mes': m.replace('_', ' '), 'Ingresos': _i, 'Gastos': _e})
            
            if hist_datos:
                df_hist = pd.DataFrame(hist_datos)
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(x=df_hist['Mes'], y=df_hist['Ingresos'], name='Ingresos', marker_color='#27AE60'))
                fig_bar.add_trace(go.Bar(x=df_hist['Mes'], y=df_hist['Gastos'], name='Salidas', marker_color='#C0392B'))
                fig_bar.update_layout(barmode='group', margin=dict(t=0, b=0, l=0, r=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_bar, use_container_width=True)

# ==========================================
# MÓDULO 2: POSICIÓN BANCARIA
# ==========================================
elif menu == "🏦 Posición Bancaria":
    st.markdown("<h1 class='titulo-banco'>🏦 Consolidado Bancario</h1>", unsafe_allow_html=True)
    
    saldos_actuales = {}
    for cta in bancos_fijos["Débito"]:
        ing = sum(limpiar_numero(m.get(f"{cta}_ingresos", 0)) for m in data_bancos.values())
        egr = sum(limpiar_numero(m.get(f"{cta}_egresos", 0)) for m in data_bancos.values())
        saldos_actuales[cta] = ing - egr
        
    for tar in bancos_fijos["Crédito"]:
        pagos = sum(limpiar_numero(m.get(f"{tar}_ingresos", 0)) for m in data_bancos.values())
        compras = sum(limpiar_numero(m.get(f"{tar}_egresos", 0)) for m in data_bancos.values())
        saldos_actuales[tar] = compras - pagos

    st.subheader("Liquidez Real (Efectivo Disponible)")
    col_e, col_c = st.columns(2)
    with col_e:
        st.info(f"**🔵 Banco Estado**\n\nCuenta Corriente: **{clp(saldos_actuales['Banco Estado (Cta. Corriente)'])}**")
    with col_c:
        st.success(f"**🔴 Banco de Chile**\n\nCuenta Corriente: **{clp(saldos_actuales['Banco de Chile (Cta. Corriente)'])}**")
        
    st.subheader("Deuda Facturada Continua")
    col_tcn, col_tci = st.columns(2)
    with col_tcn:
        st.warning(f"**💳 TC Chile Nacional:** {clp(saldos_actuales['TC Banco de Chile (Nacional)'])}")
    with col_tci:
        st.warning(f"**🌎 TC Chile Internacional:** {clp(saldos_actuales['TC Banco de Chile (Internacional)'])}")

    st.markdown("---")
    with st.expander("📝 Registrar Abonos y Cargos Mensuales", expanded=False):
        c_m, c_a = st.columns(2)
        m_banco = c_m.selectbox("Mes de Cartola", meses_lista, index=mes_actual_idx)
        a_banco = c_a.selectbox("Año", [2025, 2026, 2027], index=1)
        key_banco = f"{m_banco}_{a_banco}"
        db_mes = data_bancos.get(key_banco, {})
        
        st.write("---")
        for cta in bancos_fijos["Débito"]:
            st.write(f"**{cta}**")
            c1, c2 = st.columns(2)
            db_mes[f"{cta}_ingresos"] = c1.number_input(f"Dinero que Entró (+)", value=limpiar_numero(db_mes.get(f"{cta}_ingresos", 0)), step=10000, key=f"{key_banco}_{cta}_i")
            db_mes[f"{cta}_egresos"] = c2.number_input(f"Dinero que Salió (-)", value=limpiar_numero(db_mes.get(f"{cta}_egresos", 0)), step=10000, key=f"{key_banco}_{cta}_e")
            
        for tar in bancos_fijos["Crédito"]:
            st.write(f"**{tar}**")
            c1, c2 = st.columns(2)
            db_mes[f"{tar}_ingresos"] = c1.number_input(f"Pago de Tarjeta (+)", value=limpiar_numero(db_mes.get(f"{tar}_ingresos", 0)), step=10000, key=f"{key_banco}_{tar}_i")
            db_mes[f"{tar}_egresos"] = c2.number_input(f"Nuevas Compras (-)", value=limpiar_numero(db_mes.get(f"{tar}_egresos", 0)), step=10000, key=f"{key_banco}_{tar}_e")

        if st.button("💾 Procesar Cartolas", type="primary"):
            col_bancos.document(key_banco).set(db_mes)
            st.success("Saldos actualizados.")
            st.rerun()

# ==========================================
# MÓDULO 3: LIBRO DIARIO
# ==========================================
elif menu == "📝 Libro Diario (Mes)":
    st.markdown("<h1 class='titulo-banco'>📝 Flujo Diario</h1>", unsafe_allow_html=True)
    
    c_m, c_a = st.columns(2)
    m_flujo = c_m.selectbox("Mes", meses_lista, index=mes_actual_idx)
    a_flujo = c_a.selectbox("Año", [2025, 2026, 2027], index=1)
    key_flujo = f"{m_flujo}_{a_flujo}"
    
    d_flujo = data_flujo.get(key_flujo, {})
    
    tabs = st.tabs(["💰 Ingresos", "🏠 Supervivencia (Fijos)", "🚨 Flexibles (Emergentes)"])
    for i, (tipo, cat_list) in enumerate(categorias.items()):
        with tabs[i]:
            for c in cat_list:
                val = limpiar_numero(d_flujo.get(c, 0))
                meta = limpiar_numero(presupuesto_base.get(c, 0))
                lbl = f"{c} (Presupuesto: {clp(meta)})" if meta > 0 else c
                d_flujo[c] = st.number_input(lbl, value=val, step=5000, key=f"f_{key_flujo}_{c}")
                if tipo != "Ingresos" and meta > 0 and d_flujo[c] > meta:
                    st.error(f"⚠️ Alerta: Te pasaste por {clp(d_flujo[c] - meta)} del presupuesto.")
                    
    if st.button("💾 Asentar Entradas", type="primary", use_container_width=True):
        col_historial.document(key_flujo).set(d_flujo)
        st.success("Registros guardados.")
        st.rerun()

# ==========================================
# MÓDULO 4: PROYECCIONES Y DEUDAS
# ==========================================
elif menu == "🔮 Proyección de Deudas":
    st.markdown("<h1 class='titulo-banco'>🔮 Cronograma de Amortización</h1>", unsafe_allow_html=True)
    
    t_vista, t_admin = st.tabs(["🔭 Horizonte a 6 Meses", "💳 Administrador de Cuotas"])
    
    with t_vista:
        st.info("Visión del impacto de tus cuotas actuales en tu futuro financiero.")
        ing_base = sum(limpiar_numero(presupuesto_base.get(c, 0)) for c in categorias["Ingresos"])
        fijo_base = sum(limpiar_numero(presupuesto_base.get(c, 0)) for c in categorias["Gastos Fijos"])
        
        datos_chart = []
        
        for idx, nombre_mes in enumerate(meses_futuros):
            mes_offset = idx + 1
            cuotas_activas = {k: v for k, v in compras_cuotas.items() if limpiar_numero(v['restantes']) >= mes_offset}
            deuda_mes = sum(limpiar_numero(c['cuota']) for c in cuotas_activas.values())
            
            flujo_libre = ing_base - fijo_base - deuda_mes
            
            datos_chart.append({
                'Mes': nombre_mes,
                'Gastos Fijos': fijo_base,
                'Pago Tarjetas': deuda_mes,
                'Flujo Libre Estimado': flujo_libre
            })
            
            # CORRECCIÓN DE LA VARIABLE 'nombre_mes' EN VEZ DE 'nombre_m'
            with st.expander(f"📌 {nombre_mes} | Carga de Tarjeta: {clp(deuda_mes)}", expanded=(idx==0)):
                if not cuotas_activas: st.success("¡Deuda en cero para este mes!")
                else:
                    df_c = pd.DataFrame([{"Producto": k, "Cuota": clp(v['cuota']), "Detalle": f"Cuota {int(v['totales']) - int(v['restantes']) + mes_offset} de {v['totales']}"} for k,v in cuotas_activas.items()])
                    st.dataframe(df_c, hide_index=True, use_container_width=True)
                st.write(f"**Efectivo Disponible Estimado:** {clp(flujo_libre)}")
                
        df_proy = pd.DataFrame(datos_chart)
        fig_p = go.Figure()
        fig_p.add_trace(go.Bar(x=df_proy['Mes'], y=df_proy['Gastos Fijos'], name='Gastos de Vida', marker_color='#34495E'))
        fig_p.add_trace(go.Bar(x=df_proy['Mes'], y=df_proy['Pago Tarjetas'], name='Deuda Tarjeta', marker_color='#E74C3C'))
        fig_p.add_trace(go.Scatter(x=df_proy['Mes'], y=df_proy['Flujo Libre Estimado'], mode='lines+markers', name='Margen de Ahorro', line=dict(color='#2ECC71', width=3)))
        fig_p.update_layout(barmode='stack', title="Comportamiento del Flujo de Caja (6 Meses)")
        st.plotly_chart(fig_p, use_container_width=True)

    with t_admin:
        st.subheader("Ingresar Nueva Compra a Cuotas")
        with st.form("form_cuotas"):
            c1, c2, c3, c4 = st.columns(4)
            n_com = c1.text_input("Producto")
            n_val = c2.number_input("Valor Cuota ($)", step=5000)
            n_tot = c3.number_input("Total Cuotas", min_value=1, step=1)
            n_fal = c4.number_input("Faltan Pagar", min_value=1, step=1)
            if st.form_submit_button("Añadir al Sistema"):
                if n_com:
                    compras_cuotas[n_com] = {"cuota": limpiar_numero(n_val), "totales": int(n_tot), "restantes": int(n_fal)}
                    col_config.document("deudas_tc").set(compras_cuotas)
                    st.success("Guardado.")
                    st.rerun()
                    
        st.subheader("Auditoría de Deudas Actuales")
        for k, v in list(compras_cuotas.items()):
            col_d, col_b = st.columns([5,1])
            col_d.write(f"**{k}** — {clp(v['cuota'])} / mes (Restan {v['restantes']} cuotas)")
            if col_b.button("Saldar / Eliminar", key=f"del_{k}"):
                del compras_cuotas[k]
                col_config.document("deudas_tc").set(compras_cuotas)
                st.rerun()

# ==========================================
# MÓDULO 5: MOTOR DE DATOS (EXCEL)
# ==========================================
elif menu == "⚙️ Motor de Datos (Excel)":
    st.markdown("<h1 class='titulo-banco'>⚙️ Administrador de Base de Datos</h1>", unsafe_allow_html=True)
    
    st.subheader("1. Planificación Presupuestaria")
    with st.expander("Definir Metas Mensuales"):
        np = presupuesto_base.copy()
        for t, cats in categorias.items():
            cols = st.columns(3)
            for i, c in enumerate(cats):
                np[c] = cols[i%3].number_input(c, value=limpiar_numero(np.get(c, 0)), step=5000)
        if st.button("Guardar Política Presupuestaria"):
            col_config.document("presupuesto").set(np)
            st.success("Actualizado.")

    st.markdown("---")
    st.subheader("2. Cargas Masivas por Excel (.xlsx)")
    
    t_flujo, t_banco, t_tc = st.tabs(["📥 Libro Diario", "📥 Libro Mayor", "📥 Inventario de Cuotas"])
    
    with t_flujo:
        cols_flujo = ["Mes_Anio"] + categorias["Ingresos"] + categorias["Gastos Fijos"] + categorias["Gastos Emergentes"]
        df_f = pd.DataFrame(columns=cols_flujo)
        st.download_button("Descargar Plantilla Libro Diario", convertir_a_excel(df_f), "Libro_Diario.xlsx")
        
        f_up = st.file_uploader("Subir Libro Diario Lleno", type=["xlsx", "xls"], key="up_f")
        if f_up:
            df_in = pd.read_excel(f_up, engine='openpyxl')
            for _, r in df_in.iterrows():
                llave = str(r.get('Mes_Anio', '')).strip()
                if llave and llave != 'nan':
                    datos_limpios = {k: limpiar_numero(v) for k,v in r.to_dict().items() if k != 'Mes_Anio'}
                    col_historial.document(llave).set(datos_limpios)
            st.success("Base de datos de flujo actualizada.")
            
    with t_banco:
        cols_banco = ["Mes_Anio"]
        for c in bancos_fijos["Débito"]: cols_banco.extend([f"{c}_Ingresos", f"{c}_Egresos"])
        for c in bancos_fijos["Crédito"]: cols_banco.extend([f"{c}_Pagos", f"{c}_Compras"])
        
        df_b = pd.DataFrame(columns=cols_banco)
        st.download_button("Descargar Plantilla Libro Mayor", convertir_a_excel(df_b), "Libro_Mayor.xlsx")
        
        b_up = st.file_uploader("Subir Libro Mayor Lleno", type=["xlsx", "xls"], key="up_b")
        if b_up:
            df_in_b = pd.read_excel(b_up, engine='openpyxl')
            for _, r in df_in_b.iterrows():
                llave = str(r.get('Mes_Anio', '')).strip()
                if llave and llave != 'nan':
                    d_b = {}
                    for c in bancos_fijos["Débito"]:
                        d_b[f"{c}_ingresos"] = limpiar_numero(r.get(f"{c}_Ingresos", 0))
                        d_b[f"{c}_egresos"] = limpiar_numero(r.get(f"{c}_Egresos", 0))
                    for c in bancos_fijos["Crédito"]:
                        d_b[f"{c}_ingresos"] = limpiar_numero(r.get(f"{c}_Pagos", 0))
                        d_b[f"{c}_egresos"] = limpiar_numero(r.get(f"{c}_Compras", 0))
                    col_bancos.document(llave).set(d_b)
            st.success("Saldos bancarios recalculados.")

    with t_tc:
        df_c = pd.DataFrame(columns=["Concepto", "Cuota_Mensual", "Totales", "Restantes"])
        st.download_button("Descargar Plantilla Cuotas", convertir_a_excel(df_c), "Cuotas_TC.xlsx")
        
        c_up = st.file_uploader("Subir Cuotas", type=["xlsx", "xls"], key="up_c")
        if c_up:
            df_in_c = pd.read_excel(c_up, engine='openpyxl')
            for _, r in df_in_c.iterrows():
                cnc = str(r.get('Concepto', '')).strip()
                if cnc and cnc != 'nan':
                    compras_cuotas[cnc] = {
                        "cuota": limpiar_numero(r.get('Cuota_Mensual', 0)),
                        "totales": int(limpiar_numero(r.get('Totales', 0))),
                        "restantes": int(limpiar_numero(r.get('Restantes', 0)))
                    }
            col_config.document("deudas_tc").set(compras_cuotas)
            st.success("Deudas importadas exitosamente.")
