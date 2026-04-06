from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-super-secreta-cambiala-en-produccion'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventario.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ---------------------------------------------------------------------------
# MODELOS
# ---------------------------------------------------------------------------

class Producto(db.Model):
    __tablename__ = 'producto'

    id             = db.Column(db.Integer, primary_key=True)
    nombre         = db.Column(db.String(100), nullable=False)
    descripcion    = db.Column(db.Text, nullable=True)
    precio         = db.Column(db.Float, nullable=False, default=0.0)
    cantidad       = db.Column(db.Integer, nullable=False, default=0)
    categoria      = db.Column(db.String(50), nullable=True, default='General')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Producto {self.nombre}>'

    def estado_stock(self):
        if self.cantidad < 5:  return 'critico'
        if self.cantidad < 10: return 'bajo'
        return 'normal'

    def valor_total(self):
        return self.precio * self.cantidad


class Movimiento(db.Model):
    __tablename__ = 'movimiento'

    id                = db.Column(db.Integer, primary_key=True)
    producto_id       = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    tipo              = db.Column(db.String(20), nullable=False, default='ajuste')  # entrada | salida | ajuste | creacion
    cantidad_cambio   = db.Column(db.Integer, nullable=False)
    cantidad_anterior = db.Column(db.Integer, nullable=False)
    cantidad_nueva    = db.Column(db.Integer, nullable=False)
    nota              = db.Column(db.String(200), nullable=True)
    fecha             = db.Column(db.DateTime, default=datetime.utcnow)

    producto = db.relationship('Producto', backref='movimientos')

    def __repr__(self):
        signo = '+' if self.cantidad_cambio >= 0 else ''
        return f'<Movimiento {self.producto_id} {signo}{self.cantidad_cambio}>'


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def registrar_movimiento(producto, cantidad_anterior, tipo='ajuste', nota=None):
    """Registra un movimiento de stock. El commit lo hace el llamador."""
    cambio = producto.cantidad - cantidad_anterior
    if cambio == 0 and tipo != 'creacion':
        return
    db.session.add(Movimiento(
        producto_id       = producto.id,
        tipo              = tipo,
        cantidad_cambio   = cambio,
        cantidad_anterior = cantidad_anterior,
        cantidad_nueva    = producto.cantidad,
        nota              = nota
    ))


def _estilos_pdf():
    """Estilos ReportLab reutilizables en todos los reportes."""
    base = getSampleStyleSheet()
    return {
        'titulo':    ParagraphStyle('titulo',    parent=base['Title'],
                                    fontSize=20, textColor=colors.HexColor('#1E3A5F'), spaceAfter=4),
        'subtitulo': ParagraphStyle('subtitulo', parent=base['Normal'],
                                    fontSize=10, textColor=colors.HexColor('#64748B'), spaceAfter=2),
        'seccion':   ParagraphStyle('seccion',   parent=base['Normal'],
                                    fontSize=12, fontName='Helvetica-Bold',
                                    textColor=colors.HexColor('#1E3A5F'), spaceBefore=14, spaceAfter=6),
        'normal':    ParagraphStyle('normal',    parent=base['Normal'],
                                    fontSize=9,  textColor=colors.HexColor('#374151')),
        'pie':       ParagraphStyle('pie',       parent=base['Normal'],
                                    fontSize=8,  textColor=colors.HexColor('#9CA3AF'), alignment=TA_CENTER),
        'derecha':   ParagraphStyle('derecha',   parent=base['Normal'],
                                    fontSize=9,  textColor=colors.HexColor('#374151'), alignment=TA_RIGHT),
    }


def _encabezado_pdf(elementos, estilos, titulo, subtitulo):
    """Encabezado estándar de todos los reportes."""
    elementos.append(Paragraph('PISYS', estilos['titulo']))
    elementos.append(Paragraph(titulo, estilos['seccion']))
    elementos.append(Paragraph(
        f'{subtitulo} &nbsp;·&nbsp; Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}',
        estilos['subtitulo']
    ))
    elementos.append(HRFlowable(width='100%', thickness=1,
                                color=colors.HexColor('#2563EB'), spaceAfter=12))


