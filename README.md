
¡Bienvenido! Este proyecto es una aplicación web para que los clientes conozcan el bar y puedan iniciar una reserva en línea. 🚀

## ✨ ¿Qué tiene?

- 🏠 Página principal con información del bar.
- 🍹 Sección para mostrar la carta.
- 🎉 Espacio para promociones.
- 📍 Información de ubicación y contacto.
- 🪑 Página con formulario para solicitar una reserva.


## 🛠️ Tecnologías

- 🐍 Python
- 🌶️ Flask
- 🎨 HTML,CSS & JavaScript
- ▲ Vercel para el despliegue

## 📂 Estructura del proyecto

```text
.
├── app.py
├── conexion_db.py
├── requirements.txt
├── pyproject.toml
├── schema.sql
├── public/
│   └── css/js/
│       ├── styles.css
│       └── script.js
└── templates/
    ├── index.html
    └── reservas.html
```

## 💻 Cómo ejecutarlo localmente

1. Crea un entorno virtual:

   ```bash
   python -m venv .venv
   ```

2. Actívalo en Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Inicia la aplicación:

   ```bash
   python app.py
   ```

5. Abre en el navegador: [http://127.0.0.1:5000](http://127.0.0.1:5000) 🎊

## 🔗 Rutas principales

- `GET /` — muestra la página principal.
- `GET /reservas` — muestra el formulario de reservas.
- `POST /reservas` — ruta preparada para recibir los datos del formulario.

