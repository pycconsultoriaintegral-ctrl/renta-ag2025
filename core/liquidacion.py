# -*- coding: utf-8 -*-
"""
Motor de liquidación del impuesto de renta AG2025 - persona natural residente.

Metodología (Ley 2277 de 2022, vigente AG2025):
  1. CÉDULA GENERAL (Art. 335-336 ET): rentas de trabajo + capital + no laborales
  2. CÉDULA DE PENSIONES (Art. 337 ET)
  3. CÉDULA DE DIVIDENDOS Y PARTICIPACIONES (Art. 242 ET)
  4. GANANCIAS OCASIONALES (Art. 299-317 ET) - se liquidan por separado, no se suman
     a la renta líquida gravable ordinaria.

Cada función retorna un diccionario con el resultado Y su trazabilidad
(fórmula, norma, cálculos intermedios) para que la UI pueda mostrar
"por qué" se llegó a cada cifra, evitando una caja negra.
"""
from core import config


def liquidar_cedula_general(ingresos: dict, rentas_exentas_deducciones_soportadas: float) -> dict:
    """
    ingresos: {
        'trabajo_bruto': float, 'trabajo_incrngo': float,
        'capital_bruto': float, 'capital_costos': float,
        'no_laboral_bruto': float, 'no_laboral_costos': float,
    }
    rentas_exentas_deducciones_soportadas: suma de rentas exentas + deducciones
        especiales YA soportadas y confirmadas por el usuario (módulo Deducciones),
        SIN aplicar todavía el límite general del 40%/1.340 UVT (eso lo hace esta función).
    """
    trabajo_bruto = ingresos.get("trabajo_bruto", 0) or 0
    trabajo_incrngo = ingresos.get("trabajo_incrngo", 0) or 0
    capital_bruto = ingresos.get("capital_bruto", 0) or 0
    capital_costos = ingresos.get("capital_costos", 0) or 0
    no_laboral_bruto = ingresos.get("no_laboral_bruto", 0) or 0
    no_laboral_costos = ingresos.get("no_laboral_costos", 0) or 0

    ingresos_brutos = trabajo_bruto + capital_bruto + no_laboral_bruto
    incrngo = trabajo_incrngo  # aportes obligatorios a salud/pensión, etc.
    ingresos_netos = ingresos_brutos - incrngo
    costos_gastos = capital_costos + no_laboral_costos
    renta_liquida_antes_exentas = ingresos_netos - costos_gastos

    # Límite general Art. 336 ET: menor entre 40% de la renta líquida y 1.340 UVT
    tope_40pct = renta_liquida_antes_exentas * config.LIMITE_GENERAL_PORCENTAJE
    tope_1340uvt = config.uvt_a_pesos(config.LIMITE_GENERAL_UVT)
    limite_aplicable = max(min(tope_40pct, tope_1340uvt), 0)

    rentas_exentas_deducciones_aplicadas = min(rentas_exentas_deducciones_soportadas, limite_aplicable)

    renta_liquida_gravable = max(renta_liquida_antes_exentas - rentas_exentas_deducciones_aplicadas, 0)

    return {
        "ingresos_brutos": round(ingresos_brutos),
        "incrngo": round(incrngo),
        "ingresos_netos": round(ingresos_netos),
        "costos_y_gastos": round(costos_gastos),
        "renta_liquida_antes_de_exentas": round(renta_liquida_antes_exentas),
        "limite_general_40pct": round(tope_40pct),
        "limite_general_1340uvt_pesos": tope_1340uvt,
        "limite_general_aplicable": round(limite_aplicable),
        "rentas_exentas_deducciones_solicitadas": round(rentas_exentas_deducciones_soportadas),
        "rentas_exentas_deducciones_aplicadas": round(rentas_exentas_deducciones_aplicadas),
        "rentas_exentas_deducciones_rechazadas_por_limite": round(
            max(rentas_exentas_deducciones_soportadas - rentas_exentas_deducciones_aplicadas, 0)
        ),
        "renta_liquida_gravable_cedula_general": round(renta_liquida_gravable),
        "norma": "Art. 335, 336 Estatuto Tributario (Ley 2277 de 2022)",
        "formula": "Renta líquida gravable = (Ingresos brutos - INCRNGO - Costos y gastos) "
                   "- MIN(rentas exentas y deducciones soportadas, 40% renta líquida, 1.340 UVT)",
    }


