import csv
import re
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO, StringIO
import zipfile

from flask import Flask, abort, render_template, request, redirect, url_for, session, send_file
from conexion_db import (
    crear_tablas, cargar_carta, conectar, crear_reserva, listar_carta, listar_reservas_clientes,
    crear_admin_por_defecto, verificar_usuario, listar_productos_admin, listar_categorias,
    agregar_producto, editar_producto, eliminar_producto
)

app = Flask(__name__, static_folder="public", static_url_path="")
app.secret_key = "clave_super_secreta_del_bar"

EXPORT_TABLES = {
    "categorias": (
        ("id", "nombre"),
        "CREATE TABLE `categorias` (`id` INT NOT NULL AUTO_INCREMENT, `nombre` VARCHAR(255) NOT NULL, PRIMARY KEY (`id`), UNIQUE KEY `uq_categorias_nombre` (`nombre`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;",
    ),
    "productos": (
        ("id", "categoria_id", "nombre", "precio", "stock"),
        "CREATE TABLE `productos` (`id` INT NOT NULL AUTO_INCREMENT, `categoria_id` INT NOT NULL, `nombre` VARCHAR(255) NOT NULL, `precio` DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (`precio` >= 0), `stock` INT NOT NULL DEFAULT 0 CHECK (`stock` >= 0), PRIMARY KEY (`id`), UNIQUE KEY `uq_productos_categoria_nombre` (`categoria_id`, `nombre`), CONSTRAINT `fk_productos_categoria` FOREIGN KEY (`categoria_id`) REFERENCES `categorias` (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;",
    ),
    "promociones": (
        ("id", "titulo", "descripcion", "dias", "horario", "activa"),
        "CREATE TABLE `promociones` (`id` INT NOT NULL AUTO_INCREMENT, `titulo` VARCHAR(255) NOT NULL, `descripcion` TEXT NULL, `dias` TEXT NULL, `horario` TEXT NULL, `activa` BOOLEAN NOT NULL DEFAULT TRUE, PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;",
    ),
    "reservas": (
        ("id", "nombre", "whatsapp", "fecha", "hora", "personas", "estado"),
        "CREATE TABLE `reservas` (`id` INT NOT NULL AUTO_INCREMENT, `nombre` VARCHAR(255) NOT NULL, `whatsapp` VARCHAR(255) NOT NULL, `fecha` VARCHAR(10) NOT NULL, `hora` VARCHAR(5) NOT NULL, `personas` INT NOT NULL CHECK (`personas` > 0), `estado` VARCHAR(50) NOT NULL DEFAULT 'Pendiente' CHECK (`estado` IN ('Pendiente','Confirmada','Cancelada')), PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;",
    ),
    "ventas": (
        ("id", "fecha_hora", "total"),
        "CREATE TABLE `ventas` (`id` INT NOT NULL AUTO_INCREMENT, `fecha_hora` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, `total` DECIMAL(10,2) NOT NULL DEFAULT 0, PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;",
    ),
    "usuarios": (
        ("id", "username", "password", "rol"),
        "CREATE TABLE `usuarios` (`id` INT NOT NULL AUTO_INCREMENT, `username` VARCHAR(255) NOT NULL, `password` VARCHAR(255) NOT NULL, `rol` VARCHAR(50) NOT NULL DEFAULT 'admin', PRIMARY KEY (`id`), UNIQUE KEY `uq_usuarios_username` (`username`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;",
    ),
    "detalle_venta": (
        ("id", "venta_id", "producto_id", "cantidad", "precio_unitario"),
        "CREATE TABLE `detalle_venta` (`id` INT NOT NULL AUTO_INCREMENT, `venta_id` INT NOT NULL, `producto_id` INT NOT NULL, `cantidad` INT NOT NULL CHECK (`cantidad` > 0), `precio_unitario` DECIMAL(10,2) NOT NULL, PRIMARY KEY (`id`), CONSTRAINT `fk_detalle_venta_venta` FOREIGN KEY (`venta_id`) REFERENCES `ventas` (`id`), CONSTRAINT `fk_detalle_venta_producto` FOREIGN KEY (`producto_id`) REFERENCES `productos` (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;",
    ),
}


