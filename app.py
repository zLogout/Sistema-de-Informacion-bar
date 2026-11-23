import re
from calendar import monthrange
from datetime import date, time, timedelta

from flask import Flask, abort, render_template, request, redirect, url_for, session
from conexion_db import (
    crear_tablas, cargar_carta, conectar, crear_reserva, listar_carta, listar_reservas_clientes,
    crear_admin_por_defecto, verificar_usuario, listar_productos_admin, listar_categorias,
    agregar_producto, editar_producto, eliminar_producto
)

app = Flask(__name__, static_folder="public", static_url_path="")
app.secret_key = "clave_super_secreta_del_bar"


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
