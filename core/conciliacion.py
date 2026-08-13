# -*- coding: utf-8 -*-
"""
Motor de conciliación de la información exógena.

PRINCIPIO FUNDAMENTAL: la exógena NO es la declaración. Este módulo NUNCA
convierte automáticamente un valor reportado en ingreso gravable definitivo:
solo sugiere una clasificación inicial basada en el texto del concepto
reportado por la DIAN, que el usuario debe revisar y confirmar.

Estados posibles:
  CONFIRMADO         -> el usuario ya validó que corresponde a un hecho económico real
  POR_CONCILIAR      -> requiere que el usuario indique si aplica y a qué cédula
  NO_INGRESO         -> el concepto no constituye ingreso (ej. patrimonio, movimiento propio)
  REQUIERE_SOPORTE   -> podría ser ingreso pero falta certificado/soporte para confirmarlo
  OPORTUNIDAD        -> podría dar lugar a un beneficio tributario (deducción/exención)
  NO_INCLUIR         -> no debe incluirse en la declaración hasta verificar (riesgo de duplicidad o error)
"""
import re
import unicodedata


def _sin_tildes(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt)
    return "".join(c for c in txt if not unicodedata.combining(c)).lower()


# La columna "Uso declaración Sugerida" de la DIAN a veces trae directamente el
# número de casilla del Formulario 210 al que aplicaría el valor (ej. "R132
# Retenciones año gravable a declarar"). Cuando ese código aparece, es la
# señal MÁS confiable disponible (viene de la propia DIAN) y tiene prioridad
# sobre las reglas de palabras clave basadas en el texto del "Detalle".
CASILLAS_DIAN = [
    (re.compile(r"\bR132\b"), "Retenciones", "Retención en la fuente reportada por el tercero (casilla sugerida R132 por la DIAN)",
     "CONFIRMADO", "Certificado de retención en la fuente del tercero"),
    (re.compile(r"\bR29\b|\bR30\b"), "Patrimonio", "La DIAN sugiere llevar este valor a patrimonio bruto (R29) o deudas (R30)",
     "REQUIERE_SOPORTE", "Certificado de saldo a 31 de diciembre de 2025 de la entidad"),
    (re.compile(r"\bR112\b"), "Ganancia ocasional", "La DIAN sugiere que este valor corresponde a ganancias ocasionales (casilla R112)",
     "POR_CONCILIAR", "Escritura o documento que soporte la operación (venta de bien, herencia, etc.)"),
    (re.compile(r"\bR32\b|\bR36\b"), "Rentas de trabajo", "La DIAN sugiere ingreso bruto de trabajo (R32) o renta exenta laboral (R36)",
     "POR_CONCILIAR", "Certificado de ingresos y retenciones (formulario 220)"),
    (re.compile(r"\bR58\b|\bR59\b"), "Rentas de capital", "La DIAN sugiere ingreso bruto de capital (R58) o ingreso no constitutivo de capital (R59)",
     "POR_CONCILIAR", "Certificado de rendimientos financieros de la entidad"),
    (re.compile(r"\bR51\b|\bR67\b|\bR84\b"), "Rentas no laborales / capital", "La DIAN sugiere costo/deducción imputable a honorarios (R51), capital (R67) o no laborales (R84)",
     "POR_CONCILIAR", "Soporte del costo o gasto asociado (factura, contrato)"),
]


def _detectar_por_casilla_dian(uso_sugerido: str):
    if not uso_sugerido:
        return None
    for patron, cedula, tratamiento, estado, soporte in CASILLAS_DIAN:
        if patron.search(uso_sugerido):
            return {
                "cedula_sugerida": cedula,
                "tratamiento_sugerido": tratamiento,
                "estado": estado,
                "soporte_requerido": soporte,
            }
    return None


