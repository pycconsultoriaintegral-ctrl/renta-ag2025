# -*- coding: utf-8 -*-
import json

import streamlit as st

from core import config, db
from core.ui_common import init_app, sidebar_contribuyente, asegurar_checklist

st.set_page_config(page_title="Contribuyente - Renta AG2025", page_icon="👤", layout="wide")
init_app()
sidebar_contribuyente()

st.title("👤 Perfil del contribuyente")
st.caption("Solo se solicita la información mínima necesaria. Puede volver aquí y actualizarla en cualquier momento.")

cid_actual = st.session_state.get("contribuyente_id")
datos_previos = db.obtener_contribuyente(cid_actual) if cid_actual else {}
perfil_previo = json.loads(datos_previos.get("perfil_json") or "{}") if datos_previos else {}

st.markdown("### 1. Identificación")
c1, c2 = st.columns(2)
tipo_doc = c1.selectbox("Tipo de documento", ["C.C.", "C.E.", "Pasaporte", "NIT"],
                         index=["C.C.", "C.E.", "Pasaporte", "NIT"].index(datos_previos.get("tipo_documento", "C.C."))
                         if datos_previos.get("tipo_documento") in ["C.C.", "C.E.", "Pasaporte", "NIT"] else 0)
identificacion = c2.text_input("Número de identificación", value=datos_previos.get("identificacion", ""))

nombre = st.text_input("Nombres y apellidos / Razón social", value=datos_previos.get("nombre", ""))

st.markdown("### 2. Residencia fiscal y situación personal")
c3, c4, c5 = st.columns(3)
residencia = c3.selectbox("¿Es residente fiscal en Colombia para AG2025?", ["Sí", "No"],
                           index=0 if datos_previos.get("residencia_fiscal", "Sí") == "Sí" else 1)
estado_civil = c4.selectbox("Estado civil", ["Soltero(a)", "Casado(a)/Unión marital"],
                             index=["Soltero(a)", "Casado(a)/Unión marital"].index(datos_previos.get("estado_civil", "Soltero(a)"))
                             if datos_previos.get("estado_civil") in ["Soltero(a)", "Casado(a)/Unión marital"] else 0)
edad = c5.number_input("Edad", min_value=0, max_value=120, value=int(datos_previos.get("edad") or 0))

actividad = st.text_input("Actividad económica principal (código CIIU si lo conoce)",
                           value=datos_previos.get("actividad_economica", ""))

num_dependientes = st.number_input(
    "Número de dependientes económicos (máx. 4 para efectos de la deducción, Art. 336 ET)",
    min_value=0, max_value=10, value=int(perfil_previo.get("num_dependientes", 0)),
)

if residencia == "No":
    st.error(
        "⚠️ Si usted NO es residente fiscal en Colombia para el AG2025, esta herramienta "
        "(diseñada para el Formulario 210 de residentes) no aplica. Las personas naturales "
        "no residentes declaran en el Formulario 110 y tributan solo sobre rentas de fuente "
        "nacional a tarifas distintas. Consulte con un asesor tributario."
    )

st.markdown("---")
if st.button("💾 Guardar perfil y continuar", type="primary"):
    if not identificacion or not nombre:
        st.error("Debe indicar al menos la identificación y el nombre.")
    else:
        cid = db.contribuyente_id(tipo_doc, identificacion, config.ANIO_GRAVABLE)
        perfil_extra = {**perfil_previo, "num_dependientes": num_dependientes}
        db.upsert_contribuyente(
            cid,
            anio_gravable=config.ANIO_GRAVABLE,
            tipo_documento=tipo_doc,
            identificacion=identificacion,
            nombre=nombre,
            residencia_fiscal=residencia,
            estado_civil=estado_civil,
            edad=edad,
            actividad_economica=actividad,
            perfil_extra=perfil_extra,
        )
        asegurar_checklist(cid)
        st.session_state["contribuyente_id"] = cid
        st.success(f"Perfil guardado. Declaración activa: {nombre} ({cid})")
        st.rerun()

st.markdown("---")
st.markdown("### Declaraciones existentes en este equipo")
contribuyentes = db.listar_contribuyentes()
if contribuyentes:
    for c in contribuyentes:
        st.write(f"- **{c['nombre']}** · {c['tipo_documento']} {c['identificacion']} · AG{c['anio_gravable']} "
                  f"· actualizado {c['actualizado_en']}")
else:
    st.caption("No hay declaraciones guardadas todavía.")
