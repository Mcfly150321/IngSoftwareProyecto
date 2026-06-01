import re

with open('js/app.js', 'r') as f:
    content = f.read()

# Replace assistance endpoint call with calcular-cobro
content = re.sub(
    r'const res = await fetch\(\`\$\{API_URL\}/assistance/\$\{encodeURIComponent\(decodedText\)\}\?date=\$\{dateStr\}&action=take\`, \{ method: "POST" \}\);',
    r'const res = await fetch(`${API_URL}/automata/calcular-cobro/${encodeURIComponent(decodedText)}`, { method: "GET" });',
    content
)

# Update showResultUI_Pagos
content = re.sub(
    r'currentScanId = data\.Client_id;',
    r'currentScanId = data.client_id;',
    content
)

# Replace close payment endpoint
content = re.sub(
    r'const res = await fetch\(\`\$\{API_URL\}/payments/close/\$\{currentScanId\}\`, \{ method: \'POST\' \}\);',
    r'''const res = await fetch(`${API_URL}/automata/transaccion`, { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    client_id: currentScanId,
                    tipo_transaccion: "cobro",
                    monto: parseFloat(document.getElementById("inv-total").textContent.replace("Q",""))
                })
            });''',
    content
)

# Update Exit scan endpoint
content = re.sub(
    r'const res = await fetch\(\`\$\{API_URL\}/out/\$\{encodeURIComponent\(decodedText\)\}\`, \{ method: "POST" \}\);',
    r'''const res = await fetch(`${API_URL}/automata/entrada-salida`, { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    client_id: encodeURIComponent(decodedText),
                    tipo: "salida"
                })
            });''',
    content
)

with open('js/app.js', 'w') as f:
    f.write(content)

print("app.js updated.")