def liquidar_cedula_pensiones(ingreso_pension_mensual_promedio: float, meses: int = 12) -> dict:
    """Renta exenta de pensiones: 1.000 UVT mensuales (Art. 206 num. 5 ET)."""
    ingreso_bruto_anual = (ingreso_pension_mensual_promedio or 0) * meses
    exento_mensual = config.uvt_a_pesos(1000)
    exento_anual_max = exento_mensual * meses
    exento_aplicado = min(ingreso_bruto_anual, exento_anual_max)
    renta_gravable = max(ingreso_bruto_anual - exento_aplicado, 0)
    return {
        "ingreso_bruto_anual": round(ingreso_bruto_anual),
        "renta_exenta_aplicada": round(exento_aplicado),
        "renta_liquida_gravable_pensiones": round(renta_gravable),
        "norma": "Art. 206 numeral 5 Estatuto Tributario",
        "formula": f"Exento hasta 1.000 UVT/mes (${exento_mensual:,}/mes); el exceso es gravable",
    }


def liquidar_dividendos(dividendos_2017_en_adelante_gravados: float, dividendos_2017_en_adelante_no_gravados: float) -> dict:
    """
    Cédula de dividendos y participaciones (Art. 242 ET, Ley 2277 de 2022).
    - Dividendos NO gravados (art. 49 num. 3 ET): primeros 1.090 UVT tributan a
      tarifa reducida y el exceso se suma a la cédula general para efectos de la
      tarifa (simplificación: se aplica tabla 242 asimilada a Art. 241 sobre el total).
    - Dividendos GRAVADOS (no beneficiados art. 49): tributan primero a la tarifa
      de sociedades y luego, sobre el remanente, se aplica la tabla del Art. 242.
    """
    no_gravados = dividendos_2017_en_adelante_no_gravados or 0
    gravados = dividendos_2017_en_adelante_gravados or 0
    tope_1090_pesos = config.uvt_a_pesos(config.DIVIDENDOS_NO_GRAVADOS_LIMITE_UVT)

    base_tarifa_reducida = min(no_gravados, tope_1090_pesos)
    exceso_sobre_1090 = max(no_gravados - tope_1090_pesos, 0)

    impuesto_tarifa_reducida = round(base_tarifa_reducida * config.DIVIDENDOS_TARIFA_HASTA_LIMITE)
    # El exceso de no gravados + el 100% de los gravados tributa con tabla Art. 241/242
    base_tabla = exceso_sobre_1090 + gravados
    detalle_tabla = config.calcular_impuesto_art241(base_tabla) if base_tabla > 0 else None

    impuesto_total = impuesto_tarifa_reducida + (detalle_tabla["impuesto_pesos"] if detalle_tabla else 0)

    return {
        "dividendos_no_gravados": round(no_gravados),
        "dividendos_gravados": round(gravados),
        "base_tarifa_reducida_15pct": round(base_tarifa_reducida),
        "impuesto_tarifa_reducida": impuesto_tarifa_reducida,
        "base_tabla_241": round(base_tabla),
        "detalle_tabla_241": detalle_tabla,
        "impuesto_total_dividendos": impuesto_total,
        "norma": "Art. 242 Estatuto Tributario (Ley 2277 de 2022)",
        "formula": f"15% sobre los primeros {config.DIVIDENDOS_NO_GRAVADOS_LIMITE_UVT} UVT de dividendos no gravados; "
                   "el exceso y los dividendos gravados tributan con la tabla del Art. 241/242 ET",
    }