def _estilo_tabla_base():
    """Encabezado azul oscuro + filas alternas gris claro."""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0),  colors.HexColor('#1E3A5F')),
        ('TEXTCOLOR',  (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',   (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0),  9),
        ('FONTNAME',   (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',   (0, 1), (-1, -1), 8),
        ('ROWBACKGROUND', (0, 2), (-1, -1), colors.HexColor('#F8FAFC')),
        ('GRID',       (0, 0), (-1, -1), 0.4, colors.HexColor('#E2E8F0')),
        ('PADDING',    (0, 0), (-1, -1), 6),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
    ])


def _enviar_pdf(buffer, filename):
    """Convierte el buffer en una respuesta HTTP con tipo PDF."""
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type']        = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename={filename}'
    return response


CATEGORIAS = ['Electrónica', 'Papelería', 'Mobiliario', 'Limpieza',
              'Alimentos', 'Ropa', 'Herramientas', 'General']


# ---------------------------------------------------------------------------
# RUTAS — INICIO
# ---------------------------------------------------------------------------

@app.route('/')
def inicio():
    productos = Producto.query.all()
    return render_template('inicio.html',
        total_productos        = Producto.query.count(),
        alertas_criticas       = [p for p in productos if p.estado_stock() == 'critico'],
        alertas_bajas          = [p for p in productos if p.estado_stock() == 'bajo'],
        valor_total_inventario = sum(p.valor_total() for p in productos)
    )


# ---------------------------------------------------------------------------
# RUTAS — PRODUCTOS (CRUD)
# ---------------------------------------------------------------------------

@app.route('/productos')
def lista_productos():
    buscar    = request.args.get('buscar', '').strip()
    categoria = request.args.get('categoria', '')
    pagina    = request.args.get('pagina', 1, type=int)

    consulta = Producto.query
    if buscar:
        consulta = consulta.filter(Producto.nombre.ilike(f'%{buscar}%'))
    if categoria:
        consulta = consulta.filter(Producto.categoria == categoria)

    productos  = consulta.order_by(Producto.fecha_creacion.desc()) \
                         .paginate(page=pagina, per_page=10, error_out=False)
    categorias = [c[0] for c in db.session.query(Producto.categoria)
                                          .distinct().order_by(Producto.categoria).all() if c[0]]

    return render_template('productos.html',
                           productos=productos, categorias=categorias,
                           buscar=buscar, categoria_activa=categoria)


@app.route('/productos/<int:id>')
def detalle_producto(id):
    return render_template('detalle.html', producto=Producto.query.get_or_404(id))


@app.route('/productos/nuevo', methods=['GET', 'POST'])
def nuevo_producto():
    if request.method == 'POST':
        nombre      = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        categoria   = request.form.get('categoria', 'General').strip()

        try:
            precio   = float(request.form.get('precio', 0))
            cantidad = int(request.form.get('cantidad', 0))
        except ValueError:
            flash('❌ El precio y la cantidad deben ser números válidos.', 'danger')
            return render_template('formulario.html', titulo='Nuevo Producto',
                                   categorias=CATEGORIAS, producto=None)

        errores = []
        if not nombre:           errores.append('El nombre es obligatorio.')
        if len(nombre) > 100:    errores.append('El nombre no puede superar 100 caracteres.')
        if precio < 0:           errores.append('El precio no puede ser negativo.')
        if cantidad < 0:         errores.append('La cantidad no puede ser negativa.')

        if errores:
            for e in errores: flash(f'❌ {e}', 'danger')
            return render_template('formulario.html', titulo='Nuevo Producto',
                                   categorias=CATEGORIAS,
                                   producto={'nombre': nombre, 'descripcion': descripcion,
                                             'precio': precio, 'cantidad': cantidad, 'categoria': categoria})

        nuevo = Producto(nombre=nombre, descripcion=descripcion,
                         precio=precio, cantidad=cantidad, categoria=categoria)
        db.session.add(nuevo)
        db.session.flush()  # obtiene el ID antes del commit

        if nuevo.cantidad > 0:
            registrar_movimiento(nuevo, 0, tipo='creacion', nota='Stock inicial')

        db.session.commit()
        flash(f'✅ Producto "{nombre}" creado exitosamente.', 'success')
        return redirect(url_for('lista_productos'))

    return render_template('formulario.html', titulo='Nuevo Producto',
                           categorias=CATEGORIAS, producto=None)


@app.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    producto = Producto.query.get_or_404(id)

    if request.method == 'POST':
        nombre      = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        categoria   = request.form.get('categoria', 'General').strip()

        try:
            precio   = float(request.form.get('precio', 0))
            cantidad = int(request.form.get('cantidad', 0))
        except ValueError:
            flash('❌ El precio y la cantidad deben ser números válidos.', 'danger')
            return render_template('formulario.html', titulo=f'Editar: {producto.nombre}',
                                   categorias=CATEGORIAS, producto=producto)

        errores = []
        if not nombre:        errores.append('El nombre es obligatorio.')
        if len(nombre) > 100: errores.append('El nombre no puede superar 100 caracteres.')
        if precio < 0:        errores.append('El precio no puede ser negativo.')
        if cantidad < 0:      errores.append('La cantidad no puede ser negativa.')

        if errores:
            for e in errores: flash(f'❌ {e}', 'danger')
            return render_template('formulario.html', titulo=f'Editar: {producto.nombre}',
                                   categorias=CATEGORIAS, producto=producto)

        cantidad_anterior    = producto.cantidad
        producto.nombre      = nombre
        producto.descripcion = descripcion
        producto.precio      = precio
        producto.cantidad    = cantidad
        producto.categoria   = categoria

        if cantidad != cantidad_anterior:
            registrar_movimiento(producto, cantidad_anterior,
                                 tipo='ajuste', nota='Modificación desde formulario')

        db.session.commit()
        flash(f'✅ Producto "{nombre}" actualizado correctamente.', 'success')
        return redirect(url_for('detalle_producto', id=producto.id))

    return render_template('formulario.html', titulo=f'Editar: {producto.nombre}',
                           categorias=CATEGORIAS, producto=producto)


@app.route('/productos/eliminar/<int:id>', methods=['POST'])
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)
    nombre   = producto.nombre
    Movimiento.query.filter_by(producto_id=id).delete()
    db.session.delete(producto)
    db.session.commit()
    flash(f'🗑️ Producto "{nombre}" eliminado.', 'warning')
    return redirect(url_for('lista_productos'))


@app.route('/productos/ajustar-stock/<int:id>', methods=['POST'])
def ajustar_stock(id):
    producto = Producto.query.get_or_404(id)

    try:
        cantidad_ajuste = int(request.form.get('cantidad_ajuste', 0))
    except ValueError:
        flash('❌ La cantidad debe ser un número entero.', 'danger')
        return redirect(url_for('detalle_producto', id=id))

    if cantidad_ajuste <= 0:
        flash('❌ La cantidad debe ser mayor a 0.', 'danger')
        return redirect(url_for('detalle_producto', id=id))

    cantidad_anterior = producto.cantidad
    operacion         = request.form.get('operacion', 'sumar')

    if operacion == 'sumar':
        producto.cantidad += cantidad_ajuste
        tipo, nota = 'entrada', f'Entrada de {cantidad_ajuste} unidades'
    else:
        if producto.cantidad - cantidad_ajuste < 0:
            flash(f'❌ No puedes restar {cantidad_ajuste}. Solo hay {producto.cantidad} en stock.', 'danger')
            return redirect(url_for('detalle_producto', id=id))
        producto.cantidad -= cantidad_ajuste
        tipo, nota = 'salida', f'Salida de {cantidad_ajuste} unidades'

    registrar_movimiento(producto, cantidad_anterior, tipo=tipo, nota=nota)
    db.session.commit()
    flash(f'✅ Stock: {cantidad_anterior} → {producto.cantidad} unidades.', 'success')
    return redirect(url_for('detalle_producto', id=id))


# ---------------------------------------------------------------------------
# RUTAS — HISTORIAL
# ---------------------------------------------------------------------------

@app.route('/historial')
def historial():
    pagina      = request.args.get('pagina', 1, type=int)
    tipo_filtro = request.args.get('tipo', '')

    consulta = Movimiento.query
    if tipo_filtro:
        consulta = consulta.filter(Movimiento.tipo == tipo_filtro)

    movimientos = consulta.order_by(Movimiento.fecha.desc()) \
                          .paginate(page=pagina, per_page=20, error_out=False)

    return render_template('historial.html', movimientos=movimientos, tipo_filtro=tipo_filtro)


# ---------------------------------------------------------------------------
# RUTAS — REPORTES PDF (Semanas 7, 8 y 9)
# ---------------------------------------------------------------------------

@app.route('/reportes')
def reportes():
    productos = Producto.query.all()
    categorias = [c[0] for c in db.session.query(Producto.categoria)
                                          .distinct().order_by(Producto.categoria).all() if c[0]]
    return render_template('reportes.html',
        total_productos = len(productos),
        valor_total     = sum(p.valor_total() for p in productos),
        criticos        = len([p for p in productos if p.estado_stock() == 'critico']),
        bajos           = len([p for p in productos if p.estado_stock() == 'bajo']),
        categorias      = categorias
    )


@app.route('/reportes/inventario')
def reporte_inventario():
    """Semana 8 — PDF completo de inventario con colores por estado y resumen."""
    categoria_filtro = request.args.get('categoria', '')

    consulta = Producto.query
    if categoria_filtro:
        consulta = consulta.filter(Producto.categoria == categoria_filtro)
    productos = consulta.order_by(Producto.categoria, Producto.nombre).all()

    buffer  = io.BytesIO()
    doc     = SimpleDocTemplate(buffer, pagesize=letter,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm,  bottomMargin=2*cm)
    estilos   = _estilos_pdf()
    elementos = []

    subtitulo = f'Categoría: {categoria_filtro}' if categoria_filtro else 'Todos los productos'
    _encabezado_pdf(elementos, estilos, 'Reporte de Inventario', subtitulo)

    # Tabla principal
    filas = [['#', 'Producto', 'Categoría', 'Precio', 'Stock', 'Valor total', 'Estado']]
    for p in productos:
        estado = {'critico': 'CRÍTICO', 'bajo': 'BAJO', 'normal': 'Normal'}[p.estado_stock()]
        filas.append([str(p.id), Paragraph(p.nombre, estilos['normal']),
                      p.categoria or '—', f'${p.precio:,.0f}',
                      str(p.cantidad), f'${p.valor_total():,.0f}', estado])

    tabla = Table(filas,
                  colWidths=[1*cm, 5.5*cm, 3*cm, 2.5*cm, 1.5*cm, 2.5*cm, 2*cm],
                  repeatRows=1)
    estilo = _estilo_tabla_base()

    # Colorear filas según estado de stock
    for i, p in enumerate(productos, start=1):
        if p.estado_stock() == 'critico':
            estilo.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#FEF2F2'))
            estilo.add('TEXTCOLOR',  (6, i), (6, i),  colors.HexColor('#DC2626'))
            estilo.add('FONTNAME',   (6, i), (6, i),  'Helvetica-Bold')
        elif p.estado_stock() == 'bajo':
            estilo.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#FFFBEB'))
            estilo.add('TEXTCOLOR',  (6, i), (6, i),  colors.HexColor('#D97706'))
            estilo.add('FONTNAME',   (6, i), (6, i),  'Helvetica-Bold')
    tabla.setStyle(estilo)
    elementos.append(tabla)

    # Resumen ejecutivo
    elementos.append(Spacer(1, 0.5*cm))
    elementos.append(HRFlowable(width='100%', thickness=0.5,
                                color=colors.HexColor('#E2E8F0'), spaceAfter=8))
    criticos = len([p for p in productos if p.estado_stock() == 'critico'])
    bajos    = len([p for p in productos if p.estado_stock() == 'bajo'])
    resumen  = Table(
        [['Total productos', 'Valor inventario', 'Críticos', 'Stock bajo'],
         [str(len(productos)), f'${sum(p.valor_total() for p in productos):,.0f}',
          str(criticos), str(bajos)]],
        colWidths=[4.5*cm] * 4
    )
    resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('FONTNAME',   (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
        ('TEXTCOLOR',  (0, 1), (-1, 1),  colors.HexColor('#1E3A5F')),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('GRID',       (0, 0), (-1, -1), 0.4, colors.HexColor('#E2E8F0')),
        ('PADDING',    (0, 0), (-1, -1), 8),
    ]))
    elementos.append(resumen)
    elementos.append(Spacer(1, 0.3*cm))
    elementos.append(Paragraph('PISYS — Reporte generado automáticamente', estilos['pie']))

    doc.build(elementos)
    return _enviar_pdf(buffer, 'inventario.pdf')


