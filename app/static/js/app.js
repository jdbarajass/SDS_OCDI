/* ─────────────────────────────────────────────────
   OCDI — Lógica de formulario y UI
   ───────────────────────────────────────────────── */

// ── TABS DEL FORMULARIO ───────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const tabBtns = document.querySelectorAll('.tab-btn');
    if (tabBtns.length === 0) return;

    tabBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const targetId = btn.getAttribute('data-target');

            // Desactivar todos
            tabBtns.forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.form-section').forEach(s => s.classList.remove('active'));

            // Activar el seleccionado
            btn.classList.add('active');
            const section = document.getElementById(targetId);
            if (section) section.classList.add('active');
        });
    });
});

// ── MOSTRAR/OCULTAR CAMPO CONDICIONAL ─────────────
function toggleField(wrapId, radioValue) {
    const wrap = document.getElementById(wrapId);
    if (!wrap) return;
    wrap.style.display = (radioValue === 'SI') ? '' : 'none';
}

// ── TOGGLE SECCIÓN INVESTIGACIÓN DISCIPLINARIA ────
function toggleInvestigacion(valor) {
    const tabInv = document.getElementById('tab-inv');
    const secInv = document.getElementById('sec-5');
    const badge  = document.getElementById('inv-badge');

    const esInv = valor && valor.includes('INVESTIGACIÓN');

    if (tabInv) {
        tabInv.style.opacity = esInv ? '1' : '0.5';
        tabInv.title = esInv ? '' : 'Solo aplica si la etapa es Investigación Disciplinaria';
    }
    if (badge) {
        badge.textContent = esInv ? '✅ Aplica' : 'Solo si aplica';
        badge.style.background = esInv ? 'var(--success-bg)' : '';
        badge.style.color = esInv ? 'var(--success)' : '';
    }
}

// ── CALCULAR FECHA DE VENCIMIENTO ─────────────────
function calcularVencimiento(bloque) {
    // bloque: 'ind' o 'inv'
    const campoFecha = document.getElementById('fecha_apertura_' + (bloque === 'ind' ? 'indagacion' : 'investigacion'));
    const campoPlazo = document.getElementById('plazo_' + bloque);
    const campoVenc  = document.getElementById('fecha_vencimiento_' + bloque);

    if (!campoFecha || !campoPlazo || !campoVenc) return;

    const fechaStr = campoFecha.value;
    const plazo    = parseInt(campoPlazo.value);

    if (!fechaStr || isNaN(plazo)) {
        return;
    }

    const fecha = new Date(fechaStr + 'T00:00:00');
    fecha.setDate(fecha.getDate() + plazo);

    const yyyy = fecha.getFullYear();
    const mm   = String(fecha.getMonth() + 1).padStart(2, '0');
    const dd   = String(fecha.getDate()).padStart(2, '0');

    campoVenc.value = `${yyyy}-${mm}-${dd}`;
}

// ── ESCANEOS DINÁMICOS ────────────────────────────
let contadorEscaneo = 0;

// Contar escaneos existentes al cargar la página
document.addEventListener('DOMContentLoaded', function () {
    const existentes = document.querySelectorAll('.escaneo-row');
    contadorEscaneo = existentes.length;
});

function agregarEscaneo() {
    const container = document.getElementById('escaneos-container');
    if (!container) return;

    const idx = contadorEscaneo++;
    const row = document.createElement('div');
    row.className = 'escaneo-row';
    row.dataset.idx = idx;
    row.innerHTML = `
        <div class="form-grid form-grid-3">
            <div class="field-group">
                <label>Fecha Escáner</label>
                <input type="date" name="escaner_fecha_${idx}">
            </div>
            <div class="field-group">
                <label>Folio</label>
                <input type="text" name="escaner_folio_${idx}" placeholder="Ej: 1-45">
            </div>
            <div class="field-group">
                <label>Responsable</label>
                <input type="text" name="escaner_responsable_${idx}" placeholder="Nombre del responsable">
            </div>
        </div>
        <button type="button" class="btn-remove-row" onclick="quitarEscaneo(this)">✖ Quitar</button>
    `;
    container.appendChild(row);
}

function quitarEscaneo(btn) {
    const row = btn.closest('.escaneo-row');
    if (row) {
        row.remove();
        // Re-numerar los índices para que sean consecutivos al enviar
        renumerarEscaneos();
    }
}

function renumerarEscaneos() {
    const rows = document.querySelectorAll('.escaneo-row');
    rows.forEach(function (row, i) {
        row.querySelectorAll('input').forEach(function (input) {
            const name = input.name;
            // Reemplazar el número al final del nombre
            input.name = name.replace(/_\d+$/, '_' + i);
        });
        row.dataset.idx = i;
    });
    contadorEscaneo = rows.length;
}
