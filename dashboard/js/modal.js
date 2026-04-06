/* Area Status Modal Logic */

// API Config (Ensure consistency)
const API_BASE_MODAL = 'http://localhost:8000/api';

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

    const controls = document.getElementById('m-controls');
    // Enable controls for all modules now
    controls.style.display = 'block';
    loadStatus(module, city, area);
}

function closeModal() {
    document.getElementById('areaStatusModal').style.display = 'none';
    currentContext = null;
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