@app.route('/reportes/alertas')
def reporte_alertas():
    """Semana 8 — PDF de productos con stock crítico o bajo."""
    productos_alerta = Producto.query.filter(Producto.cantidad < 10) \
                                     .order_by(Producto.cantidad).all()

    buffer  = io.BytesIO()
    doc     = SimpleDocTemplate(buffer, pagesize=letter,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm,  bottomMargin=2*cm)
    estilos   = _estilos_pdf()
    elementos = []

    _encabezado_pdf(elementos, estilos, 'Reporte de Alertas de Stock',
                    f'{len(productos_alerta)} producto(s) requieren atención')

    if not productos_alerta:
        elementos.append(Paragraph('✅ No hay productos con stock bajo o crítico.', estilos['normal']))
    else:
        filas = [['#', 'Producto', 'Categoría', 'Stock', 'Estado', 'Valor en riesgo']]
        for p in productos_alerta:
            estado = 'CRÍTICO' if p.estado_stock() == 'critico' else 'BAJO'
            filas.append([str(p.id), Paragraph(p.nombre, estilos['normal']),
                          p.categoria or '—', str(p.cantidad), estado,
                          f'${p.valor_total():,.0f}'])

        tabla = Table(filas,
                      colWidths=[1*cm, 6*cm, 3*cm, 2*cm, 2.5*cm, 3*cm],
                      repeatRows=1)
        estilo = _estilo_tabla_base()
        for i, p in enumerate(productos_alerta, start=1):
            c_bg   = colors.HexColor('#FEF2F2') if p.estado_stock() == 'critico' else colors.HexColor('#FFFBEB')
            c_text = colors.HexColor('#DC2626') if p.estado_stock() == 'critico' else colors.HexColor('#D97706')
            estilo.add('BACKGROUND', (0, i), (-1, i), c_bg)
            estilo.add('TEXTCOLOR',  (4, i), (4, i),  c_text)
            estilo.add('FONTNAME',   (4, i), (4, i),  'Helvetica-Bold')
        tabla.setStyle(estilo)
        elementos.append(tabla)

    elementos.append(Spacer(1, 0.5*cm))
    elementos.append(Paragraph('PISYS — Reporte de alertas', estilos['pie']))
    doc.build(elementos)
    return _enviar_pdf(buffer, 'alertas.pdf')


