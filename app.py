# ============================================================
# app.py — Punto de entrada principal del sistema
# ============================================================
# Aquí vive TODO el "cerebro" de la aplicación.
# Flask es el framework que recibe peticiones del navegador
# y decide qué responder. SQLAlchemy es el "traductor" que
# convierte objetos Python en filas de la base de datos.
# ============================================================

from flask import Flask, render_template, request, redirect, url_for, flash
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
    """
    SEMANA 4 — Lista de productos con:
      - Búsqueda por nombre (parámetro GET: ?buscar=laptop)
      - Filtro por categoría (?categoria=Electrónica)
      - Paginación (10 productos por página, ?pagina=2)

    Los parámetros vienen en la URL. Flask los lee con request.args.
    Ejemplo de URL completa:
      /productos?buscar=mouse&categoria=Electrónica&pagina=1
    """

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
    """
    producto = Producto.query.get_or_404(id)
    return render_template('detalle.html', producto=producto)


# ============================================================
# SEMANA 5 — CREAR Y EDITAR PRODUCTOS
# ============================================================

# Lista de categorías fijas para el formulario.
# En un sistema más avanzado esto vendría de una tabla separada.
CATEGORIAS = ['Electrónica', 'Papelería', 'Mobiliario', 'Limpieza',
              'Alimentos', 'Ropa', 'Herramientas', 'General']


@app.route('/productos/nuevo', methods=['GET', 'POST'])
def nuevo_producto():
    """
    SEMANA 5 — Formulario para crear un producto nuevo.

    Esta ruta maneja DOS tipos de petición:
    - GET:  El usuario abre el formulario vacío (solo visitar la página)
    - POST: El usuario envió el formulario con datos (hacer clic en Guardar)

    methods=['GET', 'POST'] le dice a Flask que acepte ambos tipos.
    Dentro usamos request.method para saber cuál llegó.
    """

    if request.method == 'POST':
        # ------ EL USUARIO ENVIÓ EL FORMULARIO ------

        # request.form es un diccionario con todos los campos del formulario.
        # .get('nombre') lee el campo con name="nombre" del HTML.
        # .strip() elimina espacios en blanco al inicio y al final.
        nombre      = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        categoria   = request.form.get('categoria', 'General').strip()

        # Para precio y cantidad necesitamos convertir el texto a número.
        # Usamos try/except porque si el usuario escribe "abc" en precio,
        # float("abc") lanzaría un error y rompería la app.
        try:
            precio   = float(request.form.get('precio', 0))
            cantidad = int(request.form.get('cantidad', 0))
        except ValueError:
            # Si la conversión falla, mostramos error y volvemos al formulario
            flash('❌ El precio y la cantidad deben ser números válidos.', 'danger')
            return render_template('formulario.html',
                                   titulo='Nuevo Producto',
                                   categorias=CATEGORIAS,
                                   producto=None)

        # ------ VALIDACIONES ------
        # Verificamos que los datos tengan sentido antes de guardar.
        # Nunca confíes en que el usuario llenó bien el formulario.

        errores = []

        if not nombre:
            errores.append('El nombre del producto es obligatorio.')

        if len(nombre) > 100:
            errores.append('El nombre no puede tener más de 100 caracteres.')

        if precio < 0:
            errores.append('El precio no puede ser negativo.')

        if cantidad < 0:
            errores.append('La cantidad no puede ser negativa.')

        # Si hay errores, los mostramos y devolvemos el formulario
        # con los datos que ya había escrito el usuario (para no perderlos)
        if errores:
            for error in errores:
                flash(f'❌ {error}', 'danger')
            # Pasamos los datos del form para pre-llenar el formulario
            datos_form = {
                'nombre': nombre,
                'descripcion': descripcion,
                'precio': precio,
                'cantidad': cantidad,
                'categoria': categoria
            }
            return render_template('formulario.html',
                                   titulo='Nuevo Producto',
                                   categorias=CATEGORIAS,
                                   producto=datos_form)

        # ------ GUARDAR EN LA BASE DE DATOS ------
        # Si llegamos aquí, todos los datos son válidos.

        nuevo = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            cantidad=cantidad,
            categoria=categoria
            # fecha_creacion se pone automáticamente (default=datetime.utcnow)
        )

        # db.session es como una "caja de cambios pendientes".
        # .add() agrega el objeto a la lista de cambios.
        # .commit() ejecuta TODOS los cambios de una vez en la BD.
        # Si algo falla antes del commit, nada se guarda (es seguro).
        db.session.add(nuevo)
        db.session.commit()

        # flash() guarda un mensaje que se muestra en la SIGUIENTE página.
        # 'success' define el color verde del mensaje.
        flash(f'✅ Producto "{nombre}" creado exitosamente.', 'success')

        # redirect() lleva al usuario a otra página.
        # url_for('lista_productos') genera la URL /productos
        return redirect(url_for('lista_productos'))

    # ------ EL USUARIO SOLO ABRIÓ EL FORMULARIO (GET) ------
    # Mostramos el formulario vacío
    return render_template('formulario.html',
                           titulo='Nuevo Producto',
                           categorias=CATEGORIAS,
                           producto=None)


@app.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    """
    SEMANA 5 — Formulario para editar un producto existente.

    Es casi igual a nuevo_producto(), con dos diferencias:
    1. En GET, pre-llenamos el formulario con los datos actuales.
    2. En POST, actualizamos el producto existente en vez de crear uno nuevo.
    """

    # Buscamos el producto. Si no existe → error 404 automático.
    producto = Producto.query.get_or_404(id)

    if request.method == 'POST':
        # ------ LEER Y VALIDAR (igual que en nuevo_producto) ------

        nombre      = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        categoria   = request.form.get('categoria', 'General').strip()

        try:
            precio   = float(request.form.get('precio', 0))
            cantidad = int(request.form.get('cantidad', 0))
        except ValueError:
            flash('❌ El precio y la cantidad deben ser números válidos.', 'danger')
            return render_template('formulario.html',
                                   titulo=f'Editar: {producto.nombre}',
                                   categorias=CATEGORIAS,
                                   producto=producto)

        errores = []
        if not nombre:
            errores.append('El nombre del producto es obligatorio.')
        if len(nombre) > 100:
            errores.append('El nombre no puede tener más de 100 caracteres.')
        if precio < 0:
            errores.append('El precio no puede ser negativo.')
        if cantidad < 0:
            errores.append('La cantidad no puede ser negativa.')

        if errores:
            for error in errores:
                flash(f'❌ {error}', 'danger')
            return render_template('formulario.html',
                                   titulo=f'Editar: {producto.nombre}',
                                   categorias=CATEGORIAS,
                                   producto=producto)

        # ------ ACTUALIZAR EL PRODUCTO EXISTENTE ------
        # A diferencia de crear, aquí modificamos el objeto que ya existe.
        # SQLAlchemy detecta los cambios automáticamente al hacer commit().

        producto.nombre      = nombre
        producto.descripcion = descripcion
        producto.precio      = precio
        producto.cantidad    = cantidad
        producto.categoria   = categoria
        # Nota: NO tocamos fecha_creacion, esa queda igual

        # No necesitamos db.session.add() porque el producto
        # ya está "rastreado" por SQLAlchemy (lo obtuvimos con .get_or_404)
        db.session.commit()

        flash(f'✅ Producto "{nombre}" actualizado correctamente.', 'success')
        return redirect(url_for('detalle_producto', id=producto.id))

    # ------ GET: mostrar formulario pre-llenado con datos actuales ------
    return render_template('formulario.html',
                           titulo=f'Editar: {producto.nombre}',
                           categorias=CATEGORIAS,
                           producto=producto)


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
