# -*- coding: utf-8 -*-
import json

import streamlit as st

from core import db
from core.ui_common import init_app, sidebar_contribuyente, requiere_contribuyente
from core import patrimonio as pmod
from core import deducciones as dmod
from core.auditoria import ejecutar_auditoria

st.set_page_config(page_title="Auditoría - Renta AG2025", page_icon="🔍", layout="wide")
init_app()
sidebar_contribuyente()
cid = requiere_contribuyente()

st.title("🔍 Auditoría — Control de diferencias")

with db.get_conn() as conn:
    conciliacion = [dict(r) for r in conn.execute(
        "SELECT * FROM conciliacion WHERE contribuyente_id=?", (cid,)
    ).fetchall()]
    exogena_registros = [dict(r) for r in conn.execute(
        "SELECT * FROM exogena_registros WHERE contribuyente_id=?", (cid,)
    ).fetchall()]

contrib = db.obtener_contribuyente(cid)
perfil = json.loads(contrib.get("perfil_json") or "{}")
patr = pmod.calcular_patrimonio(cid)
beneficios = dmod.listar_beneficios(cid)

patrimonio_exogena = sum(
    r["valor"] or 0 for r in conciliacion
    if "patrimonio" in (r["cedula_sugerida"] or "").lower() and r["estado"] != "NO_INGRESO"
)
ingresos_exogena = sum(
    r["valor"] or 0 for r in conciliacion
    if r["cedula_sugerida"] not in ("Patrimonio - activo", "Patrimonio - pasivo", "Control - no es ingreso",
                                     "Control patrimonial", "Retenciones")
)
ingresos_confirmados = sum(r["valor"] or 0 for r in conciliacion if r["estado"] == "CONFIRMADO")
retenciones_exogena = sum(r["valor"] or 0 for r in conciliacion if r["cedula_sugerida"] == "Retenciones")
retenciones_confirmadas = float(perfil.get("retenciones_manual", 0))

contexto = {
    "conciliacion": conciliacion,
    "exogena_registros": exogena_registros,
    "patrimonio": patr,
    "patrimonio_informado_terceros": patrimonio_exogena,
    "beneficios": beneficios,
    "ingresos_totales_exogena": ingresos_exogena,
    "ingresos_totales_confirmados": ingresos_confirmados,
    "retenciones_exogena": retenciones_exogena,
    "retenciones_confirmadas": retenciones_confirmadas,
}

hallazgos = ejecutar_auditoria(contexto)
st.session_state["ultimos_hallazgos"] = hallazgos

for nivel in ["🔴 CRÍTICO", "🟠 REVISAR", "🟡 PENDIENTE", "🟢 OK"]:
    items = [h for h in hallazgos if h["nivel"] == nivel]
    if items:
        st.markdown(f"### {nivel}")
        for h in items:
            with st.container(border=True):
                st.markdown(f"**{h['titulo']}**")
                st.write(h["detalle"])
