const API_URL = "http://localhost:8000/api";

function renderForm(type) {
    const fields = document.getElementById('dynamic-fields');
    const title = document.getElementById('form-title');
    const subtitle = document.getElementById('form-subtitle');
    
    if (type === 'road') {
        title.innerText = 'Road & Transport Complaint';
        fields.innerHTML = `
            <div class="form-group">
                <label>City</label>
                <input type="text" name="city" required placeholder="e.g. Ahmedabad">
            </div>
            <div class="form-group">
                <label>Area</label>
                <input type="text" name="area" required placeholder="e.g. Area-5">
            </div>
            <div class="form-group">
                <label>Issue Type</label>
                <select name="issue_type" required>
                    <option value="Pothole">Pothole</option>
                    <option value="Broken Streetlight">Broken Streetlight</option>
                    <option value="Water Leakage">Water Leakage</option>
                    <option value="Traffic Signal Malfunction">Traffic Signal Malfunction</option>
                    <option value="Illegal Parking">Illegal Parking</option>
                </select>
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea name="description" required rows="4" placeholder="Detail your concern..."></textarea>
            </div>
        `;
    } else if (type === 'health') {
        title.innerText = 'Healthcare Services Complaint';
        fields.innerHTML = `
            <div class="form-group">
                <label>Patient ID (Optional)</label>
                <input type="text" name="patient_id" placeholder="e.g. PTXXXXXX">
            </div>
            <div class="form-group">
                <label>City</label>
                <input type="text" name="city" required placeholder="e.g. Surat">
            </div>
            <div class="form-group">
                <label>Area</label>
                <input type="text" name="area" required placeholder="e.g. West District">
            </div>
            <div class="form-group">
                <label>Medical Facility</label>
                <input type="text" name="facility" required placeholder="e.g. Civil Hospital">
            </div>
            <div class="form-group">
                <label>Category</label>
                <select name="category" required>
                    <option value="Infrastructure">Infrastructure</option>
                    <option value="Staff Behavior">Staff Behavior</option>
                    <option value="Sanitation">Sanitation</option>
                    <option value="Service Delay">Service Delay</option>
                    <option value="Medication Issues">Medication Issues</option>
                    <option value="Clinical Error">Clinical Error</option>
                </select>
            </div>
            <div class="form-group">
                <label>Complaint Details</label>
                <textarea name="complaint_text" required rows="4" placeholder="Describe the incident..."></textarea>
            </div>
        `;
    } else if (type === 'banking') {
        title.innerText = 'Banking & Fraud Report';
        fields.innerHTML = `
            <div class="form-group">
                <label>Account ID / Phone</label>
                <input type="text" name="account_id" required placeholder="Linked number or account ID">
            </div>
            <div class="form-group">
                <label>Amount (in INR)</label>
                <input type="number" name="amount" required placeholder="Transaction amount">
            </div>
            <div class="form-group">
                <label>Type of Fraud</label>
                <select name="merchant_category" required>
                    <option value="E-Commerce">E-Commerce</option>
                    <option value="Banking">Banking</option>
                    <option value="Phishing">Phishing</option>
                    <option value="Card Cloned">Card Cloned</option>
                    <option value="Investment Scam">Investment Scam</option>
                </select>
            </div>
            <div class="form-group">
                <label>Transaction Type</label>
                <select name="transaction_type" required>
                    <option value="UPI">UPI</option>
                    <option value="Credit Card">Credit Card</option>
                    <option value="Debit Card">Debit Card</option>
                    <option value="Net Banking">Net Banking</option>
                </select>
            </div>
             <div class="form-group">
                <label>Device Used</label>
                <select name="device_type" required>
                    <option value="Android">Android</option>
                    <option value="iOS">iOS</option>
                    <option value="Web Browser">Web Browser</option>
                </select>
            </div>
            <div class="form-group">
                <label>City</label>
                <input type="text" name="location_city" required placeholder="Current city">
            </div>
            <div class="form-group">
                <label>Area</label>
                <input type="text" name="area" required placeholder="Current area">
            </div>
        `;
    }
}

