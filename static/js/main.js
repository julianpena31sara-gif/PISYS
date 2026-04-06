// main.js — JavaScript principal de PISYS

document.addEventListener('DOMContentLoaded', function () {

    console.log('✅ PISYS cargado');

    // Auto-cerrar alertas flash después de 4 segundos
    document.querySelectorAll('.alert').forEach(function (alerta) {
        setTimeout(function () {
            alerta.classList.remove('show');
            setTimeout(() => alerta.remove(), 300);
        }, 4000);
    });

    // Aplicar tema guardado al cargar la página
    _aplicarTema(localStorage.getItem('pisys-tema') || 'claro');

});


// ── MODO OSCURO / CLARO ──────────────────────────────────────

function toggleTema() {
    const temaActual = localStorage.getItem('pisys-tema') || 'claro';
    const nuevoTema  = temaActual === 'claro' ? 'oscuro' : 'claro';
    localStorage.setItem('pisys-tema', nuevoTema);
    _aplicarTema(nuevoTema);
}

function _aplicarTema(tema) {
    const body  = document.body;
    const html  = document.documentElement;
    const icono = document.getElementById('icono-tema');

    if (tema === 'oscuro') {
        body.classList.add('tema-oscuro');
        html.classList.add('tema-oscuro');
        if (icono) icono.classList.replace('bi-moon-fill', 'bi-sun-fill');
    } else {
        body.classList.remove('tema-oscuro');
        html.classList.remove('tema-oscuro');
        if (icono) icono.classList.replace('bi-sun-fill', 'bi-moon-fill');
    }
}


// ── UTILIDADES ───────────────────────────────────────────────

function formatearMoneda(numero) {
    return '$' + numero.toLocaleString('es-CO');
}

function mostrarNotificacion(mensaje, tipo = 'success') {
    const notif = document.createElement('div');
    notif.className = `alert alert-${tipo} alert-dismissible fade show position-fixed`;
    notif.style.cssText = 'top: 80px; right: 20px; z-index: 9999; min-width: 300px;';
    notif.innerHTML = `${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.body.appendChild(notif);
    setTimeout(() => {
        notif.classList.remove('show');
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}
