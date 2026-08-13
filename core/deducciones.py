# -*- coding: utf-8 -*-
"""
Motor de detección de beneficios tributarios (rentas exentas y deducciones)
para AG2025. NUNCA aplica un beneficio automáticamente al cálculo final:
solo calcula el VALOR POTENCIAL según los datos y límites legales, y deja
en manos del usuario marcar si cuenta con el soporte documental exigido.
Si no hay soporte -> "NO APLICAR - FALTA SOPORTE".
"""
from core import config
from core.db import get_conn


def calcular_catalogo_beneficios(perfil: dict) -> list[dict]:
    """perfil: dict con las claves que el usuario diligencia en el módulo
    de Deducciones (todas opcionales; ausentes = 0)."""
    uvt = config.UVT_2025
    beneficios = []

    # 1. Renta exenta laboral 25% (Art. 206 num. 10 ET)
    ingreso_laboral = perfil.get("ingresos_laborales", 0) or 0
    if ingreso_laboral > 0:
        valor_25 = ingreso_laboral * 0.25
        tope_pesos = config.uvt_a_pesos(config.RENTA_EXENTA_25_LABORAL_LIMITE_UVT)
        valor_aplicable = min(valor_25, tope_pesos)
        beneficios.append({
            "beneficio": "Renta exenta laboral 25%",
            "valor_potencial": round(valor_aplicable),
            "limite_aplicable": f"25% del ingreso laboral, máx. {config.RENTA_EXENTA_25_LABORAL_LIMITE_UVT} UVT/año (${tope_pesos:,})",
            "documento_requerido": "Certificado de ingresos y retenciones (formulario 220)",
            "norma": "Art. 206 num. 10 Estatuto Tributario",
            "requiere_soporte": False,
        })

    # 2. Deducción por dependientes (Art. 336 ET / Decreto 2231 de 2023)
    n_dependientes = min(perfil.get("num_dependientes", 0) or 0, config.MAX_DEPENDIENTES)
    if n_dependientes > 0:
        valor = n_dependientes * config.uvt_a_pesos(config.DEDUCCION_DEPENDIENTE_UVT)
        beneficios.append({
            "beneficio": f"Deducción por dependientes ({n_dependientes})",
            "valor_potencial": valor,
            "limite_aplicable": f"{config.DEDUCCION_DEPENDIENTE_UVT} UVT/dependiente, máx. {config.MAX_DEPENDIENTES} dependientes",
            "documento_requerido": "Documento que acredite la dependencia económica (registro civil, certificado, etc.)",
            "norma": "Art. 336 Estatuto Tributario (Decreto 2231 de 2023)",
            "requiere_soporte": True,
        })

    # 3. Intereses de vivienda (Art. 119 ET)
    intereses_vivienda = perfil.get("intereses_vivienda", 0) or 0
    if intereses_vivienda > 0:
        tope = config.uvt_a_pesos(config.DEDUCCION_INTERESES_VIVIENDA_LIMITE_UVT)
        beneficios.append({
            "beneficio": "Intereses/corrección monetaria crédito de vivienda",
            "valor_potencial": min(intereses_vivienda, tope),
            "limite_aplicable": f"Máx. {config.DEDUCCION_INTERESES_VIVIENDA_LIMITE_UVT} UVT/año (${tope:,})",
            "documento_requerido": "Certificado anual de intereses de la entidad financiera",
            "norma": "Art. 119 Estatuto Tributario",
            "requiere_soporte": True,
        })

    # 4. Medicina prepagada (Art. 387 ET)
    medicina_prepagada = perfil.get("medicina_prepagada", 0) or 0
    if medicina_prepagada > 0:
        tope = config.uvt_a_pesos(config.DEDUCCION_MEDICINA_PREPAGADA_LIMITE_UVT_ANUAL)
        beneficios.append({
            "beneficio": "Pagos de salud (medicina prepagada / seguros de salud)",
            "valor_potencial": min(medicina_prepagada, tope),
            "limite_aplicable": f"Máx. {config.DEDUCCION_MEDICINA_PREPAGADA_LIMITE_UVT_MENSUAL} UVT/mes "
                                 f"({config.DEDUCCION_MEDICINA_PREPAGADA_LIMITE_UVT_ANUAL} UVT/año = ${tope:,})",
            "documento_requerido": "Certificado de pagos de la entidad de medicina prepagada",
            "norma": "Art. 387 Estatuto Tributario",
            "requiere_soporte": True,
        })

    # 5. Aportes voluntarios a pensión / cuentas AFC (Art. 126-1 y 126-4 ET)
    aportes_afc_pension = perfil.get("aportes_afc_pension_voluntario", 0) or 0
    if aportes_afc_pension > 0:
        tope = config.uvt_a_pesos(config.DEDUCCION_AFC_PENSIONES_VOLUNTARIAS_LIMITE_UVT)
        beneficios.append({
            "beneficio": "Aportes voluntarios a fondos de pensión y/o cuentas AFC",
            "valor_potencial": min(aportes_afc_pension, tope),
            "limite_aplicable": f"Máx. {config.DEDUCCION_AFC_PENSIONES_VOLUNTARIAS_LIMITE_UVT} UVT/año (${tope:,}), "
                                 "sujeto también al límite general del 40%/1.340 UVT",
            "documento_requerido": "Certificado del fondo de pensiones voluntarias o de la cuenta AFC",
            "norma": "Art. 126-1 y 126-4 Estatuto Tributario",
            "requiere_soporte": True,
        })

    # 6. GMF - 50% deducible (Art. 115 ET)
    gmf_pagado = perfil.get("gmf_pagado", 0) or 0
    if gmf_pagado > 0:
        beneficios.append({
            "beneficio": "Gravamen a los Movimientos Financieros (GMF / 4x1000)",
            "valor_potencial": round(gmf_pagado * config.GMF_PORCENTAJE_DEDUCIBLE),
            "limite_aplicable": "50% del GMF pagado, sin requisito de relación de causalidad",
            "documento_requerido": "Certificado anual de GMF de la(s) entidad(es) financiera(s)",
            "norma": "Art. 115 Estatuto Tributario",
            "requiere_soporte": True,
        })

    # 7. 1% compras soportadas en factura electrónica (Art. 336 par. 5 ET)
    compras_facturadas = perfil.get("compras_factura_electronica", 0) or 0
    ingresos_totales = perfil.get("ingresos_totales_declarados", 0) or 0
    if compras_facturadas > 0:
        tope_uvt = config.uvt_a_pesos(config.DEDUCCION_FACTURA_ELECTRONICA_LIMITE_UVT)
        tope_ingresos = ingresos_totales * config.DEDUCCION_FACTURA_ELECTRONICA_PORCENTAJE
        valor_1pct = compras_facturadas * config.DEDUCCION_FACTURA_ELECTRONICA_PORCENTAJE
        valor_aplicable = min(valor_1pct, tope_uvt, tope_ingresos) if ingresos_totales else min(valor_1pct, tope_uvt)
        beneficios.append({
            "beneficio": "1% de compras de bienes/servicios soportadas en factura electrónica",
            "valor_potencial": round(max(valor_aplicable, 0)),
            "limite_aplicable": f"1% del valor de compras, máx. {config.DEDUCCION_FACTURA_ELECTRONICA_LIMITE_UVT} UVT/año "
                                 f"(${tope_uvt:,}) y sin exceder el 1% de los ingresos declarados",
            "documento_requerido": "Facturas electrónicas con el NIT del contribuyente como adquiriente",
            "norma": "Art. 336 parágrafo 5 Estatuto Tributario (Ley 2277 de 2022)",
            "requiere_soporte": True,
        })

    return beneficios


