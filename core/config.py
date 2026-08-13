# -*- coding: utf-8 -*-
"""
Parámetros tributarios oficiales para el AÑO GRAVABLE 2025 (Colombia).
Persona natural residente fiscal - Declaración de renta (Formulario 210).

Cada parámetro incluye su fuente normativa. NO modificar sin verificar la norma.
Este módulo es la única fuente de verdad de valores legales del sistema:
así se evita "inventar" cifras en otros módulos.
"""

from dataclasses import dataclass

ANIO_GRAVABLE = 2025
ANIO_DECLARACION = 2026

# UVT 2025 = $49.799 (Resolución DIAN 000193 del 4 de diciembre de 2024)
UVT_2025 = 49_799

# Formulario 210 AG2025: mismo modelo adoptado por Resolución DIAN 000044 del
# 14 de marzo de 2024, modificada por Resolución 000120 del 31 de julio de 2024.
FORMULARIO_210_RESOLUCION = "Resolución DIAN 000044 de 2024 (modificada por Res. 000120 de 2024)"

# Plazos AG2025 (se presenta en 2026): 12 de agosto a 26 de octubre de 2026,
# según los dos últimos dígitos del NIT/cédula (calendario tributario DIAN).
PLAZO_INICIO = "2026-08-12"
PLAZO_FIN = "2026-10-26"


def uvt_a_pesos(valor_uvt: float) -> int:
    return round(valor_uvt * UVT_2025)


def pesos_a_uvt(valor_pesos: float) -> float:
    return valor_pesos / UVT_2025


# ---------------------------------------------------------------------------
# Obligación de declarar - topes AG2025 (Art. 592-594-3 ET, Decreto de plazos)
# Se listan en UVT; el motor de auditoría los usa solo como alerta informativa,
# nunca para omitir el análisis completo.
# ---------------------------------------------------------------------------
TOPES_OBLIGADOS_UVT = {
    "patrimonio_bruto": 4500,
    "ingresos_brutos": 1400,
    "consumos_tarjeta_credito": 1400,
    "compras_consumos_totales": 1400,
    "consignaciones_depositos_inversiones": 1400,
}

# ---------------------------------------------------------------------------
# Tabla del Art. 241 E.T. - tarifa marginal para personas naturales residentes.
# Rangos en UVT (no cambian de un año a otro; solo cambia el valor de la UVT).
# Fórmula: impuesto = (base_uvt - limite_inferior) * tarifa_marginal + impuesto_base_uvt
# ---------------------------------------------------------------------------
TABLA_ART_241 = [
    # (limite_inferior_uvt, limite_superior_uvt, tarifa_marginal, impuesto_acumulado_uvt)
    (0, 1090, 0.00, 0),
    (1090, 1700, 0.19, 0),
    (1700, 4100, 0.28, 116),
    (4100, 8670, 0.33, 788),
    (8670, 18970, 0.35, 2296),
    (18970, 31000, 0.37, 5901),
    (31000, float("inf"), 0.39, 10352),
]


def calcular_impuesto_art241(renta_liquida_gravable_pesos: float) -> dict:
    """Aplica la tabla del Art. 241 ET sobre una base gravable en pesos.
    Retorna detalle trazable del cálculo (nunca caja negra)."""
    base_uvt = pesos_a_uvt(renta_liquida_gravable_pesos)
    for inf, sup, tarifa, acumulado_uvt in TABLA_ART_241:
        if inf <= base_uvt < sup or (sup == float("inf") and base_uvt >= inf):
            impuesto_uvt = (base_uvt - inf) * tarifa + acumulado_uvt
            return {
                "base_gravable_pesos": round(renta_liquida_gravable_pesos),
                "base_gravable_uvt": round(base_uvt, 2),
                "rango_uvt": f"{inf} a {sup if sup != float('inf') else 'en adelante'}",
                "tarifa_marginal": tarifa,
                "impuesto_acumulado_uvt_rango": acumulado_uvt,
                "impuesto_uvt": round(impuesto_uvt, 2),
                "impuesto_pesos": uvt_a_pesos(impuesto_uvt),
                "norma": "Art. 241 Estatuto Tributario",
                "formula": f"(Base UVT {round(base_uvt,2)} - {inf}) x {tarifa:.0%} + {acumulado_uvt} UVT",
            }
    raise ValueError("Base gravable fuera de rango de la tabla Art. 241")


# ---------------------------------------------------------------------------
# Límites de rentas exentas y deducciones - Cédula General (Art. 336 ET,
# modificado por Ley 2277 de 2022, vigente para AG2025)
# ---------------------------------------------------------------------------

