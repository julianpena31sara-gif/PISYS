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


# ============================================================
# SEMANA 6 — MODELO DE MOVIMIENTOS DE STOCK
# ============================================================

class Movimiento(db.Model):
    """
    Tabla 'movimiento' — registra cada vez que el stock cambia.

    Cada vez que alguien edita la cantidad de un producto,
    guardamos un registro aquí con:
    - qué producto cambió
    - cuánto cambió (positivo = entrada, negativo = salida)
    - la cantidad antes y después del cambio
    - cuándo ocurrió

    Esto nos permite ver el historial completo y calcular
    las alertas predictivas en semana 11.
    """
    __tablename__ = 'movimiento'

    id = db.Column(db.Integer, primary_key=True)

    # Llave foránea: referencia al producto que cambió
    # ForeignKey('producto.id') le dice a SQLAlchemy que este número
    # corresponde al id de la tabla producto
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)

    # Tipo de movimiento para clasificar
    # 'entrada'  = llegó más stock (compra, devolución)
    # 'salida'   = salió stock (venta, pérdida)
    # 'ajuste'   = corrección manual
    # 'creacion' = cuando se registra el producto por primera vez
    tipo = db.Column(db.String(20), nullable=False, default='ajuste')

    # Cuántas unidades cambiaron
    # Positivo (+10) = entraron 10 unidades
    # Negativo (-5)  = salieron 5 unidades
    cantidad_cambio = db.Column(db.Integer, nullable=False)

    # Stock antes y después del cambio (útil para auditoría)
    cantidad_anterior = db.Column(db.Integer, nullable=False)
    cantidad_nueva    = db.Column(db.Integer, nullable=False)

    # Nota opcional del usuario explicando por qué cambió
    nota = db.Column(db.String(200), nullable=True)

    # Cuándo ocurrió el movimiento
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    # relationship() permite acceder al producto desde el movimiento:
    # movimiento.producto.nombre  (sin hacer otra consulta a la BD)
    # backref='movimientos' permite acceder desde el producto:
    # producto.movimientos  (lista de todos sus movimientos)
    producto = db.relationship('Producto', backref='movimientos')

    def __repr__(self):
        signo = '+' if self.cantidad_cambio >= 0 else ''
        return f'<Movimiento {self.producto_id} {signo}{self.cantidad_cambio}>'


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
        db.session.flush()  # flush() asigna el ID sin hacer commit todavía

        # Registramos el movimiento inicial de creación
        if nuevo.cantidad > 0:
            registrar_movimiento(
                nuevo,
                cantidad_anterior=0,
                tipo='creacion',
                nota='Stock inicial al registrar el producto'
            )

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
        # Guardamos la cantidad anterior ANTES de modificar
        cantidad_anterior = producto.cantidad

        producto.nombre      = nombre
        producto.descripcion = descripcion
        producto.precio      = precio
        producto.cantidad    = cantidad
        producto.categoria   = categoria

        # Si la cantidad cambió, registramos el movimiento
        if cantidad != cantidad_anterior:
            registrar_movimiento(
                producto,
                cantidad_anterior,
                tipo='ajuste',
                nota='Modificación desde formulario de edición'
            )

        db.session.commit()

        flash(f'✅ Producto "{nombre}" actualizado correctamente.', 'success')
        return redirect(url_for('detalle_producto', id=producto.id))

    # ------ GET: mostrar formulario pre-llenado con datos actuales ------
    return render_template('formulario.html',
                           titulo=f'Editar: {producto.nombre}',
                           categorias=CATEGORIAS,
                           producto=producto)


# ============================================================
# SEMANA 6 — FUNCIÓN HELPER PARA REGISTRAR MOVIMIENTOS
# ============================================================

def registrar_movimiento(producto, cantidad_anterior, tipo='ajuste', nota=None):
    """
    Función auxiliar que crea un registro en la tabla Movimiento.

    La llamamos cada vez que el stock de un producto cambia:
    - Al editar un producto (semana 5, ahora con registro)
    - Al crear un producto nuevo
    - Al eliminar (registramos antes de borrar)

    Parámetros:
        producto:          el objeto Producto que cambió
        cantidad_anterior: cuánto tenía ANTES del cambio
        tipo:              'creacion', 'ajuste', 'entrada', 'salida'
        nota:              texto explicativo opcional
    """
    cambio = producto.cantidad - cantidad_anterior

    # Solo registramos si hubo un cambio real en la cantidad
    # (no registramos si solo cambió el nombre o el precio)
    if cambio == 0 and tipo not in ('creacion',):
        return

    movimiento = Movimiento(
        producto_id       = producto.id,
        tipo              = tipo,
        cantidad_cambio   = cambio,
        cantidad_anterior = cantidad_anterior,
        cantidad_nueva    = producto.cantidad,
        nota              = nota
    )
    db.session.add(movimiento)
    # Nota: NO hacemos commit aquí — lo hace la función que nos llama.
    # Así ambos cambios (producto + movimiento) se guardan juntos.


