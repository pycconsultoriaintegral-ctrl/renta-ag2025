# -*- coding: utf-8 -*-
import json

import pandas as pd
import streamlit as st

from core import db
from core.ui_common import init_app, sidebar_contribuyente, requiere_contribuyente, fmt_cop
from core.conciliacion import ESTADOS_LABELS

st.set_page_config(page_title="Ingresos - Renta AG2025", page_icon="💰", layout="wide")
init_app()
sidebar_contribuyente()
cid = requiere_contribuyente()

st.title("💰 Conciliación de ingresos")
st.caption(
    "La exógena NO es la declaración. Revise cada registro reportado por terceros y confirme su "
    "tratamiento real. Nada se convierte automáticamente en ingreso gravable."
)

with db.get_conn() as conn:
    registros = [dict(r) for r in conn.execute(
        "SELECT * FROM conciliacion WHERE contribuyente_id=? ORDER BY estado, tercero", (cid,)
    ).fetchall()]

if not registros:
    st.info("No hay registros de exógena importados. Vaya al menú **Exógena** primero.")
    st.stop()

st.markdown("### 1. Tabla de conciliación")
st.caption("Edite el **Estado** y la **Cédula sugerida** según la realidad económica del contribuyente. Guarde al final.")

df = pd.DataFrame(registros)
df_edit = df[["id", "tercero", "concepto", "valor", "cedula_sugerida", "tratamiento_sugerido", "estado", "soporte_requerido"]].copy()
df_edit["valor"] = df_edit["valor"].apply(fmt_cop)
df_edit["estado_label"] = df_edit["estado"].map(lambda e: ESTADOS_LABELS.get(e, e))

opciones_estado = list(ESTADOS_LABELS.keys())

edited = st.data_editor(
    df_edit.rename(columns={
        "tercero": "Tercero", "concepto": "Concepto", "valor": "Valor",
        "cedula_sugerida": "Cédula sugerida", "tratamiento_sugerido": "Tratamiento",
        "estado": "Estado (código)", "soporte_requerido": "Soporte requerido",
        "estado_label": "Estado",
    }),
    column_config={
        "Estado (código)": st.column_config.SelectboxColumn(options=opciones_estado, required=True),
        "id": None,
        "Estado": None,
    },
    disabled=["Tercero", "Concepto", "Valor", "Cédula sugerida", "Tratamiento", "Soporte requerido"],
    use_container_width=True,
    hide_index=True,
    key="editor_conciliacion",
)

if st.button("💾 Guardar cambios de conciliación", type="primary"):
    with db.get_conn() as conn:
        for _, row in edited.iterrows():
            conn.execute(
                "UPDATE conciliacion SET estado=? WHERE id=?",
                (row["Estado (código)"], int(row["id"])),
            )
    st.success("Conciliación actualizada.")
    st.rerun()

st.markdown("---")
st.markdown("### 2. Resumen por estado")
resumen = df.groupby("estado")["valor"].agg(["count", "sum"]).reset_index()
resumen["estado"] = resumen["estado"].map(lambda e: ESTADOS_LABELS.get(e, e))
resumen.columns = ["Estado", "Cantidad", "Suma"]
resumen["Suma"] = resumen["Suma"].apply(fmt_cop)
st.dataframe(resumen, use_container_width=True)

confirmados = df[df["estado"] == "CONFIRMADO"]
st.metric("Total CONFIRMADO", fmt_cop(confirmados["valor"].sum() if not confirmados.empty else 0))

st.markdown("---")
st.markdown("### 3. Ingresos definitivos por cédula (para el motor de liquidación)")
st.caption(
    "Estos valores se usan en el módulo de Liquidación. Puede partir de los registros CONFIRMADOS "
    "de arriba, pero debe ajustarlos con la información completa que usted conoce (incluyendo lo que "
    "no fue reportado por terceros, si corresponde declararlo)."
)

contrib = db.obtener_contribuyente(cid)
perfil = json.loads(contrib.get("perfil_json") or "{}")
ing_prev = perfil.get("ingresos_manual", {})

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Rentas de trabajo**")
    trabajo_bruto = st.number_input("Ingresos brutos por trabajo", min_value=0.0, value=float(ing_prev.get("trabajo_bruto", 0)), step=100000.0)
    trabajo_incrngo = st.number_input("Aportes obligatorios salud/pensión (INCRNGO)", min_value=0.0, value=float(ing_prev.get("trabajo_incrngo", 0)), step=10000.0)
    st.markdown("**Rentas de capital**")
    capital_bruto = st.number_input("Ingresos brutos de capital (intereses, arriendos)", min_value=0.0, value=float(ing_prev.get("capital_bruto", 0)), step=100000.0)
    capital_costos = st.number_input("Costos/gastos asociados a rentas de capital", min_value=0.0, value=float(ing_prev.get("capital_costos", 0)), step=100000.0)
with c2:
    st.markdown("**Rentas no laborales**")
    no_laboral_bruto = st.number_input("Ingresos brutos no laborales (honorarios independientes, etc.)", min_value=0.0, value=float(ing_prev.get("no_laboral_bruto", 0)), step=100000.0)
    no_laboral_costos = st.number_input("Costos/gastos asociados a rentas no laborales", min_value=0.0, value=float(ing_prev.get("no_laboral_costos", 0)), step=100000.0)
    st.markdown("**Pensiones**")
    pension_mensual = st.number_input("Ingreso mensual promedio por pensión", min_value=0.0, value=float(ing_prev.get("pension_mensual_promedio", 0)), step=100000.0)
    meses_pension = st.number_input("Meses del año con pago de pensión", min_value=0, max_value=12, value=int(ing_prev.get("meses_pension", 12)))

st.markdown("**Dividendos y participaciones**")
c3, c4 = st.columns(2)
dividendos_no_gravados = c3.number_input("Dividendos no gravados (Art. 49 num. 3 ET)", min_value=0.0, value=float(ing_prev.get("dividendos_no_gravados", 0)), step=100000.0)
dividendos_gravados = c4.number_input("Dividendos gravados", min_value=0.0, value=float(ing_prev.get("dividendos_gravados", 0)), step=100000.0)

if st.button("💾 Guardar ingresos definitivos"):
    perfil["ingresos_manual"] = {
        "trabajo_bruto": trabajo_bruto, "trabajo_incrngo": trabajo_incrngo,
        "capital_bruto": capital_bruto, "capital_costos": capital_costos,
        "no_laboral_bruto": no_laboral_bruto, "no_laboral_costos": no_laboral_costos,
        "pension_mensual_promedio": pension_mensual, "meses_pension": meses_pension,
        "dividendos_no_gravados": dividendos_no_gravados, "dividendos_gravados": dividendos_gravados,
    }
    db.upsert_contribuyente(cid, perfil_extra=perfil)
    st.success("Ingresos definitivos guardados. Vaya al módulo de **Liquidación** para ver el cálculo.")
