# -*- coding: utf-8 -*-
import json

import pandas as pd
import streamlit as st

from core import db
from core.ui_common import init_app, sidebar_contribuyente, requiere_contribuyente, fmt_cop
from core import patrimonio as pmod
from core import liquidacion as liq
from core import deducciones as dmod
from core.formulario210 import construir_formulario210

st.set_page_config(page_title="Formulario 210 - Renta AG2025", page_icon="📄", layout="wide")
init_app()
sidebar_contribuyente()
cid = requiere_contribuyente()

st.title("📄 Formulario 210 — AG2025")
st.warning(
    "⚠️ Los números de casilla mostrados corresponden a la estructura pública documentada del "
    "Formulario 210 vigente para AG2025. **Verifique cada número de casilla contra el formulario "
    "oficial en el portal MUISCA de la DIAN** antes de transcribir los valores, ya que esta "
    "herramienta es una guía y no reemplaza el formulario oficial."
)

contrib = db.obtener_contribuyente(cid)
perfil = json.loads(contrib.get("perfil_json") or "{}")
ing = perfil.get("ingresos_manual", {})

if not ing:
    st.info("Complete los módulos de Ingresos y Liquidación primero.")
    st.stop()

patr = pmod.calcular_patrimonio(cid)
beneficios_soportados = dmod.total_soportado(cid)
cedula_general = liq.liquidar_cedula_general(ing, beneficios_soportados)
cedula_pensiones = liq.liquidar_cedula_pensiones(ing.get("pension_mensual_promedio", 0), int(ing.get("meses_pension", 12)))
dividendos = liq.liquidar_dividendos(ing.get("dividendos_gravados", 0), ing.get("dividendos_no_gravados", 0))
ganancias_ocasionales = liq.liquidar_ganancias_ocasionales(perfil.get("ganancias_ocasionales", []))
retenciones = float(perfil.get("retenciones_manual", 0))
liquidacion = liq.liquidar_declaracion(cedula_general, cedula_pensiones, dividendos, ganancias_ocasionales,
                                       retenciones, float(perfil.get("descuentos_tributarios", 0)),
                                       float(perfil.get("anticipo_renta_anterior", 0)))

casillas = construir_formulario210(patr, cedula_general, cedula_pensiones, dividendos,
                                    ganancias_ocasionales, liquidacion, ing)

for c in casillas:
    borde_color = {"SALDO_A_PAGAR": "🔴", "SALDO_A_FAVOR": "🟢"}.get(c["estado"], "▪️")
    with st.container(border=True):
        st.markdown(f"**{borde_color} Casilla {c['casilla']} — {c['nombre']}**")
        cc1, cc2 = st.columns([1, 2])
        cc1.metric("Valor", fmt_cop(c["valor"]))
        cc2.write(f"**Origen:** {c['origen']}")
        cc2.write(f"**Explicación:** {c['explicacion']}")
        cc2.write(f"**Soporte:** {c['soporte']}")

st.markdown("---")
st.markdown("## Resultado final")
c1, c2, c3 = st.columns(3)
c1.metric("Total impuesto a cargo", fmt_cop(liquidacion["total_impuesto_a_cargo"]))
c2.metric("Retenciones", fmt_cop(liquidacion["retenciones_anio"]))
if liquidacion["saldo_a_pagar"] > 0:
    c3.metric("🔴 SALDO A PAGAR", fmt_cop(liquidacion["saldo_a_pagar"]))
else:
    c3.metric("🟢 SALDO A FAVOR", fmt_cop(liquidacion["saldo_a_favor"]))

df = pd.DataFrame(casillas)
csv = df.to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇️ Descargar guía del Formulario 210 (CSV)", csv, file_name=f"formulario210_{cid}.csv", mime="text/csv")
