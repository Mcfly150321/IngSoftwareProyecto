const API_URL = "/api";
const API_URL_SCANNER = "/api";
let html5QrCode_Asistencia = null;
let isProcessing_Asistencia = false;
let currentScanId = null;

// Variables globales para los gráficos de Chart.js
let chartDiarioInstance = null;
let chartFindeInstance = null;

function logout() {
    window.location.href = '/logout';
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
            
            // Title update
            const titles = {
                'dashboard': 'Dashboard Parqueo',
                'parqueosadd': 'Agregar Parqueo',
                'tarifasadd': 'Agregar Tarifas',
                'empleadosadd': 'Agregar Empleado',
                'inscripcion': 'Nuevo Ticket / Registro',
                'pagos': 'Control de Pagos / Salida'
            };
            pageTitle.textContent = titles[target] || 'Sistema Parqueo';

            // Cargar datos según sección
            if (target === 'dashboard') updateDashboardStats();
            if (target === 'pagos') updatePagosUI();
        });
    });

    // Lógica inicial del formulario de registro
    initRegistrationForm();
    initParqueoForm();
    initTarifaForm();
    initEmpleadoForm();
    
    // Iniciar monitoreo de conexión y stats
    updateDashboardStats();
    loadParqueosOptions();
    setInterval(checkConnectionStatus, 10000);
    setInterval(updateServerDateTime, 1000);
});

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
            opt.textContent = `${p.nombre} (Cap: ${p.capacidad_maxima})`;
            select.appendChild(opt);
        });
    } catch (e) {
        select.innerHTML = '<option value="">Error al cargar parqueos</option>';
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
                capacidad_maxima: parseInt(data.capacidad_maxima)
            };

            const url = `${API_URL}/newparqueo`;
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
                numero: data.numero,
                edad: parseInt(data.edad),
                rol: data.rol,
                user: data.user,
                password: data.password
            };

            try {
                const res = await fetch(`${API_URL}/newemploy`, {
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
                nombre: data.nombretarifa,
                costo: parseInt(data.costotarif)
            };

            const url = `${API_URL}/newtarifa`;
            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(newTarifa)
                });
                const result = await res.json();
                if (!res.ok) throw new Error(result.detail || 'Error al crear tarifa');
                alert(`✅ Tarifa "${result.nombre}" creada exitosamente.`);
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
    const checkboxCF = document.getElementById('mostrarFormCF');
    const checkboxCliente = document.getElementById('mostrarFormCliente');
    const containerCliente = document.getElementById('cliente-data-container');
    const regForm = document.getElementById('registration-form');

    if (!checkboxCF || !checkboxCliente || !regForm) return;

    const updateFormVisibility = () => {
        const inputs = containerCliente.querySelectorAll('input:not(#phone)');
        if (checkboxCliente.checked) {
            containerCliente.style.display = 'contents';
            inputs.forEach(i => i.setAttribute('required', ''));
        } else {
            containerCliente.style.display = 'none';
            inputs.forEach(i => i.removeAttribute('required'));
        }
    };

    checkboxCF.addEventListener('change', () => {
        if (checkboxCF.checked) checkboxCliente.checked = false;
        else checkboxCliente.checked = true;
        updateFormVisibility();
    });

    checkboxCliente.addEventListener('change', () => {
        if (checkboxCliente.checked) checkboxCF.checked = false;
        else checkboxCliente.checked = true;
        updateFormVisibility();
    });

    regForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = e.target.querySelector('button[type="submit"]');

        await withLoading(submitBtn, async () => {
            const formData = new FormData(regForm);
            const data = Object.fromEntries(formData.entries());

            if (checkboxCF.checked) {
                data.names = "C/F";
                data.lastnames = "C/F";
                data.nit = "0";
            }

            const clientData = {
                names: data.names,
                lastnames: data.lastnames,
                nit: data.nit,
                phone: data.phone,
                parqueo_id: parseInt(data.parqueo_id)
            };

            const url = `${API_URL}/clients/`;

try {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(clientData)
    });
    
    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Error al guardar registro");
    }
    
    const result = await res.json();

    // 1. Mostramos el mensaje. El navegador se detiene aquí hasta que den "Aceptar".
    alert(`Ticket generado: ${result.idclient}`);
    
    // 2. Al dar clic en "OK", ejecutamos las aperturas de URL:
    
    // Abrir WhatsApp (Prioridad)
    if (result.url) {
        window.open(result.url, '_blank');
    }

    // Abrir el PDF (Opcional, ya que el link va en el WhatsApp)
    if (result.carnet_pdf_url) {
        // Nota: Algunos navegadores podrían bloquear esta segunda ventana emergente
        window.open(result.carnet_pdf_url, '_blank');
    }

    // 3. Limpiar formulario y actualizar vista
    regForm.reset();
    updateFormVisibility();
    updateDashboardStats();

} catch (err) {
    alert(`Error: ${err.message}`);
}
        });
    });

    updateFormVisibility();
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
            const res = await fetch(`${API_URL}/assistance/${encodeURIComponent(decodedText)}?date=${dateStr}&action=take`, { method: "POST" });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.detail || "ID no válido o vehículo ya pagado");

            if (data.status === "exited") {
                playBeepScanner();
                showResultUI_ExitSuccess(data);
            } else {
                playBeepScanner();
                showResultUI_Pagos(data);
            }
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

    currentScanId = data.Client_id;
    resultName.textContent = data.client_name;
    
    // Fill Invoice Details
    document.getElementById("inv-nit").textContent = data.client_nit;
    document.getElementById("inv-entry").textContent = new Date(data.entry_time).toLocaleTimeString();
    document.getElementById("inv-exit").textContent = new Date(data.lastscanhour).toLocaleTimeString();
    document.getElementById("inv-total").textContent = `Q${data.total.toFixed(2)}`;
    
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
    
    await withLoading(btn, async () => {
        try {
            const res = await fetch(`${API_URL}/payments/close/${currentScanId}`, { method: 'POST' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Error al procesar pago");
            
            // Show success on the card
            btn.style.display = "none";
            document.getElementById("btnNext-scanner").style.display = "block";
            document.getElementById("inv-total").style.color = "#10b981";
            document.getElementById("inv-total").textContent = `Q${data.total.toFixed(2)} [PAGADO]`;
            
            updateDashboardStats();

            // Auto-reset after 1.5 seconds
            setTimeout(() => {
                if (currentScanId === data.Client_id) { // Solo si no han escaneado a alguien más (seguridad)
                    resetForNextScanner();
                }
            }, 1500);
        } catch (err) {
            alert(err.message);
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
