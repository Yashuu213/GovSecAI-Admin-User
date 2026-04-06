// API Config
// If we're on localhost, assume the backend is on port 8000
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000/api'
    : `${window.location.origin}/api`;

// UI Refs
const panels = {
    home: document.getElementById('panel-home'),
    road: document.getElementById('panel-road'),
    health: document.getElementById('panel-health'),
    fraud: document.getElementById('panel-fraud')
};
const navBtns = {
    home: document.getElementById('nav-home'),
    road: document.getElementById('nav-road'),
    health: document.getElementById('nav-health'),
    fraud: document.getElementById('nav-fraud')
};

// Charts
let charts = {};

// --- Chart Helpers ---
const createGradient = (ctx, color1, color2) => {
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, color1);
    gradient.addColorStop(1, color2 || 'transparent');
    return gradient;
};

const CHART_DEFAULTS = {
    color: '#94a3b8',
    font: { family: "'Inter', sans-serif", size: 12 },
    responsive: true,
    maintainAspectRatio: false,
};

if (typeof Chart !== 'undefined') {
    Object.assign(Chart.defaults, CHART_DEFAULTS);
}

// Navigation
function showModule(name) {
    // Hide all
    Object.values(panels).forEach(p => { if(p) p.classList.add('hidden') });
    Object.values(navBtns).forEach(b => { if(b) b.classList.remove('active') });

    // Show selected
    if (panels[name]) panels[name].classList.remove('hidden');
    if (navBtns[name]) navBtns[name].classList.add('active');

    // Load data
    if (name === 'home') loadHomeData();
    if (name === 'road') loadRoadData();
    if (name === 'health') loadHealthData();
    if (name === 'fraud') loadFraudData();
}

// API Status
async function checkApi() {
    try {
        const r = await fetch(`${API_BASE}/ping`);
        const j = await r.json();
        const el = document.getElementById('api-status');
        if (el && j.status === 'ok') {
            el.textContent = '● Online';
            el.style.background = 'rgba(14, 215, 178, 0.1)';
            el.style.color = '#0ed7b2';
        }
    } catch (e) {
        const el = document.getElementById('api-status');
        if (el) {
            el.textContent = '● Offline';
            el.style.background = 'rgba(239, 68, 68, 0.1)';
            el.style.color = '#ef4444';
        }
    }
}

// --- HOME ---
async function loadHomeData() {
    try {
        const r = await fetch(`${API_BASE}/stats`);
        if (!r.ok) throw new Error('Stats fetch failed');
        const data = await r.json();

        // 1. Counts
        if (data.counts) {
            document.getElementById('stat-road').textContent = data.counts.road.toLocaleString();
            document.getElementById('stat-health').textContent = data.counts.health.toLocaleString();
            document.getElementById('stat-fraud').textContent = data.counts.fraud.toLocaleString();
            document.getElementById('stat-total').textContent = data.counts.total.toLocaleString();
        }

        // 2. Trend Chart
        if (typeof Chart !== 'undefined' && data.trends) {
            const ctxEl = document.getElementById('homeChart');
            if (ctxEl) {
                const ctx = ctxEl.getContext('2d');
                if (charts.home) charts.home.destroy();

                charts.home = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.trends.labels,
                        datasets: [
                            {
                                label: 'Road',
                                data: data.trends.road,
                                borderColor: '#3b82f6',
                                backgroundColor: createGradient(ctx, 'rgba(59, 130, 246, 0.2)', 'rgba(59, 130, 246, 0)'),
                                borderWeight: 3,
                                fill: true,
                                tension: 0.4,
                                pointRadius: 0,
                                pointHoverRadius: 6,
                            },
                            {
                                label: 'Health',
                                data: data.trends.health,
                                borderColor: '#10b981',
                                backgroundColor: createGradient(ctx, 'rgba(16, 185, 129, 0.2)', 'rgba(16, 185, 129, 0)'),
                                borderWeight: 3,
                                fill: true,
                                tension: 0.4,
                                pointRadius: 0,
                                pointHoverRadius: 6,
                            },
                            {
                                label: 'Fraud',
                                data: data.trends.fraud,
                                borderColor: '#ef4444',
                                backgroundColor: createGradient(ctx, 'rgba(239, 68, 68, 0.2)', 'rgba(239, 68, 68, 0)'),
                                borderWeight: 3,
                                fill: true,
                                tension: 0.4,
                                pointRadius: 0,
                                pointHoverRadius: 6,
                            }
                        ]
                    },
                    options: {
                        plugins: {
                            legend: { position: 'bottom', labels: { boxWidth: 8, usePointStyle: true, padding: 20 } },
                            tooltip: {
                                backgroundColor: '#1e293b',
                                titleFont: { size: 14, weight: 'bold' },
                                padding: 12,
                                cornerRadius: 10,
                                displayColors: true,
                                borderColor: 'rgba(255,255,255,0.1)',
                                borderWidth: 1
                            }
                        },
                        scales: {
                            y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { padding: 10 } },
                            x: { grid: { display: false } }
                        }
                    }
                });
            }
        }

        // 3. Live Alerts
        const list = document.getElementById('home-alerts');
        if (list && data.alerts) {
            list.innerHTML = '';
            data.alerts.forEach(a => {
                const div = document.createElement('div');
                div.className = 'alert-item';
                div.innerHTML = `
                    <div class="meta">
                        <span class="tag ${a.source}">${a.source}</span>
                        <span>${a.date}</span>
                    </div>
                    <div class="desc">${a.description}</div>
                    <div class="muted" style="font-size:0.75rem; margin-top:8px; opacity: 0.8">${a.city}</div>
                `;
                list.appendChild(div);
            });
        }
    } catch (e) { console.error('Home data load error:', e); }
}

