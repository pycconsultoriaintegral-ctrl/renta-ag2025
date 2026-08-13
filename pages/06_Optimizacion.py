# -*- coding: utf-8 -*-
import json

import pandas as pd
import streamlit as st

from core import db
from core.ui_common import init_app, sidebar_contribuyente, requiere_contribuyente, fmt_cop
from core import deducciones as dmod
from core import optimizador as opt

st.set_page_config(page_title="Optimización - Renta AG2025", page_icon="📊", layout="wide")
init_app()
sidebar_contribuyente()
cid = requiere_contribuyente()

st.title("📊 Optimización tributaria legal")
st.caption("Comparación de escenarios para identificar la MENOR CARGA TRIBUTARIA LEGALMENTE PROCEDENTE. Nunca se inventa un beneficio.")

contrib = db.obtener_contribuyente(cid)
perfil = json.loads(contrib.get("perfil_json") or "{}")
ing = perfil.get("ingresos_manual", {})

if not ing:
    st.warning("Complete primero el módulo **Ingresos**.")
    st.stop()

beneficios = dmod.listar_beneficios(cid)
if not beneficios:
    st.info("Aún no hay beneficios registrados en el módulo **Deducciones**. La comparación de escenarios será limitada.")

retenciones = float(perfil.get("retenciones_manual", 0))
cedula_pensiones_input = {
    "ingreso_pension_mensual_promedio": ing.get("pension_mensual_promedio", 0),
    "meses": int(ing.get("meses_pension", 12)),
}
dividendos_input = {
    "dividendos_2017_en_adelante_gravados": ing.get("dividendos_gravados", 0),
    "dividendos_2017_en_adelante_no_gravados": ing.get("dividendos_no_gravados", 0),
}
ganancias_ocasionales_items = perfil.get("ganancias_ocasionales", [])

resultado = opt.comparar_escenarios(ing, cedula_pensiones_input, beneficios, retenciones,
                                     dividendos_input, ganancias_ocasionales_items)

df = pd.DataFrame(resultado["escenarios"])
df_fmt = df.copy()
for col in ["renta_liquida", "renta_gravable", "impuesto_a_cargo", "retenciones", "saldo_a_pagar", "saldo_a_favor", "ahorro_vs_escenario_base"]:
    df_fmt[col] = df_fmt[col].apply(fmt_cop)
df_fmt.columns = ["Escenario", "Renta líquida", "Renta gravable", "Impuesto a cargo", "Retenciones",
                   "Saldo a pagar", "Saldo a favor", "Ahorro vs. escenario base"]
st.dataframe(df_fmt, use_container_width=True, hide_index=True)

st.success(f"✅ **Escenario óptimo legal disponible hoy:** {resultado['escenario_optimo_legal_hoy']}")
st.info(resultado["nota"])

mejor = min(resultado["escenarios"], key=lambda r: r["impuesto_a_cargo"])
if mejor["escenario"].startswith("C"):
    ahorro_potencial = mejor["ahorro_vs_escenario_base"] - resultado["escenarios"][1]["ahorro_vs_escenario_base"]
    if ahorro_potencial > 0:
        st.warning(
            f"💡 Si consigue los soportes documentales faltantes, podría ahorrar "
            f"**{fmt_cop(ahorro_potencial)}** adicionales. Revise el módulo **Deducciones** para ver "
            f"qué documentos hacen falta."
        )
