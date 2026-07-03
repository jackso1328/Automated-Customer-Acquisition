document.addEventListener("DOMContentLoaded", () => {
    const leadsGrid = document.getElementById("leads-grid");
    const filterSelect = document.getElementById("product-filter");
    
    let allOpportunities = [];

    // Priority tier display configuration
    const TIER_CONFIG = {
        "P1": { label: "P1 — Immediate", color: "#c0392b" },
        "P2": { label: "P2 — High",      color: "#e67e22" },
        "P3": { label: "P3 — Monitor",    color: "#8c7a52" },
        "P4": { label: "P4 — Archive",    color: "#95a5a6" },
    };

    // Fetch the parsed structured opportunities from our local server API
    async function fetchLeads() {
        try {
            const response = await fetch('/api/opportunities');
            if (!response.ok) throw new Error("Network issue communicating with local backend API.");
            
            allOpportunities = await response.json();
            
            // Sort by confidence score descending — best leads always on top
            allOpportunities.sort((a, b) => (b.confidence_score || 0) - (a.confidence_score || 0));
            
            updateMetrics(allOpportunities);
            renderLeads(allOpportunities);
        } catch (error) {
            console.error("Dashboard failed to retrieve data:", error);
            leadsGrid.innerHTML = `<div class="loading-state" style="color: red;">Error linking with Python Data Engine. Ensure server.py is running.</div>`;
        }
    }

    // Process raw metrics totals
    function updateMetrics(leads) {
        document.getElementById("metric-total").textContent = leads.length;
        
        const p1Count = leads.filter(item => item.priority_tier === "P1").length;
        const p2Count = leads.filter(item => item.priority_tier === "P2").length;
        document.getElementById("metric-high").textContent = p1Count + p2Count;
    }

    // Build visual cards dynamically from individual JSON entries
    function renderLeads(leads) {
        if (leads.length === 0) {
            leadsGrid.innerHTML = `<div class="loading-state">Active scanning underway. No structural business targets located in this configuration cycle.</div>`;
            return;
        }

        leadsGrid.innerHTML = ""; // Clear active loading state
        
        leads.forEach(lead => {
            const card = document.createElement("div");
            card.className = "opportunity-card";
            
            // Percentage and tier
            const percentageConf = Math.round((lead.confidence_score || 0) * 100);
            const tier = lead.priority_tier || "P4";
            const tierInfo = TIER_CONFIG[tier] || TIER_CONFIG["P4"];
            
            // Score breakdown (only for new algorithm leads)
            let breakdownHtml = '';
            if (lead.score_scale !== undefined) {
                breakdownHtml = `
                <div class="score-breakdown">
                    <div class="score-item">
                        <span class="score-label">Scale</span>
                        <div class="score-bar-track"><div class="score-bar-fill" style="width: ${lead.score_scale * 10}%"></div></div>
                        <strong>${lead.score_scale}/10</strong>
                    </div>
                    <div class="score-item">
                        <span class="score-label">Urgency</span>
                        <div class="score-bar-track"><div class="score-bar-fill" style="width: ${lead.score_urgency * 10}%"></div></div>
                        <strong>${lead.score_urgency}/10</strong>
                    </div>
                    <div class="score-item">
                        <span class="score-label">Revenue</span>
                        <div class="score-bar-track"><div class="score-bar-fill score-bar-revenue" style="width: ${lead.score_revenue * 10}%"></div></div>
                        <strong>${lead.score_revenue}/10</strong>
                    </div>
                    <div class="score-item">
                        <span class="score-label">Advantage</span>
                        <div class="score-bar-track"><div class="score-bar-fill" style="width: ${lead.score_sbi_advantage * 10}%"></div></div>
                        <strong>${lead.score_sbi_advantage}/10</strong>
                    </div>
                </div>
                `;
            }
            
            // Penalty warning
            let penaltyHtml = '';
            if (lead.penalty_applied) {
                penaltyHtml = `<div class="penalty-warning">⚠ Score penalized — critical weakness detected in one or more dimensions</div>`;
            }

            card.innerHTML = `
                <div class="card-top">
                    <div class="company-name">${escapeHtml(lead.company_or_entity)}</div>
                    <div class="card-badges">
                        <div class="tier-badge" style="background-color: ${tierInfo.color}">${tierInfo.label}</div>
                        <div class="confidence-badge">${percentageConf}%</div>
                    </div>
                </div>
                ${breakdownHtml}
                ${penaltyHtml}
                <div class="signal-text">"${escapeHtml(lead.detected_signal)}"</div>
                <div class="product-fit-box">
                    <div class="product-label">Recommended SBI Product</div>
                    <div class="product-name">${escapeHtml(lead.sbi_product_fit)}</div>
                </div>
                <div class="justification-text">${escapeHtml(lead.justification)}</div>
            `;
            leadsGrid.appendChild(card);
        });
    }

    // Simple string escape wrapper to secure text generation inside the browser DOM
    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    // Simple string search filter rules matching product categories
    filterSelect.addEventListener("change", (e) => {
        const val = e.target.value;
        if (val === "all") {
            renderLeads(allOpportunities);
            return;
        }

        const filtered = allOpportunities.filter(item => {
            const product = (item.sbi_product_fit || "").toLowerCase();
            if (val === "loan") return product.includes("loan") || product.includes("finance");
            if (val === "guarantee") return product.includes("guarantee") || product.includes("letter") || product.includes("lc");
            if (val === "agri") return product.includes("kcc") || product.includes("agri") || product.includes("crop");
            if (val === "retail") return product.includes("salary") || product.includes("edu") || product.includes("scholar");
            return true;
        });
        
        renderLeads(filtered);
    });

    // Run immediately, then poll the file database every 5 seconds for zero-intervention live drops
    fetchLeads();
    setInterval(fetchLeads, 5000);
});