// --- Specialized Chart Rendering ---

function renderChart(canvasId, label, dataEntries, type = 'bar', color = '#0ed7b2') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (charts[canvasId]) charts[canvasId].destroy();

    const labels = dataEntries.map(e => e[0]);
    const data = dataEntries.map(e => e[1]);

    const isCircular = type === 'doughnut' || type === 'polarArea';
    const gradient = createGradient(ctx, `${color}44`, `${color}00`);

    // Curated high-security palette for circular charts
    const palette = isCircular ? [
        `${color}ee`, `${color}cc`, `${color}aa`, `${color}88`, `${color}66`,
        `${color}55`, `${color}44`, `${color}33`, `${color}22`, `${color}11`
    ] : color;

    const config = {
        type: type,
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: palette,
                borderColor: isCircular ? '#020617' : color,
                borderWidth: isCircular ? 2 : 0,
                borderRadius: type === 'bar' ? 6 : 0,
                fill: type === 'line',
                tension: 0.4
            }]
        },
        options: {
            indexAxis: type === 'horizontalBar' ? 'y' : 'x',
            plugins: {
                legend: {
                    display: isCircular,
                    position: 'right',
                    labels: { color: '#94a3b8', boxWidth: 10, font: { size: 10 } }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    padding: 12,
                    cornerRadius: 10,
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                y: {
                    display: !isCircular,
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: { padding: 10 }
                },
                x: {
                    display: !isCircular,
                    grid: { display: false },
                    ticks: { padding: 10 }
                },
                r: {
                    display: type === 'polarArea',
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { backdropColor: 'transparent', color: '#64748b' }
                }
            }
        }
    };

    if (type === 'horizontalBar') config.type = 'bar';

    charts[canvasId] = new Chart(ctx, config);
}

function renderAreaChart(canvasId, label, dataEntries, color) {
    // Top 15 Areas always use a Horizontal Bar Chart for maximum readability
    renderChart(canvasId, label, dataEntries, 'horizontalBar', color);
}

// --- ROAD ---
async function loadRoadData() {
    const list = document.getElementById('road-cities');
    if (!list) return;
    list.innerHTML = '<div class="muted">Loading...</div>';
    try {
        const r = await fetch(`${API_BASE}/road/summary`);
        const data = await r.json();
        const cities = data.complaints_by_city || {};

        list.innerHTML = '';
        const sorted = Object.entries(cities).sort((a, b) => b[1] - a[1]);
        sorted.forEach(([city, count]) => {
            const div = document.createElement('div');
            div.className = 'list-item';
            div.innerHTML = `<span>${city}</span> <span class="muted">${count.toLocaleString()}</span>`;
            div.onclick = () => loadRoadAreas(city);
            list.appendChild(div);
        });

        renderChart('roadChart', 'City Complaints', sorted.slice(0, 10), 'horizontalBar', '#3b82f6');
        // Clear area chart on module switch
        if (charts['roadAreaChart']) charts['roadAreaChart'].destroy();
    } catch (e) { list.innerHTML = '<div class="muted">Error loading data</div>'; }
}

