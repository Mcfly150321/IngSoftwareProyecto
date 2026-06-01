import re

with open('js/app.js', 'r') as f:
    content = f.read()

# Update initRegistrationForm to call the utilities endpoint
new_registration_body = '''try {
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

                // 4. Utilidad: Generar Ticket y mostrarlo
                alert(`Ticket generado exitosamente: ${client_id}. Se generará el ticket digital...`);
                
                const ticketRes = await fetch(`${API_URL}/utilidades/ticket/${client_id}`);
                if (ticketRes.ok) {
                    const ticketData = await ticketRes.json();
                    if (ticketData.ticket_url) {
                        window.open(ticketData.ticket_url, '_blank');
                    }
                }

                // Limpiar formulario y actualizar vista
                regForm.reset();
                updateDashboardStats();

            } catch (err) {
                alert(`Error: ${err.message}`);
            }'''

# Replace the try/catch block inside initRegistrationForm
content = re.sub(r'try \{[\s\S]*?\} catch \(err\) \{[\s\S]*?\}', new_registration_body, content, count=1)

with open('js/app.js', 'w') as f:
    f.write(content)
print("Updated JS for ticket util")
