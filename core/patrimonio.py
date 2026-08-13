# -*- coding: utf-8 -*-
"""Cálculo de patrimonio bruto, deudas y patrimonio líquido a 31/12/2025."""
from core.db import get_conn

CATEGORIAS_ACTIVO = [
    "Efectivo",
    "Cuentas bancarias (ahorro/corriente)",
    "CDT y otras inversiones de renta fija",
    "Acciones y aportes en sociedades",
    "Inmuebles",
    "Vehículos",
    "Derechos fiduciarios / cuentas por cobrar",
    "Otros activos",
]

CATEGORIAS_PASIVO = [
    "Obligaciones financieras (bancos)",
    "Préstamos particulares",
    "Otras deudas",
]


def guardar_item(contribuyente_id: str, tipo: str, categoria: str, descripcion: str, valor: float, origen: str = "USUARIO"):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO patrimonio (contribuyente_id, tipo, categoria, descripcion, valor, origen) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (contribuyente_id, tipo, categoria, descripcion, valor, origen),
        )


def eliminar_item(item_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM patrimonio WHERE id=?", (item_id,))


def listar_items(contribuyente_id: str, tipo: str | None = None):
    with get_conn() as conn:
        if tipo:
            rows = conn.execute(
                "SELECT * FROM patrimonio WHERE contribuyente_id=? AND tipo=? ORDER BY categoria",
                (contribuyente_id, tipo),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM patrimonio WHERE contribuyente_id=? ORDER BY tipo, categoria",
                (contribuyente_id,),
            ).fetchall()
        return [dict(r) for r in rows]


def calcular_patrimonio(contribuyente_id: str) -> dict:
    activos = listar_items(contribuyente_id, "ACTIVO")
    pasivos = listar_items(contribuyente_id, "PASIVO")
    patrimonio_bruto = sum(a["valor"] or 0 for a in activos)
    deudas = sum(p["valor"] or 0 for p in pasivos)
    return {
        "activos": activos,
        "pasivos": pasivos,
        "patrimonio_bruto": patrimonio_bruto,
        "deudas": deudas,
        "patrimonio_liquido": patrimonio_bruto - deudas,
        "formula": "Patrimonio bruto (activos) - Deudas = Patrimonio líquido",
        "norma": "Art. 261 y 282 Estatuto Tributario",
    }