async function loadRoadAreas(city) {
    const canvasId = 'roadAreaChart';
    try {
        const r = await fetch(`${API_BASE}/road/areas/${encodeURIComponent(city)}`);
        const data = await r.json();
        const areas = data.area_counts || {};
        const sorted = Object.entries(areas).sort((a, b) => b[1] - a[1]).slice(0, 15);
        renderAreaChart(canvasId, `Top Areas in ${city}`, sorted, '#3b82f6');
    } catch (e) { console.error('Area load error:', e); }
}

// --- HEALTH ---
async function loadHealthData() {
    const list = document.getElementById('health-cities');
    if (!list) return;
    list.innerHTML = '<div class="muted">Loading...</div>';
    try {
        const r = await fetch(`${API_BASE}/health/summary`);
        const data = await r.json();
        const cities = data.complaints_by_city || {};

        list.innerHTML = '';
        const sorted = Object.entries(cities).sort((a, b) => b[1] - a[1]);
        sorted.forEach(([city, count]) => {
            const div = document.createElement('div');
            div.className = 'list-item';
            div.innerHTML = `<span>${city}</span> <span class="muted">${count.toLocaleString()}</span>`;
            div.onclick = () => loadHealthAreas(city);
            list.appendChild(div);
        });

        renderChart('healthChart', 'City Distribution', sorted.slice(0, 10), 'doughnut', '#10b981');
        if (charts['healthAreaChart']) charts['healthAreaChart'].destroy();
    } catch (e) { list.innerHTML = 'Error'; }
}

async function loadHealthAreas(city) {
    const canvasId = 'healthAreaChart';
    try {
        const r = await fetch(`${API_BASE}/health/areas/${encodeURIComponent(city)}`);
        const data = await r.json();
        const areas = data.area_counts || {};
        const sorted = Object.entries(areas).sort((a, b) => b[1] - a[1]).slice(0, 15);
        renderAreaChart(canvasId, `Top Areas in ${city}`, sorted, '#10b981');
    } catch (e) { console.error(e); }
}

// --- FRAUD ---
async function loadFraudData() {
    const list = document.getElementById('fraud-cities');
    if (!list) return;
    list.innerHTML = '<div class="muted">Loading...</div>';
    try {
        const r = await fetch(`${API_BASE}/fraud/summary`);
        const data = await r.json();
        const cities = data.fraud_by_city || {};

        list.innerHTML = '';
        const sorted = Object.entries(cities).sort((a, b) => b[1] - a[1]);
        sorted.forEach(([city, count]) => {
            const div = document.createElement('div');
            div.className = 'list-item';
            div.innerHTML = `<span>${city}</span> <span class="muted">${count.toLocaleString()}</span>`;
            div.onclick = () => loadFraudAreas(city);
            list.appendChild(div);
        });

        renderChart('fraudChart', 'Fraud Security Map', sorted.slice(0, 10), 'polarArea', '#ef4444');
        if (charts['fraudAreaChart']) charts['fraudAreaChart'].destroy();
    } catch (e) { list.innerHTML = 'Error'; }
}

async function loadFraudAreas(city) {
    const canvasId = 'fraudAreaChart';
    try {
        const r = await fetch(`${API_BASE}/fraud/areas/${encodeURIComponent(city)}`);
        const data = await r.json();
        const areas = data.area_counts || {};
        const sorted = Object.entries(areas).sort((a, b) => b[1] - a[1]).slice(0, 15);
        renderAreaChart(canvasId, `Top Fraud areas in ${city}`, sorted, '#ef4444');
    } catch (e) { console.error(e); }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard App Initializing...');

    if (!panels.home) console.error('Panel Home not found!');

    checkApi();
    setInterval(checkApi, 5000);
    // Load home by default
    showModule('home');
});
