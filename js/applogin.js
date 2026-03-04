const API_URL = "/api"; // URL de la API

function switchTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.form-content').forEach(f => f.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(`${tab}-form`).classList.add('active');
}

// Toggle Password Visibility
document.getElementById('show-password').addEventListener('change', function() {
    const passwordInput = document.getElementById('login-password');
    passwordInput.type = this.checked ? 'text' : 'password';
});

// Login
document.getElementById('formLogin').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const mensajeDiv = document.getElementById('login-mensaje');
    const loginBox = document.querySelector('.container');
    const overlay = document.getElementById('loading-overlay');
    const waterFill = document.getElementById('water-fill');
    const welcomeText = document.getElementById('welcome-text');
    const submitBtn = document.querySelector('#formLogin button[type="submit"]');
    const loaderContainer = document.getElementById('loader-container');
    
    // 1. Deshabilitar botón y mostrar cargando
    if (submitBtn) submitBtn.disabled = true;
    mensajeDiv.style.display = 'none'; // Ocultar errores previos
    loaderContainer.style.display = 'flex';
    
    // Timer de 3 segundos para el loader esmeralda
    const minWait = new Promise(resolve => setTimeout(resolve, 3000));

    try {
        const loginPromise = fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        // Esperar a que la petición termine Y que pasen al menos 3 segundos
        const [response] = await Promise.all([loginPromise, minWait]);
        const data = await response.json();
        
        if (response.ok) {
            // Ocultar loader antes de la animación final
            loaderContainer.style.display = 'none';

            // 1. Ocultar el box de login
            loginBox.style.opacity = '0';
            loginBox.style.transform = 'scale(0.9)';

            // --- SMART PRE-LOAD: Disparar petición a DB mientras la animación corre ---
            // Esto "despierta" a la base de datos sin bloquear la UI
            const dbWarmupPromise = fetch(`${API_URL}/stats`).catch(e => console.log("Pre-load ignorado", e));
            
            // Promesa de tiempo mínimo de animación (para que se vea bonito y no parpadee si la DB es muy rápida)
            const minAnimationTime = new Promise(resolve => setTimeout(resolve, 3000));
            
            setTimeout(() => {
                loginBox.style.display = 'none';
                
                // 2. Mostrar overlay de animación
                overlay.classList.add('active');
                
                // 3. Iniciar animación de "llenado de agua"
                setTimeout(() => {
                    waterFill.style.height = '100%';
                    
                    // 4. Mostrar Bienvenida
                    welcomeText.textContent = `¡Bienvenid@ ${data.first_name}!`;
                    welcomeText.classList.add('show');
                    
                    // 5. Redirigir INTELIGENTE: Esperar a que la DB responda Y que pase el tiempo mínimo
                    // Guardar rol y nombre en sessionStorage para filtrar secciones del dashboard
                    sessionStorage.setItem('userRol', (data.rol || '').toLowerCase());
                    sessionStorage.setItem('userName', data.first_name || data.username || '');

                    Promise.all([dbWarmupPromise, minAnimationTime]).then(() => {
                        window.location.href = '/dashboard';
                    }).catch(() => {
                        // Si algo falla catastróficamente, redirigir igual
                         window.location.href = '/dashboard';
                    });

                }, 100);
            }, 500);
            
        } else {
            // Error de credenciales
            loaderContainer.style.display = 'none';
            submitBtn.disabled = false;
            mensajeDiv.className = 'mensaje error';
            mensajeDiv.textContent = `❌ ${data.detail}. Intente de nuevo.`;
            mensajeDiv.style.display = 'block';
        }
        
    } catch (error) {
        loaderContainer.style.display = 'none';
        submitBtn.disabled = false;
        mensajeDiv.className = 'mensaje error';
        mensajeDiv.textContent = '❌ Error de conexión. Intente de nuevo.';
        mensajeDiv.style.display = 'block';
    }
});