def liquidar_ganancias_ocasionales(items: list[dict]) -> dict:
    """
    items: lista de {'tipo': 'venta_vivienda'|'herencia'|'loteria'|'otro', 'valor_bruto': float, 'costo_fiscal': float}
    """
    detalle = []
    total_gravable = 0
    total_impuesto = 0

    for it in items:
        tipo = it.get("tipo")
        bruto = it.get("valor_bruto", 0) or 0
        costo = it.get("costo_fiscal", 0) or 0
        utilidad = max(bruto - costo, 0)

        if tipo == "venta_vivienda":
            exento = min(utilidad, config.uvt_a_pesos(config.GO_VENTA_VIVIENDA_EXENTA_LIMITE_UVT))
            gravable = utilidad - exento
            tarifa = config.GANANCIA_OCASIONAL_TARIFA_GENERAL
            norma = "Art. 311-1 Estatuto Tributario (exento hasta 5.000 UVT si se consigna en cuenta AFC)"
        elif tipo == "herencia":
            exento = min(utilidad, config.uvt_a_pesos(config.GO_HERENCIA_EXENTA_LIMITE_UVT))
            gravable = utilidad - exento
            tarifa = config.GANANCIA_OCASIONAL_TARIFA_GENERAL
            norma = "Art. 307 num. 1 Estatuto Tributario"
        elif tipo == "loteria_rifa_apuesta":
            exento = 0
            gravable = bruto  # sobre el valor bruto del premio, sin depuración
            tarifa = config.GANANCIA_OCASIONAL_TARIFA_LOTERIAS_RIFAS
            norma = "Art. 317 Estatuto Tributario"
        else:
            exento = 0
            gravable = utilidad
            tarifa = config.GANANCIA_OCASIONAL_TARIFA_GENERAL
            norma = "Art. 300-302 Estatuto Tributario"

        impuesto = round(gravable * tarifa)
        total_gravable += gravable
        total_impuesto += impuesto
        detalle.append({
            **it, "utilidad": round(utilidad), "exento": round(exento),
            "gravable": round(gravable), "tarifa": tarifa, "impuesto": impuesto, "norma": norma,
        })

    return {
        "detalle": detalle,
        "total_ganancia_ocasional_gravable": round(total_gravable),
        "total_impuesto_ganancias_ocasionales": round(total_impuesto),
    }


def liquidar_declaracion(cedula_general: dict, cedula_pensiones: dict, dividendos: dict,
                          ganancias_ocasionales: dict, retenciones: float,
                          descuentos_tributarios: float = 0, anticipo_renta_anterior: float = 0,
                          saldo_favor_anio_anterior: float = 0) -> dict:
    """Consolida el impuesto total y determina saldo a pagar o saldo a favor.

    saldo_favor_anio_anterior: Saldo a favor del año gravable anterior que el
        contribuyente NO solicitó en devolución y/o compensación y que arrastra
        para imputar contra el impuesto del año actual (casilla 131 del
        Formulario 210 AG2025). Se resta junto con las retenciones.
    """
    renta_liquida_gravable_consolidada = (
        cedula_general["renta_liquida_gravable_cedula_general"]
        + cedula_pensiones["renta_liquida_gravable_pensiones"]
    )
    impuesto_cedula_general_pensiones = config.calcular_impuesto_art241(renta_liquida_gravable_consolidada)

    impuesto_dividendos = dividendos["impuesto_total_dividendos"]
    impuesto_ganancias_ocasionales = ganancias_ocasionales["total_impuesto_ganancias_ocasionales"]

    impuesto_bruto = impuesto_cedula_general_pensiones["impuesto_pesos"] + impuesto_dividendos
    impuesto_neto = max(impuesto_bruto - descuentos_tributarios, 0)
    total_impuesto_a_cargo = impuesto_neto + impuesto_ganancias_ocasionales

    saldo_favor_anio_anterior = saldo_favor_anio_anterior or 0
    saldo = (total_impuesto_a_cargo + anticipo_renta_anterior
             - (retenciones or 0) - saldo_favor_anio_anterior)

    return {
        "renta_liquida_gravable_consolidada": round(renta_liquida_gravable_consolidada),
        "detalle_impuesto_cedula_general_pensiones": impuesto_cedula_general_pensiones,
        "impuesto_dividendos": impuesto_dividendos,
        "impuesto_bruto": round(impuesto_bruto),
        "descuentos_tributarios": round(descuentos_tributarios),
        "impuesto_neto_renta": round(impuesto_neto),
        "impuesto_ganancias_ocasionales": round(impuesto_ganancias_ocasionales),
        "total_impuesto_a_cargo": round(total_impuesto_a_cargo),
        "retenciones_anio": round(retenciones or 0),
        "anticipo_renta_anterior": round(anticipo_renta_anterior),
        "saldo_favor_anio_anterior": round(saldo_favor_anio_anterior),
        "saldo_a_pagar": round(max(saldo, 0)),
        "saldo_a_favor": round(max(-saldo, 0)),
        "formula": "Total impuesto a cargo + anticipo año anterior - retenciones del año - saldo a favor año anterior sin solicitud de devolución/compensación = Saldo a pagar (o a favor si es negativo)",
    }
