# -*- coding: utf-8 -*-
"""Motor de control de diferencias / auditoría interna previa a la presentación."""
from core import config
from core.importer import detectar_duplicados


def ejecutar_auditoria(contexto: dict) -> list[dict]:
    """
    contexto: {
        'conciliacion': list[dict],   # registros de conciliación con estado
        'patrimonio': dict,           # resultado de calcular_patrimonio
        'patrimonio_informado_terceros': float,  # suma de activos según exógena
        'beneficios': list[dict],     # listado de deducciones/beneficios
        'ingresos_totales_exogena': float,
        'ingresos_totales_confirmados': float,
        'retenciones_exogena': float,
        'retenciones_confirmadas': float,
    }
    Retorna hallazgos clasificados 🔴 CRÍTICO / 🟠 REVISAR / 🟡 PENDIENTE / 🟢 OK
    """
    hallazgos = []

    def add(nivel, titulo, detalle):
        hallazgos.append({"nivel": nivel, "titulo": titulo, "detalle": detalle})

    conciliacion = contexto.get("conciliacion", [])

    # 1. Registros por conciliar
    pendientes = [r for r in conciliacion if r["estado"] in ("POR_CONCILIAR", "REQUIERE_SOPORTE")]
    if pendientes:
        add("🟠 REVISAR", f"{len(pendientes)} registro(s) de exógena sin conciliar",
            "Existen valores reportados por terceros que aún no han sido clasificados definitivamente "
            "por el usuario. Revise el módulo de Ingresos/Conciliación antes de presentar.")
    else:
        add("🟢 OK", "Conciliación de exógena completa",
            "Todos los registros de la exógena tienen un estado definido por el usuario.")

    # 2. Duplicados (se calculan sobre los registros crudos de la exógena)
    registros_exogena = contexto.get("exogena_registros", [])
    duplicados = detectar_duplicados(registros_exogena) if registros_exogena else []
    if duplicados:
        add("🔴 CRÍTICO", f"{len(duplicados)} posible(s) registro(s) duplicado(s) en la exógena",
            "Se detectaron filas con el mismo tercero, concepto y valor. Verifique que no estén "
            "duplicando el mismo ingreso/deducción en la declaración.")

    # 3. Beneficios sin soporte
    beneficios = contexto.get("beneficios", [])
    sin_soporte = [b for b in beneficios if not b.get("soportado")]
    if sin_soporte:
        add("🟡 PENDIENTE", f"{len(sin_soporte)} beneficio(s) tributario(s) detectado(s) sin soporte",
            "NO APLICAR - FALTA SOPORTE. Consiga los documentos requeridos antes de incluirlos "
            "en la declaración: " + "; ".join(b["beneficio"] for b in sin_soporte))

    # 4. Patrimonio: informado por terceros vs. declarado
    patrimonio = contexto.get("patrimonio", {})
    patrimonio_terceros = contexto.get("patrimonio_informado_terceros", 0) or 0
    patrimonio_usuario = patrimonio.get("patrimonio_bruto", 0) or 0
    if patrimonio_terceros and abs(patrimonio_usuario - patrimonio_terceros) > config.uvt_a_pesos(50):
        add("🟠 REVISAR", "Diferencia entre patrimonio informado por terceros y patrimonio registrado",
            f"Patrimonio según exógena: ${patrimonio_terceros:,.0f} vs. patrimonio registrado por el "
            f"usuario: ${patrimonio_usuario:,.0f}. Verifique que no falten activos por incluir.")

    # 5. Ingresos: exógena vs. confirmados
    ing_exogena = contexto.get("ingresos_totales_exogena", 0) or 0
    ing_confirmados = contexto.get("ingresos_totales_confirmados", 0) or 0
    if ing_exogena and ing_confirmados < ing_exogena * 0.9:
        add("🟠 REVISAR", "Ingresos confirmados muy por debajo de lo reportado en exógena",
            f"Exógena reporta ${ing_exogena:,.0f} en conceptos de ingreso, pero solo se han "
            f"confirmado ${ing_confirmados:,.0f}. Verifique que no haya ingresos omitidos.")

    # 6. Retenciones
    ret_exogena = contexto.get("retenciones_exogena", 0) or 0
    ret_confirmadas = contexto.get("retenciones_confirmadas", 0) or 0
    if ret_exogena and abs(ret_confirmadas - ret_exogena) > 1000:
        add("🟡 PENDIENTE", "Diferencia en retenciones en la fuente",
            f"Exógena reporta ${ret_exogena:,.0f} en retenciones, confirmadas ${ret_confirmadas:,.0f}. "
            "Concilie contra los certificados de retención.")

    if not any(h["nivel"] == "🔴 CRÍTICO" for h in hallazgos):
        add("🟢 OK", "Sin hallazgos críticos", "No se detectaron inconsistencias críticas en esta revisión.")

    return hallazgos


def tiene_criticos(hallazgos: list[dict]) -> bool:
    return any(h["nivel"] == "🔴 CRÍTICO" for h in hallazgos)
