# -*- coding: utf-8 -*-
"""
GENERADOR DE RENTA PERSONA NATURAL - AG 2025 (Colombia)
Punto de entrada de la aplicación Streamlit. Ejecutar con:
    streamlit run app.py
"""
import streamlit as st

from core import config, db
from core.ui_common import init_app, sidebar_contribuyente, fmt_cop
from core.conciliacion import ESTADOS_LABELS
from core import patrimonio as patrimonio_mod
from core import deducciones as ded_mod
from core import liquidacion as liq
from core import auditoria as aud_mod

st.set_page_config(page_title="Renta AG2025 - Inicio", page_icon="🧾", layout="wide")
init_app()
sidebar_contribuyente()

st.title("🧾 Generador de Renta Persona Natural — AG 2025")
st.caption(f"Formulario 210 · {config.FORMULARIO_210_RESOLUCION} · UVT 2025 = {fmt_cop(config.UVT_2025)}")

cid = st.session_state.get("contribuyente_id")

if not cid:
    st.info(
        "👋 Bienvenido. Esta herramienta prepara su declaración de renta de persona natural "
        "para el **Año Gravable 2025**, conciliando la información exógena de la DIAN con su "
        "realidad económica y buscando la **menor carga tributaria legalmente procedente**.\n\n"
        "**Para comenzar:** vaya al menú **Contribuyente** en la barra lateral y cree su perfil, "
        "luego cargue su archivo de exógena en el menú **Exógena**."
    )
    st.markdown("### Menú de la aplicación")
    st.markdown(
        "1. **Contribuyente** — datos del declarante\n"
        "2. **Exógena** — importar el Excel de la DIAN\n"
        "3. **Ingresos** — conciliar ingresos reportados por terceros\n"
        "4. **Patrimonio** — activos y pasivos a 31/12/2025\n"
        "5. **Deducciones** — beneficios tributarios detectados\n"
        "6. **Optimización** — comparación de escenarios\n"
        "7. **Liquidación** — cálculo completo del impuesto\n"
        "8. **Formulario 210** — casilla por casilla\n"
        "9. **Auditoría** — control de diferencias\n"
        "10. **Informe final** — resumen ejecutivo y exportación"
    )
    st.stop()

contrib = db.obtener_contribuyente(cid)
st.subheader(f"Declaración de: {contrib.get('nombre') or 'Sin nombre'}")

# --- Estado del proceso ---
with db.get_conn() as conn:
    n_exogena = conn.execute(
        "SELECT COUNT(*) c FROM exogena_registros WHERE contribuyente_id=?", (cid,)
    ).fetchone()["c"]
    conciliacion_rows = [
        dict(r) for r in conn.execute(
            "SELECT * FROM conciliacion WHERE contribuyente_id=?", (cid,)
        ).fetchall()
    ]

pendientes = [r for r in conciliacion_rows if r["estado"] in ("POR_CONCILIAR", "REQUIERE_SOPORTE")]
patr = patrimonio_mod.calcular_patrimonio(cid)
beneficios = ded_mod.listar_beneficios(cid)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Año gravable", config.ANIO_GRAVABLE)
col2.metric("Registros de exógena", n_exogena)
col3.metric("Pendientes por conciliar", len(pendientes))
col4.metric("Beneficios detectados", len(beneficios))

col5, col6, col7 = st.columns(3)
col5.metric("Patrimonio líquido", fmt_cop(patr["patrimonio_liquido"]))
col6.metric("Patrimonio bruto", fmt_cop(patr["patrimonio_bruto"]))
col7.metric("Deudas", fmt_cop(patr["deudas"]))

st.markdown("---")

if n_exogena == 0:
    st.warning("📂 Aún no ha cargado su archivo de exógena. Vaya al menú **Exógena**.")
elif pendientes:
    st.warning(f"🟡 Tiene **{len(pendientes)}** registro(s) de exógena pendientes de conciliar. Vaya al menú **Ingresos**.")
else:
    st.success("✅ Toda la información de exógena ha sido conciliada.")

st.markdown("### 📋 Documentos pendientes (beneficios sin soporte)")
sin_soporte = [b for b in beneficios if not b["soportado"]]
if sin_soporte:
    for b in sin_soporte:
        st.write(f"- **{b['beneficio']}**: {fmt_cop(b['valor_potencial'])} — falta: {b['documento_requerido']}")
else:
    st.caption("No hay beneficios pendientes de soporte, o aún no se ha ejecutado el módulo de Deducciones.")

st.caption(
    "Recuerde: la información exógena NO es la declaración. Cada valor debe conciliarse con su "
    "realidad económica antes de presentarse ante la DIAN."
)
