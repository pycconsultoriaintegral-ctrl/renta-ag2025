# -*- coding: utf-8 -*-
import json

import streamlit as st

from core import db
from core.ui_common import init_app, sidebar_contribuyente, requiere_contribuyente, asegurar_checklist
from core import patrimonio as pmod
from core import deducciones as dmod
from core import liquidacion as liq
from core.auditoria import ejecutar_auditoria
from core.informe import (
    construir_informe, listar_checklist, actualizar_checklist_item, lista_para_presentar,
)

st.set_page_config(page_title="Informe final - Renta AG2025", page_icon="✅", layout="wide")
init_app()
sidebar_contribuyente()
cid = requiere_contribuyente()
asegurar_checklist(cid)

st.title("✅ Checklist final e informe ejecutivo")

st.markdown("### Checklist previo a la presentación")
items = listar_checklist(cid)
for it in items:
    marca = "🔴 CRÍTICO" if it["critico"] else "opcional"
    completo = st.checkbox(f"{it['item']} ({marca})", value=bool(it["completo"]), key=f"chk_{it['id']}")
    if completo != bool(it["completo"]):
        actualizar_checklist_item(it["id"], completo)

with db.get_conn() as conn:
    conciliacion = [dict(r) for r in conn.execute(
        "SELECT * FROM conciliacion WHERE contribuyente_id=?", (cid,)
    ).fetchall()]
    exogena_registros = [dict(r) for r in conn.execute(
        "SELECT * FROM exogena_registros WHERE contribuyente_id=?", (cid,)
    ).fetchall()]

contrib = db.obtener_contribuyente(cid)
perfil = json.loads(contrib.get("perfil_json") or "{}")
ing = perfil.get("ingresos_manual", {})
patr = pmod.calcular_patrimonio(cid)
beneficios = dmod.listar_beneficios(cid)
beneficios_soportados = dmod.total_soportado(cid)

if not ing:
    st.warning("Complete los módulos de Ingresos y Liquidación antes de generar el informe final.")
    st.stop()

cedula_general = liq.liquidar_cedula_general(ing, beneficios_soportados)
cedula_pensiones = liq.liquidar_cedula_pensiones(ing.get("pension_mensual_promedio", 0), int(ing.get("meses_pension", 12)))
dividendos = liq.liquidar_dividendos(ing.get("dividendos_gravados", 0), ing.get("dividendos_no_gravados", 0))
ganancias_ocasionales = liq.liquidar_ganancias_ocasionales(perfil.get("ganancias_ocasionales", []))
retenciones = float(perfil.get("retenciones_manual", 0))
liquidacion = liq.liquidar_declaracion(cedula_general, cedula_pensiones, dividendos, ganancias_ocasionales,
                                       retenciones, float(perfil.get("descuentos_tributarios", 0)),
                                       float(perfil.get("anticipo_renta_anterior", 0)))

patrimonio_exogena = sum(
    r["valor"] or 0 for r in conciliacion
    if "patrimonio" in (r["cedula_sugerida"] or "").lower() and r["estado"] != "NO_INGRESO"
)
contexto = {
    "conciliacion": conciliacion, "exogena_registros": exogena_registros, "patrimonio": patr,
    "patrimonio_informado_terceros": patrimonio_exogena, "beneficios": beneficios,
    "ingresos_totales_exogena": sum(r["valor"] or 0 for r in conciliacion),
    "ingresos_totales_confirmados": sum(r["valor"] or 0 for r in conciliacion if r["estado"] == "CONFIRMADO"),
    "retenciones_exogena": sum(r["valor"] or 0 for r in conciliacion if r["cedula_sugerida"] == "Retenciones"),
    "retenciones_confirmadas": retenciones,
}
hallazgos = ejecutar_auditoria(contexto)

st.markdown("---")
listo, mensaje = lista_para_presentar(cid, hallazgos)
if listo:
    st.success(f"🟢 {mensaje}")
else:
    st.error(f"🔴 {mensaje}")

st.markdown("### Informe ejecutivo")
informe_texto = construir_informe(contrib, patr, cedula_general, cedula_pensiones, dividendos,
                                   ganancias_ocasionales, liquidacion, beneficios, hallazgos)
st.text(informe_texto)

st.download_button(
    "⬇️ Descargar informe ejecutivo (.txt)",
    informe_texto.encode("utf-8"),
    file_name=f"informe_renta_ag2025_{cid}.txt",
    mime="text/plain",
)
