# -*- coding: utf-8 -*-
"""Utilidades compartidas por todas las páginas de la app Streamlit."""
import streamlit as st

from core import db
from core.informe import construir_checklist_inicial


def init_app():
    db.init_db()
    if "contribuyente_id" not in st.session_state:
        st.session_state["contribuyente_id"] = None


def sidebar_contribuyente():
    """Selector de contribuyente activo + botón Nueva Declaración, visible en todas las páginas."""
    st.sidebar.markdown("### 👤 Declaración activa")
    contribuyentes = db.listar_contribuyentes()

    opciones = {"— Ninguna (crear nueva) —": None}
    for c in contribuyentes:
        etiqueta = f"{c['nombre'] or 'Sin nombre'} · {c['identificacion']} · AG{c['anio_gravable']}"
        opciones[etiqueta] = c["id"]

    actual = st.session_state.get("contribuyente_id")
    etiquetas = list(opciones.keys())
    idx_actual = 0
    for i, (label, cid) in enumerate(opciones.items()):
        if cid == actual:
            idx_actual = i
            break

    seleccion = st.sidebar.selectbox("Contribuyente / Año gravable", etiquetas, index=idx_actual)
    st.session_state["contribuyente_id"] = opciones[seleccion]

    if st.sidebar.button("➕ Nueva declaración", use_container_width=True):
        st.session_state["contribuyente_id"] = None
        st.session_state["modo_nueva_declaracion"] = True
        st.switch_page("pages/01_Contribuyente.py")

    if st.session_state.get("contribuyente_id"):
        with st.sidebar.expander("⚠️ Zona de riesgo"):
            if st.button("🗑️ Eliminar esta declaración y todos sus datos"):
                db.eliminar_contribuyente(st.session_state["contribuyente_id"])
                st.session_state["contribuyente_id"] = None
                st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.caption("AG 2025 · UVT $49.799 · Todo el procesamiento es local, sin envío a servicios externos.")


def requiere_contribuyente():
    if not st.session_state.get("contribuyente_id"):
        st.warning("Primero seleccione o cree una declaración en el menú **Contribuyente**.")
        st.stop()
    return st.session_state["contribuyente_id"]


def asegurar_checklist(cid: str):
    construir_checklist_inicial(cid)


def fmt_cop(valor) -> str:
    try:
        return f"${valor:,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"
