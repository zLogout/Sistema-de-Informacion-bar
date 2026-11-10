from flask import Flask, render_template, jsonify
# Si ya tienes funciones hechas en conexion_db.py, puedes importarlas aquí:
from conexion_db import crear_tablas, cargar_carta, conectar, crear_reserva, listar_carta, listar_reservas 

app = Flask(__name__)

@app.route('/')
def home():
    # Renderiza tu página principal ubicada en la carpeta 'templates'
    return render_template('index.html')

# Ejemplo de una ruta API para que tu JavaScript consulte datos de SQLite en el futuro
@app.route('/api/inventario', methods=['GET'])
def api_inventario():
    # Aquí llamarías a tu lógica de Python/SQLite (ej. consultar la BD)
    # datos = obtener_inventario()
    
    # Por ahora, un ejemplo de prueba:
    datos_ejemplo = [{"producto": "Cerveza", "stock": 24, "precio": 5.00}]
    return jsonify(datos_ejemplo)

if __name__ == '__main__':
    app.run(debug=True)