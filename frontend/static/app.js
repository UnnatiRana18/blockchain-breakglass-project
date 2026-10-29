
document.addEventListener('DOMContentLoaded', () => {
    let state = { doctors: [], patients: [], activeGrant: null, timerInterval: null, totalDuration: 0, remainingSeconds: 0 };
    const elements = {
        systemClock: document.getElementById('system-clock'), tabBtns: document.querySelectorAll('.tab-btn'), tabPanes: document.querySelectorAll('.tab-pane'),
        doctorSelect: document.getElementById('doctor-select'), doctorMeta: document.getElementById('doctor-meta'),
        patientSelect: document.getElementById('patient-select'), patientTriageInfo: document.getElementById('patient-triage-info'),
        urgencySelect: document.getElementById('urgency-select'), durationSelect: document.getElementById('duration-select'),
        reasonInput: document.getElementById('reason-input'), breakGlassForm: document.getElementById('break-glass-form'),
        quickReasonBtns: document.querySelectorAll('.btn-chip'), sessionBadge: document.getElementById('session-badge'),
        noSessionPlaceholder: document.getElementById('no-session-placeholder'), activeSessionView: document.getElementById('active-session-view'),
        expiredSessionView: document.getElementById('expired-session-view'), countdownTimer: document.getElementById('countdown-timer'),
        timerProgress: document.getElementById('timer-progress'), btnEarlyRevoke: document.getElementById('btn-early-revoke'),
        btnResetSession: document.getElementById('btn-reset-session'), activeGrantId: document.getElementById('active-grant-id'),
        activeBlockInfo: document.getElementById('active-block-info'), activeLatency: document.getElementById('active-latency'),
        medBloodGroup: document.getElementById('med-blood-group'), medAllergies: document.getElementById('med-allergies'),
        medMedications: document.getElementById('med-medications'), medConditions: document.getElementById('med-conditions'),
        medResuscitation: document.getElementById('med-resuscitation'), medContacts: document.getElementById('med-contacts'),
        medClinicalWarning: document.getElementById('med-clinical-warning'), statBlocksCount: document.getElementById('stat-blocks-count'),
        statLogsCount: document.getElementById('stat-logs-count'), statIntegrityStatus: document.getElementById('stat-integrity-status'),
        btnVerifyIntegrity: document.getElementById('btn-verify-integrity'), btnSimulateTamper: document.getElementById('btn-simulate-tamper'),
        btnRestoreLedger: document.getElementById('btn-restore-ledger'), verificationBanner: document.getElementById('verification-banner'),
        bannerIcon: document.getElementById('banner-icon'), bannerTitle: document.getElementById('banner-title'), bannerDesc: document.getElementById('banner-desc'),
        bannerMeta: document.getElementById('banner-meta'), auditTableBody: document.getElementById('audit-table-body'), blocksList: document.getElementById('blocks-list'),
        btnRunBenchmark: document.getElementById('btn-run-benchmark'), benchSmartLat: document.getElementById('bench-smart-lat'),
        benchSmartRange: document.getElementById('bench-smart-range'), benchCentLat: document.getElementById('bench-cent-lat'), benchOverhead: document.getElementById('bench-overhead')
    };

    function updateClock() { elements.systemClock.textContent = new Date().toTimeString().split(' ')[0]; }
    setInterval(updateClock, 1000); updateClock();

    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.tabBtns.forEach(b => b.classList.remove('active'));
            elements.tabPanes.forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            document.getElementById(targetId).classList.add('active');
            if (targetId === 'audit-tab') { loadAuditData(); loadBlocks(); }
        });
    });

    async function initData() {
        const [docsRes, patsRes] = await Promise.all([fetch('/api/doctors'), fetch('/api/patients')]);
        const docsData = await docsRes.json();
        const patsData = await patsRes.json();
        state.doctors = docsData.doctors || [];
        state.patients = patsData.patients || [];
        elements.doctorSelect.innerHTML = state.doctors.map(d => `<option value="${d.doctor_id}">${d.name} (${d.doctor_id})</option>`).join('');
        elements.patientSelect.innerHTML = state.patients.map(p => `<option value="${p.patient_id}">${p.full_name} (${p.patient_id}) - ${p.triage_state}</option>`).join('');
        loadAuditData();
    }

    elements.quickReasonBtns.forEach(btn => btn.addEventListener('click', () => elements.reasonInput.value = btn.getAttribute('data-reason')));

    elements.breakGlassForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            patient_id: elements.patientSelect.value, doctor_id: elements.doctorSelect.value,
            urgency: elements.urgencySelect.value, duration_seconds: parseInt(elements.durationSelect.value, 10),
            reason: elements.reasonInput.value.trim()
        };
        const res = await fetch('/api/emergency/request', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        const data = await res.json();
        startEmergencySession(data);
    });

    function startEmergencySession(sessionData) {
        clearInterval(state.timerInterval);
        state.activeGrant = sessionData.grant;
        state.totalDuration = sessionData.grant.duration_seconds;
        state.remainingSeconds = sessionData.grant.duration_seconds;
        elements.noSessionPlaceholder.style.display = 'none';
        elements.expiredSessionView.style.display = 'none';
        elements.activeSessionView.style.display = 'block';
        elements.sessionBadge.textContent = 'Active Break-Glass Token';
        elements.sessionBadge.className = 'badge badge-success';
        elements.activeGrantId.textContent = sessionData.grant.grant_id.substring(0, 24) + '...';
        elements.activeBlockInfo.textContent = `Confirmed on-chain | Triage: ${sessionData.grant.urgency}`;
        elements.activeLatency.textContent = `${sessionData.latency_ms} ms`;
        const med = sessionData.medical_data.emergency_clinical_profile;
        elements.medBloodGroup.textContent = med.blood_group;
        elements.medAllergies.textContent = Array.isArray(med.allergies) ? med.allergies.join('; ') : med.allergies;
        elements.medMedications.textContent = Array.isArray(med.active_medications) ? med.active_medications.join('; ') : med.active_medications;
        elements.medConditions.textContent = Array.isArray(med.existing_chronic_conditions) ? med.existing_chronic_conditions.join('; ') : med.existing_chronic_conditions;
        elements.medResuscitation.textContent = med.resuscitation_code;
        elements.medContacts.textContent = (med.emergency_contacts || []).map(c => `${c.name} (${c.relationship}): ${c.phone}`).join(', ');
        elements.medClinicalWarning.textContent = med.critical_warnings || 'None';
        renderCountdown();
        state.timerInterval = setInterval(() => {
            state.remainingSeconds--;
            renderCountdown();
            if (state.remainingSeconds <= 0) {
                clearInterval(state.timerInterval);
                elements.activeSessionView.style.display = 'none';
                elements.expiredSessionView.style.display = 'block';
                elements.sessionBadge.textContent = 'Access Expired';
                elements.sessionBadge.className = 'badge badge-danger';
                loadAuditData();
            }
        }, 1000);
    }

    function renderCountdown() {
        const mins = Math.floor(Math.max(0, state.remainingSeconds) / 60);
        const secs = Math.floor(Math.max(0, state.remainingSeconds) % 60);
        elements.countdownTimer.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        elements.timerProgress.style.width = `${Math.max(0, (state.remainingSeconds / state.totalDuration) * 100)}%`;
    }

    elements.btnEarlyRevoke.addEventListener('click', async () => {
        if (!state.activeGrant) return;
        await fetch('/api/emergency/revoke', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ grant_id: state.activeGrant.grant_id, doctor_or_admin: state.activeGrant.doctor_id, reason: "Session closed early." })
        });
        clearInterval(state.timerInterval);
        elements.activeSessionView.style.display = 'none';
        elements.expiredSessionView.style.display = 'block';
    });

    elements.btnResetSession.addEventListener('click', () => {
        elements.expiredSessionView.style.display = 'none';
        elements.noSessionPlaceholder.style.display = 'block';
        elements.sessionBadge.textContent = 'No Active Session';
        elements.sessionBadge.className = 'badge badge-secondary';
    });

    async function loadAuditData() {
        const res = await fetch('/api/audit/logs');
        const data = await res.json();
        elements.statLogsCount.textContent = data.total_count;
        elements.auditTableBody.innerHTML = (data.logs || []).map(log => `
            <tr>
                <td>${new Date(log.timestamp * 1000).toLocaleTimeString()}</td>
                <td><span class="badge ${log.action.includes('TRIGGERED') ? 'badge-danger' : 'badge-success'}">${log.action}</span></td>
                <td><strong>${log.patient_id}</strong></td>
                <td>${log.doctor_name || log.doctor_id}</td>
                <td><small>${log.data_category}</small></td>
                <td class="mono"><small>${log.payload_hash.substring(0, 16)}...</small></td>
                <td class="mono"><small>${log.previous_log_hash.substring(0, 16)}...</small></td>
            </tr>
        `).join('');
    }

    async function loadBlocks() {
        const res = await fetch('/api/audit/blocks');
        const data = await res.json();
        elements.statBlocksCount.textContent = data.chain_length;
        elements.blocksList.innerHTML = data.blocks.map(b => `
            <div class="block-item" style="background:#f8fafc; padding:0.8rem; margin-bottom:0.5rem; border:1px solid #e2e8f0; border-radius:6px;">
                <strong>Block #${b.index}</strong> | Hash: <span class="mono">${b.hash.substring(0, 20)}...</span> | Txs: ${b.transactions.length}
            </div>
        `).join('');
    }

    elements.btnVerifyIntegrity.addEventListener('click', async () => {
        const res = await fetch('/api/audit/verify');
        const report = await res.json();
        elements.verificationBanner.style.display = 'flex';
        if (report.is_valid) {
            elements.verificationBanner.className = 'verification-banner banner-pass';
            elements.bannerIcon.textContent = '✅';
            elements.bannerTitle.textContent = 'Cryptographic Integrity Confirmed';
            elements.bannerDesc.textContent = `All ${report.total_blocks} blocks and ${report.total_audit_logs} audit entries are 100% verified.`;
        } else {
            elements.verificationBanner.className = 'verification-banner banner-fail';
            elements.bannerIcon.textContent = '🚨';
            elements.bannerTitle.textContent = 'Tampering Detected!';
            elements.bannerDesc.textContent = `Caught ${report.block_issues.length} block anomalies.`;
        }
    });

    elements.btnSimulateTamper.addEventListener('click', async () => {
        await fetch('/api/audit/tamper?block_index=1', { method: 'POST' });
        elements.btnRestoreLedger.style.display = 'inline-flex';
        elements.btnVerifyIntegrity.click();
    });

    elements.btnRestoreLedger.addEventListener('click', async () => {
        await fetch('/api/audit/restore', { method: 'POST' });
        elements.btnRestoreLedger.style.display = 'none';
        elements.btnVerifyIntegrity.click();
        loadAuditData();
    });

    elements.btnRunBenchmark.addEventListener('click', async () => {
        elements.btnRunBenchmark.disabled = true;
        const res = await fetch('/api/benchmark/run?iterations=50', { method: 'POST' });
        const data = await res.json();
        elements.benchSmartLat.textContent = `${data.smart_contract.avg_latency_ms} ms`;
        elements.benchSmartRange.textContent = `Min: ${data.smart_contract.min_latency_ms}ms | Max: ${data.smart_contract.max_latency_ms}ms`;
        elements.benchCentLat.textContent = `${data.centralized_baseline.avg_latency_ms} ms`;
        elements.benchOverhead.textContent = `+${data.overhead_analysis.additional_latency_ms} ms`;
        elements.btnRunBenchmark.disabled = false;
    });

    initData();
});
