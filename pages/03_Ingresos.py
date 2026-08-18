# -*- coding: utf-8 -*-
import json

import pandas as pd
import streamlit as st

from core import db
from core.ui_common import init_app, sidebar_contribuyente, requiere_contribuyente, fmt_cop
from core.conciliacion import ESTADOS_LABELS
from core import autollenado

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

if st.button("🔄 Autocompletar retenciones y renta de capital confirmadas desde la exógena",
             help="Solo trae valores donde no hay ambigüedad: retenciones ya marcadas CONFIRMADO y "
                  "rentas de capital ya marcadas CONFIRMADO. Trabajo, no laborales y pensión los debe "
                  "revisar usted porque su tratamiento depende de hechos que la exógena no reporta "
                  "(habitualidad, tiempo de tenencia, existencia de costos, etc.)."):
    # Los valores sugeridos son totales ya calculados de forma fresca desde la
    # conciliación (no acumulados) -> se REEMPLAZA el valor existente, nunca se
    # suma, para que hacer clic varias veces no duplique las cifras.
    sugerencias = autollenado.autocompletar_ingresos(cid)
    st.session_state[f"ing_capital_bruto_{cid}"] = sugerencias["capital_bruto_sugerido"]
    perfil["retenciones_manual"] = sugerencias["retenciones_sugeridas"]
    db.upsert_contribuyente(cid, perfil_extra=perfil)
    if sugerencias["pendientes_revision_manual"]:
        detalle_pendientes = "; ".join(
            f"{r['concepto']} ({fmt_cop(r['valor'])})" for r in sugerencias["pendientes_revision_manual"][:5]
        )
        st.warning(f"Quedan {len(sugerencias['pendientes_revision_manual'])} registro(s) de ingreso que "
                   f"requieren su revisión manual (no se autocompletan): {detalle_pendientes}")
    st.success(f"Retenciones: {fmt_cop(sugerencias['retenciones_sugeridas'])} · "
               f"Capital bruto: {fmt_cop(sugerencias['capital_bruto_sugerido'])}. "
               "Estos valores REEMPLAZAN lo que hubiera en esos dos campos (puede hacer clic varias veces "
               "sin duplicar). Si había agregado manualmente otro ingreso de capital no reportado por "
               "terceros, vuelva a sumarlo aparte.")
    st.rerun()

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Rentas de trabajo**")
    trabajo_bruto = st.number_input("Ingresos brutos por trabajo", min_value=0.0, value=float(ing_prev.get("trabajo_bruto", 0)), step=100000.0, key=f"ing_trabajo_bruto_{cid}")
    trabajo_incrngo = st.number_input("Aportes obligatorios salud/pensión (INCRNGO)", min_value=0.0, value=float(ing_prev.get("trabajo_incrngo", 0)), step=10000.0, key=f"ing_trabajo_incrngo_{cid}")
    st.markdown("**Rentas de capital**")
    capital_bruto = st.number_input("Ingresos brutos de capital (intereses, arriendos)", min_value=0.0, value=float(ing_prev.get("capital_bruto", 0)), step=100000.0, key=f"ing_capital_bruto_{cid}")
    capital_costos = st.number_input("Costos/gastos asociados a rentas de capital", min_value=0.0, value=float(ing_prev.get("capital_costos", 0)), step=100000.0, key=f"ing_capital_costos_{cid}")
with c2:
    st.markdown("**Rentas no laborales**")
    no_laboral_bruto = st.number_input("Ingresos brutos no laborales (honorarios independientes, etc.)", min_value=0.0, value=float(ing_prev.get("no_laboral_bruto", 0)), step=100000.0, key=f"ing_no_laboral_bruto_{cid}")
    no_laboral_costos = st.number_input("Costos/gastos asociados a rentas no laborales", min_value=0.0, value=float(ing_prev.get("no_laboral_costos", 0)), step=100000.0, key=f"ing_no_laboral_costos_{cid}")
    st.markdown("**Pensiones**")
    pension_mensual = st.number_input("Ingreso mensual promedio por pensión", min_value=0.0, value=float(ing_prev.get("pension_mensual_promedio", 0)), step=100000.0, key=f"ing_pension_mensual_{cid}")
    meses_pension = st.number_input("Meses del año con pago de pensión", min_value=0, max_value=12, value=int(ing_prev.get("meses_pension", 12)), key=f"ing_meses_pension_{cid}")

