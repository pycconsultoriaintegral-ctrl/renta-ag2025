# -*- coding: utf-8 -*-
"""
Auto-diligenciado de Patrimonio e Ingresos a partir de la conciliación de
exógena ya realizada por el usuario.

IMPORTANTE: esto NO reemplaza el criterio del usuario. Solo traslada a
Patrimonio/Ingresos los registros que la conciliación ya dejó en un estado
claro (CONFIRMADO para retenciones, o con categoría de patrimonio inequívoca
según el código de casilla R29/R30 que la propia DIAN sugiere). Los ingresos
ambiguos (venta de bienes, honorarios, etc.) NUNCA se autocompletan solos:
requieren revisión manual en el módulo de Ingresos porque su tratamiento
tributario depende de hechos que la exógena no reporta (tiempo de tenencia,
habitualidad, existencia de costos, etc.).
"""
import unicodedata

from core import db, patrimonio as pmod


def _sin_tildes(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt or "")
    return "".join(c for c in txt if not unicodedata.combining(c)).lower()


def _categoria_patrimonio(concepto: str) -> tuple:
    """Devuelve (tipo, categoria) a partir del texto del concepto.
    Solo reconoce conceptos de SALDO/PRINCIPAL (patrimonio a 31/12), nunca
    conceptos de FLUJO durante el año (rendimientos pagados, retenciones,
    consumos), que son ingreso o retención, no patrimonio."""
    t = _sin_tildes(concepto)
    # Excluir explícitamente flujos del año que NO son saldo patrimonial,
    # aunque contengan palabras como "cdt" o "cuenta".
    if "rendimiento" in t or "retencion" in t or "consumo" in t or "movimiento" in t:
        return None, None
    if "cuenta de ahorro" in t or "cuenta corriente" in t or "cuentas bancarias" in t or "saldo cuentas" in t:
        return "ACTIVO", "Cuentas bancarias (ahorro/corriente)"
    if "cdt" in t or "certificado de deposito" in t or "inversion efectuada" in t:
        return "ACTIVO", "CDT y otras inversiones de renta fija"
    if "vehiculo" in t:
        return "ACTIVO", "Vehículos"
    if "cuentas por pagar" in t or "obligacion financiera" in t or "prestamo" in t:
        return "PASIVO", "Otras deudas"
    if "cesantia" in t:
        return "ACTIVO", "Otros activos"
    return None, None


def autocompletar_patrimonio(cid: str) -> dict:
    """Inserta en Patrimonio los registros de conciliación con categoría
    inequívoca (cuentas, CDT, vehículos, cuentas por pagar) que aún no se
    hayan trasladado antes (evita duplicados vía 'origen=EXOGENA' + concepto)."""
    # No se filtra por cédula_sugerida: se evalúa el texto del concepto de TODOS
    # los registros, porque conceptos de patrimonio inequívocos (cuentas, CDT,
    # vehículos, deudas) a veces quedan clasificados bajo cédulas de control
    # genéricas ("Control patrimonial") en vez de "Patrimonio*". La función
    # _categoria_patrimonio ya es lo bastante estricta como para no traer
    # conceptos ambiguos (solo reconoce palabras clave inequívocas).
    with db.get_conn() as conn:
        registros = [dict(r) for r in conn.execute(
            "SELECT * FROM conciliacion WHERE contribuyente_id=?", (cid,)
        ).fetchall()]
        ya_cargados = {
            (r["categoria"], r["descripcion"])
            for r in conn.execute(
                "SELECT categoria, descripcion FROM patrimonio WHERE contribuyente_id=? AND origen='EXOGENA'",
                (cid,),
            ).fetchall()
        }

    agregados = []
    omitidos_sin_categoria = []
    for r in registros:
        tipo, categoria = _categoria_patrimonio(r["concepto"] or "")
        if not tipo:
            omitidos_sin_categoria.append(r)
            continue
        descripcion = f"{r['tercero'] or 'Tercero no identificado'} — {r['concepto']} (exógena, auto)"
        if (categoria, descripcion) in ya_cargados:
            continue
        pmod.guardar_item(cid, tipo, categoria, descripcion, r["valor"] or 0, origen="EXOGENA")
        agregados.append({"tipo": tipo, "categoria": categoria, "descripcion": descripcion, "valor": r["valor"]})

    return {"agregados": agregados, "omitidos_sin_categoria": omitidos_sin_categoria}


def autocompletar_ingresos(cid: str) -> dict:
    """
    Calcula sugerencias de:
      - retenciones_manual: suma de registros CONFIRMADOS de cédula 'Retenciones'
      - capital_bruto: suma de registros de 'Rentas de capital' en estado CONFIRMADO
    NO toca trabajo/no laboral (requieren juicio del usuario: habitualidad,
    tiempo de tenencia, existencia de costos, etc.) ni sobrescribe valores que
    el usuario ya haya guardado manualmente si son distintos de cero, salvo que
    el usuario lo pida explícitamente.
    """
    with db.get_conn() as conn:
        registros = [dict(r) for r in conn.execute(
            "SELECT * FROM conciliacion WHERE contribuyente_id=?", (cid,)
        ).fetchall()]

    retenciones = sum(
        r["valor"] or 0 for r in registros
        if r["estado"] == "CONFIRMADO" and (r["cedula_sugerida"] or "") == "Retenciones"
    )
    capital_bruto = sum(
        r["valor"] or 0 for r in registros
        if r["estado"] == "CONFIRMADO" and "capital" in _sin_tildes(r["cedula_sugerida"] or "")
    )
    pendientes_revision = [
        r for r in registros
        if r["estado"] in ("POR_CONCILIAR", "REQUIERE_SOPORTE")
        and "patrimonio" not in _sin_tildes(r["cedula_sugerida"] or "")
        and "indicador" not in _sin_tildes(r["cedula_sugerida"] or "")
        and "control" not in _sin_tildes(r["cedula_sugerida"] or "")
    ]

    return {
        "retenciones_sugeridas": retenciones,
        "capital_bruto_sugerido": capital_bruto,
        "pendientes_revision_manual": pendientes_revision,
    }
