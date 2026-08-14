# -*- coding: utf-8 -*-
import streamlit as st

from core.ui_common import init_app, sidebar_contribuyente, requiere_contribuyente, fmt_cop
from core import patrimonio as pmod
from core import autollenado

st.set_page_config(page_title="Patrimonio - Renta AG2025", page_icon="🏠", layout="wide")
init_app()
sidebar_contribuyente()
cid = requiere_contribuyente()

st.title("🏠 Patrimonio a 31 de diciembre de 2025")

autocompletar_click = st.button(
    "🔄 Autocompletar desde exógena (cuentas, CDT, vehículos, deudas)",
    help="Trae automáticamente los registros de la exógena que la DIAN clasificó sin ambigüedad "
         "como patrimonio (cuentas bancarias, CDT, vehículos, cuentas por pagar). No duplica lo "
         "que ya haya sido agregado antes con este mismo botón.",
)
if autocompletar_click:
    resultado = autollenado.autocompletar_patrimonio(cid)
    if resultado["agregados"]:
        st.success(f"Se agregaron {len(resultado['agregados'])} ítem(s) de patrimonio desde la exógena. "
                    "Revíselos abajo y ajuste lo que corresponda (ej. vehículos: use el costo fiscal, no el avalúo).")
    else:
        st.info("No hay ítems nuevos de la exógena para agregar (ya se agregaron antes, o no hay registros de "
                "patrimonio con categoría clara todavía — revise el módulo Ingresos).")
    if resultado["omitidos_sin_categoria"]:
        st.caption(f"{len(resultado['omitidos_sin_categoria'])} registro(s) de patrimonio de la exógena no se "
                   "pudieron clasificar automáticamente en una categoría (ej. saldos genéricos sin detalle claro) "
                   "y deben agregarse manualmente si corresponde.")
    st.rerun()

tab_activos, tab_pasivos = st.tabs(["Activos", "Deudas"])

with tab_activos:
    st.markdown("### Agregar activo")
    c1, c2, c3 = st.columns([2, 3, 2])
    categoria = c1.selectbox("Categoría", pmod.CATEGORIAS_ACTIVO, key="cat_activo")
    descripcion = c2.text_input("Descripción", key="desc_activo")
    valor = c3.number_input("Valor patrimonial", min_value=0.0, step=100000.0, key="valor_activo")
    if st.button("➕ Agregar activo"):
        pmod.guardar_item(cid, "ACTIVO", categoria, descripcion, valor)
        st.rerun()

    activos = pmod.listar_items(cid, "ACTIVO")
    if activos:
        for a in activos:
            cc1, cc2, cc3, cc4 = st.columns([2, 3, 2, 1])
            cc1.write(a["categoria"])
            cc2.write(a["descripcion"] or "—")
            cc3.write(fmt_cop(a["valor"]))
            if cc4.button("🗑️", key=f"del_a_{a['id']}"):
                pmod.eliminar_item(a["id"])
                st.rerun()
    else:
        st.caption("Aún no hay activos registrados.")

with tab_pasivos:
    st.markdown("### Agregar deuda")
    c1, c2, c3 = st.columns([2, 3, 2])
    categoria_p = c1.selectbox("Categoría", pmod.CATEGORIAS_PASIVO, key="cat_pasivo")
    descripcion_p = c2.text_input("Descripción", key="desc_pasivo")
    valor_p = c3.number_input("Saldo a 31/12/2025", min_value=0.0, step=100000.0, key="valor_pasivo")
    if st.button("➕ Agregar deuda"):
        pmod.guardar_item(cid, "PASIVO", categoria_p, descripcion_p, valor_p)
        st.rerun()

    pasivos = pmod.listar_items(cid, "PASIVO")
    if pasivos:
        for p in pasivos:
            cc1, cc2, cc3, cc4 = st.columns([2, 3, 2, 1])
            cc1.write(p["categoria"])
            cc2.write(p["descripcion"] or "—")
            cc3.write(fmt_cop(p["valor"]))
            if cc4.button("🗑️", key=f"del_p_{p['id']}"):
                pmod.eliminar_item(p["id"])
                st.rerun()
    else:
        st.caption("Aún no hay deudas registradas.")

st.markdown("---")
resultado = pmod.calcular_patrimonio(cid)
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio bruto", fmt_cop(resultado["patrimonio_bruto"]))
c2.metric("Deudas", fmt_cop(resultado["deudas"]))
c3.metric("Patrimonio líquido", fmt_cop(resultado["patrimonio_liquido"]))
st.caption(f"{resultado['formula']} · {resultado['norma']}")
