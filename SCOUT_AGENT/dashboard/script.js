// dashboard/script.js
// Next-Gen UI Logic — Smart Sorting, P4 Filtering, Archive Toggle

let currentFilter = 'all';
let showArchived = false;

// ────────────────────────────────────────────────
// Count-Up Animation (easeOutQuart)
// ────────────────────────────────────────────────
function animateValue(el, start, end, duration, prefix = "") {
    let t0 = null;
    const step = (ts) => {
        if (!t0) t0 = ts;
        const p = Math.min((ts - t0) / duration, 1);
        const v = Math.floor(p * (end - start) + start);
        el.innerHTML = prefix + v.toLocaleString();
        if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}

// ────────────────────────────────────────────────
// Composite Score for Algorithmic Sorting
// Leads with high Propensity + high LTV float to the top.
// The formula: 40% Propensity + 35% LTV + 25% Confidence
// ────────────────────────────────────────────────
const TIER_ORDER = { 'P1': 0, 'P2': 1, 'P3': 2, 'P4': 3 };

function compositeScore(lead) {
    const prop = lead.score_propensity || 0;
    const ltv  = lead.score_ltv || 0;
    const conf = (lead.confidence_score || 0) * 10; // normalize 0-1 to 0-10
    return (prop * 0.40) + (ltv * 0.35) + (conf * 0.25);
}

function sortLeads(a, b) {
    // Primary: tier rank (P1 first, P4 last)
    const tierA = TIER_ORDER[a.priority_tier] ?? 3;
    const tierB = TIER_ORDER[b.priority_tier] ?? 3;
    if (tierA !== tierB) return tierA - tierB;
    // Secondary: composite score descending within the same tier
    return compositeScore(b) - compositeScore(a);
}

// ────────────────────────────────────────────────
// Fetch + Render Pipeline
// ────────────────────────────────────────────────
async function fetchOpportunities() {
    try {
        const res = await fetch('/api/opportunities');
        const data = await res.json();
        renderDashboard(data);
    } catch (err) {
        console.error('Fetch error:', err);
    }
}

function renderDashboard(allLeads) {
    const grid = document.getElementById('leads-grid');

    // ── Step 1: Product filter ──
    let leads = allLeads.filter(lead => {
        if (currentFilter === 'all') return true;
        const fit = (lead.sbi_product_fit || '').toLowerCase();
        if (currentFilter === 'loan') return fit.includes('loan') || fit.includes('finance') || fit.includes('credit');
        if (currentFilter === 'retail') return fit.includes('account') || fit.includes('retail') || fit.includes('edu');
        return true;
    });

    // ── Step 2: P4 archive filter ──
    const activeLeads  = leads.filter(l => l.priority_tier !== 'P4');
    const archivedLeads = leads.filter(l => l.priority_tier === 'P4');
    const visibleLeads = showArchived ? leads : activeLeads;

    // ── Step 3: Algorithmic sort (tier-first, then composite score) ──
    visibleLeads.sort(sortLeads);

    // ── Step 4: Compute top-level metrics (always from ALL leads, not just visible) ──
    let highPropCount = 0;
    let totalLTV = 0;
    allLeads.forEach(l => {
        if ((l.score_propensity || 0) >= 8) highPropCount++;
        totalLTV += (l.score_ltv || 5) * 50000;
    });

    // ── Step 5: Animate top metrics ──
    const totalEl = document.getElementById('metric-total');
    const highEl  = document.getElementById('metric-high');
    const ltvEl   = document.getElementById('metric-ltv');

    if (totalEl.dataset.val != allLeads.length) {
        animateValue(totalEl, parseInt(totalEl.dataset.val || 0), allLeads.length, 800);
        totalEl.dataset.val = allLeads.length;
    }
    if (highEl.dataset.val != highPropCount) {
        animateValue(highEl, parseInt(highEl.dataset.val || 0), highPropCount, 800);
        highEl.dataset.val = highPropCount;
    }
    if (ltvEl.dataset.val != totalLTV) {
        animateValue(ltvEl, parseInt(ltvEl.dataset.val || 0), totalLTV, 1200, "₹");
        ltvEl.dataset.val = totalLTV;
    }

    // ── Step 6: Render cards ──
    grid.innerHTML = '';

    if (visibleLeads.length === 0) {
        grid.innerHTML = `
            <div class="loading-state glass-card">
                <p>${showArchived ? 'No archived signals found.' : 'No actionable signals yet. Agents are scanning...'}</p>
            </div>`;
        return;
    }

    visibleLeads.forEach((lead, i) => {
        const card = document.createElement('div');
        card.className = 'opportunity-card glass-card fade-in-up';
        card.style.animationDelay = `${Math.min(i, 8) * 0.08}s`;

        const tier = lead.priority_tier || 'P3';
        const propensity = lead.score_propensity || 5;
        const ltv = lead.score_ltv || 5;
        const veracity = lead.veracity_score || 100;
        const xai = lead.xai_reasoning || "Standard algorithmic match based on demographic indicators.";
        
        // Entity Graph specific fields
        const companyName = lead.normalized_company_name || lead.company_or_entity || 'Unknown Entity';
        const decayedConf = Math.round((lead.decayed_confidence_score || lead.confidence_score || 0) * 100);
        const peakConf = Math.round((lead.confidence_score || 0) * 100);
        const signalCount = (lead.signal_history && lead.signal_history.length) ? lead.signal_history.length : 1;
        const daysOld = lead.days_since_last_signal || 0;
        
        const existingClientBadge = lead.is_existing_client ? `<span class="tier-badge" style="background: rgba(46, 204, 113, 0.2); color: #2ecc71; border-color: rgba(46, 204, 113, 0.4);">Existing Client</span>` : '';
        const decayText = (daysOld > 0 && decayedConf < peakConf) ? `<span style="font-size: 0.75rem; color: #e74c3c; display: block; margin-top: 4px;">Decayed from ${peakConf}% (${daysOld}d old)</span>` : '';

        card.innerHTML = `
            <div class="card-header">
                <div>
                    <h3 class="company-name">${companyName}</h3>
                    <div style="margin-top: 4px; font-size: 0.8rem; color: #a0aec0;">
                        ${signalCount > 1 ? `🔥 Aggregated from ${signalCount} signals` : `New Signal Detected`}
                    </div>
                </div>
                <div class="card-badges" style="text-align: right;">
                    <span class="conf-badge">${decayedConf}%</span>
                    ${decayText}
                    <div style="margin-top: 8px;">
                        ${existingClientBadge}
                        <span class="tier-badge tier-${tier}">${tier}</span>
                    </div>
                </div>
            </div>
            
            <p class="signal-text">"${lead.detected_signal || ''}"</p>
            
            <div class="metrics-container">
                <div class="metric-row">
                    <span class="metric-label">Propensity</span>
                    <div class="progress-track">
                        <div class="progress-fill fill-green" style="width: ${propensity * 10}%"></div>
                    </div>
                    <span class="metric-value">${propensity}/10</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Pred. LTV</span>
                    <div class="progress-track">
                        <div class="progress-fill fill-purple" style="width: ${ltv * 10}%"></div>
                    </div>
                    <span class="metric-value">${ltv}/10</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Veracity</span>
                    <div class="progress-track">
                        <div class="progress-fill fill-blue" style="width: ${veracity}%"></div>
                    </div>
                    <span class="metric-value">${veracity}%</span>
                </div>
            </div>

            <div class="xai-box">
                <div class="xai-label"><span>🧠</span> AI Reasoning (XAI)</div>
                <div class="xai-text">${xai}</div>
            </div>
            
            <div class="product-fit">
                🎯 ${lead.sbi_product_fit || 'Custom Solution'}
            </div>
        `;

        grid.appendChild(card);
    });

    // ── Step 7: Show archive count on button ──
    const archBtn = document.getElementById('archive-toggle');
    if (archBtn) {
        archBtn.innerHTML = showArchived
            ? `<span class="archive-icon">📦</span> Hide Archived (${archivedLeads.length})`
            : `<span class="archive-icon">📦</span> Show Archived (${archivedLeads.length})`;
    }
}

// ────────────────────────────────────────────────
// Event Listeners
// ────────────────────────────────────────────────
document.getElementById('product-filter').addEventListener('change', (e) => {
    currentFilter = e.target.value;
    fetchOpportunities();
});

document.getElementById('archive-toggle').addEventListener('click', () => {
    showArchived = !showArchived;
    const btn = document.getElementById('archive-toggle');
    btn.classList.toggle('active', showArchived);
    fetchOpportunities();
});

// ── Boot ──
fetchOpportunities();
setInterval(fetchOpportunities, 5000);