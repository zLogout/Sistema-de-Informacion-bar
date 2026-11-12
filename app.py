from flask import Flask, render_template, jsonify
# Si ya tienes funciones hechas en conexion_db.py, puedes importarlas aquí:
from conexion_db import crear_tablas, cargar_carta, conectar, crear_reserva, listar_carta, listar_reservas 

app = Flask(__name__)

@app.route('/')
def home():
    # Renderiza tu página principal ubicada en la carpeta 'templates'
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)