@app.route('/reportes/historial')
def reporte_historial():
    """Semana 9 — PDF del historial de movimientos con resumen por tipo."""
    tipo_filtro = request.args.get('tipo', '')

    consulta = Movimiento.query
    if tipo_filtro:
        consulta = consulta.filter(Movimiento.tipo == tipo_filtro)
    movimientos = consulta.order_by(Movimiento.fecha.desc()).all()

    buffer  = io.BytesIO()
    doc     = SimpleDocTemplate(buffer, pagesize=letter,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm,  bottomMargin=2*cm)
    estilos   = _estilos_pdf()
    elementos = []

    subtitulo = f'Tipo: {tipo_filtro.capitalize()}' if tipo_filtro else 'Todos los movimientos'
    _encabezado_pdf(elementos, estilos, 'Historial de Movimientos', subtitulo)

    if not movimientos:
        elementos.append(Paragraph('No hay movimientos registrados aún.', estilos['normal']))
    else:
        filas = [['Fecha', 'Producto', 'Tipo', 'Antes', 'Cambio', 'Después', 'Nota']]
        for m in movimientos:
            signo  = '+' if m.cantidad_cambio > 0 else ''
            cambio = f'{signo}{m.cantidad_cambio}'
            filas.append([
                m.fecha.strftime('%d/%m/%Y %H:%M'),
                Paragraph(m.producto.nombre, estilos['normal']),
                m.tipo.capitalize(),
                str(m.cantidad_anterior),
                cambio,
                str(m.cantidad_nueva),
                Paragraph(m.nota or '—', estilos['normal']),
            ])

        tabla = Table(filas,
                      colWidths=[3*cm, 4.5*cm, 2*cm, 1.5*cm, 1.8*cm, 1.8*cm, 3.4*cm],
                      repeatRows=1)
        estilo = _estilo_tabla_base()
        for i, m in enumerate(movimientos, start=1):
            if m.cantidad_cambio > 0:
                estilo.add('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#16A34A'))
                estilo.add('FONTNAME',  (4, i), (4, i), 'Helvetica-Bold')
            elif m.cantidad_cambio < 0:
                estilo.add('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#DC2626'))
                estilo.add('FONTNAME',  (4, i), (4, i), 'Helvetica-Bold')
        tabla.setStyle(estilo)
        elementos.append(tabla)

        # Resumen de totales por tipo
        elementos.append(Spacer(1, 0.5*cm))
        elementos.append(Paragraph('Resumen', estilos['seccion']))
        entradas  = sum(m.cantidad_cambio for m in movimientos if m.cantidad_cambio > 0)
        salidas   = sum(abs(m.cantidad_cambio) for m in movimientos if m.cantidad_cambio < 0)
        resumen   = Table(
            [['Total movimientos', 'Unidades ingresadas', 'Unidades salidas', 'Balance neto'],
             [str(len(movimientos)), f'+{entradas}', f'-{salidas}', f'{entradas - salidas:+}']],
            colWidths=[4.5*cm] * 4
        )
        resumen.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('FONTNAME',   (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE',   (0, 0), (-1, -1), 9),
            ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
            ('GRID',       (0, 0), (-1, -1), 0.4, colors.HexColor('#E2E8F0')),
            ('PADDING',    (0, 0), (-1, -1), 8),
            ('TEXTCOLOR',  (1, 1), (1, 1), colors.HexColor('#16A34A')),
            ('TEXTCOLOR',  (2, 1), (2, 1), colors.HexColor('#DC2626')),
        ]))
        elementos.append(resumen)

    elementos.append(Spacer(1, 0.3*cm))
    elementos.append(Paragraph('PISYS — Historial de movimientos', estilos['pie']))
    doc.build(elementos)
    return _enviar_pdf(buffer, 'historial.pdf')


