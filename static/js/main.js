// ============================================================
// main.js — JavaScript del sistema PISYS
// ============================================================
// Por ahora este archivo es pequeño. En semanas posteriores
// agregaremos más interactividad aquí:
//   - Semana 6: confirmación de eliminación de productos
//   - Semana 10: inicialización de gráficos Plotly
// ============================================================

// Esperamos a que el HTML esté listo antes de ejecutar el código
document.addEventListener('DOMContentLoaded', function() {

    console.log('✅ PISYS cargado correctamente');

    // ------ AUTO-CERRAR ALERTAS FLASH ------
    // Los mensajes de éxito/error de Flask se cierran solos
    // después de 4 segundos para no molestar al usuario
    const alertas = document.querySelectorAll('.alert');
    alertas.forEach(function(alerta) {
        setTimeout(function() {
            // Bootstrap tiene una clase "fade" para animación de salida
            alerta.classList.remove('show');
            // Esperamos que termine la animación (300ms) y lo quitamos del DOM
            setTimeout(function() {
                alerta.remove();
            }, 300);
        }, 4000); // 4000ms = 4 segundos
    });


    // ------ RESALTAR FILA ACTIVA EN TABLA ------
    // Cuando el mouse pasa sobre una fila de la tabla de productos,
    // el CSS ya maneja el cambio de color (ver .fila-producto:hover).
    // Aquí podríamos agregar lógica más avanzada si la necesitáramos.


    // ------ NAVBAR: INDICADOR DE PÁGINA ACTIVA ------
    // Bootstrap ya maneja esto con la clase 'active' en base.html,
    // pero agregamos un console.log para depuración.
    const linkActivo = document.querySelector('.nav-link.active');
    if (linkActivo) {
        console.log('📍 Página activa:', linkActivo.textContent.trim());
    }

});


// ============================================================
// FUNCIONES DE UTILIDAD (para usar en semanas futuras)
// ============================================================

/**
 * Formatea un número como moneda colombiana
 * Ej: formatearMoneda(1850000) → "$1.850.000"
 * 
 * En semana 10 la usaremos en los gráficos de Plotly.
 */
function formatearMoneda(numero) {
    return '$' + numero.toLocaleString('es-CO');
}

/**
 * Muestra una notificación temporal en la pantalla
 * Por ahora usamos los flash messages de Flask,
 * pero esta función será útil para acciones AJAX en el futuro.
 */
function mostrarNotificacion(mensaje, tipo = 'success') {
    const notif = document.createElement('div');
    notif.className = `alert alert-${tipo} alert-dismissible fade show position-fixed`;
    notif.style.cssText = 'top: 80px; right: 20px; z-index: 9999; min-width: 300px;';
    notif.innerHTML = `
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(notif);

    // Auto-eliminar después de 3 segundos
    setTimeout(function() {
        notif.classList.remove('show');
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}
