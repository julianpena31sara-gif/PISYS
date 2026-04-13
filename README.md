# 📦 PISYS — Sistema de Gestión de Inventario

> Proyecto académico desarrollado en Python + Flask + SQLite  
> Plan de 16 semanas | Tecnología en Desarrollo de Software

---

## 🚀 Cómo correr el proyecto (Semanas 1–3)

### 1. Requisitos previos
- Python 3.11 o superior instalado
- Visual Studio Code con la extensión **Python** (Microsoft)

### 2. Abrir el proyecto en VS Code
```
File → Open Folder → Seleccionar la carpeta "inventario"
```

### 3. Crear el entorno virtual
Abre la terminal en VS Code (`Ctrl + ñ` en Windows / `Ctrl + \`` en Mac):

```bash
# Crear el entorno virtual
python -m venv venv

# Activarlo en Windows:
venv\Scripts\activate

# Activarlo en Mac/Linux:
source venv/bin/activate
```

> ✅ Sabes que está activo cuando ves `(venv)` al inicio de la línea

### 4. Instalar las dependencias
```bash
pip install -r requirements.txt
```

### 5. Crear la base de datos y cargar datos de prueba
```bash
python seed.py
```

### 6. Correr la aplicación
```bash
python app.py
```

### 7. Abrir en el navegador
```
http://localhost:5000
```

---

## 📁 Estructura del proyecto

```
inventario/
│
├── app.py              ← Punto de entrada principal (Flask + rutas)
├── seed.py             ← Script para cargar datos de prueba
├── requirements.txt    ← Librerías necesarias
├── README.md           ← Este archivo
│
├── templates/          ← Páginas HTML (Jinja2)
│   ├── base.html       ← Plantilla base con navbar
│   ├── inicio.html     ← Panel de control con KPIs y alertas
│   ├── productos.html  ← Lista de productos
│   ├── dashboard.html  ← Dashboard (Semana 10)
│   └── reportes.html   ← Reportes PDF (Semana 7)
│
├── static/             ← Archivos estáticos (CSS, JS, imágenes)
│   ├── css/
│   │   └── estilos.css ← Estilos personalizados
│   └── js/
│       └── main.js     ← JavaScript del sistema
│
└── instance/           ← Creada automáticamente por Flask
    └── inventario.db   ← Base de datos SQLite (NO subir a git)
```

---

## 🗓️ Plan de desarrollo — 11 semanas


| ✅ Bases | Entorno, BD, HTML base |
| 🔄 CRUD | Crear, editar, eliminar productos + alertas |
| ⏳ Reportes | PDF con ReportLab |
| ⏳ Dashboard | Gráficos Plotly + alertas predictivas |

---

## 🛠️ Tecnologías usadas

- **Python 3.11+** — Lenguaje principal
- **Flask** — Framework web
- **SQLAlchemy** — ORM para la base de datos
- **SQLite** — Base de datos (archivo local)
- **Bootstrap 5** — Diseño responsive
- **ReportLab** — Generación de PDF (Semana 7)
- **Plotly** — Gráficos interactivos (Semana 10)

---

## ⚠️ Archivos que NO debes subir a git

Crea un archivo `.gitignore` con este contenido:

```
venv/
instance/
__pycache__/
*.pyc
.env
```

---

## 💡 Comandos útiles

```bash
# Ver la base de datos en VS Code
# Instala la extensión "SQLite Viewer" y haz clic en instance/inventario.db

# Reiniciar la base de datos desde cero:
# 1. Borra el archivo instance/inventario.db
# 2. Vuelve a correr: python seed.py

# Si agregas un nuevo paquete:
pip install nombre-paquete
pip freeze > requirements.txt  # Actualiza el archivo de dependencias
```
