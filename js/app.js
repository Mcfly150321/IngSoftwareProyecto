const API_URL = "/api";
const API_URL_SCANNER = "/api";
let html5QrCode_Asistencia = null;
let isProcessing_Asistencia = false;
let currentScanId = null;

// Variables globales para los gráficos de Chart.js
let chartDiarioInstance = null;
let chartFindeInstance = null;

function logout() {
    sessionStorage.removeItem('userRol');
    sessionStorage.removeItem('userName');
    window.location.href = '/logout';
}

/**
 * FILTRADO POR ROL
 * Lee userRol de sessionStorage y muestra solo los nav links y secciones permitidos.
 * Gerente    → todo
 * Seguridad  → Dashboard, Registro, Pagos
 * Maquina    → Registro, Pagos
 */
function applyRolFilter() {
    const rol = (sessionStorage.getItem('userRol') || '').toLowerCase();
    const navLinks = document.querySelectorAll('.nav-link[data-roles]');

    let firstVisibleTarget = null;

    navLinks.forEach(link => {
        const allowed = link.dataset.roles.split(',').map(r => r.trim().toLowerCase());
        if (allowed.includes(rol)) {
            link.style.display = '';
            if (!firstVisibleTarget) firstVisibleTarget = link.dataset.target;
        } else {
            link.style.display = 'none';
        }
    });

    // Si la sección activa quedó oculta, activar la primera disponible
    const activeLink = document.querySelector('.nav-link.active');
    if (activeLink) {
        const activeRoles = (activeLink.dataset.roles || '').split(',').map(r => r.trim().toLowerCase());
        if (!activeRoles.includes(rol) && firstVisibleTarget) {
            // Simular clic en el primer link visible
            const firstLink = document.querySelector(`.nav-link[data-target="${firstVisibleTarget}"]`);
            if (firstLink) firstLink.click();
        }
    }
}

/** 
 * LOGICA DE NAVEGACION Y UI
 */

document.addEventListener('DOMContentLoaded', function() {
    // Configurar navegación
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.content-section');
    const pageTitle = document.getElementById('page-title');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const target = link.dataset.target;
            
            // UI Update
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            sections.forEach(s => s.classList.remove('active'));
            const targetSection = document.getElementById(target);
            if (targetSection) targetSection.classList.add('active');
            
            // Detener cámaras al cambiar de sección
            try { stopScannerExplicitScanner(); } catch(e) {}
            try { stopExitScanner(); } catch(e) {}
            try { stopEntryScanner(); } catch(e) {}
            try { stopRecargaScanner(); } catch(e) {}

            // Title update
            const titles = {
                'dashboard': 'Dashboard Parqueo',
                'parqueosadd': 'Agregar Parqueo',
                'tarifasadd': 'Agregar Tarifas',
                'empleadosadd': 'Agregar Empleado',
                'editarparqueos': 'Editar Parqueos',
                'editartarifas': 'Editar Tarifas',
                'inscripcion': 'Nuevo Ticket / Registro',
                'pagos': 'Control de Pagos / Salida',
                'recarga': 'Recargar Saldo de Ticket',
                'entrada': 'Entrada al Parqueo',
                'salida': 'Salida del Parqueo'
            };
            pageTitle.textContent = titles[target] || 'Sistema Parqueo';

            // Cargar datos según sección
            if (target === 'dashboard') updateDashboardStats();
            if (target === 'pagos') updatePagosUI();
            if (target === 'editarparqueos') loadParqueosEdit();
            if (target === 'editartarifas') loadTarifasEdit();
        });
    });

    // Título de pestaña dinámico: Rol - Nombre
    const tabRol = (sessionStorage.getItem('userRol') || '').toUpperCase();
    const tabName = sessionStorage.getItem('userName') || '';
    if (tabRol && tabName) document.title = `${tabRol} - ${tabName} | Parqueos`;

    // Lógica inicial del formulario de registro
    applyRolFilter();
    initRegistrationForm();
    initParqueoForm();
    initTarifaForm();
    initEmpleadoForm();
    
    // Iniciar monitoreo de conexión y stats
    updateDashboardStats();
    loadParqueosOptions();
    loadDropdowns();
    setInterval(checkConnectionStatus, 10000);
    setInterval(updateServerDateTime, 1000);
});

async function loadDropdowns() {
    try {
        const [resVehiculos, resUnidades] = await Promise.all([
            fetch(`${API_URL}/tipos-vehiculo/`),
            fetch(`${API_URL}/unidades-tiempo/`)
        ]);
        const vehiculos = await resVehiculos.json();
        const unidades = await resUnidades.json();

        // Llenar tipo vehiculo en tarifa
        const selTipoTarifa = document.getElementById('tipo_vehiculo_id_tarifa');
        if (selTipoTarifa) {
            selTipoTarifa.innerHTML = '<option value="">-- Seleccione tipo --</option>' + 
                vehiculos.map(v => `<option value="${v.id}">${v.nombre}</option>`).join('');
        }

        // Llenar unidad tiempo en tarifa
        const selUnidadTarifa = document.getElementById('unidad_tiempo_id');
        if (selUnidadTarifa) {
            selUnidadTarifa.innerHTML = '<option value="">-- Seleccione unidad --</option>' + 
                unidades.map(u => `<option value="${u.id}">${u.nombre}</option>`).join('');
        }

        // Llenar tipo vehiculo en registro de vehiculo
        const selTipoReg = document.getElementById('tipo_vehiculo_id_reg');
        if (selTipoReg) {
            selTipoReg.innerHTML = '<option value="">-- Seleccione tipo --</option>' + 
                vehiculos.map(v => `<option value="${v.id}">${v.nombre}</option>`).join('');
        }
    } catch (err) {
        console.error("Error cargando dropdowns:", err);
    }
}