def guardar_beneficio(contribuyente_id: str, beneficio: dict, soportado: bool, valor_utilizado: float, notas: str = ""):
    with get_conn() as conn:
        existente = conn.execute(
            "SELECT id FROM deducciones WHERE contribuyente_id=? AND beneficio=?",
            (contribuyente_id, beneficio["beneficio"]),
        ).fetchone()
        if existente:
            conn.execute(
                "UPDATE deducciones SET valor_potencial=?, limite_aplicable=?, documento_requerido=?, "
                "soportado=?, valor_utilizado=?, notas=? WHERE id=?",
                (beneficio["valor_potencial"], beneficio["limite_aplicable"], beneficio["documento_requerido"],
                 int(soportado), valor_utilizado if soportado else 0, notas, existente["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO deducciones (contribuyente_id, beneficio, valor_potencial, limite_aplicable, "
                "documento_requerido, soportado, valor_utilizado, notas) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (contribuyente_id, beneficio["beneficio"], beneficio["valor_potencial"], beneficio["limite_aplicable"],
                 beneficio["documento_requerido"], int(soportado), valor_utilizado if soportado else 0, notas),
            )


def listar_beneficios(contribuyente_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM deducciones WHERE contribuyente_id=? ORDER BY beneficio", (contribuyente_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def total_soportado(contribuyente_id: str) -> float:
    return sum(b["valor_utilizado"] or 0 for b in listar_beneficios(contribuyente_id) if b["soportado"])