# ============================================================
# SEMANA 6 — ELIMINAR PRODUCTO
# ============================================================

@app.route('/productos/eliminar/<int:id>', methods=['POST'])
def eliminar_producto(id):
    """
    SEMANA 6 — Elimina un producto de la base de datos.

    IMPORTANTE: Solo aceptamos POST, nunca GET.
    Si aceptáramos GET, alguien podría enviarte un link como:
        <img src="/productos/eliminar/5">
    y al cargar la imagen, ¡borraría el producto 5 sin querer!
    Con POST solo se puede hacer desde un formulario o JS intencional.

    La confirmación real sucede en el navegador (JavaScript),
    pero aquí en el servidor también verificamos que el producto exista.
    """
    producto = Producto.query.get_or_404(id)
    nombre   = producto.nombre  # Guardamos el nombre antes de borrar

    # Antes de eliminar, borramos sus movimientos también
    # (porque tienen una llave foránea que apunta a este producto)
    Movimiento.query.filter_by(producto_id=id).delete()

    db.session.delete(producto)
    db.session.commit()

    flash(f'🗑️ Producto "{nombre}" eliminado correctamente.', 'warning')
    return redirect(url_for('lista_productos'))


# ============================================================
# SEMANA 6 — AJUSTE RÁPIDO DE STOCK
# ============================================================

@app.route('/productos/ajustar-stock/<int:id>', methods=['POST'])
def ajustar_stock(id):
    """
    SEMANA 6 — Ajusta el stock de un producto sin ir al formulario completo.

    Recibe dos campos del formulario:
    - 'operacion': 'sumar' o 'restar'
    - 'cantidad_ajuste': cuántas unidades sumar o restar

    Esto es más rápido que abrir el formulario de edición completo
    solo para cambiar 5 unidades de stock.
    """
    producto = Producto.query.get_or_404(id)

    try:
        cantidad_ajuste = int(request.form.get('cantidad_ajuste', 0))
    except ValueError:
        flash('❌ La cantidad debe ser un número entero.', 'danger')
        return redirect(url_for('detalle_producto', id=id))

    if cantidad_ajuste <= 0:
        flash('❌ La cantidad del ajuste debe ser mayor a 0.', 'danger')
        return redirect(url_for('detalle_producto', id=id))

    operacion        = request.form.get('operacion', 'sumar')
    cantidad_anterior = producto.cantidad

    if operacion == 'sumar':
        producto.cantidad += cantidad_ajuste
        tipo = 'entrada'
        nota = f'Entrada de {cantidad_ajuste} unidades (ajuste rápido)'
    else:
        # Verificamos que no quede en negativo
        if producto.cantidad - cantidad_ajuste < 0:
            flash(f'❌ No puedes restar {cantidad_ajuste} unidades. Solo hay {producto.cantidad} en stock.', 'danger')
            return redirect(url_for('detalle_producto', id=id))
        producto.cantidad -= cantidad_ajuste
        tipo = 'salida'
        nota = f'Salida de {cantidad_ajuste} unidades (ajuste rápido)'

    # Registramos el movimiento ANTES del commit
    registrar_movimiento(producto, cantidad_anterior, tipo=tipo, nota=nota)
    db.session.commit()

    flash(f'✅ Stock actualizado: {cantidad_anterior} → {producto.cantidad} unidades.', 'success')
    return redirect(url_for('detalle_producto', id=id))


# ============================================================
# SEMANA 6 — HISTORIAL DE MOVIMIENTOS
# ============================================================

@app.route('/historial')
def historial():
    """
    SEMANA 6 — Muestra el historial completo de movimientos de stock.

    Útil para auditoría: ver qué cambió, cuándo y cuánto.
    En semana 9 generaremos un PDF con este historial.
    """
    pagina    = request.args.get('pagina', 1, type=int)
    tipo_filtro = request.args.get('tipo', '')

    consulta = Movimiento.query

    if tipo_filtro:
        consulta = consulta.filter(Movimiento.tipo == tipo_filtro)

    # Ordenamos del más reciente al más antiguo
    movimientos = consulta.order_by(Movimiento.fecha.desc())\
                          .paginate(page=pagina, per_page=20, error_out=False)

    return render_template('historial.html',
                           movimientos=movimientos,
                           tipo_filtro=tipo_filtro)


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
