# -*- coding: utf-8 -*-
"""
Mapeo de resultados al Formulario 210 AG2025 (Resolución DIAN 000044 de 2024,
modificada por Resolución 000120 de 2024 - misma estructura vigente para AG2025).

AVISO DE TRAZABILIDAD: los números de casilla aquí mostrados corresponden a la
estructura pública documentada del Formulario 210 vigente. Antes de transcribir
estos valores en el formulario real de la DIAN (MUISCA), el usuario DEBE
verificar cada número de casilla contra el PDF oficial del formulario, ya que
la numeración exacta de casillas intermedias puede variar levemente y esta
herramienta no reemplaza la verificación en la fuente oficial.
"""


def construir_formulario210(patrimonio: dict, cedula_general: dict, cedula_pensiones: dict,
                             dividendos: dict, ganancias_ocasionales: dict, liquidacion: dict,
                             ingresos_detalle: dict) -> list[dict]:
    casillas = []

    def add(numero, nombre, valor, origen, explicacion, soporte, estado="OK"):
        casillas.append({
            "casilla": numero, "nombre": nombre, "valor": round(valor or 0),
            "origen": origen, "explicacion": explicacion, "soporte": soporte, "estado": estado,
        })

    add("29", "Total patrimonio bruto", patrimonio["patrimonio_bruto"],
        "Módulo Patrimonio", "Suma de todos los activos a 31/12/2025", "Certificados bancarios, avalúos, tarjetas de propiedad")
    add("30", "Deudas", patrimonio["deudas"], "Módulo Patrimonio",
        "Suma de obligaciones financieras y otras deudas a 31/12/2025", "Certificados de saldo de obligaciones")
    add("31", "Total patrimonio líquido", patrimonio["patrimonio_liquido"], "Calculado",
        "Patrimonio bruto - Deudas", "N/A (cálculo)")

    add("32", "Ingresos brutos rentas de trabajo", ingresos_detalle.get("trabajo_bruto", 0),
        "Módulo Ingresos", "Salarios, honorarios y compensaciones por trabajo", "Certificado de ingresos y retenciones")
    add("36", "Rentas exentas de trabajo (25% + otras)", cedula_general["rentas_exentas_deducciones_aplicadas"],
        "Módulo Deducciones", "Renta exenta 25% laboral y demás exentas imputables, ya limitadas al 40%/1.340 UVT",
        "Certificados de ingresos, soportes de deducciones")
    add("58", "Ingresos brutos rentas de capital", ingresos_detalle.get("capital_bruto", 0),
        "Módulo Ingresos", "Intereses, arrendamientos, rendimientos financieros", "Certificados de rendimientos/arrendamientos")
    add("74", "Ingresos brutos rentas no laborales", ingresos_detalle.get("no_laboral_bruto", 0),
        "Módulo Ingresos", "Honorarios sin vinculación laboral, otros ingresos no laborales", "Certificados de retención, contratos")
    add("91", "Renta líquida de la cédula general", cedula_general["renta_liquida_antes_de_exentas"],
        "Calculado", "Ingresos netos - Costos y gastos procedentes", "N/A (cálculo)")
    add("93", "Renta líquida ordinaria del ejercicio (cédula general)",
        cedula_general["renta_liquida_gravable_cedula_general"], "Calculado",
        "Renta líquida cédula general - rentas exentas y deducciones (límite 40%/1.340 UVT)", "N/A (cálculo)")

    add("P-1", "Ingreso bruto pensiones", cedula_pensiones["ingreso_bruto_anual"],
        "Módulo Ingresos", "Pagos por pensión de jubilación/vejez/invalidez", "Certificado de la entidad pagadora de pensión")
    add("P-2", "Renta líquida gravable pensiones", cedula_pensiones["renta_liquida_gravable_pensiones"],
        "Calculado", "Ingreso pensión - renta exenta (1.000 UVT/mes)", "N/A (cálculo)")

    add("111", "Renta líquida gravable consolidada (general + pensiones)",
        liquidacion["renta_liquida_gravable_consolidada"], "Calculado",
        "Suma de la renta líquida gravable de la cédula general y de pensiones", "N/A (cálculo)")

    add("116-121", "Impuesto sobre renta líquida gravable (tabla Art. 241 ET)",
        liquidacion["detalle_impuesto_cedula_general_pensiones"]["impuesto_pesos"], "Calculado",
        liquidacion["detalle_impuesto_cedula_general_pensiones"]["formula"], "N/A (cálculo)")

    add("DIV", "Impuesto cédula de dividendos y participaciones", dividendos["impuesto_total_dividendos"],
        "Módulo Ingresos + Calculado", dividendos["formula"], "Certificado de dividendos y participaciones")

    add("126", "Impuesto neto de renta", liquidacion["impuesto_neto_renta"], "Calculado",
        "Impuesto bruto (cédula general/pensiones + dividendos) - descuentos tributarios", "N/A (cálculo)")

    add("GO", "Impuesto de ganancias ocasionales", ganancias_ocasionales["total_impuesto_ganancias_ocasionales"],
        "Módulo Ingresos + Calculado", "Ver detalle en módulo de Ganancias Ocasionales", "Escrituras, certificados de premios, documentos de sucesión")

    add("129", "Total impuesto a cargo", liquidacion["total_impuesto_a_cargo"], "Calculado",
        "Impuesto neto de renta + Impuesto de ganancias ocasionales", "N/A (cálculo)")
    add("132", "Total retenciones año gravable 2025", liquidacion["retenciones_anio"],
        "Módulo Exógena (conciliado)", "Suma de retenciones en la fuente confirmadas en la conciliación",
        "Certificados de retención en la fuente")

    if liquidacion["saldo_a_pagar"] > 0:
        add("Final", "Saldo a pagar", liquidacion["saldo_a_pagar"], "Calculado",
            "Total impuesto a cargo + anticipo - retenciones", "N/A (cálculo)", estado="SALDO_A_PAGAR")
    else:
        add("Final", "Saldo a favor", liquidacion["saldo_a_favor"], "Calculado",
            "Retenciones - (Total impuesto a cargo + anticipo)", "N/A (cálculo)", estado="SALDO_A_FAVOR")

    return casillas
