import re

with open('js/app.js', 'r') as f:
    content = f.read()

# 1. Update initRegistrationForm completely
new_init_form = '''function initRegistrationForm() {
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
                tipo_vehiculo_id: parseInt(data.tipo_vehiculo_id || 1)
            };

            try {
                // 1. Obtener seqcode y client_id
                const reqRes = await fetch(`${API_URL}/automata/client-request`, { method: 'POST' });
                if (!reqRes.ok) throw new Error("Error generating client request");
                const { seqcode, client_id } = await reqRes.json();
                
                // 2. Registrar cliente
                clientData.seqcode = seqcode;
                clientData.client_id = client_id;
                
                const clientRes = await fetch(`${API_URL}/automata/client`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(clientData)
                });
                
                if (!clientRes.ok) {
                    const errorData = await clientRes.json();
                    throw new Error(errorData.detail || "Error al guardar registro del cliente");
                }

                // 3. Registrar entrada
                const entRes = await fetch(`${API_URL}/automata/entrada-salida/${client_id}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tipo: "entrada" })
                });

                if (!entRes.ok) {
                    throw new Error("Error al registrar entrada en parqueo");
                }

                alert(`Ticket generado exitosamente: ${client_id}`);
                
                // Limpiar formulario y actualizar vista
                regForm.reset();
                updateDashboardStats();

            } catch (err) {
                alert(`Error: ${err.message}`);
            }
        });
    });
}'''
content = re.sub(r'function initRegistrationForm\(\) \{[\s\S]*?\}\n/\*\*', new_init_form + '\n/**', content)

# 2. Add loading of tipos-vehiculo and unidades-tiempo
load_dropdowns = '''
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
'''
content = content.replace("function loadParqueosOptions() {", load_dropdowns + "\nasync function loadParqueosOptions() {")

# Add call to loadDropdowns
content = content.replace("loadParqueosOptions();\n    setInterval(checkConnectionStatus, 10000);", "loadParqueosOptions();\n    loadDropdowns();\n    setInterval(checkConnectionStatus, 10000);")

# 3. Update initTarifaForm to use the correct fields
new_init_tarifa = '''function initTarifaForm() {
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
}'''
content = re.sub(r'function initTarifaForm\(\) \{[\s\S]*?\}\n\n/\*\*', new_init_tarifa + '\n\n/**', content)

with open('js/app.js', 'w') as f:
    f.write(content)

print("done")
