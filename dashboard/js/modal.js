const API_BASE_MODAL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000/api'
    : `${window.location.origin}/api`;

const getFullUrlModal = (path) => {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    const base = API_BASE_MODAL.replace('/api', '');
    return `${base}${path.startsWith('/') ? '' : '/'}${path}`;
};

let currentContext = null;

function createModal() {
    if (document.getElementById('areaStatusModal')) return;

    const html = `
    <div id="areaStatusModal" class="modal-overlay" style="display:none">
      <div class="modal-content">
        <div class="modal-header">
          <div class="modal-title">Area Status</div>
          <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
          <div class="modal-info-row">
            <span class="muted">City</span>
            <span id="m-city" style="font-weight:bold">-</span>
          </div>
          <div class="modal-info-row">
            <span class="muted">Area</span>
            <span id="m-area" style="font-weight:bold">-</span>
          </div>
          <div class="modal-info-row">
            <span class="muted">Complaints</span>
            <span id="m-count">-</span>
          </div>
          
          <div id="m-controls" style="display:none">
            <div class="status-buttons">
              <button class="status-btn pending" onclick="setStatus('Pending')">Pending</button>
              <button class="status-btn processing" onclick="setStatus('Processing')">Processing</button>
              <button class="status-btn resolved" onclick="setStatus('Resolved')">Resolved</button>
            </div>
            <div class="modal-actions">
              <button class="modal-btn modal-btn-alert" onclick="resolveAll()">Resolve All</button>
              <button class="modal-btn modal-btn-save" onclick="saveStatus()">Save</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
    document.body.insertAdjacentHTML('beforeend', html);

    document.getElementById('areaStatusModal').addEventListener('click', e => {
        if (e.target.id === 'areaStatusModal') closeModal();
    });
}

function showAreaStatusPopup(module, city, area, count) {
    createModal();
    currentContext = { module, city, area, status: 'Pending' };

    document.getElementById('m-city').textContent = city;
    document.getElementById('m-area').textContent = area;
    document.getElementById('m-count').textContent = count;

    const modal = document.getElementById('areaStatusModal');
    modal.style.display = 'flex';

    // Show complaint list section
    const body = document.querySelector('.modal-body');
    let listContainer = document.getElementById('m-complaint-list');
    if (!listContainer) {
        listContainer = document.createElement('div');
        listContainer.id = 'm-complaint-list';
        listContainer.style.marginTop = '20px';
        listContainer.style.maxHeight = '300px';
        listContainer.style.overflowY = 'auto';
        listContainer.style.borderTop = '1px solid rgba(255,255,255,0.1)';
        listContainer.style.paddingTop = '15px';
        body.insertBefore(listContainer, document.getElementById('m-controls'));
    }
    
    listContainer.innerHTML = '<div class="muted">Loading complaints...</div>';

    const controls = document.getElementById('m-controls');
    controls.style.display = 'block';
    
    loadStatus(module, city, area);
    fetchComplaints(module, city, area);
}

async function fetchComplaints(module, city, area) {
    const listContainer = document.getElementById('m-complaint-list');
    try {
        const r = await fetch(`${API_BASE_MODAL}/${module}/list/${encodeURIComponent(city)}/${encodeURIComponent(area)}`);
        const data = await r.json();
        
        if (!data || data.length === 0) {
            listContainer.innerHTML = '<div class="muted">No individual complaints found.</div>';
            return;
        }

        listContainer.innerHTML = `<h4>Individual Submissions (${data.length})</h4>`;
        data.forEach(item => {
            const div = document.createElement('div');
            div.className = 'complaint-item';
            div.style.background = 'rgba(255,255,255,0.03)';
            div.style.padding = '10px';
            div.style.borderRadius = '8px';
            div.style.marginBottom = '10px';
            div.style.fontSize = '13px';
            
            const imgUrl = getFullUrlModal(item.evidence_url);
            const imgHtml = item.evidence_url 
                ? `<div style="margin-top:8px"><img src="${imgUrl}" style="width:100%; border-radius:4px; cursor:pointer" onclick="openLightbox('${imgUrl}')"></div>`
                : '';

            const aiStatus = module === 'fraud' 
                ? `<span class="pill" style="background:rgba(239, 68, 68, 0.2); color:#ef4444; font-size:10px">Risk: ${item.risk_score}%</span>`
                : `<span class="pill" style="background:rgba(14, 215, 178, 0.2); color:#0ed7b2; font-size:10px">AI: ${item.status || 'Verified'}</span>`;

            div.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px">
                    <span style="font-weight:600; color:#3b82f6">${item.complaint_id || item.transaction_id}</span>
                    ${aiStatus}
                </div>
                <div class="muted">${item.description || item.complaint_text || 'No description'}</div>
                ${imgHtml}
            `;
            listContainer.appendChild(div);
        });
    } catch (e) {
        listContainer.innerHTML = '<div class="muted">Error loading complaints</div>';
    }
}

function closeModal() {
    document.getElementById('areaStatusModal').style.display = 'none';
    currentContext = null;
    const list = document.getElementById('m-complaint-list');
    if (list) list.innerHTML = '';
}

async function loadStatus(module, city, area) {
    try {
        const r = await fetch(`${API_BASE_MODAL}/${module}/area-status/${encodeURIComponent(city)}/${encodeURIComponent(area)}`);
        const d = await r.json();
        updateButtons(d.status || 'Pending');
    } catch (e) {
        console.error(e);
    }
}

function setStatus(status) {
    if (!currentContext) return;
    currentContext.status = status;
    updateButtons(status);
}

function updateButtons(status) {
    document.querySelectorAll('.status-btn').forEach(b => {
        b.classList.remove('active');
        if (b.textContent === status) b.classList.add('active');
    });
}

async function saveStatus() {
    if (!currentContext) return;
    const { module, city, area, status } = currentContext;

    try {
        const r = await fetch(`${API_BASE_MODAL}/${module}/area-status/${encodeURIComponent(city)}/${encodeURIComponent(area)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });

        if (r.ok) {
            if (status === 'Resolved') {
                if (confirm('Status is Resolved. Remove all complaints?')) {
                    resolveAll();
                    return;
                }
            }
            alert('Saved!');
            closeModal();
        } else {
            alert('Failed to save');
        }
    } catch (e) {
        alert('Error saving');
    }
}

async function resolveAll() {
    if (!currentContext) return;
    const { module, city, area } = currentContext;

    if (!confirm('Permanently remove all complaints?')) return;

    try {
        const r = await fetch(`${API_BASE_MODAL}/${module}/area-resolve/${encodeURIComponent(city)}/${encodeURIComponent(area)}`, {
            method: 'POST'
        });
        if (r.ok) {
            const d = await r.json();
            alert(`Removed ${d.removed_count} complaints.`);
            closeModal();

            // Refresh parent list based on module
            if (module === 'road' && window.loadRoadAreas) window.loadRoadAreas(city);
            if (module === 'health' && window.loadHealthAreas) window.loadHealthAreas(city);
            if (module === 'fraud' && window.loadFraudAreas) window.loadFraudAreas(city);
        } else {
            alert('Failed to resolve');
        }
    } catch (e) {
        alert('Error resolving');
    }
}
