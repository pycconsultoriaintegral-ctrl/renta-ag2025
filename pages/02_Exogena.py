# -*- coding: utf-8 -*-
from pathlib import Path

import pandas as pd
import streamlit as st

from core import db
from core.ui_common import init_app, sidebar_contribuyente, requiere_contribuyente, fmt_cop
from core.importer import importar_exogena, detectar_duplicados
from core.conciliacion import clasificar_registro, ESTADOS_LABELS

st.set_page_config(page_title="Exógena - Renta AG2025", page_icon="📂", layout="wide")
init_app()
sidebar_contribuyente()
cid = requiere_contribuyente()

st.title("📂 Importar información exógena")
st.caption(
    "Cargue el archivo .xlsx de 'Consulta de información reportada por terceros' descargado del "
    "portal de la DIAN. El archivo original nunca se modifica."
)

archivo = st.file_uploader("Archivo de exógena (.xlsx)", type=["xlsx"])

if archivo is not None:
    uploads_dir = Path(__file__).resolve().parent.parent / "data" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    ruta_local = uploads_dir / f"{cid}_{archivo.name}"
    with open(ruta_local, "wb") as f:
        f.write(archivo.getbuffer())

    resultado = importar_exogena(str(ruta_local))

    st.markdown("### Datos detectados en el encabezado del archivo")
    c1, c2, c3 = st.columns(3)
    c1.write(f"**Año de consulta:** {resultado.anio_consulta}")
    c2.write(f"**Identificación consultante:** {resultado.tipo_documento} {resultado.identificacion}")
    c3.write(f"**Nombre:** {resultado.nombre}")

    if resultado.anio_consulta and resultado.anio_consulta != 2025:
        st.error(
            f"⚠️ El archivo corresponde al año {resultado.anio_consulta}, NO al año gravable 2025. "
            "Esta herramienta está diseñada exclusivamente para AG2025. Cargue el archivo correcto."
        )

    for adv in resultado.advertencias:
        st.warning(adv)

    if resultado.registros:
        st.markdown(f"### Registros encontrados: {len(resultado.registros)}")

        duplicados = detectar_duplicados(resultado.registros)
        if duplicados:
            st.error(f"🔴 Se detectaron {len(duplicados)} registro(s) con posible duplicidad (mismo tercero, concepto y valor).")

        if st.button("💾 Guardar esta importación y clasificar automáticamente", type="primary"):
            with db.get_conn() as conn:
                conn.execute("DELETE FROM exogena_registros WHERE contribuyente_id=? AND archivo_origen=?",
                             (cid, archivo.name))
                for r in resultado.registros:
                    conn.execute(
                        "INSERT INTO exogena_registros (contribuyente_id, archivo_origen, nit_reportante, "
                        "nombre_reportante, concepto, valor, uso_sugerido, info_adicional, fila_excel, hash_fila) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (cid, archivo.name, r["nit_reportante"], r["nombre_reportante"], r["detalle"],
                         r["valor"], r["uso_sugerido"], r["info_adicional"], r["fila_excel"], r["hash_fila"]),
                    )
                exogena_ids = conn.execute(
                    "SELECT id, nombre_reportante, concepto, valor, uso_sugerido FROM exogena_registros "
                    "WHERE contribuyente_id=? AND archivo_origen=?", (cid, archivo.name)
                ).fetchall()
                for row in exogena_ids:
                    ya_existe = conn.execute(
                        "SELECT id FROM conciliacion WHERE contribuyente_id=? AND exogena_id=?",
                        (cid, row["id"]),
                    ).fetchone()
                    if ya_existe:
                        continue
                    clasif = clasificar_registro(row["concepto"] or "", row["uso_sugerido"] or "")
                    conn.execute(
                        "INSERT INTO conciliacion (contribuyente_id, exogena_id, tercero, concepto, valor, "
                        "cedula_sugerida, tratamiento_sugerido, estado, soporte_requerido) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (cid, row["id"], row["nombre_reportante"], row["concepto"], row["valor"],
                         clasif["cedula_sugerida"], clasif["tratamiento_sugerido"], clasif["estado"],
                         clasif["soporte_requerido"]),
                    )
            st.success("Importación guardada y clasificada automáticamente. Vaya al menú **Ingresos** para conciliar.")

        df = pd.DataFrame(resultado.registros)
        st.markdown("### Vista previa")
        df_preview = df[["nombre_reportante", "nit_reportante", "detalle", "valor", "uso_sugerido"]].copy()
        df_preview["valor"] = df_preview["valor"].apply(fmt_cop)
        st.dataframe(
            df_preview.rename(columns={"nombre_reportante": "Tercero", "nit_reportante": "NIT tercero",
                              "detalle": "Concepto", "valor": "Valor", "uso_sugerido": "Uso sugerido DIAN"}),
            use_container_width=True,
        )

        st.markdown("### Agrupado por tercero")
        agg_tercero = df.groupby("nombre_reportante", dropna=False)["valor"].sum().reset_index()
        agg_tercero.columns = ["Tercero", "Total reportado"]
        agg_tercero["Total reportado"] = agg_tercero["Total reportado"].apply(fmt_cop)
        st.dataframe(agg_tercero, use_container_width=True)

        st.markdown("### Agrupado por concepto")
        agg_concepto = df.groupby("detalle", dropna=False)["valor"].sum().reset_index()
        agg_concepto.columns = ["Concepto", "Total reportado"]
        agg_concepto["Total reportado"] = agg_concepto["Total reportado"].apply(fmt_cop)
        st.dataframe(agg_concepto, use_container_width=True)

st.markdown("---")
st.markdown("### Registros ya guardados para esta declaración")
with db.get_conn() as conn:
    guardados = [dict(r) for r in conn.execute(
        "SELECT * FROM exogena_registros WHERE contribuyente_id=?", (cid,)
    ).fetchall()]
if guardados:
    dfg = pd.DataFrame(guardados)[["nombre_reportante", "concepto", "valor", "archivo_origen"]].copy()
    dfg["valor"] = dfg["valor"].apply(fmt_cop)
    dfg = dfg.rename(columns={"nombre_reportante": "Tercero", "concepto": "Concepto", "valor": "Valor",
                               "archivo_origen": "Archivo"})
    st.dataframe(dfg, use_container_width=True)
    st.write(f"**Total registros guardados:** {len(guardados)} · **Suma total:** {fmt_cop(sum(g['valor'] or 0 for g in guardados))}")
else:
    st.caption("Aún no hay registros guardados.")
