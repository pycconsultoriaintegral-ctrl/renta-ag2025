# -*- coding: utf-8 -*-
"""
Optimizador tributario legal: compara escenarios de aplicación de beneficios
para mostrar la MENOR CARGA TRIBUTARIA LEGALMENTE PROCEDENTE.
Nunca inventa un beneficio: solo compara aplicar o no aplicar los que el
usuario ya registró (soportados o no) en el módulo de Deducciones.
"""
from core import liquidacion as liq


def comparar_escenarios(ingresos: dict, cedula_pensiones_input: dict, beneficios: list,
                         retenciones: float, dividendos_input: dict, ganancias_ocasionales_items: list) -> dict:
    soportados = [b for b in beneficios if b.get("soportado")]
    todos_potenciales = beneficios  # incluye soportados y no soportados

    valor_soportados = sum(b["valor_utilizado"] or b["valor_potencial"] for b in soportados)
    valor_todos = sum(b["valor_potencial"] for b in todos_potenciales)

    escenarios_def = [
        ("A - Sin beneficios pendientes", 0),
        ("B - Aplicando solo beneficios soportados", valor_soportados),
        ("C - Aplicando todos los beneficios detectados (hipotético, requiere soporte)", valor_todos),
    ]

    resultados = []
    for nombre, valor_exentas_deducciones in escenarios_def:
        ced_gen = liq.liquidar_cedula_general(ingresos, valor_exentas_deducciones)
        ced_pen = liq.liquidar_cedula_pensiones(**cedula_pensiones_input)
        div = liq.liquidar_dividendos(**dividendos_input)
        go = liq.liquidar_ganancias_ocasionales(ganancias_ocasionales_items)
        liquidacion = liq.liquidar_declaracion(ced_gen, ced_pen, div, go, retenciones)
        resultados.append({
            "escenario": nombre,
            "renta_liquida": ced_gen["renta_liquida_antes_de_exentas"],
            "renta_gravable": liquidacion["renta_liquida_gravable_consolidada"],
            "impuesto_a_cargo": liquidacion["total_impuesto_a_cargo"],
            "retenciones": liquidacion["retenciones_anio"],
            "saldo_a_pagar": liquidacion["saldo_a_pagar"],
            "saldo_a_favor": liquidacion["saldo_a_favor"],
        })

    base = resultados[0]["impuesto_a_cargo"]
    for r in resultados:
        r["ahorro_vs_escenario_base"] = base - r["impuesto_a_cargo"]

    optimo = min(resultados, key=lambda r: r["impuesto_a_cargo"])
    # El escenario "óptimo real" (legalmente disponible hoy) es B, no C, salvo que
    # C esté igual de soportado; C es solo referencia de lo que se ganaría consiguiendo soportes.
    optimo_legal = resultados[1]

    return {
        "escenarios": resultados,
        "escenario_optimo_referencial": optimo["escenario"],
        "escenario_optimo_legal_hoy": optimo_legal["escenario"],
        "nota": "El 'óptimo legal disponible hoy' corresponde al escenario B (solo beneficios con "
                "soporte). El escenario C es una referencia de cuánto se podría ahorrar adicionalmente "
                "si se consiguen los soportes faltantes: NO debe presentarse sin dichos soportes.",
    }
