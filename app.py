# ============================================================
# app.py — Punto de entrada principal del sistema
# ============================================================
# Aquí vive TODO el "cerebro" de la aplicación.
# Flask es el framework que recibe peticiones del navegador
# y decide qué responder. SQLAlchemy es el "traductor" que
# convierte objetos Python en filas de la base de datos.
# ============================================================

from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# ------ CONFIGURACIÓN DE LA APP ------

# Flask(__name__) le dice a Flask dónde está el proyecto
# para que encuentre las carpetas templates/ y static/
app = Flask(__name__)

# SECRET_KEY se usa para cifrar las sesiones y mensajes flash.
# En producción real usarías algo más seguro, pero para
# aprender esto funciona perfecto.
app.config['SECRET_KEY'] = 'clave-super-secreta-cambiala-en-produccion'

# La base de datos SQLite se guarda en la carpeta instance/
# que Flask crea automáticamente. No la metas en git.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventario.db'

# Esto desactiva un aviso molesto de SQLAlchemy
# que no necesitamos para aprender
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# db es el objeto que usaremos en TODA la app para hablar
# con la base de datos. Se conecta con la app de Flask.
db = SQLAlchemy(app)


# ------ MODELOS (TABLAS DE LA BASE DE DATOS) ------

# Cada clase que hereda de db.Model se convierte en una tabla.
# Los atributos db.Column(...) son las columnas de esa tabla.

class Producto(db.Model):
    """
    Tabla 'producto' en la base de datos.
    Guarda toda la información de cada producto del inventario.
    """
    # Nombre de la tabla en SQLite (opcional, Flask lo genera solo)
    __tablename__ = 'producto'

    # Clave primaria: identificador único, se auto-incrementa (1, 2, 3...)
    id = db.Column(db.Integer, primary_key=True)

    # Nombre del producto — obligatorio (nullable=False)
    nombre = db.Column(db.String(100), nullable=False)

    # Descripción opcional — puede estar vacía
    descripcion = db.Column(db.Text, nullable=True)

    # Precio con decimales (Ej: 15.99)
    precio = db.Column(db.Float, nullable=False, default=0.0)

    # Cantidad en stock — cuántas unidades hay
    cantidad = db.Column(db.Integer, nullable=False, default=0)

    # Categoría para agrupar productos (Electronics, Ropa, etc.)
    categoria = db.Column(db.String(50), nullable=True, default='General')

    # Fecha en que se agregó el producto — se pone automáticamente
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # __repr__ define cómo se ve el objeto en la consola de Python
    # Es solo para depuración, no afecta la app
    def __repr__(self):
        return f'<Producto {self.nombre} | Stock: {self.cantidad}>'

    def estado_stock(self):
        """
        Devuelve el estado del stock para mostrar colores en la interfaz.
        - 'critico'  → menos de 5 unidades  (rojo)
        - 'bajo'     → menos de 10 unidades  (amarillo)
        - 'normal'   → 10 o más unidades     (verde)
        """
        if self.cantidad < 5:
            return 'critico'
        elif self.cantidad < 10:
            return 'bajo'
        return 'normal'

    def valor_total(self):
        """
        Calcula el valor total del stock de este producto.
        Ej: 50 unidades × $15.99 = $799.50
        """
        return self.precio * self.cantidad


# ------ RUTAS (PÁGINAS DE LA APP) ------

# Una "ruta" es la URL que escribe el usuario en el navegador.
# @app.route('/') significa "cuando alguien vaya a localhost:5000/"
# ejecuta la función que está abajo.

@app.route('/')
def inicio():
    """
    Página principal del sistema.
    Muestra un resumen del inventario: totales, alertas, etc.
    """
    # Contamos cuántos productos hay en total
    total_productos = Producto.query.count()

    # Buscamos productos con stock CRÍTICO (menos de 5 unidades)
    # .filter() es como el WHERE en SQL
    # .all() trae todos los resultados como lista
    alertas_criticas = Producto.query.filter(Producto.cantidad < 5).all()

    # Buscamos productos con stock BAJO (entre 5 y 9 unidades)
    alertas_bajas = Producto.query.filter(
        Producto.cantidad >= 5,
        Producto.cantidad < 10
    ).all()

    # Calculamos el valor total del inventario completo
    # Sumamos precio×cantidad de cada producto
    todos_los_productos = Producto.query.all()
    valor_total_inventario = sum(p.valor_total() for p in todos_los_productos)

    # render_template() busca el archivo en la carpeta templates/
    # y le pasa las variables como parámetros nombrados
    return render_template(
        'inicio.html',
        total_productos=total_productos,
        alertas_criticas=alertas_criticas,
        alertas_bajas=alertas_bajas,
        valor_total_inventario=valor_total_inventario
    )