async function loadParqueosOptions() {
    const select = document.getElementById('parking');
    if (!select) return;
    
    try {
        const res = await fetch(`${API_URL}/parqueos/`);
        const parqueos = await res.json();
        
        select.innerHTML = '<option value="">-- Seleccione un parqueo --</option>';
        parqueos.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            
            const cap = p.capacidad;
            const oc = p.ocupacion || 0;
            const full = oc >= cap;
            
            if (full) {
                opt.textContent = `❌ ${p.nombre} (LLENO: ${oc}/${cap})`;
                opt.disabled = true;
                opt.style.color = 'red';
            } else {
                opt.textContent = `✅ ${p.nombre} (Disp: ${cap - oc})`;
            }
            
            select.appendChild(opt);
        });
    } catch (e) {
        select.innerHTML = '<option value="">Error al cargar parqueos</option>';
    }
}

/** EDITAR PARQUEOS Y TARIFAS (ROL GERENTE) */

async function loadParqueosEdit() {
    const container = document.getElementById('parqueos-edit-list');
    if (!container) return;
    container.innerHTML = '<p>Cargando...</p>';
    try {
        const res = await fetch(`${API_URL}/parqueos/`);
        const parqueos = await res.json();
        container.innerHTML = parqueos.map(p => `
            <div class="card" style="padding:1rem; border:1px solid var(--border);">
                <div class="form-grid" style="grid-template-columns:1fr 1fr auto;">
                    <div class="form-group">
                        <label>Nombre</label>
                        <input type="text" id="p-nombre-${p.id}" value="${p.nombre}">
                    </div>
                    <div class="form-group">
                        <label>Capacidad Máxima</label>
                        <input type="number" id="p-cap-${p.id}" value="${p.capacidad}">
                    </div>
                    <div style="display:flex; align-items:flex-end;">
                        <button class="btn-primary" onclick="saveParqueo(${p.id})">💾 Guardar</button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (err) {
        container.innerHTML = `<p style="color:red;">❌ ${err.message}</p>`;
    }
}

async function saveParqueo(id) {
    const nombre = document.getElementById(`p-nombre-${id}`).value;
    const cap = parseInt(document.getElementById(`p-cap-${id}`).value);
    try {
        const res = await fetch(`${API_URL}/parqueos/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nombre, capacidad: cap })
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail);
        alert(`✅ Parqueo "${result.nombre}" actualizado.`);
        loadParqueosOptions();
    } catch (err) {
        alert(`❌ ${err.message}`);
    }
}

async function loadTarifasEdit() {
    const container = document.getElementById('tarifas-edit-list');
    if (!container) return;
    container.innerHTML = '<p>Cargando tarifas...</p>';
    try {
        const [resTarifas, resVehiculos, resUnidades] = await Promise.all([
            fetch(`${API_URL}/tarifas/`),
            fetch(`${API_URL}/tipos-vehiculo/`),
            fetch(`${API_URL}/unidades-tiempo/`)
        ]);
        const tarifas = await resTarifas.json();
        const vehiculos = await resVehiculos.json();
        const unidades = await resUnidades.json();

        container.innerHTML = tarifas.map(t => {
            const vehOptions = vehiculos.map(v => 
                `<option value="${v.id}" ${v.id === t.tipo_vehiculo_id ? 'selected' : ''}>${v.nombre}</option>`
            ).join('');
            const uniOptions = unidades.map(u => 
                `<option value="${u.id}" ${u.id === t.unidad_tiempo_id ? 'selected' : ''}>${u.nombre}</option>`
            ).join('');

            return `
            <div class="card" style="padding:1rem; border:1px solid var(--border); margin-bottom: 1rem;">
                <div class="form-grid" style="grid-template-columns:1fr 1fr 1fr auto; gap: 1rem; align-items: flex-end;">
                    <div class="form-group">
                        <label>Tipo de Vehículo</label>
                        <select id="t-veh-${t.id}">
                            ${vehOptions}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Unidad de Tiempo</label>
                        <select id="t-uni-${t.id}">
                            ${uniOptions}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Costo (Q)</label>
                        <input type="number" step="0.01" id="t-costo-${t.id}" value="${t.costo}">
                    </div>
                    <div>
                        <button class="btn-primary" onclick="saveTarifa(${t.id})">💾 Guardar</button>
                    </div>
                </div>
            </div>
            `;
        }).join('');
    } catch (err) {
        container.innerHTML = `<p style="color:red;">❌ ${err.message}</p>`;
    }
}