# Renta exenta laboral del 25% (Art. 206 num. 10 ET) - límite anual 790 UVT
RENTA_EXENTA_25_LABORAL_LIMITE_UVT = 790

# Límite general: la sumatoria de rentas exentas + deducciones especiales
# imputables a la cédula general no puede exceder el 40% del ingreso neto
# (ingresos - ingresos no constitutivos - costos y gastos procedentes),
# ni 1.340 UVT anuales. Art. 336 ET.
LIMITE_GENERAL_PORCENTAJE = 0.40
LIMITE_GENERAL_UVT = 1340

# Deducción por dependientes (Art. 336 ET, Decreto 2231 de 2023):
# 72 UVT anuales por dependiente, máximo 4 dependientes.
DEDUCCION_DEPENDIENTE_UVT = 72
MAX_DEPENDIENTES = 4

# Deducción Art. 387 ET (alternativa/adicional a dependientes si hay relación
# laboral): 10% de ingresos brutos de trabajo, máximo 32 UVT mensuales (384 UVT/año)
DEDUCCION_10PCT_LABORAL_LIMITE_UVT_MENSUAL = 32

# Intereses / corrección monetaria en préstamos para adquisición de vivienda
# (Art. 119 ET): límite 1.200 UVT anuales
DEDUCCION_INTERESES_VIVIENDA_LIMITE_UVT = 1200

# Medicina prepagada / seguros de salud (Art. 387 ET): límite 16 UVT mensuales
# (192 UVT anuales)
DEDUCCION_MEDICINA_PREPAGADA_LIMITE_UVT_MENSUAL = 16
DEDUCCION_MEDICINA_PREPAGADA_LIMITE_UVT_ANUAL = 192

# Aportes voluntarios a fondos de pensiones + cuentas AFC (Art. 126-1 y 126-4 ET):
# límite conjunto 3.800 UVT anuales (adicional al límite general del 40%/1340 UVT,
# pero sujeto también a él en la cédula general)
DEDUCCION_AFC_PENSIONES_VOLUNTARIAS_LIMITE_UVT = 3800

# GMF (4x1000) - 50% deducible sin necesidad de que sea factor de costo (Art. 115 ET)
GMF_PORCENTAJE_DEDUCIBLE = 0.50

# Deducción 1% adquisición de bienes/servicios soportada en factura electrónica
# (Art. 336 par. 5 ET / Ley 2277 de 2022): 1% del valor, límite 240 UVT anuales,
# sin exceder el 1% de los ingresos declarados. No se puede usar simultáneamente
# como costo/deducción imputada por otro concepto y beneficio de esta deducción.
DEDUCCION_FACTURA_ELECTRONICA_PORCENTAJE = 0.01
DEDUCCION_FACTURA_ELECTRONICA_LIMITE_UVT = 240

# ---------------------------------------------------------------------------
# Cédula de dividendos y participaciones (Art. 242 ET, modificado Ley 2277/2022)
# ---------------------------------------------------------------------------
# Dividendos no gravados (num.3 Art 49 ET) provenientes de utilidades AG2017+:
# primeros 1.090 UVT gravados a tarifa marginal reducida; exceso a tabla 242.
DIVIDENDOS_NO_GRAVADOS_LIMITE_UVT = 1090
DIVIDENDOS_TARIFA_HASTA_LIMITE = 0.15  # 15% sobre exceso de 0 a 1090 UVT (retención trasladable)

# ---------------------------------------------------------------------------
# Ganancias ocasionales (Art. 302-317 ET)
# ---------------------------------------------------------------------------
GANANCIA_OCASIONAL_TARIFA_GENERAL = 0.15
GANANCIA_OCASIONAL_TARIFA_LOTERIAS_RIFAS = 0.20
# Venta de casa/apto de habitación: primeras 5.000 UVT de la utilidad exentas
# (Art. 311-1 ET), sujeto a que el valor de la venta se consigne en cuenta AFC
GO_VENTA_VIVIENDA_EXENTA_LIMITE_UVT = 5000
# Herencias/legados/donaciones: porción exenta hasta 3.490 UVT (Art. 307 num.1 ET)
GO_HERENCIA_EXENTA_LIMITE_UVT = 3490


@dataclass
class ParametrosAG2025:
    anio: int = ANIO_GRAVABLE
    uvt: int = UVT_2025

    def resumen(self) -> dict:
        return {
            "anio_gravable": self.anio,
            "uvt": self.uvt,
            "formulario": FORMULARIO_210_RESOLUCION,
            "plazo": f"{PLAZO_INICIO} a {PLAZO_FIN}",
        }