# Cada regla: (palabras_clave, cedula, tratamiento, estado, soporte_requerido)
REGLAS = [
    (["salario", "pagos laborales", "relacion laboral", "aportes obligatorios"],
     "Rentas de trabajo", "Ingreso laboral - depurar con certificado de ingresos y retenciones",
     "POR_CONCILIAR", "Certificado de ingresos y retenciones (formulario 220) del empleador"),

    (["honorarios", "comisiones", "servicios"],
     "Rentas de trabajo / no laborales", "Definir si hay vinculación/subordinación (trabajo) o independencia (no laboral)",
     "POR_CONCILIAR", "Certificado de retención en la fuente / contrato de prestación de servicios"),

    (["pension", "pensiones"],
     "Rentas de pensiones", "Ingreso por pensión - verificar renta exenta (1.000 UVT/mes, Art. 206 num. 5 ET)",
     "POR_CONCILIAR", "Certificado de pagos por pensión de la entidad pagadora"),

    (["dividendo", "participaciones"],
     "Dividendos y participaciones", "Cédula de dividendos - verificar si gravados/no gravados (Art. 49 ET)",
     "POR_CONCILIAR", "Certificado de dividendos y participaciones de la sociedad"),

    (["interes", "rendimiento financiero", "rendimientos financieros"],
     "Rentas de capital", "Interés/rendimiento financiero gravable",
     "POR_CONCILIAR", "Certificado de rendimientos financieros de la entidad"),

    (["arrendamiento", "arriendo"],
     "Rentas de capital", "Ingreso por arrendamiento - se pueden restar costos y gastos asociados",
     "POR_CONCILIAR", "Contrato de arrendamiento y soportes de costos asociados"),

    (["enajenacion de activos fijos", "venta de activos", "enajenacion de bien"],
     "Renta líquida / Ganancia ocasional", "Definir si el activo se poseyó >2 años (ganancia ocasional) o <2 años (renta ordinaria)",
     "POR_CONCILIAR", "Escritura o documento de compra y venta del activo, certificados de tradición"),

    (["retencion", "autorretencion"],
     "Retenciones", "Retención practicada - se descuenta del impuesto a cargo",
     "CONFIRMADO", "Certificado de retención en la fuente"),

    (["gravamen a los movimientos financieros", "gmf", "4x1000", "4 x 1000"],
     "Deducción GMF", "50% del GMF pagado es deducible sin requisito de relación de causalidad (Art. 115 ET)",
     "OPORTUNIDAD", "Certificado anual de GMF de la entidad financiera"),

    (["consignaciones", "depositos e inversiones", "movimientos financieros"],
     "Control patrimonial", "Insumo de control patrimonial/obligación de declarar - NO es ingreso por sí mismo",
     "NO_INGRESO", None),

    (["cuenta de ahorro", "cuenta corriente", "cuentas bancarias", "saldo en cuenta"],
     "Patrimonio - activo", "Saldo bancario a 31/12 - se lleva a patrimonio, no a ingresos",
     "NO_INGRESO", "Certificado bancario de saldos a 31 de diciembre de 2025"),

    (["certificado de deposito a termino", "cdt"],
     "Patrimonio - activo", "Inversión CDT - se lleva a patrimonio; los rendimientos van a rentas de capital",
     "NO_INGRESO", "Certificado de la entidad financiera"),

    (["acciones", "aportes en sociedades", "aportes sociales"],
     "Patrimonio - activo", "Participación societaria - se lleva a patrimonio por valor patrimonial/costo fiscal",
     "NO_INGRESO", "Certificado de la sociedad o comisionista de bolsa"),

    (["bienes raices", "inmueble", "predial"],
     "Patrimonio - activo", "Inmueble - se lleva a patrimonio por el mayor valor entre costo fiscal y avalúo catastral",
     "NO_INGRESO", "Certificado de tradición, avalúo catastral / autoavalúo"),

    (["vehiculo", "vehiculos"],
     "Patrimonio - activo", "Vehículo - se lleva a patrimonio por el costo fiscal ajustado",
     "NO_INGRESO", "Tarjeta de propiedad, factura de compra"),

    (["prestamo", "credito", "obligacion financiera", "deuda"],
     "Patrimonio - pasivo", "Obligación financiera - se lleva a patrimonio (pasivo), no es ingreso",
     "NO_INGRESO", "Certificado de saldo de la obligación a 31 de diciembre de 2025"),

    (["compras", "consumos tarjeta de credito", "consumos con tarjeta"],
     "Control - no es ingreso", "Consumo/compra reportado como control patrimonial - no constituye ingreso",
     "NO_INGRESO", None),

    (["aportes voluntarios", "fondo de pensiones voluntario", "afc", "ahorro para el fomento a la construccion"],
     "Deducción/renta exenta", "Posible deducción por aportes voluntarios a pensión o cuentas AFC (límite 3.800 UVT, Art. 126 ET)",
     "OPORTUNIDAD", "Certificado del fondo de pensiones voluntarias o de la cuenta AFC"),

    (["salud prepagada", "medicina prepagada", "seguro de salud"],
     "Deducción", "Posible deducción por medicina prepagada (límite 16 UVT/mes, Art. 387 ET)",
     "OPORTUNIDAD", "Certificado de pagos de la entidad de medicina prepagada"),

    (["indemnizacion"],
     "Renta / Ganancia ocasional", "Definir naturaleza de la indemnización (daño emergente no gravado; lucro cesante gravado)",
     "POR_CONCILIAR", "Documento o sentencia que origina la indemnización"),

    (["donacion", "herencia", "legado", "sucesion"],
     "Ganancia ocasional", "Herencia/legado/donación - renta exenta hasta 3.490 UVT (Art. 307 ET)",
     "POR_CONCILIAR", "Escritura de sucesión / documento de donación"),

    (["loteria", "rifa", "apuesta", "premio"],
     "Ganancia ocasional", "Loterías, rifas y apuestas tributan al 20% (Art. 317 ET), no se pueden depurar",
     "POR_CONCILIAR", "Certificado de pago del premio"),

    (["tope 1", "tope 2", "tope"],
     "Indicador de control DIAN", "Este valor es un INDICADOR AGREGADO usado por la DIAN para determinar el "
     "tope que originó la obligación de declarar (Art. 592-594-3 ET); NO es un concepto de ingreso "
     "individual. Debe conciliarse revisando el detalle real de la operación económica del "
     "contribuyente, ya que la exógena no desglosó el concepto específico.",
     "REQUIERE_SOPORTE", "Extractos bancarios, certificados de ingresos y demás soportes que expliquen "
     "el origen económico real de este valor"),
]