async function saveTarifa(id) {
    const tipo_vehiculo_id = parseInt(document.getElementById(`t-veh-${id}`).value);
    const unidad_tiempo_id = parseInt(document.getElementById(`t-uni-${id}`).value);
    const costo = parseFloat(document.getElementById(`t-costo-${id}`).value);
    try {
        const res = await fetch(`${API_URL}/tarifas/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tipo_vehiculo_id, unidad_tiempo_id, costo })
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || "Error al actualizar tarifa");
        alert(`✅ Tarifa actualizada exitosamente.`);
        loadTarifasEdit();
    } catch (err) {
        alert(`❌ ${err.message}`);
    }
}

async function checkConnectionStatus() {
    const dot = document.getElementById('conn-dot');
    const text = document.getElementById('conn-text');
    const startTime = performance.now();
    try {
        const res = await fetch(`${API_URL}/ping`);
        const endTime = performance.now();
        const latency = Math.round(endTime - startTime);

        if (res.ok) {
            let status = 'Excelente';
            let color = '#10b981'; // Green

            if (latency > 500) {
                status = 'Muy Lenta';
                color = '#f43f5e'; // Rose/Red
            } else if (latency > 300) {
                status = 'Lenta';
                color = '#f59e0b'; // Amber
            } else if (latency > 150) {
                status = 'Decente';
                color = '#3b82f6'; // Blue
            }

            dot.style.background = color;
            text.textContent = `Conectado (${latency}ms - ${status})`;
        } else {
            throw new Error();
        }
    } catch (e) {
        dot.style.background = '#ef4444';
        text.textContent = 'Desconectado';
    }
}

function updateServerDateTime() {
    const el = document.getElementById('server-datetime');
    if (!el) return;
    const now = new Date();
    el.textContent = now.toLocaleString('es-GT', { timeZone: 'America/Guatemala' });
}

async function withLoading(btn, asyncAction) {
    if (!btn) return await asyncAction();
    const originalContent = btn.innerHTML;
    const originalDisabled = btn.disabled;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cargando...';
    
    try {
        return await asyncAction();
    } finally {
        btn.disabled = originalDisabled;
        btn.innerHTML = originalContent;
    }
}

/**
 * SECCION: DASHBOARD
 */

async function updateDashboardStats() {
    try {
        const res = await fetch(`${API_URL}/stats`);
        const stats = await res.json();
        
        const statClients = document.getElementById('stat-clients');
        if (statClients) statClients.textContent = stats.clients || 0;

        if (stats.charts_data) renderAttendanceCharts(stats.charts_data);
        
        // Update server time if provided
        const serverTimeEl = document.getElementById('server-datetime');
        if (serverTimeEl && stats.server_datetime) {
            serverTimeEl.textContent = stats.server_datetime;
        }
    } catch (e) {
        console.error("Error al cargar stats:", e);
    }
}

function renderAttendanceCharts(data) {
    if (!data || !data.labels) return;
    
    const ctxDiario = document.getElementById('chart-diario')?.getContext('2d');
    // Usamos el primer canvas para mostrar todos los parqueos dinámicamente
    // Si hay muchos, Chart.js los manejará como barras en el mismo eje

    if (ctxDiario) {
        if (chartDiarioInstance) chartDiarioInstance.destroy();
        chartDiarioInstance = new Chart(ctxDiario, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Ocupación %',
                    data: data.values,
                    backgroundColor: data.labels.map((_, i) => i % 2 === 0 ? '#3b82f6' : '#10b981')
                }]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }
}


/** seccion de add parqueo */
function initParqueoForm() {
    const addParqueoForm = document.getElementById('add-parqueo-form');
    if (!addParqueoForm) return;

    addParqueoForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = document.getElementById('submitparqueo');
        await withLoading(submitBtn, async () => {
            const formData = new FormData(addParqueoForm);
            const data = Object.fromEntries(formData.entries());

            const newParqueo = {
                nombre: data.nombreparqueo,
                capacidad: parseInt(data.capacidad_maxima)
            };

            const url = `${API_URL}/parqueos/`;
            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(newParqueo)
                });
                const result = await res.json();
                if (!res.ok) throw new Error(result.detail || 'Error al crear parqueo');
                alert(`✅ Parqueo "${result.nombre}" creado exitosamente.`);
                addParqueoForm.reset();
                loadParqueosOptions();
            } catch (err) {
                alert(`❌ Error: ${err.message}`);
            }
        });
    });
}


/** hola a todos */
/**puta madre */





/** seccion de add empleado */
function checkEmpPasswords() {
    const p1 = document.getElementById('emp-password').value;
    const p2 = document.getElementById('emp-password2').value;
    const btn = document.getElementById('submitEmpleado');
    const msg = document.getElementById('emp-pass-msg');

    if (p2 === '') {
        msg.style.display = 'none';
        btn.disabled = true;
    } else if (p1 !== p2) {
        msg.style.display = 'block';
        btn.disabled = true;
    } else {
        msg.style.display = 'none';
        btn.disabled = false;
    }
}

function initEmpleadoForm() {
    const form = document.getElementById('add-empleado-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = document.getElementById('submitEmpleado');
        await withLoading(submitBtn, async () => {
            const fd = new FormData(form);
            const data = Object.fromEntries(fd.entries());

            const newEmpleado = {
                nombres: data.nombres,
                apellidos: data.apellidos,
                cui: data.cui,
                edad: parseInt(data.edad),
                rol: data.rol,
                user: data.user,
                passwd: data.password
            };
//comentando algo para actualizaarajnk

//aqui vamos a insertar comentarioa para que supeustamente detecte cambiosclecl

            try {
                const res = await fetch(`${API_URL}/empleados/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(newEmpleado)
                });
                const result = await res.json();
                if (!res.ok) throw new Error(result.detail || 'Error al crear empleado');
                alert(`✅ Empleado "${result.nombres} ${result.apellidos}" registrado exitosamente.`);
                form.reset();
                document.getElementById('submitEmpleado').disabled = true;
            } catch (err) {
                alert(`❌ Error: ${err.message}`);
            }
        });
    });
}