# -*- coding: utf-8 -*-
"""
Motor de liquidación del impuesto de renta AG2025 - persona natural residente.

Metodología (Ley 2277 de 2022, vigente AG2025):
  1. CÉDULA GENERAL (Art. 335-336 ET): rentas de trabajo + capital + no laborales
    2. CÉDULA DE PENSIONES (Art. 337 ET)
      3. CÉDULA DE DIVIDENDOS Y PARTICIPACIONES (Art. 242 ET)
        4. GANANCIAS OCASIONALES (Art. 299-317 ET) - se liquidan por separado, no se suman
             a la renta líquida gravable ordinaria.

             Cada función retorna un diccionario con el resultado Y su trazabilidad
             (fórmula, norma, cálculos intermedios) para que la UI pueda mostrar
             "por qué" se llegó a cada cifra, evitando una caja negra.
             """
from core import config


def liquidar_cedula_general(ingresos: dict, rentas_exentas_deducciones_soportadas: float) -> dict:
      """
          ingresos: {
                  'trabajo_bruto': float, 'trabajo_incrngo': float,
                          'capital_bruto': float, 'capital_costos': float,
                                  'no_laboral_bruto': float, 'no_laboral_costos': float,
                                      }
                                          rentas_exentas_deducciones_soportadas: suma de rentas exentas + deducciones
                                                  especiales YA soportadas y confirmadas por el usuario (módulo Deducciones),
                                                          SIN aplicar todavía el límite general del 40%/1.340 UVT (eso lo hace esta función).
                                                              """
      trabajo_bruto = ingresos.get("trabajo_bruto", 0) or 0
      trabajo_incrngo = ingresos.get("trabajo_incrngo", 0) or 0
      capital_bruto = ingresos.get("capital_bruto", 0) or 0
      capital_costos = ingresos.get("capital_costos", 0) or 0
      no_laboral_bruto = ingresos.get("no_laboral_bruto", 0) or 0
      no_laboral_costos = ingresos.get("no_laboral_costos", 0) or 0

    ingresos_brutos = trabajo_bruto + capital_bruto + no_laboral_bruto
    incrngo = trabajo_incrngo  # aportes obligatorios a salud/pensión, etc.
    ingresos_netos = ingresos_brutos - incrngo
    costos_gastos = capital_costos + no_laboral_costos
    renta_liquida_antes_exentas = ingresos_netos - costos_gastos

    # Límite general Art. 336 ET: menor entre 40% de la renta líquida y 1.340 UVT
    tope_40pct = renta_liquida_antes_exentas * config.LIMITE_GENERAL_PORCENTAJE
    tope_1340uvt = config.uvt_a_pesos(config.LIMITE_GENERAL_UVT)
    limite_aplicable = max(min(tope_40pct, tope_1340uvt), 0)

    rentas_exentas_deducciones_aplicadas = min(rentas_exentas_deducciones_soportadas, limite_aplicable)

    renta_liquida_gravable = max(renta_liquida_antes_exentas - rentas_exentas_deducciones_aplicadas, 0)

    return {
              "ingresos_brutos": round(ingresos_brutos),
              "incrngo": round(incrngo),
              "ingresos_netos": round(ingresos_netos),
              "costos_y_gastos": round(costos_gastos),
              "renta_liquida_antes_de_exentas": round(renta_liquida_antes_exentas),
              "limite_general_40pct": round(tope_40pct),
              "limite_general_1340uvt_pesos": tope_1340uvt,
              "limite_general_aplicable": round(limite_aplicable),
              "rentas_exentas_deducciones_solicitadas": round(rentas_exentas_deducciones_soportadas),
              "rentas_exentas_deducciones_aplicadas": round(rentas_exentas_deducciones_aplicadas),
              "rentas_exentas_deducciones_rechazadas_por_limite": round(
                            max(rentas_exentas_deducciones_soportadas - rentas_exentas_deducciones_aplicadas, 0)
              ),
              "renta_liquida_gravable_cedula_general": round(renta_liquida_gravable),
              "norma": "Art. 335, 336 Estatuto Tributario (Ley 2277 de 2022)",
              "formula": "Renta líquida gravable = (Ingresos brutos - INCRNGO - Costos y gastos) "
                         "- MIN(rentas exentas y deducciones soportadas, 40% renta líquida, 1.340 UVT)",
    }


