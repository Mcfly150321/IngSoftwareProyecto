import re

with open('js/app.js', 'r') as f:
    content = f.read()

# Update initRegistrationForm
content = re.sub(
    r'fetch\(\`\$\{API_URL\}/automata/entrada-salida\`, \{[\s\S]*?body: JSON.stringify\(\{ client_id: client_id, tipo: "entrada" \}\)[\s\S]*?\}\);',
    r'''fetch(`${API_URL}/automata/entrada-salida/${client_id}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tipo: "entrada" })
                });''',
    content
)

# Update showResultUI_Pagos confirm transaction
content = re.sub(
    r'fetch\(\`\$\{API_URL\}/automata/transaccion\`, \{[\s\S]*?body: JSON.stringify\(\{[\s\S]*?client_id: currentScanId,[\s\S]*?\}\)[\s\S]*?\}\);',
    r'''fetch(`${API_URL}/automata/transaccion/${currentScanId}`, { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tipo_transaccion: "cobro",
                    monto: parseFloat(document.getElementById("inv-total").textContent.replace("Q",""))
                })
            });''',
    content
)

# Update Exit scan endpoint
content = re.sub(
    r'fetch\(\`\$\{API_URL\}/automata/entrada-salida\`, \{[\s\S]*?body: JSON.stringify\(\{[\s\S]*?client_id: encodeURIComponent\(decodedText\),[\s\S]*?\}\)[\s\S]*?\}\);',
    r'''fetch(`${API_URL}/automata/entrada-salida/${encodeURIComponent(decodedText)}`, { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tipo: "salida"
                })
            });''',
    content
)

with open('js/app.js', 'w') as f:
    f.write(content)

print("app.js updated.")