/** seccion de add tarifa */
function initTarifaForm() {
    const addTarifaForm = document.getElementById('add-tarifa-form');
    if (!addTarifaForm) return;

    addTarifaForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = document.getElementById('submittarifa');
        await withLoading(submitBtn, async () => {
            const formData = new FormData(addTarifaForm);
            const data = Object.fromEntries(formData.entries());

            const newTarifa = {
                tipo_vehiculo_id: parseInt(data.tipo_vehiculo_id),
                unidad_tiempo_id: parseInt(data.unidad_tiempo_id),
                costo: parseFloat(data.costotarif)
            };

            const url = `${API_URL}/tarifas/`;
            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(newTarifa)
                });
                const result = await res.json();
                if (!res.ok) throw new Error(result.detail || 'Error al crear tarifa');
                alert(`✅ Tarifa creada exitosamente.`);
                addTarifaForm.reset();

            } catch (err) {
                alert(`❌ Error: ${err.message}`);
            }
        });
    });
}

/**
 * SECCION: REGISTRO (NUEVO TICKET)
 */

function initRegistrationForm() {
    const regForm = document.getElementById('registration-form');
    if (!regForm) return;

    regForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = e.target.querySelector('button[type="submit"]');

        await withLoading(submitBtn, async () => {
            const formData = new FormData(regForm);
            const data = Object.fromEntries(formData.entries());

            const clientData = {
                nombres: data.nombres || "",
                apellidos: data.apellidos || "",
                dpi: data.dpi || "",
                placa: data.placa || "", 
                tipo_vehiculo_id: parseInt(data.tipo_vehiculo_id || 1),
                numero: data.numero ? parseInt(data.numero) : null
            };

            try {
                // 1. Registrar cliente directo
                const clientRes = await fetch(`${API_URL}/clients/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(clientData)
                });
                
                if (!clientRes.ok) {
                    const errorData = await clientRes.json();
                    throw new Error(errorData.detail || "Error al guardar registro del cliente");
                }

                const { client_id, ticket_url, whatsapp_url } = await clientRes.json();

                // 2. Registrar entrada directa
                const entRes = await fetch(`${API_URL}/entradas-salidas/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ client_id, tipo: "entrada" })
                });

                if (!entRes.ok) {
                    throw new Error("Error al registrar entrada en parqueo");
                }

                // 3. Mostrar ticket y abrir WhatsApp si aplica
                const msgEl = document.getElementById("message-registration");
                if (msgEl) {
                    msgEl.innerHTML = `<div style="background-color: #d1fae5; color: #065f46; padding: 12px; border-radius: 8px; font-weight: 600; border: 1px solid #10b981; margin-top: 10px;">✅ ¡Vehículo ingresado y ticket generado exitosamente!<br><b>Ticket ID:</b> ${client_id}</div>`;
                }
                
                if (ticket_url) {
                    window.open(ticket_url, '_blank');
                }
                
                if (whatsapp_url) {
                    window.open(whatsapp_url, '_blank');
                }

                // Limpiar formulario y actualizar vista
                regForm.reset();
                updateDashboardStats();

            } catch (err) {
                const msgEl = document.getElementById("message-registration");
                if (msgEl) {
                    msgEl.innerHTML = `<div style="background-color: #fee2e2; color: #991b1b; padding: 12px; border-radius: 8px; font-weight: 600; border: 1px solid #ef4444; margin-top: 10px;">❌ Error: ${err.message}</div>`;
                }
            }
        });
    });
}
/**
 * SECCION: PAGOS (ESCÁNER DE SALIDA)
 */

const audioCtx_Scanner = new (window.AudioContext || window.webkitAudioContext)();

function playBeepScanner() {
    const oscillator = audioCtx_Scanner.createOscillator();
    const gainNode = audioCtx_Scanner.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(audioCtx_Scanner.destination);
    oscillator.type = "sine"; 
    oscillator.frequency.setValueAtTime(1046.50, audioCtx_Scanner.currentTime); 
    gainNode.gain.setValueAtTime(0, audioCtx_Scanner.currentTime);
    gainNode.gain.linearRampToValueAtTime(0.15, audioCtx_Scanner.currentTime + 0.02);
    gainNode.gain.linearRampToValueAtTime(0.10, audioCtx_Scanner.currentTime + 0.15);
    gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx_Scanner.currentTime + 0.5);
    oscillator.start();
    oscillator.stop(audioCtx_Scanner.currentTime + 0.55);
}

