import streamlit as st

# Configuración de la página para dispositivos móviles
st.set_page_config(page_title="Mis Finanzas", page_icon="💰", layout="centered")

st.title("💰 Control de Finanzas")
st.write("Gestiona tus ingresos, sueldo, horas extras y gastos mensuales de forma sencilla.")

# --- SECCIÓN 1: INGRESOS ---
st.header("1. Ingresos Mensuales")
sueldo_base = st.number_input("Sueldo Base ($)", min_value=0.0, value=0.0, step=1000.0)
horas_extras = st.number_input("Monto por Horas Extras ($)", min_value=0.0, value=0.0, step=500.0)

total_ingresos = sueldo_base + horas_extras
st.success(f"**Total Ingresos:** ${total_ingresos:,.2f}")

# --- SECCIÓN 2: GASTOS FIJOS NECESARIOS ---
st.header("2. Gastos Fijos Mensuales")

arriendo = st.number_input("Arriendo ($)", min_value=0.0, value=0.0, step=500.0)
alimentacion = st.number_input("Alimentación / Supermercado ($)", min_value=0.0, value=0.0, step=500.0)
bencina = st.number_input("Bencina / Combustible ($)", min_value=0.0, value=0.0, step=500.0)
cuentas_basicas = st.number_input("Cuentas Básicas (Luz, Agua, Gas, Internet) ($)", min_value=0.0, value=0.0, step=500.0)
gastos_comunes = st.number_input("Gastos Comunes ($)", min_value=0.0, value=0.0, step=500.0)
seguro_auto = st.number_input("Seguro de Auto ($)", min_value=0.0, value=0.0, step=500.0)

total_fijos = arriendo + alimentacion + bencina + cuentas_basicas + gastos_comunes + seguro_auto
st.info(f"**Total Gastos Fijos:** ${total_fijos:,.2f}")

# --- SECCIÓN 3: GASTOS EMERGENTES ---
st.header("3. Gastos Emergentes / Imprevistos")
gastos_emergentes = st.number_input("Monto en Gastos Emergentes del Mes ($)", min_value=0.0, value=0.0, step=500.0)

# --- RESUMEN FINAL ---
st.header("📊 Balance del Mes")
total_gastos = total_fijos + gastos_emergentes
balance = total_ingresos - total_gastos

col1, col2 = st.columns(2)
with col1:
    st.metric("Total Ingresos", f"${total_ingresos:,.2f}")
with col2:
    st.metric("Total Gastos", f"${total_gastos:,.2f}")

st.divider()

if balance > 0:
    st.success(f"¡Vas bien! Te quedan **${balance:,.2f}** disponibles para ahorro o libre disposición.")
elif balance == 0:
    st.warning("Estás con saldo exacto (Ingresos igualan a los gastos).")
else:
    st.error(f"¡Atención! Tienes un déficit de **${abs(balance):,.2f}**. Los gastos superan los ingresos.")
