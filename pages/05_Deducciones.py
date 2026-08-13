# -*- coding: utf-8 -*-
import json

import streamlit as st

from core import db
from core.ui_common import init_app, sidebar_contribuyente, requiere_contribuyente, fmt_cop
from core import deducciones as dmod

st.set_page_config(page_title="Deducciones - Renta AG2025", page_icon="🎯", layout="wide")
init_app()
sidebar_contribuyente()
cid = requiere_contribuyente()

st.title("🎯 Deducciones y beneficios tributarios")
st.caption("El motor calcula el VALOR POTENCIAL según los límites legales AG2025. Nada se aplica sin que usted confirme el soporte documental.")

contrib = db.obtener_contribuyente(cid)
perfil = json.loads(contrib.get("perfil_json") or "{}")
ing_manual = perfil.get("ingresos_manual", {})
ded_prev = perfil.get("deducciones_perfil", {})

def _persistir_deducciones_perfil(valores: dict):
    """Guarda de inmediato los datos de esta página en el perfil, para que no
    se pierdan al recargar o al interactuar con otro botón de la página
    (ej. al guardar un beneficio individual más abajo)."""
    perfil_actual = json.loads(db.obtener_contribuyente(cid).get("perfil_json") or "{}")
    perfil_actual["deducciones_perfil"] = valores
    db.upsert_contribuyente(cid, perfil_extra=perfil_actual)


# Las claves explícitas (ligadas al contribuyente) evitan que Streamlit pierda
# el valor escrito por el usuario al recargar la página entre interacciones.
st.markdown("### Datos para calcular beneficios")
c1, c2 = st.columns(2)
with c1:
    intereses_vivienda = st.number_input("Intereses pagados por crédito de vivienda en 2025", min_value=0.0, step=50000.0,
                                          value=float(ded_prev.get("intereses_vivienda", 0)), key=f"ded_intereses_{cid}")
    medicina_prepagada = st.number_input("Pagos anuales de medicina prepagada/seguro de salud", min_value=0.0, step=50000.0,
                                          value=float(ded_prev.get("medicina_prepagada", 0)), key=f"ded_medicina_{cid}")
    gmf_pagado = st.number_input("GMF (4x1000) pagado en el año (según certificado bancario)", min_value=0.0, step=10000.0,
                                  value=float(ded_prev.get("gmf_pagado", 0)), key=f"ded_gmf_{cid}")
with c2:
    aportes_afc = st.number_input("Aportes voluntarios a pensión y/o cuentas AFC", min_value=0.0, step=50000.0,
                                   value=float(ded_prev.get("aportes_afc_pension_voluntario", 0)), key=f"ded_afc_{cid}")
    compras_fe = st.number_input("Compras de bienes/servicios soportadas en factura electrónica", min_value=0.0, step=50000.0,
                                  value=float(ded_prev.get("compras_factura_electronica", 0)), key=f"ded_facturae_{cid}")

perfil_calc = {
    "ingresos_laborales": ing_manual.get("trabajo_bruto", 0),
    "num_dependientes": perfil.get("num_dependientes", 0),
    "intereses_vivienda": intereses_vivienda,
    "medicina_prepagada": medicina_prepagada,
    "aportes_afc_pension_voluntario": aportes_afc,
    "gmf_pagado": gmf_pagado,
    "compras_factura_electronica": compras_fe,
    "ingresos_totales_declarados": sum([
        ing_manual.get("trabajo_bruto", 0), ing_manual.get("capital_bruto", 0), ing_manual.get("no_laboral_bruto", 0)
    ]),
}
valores_a_guardar = {k: v for k, v in perfil_calc.items() if k not in ("ingresos_laborales", "num_dependientes")}

if st.button("💾 Guardar datos y calcular beneficios", type="primary"):
    _persistir_deducciones_perfil(valores_a_guardar)
    catalogo = dmod.calcular_catalogo_beneficios(perfil_calc)
    st.session_state["catalogo_beneficios"] = catalogo
    st.success("Datos guardados.")
    st.rerun()

catalogo = st.session_state.get("catalogo_beneficios") or dmod.calcular_catalogo_beneficios(perfil_calc)

st.markdown("---")
st.markdown("### Beneficios detectados")
if not catalogo:
    st.info("Aún no se detectan beneficios. Complete los datos de ingresos (módulo Ingresos) y de esta página.")
else:
    for b in catalogo:
        with st.container(border=True):
            cc1, cc2 = st.columns([3, 2])
            with cc1:
                st.markdown(f"**{b['beneficio']}**")
                st.caption(f"Límite: {b['limite_aplicable']}")
                st.caption(f"Norma: {b['norma']}")
                st.caption(f"Documento requerido: {b['documento_requerido']}")
            with cc2:
                st.metric("Valor potencial", fmt_cop(b["valor_potencial"]))
                soportado = st.checkbox("✅ Cuento con el soporte documental", key=f"sop_{b['beneficio']}")
                valor_final = b["valor_potencial"] if soportado else 0
                if not soportado:
                    st.error("NO APLICAR — FALTA SOPORTE")
                if st.button("Guardar", key=f"guardar_{b['beneficio']}"):
                    dmod.guardar_beneficio(cid, b, soportado, valor_final)
                    _persistir_deducciones_perfil(valores_a_guardar)
                    st.success("Guardado")
                    st.rerun()

st.markdown("---")
st.markdown("### Beneficios guardados para esta declaración")
guardados = dmod.listar_beneficios(cid)
if guardados:
    total_utilizado = dmod.total_soportado(cid)
    for g in guardados:
        estado = "✅ Soportado" if g["soportado"] else "❌ Sin soporte (no aplicado)"
        st.write(f"- **{g['beneficio']}**: {fmt_cop(g['valor_potencial'])} potencial · {estado} · "
                 f"usado: {fmt_cop(g['valor_utilizado'])}")
    st.metric("Total de beneficios soportados y aplicables", fmt_cop(total_utilizado))
else:
    st.caption("Aún no ha guardado beneficios.")
