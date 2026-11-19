from flask import Flask, render_template, request, redirect, url_for, session
from conexion_db import (
    crear_tablas, cargar_carta, conectar, crear_reserva, listar_carta, listar_reservas,
    verificar_usuario, listar_productos_admin, listar_categorias,
    agregar_producto, editar_producto, eliminar_producto
)

app = Flask(__name__)
app.secret_key = "clave_super_secreta_del_bar"

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/reservas", methods=["GET"])
def mostrar_reservas():
    return render_template("reservas.html")

@app.route("/reservas", methods=["POST"])
def guardar_reserva():
    None

# --- RUTAS DE INICIO DE SESIÓN ---
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        with conectar() as conn:
            usuario = verificar_usuario(conn, username, password)
            
        if usuario:
            session["usuario_id"] = usuario["id"]
            session["username"] = usuario["username"]
            session["rol"] = usuario["rol"]
            return redirect(url_for("panel_admin"))
        else:
            error = "Usuario o contraseña incorrectos."
            
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
