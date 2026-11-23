import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

CARTA = {
    "Cervezas": ["Cerveza nacional", "Cerveza importada", "Cerveza artesanal"],
    "Cócteles": ["Cóctel de la casa", "Clásico de barra", "Cóctel sin alcohol"],
    "Licores": ["Aguardiente", "Ron", "Whisky", "Tequila"],
    "Botellas y combos": ["Botella para la mesa", "Combo para grupos"],
}


def conectar():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Falta la variable de entorno DATABASE_URL.")
    return psycopg.connect(url, row_factory=dict_row)


def crear_tablas(conn):
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    for statement in schema.split(";"):
        if statement.strip():
            conn.execute(statement)
    conn.commit()


def cargar_carta(conn):
    for categoria, productos in CARTA.items():
        conn.execute(
            "INSERT INTO categorias(nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING",
            (categoria,),
        )
        cat_id = conn.execute(
            "SELECT id FROM categorias WHERE nombre = %s", (categoria,)
        ).fetchone()["id"]
        for nombre in productos:
            conn.execute(
                "INSERT INTO productos(categoria_id, nombre) VALUES (%s, %s) "
                "ON CONFLICT (categoria_id, nombre) DO NOTHING",
                (cat_id, nombre),
            )
    conn.commit()


def listar_carta(conn):
    sql = """
    SELECT c.nombre AS categoria, p.nombre AS producto,
           p.precio::float AS precio, p.stock
    FROM productos p JOIN categorias c ON c.id = p.categoria_id
    ORDER BY c.id, p.id
    """
    return conn.execute(sql).fetchall()


def crear_reserva(conn, nombre, whatsapp, fecha, hora, personas):
    fila = conn.execute(
        "INSERT INTO reservas(nombre, whatsapp, fecha, hora, personas) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (nombre, whatsapp, fecha, hora, personas),
    ).fetchone()
    conn.commit()
    return fila["id"]


def listar_reservas(conn):
    return conn.execute("SELECT * FROM reservas ORDER BY fecha, hora").fetchall()


def listar_reservas_clientes(conn, fecha_inicio=None, fecha_fin=None):
    if fecha_inicio is None and fecha_fin is None:
        return conn.execute(
            "SELECT nombre, whatsapp, fecha, hora, personas, estado "
            "FROM reservas ORDER BY fecha DESC, hora DESC, id DESC"
        ).fetchall()

    return conn.execute(
        "SELECT nombre, whatsapp, fecha, hora, personas, estado "
        "FROM reservas WHERE fecha >= %s AND fecha <= %s "
        "ORDER BY fecha DESC, hora DESC, id DESC",
        (fecha_inicio, fecha_fin),
    ).fetchall()


# --- FUNCIONES DE USUARIOS / ADMIN ---
def crear_admin_por_defecto(conn):
    # Crea un usuario admin inicial si no existe
    conn.execute(
        "INSERT INTO usuarios (username, password, rol) VALUES (%s, %s, %s) ON CONFLICT (username) DO NOTHING",
        ("admin", "admin123", "admin")
    )
    conn.commit()

def verificar_usuario(conn, username, password):
    return conn.execute(
        "SELECT * FROM usuarios WHERE username = %s AND password = %s",
        (username, password)
    ).fetchone()

# --- FUNCIONES CRUD DE PRODUCTOS ---
def listar_productos_admin(conn):
    sql = """
    SELECT p.id, c.id AS categoria_id, c.nombre AS categoria, p.nombre, p.precio::float AS precio, p.stock
    FROM productos p
    JOIN categorias c ON c.id = p.categoria_id
    ORDER BY p.id ASC
    """
    return conn.execute(sql).fetchall()

def listar_categorias(conn):
    return conn.execute("SELECT * FROM categorias ORDER BY id ASC").fetchall()

def agregar_producto(conn, categoria_id, nombre, precio, stock):
    conn.execute(
        "INSERT INTO productos (categoria_id, nombre, precio, stock) VALUES (%s, %s, %s, %s)",
        (categoria_id, nombre, precio, stock)
    )
    conn.commit()

def editar_producto(conn, producto_id, categoria_id, nombre, precio, stock):
    conn.execute(
        """UPDATE productos 
           SET categoria_id = %s, nombre = %s, precio = %s, stock = %s 
           WHERE id = %s""",
        (categoria_id, nombre, precio, stock, producto_id)
    )
    conn.commit()

def eliminar_producto(conn, producto_id):
    conn.execute("DELETE FROM productos WHERE id = %s", (producto_id,))
    conn.commit()
if __name__ == "__main__":
    with conectar() as conn:
        crear_tablas(conn)
        cargar_carta(conn)
        crear_admin_por_defecto(conn)
        print("Conexión exitosa a Neon. Carta:")
        for fila in listar_carta(conn):
            print(f"  {fila['categoria']:<18} {fila['producto']:<24} ${fila['precio']:,.0f}")
        print("Reservas:", len(listar_reservas(conn)))