def normalizar_whatsapp(valor):
    valor = valor.strip()
    if not valor:
        return ""
    if not re.fullmatch(r"\+?[\d\s().-]+", valor):
        return None

    digitos = re.sub(r"\D", "", valor)
    if not 7 <= len(digitos) <= 15:
        return None
    return ("+" if valor.startswith("+") else "") + digitos


@app.route('/')
def home():
    with conectar() as conn:
        carta = listar_carta(conn)
    return render_template('index.html', carta=carta)

@app.route("/reservas", methods=["GET"])
def mostrar_reservas():
    return render_template(
        "reservas.html",
        error=None,
        reservada=request.args.get("reservada") == "1",
    )

@app.route("/reservas", methods=["POST"])
def guardar_reserva():
    nombre = request.form.get("nombre", "").strip()
    whatsapp = request.form.get("whatsapp", "").strip()
    fecha_ingresada = request.form.get("fecha", "")
    hora_ingresada = request.form.get("hora", "")
    personas_ingresadas = request.form.get("personas", "")

    if not nombre:
        return render_template(
            "reservas.html",
            error="Escribe tu nombre para continuar.",
            reservada=False,
        )

    whatsapp = normalizar_whatsapp(whatsapp)
    if whatsapp is None:
        return render_template(
            "reservas.html",
            error="El WhatsApp debe ser un número válido de 7 a 15 dígitos.",
            reservada=False,
        )

    try:
        fecha = date.fromisoformat(fecha_ingresada).isoformat()
        hora = time.fromisoformat(hora_ingresada).strftime("%H:%M")
        personas = int(personas_ingresadas)
        if personas < 1:
            raise ValueError
    except ValueError:
        return render_template(
            "reservas.html",
            error="Revisa la fecha, la hora y el número de personas.",
            reservada=False,
        )

    with conectar() as conn:
        crear_reserva(conn, nombre, whatsapp, fecha, hora, personas)

    return redirect(url_for("mostrar_reservas", reservada=1))

# --- RUTAS DE INICIO DE SESIÓN ---
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            with conectar() as conn:
                crear_tablas(conn)
                crear_admin_por_defecto(conn)
                usuario = verificar_usuario(conn, username, password)
                if usuario:
                    cargar_carta(conn)

            if usuario:
                session["usuario_id"] = usuario["id"]
                session["username"] = usuario["username"]
                session["rol"] = usuario["rol"]
                return redirect(url_for("panel_admin"))
            else:
                error = "Usuario o contraseña incorrectos."
        except Exception as e:
            error = f"Error de conexión con la base de datos: {e}"

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# --- PANEL ADMINISTRADOR (CRUD PRODUCTOS) ---
@app.route("/admin")
def panel_admin():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
        
    with conectar() as conn:
        productos = listar_productos_admin(conn)
        categorias = listar_categorias(conn)
        
    return render_template("admin.html", productos=productos, categorias=categorias)


def _mysql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, (date, datetime, time)):
        value = value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    escaped = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{escaped}'"


@app.route("/admin/exportar/<formato>")
def exportar_datos(formato):
    if "usuario_id" not in session or session.get("rol") != "admin":
        return redirect(url_for("login"))
    if formato not in {"sql", "csv"}:
        abort(404)

    with conectar() as conn:
        datos = {}
        for tabla, (columnas, _) in EXPORT_TABLES.items():
            seleccion = ", ".join(f'"{columna}"' for columna in columnas)
            datos[tabla] = conn.execute(
                f'SELECT {seleccion} FROM "{tabla}" ORDER BY "id"'
            ).fetchall()

    if formato == "sql":
        lineas = [
            "-- Exportación para MySQL 8.0 o posterior",
            "SET NAMES utf8mb4;",
        ]
        lineas.extend(ddl for _, ddl in EXPORT_TABLES.values())
        for tabla, (columnas, _) in EXPORT_TABLES.items():
            for fila in datos[tabla]:
                valores = ", ".join(_mysql_literal(fila[columna]) for columna in columnas)
                campos = ", ".join(f"`{columna}`" for columna in columnas)
                lineas.append(f"INSERT INTO `{tabla}` ({campos}) VALUES ({valores});")
        contenido = "\n".join(lineas) + "\n"
        return send_file(
            BytesIO(contenido.encode("utf-8")),
            mimetype="application/sql",
            as_attachment=True,
            download_name="respaldo_bar_mysql.sql",
        )

    archivo = BytesIO()
    with zipfile.ZipFile(archivo, "w", zipfile.ZIP_DEFLATED) as comprimido:
        for tabla, (columnas, _) in EXPORT_TABLES.items():
            texto = StringIO(newline="")
            escritor = csv.DictWriter(texto, fieldnames=columnas)
            escritor.writeheader()
            escritor.writerows(datos[tabla])
            comprimido.writestr(f"{tabla}.csv", "\ufeff" + texto.getvalue())
    archivo.seek(0)
    return send_file(
        archivo,
        mimetype="application/zip",
        as_attachment=True,
        download_name="respaldo_bar_csv.zip",
    )


