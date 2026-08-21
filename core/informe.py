# -*- coding: utf-8 -*-
"""Generación del informe ejecutivo final (texto + estructura para exportar)."""
from datetime import datetime


ITEMS_CHECKLIST_BASE = [
    ("Información personal completa (documento, nombre, residencia fiscal)", True),
    ("Residencia fiscal para AG2025 verificada", True),
    ("Patrimonio a 31/12/2025 registrado (activos)", True),
    ("Deudas a 31/12/2025 registradas", False),
    ("Ingresos conciliados (sin registros 'por conciliar' pendientes)", True),
    ("Costos procedentes soportados", False),
    ("Deducciones y rentas exentas con soporte documental", True),
    ("Retenciones en la fuente conciliadas con certificados", True),
    ("Ganancias ocasionales revisadas (si aplica)", False),
    ("Dependientes acreditados (si aplica deducción)", False),
    ("Soportes documentales archivados y disponibles", True),
    ("Conciliación con exógena sin diferencias críticas", True),
    ("Formulario 210 revisado casilla por casilla", True),
    ("Resultado final (saldo a pagar/favor) revisado y entendido", True),
]


def construir_informe(contribuyente: dict, patrimonio: dict, cedula_general: dict,
                       cedula_pensiones: dict, dividendos: dict, ganancias_ocasionales: dict,
                       liquidacion: dict, beneficios: list, hallazgos: list) -> str:
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    oportunidades = [b for b in beneficios if not b.get("soportado")]
    documentos_faltantes = sorted({b["documento_requerido"] for b in oportunidades if b.get("documento_requerido")})
    riesgos = [h for h in hallazgos if h["nivel"] in ("🔴 CRÍTICO", "🟠 REVISAR")]

    lineas = [
        "=" * 78,
        "INFORME EJECUTIVO - DECLARACIÓN DE RENTA PERSONA NATURAL",
        f"AÑO GRAVABLE 2025  |  Generado: {fecha}",
        "=" * 78,
        "",
        f"Contribuyente: {contribuyente.get('nombre', 'N/D')}",
        f"Identificación: {contribuyente.get('tipo_documento', '')} {contribuyente.get('identificacion', '')}",
        "",
        "-" * 78,
        "RESUMEN TRIBUTARIO",
        "-" * 78,
        f"Patrimonio bruto:                  ${patrimonio['patrimonio_bruto']:>18,.0f}",
        f"Deudas:                             ${patrimonio['deudas']:>18,.0f}",
        f"Patrimonio líquido:                 ${patrimonio['patrimonio_liquido']:>18,.0f}",
        "",
        f"Ingresos brutos cédula general:     ${cedula_general['ingresos_brutos']:>18,.0f}",
        f"Rentas exentas y deducciones aplic.: ${cedula_general['rentas_exentas_deducciones_aplicadas']:>18,.0f}",
        f"Renta líquida gravable consolidada:  ${liquidacion['renta_liquida_gravable_consolidada']:>18,.0f}",
        f"Impuesto neto de renta:              ${liquidacion['impuesto_neto_renta']:>18,.0f}",
        f"Impuesto ganancias ocasionales:      ${liquidacion['impuesto_ganancias_ocasionales']:>18,.0f}",
        f"Total impuesto a cargo:              ${liquidacion['total_impuesto_a_cargo']:>18,.0f}",
        f"Retenciones del año:                 ${liquidacion['retenciones_anio']:>18,.0f}",
        f"Saldo a favor año anterior (no dev.): ${liquidacion.get('saldo_favor_anio_anterior', 0):>18,.0f}",
        f"SALDO A PAGAR:                       ${liquidacion['saldo_a_pagar']:>18,.0f}" if liquidacion["saldo_a_pagar"] > 0 else
        f"SALDO A FAVOR:                       ${liquidacion['saldo_a_favor']:>18,.0f}",
        "",
        "-" * 78,
        "OPORTUNIDADES TRIBUTARIAS PENDIENTES DE SOPORTE",
        "-" * 78,
    ]
    if oportunidades:
        for b in oportunidades:
            lineas.append(f"  - {b['beneficio']}: valor potencial ${b['valor_potencial']:,.0f} "
                           f"(NO APLICADO - FALTA SOPORTE: {b['documento_requerido']})")
    else:
        lineas.append("  Ninguna pendiente. Todos los beneficios detectados están soportados o no aplican.")

    lineas += ["", "-" * 78, "DOCUMENTOS FALTANTES", "-" * 78]
    if documentos_faltantes:
        for d in documentos_faltantes:
            lineas.append(f"  - {d}")
    else:
        lineas.append("  No se identificaron documentos faltantes.")

    lineas += ["", "-" * 78, "RIESGOS / INCONSISTENCIAS DETECTADAS", "-" * 78]
    if riesgos:
        for h in riesgos:
            lineas.append(f"  {h['nivel']} {h['titulo']}: {h['detalle']}")
    else:
        lineas.append("  No se detectaron riesgos críticos ni puntos por revisar.")

    lineas += [
        "", "-" * 78, "RESULTADO Y EXPLICACIÓN", "-" * 78,
        liquidacion["formula"],
        cedula_general["formula"],
        "",
        "IMPORTANTE: Este informe es una herramienta de apoyo para preparar la declaración.",
        "La exógena tributaria consultada NO reemplaza la información de la realidad económica",
        "del contribuyente. Verifique cada cifra contra sus soportes antes de presentar el",
        "Formulario 210 en el portal de la DIAN.",
        "=" * 78,
    ]
    return "\n".join(lineas)


def construir_checklist_inicial(contribuyente_id: str):
    from core.db import get_conn
    with get_conn() as conn:
        existentes = conn.execute(
            "SELECT item FROM checklist WHERE contribuyente_id=?", (contribuyente_id,)
        ).fetchall()
        if existentes:
            return
        for item, critico in ITEMS_CHECKLIST_BASE:
            conn.execute(
                "INSERT INTO checklist (contribuyente_id, item, completo, critico) VALUES (?, ?, 0, ?)",
                (contribuyente_id, item, int(critico)),
            )


def listar_checklist(contribuyente_id: str):
    from core.db import get_conn
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM checklist WHERE contribuyente_id=? ORDER BY id", (contribuyente_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def actualizar_checklist_item(item_id: int, completo: bool):
    from core.db import get_conn
    with get_conn() as conn:
        conn.execute("UPDATE checklist SET completo=? WHERE id=?", (int(completo), item_id))


def lista_para_presentar(contribuyente_id: str, hallazgos: list) -> tuple:
    from core.auditoria import tiene_criticos
    items = listar_checklist(contribuyente_id)
    criticos_pendientes = [i for i in items if i["critico"] and not i["completo"]]
    if tiene_criticos(hallazgos):
        return False, "Existen hallazgos CRÍTICOS en la auditoría que deben resolverse primero."
    if criticos_pendientes:
        nombres = ", ".join(i["item"] for i in criticos_pendientes)
        return False, f"Faltan puntos críticos del checklist: {nombres}"
    return True, "La declaración está lista para presentar."
