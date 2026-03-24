# ============================================================
# seed.py — Carga datos de prueba en la base de datos
# ============================================================
# Ejecuta este archivo UNA SOLA VEZ después de crear la BD:
#   python seed.py
#
# Esto inserta productos de ejemplo para que puedas ver
# la app funcionando sin tener que cargar datos a mano.
# ============================================================

from app import app, db, Producto
from datetime import datetime, timedelta
import random

# Lista de productos de ejemplo
# Mezcla productos con diferentes niveles de stock
# para que las alertas funcionen desde el principio
productos_ejemplo = [
    # --- Electrónica ---
    {
        'nombre': 'Laptop Dell Inspiron 15',
        'descripcion': 'Procesador Intel i5, 8GB RAM, 256GB SSD',
        'precio': 1850000,
        'cantidad': 12,
        'categoria': 'Electrónica'
    },
    {
        'nombre': 'Mouse Inalámbrico Logitech',
        'descripcion': 'Mouse ergonómico con receptor USB nano',
        'precio': 85000,
        'cantidad': 3,     # <-- Stock CRÍTICO (rojo)
        'categoria': 'Electrónica'
    },
    {
        'nombre': 'Teclado Mecánico RGB',
        'descripcion': 'Switches azules, retroiluminación RGB',
        'precio': 220000,
        'cantidad': 7,     # <-- Stock BAJO (amarillo)
        'categoria': 'Electrónica'
    },
    {
        'nombre': 'Monitor LG 24"',
        'descripcion': 'Full HD IPS, 75Hz, HDMI y DisplayPort',
        'precio': 650000,
        'cantidad': 15,
        'categoria': 'Electrónica'
    },
    {
        'nombre': 'Auriculares Sony WH-1000XM4',
        'descripcion': 'Cancelación de ruido activa, Bluetooth 5.0',
        'precio': 980000,
        'cantidad': 2,     # <-- Stock CRÍTICO
        'categoria': 'Electrónica'
    },

    # --- Papelería ---
    {
        'nombre': 'Resma de Papel A4',
        'descripcion': '500 hojas, 75g/m², blancura 92%',
        'precio': 18000,
        'cantidad': 45,
        'categoria': 'Papelería'
    },
    {
        'nombre': 'Bolígrafos BIC pack x12',
        'descripcion': 'Punta media, tinta azul, cuerpo transparente',
        'precio': 12000,
        'cantidad': 8,     # <-- Stock BAJO
        'categoria': 'Papelería'
    },
    {
        'nombre': 'Carpeta Archivadora A-Z',
        'descripcion': 'Lomo 8cm, cubierta plástica, varios colores',
        'precio': 9500,
        'cantidad': 30,
        'categoria': 'Papelería'
    },

    # --- Mobiliario ---
    {
        'nombre': 'Silla Ergonómica de Oficina',
        'descripcion': 'Soporte lumbar ajustable, apoyabrazos 3D',
        'precio': 520000,
        'cantidad': 4,     # <-- Stock CRÍTICO
        'categoria': 'Mobiliario'
    },
    {
        'nombre': 'Escritorio de Pie Regulable',
        'descripcion': 'Altura ajustable eléctrica, superficie 160x80cm',
        'precio': 1200000,
        'cantidad': 6,     # <-- Stock BAJO
        'categoria': 'Mobiliario'
    },

    # --- Limpieza ---
    {
        'nombre': 'Desinfectante Multiusos 1L',
        'descripcion': 'Elimina el 99.9% de bacterias, fragancia lavanda',
        'precio': 15000,
        'cantidad': 25,
        'categoria': 'Limpieza'
    },
    {
        'nombre': 'Papel Higiénico x12 rollos',
        'descripcion': 'Doble hoja, hoja larga, soft plus',
        'precio': 28000,
        'cantidad': 1,     # <-- Stock CRÍTICO (muy urgente)
        'categoria': 'Limpieza'
    },
]

def cargar_datos():
    with app.app_context():
        # Primero creamos las tablas si no existen
        db.create_all()

        # Verificamos si ya hay datos para no duplicar
        if Producto.query.count() > 0:
            print("⚠️  Ya hay datos en la base de datos.")
            print("   Si quieres reiniciar, borra el archivo instance/inventario.db")
            return

        print("📦 Cargando productos de ejemplo...")

        # Insertamos cada producto
        for i, datos in enumerate(productos_ejemplo):
            # Simulamos fechas de creación diferentes (útil para el historial)
            dias_atras = random.randint(1, 60)
            fecha = datetime.utcnow() - timedelta(days=dias_atras)

            producto = Producto(
                nombre=datos['nombre'],
                descripcion=datos['descripcion'],
                precio=datos['precio'],
                cantidad=datos['cantidad'],
                categoria=datos['categoria'],
                fecha_creacion=fecha
            )
            db.session.add(producto)
            print(f"   ✓ {datos['nombre']} ({datos['cantidad']} unidades)")

        # commit() guarda TODOS los cambios de una vez en la BD
        db.session.commit()
        print(f"\n✅ {len(productos_ejemplo)} productos cargados exitosamente!")
        print("   Abre http://localhost:5000 para verlos")

if __name__ == '__main__':
    cargar_datos()