def liquidar_cedula_pensiones(ingreso_pension_mensual_promedio: float, meses: int = 12) -> dict:
      """Renta exenta de pensiones: 1.000 UVT mensuales (Art. 206 num. 5 ET)."""
      ingreso_bruto_anual = (ingreso_pension_mensual_promedio or 0) * meses
      exento_mensual = config.uvt_a_pesos(1000)
      exento_anual_max = exento_mensual * meses
      exento_aplicado = min(ingreso_bruto_anual, exento_anual_max)
      renta_gravable = max(ingreso_bruto_anual - exento_aplicado, 0)
      return {
          "ingreso_bruto_anual": round(ingreso_bruto_anual),
          "renta_exenta_aplicada": round(exento_aplicado),
          "renta_liquida_gravable_pensiones": round(renta_gravable),
          "norma": "Art. 206 numeral 5 Estatuto Tributario",
          "formula": f"Exento hasta 1.000 UVT/mes (${exento_mensual:,}/mes); el exceso es gravable",
      }


def liquidar_dividendos(dividendos_2017_en_adelante_gravados: float, dividendos_2017_en_adelante_no_gravados: float) -> dict:
      """
          Cédula de dividendos y participaciones (Art. 242 ET, Ley 2277 de 2022).
              - Dividendos NO gravados (art. 49 num. 3 ET): primeros 1.090 UVT tributan a
                    tarifa reducida y el exceso se suma a la cédula general para efectos de la
                          tarifa (simplificación: se aplica tabla 242 asimilada a Art. 241 sobre el total).
                              - Dividendos GRAVADOS (no beneficiados art. 49): tributan primero a la tarifa
                                    de sociedades y luego, sobre el remanente, se aplica la tabla del Art. 242.
                                        """
      no_gravados = dividendos_2017_en_adelante_no_gravados or 0
      gravados = dividendos_2017_en_adelante_gravados or 0
      tope_1090_pesos = config.uvt_a_pesos(config.DIVIDENDOS_NO_GRAVADOS_LIMITE_UVT)

    base_tarifa_reducida = min(no_gravados, tope_1090_pesos)
    exceso_sobre_1090 = max(no_gravados - tope_1090_pesos, 0)

    impuesto_tarifa_reducida = round(base_tarifa_reducida * config.DIVIDENDOS_TARIFA_HASTA_LIMITE)
    # El exceso de no gravados + el 100% de los gravados tributa con tabla Art. 241/242
    base_tabla = exceso_sobre_1090 + gravados
    detalle_tabla = config.calcular_impuesto_art241(base_tabla) if base_tabla > 0 else None

    impuesto_total = impuesto_tarifa_reducida + (detalle_tabla["impuesto_pesos"] if detalle_tabla else 0)

    return {
              "dividendos_no_gravados": round(no_gravados),
              "dividendos_gravados": round(gravados),
              "base_tarifa_reducida_15pct": round(base_tarifa_reducida),
              "impuesto_tarifa_reducida": impuesto_tarifa_reducida,
              "base_tabla_241": round(base_tabla),
              "detalle_tabla_241": detalle_tabla,
              "impuesto_total_dividendos": impuesto_total,
              "norma": "Art. 242 Estatuto Tributario (Ley 2277 de 2022)",
              "formula": f"15% sobre los primeros {config.DIVIDENDOS_NO_GRAVADOS_LIMITE_UVT} UVT de dividendos no gravados; "
                         "el exceso y los dividendos gravados tributan con la tabla del Art. 241/242 ET",
    }


def liquidar_ganancias_ocasionales(items: list[dict]) -> dict:
      """
          items: lista de {'tipo': 'venta_vivienda'|'herencia'|'loteria'|'otro', 'valor_bruto': float, 'costo_fiscal': float}
              """
      detalle = []
      total_gravable = 0
      total_impuesto = 0

    for it in items:
              tipo = it.get("tipo")
              bruto = it.get("valor_bruto", 0) or 0
              costo = it.get("costo_fiscal", 0) or 0
              utilidad = max(bruto - costo, 0)

        if tipo == "venta_vivienda":
                      exento = min(utilidad, config.uvt_a_pesos(config.GO_VENTA_VIVIENDA_EXENTA_LIMITE_UVT))
                      gravable = utilidad - exento
                      tarifa = config.GANANCIA_OCASIONAL_TARIFA_GENERAL
                      norma = "Art. 311-1 Estatuto Tributario (exento hasta 5.000 UVT si se consigna en cuenta AFC)"
