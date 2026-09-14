/**
 * Guided Demo Flow Controller for AI Food Quality System (Step 20)
 * Provides a 10-step interactive guided presentation of all live system features.
 */

window.demoGuideController = {
  currentStep: 0,
  totalSteps: 10,
  isActive: false,

  steps: [
    {
      step: 1,
      title: "Step 1: Executive Quality Dashboard",
      tab: "dashboard",
      targetId: "view-dashboard",
      message: "The Executive Dashboard displays real-time throughput metrics (Total, PASS, WARNING, HOLD, REJECT), live inspection throughput charts, and active risk alerts.",
      action: async () => {
        if (window.switchTab) window.switchTab("dashboard");
        if (window.refreshDashboard) await window.refreshDashboard();
      }
    },
    {
      step: 2,
      title: "Step 2: Live Quality Inspection Console",
      tab: "inspection",
      targetId: "view-inspection",
      message: "The Live Inspection Console provides dual camera/upload snapshot acquisition, real-time AI product & packaging condition classification, and instant decision engine rules.",
      action: async () => {
        if (window.switchTab) window.switchTab("inspection");
      }
    },
    {
      step: 3,
      title: "Step 3: Chips Packet Inspection (PASS)",
      tab: "inspection",
      targetId: "view-inspection",
      message: "Simulating live inspection of a Chips Packet. Product AI classifies 'Chips Packet' (96.4% conf), Packaging AI predicts 'Normal Package' (93.1% conf), fetching nutrition automatically -> 🟢 PASS.",
      action: async () => {
        if (window.switchTab) window.switchTab("inspection");
        const prodSelect = document.getElementById("inspect-expected-product");
        if (prodSelect) prodSelect.value = "Chips Packet";
        
        const aiResult = {
          detectedProduct: "Chips Packet",
          productConfidence: 0.964,
          packagingCondition: "Normal Package",
          conditionConfidence: 0.931
        };
        
        if (window.updateAIBadges) window.updateAIBadges(aiResult);
        if (window.runEvaluationWithData) {
          await window.runEvaluationWithData("Chips Packet", aiResult, {
            batch_number: "BAT-DEMO-CHIPS-01",
            exp_date: "2026-11-20",
            net_weight: "50 g",
            serving_size: "20 g",
            is_label_found: true
          });
        }
      }
    },
    {
      step: 4,
      title: "Step 4: Damaged Package Detection (REJECT)",
      tab: "inspection",
      targetId: "view-inspection",
      message: "Simulating damaged package inspection. Packaging AI flags 'Damage Package' (91.0% conf) -> 🔴 REJECT. Recommended Action: Quarantine damaged stock.",
      action: async () => {
        if (window.switchTab) window.switchTab("inspection");
        const prodSelect = document.getElementById("inspect-expected-product");
        if (prodSelect) prodSelect.value = "Chips Packet";

        const aiResult = {
          detectedProduct: "Chips Packet",
          productConfidence: 0.925,
          packagingCondition: "Damage Package",
          conditionConfidence: 0.910
        };

        if (window.updateAIBadges) window.updateAIBadges(aiResult);
        if (window.runEvaluationWithData) {
          await window.runEvaluationWithData("Chips Packet", aiResult, {
            batch_number: "BAT-DEMO-CHIPS-02",
            exp_date: "2026-10-01",
            net_weight: "50 g",
            serving_size: "20 g",
            is_label_found: true
          });
        }
      }
    },
    {
      step: 5,
      title: "Step 5: Milk Pouch Inspection & Lab Parameters (PASS)",
      tab: "inspection",
      targetId: "view-inspection",
      message: "Simulating Milk Pouch inspection. Category detects 'Milk Pouch' (96.2% conf), loads Per 100 ml liquid nutrition, and verifies lab parameters (Fat 3.8%, SNF 8.6%, pH 6.6) -> 🟢 PASS.",
      action: async () => {
        if (window.switchTab) window.switchTab("inspection");
        const prodSelect = document.getElementById("inspect-expected-product");
        if (prodSelect) {
          prodSelect.value = "Milk Pouch";
          if (window.toggleMilkParamsDrawer) window.toggleMilkParamsDrawer("Milk Pouch");
        }

        const aiResult = {
          detectedProduct: "Milk Pouch",
          productConfidence: 0.962,
          packagingCondition: "Normal Package",
          conditionConfidence: 0.941
        };

        if (window.updateAIBadges) window.updateAIBadges(aiResult);
        if (window.runEvaluationWithData) {
          await window.runEvaluationWithData("Milk Pouch", aiResult, {
            batch_number: "BAT-DEMO-MILK-01",
            exp_date: "2026-10-15",
            net_weight: "500 ml",
            serving_size: "150 ml",
            is_label_found: true
          });
        }
      }
    },
    {
      step: 6,
      title: "Step 6: Product Category Mismatch (HOLD)",
      tab: "inspection",
      targetId: "view-inspection",
      message: "Simulating product mismatch error: Expected 'Chips Packet', but AI detects 'Milk Pouch' -> 🟠 HOLD. Prevents incorrect product packaging on production lines.",
      action: async () => {
        if (window.switchTab) window.switchTab("inspection");
        const prodSelect = document.getElementById("inspect-expected-product");
        if (prodSelect) prodSelect.value = "Chips Packet";

        const aiResult = {
          detectedProduct: "Milk Pouch",
          productConfidence: 0.915,
          packagingCondition: "Normal Package",
          conditionConfidence: 0.950
        };

        if (window.updateAIBadges) window.updateAIBadges(aiResult);
        if (window.runEvaluationWithData) {
          await window.runEvaluationWithData("Chips Packet", aiResult, {
            batch_number: "BAT-DEMO-CHIPS-01",
            exp_date: "2026-11-20",
            net_weight: "50 g",
            serving_size: "20 g",
            is_label_found: true
          });
        }
      }
    },
    {
      step: 7,
      title: "Step 7: Production Batch Management",
      tab: "batches",
      targetId: "view-batches",
      message: "The Batches tab lists all registered production batches, manufacturing dates, shelf-life rules, remaining days, and active batch activation controls.",
      action: async () => {
        if (window.switchTab) window.switchTab("batches");
        if (window.loadBatches) await window.loadBatches();
      }
    },
    {
      step: 8,
      title: "Step 8: Batch Expiry Monitoring & Stock at Risk",
      tab: "dashboard",
      targetId: "view-dashboard",
      message: "Expiry Monitoring categorizes stock into Normal, Expiring Soon, and Expired. The Stock at Risk table highlights urgent batches to support waste prevention.",
      action: async () => {
        if (window.switchTab) window.switchTab("dashboard");
        if (window.refreshDashboard) await window.refreshDashboard();
        const expElem = document.getElementById("expiry-stat-soon");
        if (expElem) expElem.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    },
    {
      step: 9,
      title: "Step 9: Inspection Audit Logs & History",
      tab: "history",
      targetId: "view-history",
      message: "The History tab logs every quality inspection with timestamps, confidence scores, decision status, and audit trail records saved to SQLite.",
      action: async () => {
        if (window.switchTab) window.switchTab("history");
        if (window.loadInspectionHistory) await window.loadInspectionHistory();
      }
    },
    {
      step: 10,
      title: "Step 10: Printable Inspection Audit Report",
      tab: "history",
      targetId: "report-modal",
      message: "Clicking 'Report' generates a formal, printable Audit Report modal containing complete AI classification, label verification, and operator review data.",
      action: async () => {
        if (window.switchTab) window.switchTab("history");
        if (window.viewPrintableReport) await window.viewPrintableReport(1);
      }
    }
  ],

  start: function() {
    this.isActive = true;
    this.currentStep = 0;
    this.renderOverlay();
    this.goToStep(0);
  },

  goToStep: async function(index) {
    if (index < 0) index = 0;
    if (index >= this.totalSteps) {
      this.finish();
      return;
    }

    this.currentStep = index;
    const stepObj = this.steps[index];

    // Close open report modal if switching away from Step 10
    if (index !== 9) {
      const modal = document.getElementById("report-modal");
      if (modal) modal.classList.remove("active");
    }

    if (stepObj.action) {
      try {
        await stepObj.action();
      } catch (err) {
        console.error("Demo step action error:", err);
      }
    }

    this.updateOverlayUI();
  },

  next: function() {
    this.goToStep(this.currentStep + 1);
  },

  prev: function() {
    this.goToStep(this.currentStep - 1);
  },

  skip: function() {
    this.finish();
  },

  finish: function() {
    this.isActive = false;
    const overlay = document.getElementById("demo-guided-overlay");
    if (overlay) overlay.style.display = "none";
    const reportModal = document.getElementById("report-modal");
    if (reportModal) reportModal.classList.remove("active");
    if (window.switchTab) window.switchTab("dashboard");
    if (window.showToast) window.showToast("success", "🎬 Guided Demo completed successfully!");
  },

  renderOverlay: function() {
    let overlay = document.getElementById("demo-guided-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "demo-guided-overlay";
      overlay.style.cssText = `
        position: fixed;
        top: 4.5rem;
        left: 50%;
        transform: translateX(-50%);
        z-index: 10000;
        width: 90%;
        max-width: 680px;
        background: var(--bg-card);
        border: 2px solid var(--accent);
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        border-radius: 10px;
        padding: 0.85rem 1.1rem;
        color: var(--text-color);
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        backdrop-filter: blur(8px);
      `;
      document.body.appendChild(overlay);
    }
    overlay.style.display = "flex";
  },

  updateOverlayUI: function() {
    const overlay = document.getElementById("demo-guided-overlay");
    if (!overlay) return;

    const stepObj = this.steps[this.currentStep];
    const isFirst = this.currentStep === 0;
    const isLast = this.currentStep === this.totalSteps - 1;

    overlay.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-color); padding-bottom:0.4rem;">
        <div style="display:flex; align-items:center; gap:0.5rem;">
          <span style="background:var(--primary); color:#fff; font-size:0.7rem; font-weight:700; padding:0.2rem 0.5rem; border-radius:4px;">DEMO MODE</span>
          <strong style="font-size:0.9rem; color:var(--accent); font-family:var(--font-heading);">${stepObj.title}</strong>
        </div>
        <span style="font-size:0.75rem; color:var(--text-dim); font-weight:600;">Step ${stepObj.step} of ${this.totalSteps}</span>
      </div>

      <div style="font-size:0.8rem; color:var(--text-muted); line-height:1.4;">
        ${stepObj.message}
      </div>

      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.2rem;">
        <button id="btn-demo-skip" class="btn" style="padding:0.25rem 0.6rem; font-size:0.75rem; border:1px solid var(--border-color); color:var(--text-dim);">Skip</button>
        
        <div style="display:flex; gap:0.4rem;">
          <button id="btn-demo-prev" class="btn" style="padding:0.25rem 0.75rem; font-size:0.75rem;" ${isFirst ? 'disabled' : ''}>← Previous</button>
          <button id="btn-demo-next" class="btn btn-primary" style="padding:0.25rem 0.85rem; font-size:0.75rem; font-weight:700;">${isLast ? 'Finish Demo' : 'Next →'}</button>
        </div>
      </div>
    `;

    document.getElementById("btn-demo-skip")?.addEventListener("click", () => this.skip());
    document.getElementById("btn-demo-prev")?.addEventListener("click", () => this.prev());
    document.getElementById("btn-demo-next")?.addEventListener("click", () => this.next());
  }
};