def clasificar_registro(detalle: str, uso_sugerido: str = "") -> dict:
    # 1) Prioridad: código de casilla que la propia DIAN sugiere (más confiable)
    por_casilla = _detectar_por_casilla_dian(uso_sugerido)
    if por_casilla:
        return por_casilla

    # 2) Reglas basadas en palabras clave del texto del concepto
    texto = _sin_tildes(f"{detalle} {uso_sugerido}")
    for palabras, cedula, tratamiento, estado, soporte in REGLAS:
        if any(_sin_tildes(p) in texto for p in palabras):
            return {
                "cedula_sugerida": cedula,
                "tratamiento_sugerido": tratamiento,
                "estado": estado,
                "soporte_requerido": soporte,
            }
    return {
        "cedula_sugerida": "Sin clasificar",
        "tratamiento_sugerido": "Concepto no reconocido automáticamente por el motor de reglas. "
        "Requiere análisis manual del usuario o del contador.",
        "estado": "POR_CONCILIAR",
        "soporte_requerido": "Por determinar según la naturaleza real de la operación",
    }


ESTADOS_LABELS = {
    "CONFIRMADO": "🟢 Confirmado",
    "POR_CONCILIAR": "🟡 Por conciliar",
    "NO_INGRESO": "⚪ No corresponde a ingreso",
    "REQUIERE_SOPORTE": "🟠 Requiere soporte",
    "OPORTUNIDAD": "🔵 Oportunidad tributaria",
    "NO_INCLUIR": "🔴 No incluir hasta verificar",
}