function playErrorBeepScanner() {
    const oscillator = audioCtx_Scanner.createOscillator();
    const gainNode = audioCtx_Scanner.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(audioCtx_Scanner.destination);
    oscillator.type = "sawtooth";
    oscillator.frequency.setValueAtTime(220, audioCtx_Scanner.currentTime);
    gainNode.gain.setValueAtTime(0, audioCtx_Scanner.currentTime);
    gainNode.gain.linearRampToValueAtTime(0.1, audioCtx_Scanner.currentTime + 0.05);
    gainNode.gain.linearRampToValueAtTime(0.1, audioCtx_Scanner.currentTime + 0.3);
    gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx_Scanner.currentTime + 0.6);
    oscillator.start();
    oscillator.stop(audioCtx_Scanner.currentTime + 0.65);
}

function updatePagosUI() {
    const serverDateEl = document.getElementById('server-date');
    if (serverDateEl) {
        const now = new Date();
        serverDateEl.textContent = now.toLocaleDateString('es-GT', { timeZone: 'America/Guatemala', day: '2-digit', month: 'long', year: 'numeric' });
    }
}

async function startScannerPagos() {
    if (html5QrCode_Asistencia) return;
    
    html5QrCode_Asistencia = new Html5Qrcode("reader-scanner");
    const config = { fps: 20, qrbox: { width: 250, height: 250 } };

    document.getElementById("btnStartScanner-scanner").style.display = "none";
    document.getElementById("btnStopScanner-scanner").style.display = "inline-block";

    try {
        await html5QrCode_Asistencia.start({ facingMode: "environment" }, config, onScanSuccessPagos);
    } catch (err) {
        console.error("No se pudo iniciar la cámara:", err);
        alert("No se pudo acceder a la cámara");
    }
}

async function stopScannerExplicitScanner() {
    if (html5QrCode_Asistencia) {
        await html5QrCode_Asistencia.stop();
        html5QrCode_Asistencia = null;
    }
    document.getElementById("btnStartScanner-scanner").style.display = "inline-block";
    document.getElementById("btnStopScanner-scanner").style.display = "none";
}

async function onScanSuccessPagos(decodedText) {
    if (isProcessing_Asistencia) return;
    isProcessing_Asistencia = true;

    if (audioCtx_Scanner.state === 'suspended') audioCtx_Scanner.resume();

    await stopScannerExplicitScanner();

    setTimeout(async () => {
        try {
            const dateStr = new Date().toISOString().split('T')[0];
            const res = await fetch(`${API_URL}/calcular-cobro/${encodeURIComponent(decodedText)}`, { method: "GET" });
            const data = await res.json();
            
            if (!res.ok) {
                if (data.detail === "exited") {
                    playBeepScanner();
                    showResultUI_ExitSuccess({ client_name: decodedText, message: "Vehículo ya registrado con salida" });
                    return;
                }
                throw new Error(data.detail || "ID no válido o vehículo ya pagado");
            }

            playBeepScanner();
            showResultUI_Pagos(data);
        } catch (err) {
            playErrorBeepScanner();
            showResultUI_Error(err.message);
        }
    }, 300);
}

function showResultUI_Pagos(data) {
    const overlay = document.getElementById("resultOverlay-scanner");
    const successCircle = document.getElementById("successCircle-scanner");
    const errorCircle = document.getElementById("errorCircle-scanner");
    const resultName = document.getElementById("scanResultName-scanner");
    const invoiceDetails = document.getElementById("invoice-details-scanner");
    const btnNext = document.getElementById("btnNext-scanner");
    const btnConfirm = document.getElementById("btnConfirmPay-scanner");

    currentScanId = data.client_id;
    resultName.textContent = data.nombres;
    
    // Fill Invoice Details
    document.getElementById("inv-nit").textContent = data.client_id; // Ya no hay NIT, mostramos ID
    document.getElementById("inv-entry").textContent = new Date(data.ultima_entrada).toLocaleTimeString();
    document.getElementById("inv-exit").textContent = new Date().toLocaleTimeString();
    document.getElementById("inv-total").textContent = `Q${data.total_cobrar.toFixed(2)}`;
    
    invoiceDetails.style.display = "block";
    btnNext.style.display = "none";
    btnConfirm.style.display = "block";

    overlay.classList.add("active");
    successCircle.style.display = "flex";
    errorCircle.style.display = "none";
}

function showResultUI_ExitSuccess(data) {
    const overlay = document.getElementById("resultOverlay-scanner");
    const successCircle = document.getElementById("successCircle-scanner");
    const errorCircle = document.getElementById("errorCircle-scanner");
    const resultName = document.getElementById("scanResultName-scanner");
    const invoiceDetails = document.getElementById("invoice-details-scanner");
    const btnNext = document.getElementById("btnNext-scanner");
    const btnConfirm = document.getElementById("btnConfirmPay-scanner");

    resultName.textContent = `${data.client_name}: ${data.message}`;
    invoiceDetails.style.display = "none";
    btnNext.style.display = "block";
    btnConfirm.style.display = "none";

    overlay.classList.add("active");
    successCircle.style.display = "flex";
    errorCircle.style.display = "none";

    updateDashboardStats();
    
    // Auto reset for checkout
    setTimeout(() => {
        resetForNextScanner();
    }, 2000);
}