elif tipo == "herencia":
              exento = min(utilidad, config.uvt_a_pesos(config.GO_HERENCIA_EXENTA_LIMITE_UVT))
              gravable = utilidad - exento
              tarifa = config.GANANCIA_OCASIONAL_TARIFA_GENERAL
              norma = "Art. 307 num. 1 Estatuto Tributario"
elif tipo == "loteria_rifa_apuesta":
              exento = 0
              gravable = bruto  # sobre el valor bruto del premio, sin depuración
            tarifa = config.GANANCIA_OCASIONAL_TARIFA_LOTERIAS_RIFAS
            norma = "Art. 317 Estatuto Tributario"
else:
            exento = 0
              gravable = utilidad
            tarifa = config.GANANCIA_OCASIONAL_TARIFA_GENERAL
            norma = "Art. 300-302 Estatuto Tributario"

        impuesto = round(gravable * tarifa)
        total_gravable += gravable
        total_impuesto += impuesto
        detalle.append({
                      **it, "utilidad": round(utilidad), "exento": round(exento),
                      "gravable": round(gravable), "tarifa": tarifa, "impuesto": impuesto, "norma": norma,
        })

    return {
              "detalle": detalle,
              "total_ganancia_ocasional_gravable": round(total_gravable),
              "total_impuesto_ganancias_ocasionales": round(total_impuesto),
    }


def liquidar_declaracion(cedula_general: dict, cedula_pensiones: dict, dividendos: dict,
                                                   ganancias_ocasionales: dict, retenciones: float,
                                                   descuentos_tributarios: float = 0, anticipo_renta_anterior: float = 0,
                                                   saldo_favor_anio_anterior: float = 0) -> dict:
                                                         """Consolida el impuesto total y determina saldo a pagar o saldo a favor.

                                                             saldo_favor_anio_anterior: Saldo a favor del año gravable anterior que el
                                                                     contribuyente NO solicitó en devolución y/o compensación y que arrastra
                                                                             para imputar contra el impuesto del año actual (casilla 131 del
                                                                                     Formulario 210 AG2025). Se resta junto con las retenciones.
                                                                                         """
                                                         renta_liquida_gravable_consolidada = (
                                                             cedula_general["renta_liquida_gravable_cedula_general"]
                                                             + cedula_pensiones["renta_liquida_gravable_pensiones"]
                                                         )
                                                         impuesto_cedula_general_pensiones = config.calcular_impuesto_art241(renta_liquida_gravable_consolidada)

    impuesto_dividendos = dividendos["impuesto_total_dividendos"]
    impuesto_ganancias_ocasionales = ganancias_ocasionales["total_impuesto_ganancias_ocasionales"]

    impuesto_bruto = impuesto_cedula_general_pensiones["impuesto_pesos"] + impuesto_dividendos
    impuesto_neto = max(impuesto_bruto - descuentos_tributarios, 0)
    total_impuesto_a_cargo = impuesto_neto + impuesto_ganancias_ocasionales

    saldo_favor_anio_anterior = saldo_favor_anio_anterior or 0
    saldo = (total_impuesto_a_cargo + anticipo_renta_anterior
                          - (retenciones or 0) - saldo_favor_anio_anterior)

    return {
              "renta_liquida_gravable_consolidada": round(renta_liquida_gravable_consolidada),
              "detalle_impuesto_cedula_general_pensiones": impuesto_cedula_general_pensiones,
              "impuesto_dividendos": impuesto_dividendos,
              "impuesto_bruto": round(impuesto_bruto),
              "descuentos_tributarios": round(descuentos_tributarios),
              "impuesto_neto_renta": round(impuesto_neto),
              "impuesto_ganancias_ocasionales": round(impuesto_ganancias_ocasionales),
              "total_impuesto_a_cargo": round(total_impuesto_a_cargo),
              "retenciones_anio": round(retenciones or 0),
              "anticipo_renta_anterior": round(anticipo_renta_anterior),
              "saldo_favor_anio_anterior": round(saldo_favor_anio_anterior),
              "saldo_a_pagar": round(max(saldo, 0)),
              "saldo_a_favor": round(max(-saldo, 0)),
              "formula": "Total impuesto a cargo + anticipo año anterior - retenciones del año - saldo a favor año anterior sin solicitud de devolución/compensación = Saldo a pagar (o a favor si es negativo)",
    }