// Global Form Submission Handling
const complaintForm = document.getElementById('complaint-form');
if (complaintForm) {
    complaintForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const type = new URLSearchParams(window.location.search).get('type') || 'road';
        const formData = new FormData(complaintForm);
        const data = Object.fromEntries(formData.entries());
        
        // Final button loading state
        const btn = document.querySelector('.btn');
        const btnText = document.getElementById('btn-text');
        btn.disabled = true;
        btnText.innerText = "Submitting...";

        try {
            const response = await fetch(`${API_URL}/submit/${type}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                const result = await response.json();
                
                // Save to History
                saveToHistory(result.id, {
                    type: type,
                    city: data.city || data.location_city,
                    area: data.area,
                    date: new Date().toLocaleDateString()
                });

                document.querySelector('.form-container').style.display = 'none';
                document.getElementById('success-view').style.display = 'block';
                document.getElementById('ref-id').innerText = result.id;
                // Force Dashboard Update
                fetch(`${API_URL}/reload`);
            } else {
                alert("Submission failed. Please try again.");
                btn.disabled = false;
                btnText.innerText = "Submit Complaint";
            }
        } catch (error) {
            console.error("Error:", error);
            alert("Connection error. Is the backend running?");
            btn.disabled = false;
            btnText.innerText = "Submit Complaint";
        }
    });
}

// Tracking logic
async function trackComplaint() {
    const id = document.getElementById('track-id').value.trim();
    if (!id) return;

    const resultDiv = document.getElementById('track-result');
    const errorDiv = document.getElementById('track-error');
    
    resultDiv.style.display = 'none';
    errorDiv.style.display = 'none';

    try {
        const response = await fetch(`${API_URL}/track/${id}`);
        if (response.ok) {
            const data = await response.json();
            
            // Set details
            document.getElementById('res-type').innerText = `${data.type} Complaint`;
            document.getElementById('res-status').innerText = data.status;
            document.getElementById('res-status').className = `status-badge status-${data.status.toLowerCase()}`;
            
            let city = data.details.city || data.details.location_city;
            let area = data.details.area;
            document.getElementById('res-city-area').innerText = `${city} - ${area}`;
            
            let desc = data.details.description || data.details.complaint_text || `Amount: ${data.details.amount} via ${data.details.transaction_type}`;
            document.getElementById('res-desc').innerText = desc;

            resultDiv.style.display = 'block';
        } else {
            errorDiv.style.display = 'block';
        }
    } catch (e) {
        console.error(e);
        errorDiv.style.display = 'block';
    }
}

// History Management
function saveToHistory(id, data) {
    let history = JSON.parse(localStorage.getItem('complaintHistory') || '[]');
    // Avoid duplicates
    if (!history.find(item => item.id === id)) {
        history.unshift({ id, ...data });
        // Keep last 10
        history = history.slice(0, 10);
        localStorage.setItem('complaintHistory', JSON.stringify(history));
    }
}

function loadHistory() {
    const historyList = document.getElementById('history-list');
    const historySection = document.getElementById('recent-history-section');
    if (!historyList) return;

    const history = JSON.parse(localStorage.getItem('complaintHistory') || '[]');
    
    if (history.length > 0) {
        historySection.style.display = 'block';
        historyList.innerHTML = history.map(item => `
            <div class="history-item" onclick="autoTrack('${item.id}')">
                <div class="history-label">${item.type.toUpperCase()} - ${item.city}</div>
                <div class="history-meta">${item.area} | ${item.date}</div>
                <div class="history-id">${item.id}</div>
            </div>
        `).join('');
    } else {
        historySection.style.display = 'none';
    }
}

function autoTrack(id) {
    const input = document.getElementById('track-id');
    if (input) {
        input.value = id;
        trackComplaint();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('track.html')) {
        loadHistory();
    }
});