function showResultUI_Error(msg) {
    const overlay = document.getElementById("resultOverlay-scanner");
    const successCircle = document.getElementById("successCircle-scanner");
    const errorCircle = document.getElementById("errorCircle-scanner");
    const resultName = document.getElementById("scanResultName-scanner");
    const invoiceDetails = document.getElementById("invoice-details-scanner");
    const btnNext = document.getElementById("btnNext-scanner");
    const btnConfirm = document.getElementById("btnConfirmPay-scanner");

    resultName.textContent = msg;
    invoiceDetails.style.display = "none";
    btnNext.style.display = "block";
    btnConfirm.style.display = "none";

    overlay.classList.add("active");
    successCircle.style.display = "none";
    errorCircle.style.display = "flex";
}

function resetForNextScanner() {
    document.getElementById("resultOverlay-scanner").classList.remove("active");
    document.getElementById("invoice-details-scanner").style.display = "none";
    isProcessing_Asistencia = false;
    currentScanId = null;
    
    // Clear all textual fields
    document.getElementById("scanResultName-scanner").textContent = "";
    document.getElementById("inv-nit").textContent = "-";
    document.getElementById("inv-entry").textContent = "-";
    document.getElementById("inv-exit").textContent = "-";
    
    const totalEl = document.getElementById("inv-total");
    totalEl.textContent = "Q0.00";
    totalEl.style.color = ""; // Reset color
    
    startScannerPagos(); 
}

