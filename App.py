import streamlit as st

# Configuración de la página
st.set_page_config(page_title="Mis Finanzas V2", page_icon="📊", layout="centered")

st.title("📊 Dashboard Financiero")
st.markdown("Gestión estratégica de ingresos, costos operativos y estilo de vida.")

# Creación de pestañas para navegación móvil óptima
tab_ingresos, tab_fijos, tab_movilidad, tab_vida, tab_balance = st.tabs([
    "Ingresos", "Fijos", "Movilidad", "Estilo de Vida", "Balance"
])

# --- PESTAÑA 1: INGRESOS ---
with tab_ingresos:
    st.header("💰 Ingresos Mensuales")
    sueldo_base = st.number_input("Sueldo Base Líquido ($)", min_value=0.0, step=10000.0)
    turnos_extras = st.number_input("Turnos Adicionales / Horas Extras ($)", min_value=0.0, step=5000.0)
    bonos = st.number_input("Bonos / Otros Ingresos ($)", min_value=0.0, step=5000.0)
    
    total_ingresos = sueldo_base + turnos_extras + bonos
    st.success(f"**Ingresos Totales:** ${total_ingresos:,.0f}")

# --- PESTAÑA 2: GASTOS FIJOS (SUPERVIVENCIA) ---
with tab_fijos:
    st.header("🏠 Costos Operativos Base")
    arriendo = st.number_input("Arriendo / Dividendo ($)", min_value=0.0, step=10000.0)
    gastos_comunes = st.number_input("Gastos Comunes ($)", min_value=0.0, step=5000.0)
    cuentas = st.number_input("Cuentas Básicas (Luz, Agua, Gas, Internet) ($)", min_value=0.0, step=2000.0)
    supermercado = st.number_input("Supermercado y Aseo ($)", min_value=0.0, step=5000.0)
    
    total_fijos = arriendo + gastos_comunes + cuentas + supermercado
    st.info(f"**Total Fijos:** ${total_fijos:,.0f}")

# --- PESTAÑA 3: MOVILIDAD (VEHÍCULO) ---
with tab_movilidad:
    st.header("🚗 Vehículo y Transporte")
    bencina = st.number_input("Bencina ($)", min_value=0.0, step=5000.0)
    seguro_auto = st.number_input("Seguro Automotriz ($)", min_value=0.0, step=1000.0)
    tag_peajes = st.number_input("TAG y Peajes ($)", min_value=0.0, step=1000.0)
    mantenimiento = st.number_input("Fondo Mantenimiento / Estacionamiento ($)", min_value=0.0, step=2000.0)
    
    total_movilidad = bencina + seguro_auto + tag_peajes + mantenimiento
    st.info(f"**Total Movilidad:** ${total_movilidad:,.0f}")

# --- PESTAÑA 4: ESTILO DE VIDA Y OTROS ---
with tab_vida:
    st.header("☕ Estilo de Vida y Desarrollo")
    mascota = st.number_input("Mascota (Comida gato, arena, vet) ($)", min_value=0.0, step=2000.0)
    ocio = st.number_input("Salidas, Bares, Restaurantes, Citas ($)", min_value=0.0, step=5000.0)
    cuidado_personal = st.number_input("Cuidado Personal (Barbería, Ropa) ($)", min_value=0.0, step=2000.0)
    suscripciones = st.number_input("Suscripciones (Netflix, Spotify, Gym) ($)", min_value=0.0, step=1000.0)
    salud = st.number_input("Salud / Autocuidado ($)", min_value=0.0, step=5000.0)
    imprevistos = st.number_input("Fondo Imprevistos del Mes ($)", min_value=0.0, step=5000.0)
    
    total_vida = mascota + ocio + cuidado_personal + suscripciones + salud + imprevistos
    st.info(f"**Total Estilo de Vida:** ${total_vida:,.0f}")

# --- PESTAÑA 5: BALANCE Y MÉTRICAS ---
with tab_balance:
    st.header("📈 Resumen del Mes")
    
    total_gastos = total_fijos + total_movilidad + total_vida
    flujo_caja = total_ingresos - total_gastos
    
    # KPIs Financieros
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Ingresos", f"${total_ingresos:,.0f}")
        st.metric("Total Gastos", f"${total_gastos:,.0f}")
    with col2:
        st.metric("Flujo de Caja (Disponible)", f"${flujo_caja:,.0f}")
        
        # Calcular porcentaje de gasto sobre ingreso (evitar división por cero)
        if total_ingresos > 0:
            porcentaje_gasto = (total_gastos / total_ingresos) * 100
            st.metric("Nivel de Gasto", f"{porcentaje_gasto:.1f}%", delta_color="inverse")
        else:
            st.metric("Nivel de Gasto", "0%")

    st.divider()
    
    # Análisis de Salud Financiera
    st.subheader("Diagnóstico")
    if total_ingresos == 0:
        st.write("Registra tus ingresos para ver el diagnóstico.")
    elif flujo_caja > 0:
        st.success(f"**Excelente.** Tienes un excedente de **${flujo_caja:,.0f}**. Ideal para destinarlo a ahorro, inversión o proyectos personales.")
        
        # Regla 50/30/20 simplificada
        if porcentaje_gasto <= 80:
            st.write("Tus finanzas están sanas. Mantienes un buen margen de maniobra.")
        else:
            st.warning("Cuidado: Estás gastando una gran parte de tus ingresos. Revisa tus gastos de estilo de vida.")
            
    elif flujo_caja == 0:
        st.warning("Estás en el punto de equilibrio exacto. Cualquier imprevisto te dejará en números rojos.")
    else:
        st.error(f"**Alerta:** Tienes un déficit de **${abs(flujo_caja):,.0f}**. Estás financiando tu mes con deuda o ahorros previos.")