@app.route("/admin/clientes")
def modulo_clientes():
    if "usuario_id" not in session or session.get("rol") != "admin":
        return redirect(url_for("login"))

    periodo = request.args.get("periodo", "todos")
    hoy = date.today()
    rangos = {
        "semana": (
            hoy - timedelta(days=hoy.weekday()),
            hoy - timedelta(days=hoy.weekday()) + timedelta(days=6),
            "Semana actual",
        ),
        "mes": (
            hoy.replace(day=1),
            hoy.replace(day=monthrange(hoy.year, hoy.month)[1]),
            "Mes actual",
        ),
        "año": (
            hoy.replace(month=1, day=1),
            hoy.replace(month=12, day=31),
            "Año actual",
        ),
        "todos": (None, None, "Todo el historial"),
    }
    if periodo not in rangos:
        abort(400)

    fecha_inicio, fecha_fin, periodo_nombre = rangos[periodo]
    with conectar() as conn:
        reservas = listar_reservas_clientes(
            conn,
            fecha_inicio.isoformat() if fecha_inicio else None,
            fecha_fin.isoformat() if fecha_fin else None,
        )

    clientes_por_whatsapp = {}
    for reserva in reservas:
        whatsapp = normalizar_whatsapp(reserva["whatsapp"] or "")
        if whatsapp is None:
            clave_cliente = f"registro-{reserva['id']}"
            whatsapp_mostrado = "Dato no válido"
        elif not whatsapp:
            clave_cliente = f"registro-{reserva['id']}"
            whatsapp_mostrado = "No proporcionado"
        else:
            clave_cliente = whatsapp
            whatsapp_mostrado = whatsapp

        cliente = clientes_por_whatsapp.get(clave_cliente)
        if cliente is None:
            cliente = {
                "nombre": reserva["nombre"],
                "whatsapp": whatsapp_mostrado,
                "reservas": 0,
                "ultima_visita": reserva["fecha"],
                "personas": 0,
            }
            clientes_por_whatsapp[clave_cliente] = cliente
        cliente["reservas"] += 1
        cliente["personas"] += reserva["personas"]

    clientes = list(clientes_por_whatsapp.values())
    return render_template(
        "clientes.html",
        clientes=clientes,
        periodo=periodo,
        periodo_nombre=periodo_nombre,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        total_reservas=len(reservas),
        total_personas=sum(reserva["personas"] for reserva in reservas),
    )


@app.route("/admin/productos/agregar", methods=["POST"])
def ruta_agregar_producto():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
        
    categoria_id = request.form.get("categoria_id")
    nombre = request.form.get("nombre")
    precio = request.form.get("precio")
    stock = request.form.get("stock")
    
    with conectar() as conn:
        agregar_producto(conn, categoria_id, nombre, precio, stock)
        
    return redirect(url_for("panel_admin"))

@app.route("/admin/productos/editar/<int:id>", methods=["POST"])
def ruta_editar_producto(id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))
        
    categoria_id = request.form.get("categoria_id")
    nombre = request.form.get("nombre")
    precio = request.form.get("precio")
    stock = request.form.get("stock")
    
    with conectar() as conn:
        editar_producto(conn, id, categoria_id, nombre, precio, stock)
        
    return redirect(url_for("panel_admin"))

@app.route("/admin/productos/eliminar/<int:id>", methods=["POST"])
def ruta_eliminar_producto(id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))
        
    with conectar() as conn:
        eliminar_producto(conn, id)
        
    return redirect(url_for("panel_admin"))

if __name__ == '__main__':
    app.run(debug=True)