@app.route('/productos')
def lista_productos():
    buscar    = request.args.get('buscar', '').strip()
    categoria = request.args.get('categoria', '')
    pagina    = request.args.get('pagina', 1, type=int)
    POR_PAGINA = 10

    consulta = Producto.query

    if buscar:
        consulta = consulta.filter(Producto.nombre.ilike(f'%{buscar}%'))

    if categoria:
        consulta = consulta.filter(Producto.categoria == categoria)

    consulta = consulta.order_by(Producto.fecha_creacion.desc())

    productos_paginados = consulta.paginate(
        page=pagina,
        per_page=POR_PAGINA,
        error_out=False
    )

    categorias = db.session.query(Producto.categoria)\
                           .distinct()\
                           .order_by(Producto.categoria)\
                           .all()
    categorias = [c[0] for c in categorias if c[0]]

    return render_template(
        'productos.html',
        productos=productos_paginados,
        categorias=categorias,
        buscar=buscar,
        categoria_activa=categoria
    )

    # ------ LEER PARÁMETROS DE LA URL ------

    # request.args.get('clave', 'valor_por_defecto')
    # Si el parámetro no está en la URL, devuelve el valor por defecto
    buscar    = request.args.get('buscar', '').strip()
    categoria = request.args.get('categoria', '')
    pagina    = request.args.get('pagina', 1, type=int)  # type=int convierte automáticamente

    # Cuántos productos mostramos por página
    POR_PAGINA = 10

    # ------ CONSTRUIR LA CONSULTA DINÁMICAMENTE ------

    # Empezamos con una consulta base — todavía no va a la BD
    # Es como armar la frase SQL paso a paso
    consulta = Producto.query

    # Si el usuario escribió algo en el buscador, filtramos por nombre
    # ilike() es como LIKE en SQL pero sin importar mayúsculas/minúsculas
    # El % antes y después significa "cualquier texto alrededor"
    if buscar:
        consulta = consulta.filter(
            Producto.nombre.ilike(f'%{buscar}%')
        )

    # Si el usuario eligió una categoría, filtramos por ella
    if categoria:
        consulta = consulta.filter(Producto.categoria == categoria)

    # Ordenamos: primero los más recientes
    consulta = consulta.order_by(Producto.fecha_creacion.desc())

    # ------ PAGINACIÓN ------

    # .paginate() divide los resultados en páginas automáticamente.
    # Devuelve un objeto especial con los productos de la página actual
    # y metadata útil: total de páginas, si hay página siguiente, etc.
    productos_paginados = consulta.paginate(
        page=pagina,
        per_page=POR_PAGINA,
        error_out=False   # Si la página no existe, devuelve lista vacía (no error 404)
    )

    # ------ CATEGORÍAS PARA EL FILTRO ------

    # Obtenemos todas las categorías únicas para mostrar en el select
    # .distinct() es como SELECT DISTINCT en SQL — sin repetidos
    categorias = db.session.query(Producto.categoria)\
                           .distinct()\
                           .order_by(Producto.categoria)\
                           .all()
    # El resultado es una lista de tuplas [('Electrónica',), ('Papelería',)]
    # La convertimos a lista plana ['Electrónica', 'Papelería']
    categorias = [c[0] for c in categorias if c[0]]

    return render_template(
        'productos.html',
        productos=productos_paginados,   # objeto paginado (no lista simple)
        categorias=categorias,
        buscar=buscar,                   # para que el input muestre lo que buscó
        categoria_activa=categoria       # para resaltar el filtro activo
    )


@app.route('/productos/<int:id>')
def detalle_producto(id):
    """
    SEMANA 4 — Página de detalle de un producto individual.

    <int:id> en la ruta captura el número de la URL.
    Ejemplo: /productos/3 → id = 3

    get_or_404() busca el producto por ID.
    Si no existe, Flask devuelve automáticamente una página de error 404.
    Mucho mejor que dejar que el servidor explote con un error feo.
    """
    producto = Producto.query.get_or_404(id)

    return render_template('detalle.html', producto=producto)


@app.route('/dashboard')
def dashboard():
    """
    Página del dashboard con gráficos.
    En semana 10 agregaremos Plotly aquí.
    """
    return render_template('dashboard.html')


@app.route('/reportes')
def reportes():
    """
    Página de generación de reportes PDF.
    En semana 7 conectaremos ReportLab aquí.
    """
    return render_template('reportes.html')


# ------ ARRANQUE DE LA APP ------

# Este bloque solo corre si ejecutas: python app.py
# NO corre si otro archivo importa app.py
if __name__ == '__main__':
    # Creamos las tablas en la base de datos si no existen todavía.
    # app_context() es necesario para que SQLAlchemy sepa a qué
    # app pertenece la operación.
    with app.app_context():
        db.create_all()
        print("✅ Base de datos lista")
        print("🚀 Servidor corriendo en: http://localhost:5000")
        print("   Presiona Ctrl+C para detenerlo")

    # debug=True recarga la app automáticamente cuando cambias el código
    # NUNCA uses debug=True en producción real
    app.run(debug=True)