# ---------------------------------------------------------------------------
# RUTAS — DASHBOARD Y ALERTAS PREDICTIVAS (Semanas 10 y 11)
# ---------------------------------------------------------------------------

@app.route('/dashboard')
def dashboard():
    productos  = Producto.query.all()
    movimientos = Movimiento.query.order_by(Movimiento.fecha.desc()).all()

    # --- KPIs generales ---
    total_productos        = len(productos)
    valor_total_inventario = sum(p.valor_total() for p in productos)
    total_criticos         = len([p for p in productos if p.estado_stock() == 'critico'])
    total_movimientos      = len(movimientos)

    # --- Gráfico 1: stock por categoría ---
    # Agrupamos cantidad total por categoría para las barras
    from collections import defaultdict
    stock_por_cat = defaultdict(int)
    valor_por_cat = defaultdict(float)
    for p in productos:
        cat = p.categoria or 'General'
        stock_por_cat[cat] += p.cantidad
        valor_por_cat[cat] += p.valor_total()

    categorias_labels = list(stock_por_cat.keys())
    categorias_stock  = [stock_por_cat[c] for c in categorias_labels]
    categorias_valor  = [round(valor_por_cat[c], 0) for c in categorias_labels]

    # --- Gráfico 2: distribución de valor (pastel) ---
    pastel_labels = categorias_labels
    pastel_values = categorias_valor

    # --- Gráfico 3: movimientos por día (últimos 30 días) ---
    from datetime import timedelta
    from collections import Counter
    hace_30 = datetime.utcnow() - timedelta(days=30)
    movs_recientes = Movimiento.query.filter(Movimiento.fecha >= hace_30).all()

    entradas_por_dia = Counter()
    salidas_por_dia  = Counter()
    for m in movs_recientes:
        dia = m.fecha.strftime('%d/%m')
        if m.cantidad_cambio > 0:
            entradas_por_dia[dia] += m.cantidad_cambio
        else:
            salidas_por_dia[dia]  += abs(m.cantidad_cambio)

    # Generar eje X con todos los días del rango
    dias_labels = []
    for i in range(29, -1, -1):
        dia = (datetime.utcnow() - timedelta(days=i)).strftime('%d/%m')
        dias_labels.append(dia)
    entradas_vals = [entradas_por_dia.get(d, 0) for d in dias_labels]
    salidas_vals  = [salidas_por_dia.get(d, 0)  for d in dias_labels]

    # --- Semana 11: Alertas predictivas ---
    # Algoritmo simple: promedio de salidas diarias de los últimos 30 días.
    # Si el stock actual / promedio_diario < 7 días → alerta "se agota pronto".
    alertas_predictivas = []
    for p in productos:
        salidas_producto = [
            abs(m.cantidad_cambio)
            for m in p.movimientos
            if m.cantidad_cambio < 0
            and m.fecha >= hace_30
        ]
        if not salidas_producto:
            continue

        promedio_diario = sum(salidas_producto) / 30
        if promedio_diario <= 0:
            continue

        dias_restantes = p.cantidad / promedio_diario

        if dias_restantes <= 14:  # Menos de 2 semanas
            alertas_predictivas.append({
                'producto':       p,
                'dias_restantes': round(dias_restantes, 1),
                'promedio_diario': round(promedio_diario, 1),
                'urgencia':       'critica' if dias_restantes <= 7 else 'advertencia'
            })

    # Ordenar: primero los más urgentes
    alertas_predictivas.sort(key=lambda x: x['dias_restantes'])

    return render_template('dashboard.html',
        # KPIs
        total_productos        = total_productos,
        valor_total_inventario = valor_total_inventario,
        total_criticos         = total_criticos,
        total_movimientos      = total_movimientos,
        # Datos para gráficos (se pasan como listas Python → JSON en el template)
        categorias_labels = categorias_labels,
        categorias_stock  = categorias_stock,
        categorias_valor  = categorias_valor,
        pastel_labels     = pastel_labels,
        pastel_values     = pastel_values,
        dias_labels       = dias_labels,
        entradas_vals     = entradas_vals,
        salidas_vals      = salidas_vals,
        # Alertas predictivas
        alertas_predictivas = alertas_predictivas,
    )


# ---------------------------------------------------------------------------
# ARRANQUE
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('✅ Base de datos lista')
        print('🚀 http://localhost:5000')
    app.run(debug=True)