async function confirmCurrentPayment() {
    if (!currentScanId) return;
    const btn = document.getElementById("btnConfirmPay-scanner");
    const msgEl = document.getElementById("message-scanner");
    if (msgEl) msgEl.innerHTML = "";
    
    await withLoading(btn, async () => {
        try {
            const res = await fetch(`${API_URL}/cobrar/${currentScanId}`, { 
                method: 'POST'
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Error al procesar pago");
            
            // Show success on the card
            btn.style.display = "none";
            document.getElementById("btnNext-scanner").style.display = "block";
            document.getElementById("inv-total").style.color = "#10b981";
            document.getElementById("inv-total").textContent = `Q${data.monto_cobrado.toFixed(2)} [PAGADO]`;
            
            if (msgEl) {
                msgEl.innerHTML = `<div style="background-color: #d1fae5; color: #065f46; padding: 12px; border-radius: 8px; font-weight: 600; border: 1px solid #10b981; margin-top: 10px;">✅ Pago procesado exitosamente por Q${data.monto_cobrado.toFixed(2)}. Saldo restante: Q${data.saldo_restante.toFixed(2)}</div>`;
            }

            updateDashboardStats();

            // Auto-reset after 1.5 seconds
            setTimeout(() => {
                if (currentScanId === data.client_id) { // Solo si no han escaneado a alguien más (seguridad)
                    resetForNextScanner();
                }
            }, 1500);
        } catch (err) {
            if (msgEl) {
                msgEl.innerHTML = `<div style="background-color: #fee2e2; color: #991b1b; padding: 12px; border-radius: 8px; font-weight: 600; border: 1px solid #ef4444; margin-top: 10px;">❌ Error: ${err.message}</div>`;
            }
        }
    });
}
async function closeAllTransactions() {
    await stopScannerExplicitScanner();
    document.getElementById("resultOverlay-scanner").classList.remove("active");
    document.getElementById("invoice-details-scanner").style.display = "none";
    isProcessing_Asistencia = false;
    currentScanId = null;
    
    // Reset message
    const msgEl = document.getElementById("message-scanner");
    if (msgEl) msgEl.textContent = "";
}

/**
 * SECCION: SALIDA (SCANNER DE SALIDA - ROL SEGURIDAD)
 */
let html5QrCode_Exit = null;
let isProcessing_Exit = false;

async function startExitScanner() {
    if (html5QrCode_Exit) return;
    html5QrCode_Exit = new Html5Qrcode("reader-exit");
    const config = { fps: 20, qrbox: { width: 250, height: 250 } };

    document.getElementById("btnStartScanner-exit").style.display = "none";
    document.getElementById("btnStopScanner-exit").style.display = "inline-block";

    try {
        await html5QrCode_Exit.start(
            { facingMode: "environment" },
            config,
            onScanSuccessExit
        );
    } catch (err) {
        html5QrCode_Exit = null;
        document.getElementById("btnStartScanner-exit").style.display = "inline-block";
        document.getElementById("btnStopScanner-exit").style.display = "none";
        const msgEl = document.getElementById("message-exit");
        if (msgEl) msgEl.textContent = "❌ No se pudo iniciar la cámara.";
    }
}

async function stopExitScanner() {
    if (html5QrCode_Exit) {
        try { await html5QrCode_Exit.stop(); } catch {}
        html5QrCode_Exit = null;
    }
    document.getElementById("btnStartScanner-exit").style.display = "inline-block";
    document.getElementById("btnStopScanner-exit").style.display = "none";
}

function resetExitScanner() {
    const overlay = document.getElementById("resultOverlay-exit");
    if (overlay) overlay.classList.remove("active");
    const nameEl = document.getElementById("scanResultName-exit");
    if (nameEl) nameEl.textContent = "";
    const successCircle = document.getElementById("successCircle-exit");
    const errorCircle = document.getElementById("errorCircle-exit");
    if (successCircle) successCircle.style.display = "flex";
    if (errorCircle) errorCircle.style.display = "none";
    isProcessing_Exit = false;
    stopExitScanner();
}

async function onScanSuccessExit(decodedText) {
    if (isProcessing_Exit) return;
    isProcessing_Exit = true;

    if (audioCtx_Scanner.state === 'suspended') audioCtx_Scanner.resume();
    await stopExitScanner();

    setTimeout(async () => {
        try {
            const res = await fetch(`${API_URL}/entradas-salidas/`, { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    client_id: decodedText,
                    tipo: "salida"
                })
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.detail || "Error al procesar salida");

            playBeepScanner();
            // Mostrar éxito
            const overlay = document.getElementById("resultOverlay-exit");
            const successCircle = document.getElementById("successCircle-exit");
            const errorCircle = document.getElementById("errorCircle-exit");
            const nameEl = document.getElementById("scanResultName-exit");

            nameEl.textContent = `Salida registrada exitosamente (Ticket: ${data.client_id})`;
            successCircle.style.display = "flex";
            errorCircle.style.display = "none";
            overlay.classList.add("active");
            updateDashboardStats();

            // Auto-reset 2 segundos
            setTimeout(() => resetExitScanner(), 2000);

        } catch (err) {
            playErrorBeepScanner();
            const overlay = document.getElementById("resultOverlay-exit");
            const successCircle = document.getElementById("successCircle-exit");
            const errorCircle = document.getElementById("errorCircle-exit");
            const nameEl = document.getElementById("scanResultName-exit");

            nameEl.textContent = err.message;
            successCircle.style.display = "none";
            errorCircle.style.display = "flex";
            overlay.classList.add("active");
            isProcessing_Exit = false;

            // Auto-reiniciar cámara al error para el siguiente scan
            setTimeout(() => {
                overlay.classList.remove("active");
                isProcessing_Exit = false;
                startExitScanner();
            }, 2500);
        }
    }, 300);
}


/**
 * SECCION: ENTRADA (SCANNER DE ENTRADA - ROL SEGURIDAD)
 */
let html5QrCode_Entry = null;
let isProcessing_Entry = false;

async function startEntryScanner() {
    if (html5QrCode_Entry) return;
    html5QrCode_Entry = new Html5Qrcode("reader-entry");
    const config = { fps: 20, qrbox: { width: 250, height: 250 } };

    document.getElementById("btnStartScanner-entry").style.display = "none";
    document.getElementById("btnStopScanner-entry").style.display = "inline-block";

    try {
        await html5QrCode_Entry.start(
            { facingMode: "environment" },
            config,
            onScanSuccessEntry
        );
    } catch (err) {
        html5QrCode_Entry = null;
        document.getElementById("btnStartScanner-entry").style.display = "inline-block";
        document.getElementById("btnStopScanner-entry").style.display = "none";
        const msgEl = document.getElementById("message-entry");
        if (msgEl) msgEl.textContent = "❌ No se pudo iniciar la cámara.";
    }
}

async function stopEntryScanner() {
    if (html5QrCode_Entry) {
        try { await html5QrCode_Entry.stop(); } catch {}
        html5QrCode_Entry = null;
    }
    document.getElementById("btnStartScanner-entry").style.display = "inline-block";
    document.getElementById("btnStopScanner-entry").style.display = "none";
}

function resetEntryScanner() {
    const overlay = document.getElementById("resultOverlay-entry");
    if (overlay) overlay.classList.remove("active");
    const nameEl = document.getElementById("scanResultName-entry");
    if (nameEl) nameEl.textContent = "";
    const successCircle = document.getElementById("successCircle-entry");
    const errorCircle = document.getElementById("errorCircle-entry");
    if (successCircle) successCircle.style.display = "flex";
    if (errorCircle) errorCircle.style.display = "none";
    isProcessing_Entry = false;
    stopEntryScanner();
}

async function onScanSuccessEntry(decodedText) {
    if (isProcessing_Entry) return;
    isProcessing_Entry = true;

    if (audioCtx_Scanner.state === 'suspended') audioCtx_Scanner.resume();
    await stopEntryScanner();

    setTimeout(async () => {
        try {
            const res = await fetch(`${API_URL}/entradas-salidas/`, { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    client_id: decodedText,
                    tipo: "entrada"
                })
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.detail || "Error al procesar entrada");

            playBeepScanner();
            // Mostrar éxito
            const overlay = document.getElementById("resultOverlay-entry");
            const successCircle = document.getElementById("successCircle-entry");
            const errorCircle = document.getElementById("errorCircle-entry");
            const nameEl = document.getElementById("scanResultName-entry");

            nameEl.textContent = `Entrada registrada exitosamente (Ticket: ${data.client_id})`;
            successCircle.style.display = "flex";
            errorCircle.style.display = "none";
            overlay.classList.add("active");
            updateDashboardStats();

            // Auto-reset 2 segundos
            setTimeout(() => resetEntryScanner(), 2000);

        } catch (err) {
            playErrorBeepScanner();
            const overlay = document.getElementById("resultOverlay-entry");
            const successCircle = document.getElementById("successCircle-entry");
            const errorCircle = document.getElementById("errorCircle-entry");
            const nameEl = document.getElementById("scanResultName-entry");

            nameEl.textContent = err.message;
            successCircle.style.display = "none";
            errorCircle.style.display = "flex";
            overlay.classList.add("active");
            isProcessing_Entry = false;

            // Auto-reiniciar cámara al error para el siguiente scan
            setTimeout(() => {
                overlay.classList.remove("active");
                isProcessing_Entry = false;
                startEntryScanner();
            }, 2500);
        }
    }, 300);
}


