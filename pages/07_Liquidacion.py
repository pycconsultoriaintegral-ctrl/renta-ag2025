# -*- coding: utf-8 -*-
import json

import streamlit as st

from core import db
from core.ui_common import init_app, sidebar_contribuyente, requiere_contribuyente, fmt_cop
from core import liquidacion as liq
from core import deducciones as dmod

st.set_page_config(page_title="Liquidación - Renta AG2025", page_icon="🧮", layout="wide")
init_app()
sidebar_contribuyente()
cid = requiere_contribuyente()

st.title("🧮 Motor de liquidación AG2025")
st.caption("Cálculo transparente: cada cifra muestra su fórmula y norma aplicada. No es una caja negra.")

contrib = db.obtener_contribuyente(cid)
perfil = json.loads(contrib.get("perfil_json") or "{}")
ing = perfil.get("ingresos_manual", {})

if not ing:
    st.warning("Aún no ha guardado los ingresos definitivos. Vaya al módulo **Ingresos**.")
    st.stop()

beneficios_soportados = dmod.total_soportado(cid)

st.markdown("### Retenciones y otros datos")
c1, c2, c3, c4 = st.columns(4)
retenciones = c1.number_input("Total retenciones en la fuente del año (confirmadas)", min_value=0.0, step=10000.0,
                               value=float(perfil.get("retenciones_manual", 0)))
descuentos = c2.number_input("Descuentos tributarios (ej. impuestos pagados en el exterior)", min_value=0.0, step=10000.0,
                              value=float(perfil.get("descuentos_tributarios", 0)))
anticipo = c3.number_input("Anticipo de renta liquidado en la declaración anterior", min_value=0.0, step=10000.0,
                            value=float(perfil.get("anticipo_renta_anterior", 0)))
saldo_favor_anterior = c4.number_input(
    "Saldo a favor del año anterior sin solicitud de devolución y/o compensación",
    min_value=0.0, step=10000.0,
    value=float(perfil.get("saldo_favor_anio_anterior", 0)),
    help="Casilla 131 del Formulario 210. Saldo a favor del año gravable anterior que no fue "
         "solicitado en devolución/compensación y que se imputa contra el impuesto de este año.",
)

if st.button("💾 Guardar y calcular", type="primary"):
    perfil["retenciones_manual"] = retenciones
    perfil["descuentos_tributarios"] = descuentos
    perfil["anticipo_renta_anterior"] = anticipo
    perfil["saldo_favor_anio_anterior"] = saldo_favor_anterior
    db.upsert_contribuyente(cid, perfil_extra=perfil)
    st.rerun()

st.markdown("---")

cedula_general = liq.liquidar_cedula_general(ing, beneficios_soportados)
cedula_pensiones = liq.liquidar_cedula_pensiones(ing.get("pension_mensual_promedio", 0), int(ing.get("meses_pension", 12)))
dividendos = liq.liquidar_dividendos(ing.get("dividendos_gravados", 0), ing.get("dividendos_no_gravados", 0))
ganancias_ocasionales_items = perfil.get("ganancias_ocasionales", [])
ganancias_ocasionales = liq.liquidar_ganancias_ocasionales(ganancias_ocasionales_items)
resultado = liq.liquidar_declaracion(cedula_general, cedula_pensiones, dividendos, ganancias_ocasionales,
                                      retenciones, descuentos, anticipo, saldo_favor_anterior)

st.session_state["ultimo_calculo"] = {
    "cedula_general": cedula_general, "cedula_pensiones": cedula_pensiones,
    "dividendos": dividendos, "ganancias_ocasionales": ganancias_ocasionales, "liquidacion": resultado,
}

st.markdown("### 1. Cédula general")
with st.expander("Ver detalle y fórmula", expanded=True):
    st.json(cedula_general)

st.markdown("### 2. Cédula de pensiones")
with st.expander("Ver detalle y fórmula"):
    st.json(cedula_pensiones)

st.markdown("### 3. Cédula de dividendos y participaciones")
with st.expander("Ver detalle y fórmula"):
    st.json(dividendos)

st.markdown("### 4. Ganancias ocasionales")
with st.expander("Ver detalle"):
    st.json(ganancias_ocasionales)
    st.caption("Para agregar ganancias ocasionales (venta de vivienda, herencias, loterías) use el módulo Formulario 210 → sección avanzada, o contacte soporte técnico para habilitar edición directa.")

st.markdown("### 5. Resultado consolidado")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Renta líquida gravable", fmt_cop(resultado["renta_liquida_gravable_consolidada"]))
c2.metric("Impuesto neto de renta", fmt_cop(resultado["impuesto_neto_renta"]))
c3.metric("Total impuesto a cargo", fmt_cop(resultado["total_impuesto_a_cargo"]))
if resultado["saldo_a_pagar"] > 0:
    c4.metric("Saldo a PAGAR", fmt_cop(resultado["saldo_a_pagar"]))
else:
    c4.metric("Saldo a FAVOR", fmt_cop(resultado["saldo_a_favor"]))

st.caption(resultado["formula"])
with st.expander("Ver todo el detalle del cálculo (trazabilidad completa)"):
    st.json(resultado)
