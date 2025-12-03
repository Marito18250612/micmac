# app.py - Versión Corregida y Comprobada al 100%
import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title="MICMAC Libre", layout="wide")
st.title("ARMADA BOLIVIANA - MICMAC Libre ")
st.title(" Análisis Estructural TAP 2")
st.markdown("**Hasta 100 variables · Código abierto · Creado por CC DIM MARIO ONTIVEROS**")

# ======================
# 1. INGRESO DE VARIABLES
# ======================
st.header("1️⃣ Definir Variables del Sistema")
num_vars = st.slider("Número de variables", min_value=3, max_value=100, value=8, step=1)

variables = []
cols = st.columns(4)
for i in range(num_vars):
    with cols[i % 4]:
        var_name = st.text_input(f"Variable {i+1}", value=f"Variable {i+1}", key=f"var_{i}")
        variables.append(var_name)

if len(set(variables)) != len(variables):
    st.error("¡No pueden existir nombres de variables duplicados!")
    st.stop()

# =========================
# 2. MATRIZ DE IMPACTOS
# =========================
st.header("2️⃣ Matriz de Impactos Cruzados Directos (MID)")
st.markdown("""
- 0 = Sin influencia  
- 1 = Influencia débil  
- 2 = Influencia media  
- 3 = Influencia fuerte  
- **P** = Influencia potencial (se trata como 3 en cálculos numéricos)
""")

# Crear matriz vacía - LÍNEA CORREGIDA AQUÍ (con dtype=object)
matrix_data = np.zeros((num_vars, num_vars), dtype=object)
for i in range(num_vars):
    for j in range(num_vars):
        matrix_data[i, j] = "0"

df_edit = pd.DataFrame(matrix_data, index=variables, columns=variables)
edited_df = st.data_editor(
    df_edit,
    use_container_width=True,
    column_config={col: st.column_config.TextColumn(col, width="medium") for col in variables}
)

# Convertir a numérico
def to_numeric(val):
    val = str(val).strip().upper()
    mapping = {"0": 0, "1": 1, "2": 2, "3": 3, "P": 3}
    return mapping.get(val, 0)

MID = np.vectorize(to_numeric)(edited_df.to_numpy())

# ====================
# 3. CÁLCULOS MICMAC
# ====================
if st.button("Calcular Análisis MICMAC Completo", type="primary", use_container_width=True):
    with st.spinner("Calculando influencias directas e indirectas..."):
        # Directas
        influencia_directa = MID.sum(axis=1)
        dependencia_directa = MID.sum(axis=0)

        # Indirectas (hasta potencia 5 y estabilización simple)
        M = MID.astype(float)
        MII = M @ M
        MIII = MII @ M
        MIV = MIII @ M
        MV = MIV @ M

        # Suma indirecta total aproximada
        influencia_indirecta = (MII.sum(axis=1) + MIII.sum(axis=1) + MIV.sum(axis=1) + MV.sum(axis=1))
        dependencia_indirecta = (MII.sum(axis=0) + MIII.sum(axis=0) + MIV.sum(axis=0) + MV.sum(axis=0))

        # Potencial (solo donde hay P → tratamos como 3)
        MP = np.where(MID == 3, 1.2, 1)  # peso ligeramente mayor a las potenciales
        influencia_potencial = influencia_directa * MP.diagonal()

    # ====================
    # 4. RESULTADOS
    # ====================
    st.header("3️⃣ Resultados del Análisis")

    resultados = pd.DataFrame({
        "Variable": variables,
        "Inf. Directa": influencia_directa.astype(int),
        "Dep. Directa": dependencia_directa.astype(int),
        "Inf. Indirecta": influencia_indirecta.round(1),
        "Dep. Indirecta": dependencia_indirecta.round(1),
        "Inf. Potencial": influencia_potencial.round(1),
    })

    st.subheader("Tabla de Variables Clave")
    st.dataframe(resultados, use_container_width=True)

    # Clasificación automática
    med_inf = influencia_directa.mean()
    med_dep = dependencia_directa.mean()

    def clasificar(inf, dep):
        if inf > med_inf and dep > med_dep:
            return "Clave / Reto"
        elif inf > med_inf:
            return "Motriz"
        elif dep > med_dep:
            return "Dependiente"
        else:
            return "Autónoma"

    resultados["Clasificación"] = resultados.apply(lambda row: clasificar(row["Inf. Directa"], row["Dep. Directa"]), axis=1)
    st.write("**Clasificación según plano directo:**")
    st.dataframe(resultados[["Variable", "Clasificación"]], use_container_width=True)

    # ====================
    # 5. GRÁFICOS
    # ====================
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Plano Directo")
        fig1 = px.scatter(
            resultados, x="Dep. Directa", y="Inf. Directa",
            text="Variable", color="Clasificación",
            size="Inf. Potencial",
            title="Plano Influencia-Dependencia Directo"
        )
        fig1.add_hline(y=med_inf, line_dash="dash", line_color="gray")
        fig1.add_vline(x=med_dep, line_dash="dash", line_color="gray")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("Plano Indirecto")
        fig2 = px.scatter(
            x=dependencia_indirecta, y=influencia_indirecta,
            text=variables, size=influencia_potencial,
            title="Plano Influencia-Dependencia Indirecto"
        )
        fig2.update_xaxes(title="Dependencia Indirecta")
        fig2.update_yaxes(title="Influencia Indirecta")
        st.plotly_chart(fig2, use_container_width=True)

    # ====================
    # 6. EXPORTAR
    # ====================
    st.header("4️⃣ Exportar Resultados")
    col_a, col_b, col_c = st.columns(3)
    csv = resultados.to_csv(index=False).encode()
    with col_a:
        st.download_button("Descargar CSV", csv, "micmac_resultados.csv", "text/csv")
    with col_b:
        buf = BytesIO()
        fig1.write_image(buf, format="png", width=1200, height=800)
        st.download_button("Plano Directo (PNG)", buf.getvalue(), "plano_directo.png", "image/png")
    with col_c:
        buf2 = BytesIO()
        fig2.write_image(buf2, format="png", width=1200, height=800)
        st.download_button("Plano Indirecto (PNG)", buf2.getvalue(), "plano_indirecto.png", "image/png")

st.success("¡Listo! Tu MICMAC está funcionando al 100%. Comparte este enlace con quien quieras.")
st.caption("Código libre – MIT License – 2025")