st.markdown("**Dividendos y participaciones**")
c3, c4 = st.columns(2)
dividendos_no_gravados = c3.number_input("Dividendos no gravados (Art. 49 num. 3 ET)", min_value=0.0, value=float(ing_prev.get("dividendos_no_gravados", 0)), step=100000.0, key=f"ing_div_no_grav_{cid}")
dividendos_gravados = c4.number_input("Dividendos gravados", min_value=0.0, value=float(ing_prev.get("dividendos_gravados", 0)), step=100000.0, key=f"ing_div_grav_{cid}")

if st.button("💾 Guardar ingresos definitivos", type="primary"):
    perfil["ingresos_manual"] = {
        "trabajo_bruto": trabajo_bruto, "trabajo_incrngo": trabajo_incrngo,
        "capital_bruto": capital_bruto, "capital_costos": capital_costos,
        "no_laboral_bruto": no_laboral_bruto, "no_laboral_costos": no_laboral_costos,
        "pension_mensual_promedio": pension_mensual, "meses_pension": meses_pension,
        "dividendos_no_gravados": dividendos_no_gravados, "dividendos_gravados": dividendos_gravados,
    }
    db.upsert_contribuyente(cid, perfil_extra=perfil)
    st.success("Ingresos definitivos guardados. Vaya al módulo de **Liquidación** para ver el cálculo.")
    st.rerun()

st.markdown("---")
st.markdown("### 4. Ganancias ocasionales")
st.caption(
    "Venta de activos poseídos por MÁS de 2 años, herencias/legados, loterías y similares. "
    "Tributan aparte de la cédula general, normalmente al 15% sobre la utilidad (venta - costo fiscal). "
    "Si el activo se poseyó 2 años o menos, NO va aquí: es renta ordinaria (arriba, en 'no laborales')."
)

ganancias_prev = perfil.get("ganancias_ocasionales", [])
if ganancias_prev:
    for i, g in enumerate(ganancias_prev):
        cc1, cc2, cc3, cc4, cc5 = st.columns([2, 2, 2, 3, 1])
        cc1.write(g.get("tipo", "otro"))
        cc2.write(fmt_cop(g.get("valor_bruto", 0)))
        cc3.write(fmt_cop(g.get("costo_fiscal", 0)))
        cc4.write(g.get("nota", ""))
        if cc5.button("🗑️", key=f"del_go_{i}_{cid}"):
            ganancias_prev.pop(i)
            perfil["ganancias_ocasionales"] = ganancias_prev
            db.upsert_contribuyente(cid, perfil_extra=perfil)
            st.rerun()
else:
    st.caption("Aún no hay ganancias ocasionales registradas.")

with st.form(key=f"form_ganancia_ocasional_{cid}"):
    st.markdown("**Agregar ganancia ocasional**")
    gc1, gc2, gc3 = st.columns(3)
    tipo_go = gc1.selectbox("Tipo", ["otro", "venta_vivienda", "herencia", "loteria_rifa_apuesta"],
                             help="'venta_vivienda' aplica solo si es su casa/apto de habitación (exención hasta 5.000 UVT, "
                                  "Art. 311-1 ET). 'herencia' aplica a la porción exenta de una herencia recibida en el año "
                                  "(Art. 307 ET). 'otro' es el tratamiento general (venta de activo >2 años, sin exención "
                                  "especial) - use esta opción por defecto si no está seguro.")
    valor_bruto_go = gc2.number_input("Valor de la venta / valor bruto", min_value=0.0, step=100000.0)
    costo_fiscal_go = gc3.number_input("Costo fiscal (precio de compra o valor de adjudicación)", min_value=0.0, step=100000.0)
    nota_go = st.text_input("Nota (ej. fecha de adquisición y de venta, para dejar trazabilidad)")
    if st.form_submit_button("➕ Agregar"):
        ganancias_prev.append({
            "tipo": tipo_go, "valor_bruto": valor_bruto_go, "costo_fiscal": costo_fiscal_go, "nota": nota_go,
        })
        perfil["ganancias_ocasionales"] = ganancias_prev
        db.upsert_contribuyente(cid, perfil_extra=perfil)
        st.success("Ganancia ocasional agregada.")
        st.rerun()