/**
 * SECCION: RECARGA SALDO (CON LECTOR QR Y BOTONES DE MONTO)
 */
let html5QrCode_Recarga = null;
let isProcessing_Recarga = false;
let currentRechargeClientId = null;

async function startRecargaScanner() {
    if (html5QrCode_Recarga) return;
    html5QrCode_Recarga = new Html5Qrcode("reader-recarga");
    const config = { fps: 20, qrbox: { width: 250, height: 250 } };

    document.getElementById("btnStartScanner-recarga").style.display = "none";
    document.getElementById("btnStopScanner-recarga").style.display = "inline-block";
    document.getElementById("rechargePanel").style.display = "none";

    try {
        await html5QrCode_Recarga.start(
            { facingMode: "environment" },
            config,
            onScanSuccessRecarga
        );
    } catch (err) {
        html5QrCode_Recarga = null;
        document.getElementById("btnStartScanner-recarga").style.display = "inline-block";
        document.getElementById("btnStopScanner-recarga").style.display = "none";
        const msgEl = document.getElementById("message-recarga");
        if (msgEl) msgEl.textContent = "❌ No se pudo iniciar la cámara.";
    }
}

async function stopRecargaScanner() {
    if (html5QrCode_Recarga) {
        try { await html5QrCode_Recarga.stop(); } catch {}
        html5QrCode_Recarga = null;
    }
    document.getElementById("btnStartScanner-recarga").style.display = "inline-block";
    document.getElementById("btnStopScanner-recarga").style.display = "none";
}

function resetRecargaScanner() {
    const overlay = document.getElementById("resultOverlay-recarga");
    if (overlay) overlay.classList.remove("active");
    const nameEl = document.getElementById("scanResultName-recarga");
    if (nameEl) nameEl.textContent = "";
    const successCircle = document.getElementById("successCircle-recarga");
    const errorCircle = document.getElementById("errorCircle-recarga");
    if (successCircle) successCircle.style.display = "flex";
    if (errorCircle) errorCircle.style.display = "none";
    
    document.getElementById("rechargePanel").style.display = "none";
    currentRechargeClientId = null;
    isProcessing_Recarga = false;
    stopRecargaScanner();
}

async function onScanSuccessRecarga(decodedText) {
    if (isProcessing_Recarga) return;
    isProcessing_Recarga = true;

    if (audioCtx_Scanner.state === 'suspended') audioCtx_Scanner.resume();
    await stopRecargaScanner();

    setTimeout(async () => {
        try {
            // 1. Obtener balance del cliente
            const res = await fetch(`${API_URL}/balance/${decodedText}`);
            const data = await res.json();

            if (!res.ok) throw new Error(data.detail || "Ticket o cliente no encontrado en la base de datos");

            playBeepScanner();
            
            // 2. Cargar panel de recarga
            currentRechargeClientId = decodedText;
            document.getElementById("rechargeClientName").textContent = data.nombres;
            document.getElementById("rechargeClientId").textContent = decodedText;
            document.getElementById("rechargeCurrentBalance").textContent = `Q${data.saldo.toFixed(2)}`;
            
            document.getElementById("rechargePanel").style.display = "block";
            isProcessing_Recarga = false;

        } catch (err) {
            playErrorBeepScanner();
            const overlay = document.getElementById("resultOverlay-recarga");
            const successCircle = document.getElementById("successCircle-recarga");
            const errorCircle = document.getElementById("errorCircle-recarga");
            const nameEl = document.getElementById("scanResultName-recarga");

            nameEl.textContent = err.message;
            successCircle.style.display = "none";
            errorCircle.style.display = "flex";
            overlay.classList.add("active");
            isProcessing_Recarga = false;

            // Auto-reiniciar cámara al error para el siguiente scan
            setTimeout(() => {
                overlay.classList.remove("active");
                isProcessing_Recarga = false;
                startRecargaScanner();
            }, 2500);
        }
    }, 300);
}

async function executeRecharge(btn, monto) {
    if (!currentRechargeClientId) return;
    const msgEl = document.getElementById("message-recarga");
    if (msgEl) msgEl.innerHTML = "";

    await withLoading(btn, async () => {
        try {
            const res = await fetch(`${API_URL}/recargar/${currentRechargeClientId}?monto=${monto}`, {
                method: 'POST'
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.detail || "Error al procesar recarga");

            if (msgEl) {
                msgEl.innerHTML = `<div style="background-color: #d1fae5; color: #065f46; padding: 12px; border-radius: 8px; font-weight: 600; border: 1px solid #10b981; margin-top: 10px;">✅ ¡Recarga de Q${monto.toFixed(2)} procesada con éxito! Nuevo saldo: Q${data.nuevo_saldo.toFixed(2)}</div>`;
            }
            
            // Actualizar el saldo mostrado en pantalla
            document.getElementById("rechargeCurrentBalance").textContent = `Q${data.nuevo_saldo.toFixed(2)}`;

        } catch (err) {
            if (msgEl) {
                msgEl.innerHTML = `<div style="background-color: #fee2e2; color: #991b1b; padding: 12px; border-radius: 8px; font-weight: 600; border: 1px solid #ef4444; margin-top: 10px;">❌ Error al recargar: ${err.message}</div>`;
            }
        }
    });
}
