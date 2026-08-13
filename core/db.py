# -*- coding: utf-8 -*-
"""
Capa de persistencia local (SQLite). Todo el almacenamiento ocurre en
./data/renta.db dentro de la carpeta del proyecto. No se envía información
a ningún servicio externo. Cada contribuyente se identifica por su
número de identificación + año gravable, lo que permite reutilizar la
herramienta para múltiples declaraciones sin tocar el código
("Nueva Declaración").
"""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "renta.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS contribuyentes (
    id TEXT PRIMARY KEY,              -- f"{tipo_doc}-{identificacion}-{anio}"
    anio_gravable INTEGER NOT NULL,
    tipo_documento TEXT,
    identificacion TEXT,
    nombre TEXT,
    residencia_fiscal TEXT,
    estado_civil TEXT,
    edad INTEGER,
    actividad_economica TEXT,
    perfil_json TEXT,                 -- resto de datos progresivos del perfil
    creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exogena_registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contribuyente_id TEXT NOT NULL,
    archivo_origen TEXT,
    nit_reportante TEXT,
    nombre_reportante TEXT,
    concepto TEXT,
    valor REAL,
    uso_sugerido TEXT,
    info_adicional TEXT,
    fila_excel INTEGER,
    hash_fila TEXT,
    FOREIGN KEY (contribuyente_id) REFERENCES contribuyentes(id)
);

CREATE TABLE IF NOT EXISTS conciliacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contribuyente_id TEXT NOT NULL,
    exogena_id INTEGER,
    tercero TEXT,
    concepto TEXT,
    valor REAL,
    cedula_sugerida TEXT,
    tratamiento_sugerido TEXT,
    estado TEXT,                       -- CONFIRMADO / POR CONCILIAR / NO_INGRESO / REQUIERE_SOPORTE / OPORTUNIDAD / NO_INCLUIR
    estado_usuario TEXT,               -- override manual del usuario, si aplica
    pertenece_contribuyente INTEGER DEFAULT 1,
    ya_incluido_en TEXT,
    soporte_requerido TEXT,
    notas TEXT,
    FOREIGN KEY (contribuyente_id) REFERENCES contribuyentes(id)
);

CREATE TABLE IF NOT EXISTS patrimonio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contribuyente_id TEXT NOT NULL,
    tipo TEXT,                         -- ACTIVO / PASIVO
    categoria TEXT,
    descripcion TEXT,
    valor REAL,
    origen TEXT,                       -- USUARIO / EXOGENA
    FOREIGN KEY (contribuyente_id) REFERENCES contribuyentes(id)
);

CREATE TABLE IF NOT EXISTS deducciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contribuyente_id TEXT NOT NULL,
    beneficio TEXT,
    valor_potencial REAL,
    limite_aplicable TEXT,
    documento_requerido TEXT,
    soportado INTEGER DEFAULT 0,
    valor_utilizado REAL DEFAULT 0,
    notas TEXT,
    FOREIGN KEY (contribuyente_id) REFERENCES contribuyentes(id)
);

CREATE TABLE IF NOT EXISTS checklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contribuyente_id TEXT NOT NULL,
    item TEXT,
    completo INTEGER DEFAULT 0,
    critico INTEGER DEFAULT 0,
    notas TEXT,
    FOREIGN KEY (contribuyente_id) REFERENCES contribuyentes(id)
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def contribuyente_id(tipo_documento: str, identificacion: str, anio: int) -> str:
    ident_limpia = "".join(ch for ch in str(identificacion) if ch.isalnum())
    return f"{tipo_documento}-{ident_limpia}-{anio}"


def upsert_contribuyente(cid: str, **campos):
    with get_conn() as conn:
        existe = conn.execute(
            "SELECT id FROM contribuyentes WHERE id=?", (cid,)
        ).fetchone()
        tiene_perfil_extra = "perfil_extra" in campos
        perfil_extra = campos.pop("perfil_extra", None)
        if existe:
            sets_parts = [f"{k}=?" for k in campos]
            valores = list(campos.values())
            if tiene_perfil_extra:
                sets_parts.append("perfil_json=?")
                valores.append(json.dumps(perfil_extra, ensure_ascii=False))
            sets_parts.append("actualizado_en=CURRENT_TIMESTAMP")
            valores.append(cid)
            sets = ", ".join(sets_parts)
            conn.execute(
                f"UPDATE contribuyentes SET {sets} WHERE id=?",
                valores,
            )
        else:
            campos["id"] = cid
            campos["perfil_json"] = json.dumps(perfil_extra or {}, ensure_ascii=False)
            cols = ", ".join(campos.keys())
            qs = ", ".join("?" for _ in campos)
            conn.execute(
                f"INSERT INTO contribuyentes ({cols}) VALUES ({qs})",
                list(campos.values()),
            )


def listar_contribuyentes():
    with get_conn() as conn:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM contribuyentes ORDER BY actualizado_en DESC"
            ).fetchall()
        ]


def obtener_contribuyente(cid: str):
    with get_conn() as conn:
        r = conn.execute(
            "SELECT * FROM contribuyentes WHERE id=?", (cid,)
        ).fetchone()
        return dict(r) if r else None


def eliminar_contribuyente(cid: str):
    """Elimina de forma segura todos los datos de un contribuyente (RGPD-like)."""
    with get_conn() as conn:
        for tabla in [
            "exogena_registros",
            "conciliacion",
            "patrimonio",
            "deducciones",
            "checklist",
        ]:
            conn.execute(f"DELETE FROM {tabla} WHERE contribuyente_id=?", (cid,))
        conn.execute("DELETE FROM contribuyentes WHERE id=?", (cid,))
