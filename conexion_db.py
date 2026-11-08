"""Conexión de Python con la base de datos SQLite del bar (Corredor Ecológico, Villavicencio)."""
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent
DB_PATH = BASE / "bar.db"
SCHEMA_PATH = BASE / "schema.sql"

# Misma carta de la landing page. Los precios están en 0: complétalos con los reales.
CARTA = {
    "Cervezas": ["Cerveza nacional", "Cerveza importada", "Cerveza artesanal"],
    "Cócteles": ["Cóctel de la casa", "Clásico de barra", "Cóctel sin alcohol"],
    "Licores": ["Aguardiente", "Ron", "Whisky", "Tequila"],
    "Botellas y combos": ["Botella para la mesa", "Combo para grupos"],
}


def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def crear_tablas(conn):
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def cargar_carta(conn):
    for categoria, productos in CARTA.items():
        conn.execute("INSERT OR IGNORE INTO categorias(nombre) VALUES (?)", (categoria,))
        cat_id = conn.execute("SELECT id FROM categorias WHERE nombre = ?", (categoria,)).fetchone()["id"]
        for nombre in productos:
            conn.execute(
                "INSERT OR IGNORE INTO productos(categoria_id, nombre) VALUES (?, ?)",
                (cat_id, nombre),
            )
    conn.commit()


def listar_carta(conn):
    sql = """
    SELECT c.nombre AS categoria, p.nombre AS producto, p.precio, p.stock
    FROM productos p JOIN categorias c ON c.id = p.categoria_id
    ORDER BY c.id, p.id
    """
    return conn.execute(sql).fetchall()


def crear_reserva(conn, nombre, whatsapp, fecha, hora, personas):
    cur = conn.execute(
        "INSERT INTO reservas(nombre, whatsapp, fecha, hora, personas) VALUES (?,?,?,?,?)",
        (nombre, whatsapp, fecha, hora, personas),
    )
    conn.commit()
    return cur.lastrowid


def listar_reservas(conn):
    return conn.execute("SELECT * FROM reservas ORDER BY fecha, hora").fetchall()


if __name__ == "__main__":
    with conectar() as conn:
        crear_tablas(conn)
        cargar_carta(conn)
        if not listar_reservas(conn):
            crear_reserva(conn, "Cliente de prueba", "3001234567", "2026-11-14", "20:00", 6)
        print("Conexión exitosa. Carta:")
        for fila in listar_carta(conn):
            print(f"  {fila['categoria']:<18} {fila['producto']:<24} ${fila['precio']:,.0f}")
        print("Reservas:")
        for fila in listar_reservas(conn):
            print(" ", dict(fila))
