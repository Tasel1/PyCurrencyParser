document.addEventListener('DOMContentLoaded', () => {
    // State
    let isLoginMode = true;
    let chartInstance = null;

    // DOM Elements
    const screens = {
        auth: document.getElementById('auth-section'),
        dashboard: document.getElementById('dashboard-section'),
        profile: document.getElementById('profile-section')
    };

    const authForm = document.getElementById('auth-form');
    const authTitle = document.getElementById('auth-title');
    const authBtn = document.getElementById('auth-btn');
    const authSwitchLink = document.getElementById('auth-switch-link');
    const authSwitchText = document.getElementById('auth-switch-text');
    const authError = document.getElementById('auth-error');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');

    const ratesTableBody = document.querySelector('#rates-table tbody');
    const chartCtx = document.getElementById('ratesChart').getContext('2d');

    // Navigation Buttons
    document.getElementById('nav-dashboard').addEventListener('click', () => switchScreen('dashboard'));
    document.getElementById('nav-profile').addEventListener('click', () => switchScreen('profile'));
    document.getElementById('nav-dashboard-back').addEventListener('click', () => switchScreen('dashboard'));
    
    document.getElementById('nav-logout').addEventListener('click', handleLogout);
    document.getElementById('nav-logout-profile').addEventListener('click', handleLogout);

    // Initial Screen
    checkAuthStatus();

    // Screen Switching Logic
    function switchScreen(screenName) {
        Object.values(screens).forEach(screen => {
            if(screen) screen.classList.remove('active');
        });
        if(screens[screenName]) {
            screens[screenName].classList.add('active');
            if(screenName === 'dashboard') {
                loadDashboardData();
            }
        }
    }

    // Auth Mode Switching
    function toggleAuthMode(e) {
        if(e) e.preventDefault();
        isLoginMode = !isLoginMode;
        authTitle.textContent = isLoginMode ? 'Login' : 'Sign Up';
        authBtn.textContent = isLoginMode ? 'Login' : 'Sign Up';
        authSwitchText.innerHTML = isLoginMode 
            ? 'Don\'t have an account? <a href="#" id="auth-switch-link">Sign up</a>'
            : 'Already have an account? <a href="#" id="auth-switch-link">Login</a>';
        
        // Re-attach listener to new link
        document.getElementById('auth-switch-link').addEventListener('click', toggleAuthMode);
        authError.textContent = '';
    }

    if(authSwitchLink) {
        authSwitchLink.addEventListener('click', toggleAuthMode);
    }

    // Auth Form Submission
    if(authForm) {
        authForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            authError.textContent = '';
            
            const username = usernameInput.value;
            const password = passwordInput.value;
            const endpoint = isLoginMode ? '/auth/login' : '/auth/signup';

            try {
                // Determine content type based on endpoint
                let body, headers;
                if (isLoginMode) {
                    // OAuth2PasswordRequestForm expects application/x-www-form-urlencoded
                    body = new URLSearchParams();
                    body.append('username', username);
                    body.append('password', password);
                    headers = { 'Content-Type': 'application/x-www-form-urlencoded' };
                } else {
                    // Signup typically expects JSON
                    body = JSON.stringify({ username, password });
                    headers = { 'Content-Type': 'application/json' };
                }

                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: headers,
                    body: body
                });

                if (response.ok) {
                    usernameInput.value = '';
                    passwordInput.value = '';
                    if (!isLoginMode) {
                         // auto login after signup
                         const loginBody = new URLSearchParams();
                         loginBody.append('username', username);
                         loginBody.append('password', password);
                         const loginRes = await fetch('/auth/login', {
                             method: 'POST',
                             headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                             body: loginBody
                         });
                         if (loginRes.ok) {
                             switchScreen('dashboard');
                         } else {
                             switchScreen('auth');
                             authError.textContent = 'Signed up but failed to login.';
                         }
                    } else {
                        switchScreen('dashboard');
                    }
                } else {
                    const data = await response.json();
                    authError.textContent = data.detail || 'Authentication failed';
                }
            } catch (error) {
                authError.textContent = 'Network error. Please try again.';
                console.error(error);
            }
        });
    }

    // Check Auth (dummy check by calling an api, if 401 goto login)
    async function checkAuthStatus() {
        try {
            const response = await fetch('/api/rates');
            if (response.status === 401) {
                switchScreen('auth');
            } else {
                switchScreen('dashboard');
            }
        } catch (error) {
            switchScreen('auth');
        }
    }

    // Logout
    async function handleLogout() {
        try {
            await fetch('/auth/logout', { method: 'POST' });
            switchScreen('auth');
        } catch (error) {
            console.error('Logout failed', error);
            switchScreen('auth');
        }
    }

    // Load Dashboard Data
    async function loadDashboardData() {
        try {
            // Load Rates
            const ratesRes = await fetch('/api/rates');
            if (ratesRes.status === 401) {
                switchScreen('auth');
                return;
            }
            if(ratesRes.ok) {
                const rates = await ratesRes.json();
                renderRatesTable(rates);
            }

            // Load History for Chart
            const historyRes = await fetch('/api/rates/history');
            if(historyRes.ok) {
                const history = await historyRes.json();
                renderChart(history);
            }
        } catch (error) {
            console.error('Error loading dashboard data', error);
        }
    }

    function renderRatesTable(rates) {
        if(!ratesTableBody) return;
        ratesTableBody.innerHTML = '';
        
        // Handle object or array based on backend response structure
        const entries = Array.isArray(rates) ? rates : Object.entries(rates);
        
        entries.forEach(entry => {
            const tr = document.createElement('tr');
            
            // if entry is array [currency, rate], else if object {currency: '...', rate: '...'}
            let currency, rate;
            if (Array.isArray(entry)) {
                currency = entry[0];
                rate = entry[1];
            } else {
                currency = entry.currency || entry.id;
                rate = entry.rate || entry.value;
            }

            tr.innerHTML = `
                <td>${currency}</td>
                <td>${rate}</td>
            `;
            ratesTableBody.appendChild(tr);
        });
    }

    function renderChart(history) {
        if(!chartCtx) return;

        // Ensure Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded');
            return;
        }

        // Parse history data
        // Expecting something like { labels: [...], datasets: [{label: '...', data: [...]}] }
        // or a raw array of history items. Adjust based on exact backend spec.
        
        // Dummy mapping if array:
        let labels = [];
        let data = [];
        if (Array.isArray(history)) {
            labels = history.map(h => h.date || h.timestamp);
            data = history.map(h => h.rate || h.value);
        } else {
            labels = history.labels || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
            data = history.data || [10, 20, 15, 25, 22];
        }

        if (chartInstance) {
            chartInstance.destroy();
        }

        chartInstance = new Chart(chartCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Rate History',
                    data: data,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: '#f8fafc' }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    y: {
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    }
                }
            }
        });
    }
});