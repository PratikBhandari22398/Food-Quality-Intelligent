/**
 * Main Application Frontend Controller
 */

const API_BASE = ""; // Same-origin relative API calls

let state = {
  activeTab: "dashboard",
  activeBatch: null,
  batches: [],
  products: [],
  currentInspectionResult: null,
  capturedImageBase64: null,
  ocrExtractedData: null,
  lastSavedInspectionId: null
};

document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

async function initApp() {
  setupNavigation();
  setupEvents();
  resetInspectionState();
  await loadProducts();
  await loadBatches();
  await refreshDashboard();
  
  // Initialize Teachable Machine AI Classifier
  if (window.aiClassifier) {
    window.aiClassifier.init();
  }
}

/* Navigation Setup */
function setupNavigation() {
  const navBtns = document.querySelectorAll(".nav-btn");
  navBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.target;
      switchTab(target);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll(".nav-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.target === tabId);
  });
  document.querySelectorAll(".view-section").forEach(sec => {
    sec.classList.toggle("active", sec.id === `view-${tabId}`);
  });

  if (tabId === "dashboard") {
    refreshDashboard();
  } else if (tabId === "history") {
    loadInspectionHistory();
  } else if (tabId === "batches") {
    loadBatches();
  } else if (tabId === "inspection") {
    loadBatches();
  }
}

/* Event Listeners */
function setupEvents() {
  // Product & Variant Selector Change in Inspection Console
  const prodSelect = document.getElementById("inspect-expected-product");
  const varSelect = document.getElementById("inspect-product-variant");

  function updateVariantOptions(category) {
    if (!varSelect) return;
    const catLower = (category || "").toLowerCase();
    if (catLower.includes("chips")) {
      varSelect.innerHTML = `
        <option value="Lay's Classic Salted">Lay's Classic Salted ₹20</option>
        <option value="Lay's Spanish Tomato Tango">Lay's Spanish Tomato Tango ₹20</option>
      `;
    } else if (catLower.includes("milk")) {
      varSelect.innerHTML = `
        <option value="₹10 Milk Pouch">₹10 Milk Pouch</option>
        <option value="₹31 Milk Pouch">₹31 Milk Pouch</option>
      `;
    } else {
      varSelect.innerHTML = `
        <option value="${category}">${category}</option>
      `;
    }
    fetchProductProfile(varSelect.value);
  }

  if (prodSelect) {
    prodSelect.addEventListener("change", (e) => {
      toggleMilkParamsDrawer(e.target.value);
      updateVariantOptions(e.target.value);
    });
  }

  if (varSelect) {
    varSelect.addEventListener("change", (e) => {
      fetchProductProfile(e.target.value);
    });
    // Initial fetch for demo default variant
    fetchProductProfile(varSelect.value);
  }

  // Camera, Upload & Reset Buttons (Step 22 State Management)
  const btnStartCam = document.getElementById("btn-start-cam");
  const btnUploadFront = document.getElementById("btn-upload-front");
  const btnStopCam = document.getElementById("btn-stop-cam");
  const btnCapture = document.getElementById("btn-capture-frame");
  const btnReset = document.getElementById("btn-reset-inspection");
  const fileInput = document.getElementById("image-file-input");
  const dropZone = document.getElementById("drag-drop-zone");

  if (btnStartCam) {
    btnStartCam.addEventListener("click", async () => {
      const started = await window.cameraHandler.startCamera();
      if (started) {
        btnStartCam.style.display = "none";
        if (btnUploadFront) btnUploadFront.style.display = "none";
        if (btnStopCam) {
          btnStopCam.style.display = "inline-flex";
          btnStopCam.innerHTML = `<i class="ph ph-arrow-counter-clockwise"></i> ↻ RETAKE`;
        }
        if (btnCapture) {
          btnCapture.style.display = "inline-flex";
          btnCapture.innerHTML = `<i class="ph ph-aperture"></i> ⚡ INSPECT`;
        }
        const card = document.getElementById("decision-result-card");
        if (card) card.className = "decision-card IDLE";
        const title = document.getElementById("decision-status-title");
        if (title) {
          title.innerText = "Camera Active";
          title.style.color = "var(--primary)";
        }
        const actionDiv = document.getElementById("decision-recommended-action");
        if (actionDiv) actionDiv.innerText = "Align product package in camera view and click ⚡ INSPECT.";
      }
    });
  }

  if (btnUploadFront && fileInput) {
    btnUploadFront.addEventListener("click", () => fileInput.click());
  }

  if (btnStopCam) {
    btnStopCam.addEventListener("click", () => {
      resetInspectionState();
    });
  }

  if (btnReset) {
    btnReset.addEventListener("click", () => {
      resetInspectionState();
      showToast("info", "Inspection state reset.");
    });
  }

  if (btnCapture) {
    btnCapture.addEventListener("click", handleInspectButtonClick);
  }

  if (fileInput && dropZone) {
    dropZone.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", async (e) => {
      if (e.target.files && e.target.files[0]) {
        const file = e.target.files[0];
        const b64 = await window.cameraHandler.loadImageFromFile(file);
        setImageReadyState(b64);
      }
    });

    // Drag & Drop handlers
    dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
    dropZone.addEventListener("drop", async (e) => {
      e.preventDefault();
      dropZone.classList.remove("drag-over");
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        const b64 = await window.cameraHandler.loadImageFromFile(e.dataTransfer.files[0]);
        setImageReadyState(b64);
      }
    });
  }

  // Label / OCR Back-Side Scan Controls (Requirement 1, 2, 3, 13, 18)
  const btnOcrUpload = document.getElementById("btn-ocr-upload");
  const btnOcrCapture = document.getElementById("btn-ocr-capture");
  const btnDoOcrScan = document.getElementById("btn-do-ocr-scan");
  const btnResetOcr = document.getElementById("btn-reset-ocr");
  const ocrFileInput = document.getElementById("ocr-file-input");

  if (btnOcrUpload && ocrFileInput) {
    btnOcrUpload.addEventListener("click", () => ocrFileInput.click());
    ocrFileInput.addEventListener("change", async (e) => {
      if (e.target.files && e.target.files[0]) {
        const file = e.target.files[0];
        if (validateImageFile(file)) {
          setBackLabelFile(file);
        }
      }
    });
  }

  if (btnOcrCapture) {
    btnOcrCapture.addEventListener("click", async () => {
      let b64 = window.cameraHandler.captureFrame();
      if (!b64) {
        const started = await window.cameraHandler.startCamera();
        if (started) {
          showToast("info", "📷 Camera started. Align back label and click CAPTURE again.");
          return;
        }
      }

      if (b64) {
        try {
          const blob = await (await fetch(b64)).blob();
          if (validateImageFile(blob)) {
            setBackLabelFile(blob, b64);
          }
        } catch (err) {
          console.error("Error creating back label blob:", err);
        }
      } else {
        showToast("error", "❌ Unable to capture frame. Please start camera or upload an image.");
      }
    });
  }

  if (btnDoOcrScan) {
    btnDoOcrScan.addEventListener("click", () => {
      if (state.backLabelFileOrBlob) {
        scanBackLabel(state.backLabelFileOrBlob);
      } else {
        showToast("warning", "⚠️ Please capture or upload a back label image first.");
      }
    });
  }

  if (btnResetOcr) {
    btnResetOcr.addEventListener("click", () => {
      resetBackLabelState();
    });
  }

  // Run Re-evaluate on Lab Parameters change
  const milkInputs = document.querySelectorAll(".milk-lab-input");
  milkInputs.forEach(inp => {
    inp.addEventListener("change", () => {
      if (state.capturedImageBase64) {
        runEvaluationOnly();
      }
    });
  });

  // View Details Modal Listeners (Requirement 6 & 14)
  const btnOpenModal = document.getElementById("btn-open-details-modal");
  const btnCloseModal = document.getElementById("btn-close-details-modal");
  const detailsModal = document.getElementById("inspection-details-modal");

  if (btnOpenModal && detailsModal) {
    btnOpenModal.addEventListener("click", () => {
      detailsModal.style.display = "flex";
    });
  }
  if (btnCloseModal && detailsModal) {
    btnCloseModal.addEventListener("click", () => {
      detailsModal.style.display = "none";
    });
  }
  if (detailsModal) {
    detailsModal.addEventListener("click", (e) => {
      if (e.target === detailsModal) detailsModal.style.display = "none";
    });
  }

  // Save Inspection Button
  const btnSave = document.getElementById("btn-save-inspection");
  if (btnSave) {
    btnSave.addEventListener("click", saveCurrentInspection);
  }

  // Human Review Buttons (Requirement 9)
  const btnApprove = document.getElementById("btn-review-approve");
  const btnReject = document.getElementById("btn-review-reject");
  const btnReinspect = document.getElementById("btn-review-reinspect");

  if (btnApprove) btnApprove.addEventListener("click", () => submitHumanReview("APPROVED"));
  if (btnReject) btnReject.addEventListener("click", () => submitHumanReview("REJECTED"));
  if (btnReinspect) btnReinspect.addEventListener("click", () => submitHumanReview("REINSPECT_REQUESTED"));

  // Create Batch Form Submit
  const batchForm = document.getElementById("create-batch-form");
  if (batchForm) {
    batchForm.addEventListener("submit", createNewBatch);
  }

  // Batch Expiry Rule Type Selector Toggle
  const ruleTypeSelect = document.getElementById("batch-rule-type-select");
  const groupExp = document.getElementById("group-batch-exp-date");
  const groupDur = document.getElementById("group-batch-duration");

  if (ruleTypeSelect) {
    ruleTypeSelect.addEventListener("change", (e) => {
      if (e.target.value === "MONTHS_FROM_MANUFACTURE") {
        if (groupExp) groupExp.style.display = "none";
        if (groupDur) groupDur.style.display = "block";
      } else {
        if (groupExp) groupExp.style.display = "block";
        if (groupDur) groupDur.style.display = "none";
      }
    });
  }

  const btnCloseBatchModal = document.getElementById("btn-close-batch-modal");
  const batchDetailsModal = document.getElementById("batch-details-modal");
  if (btnCloseBatchModal && batchDetailsModal) {
    btnCloseBatchModal.addEventListener("click", () => {
      batchDetailsModal.style.display = "none";
    });
  }
  if (batchDetailsModal) {
    batchDetailsModal.addEventListener("click", (e) => {
      if (e.target === batchDetailsModal) batchDetailsModal.style.display = "none";
    });
  }

  // Start Guided Demo Button
  const btnStartDemo = document.getElementById("btn-start-demo");
  if (btnStartDemo) {
    btnStartDemo.addEventListener("click", () => {
      if (window.demoGuideController) {
        window.demoGuideController.start();
      }
    });
  }
}



/* Toast Notifications (Requirement 15) */
function showToast(type, message) {
  const container = document.getElementById("app-toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  const bgMap = {
    success: "rgba(16, 185, 129, 0.95)",
    warning: "rgba(245, 158, 11, 0.95)",
    error: "rgba(239, 68, 68, 0.95)",
    info: "rgba(99, 102, 241, 0.95)"
  };

  toast.style.cssText = `
    background: ${bgMap[type] || bgMap.info};
    color: #fff;
    padding: 0.65rem 0.9rem;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    z-index: 10000;
    transition: all 0.3s ease;
  `;
  toast.innerText = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

window.showToast = showToast;

/* Image Validation (Requirement 4) */
function validateImageFile(fileOrBlob) {
  if (!fileOrBlob) {
    showToast("error", "❌ Invalid Image: No file provided.");
    return false;
  }
  if (fileOrBlob.type && !fileOrBlob.type.startsWith("image/")) {
    showToast("error", "❌ Invalid Image: Please select a valid JPG, JPEG, PNG or WEBP image.");
    return false;
  }
  if (fileOrBlob.size && (fileOrBlob.size < 50 || fileOrBlob.size > 15 * 1024 * 1024)) {
    showToast("error", "❌ Invalid Image: Image size must be under 15 MB.");
    return false;
  }
  return true;
}

/* Back Label State Management (Requirement 1, 13, 14, 15) */
function setBackLabelFile(fileOrBlob, previewDataUrl = null) {
  if (!fileOrBlob) return;

  // Revoke previous object URL to avoid memory leaks
  if (state.backLabelPreviewUrl) {
    try { URL.revokeObjectURL(state.backLabelPreviewUrl); } catch(e) {}
    state.backLabelPreviewUrl = null;
  }

  state.backLabelFileOrBlob = fileOrBlob;
  state.ocrExtractedData = null;
  resetPreviousOCRResults();

  const previewContainer = document.getElementById("ocr-preview-container");
  const previewImg = document.getElementById("ocr-image-preview");
  const scanControls = document.getElementById("ocr-scan-controls");
  const ocrBadge = document.getElementById("ocr-scan-status-badge");
  const btnScan = document.getElementById("btn-do-ocr-scan");

  if (previewContainer && previewImg) {
    if (previewDataUrl) {
      previewImg.src = previewDataUrl;
    } else if (fileOrBlob instanceof Blob || fileOrBlob instanceof File) {
      state.backLabelPreviewUrl = URL.createObjectURL(fileOrBlob);
      previewImg.src = state.backLabelPreviewUrl;
    }
    previewContainer.style.display = "block";
  }

  if (scanControls) scanControls.style.display = "grid";
  if (btnScan) {
    btnScan.innerText = "⚡ SCAN LABEL";
    btnScan.disabled = false;
  }
  if (ocrBadge) {
    ocrBadge.innerText = "Back label ready to scan.";
    ocrBadge.style.color = "var(--accent)";
  }

  showToast("info", "📸 Back label ready to scan. Click SCAN LABEL to process.");
}

function resetBackLabelState() {
  if (state.backLabelPreviewUrl) {
    try { URL.revokeObjectURL(state.backLabelPreviewUrl); } catch(e) {}
    state.backLabelPreviewUrl = null;
  }
  state.backLabelFileOrBlob = null;
  state.ocrExtractedData = null;

  const previewContainer = document.getElementById("ocr-preview-container");
  const scanControls = document.getElementById("ocr-scan-controls");
  const ocrBadge = document.getElementById("ocr-scan-status-badge");
  const btnScan = document.getElementById("btn-do-ocr-scan");

  if (previewContainer) previewContainer.style.display = "none";
  if (scanControls) scanControls.style.display = "none";
  if (btnScan) {
    btnScan.innerText = "⚡ SCAN LABEL";
    btnScan.disabled = true;
  }
  if (ocrBadge) {
    ocrBadge.innerText = "Upload or capture a back-label image.";
    ocrBadge.style.color = "var(--text-dim)";
  }

  resetPreviousOCRResults();
  runEvaluationOnly();
}

function resetPreviousOCRResults() {
  const mBatch = document.getElementById("modal-ocr-batch");
  const mExp = document.getElementById("modal-ocr-exp");
  const mWeight = document.getElementById("modal-ocr-weight");
  const mServing = document.getElementById("modal-ocr-serving");

  if (mBatch) mBatch.innerText = "--";
  if (mExp) mExp.innerText = "--";
  if (mWeight) mWeight.innerText = "--";
  if (mServing) mServing.innerText = "--";
}

/* Process & Scan OCR Label File (Requirement 1, 4, 5, 6, 7, 12, 14, 15) */
async function scanBackLabel(fileOrBlob) {
  const targetFile = fileOrBlob || state.backLabelFileOrBlob;
  if (!targetFile || !(targetFile instanceof Blob || targetFile instanceof File)) {
    showToast("warning", "⚠️ Upload or capture a back-label image.");
    return;
  }
  if (!validateImageFile(targetFile)) return;

  const ocrBadge = document.getElementById("ocr-scan-status-badge");
  const btnScan = document.getElementById("btn-do-ocr-scan");

  // Requirement 4: Developer-only debug logging
  console.log("BACK LABEL SCAN DEBUG", {
    fileExists: Boolean(targetFile),
    fileName: targetFile.name || "back_label.jpg",
    fileType: targetFile.type || "image/jpeg",
    fileSize: targetFile.size || 0
  });

  if (ocrBadge) {
    ocrBadge.innerText = "Scanning label...";
    ocrBadge.style.color = "var(--warn-color)";
  }

  if (btnScan) {
    btnScan.innerText = "🔄 SCANNING...";
    btnScan.disabled = true;
  }

  const expectedProduct = document.getElementById("inspect-expected-product").value;
  const detectedProduct = document.getElementById("badge-product-name").innerText || expectedProduct;

  const formData = new FormData();
  formData.append("image", targetFile, targetFile.name || "back_label.jpg");
  formData.append("file", targetFile, targetFile.name || "back_label.jpg");
  formData.append("expected_product", expectedProduct);
  formData.append("ai_detected_product", detectedProduct);

  // Requirement 5: Network request logging
  console.log("OCR request starting", {
    url: `${API_BASE}/api/inspect/ocr`,
    method: "POST",
    formDataKey: "image"
  });

  try {
    const res = await fetch(`${API_BASE}/api/inspect/ocr`, { method: "POST", body: formData });
    
    console.log("OCR Response HTTP Status:", res.status, res.headers.get("content-type"));

    if (!res.ok) {
      let errorMsg = "❌ OCR service failed.";
      if (res.status === 400) {
        errorMsg = "❌ Label image was not received.";
      } else if (res.status === 422) {
        errorMsg = "❌ Invalid image file.";
      } else if (res.status === 500) {
        errorMsg = "❌ OCR service failed. Please try again.";
      }

      try {
        const errData = await res.json();
        if (errData && errData.message) {
          errorMsg = `❌ ${errData.message}`;
        }
      } catch(e) {}

      if (ocrBadge) {
        ocrBadge.innerText = errorMsg;
        ocrBadge.style.color = "var(--reject-color)";
      }
      showToast("error", errorMsg);

      if (btnScan) {
        btnScan.innerText = "⚡ SCAN LABEL";
        btnScan.disabled = false;
      }
      return;
    }

    const resData = await res.json();
    const ocrRes = resData.ocr_result || resData;
    const ocrStatus = resData.ocr_status || ocrRes.ocr_status || "unclear";
    const fields = resData.fields || ocrRes.fields || {};
    const nutritionStatus = resData.nutrition_status || ocrRes.nutrition_status || "not_detected";

    state.ocrExtractedData = ocrRes;

    // Requirement 12: Frontend render debug logging
    console.log("OCR Response Render Debug", {
      ocrResponseReceived: true,
      nutritionDataPresent: Boolean(resData.nutrition_data && Object.keys(resData.nutrition_data).length > 0),
      batchPresent: Boolean(fields.batch_number && fields.batch_number.value),
      datePresent: Boolean(fields.mfg_date?.value || fields.use_by_date?.value || fields.best_before?.value),
      renderFunctionCalled: true
    });

    if (ocrStatus === "complete") {
      if (ocrBadge) {
        ocrBadge.innerText = "✅ Label scan complete.";
        ocrBadge.style.color = "var(--pass-color)";
      }
      showToast("success", "✅ Label scan complete.");
    } else if (ocrStatus === "partial_success" || ocrStatus === "nutrition_detected" || nutritionStatus === "detected") {
      if (ocrBadge) {
        ocrBadge.innerText = "🟡 Label scan partially completed.";
        ocrBadge.style.color = "var(--warn-color)";
      }
      showToast("warning", "🟡 Label scan partially completed.");
    } else if (ocrStatus === "unclear") {
      if (ocrBadge) {
        ocrBadge.innerText = "⚠️ Text could not be read clearly. Try another image.";
        ocrBadge.style.color = "var(--warn-color)";
      }
      showToast("warning", "⚠️ Text could not be read clearly. Try another image.");
    } else {
      if (ocrBadge) {
        ocrBadge.innerText = "❌ OCR service failed.";
        ocrBadge.style.color = "var(--reject-color)";
      }
      showToast("error", "❌ OCR service failed.");
    }

    populateOCRFields(ocrRes, fields);
    updateOCRVerificationBadges(resData);
    updateDebugPanel(resData);

    if (nutritionStatus === "detected" && resData.nutrition_data) {
      renderNutritionTable(resData.nutrition_data, "OCR From Package");
    }

    // Re-run decision evaluation with updated OCR data
    await runEvaluationOnly();

    if (btnScan) {
      btnScan.innerText = "🔄 SCAN AGAIN";
      btnScan.disabled = false;
    }
  } catch (err) {
    console.error("Technical OCR scan error:", err);
    
    if (btnScan) {
      btnScan.innerText = "⚡ SCAN LABEL";
      btnScan.disabled = false;
    }

    if (err instanceof TypeError || (err.message && err.message.includes("fetch"))) {
      if (ocrBadge) {
        ocrBadge.innerText = "❌ Unable to connect to inspection service.";
        ocrBadge.style.color = "var(--reject-color)";
      }
      showToast("error", "❌ Unable to connect to inspection service.");
    } else {
      if (ocrBadge) {
        ocrBadge.innerText = "❌ OCR service failed.";
        ocrBadge.style.color = "var(--reject-color)";
      }
      showToast("error", "❌ OCR service failed.");
    }
  }
}

// Alias processOCRLabelFile to scanBackLabel for backward compatibility
const processOCRLabelFile = scanBackLabel;

function updateOCRVerificationBadges(data) {
  const bConsistency = document.getElementById("badge-consistency-check");
  const bExpiry = document.getElementById("badge-expiry-check");
  const bOcrDb = document.getElementById("badge-ocr-vs-db-check");
  const bRef = document.getElementById("badge-reference-check");

  if (data.consistency_check && bConsistency) {
    bConsistency.innerText = data.consistency_check.status_text;
    bConsistency.style.borderColor = data.consistency_check.is_consistent ? "var(--pass-color)" : "var(--warn-color)";
    bConsistency.style.color = data.consistency_check.is_consistent ? "var(--pass-color)" : "var(--warn-color)";
  }

  if (data.ocr_result && bExpiry) {
    bExpiry.innerText = data.ocr_result.expiry_status_display;
    const isVal = data.ocr_result.expiry_status === "VALID";
    bExpiry.style.borderColor = isVal ? "var(--pass-color)" : "var(--reject-color)";
    bExpiry.style.color = isVal ? "var(--pass-color)" : "var(--reject-color)";
  }

  if (data.ocr_vs_database && bOcrDb) {
    bOcrDb.innerText = `DB vs OCR: ${data.ocr_vs_database.overall_status}`;
    bOcrDb.style.borderColor = data.ocr_vs_database.has_mismatch ? "var(--warn-color)" : "var(--primary)";
    bOcrDb.style.color = data.ocr_vs_database.has_mismatch ? "var(--warn-color)" : "var(--accent)";
  }

  if (data.reference_check && bRef) {
    bRef.innerText = data.reference_check.overall_status;
    const isWithin = data.reference_check.overall_status === "✅ WITHIN REFERENCE";
    bRef.style.borderColor = isWithin ? "var(--pass-color)" : "var(--warn-color)";
    bRef.style.color = isWithin ? "var(--pass-color)" : "var(--warn-color)";
  }
}

function updateDebugPanel(resData) {
  const dbg = resData.debug_info || resData.ocr_result?.debug_info;
  if (!dbg) return;
  const eng = document.getElementById("debug-ocr-engine");
  const pre = document.getElementById("debug-ocr-preproc");
  const tm = document.getElementById("debug-ocr-time");
  const raw = document.getElementById("debug-ocr-raw-text");

  if (eng) eng.innerText = dbg.engine_used || "PyTesseract";
  if (pre) pre.innerText = dbg.preprocessing_method || "Multi-variant";
  if (tm) tm.innerText = `${dbg.processing_time_ms || 0} ms`;
  if (raw) raw.value = dbg.raw_text || "";
}

/* Toggle Milk Parameters Drawer */
function toggleMilkParamsDrawer(productName) {
  const drawer = document.getElementById("milk-params-drawer");
  const naNotice = document.getElementById("milk-na-notice");
  if (!productName) return;
  const isMilk = productName.toLowerCase().includes("milk");
  if (drawer) drawer.style.display = isMilk ? "block" : "none";
  if (naNotice) naNotice.style.display = isMilk ? "none" : "block";
}

/* API Calls */
async function loadProducts() {
  try {
    const res = await fetch(`${API_BASE}/api/products`);
    const data = await res.json();
    state.products = data;
    
    const select = document.getElementById("inspect-expected-product");
    const batchProdSelect = document.getElementById("batch-product-select");
    
    if (select) {
      select.innerHTML = `<option value="Not Specified">Not Specified (General Inspection)</option>` +
        data.map(p => `<option value="${p.name}">${p.name}</option>`).join("");
      select.value = "Not Specified";
      toggleMilkParamsDrawer("Not Specified");
    }
    if (batchProdSelect) {
      batchProdSelect.innerHTML = data.map(p => `<option value="${p.id}">${p.name}</option>`).join("");
    }
  } catch (err) {
    console.error("Failed to load products:", err);
  }
}

async function loadBatches() {
  try {
    const res = await fetch(`${API_BASE}/api/batches`);
    const data = await res.json();
    state.batches = data;
    
    const active = data.find(b => b.status === "ACTIVE") || null;
    state.activeBatch = active;

    const activePill = document.getElementById("active-batch-name");
    if (activePill) {
      if (active) {
        activePill.innerText = `${active.batch_number} (${active.product_name})`;
      } else {
        activePill.innerText = "No active batch selected";
      }
    }

    renderBatchesTable(data);
  } catch (err) {
    console.error("Failed to load batches:", err);
  }
}


async function refreshDashboard() {
  try {
    const resSummary = await fetch(`${API_BASE}/api/dashboard/summary`);
    const summary = await resSummary.json();

    document.getElementById("stat-total").innerText = summary.total_inspections;
    document.getElementById("stat-pass").innerText = summary.pass_count;
    document.getElementById("stat-warn").innerText = summary.warning_count;
    document.getElementById("stat-hold").innerText = summary.hold_count;
    document.getElementById("stat-reject").innerText = summary.reject_count;

    renderRecentActivity(summary.recent_inspections);

    // Fetch active alerts from API
    if (summary.active_alerts && summary.active_alerts.length > 0) {
      renderAlertsFeed(summary.active_alerts);
    } else {
      const resAlerts = await fetch(`${API_BASE}/api/inspect/alerts`);
      const alertsData = await resAlerts.json();
      renderAlertsFeed(alertsData);
    }

    // Populate Expiry Monitoring Stat Cards
    if (summary.expiry_summary) {
      const expNorm = document.getElementById("expiry-stat-normal");
      const expSoon = document.getElementById("expiry-stat-soon");
      const expExp = document.getElementById("expiry-stat-expired");
      const expUnk = document.getElementById("expiry-stat-unknown");

      if (expNorm) expNorm.innerText = summary.expiry_summary.NORMAL || 0;
      if (expSoon) expSoon.innerText = summary.expiry_summary.EXPIRING_SOON || 0;
      if (expExp) expExp.innerText = summary.expiry_summary.EXPIRED || 0;
      if (expUnk) expUnk.innerText = summary.expiry_summary.UNKNOWN || 0;
    }

    // Populate Stock at Risk Table
    renderStockAtRiskTable(summary.stock_at_risk || []);

    const resCharts = await fetch(`${API_BASE}/api/dashboard/charts`);
    const chartsData = await resCharts.json();

    if (window.dashboardCharts) {
      window.dashboardCharts.renderStatusPie("chart-status-pie", chartsData.pie);
      window.dashboardCharts.renderTimeline("chart-timeline", chartsData.timeline);
    }
  } catch (err) {
    console.error("Failed to refresh dashboard:", err);
    showToast("warning", "⚠️ Dashboard data unavailable.");
  }
}


async function getPredictionTargetElement() {
  const video = document.getElementById("webcam-video");
  if (video && video.style.display !== "none" && video.readyState >= 2 && video.videoWidth > 0) {
    return video;
  }

  const img = document.getElementById("image-preview");
  if (img && img.src && img.complete && img.naturalWidth > 0) {
    return img;
  }

  if (state.capturedImageBase64) {
    return new Promise((resolve, reject) => {
      const newImg = new Image();
      newImg.onload = () => resolve(newImg);
      newImg.onerror = () => reject(new Error("Failed to load captured image for AI model."));
      newImg.src = state.capturedImageBase64;
    });
  }

  if (img && img.src) {
    return new Promise((resolve, reject) => {
      const newImg = new Image();
      newImg.onload = () => resolve(newImg);
      newImg.onerror = () => reject(new Error("Failed to load image preview for AI model."));
      newImg.src = img.src;
    });
  }

  throw new Error("No valid image input available for AI inspection.");
}

/* Full AI + OCR + Decision Engine Pipeline */
async function runFullInspectionPipeline(imageBase64) {
  state.inspectionSavedForCurrentRun = false;
  state.lastSavedInspectionId = null;

  const expectedProduct = document.getElementById("inspect-expected-product")?.value || "Not Specified";
  
  let targetElement;
  try {
    targetElement = await getPredictionTargetElement();
  } catch (err) {
    console.error("Image Input Resolution Error:", err);
    renderModelErrorCard("Invalid image input provided for AI prediction.");
    return;
  }

  let aiResult;
  try {
    // Step 1: AI Dual Teachable Machine Prediction
    aiResult = await window.aiClassifier.predict(targetElement);
  } catch (err) {
    console.error("AI Model Prediction Error:", err);
    renderModelErrorCard(err.message || "AI Model Prediction Error");
    return;
  }

  try {
    // Update AI Badges in UI
    updateAIBadges(aiResult);

    // Step 2: OCR Label Extraction if not already loaded
    let ocrData = state.ocrExtractedData || { is_label_found: true };

    // Step 3: Run Decision Engine Evaluation
    await runEvaluationWithData(expectedProduct, aiResult, ocrData);
  } catch (err) {
    console.error("Evaluation Error:", err);
    renderModelErrorCard("Decision engine evaluation failed.");
  }
}

function renderModelErrorCard(errorMsg) {
  const card = document.getElementById("decision-result-card");
  const title = document.getElementById("decision-status-title");
  const actionDiv = document.getElementById("decision-recommended-action");

  if (card) card.className = "decision-card REJECT";
  if (title) {
    title.innerText = "❌ ERROR";
    title.style.color = "var(--reject-color)";
  }
  if (actionDiv) {
    actionDiv.innerText = errorMsg || "AI inspection could not be completed. Please try another image.";
  }

  const actionsContainer = document.getElementById("result-actions-container");
  if (actionsContainer) actionsContainer.style.display = "none";

  const livePanel = document.getElementById("live-nutrition-panel");
  if (livePanel) livePanel.style.display = "none";
}

function updateAIBadges(aiResult) {
  const pName = document.getElementById("badge-product-name");
  const pConf = document.getElementById("badge-product-conf");
  const pBar = document.getElementById("bar-product-conf");
  const cName = document.getElementById("badge-condition-name");
  const cConf = document.getElementById("badge-condition-conf");
  const cBar = document.getElementById("bar-condition-conf");

  if (pName) pName.innerText = aiResult.detectedProduct;
  if (pConf) pConf.innerText = `${(aiResult.productConfidence * 100).toFixed(1)}%`;
  if (pBar) pBar.style.width = `${aiResult.productConfidence * 100}%`;

  if (cName) cName.innerText = aiResult.packagingCondition;
  if (cConf) cConf.innerText = `${(aiResult.conditionConfidence * 100).toFixed(1)}%`;
  if (cBar) cBar.style.width = `${aiResult.conditionConfidence * 100}%`;

  // Render Developer Diagnostics Raw Probabilities (PART W)
  const diagModel1 = document.getElementById("diag-model1-probabilities");
  const diagModel2 = document.getElementById("diag-model2-probabilities");

  if (diagModel1 && aiResult.productTopPredictions) {
    diagModel1.innerHTML = aiResult.productTopPredictions.map(p =>
      `<div>- ${p.className}: <strong>${(p.probability * 100).toFixed(1)}%</strong></div>`
    ).join("");
  }
  if (diagModel2 && aiResult.packagingTopPredictions) {
    diagModel2.innerHTML = aiResult.packagingTopPredictions.map(k =>
      `<div>- ${k.className}: <strong>${(k.probability * 100).toFixed(1)}%</strong></div>`
    ).join("");
  }

  const warnBanner = document.getElementById("low-confidence-warning");
  if (warnBanner) {
    warnBanner.style.display = aiResult.isLowConfidence ? "block" : "none";
  }
}

function populateOCRFields(ocrData, fieldsMap = null) {
  const bNo = document.getElementById("ocr-batch-no");
  const eDate = document.getElementById("ocr-exp-date");
  const nWeight = document.getElementById("ocr-net-weight");
  const sSize = document.getElementById("ocr-serving-size");
  const bConf = document.getElementById("ocr-batch-conf");

  if (bNo) bNo.value = (ocrData.batch_number && ocrData.batch_number !== "Not Clearly Read" && ocrData.batch_number !== "Not detected") ? ocrData.batch_number : "";
  if (eDate) eDate.value = ocrData.exp_date || "";
  if (nWeight) nWeight.value = (ocrData.net_weight && ocrData.net_weight !== "Not detected") ? ocrData.net_weight : "";
  if (sSize) sSize.value = (ocrData.serving_size && ocrData.serving_size !== "Not detected") ? ocrData.serving_size : "";
  if (bConf && ocrData.ocr_confidence) bConf.innerText = `${ocrData.ocr_confidence}%`;

  // Populate Modal Fields
  const mBatch = document.getElementById("modal-ocr-batch");
  const mExp = document.getElementById("modal-ocr-exp");
  const mWeight = document.getElementById("modal-ocr-weight");
  const mServing = document.getElementById("modal-ocr-serving");

  const fields = fieldsMap || ocrData.fields || {};
  const bbStatus = fields.best_before?.status;

  if (mBatch) {
    const bVal = ocrData.batch_number;
    if (bVal && bVal !== "Not Clearly Read" && bVal !== "Not detected") {
      mBatch.innerText = bVal;
      mBatch.style.color = "var(--text-muted)";
    } else {
      mBatch.innerText = "⚠ Not Detected";
      mBatch.style.color = "var(--warn-color)";
    }
  }

  if (mExp) {
    if (ocrData.exp_date) {
      mExp.innerText = ocrData.exp_date;
      mExp.style.color = "var(--text-muted)";
    } else if (bbStatus === "relative_statement" || ocrData.expiry_status_display?.includes("Relative")) {
      mExp.innerText = "⚠ Relative Statement (Exact date unavailable)";
      mExp.style.color = "var(--warn-color)";
    } else {
      mExp.innerText = "⚠ Not Detected";
      mExp.style.color = "var(--warn-color)";
    }
  }

  if (mWeight) {
    const wVal = ocrData.net_weight;
    if (wVal && wVal !== "Not detected") {
      mWeight.innerText = wVal;
      mWeight.style.color = "var(--text-muted)";
    } else {
      mWeight.innerText = "⚠ Not Detected";
      mWeight.style.color = "var(--warn-color)";
    }
  }

  if (mServing) {
    mServing.innerText = ocrData.serving_size || "20 g";
  }

  if (ocrData.basis) {
    const basisBadge = document.getElementById("nutrition-basis-badge");
    if (basisBadge) basisBadge.innerText = `Basis: ${ocrData.basis.replace("_", " ")}`;
  }
}

function getMilkLabParamsFromUI() {
  const expectedProduct = document.getElementById("inspect-expected-product")?.value || "";
  const detectedProduct = document.getElementById("badge-product-name")?.innerText || "";
  const isMilk = expectedProduct.toLowerCase().includes("milk") || detectedProduct.toLowerCase().includes("milk");
  if (!isMilk) return null;

  const fat = parseFloat(document.getElementById("milk-fat-input").value) || 3.8;
  const snf = parseFloat(document.getElementById("milk-snf-input").value) || 8.6;
  const ph = parseFloat(document.getElementById("milk-ph-input").value) || 6.6;
  const temp = parseFloat(document.getElementById("milk-temp-input").value) || 5.0;

  return { fat, snf, ph, temperature: temp };
}

async function runEvaluationOnly() {
  const expectedProduct = document.getElementById("inspect-expected-product").value;
  const detectedProduct = document.getElementById("badge-product-name").innerText || expectedProduct;
  const productConf = parseFloat(document.getElementById("badge-product-conf").innerText) / 100 || 0.95;
  const packagingCond = document.getElementById("badge-condition-name").innerText || "Normal Package";
  const condConf = parseFloat(document.getElementById("badge-condition-conf").innerText) / 100 || 0.95;

  const aiResult = {
    detectedProduct,
    productConfidence: productConf,
    packagingCondition: packagingCond,
    conditionConfidence: condConf
  };

  const ocrData = state.ocrExtractedData || {
    batch_number: document.getElementById("ocr-batch-no").value,
    exp_date: document.getElementById("ocr-exp-date").value,
    net_weight: document.getElementById("ocr-net-weight").value,
    serving_size: document.getElementById("ocr-serving-size").value,
    is_label_found: true
  };

  await runEvaluationWithData(expectedProduct, aiResult, ocrData);
}

async function runEvaluationWithData(expectedProduct, aiResult, ocrData) {
  const milkParams = getMilkLabParamsFromUI();

  const payload = {
    expected_product: expectedProduct,
    detected_product: aiResult.detectedProduct,
    product_confidence: aiResult.productConfidence,
    packaging_condition: aiResult.packagingCondition,
    condition_confidence: aiResult.conditionConfidence,
    ocr_data: ocrData,
    milk_lab_params: milkParams,
    batch_number: (expectedProduct === "Not Specified" || !expectedProduct) ? null : state.activeBatch?.batch_number
  };

  try {
    const res = await fetch(`${API_BASE}/api/inspect/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const decision = await res.json();
    state.currentInspectionResult = { ...payload, decision };
    renderDecisionCard(decision);
    renderChecklistUI(decision.checklist);
    renderHumanReviewDrawer(decision);
    renderNutritionTable(decision.verified_nutrition);

    // Auto-save inspection to DB & update Dashboard, History, and Batches live data!
    state.inspectionSavedForCurrentRun = false;
    await saveCurrentInspection();
  } catch (err) {
    console.error("Failed to evaluate decision engine:", err);
  }
}

function renderDecisionCard(decision) {
  const card = document.getElementById("decision-result-card");
  const title = document.getElementById("decision-status-title");
  const actionDiv = document.getElementById("decision-recommended-action");
  const tsSpan = document.getElementById("summary-card-timestamp");
  const actionsContainer = document.getElementById("result-actions-container");

  if (card) card.className = `decision-card ${decision.final_status}`;
  if (title) {
    title.innerText = decision.final_status;
    title.style.color = "";
  }
  if (actionDiv) actionDiv.innerText = decision.recommended_action || decision.summary_card?.recommended_action || decision.reasons?.[0] || "";
  if (tsSpan) tsSpan.innerText = formatTimestamp(decision.summary_card?.timestamp || new Date());

  if (actionsContainer) actionsContainer.style.display = "flex";
}

/* Render Checklist UI (Requirement 7) */
function renderChecklistUI(chk) {
  if (!chk) return;
  document.getElementById("chk-prod-det").innerText = chk["Product Detection"] || "--";
  document.getElementById("chk-prod-match").innerText = chk["Product Match"] || "--";
  document.getElementById("chk-pkg-cond").innerText = chk["Package Condition"] || "--";
  document.getElementById("chk-lbl-read").innerText = chk["Label Readability"] || "--";
  document.getElementById("chk-batch-num").innerText = chk["Batch Number"] || "--";
  document.getElementById("chk-exp-date").innerText = chk["Best Before"] || "--";
  document.getElementById("chk-nutrition").innerText = chk["Nutrition"] || "--";
  document.getElementById("chk-milk-qual").innerText = chk["Milk Quality"] || "N/A";
  document.getElementById("chk-final-dec").innerText = chk["Final Decision"] || "--";
}

/* Render Human Review Drawer (Requirement 9) */
function renderHumanReviewDrawer(decision) {
  const drawer = document.getElementById("human-review-drawer");
  const recSpan = document.getElementById("review-ai-recommendation");
  if (!drawer) return;

  if (decision.final_status === "HOLD" || decision.final_status === "REJECT" || decision.final_status === "WARNING") {
    drawer.style.display = "block";
    if (recSpan) recSpan.innerText = `AI Rec: ${decision.final_status}`;
  } else {
    drawer.style.display = "none";
  }
}

/* Submit Human Review */
async function submitHumanReview(decisionChoice) {
  if (!state.lastSavedInspectionId) {
    alert("Please log and save the inspection record first before submitting operator review.");
    return;
  }

  const reviewer = document.getElementById("reviewer-name-input").value || "Quality Operator";
  const comment = document.getElementById("reviewer-comment-input").value || "";

  try {
    const res = await fetch(`${API_BASE}/api/inspect/human-review/${state.lastSavedInspectionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision: decisionChoice, reviewer, comment })
    });

    if (res.ok) {
      alert(`Human Operator Review recorded successfully: ${decisionChoice}`);
      document.getElementById("human-review-drawer").style.display = "none";
      await refreshDashboard();
    } else {
      alert("Failed to submit operator review.");
    }
  } catch (err) {
    console.error("Error submitting human review:", err);
  }
}

async function fetchProductProfile(variantName) {
  if (!variantName) return;
  try {
    const res = await fetch(`${API_BASE}/api/inspect/product-profile/${encodeURIComponent(variantName)}`);
    if (!res.ok) return;
    const profile = await res.json();
    state.currentProductProfile = profile;
    renderNutritionTable(profile);
  } catch (err) {
    console.error("Failed to fetch product profile:", err);
  }
}

function safeVal(val, defaultText = "Not Available") {
  if (val === null || val === undefined || val === "" || String(val).toLowerCase() === "null" || String(val).toLowerCase() === "undefined" || String(val) === "NaN") {
    return defaultText;
  }
  return String(val);
}

function formatTimestamp(tsStr) {
  if (!tsStr) return "Not Available";
  const d = new Date(tsStr);
  if (isNaN(d.getTime())) return String(tsStr);
  
  const day = d.getDate();
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const month = months[d.getMonth()];
  const year = d.getFullYear();
  
  let hours = d.getHours();
  const minutes = d.getMinutes().toString().padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12;
  hours = hours ? hours : 12;
  const formattedHours = hours.toString().padStart(2, '0');
  
  return `${day} ${month} ${year}, ${formattedHours}:${minutes} ${ampm}`;
}

function resetInspectionState() {
  state.currentInspectionResult = null;
  state.capturedImageBase64 = null;
  state.ocrExtractedData = null;
  state.inspectionSavedForCurrentRun = false;

  const prodSelect = document.getElementById("inspect-expected-product");
  if (prodSelect) {
    prodSelect.value = "Not Specified";
    toggleMilkParamsDrawer("Not Specified");
  }

  if (window.cameraHandler) {
    window.cameraHandler.resetViewport();
  }

  const fileInput = document.getElementById("image-file-input");
  if (fileInput) fileInput.value = "";

  const ocrFileInput = document.getElementById("ocr-file-input");
  if (ocrFileInput) ocrFileInput.value = "";

  const livePanel = document.getElementById("live-nutrition-panel");
  if (livePanel) livePanel.style.display = "none";

  const actionsContainer = document.getElementById("result-actions-container");
  if (actionsContainer) actionsContainer.style.display = "none";

  const warnBanner = document.getElementById("low-confidence-warning");
  if (warnBanner) warnBanner.style.display = "none";

  const varSelectContainer = document.getElementById("variant-select-container");
  if (varSelectContainer) varSelectContainer.style.display = "none";

  const card = document.getElementById("decision-result-card");
  if (card) card.className = "decision-card IDLE";

  const title = document.getElementById("decision-status-title");
  if (title) {
    title.innerText = "Waiting for image";
    title.style.color = "var(--text-muted)";
  }

  const pName = document.getElementById("badge-product-name");
  if (pName) pName.innerText = "Pending...";

  const pConf = document.getElementById("badge-product-conf");
  if (pConf) pConf.innerText = "--%";

  const cName = document.getElementById("badge-condition-name");
  if (cName) cName.innerText = "Pending...";

  const cConf = document.getElementById("badge-condition-conf");
  if (cConf) cConf.innerText = "--%";

  const actionDiv = document.getElementById("decision-recommended-action");
  if (actionDiv) actionDiv.innerText = "Capture or upload an image to begin inspection.";

  const tsSpan = document.getElementById("summary-card-timestamp");
  if (tsSpan) tsSpan.innerText = "--:--";

  const btnStartCam = document.getElementById("btn-start-cam");
  const btnUploadFront = document.getElementById("btn-upload-front");
  const btnStopCam = document.getElementById("btn-stop-cam");
  const btnCapture = document.getElementById("btn-capture-frame");

  if (btnStartCam) btnStartCam.style.display = "inline-flex";
  if (btnUploadFront) btnUploadFront.style.display = "inline-flex";
  if (btnStopCam) btnStopCam.style.display = "none";
  if (btnCapture) btnCapture.style.display = "none";
}

function setImageReadyState(b64) {
  state.capturedImageBase64 = b64;
  state.currentInspectionResult = null;
  state.ocrExtractedData = null;

  const dropZone = document.getElementById("drag-drop-zone");
  if (dropZone) dropZone.style.display = "none";

  const btnStartCam = document.getElementById("btn-start-cam");
  const btnUploadFront = document.getElementById("btn-upload-front");
  const btnStopCam = document.getElementById("btn-stop-cam");
  const btnCapture = document.getElementById("btn-capture-frame");

  if (btnStartCam) btnStartCam.style.display = "none";
  if (btnUploadFront) btnUploadFront.style.display = "none";
  if (btnStopCam) {
    btnStopCam.style.display = "inline-flex";
    btnStopCam.innerHTML = `<i class="ph ph-arrow-counter-clockwise"></i> ↻ RETAKE`;
  }
  if (btnCapture) {
    btnCapture.style.display = "inline-flex";
    btnCapture.innerHTML = `<i class="ph ph-aperture"></i> ⚡ INSPECT`;
  }

  const livePanel = document.getElementById("live-nutrition-panel");
  if (livePanel) livePanel.style.display = "none";

  const actionsContainer = document.getElementById("result-actions-container");
  if (actionsContainer) actionsContainer.style.display = "none";

  const warnBanner = document.getElementById("low-confidence-warning");
  if (warnBanner) warnBanner.style.display = "none";

  const card = document.getElementById("decision-result-card");
  if (card) card.className = "decision-card IDLE";

  const title = document.getElementById("decision-status-title");
  if (title) {
    title.innerText = "Image Ready";
    title.style.color = "var(--primary)";
  }

  const pName = document.getElementById("badge-product-name");
  if (pName) pName.innerText = "Pending...";

  const pConf = document.getElementById("badge-product-conf");
  if (pConf) pConf.innerText = "--%";

  const cName = document.getElementById("badge-condition-name");
  if (cName) cName.innerText = "Pending...";

  const cConf = document.getElementById("badge-condition-conf");
  if (cConf) cConf.innerText = "--%";

  const actionDiv = document.getElementById("decision-recommended-action");
  if (actionDiv) actionDiv.innerText = "Image loaded and ready. Click ⚡ INSPECT to run AI inspection.";
}

async function handleInspectButtonClick() {
  const imageElement = document.getElementById("image-preview");
  let b64 = state.capturedImageBase64;
  
  if (!b64 && window.cameraHandler && window.cameraHandler.currentMode === "camera") {
    b64 = window.cameraHandler.captureFrame();
    state.capturedImageBase64 = b64;
  }

  if (!b64 && imageElement && imageElement.src && imageElement.src.startsWith("data:image")) {
    b64 = imageElement.src;
    state.capturedImageBase64 = b64;
  }

  if (!b64) {
    showToast("warning", "Please capture or upload a product image first.");
    return;
  }

  const card = document.getElementById("decision-result-card");
  if (card) card.className = "decision-card IDLE";
  
  const title = document.getElementById("decision-status-title");
  if (title) {
    title.innerText = "🔄 ANALYZING...";
    title.style.color = "var(--accent)";
  }
  
  const actionDiv = document.getElementById("decision-recommended-action");
  if (actionDiv) actionDiv.innerText = "Running AI product and packaging condition classifiers...";

  await runFullInspectionPipeline(b64);
}

function renderNutritionTable(profileOrNutritionData) {
  const livePanel = document.getElementById("live-nutrition-panel");
  const missingNotice = document.getElementById("live-nutrition-missing-notice");
  const tableContainer = document.getElementById("live-nutrition-table-container");
  const liveTbody = document.getElementById("live-nutrition-table-body");
  const liveBasis = document.getElementById("live-nutrition-basis");
  const liveSource = document.getElementById("live-nutrition-source");

  const detectedProduct = document.getElementById("badge-product-name")?.innerText || "";
  const isSupportedFood = detectedProduct.toLowerCase().includes("chips") || detectedProduct.toLowerCase().includes("milk");

  if (!profileOrNutritionData || !isSupportedFood) {
    if (livePanel) {
      if (detectedProduct.toLowerCase().includes("other food")) {
        livePanel.style.display = "block";
        if (missingNotice) missingNotice.style.display = "block";
        if (tableContainer) tableContainer.style.display = "none";
      } else {
        livePanel.style.display = "none";
      }
    }
    return;
  }

  const profile = state.currentProductProfile || {};
  const nutritionTable = profileOrNutritionData.nutrition_table || profile.nutrition_table || profileOrNutritionData.nutrition_per_100g || profileOrNutritionData;
  const perServingTable = profileOrNutritionData.per_serving_table || profile.per_serving_table || {};
  const perPackTable = profileOrNutritionData.per_pack_table || profile.per_pack_table || {};
  const basis = profileOrNutritionData.nutrition_basis || profile.nutrition_basis || profile.basis || (detectedProduct.toLowerCase().includes("milk") ? "Per 100 ml" : "Per 100 g");
  const mrp = profileOrNutritionData.mrp || profile.mrp || "₹20";
  const netWeight = profileOrNutritionData.net_weight || profile.net_weight || "50 g";
  const servingSize = profileOrNutritionData.serving_size || profile.serving_size || "20 g";
  const source = profileOrNutritionData.nutrition_source || profile.nutrition_source || profile.source || "Verified Product Label";

  const keys = Object.keys(nutritionTable).filter(k => !["basis", "source", "category", "mrp", "net_weight", "serving_size", "nutrition_table", "per_serving_table", "per_pack_table"].includes(k));

  if (keys.length === 0) {
    if (livePanel) livePanel.style.display = "block";
    if (missingNotice) missingNotice.style.display = "block";
    if (tableContainer) tableContainer.style.display = "none";
    return;
  }

  if (livePanel) livePanel.style.display = "block";
  if (missingNotice) missingNotice.style.display = "none";
  if (tableContainer) tableContainer.style.display = "block";

  if (liveBasis) liveBasis.innerText = safeVal(basis, "Per 100 g").replace(/^Basis:\s*/i, "");
  if (liveSource) liveSource.innerText = safeVal(source, "Verified Product Label");

  if (liveTbody) {
    liveTbody.innerHTML = keys.map(key => {
      const labelVal = safeVal(nutritionTable[key]);
      return `
        <tr>
          <td style="text-transform: capitalize; font-weight: 500;">${key.replace(/_/g, " ")}</td>
          <td><span style="color: var(--accent); font-weight:600;">${labelVal}</span></td>
        </tr>
      `;
    }).join("");
  }

  // Update Modal Metadata Elements
  const mMrp = document.getElementById("modal-product-mrp");
  const mNet = document.getElementById("modal-product-net-weight");
  const mServing = document.getElementById("modal-product-serving-size");
  const mSource = document.getElementById("nutrition-source-val");

  if (mMrp) mMrp.innerText = safeVal(mrp, "₹20");
  if (mNet) mNet.innerText = safeVal(netWeight, "50 g");
  if (mServing) mServing.innerText = safeVal(servingSize, "20 g");
  if (mSource) mSource.innerText = safeVal(source, "Verified Product Label");

  const basisBadge = document.getElementById("nutrition-basis-badge");
  if (basisBadge) {
    basisBadge.innerText = `Basis: ${safeVal(basis, "Per 100 g")}`;
  }

  const tbody = document.getElementById("nutrition-table-body");
  if (tbody) {
    tbody.innerHTML = keys.map(key => {
      const labelVal = safeVal(nutritionTable[key]);
      const servingVal = safeVal(perServingTable[key], "--");
      const packVal = safeVal(perPackTable[key], "--");
      return `
        <tr>
          <td style="text-transform: capitalize; font-weight: 500;">${key.replace(/_/g, " ")}</td>
          <td><span style="color: var(--accent); font-weight:600;">${labelVal}</span></td>
          <td><span style="color: var(--pass-color); font-weight:600;">${servingVal}</span> <span style="font-size:0.65rem; color:var(--text-dim);">(Calculated)</span></td>
          <td><span style="color: var(--primary); font-weight:600;">${packVal}</span> <span style="font-size:0.65rem; color:var(--text-dim);">(Calculated)</span></td>
        </tr>
      `;
    }).join("");
  }
}

/* Save Inspection */
async function saveCurrentInspection() {
  if (!state.currentInspectionResult) {
    showToast("warning", "⚠️ Please capture or upload an image to analyze first.");
    return;
  }

  if (state.inspectionSavedForCurrentRun) {
    showToast("info", "ℹ️ Inspection record has already been saved to database.");
    return;
  }

  const btnSave = document.getElementById("btn-save-inspection");
  if (btnSave) btnSave.disabled = true;

  const expProd = state.currentInspectionResult?.expected_product || "Not Specified";
  const isGen = expProd === "Not Specified" || !expProd;
  const payload = {
    ...state.currentInspectionResult,
    batch_id: isGen ? null : state.activeBatch?.id,
    image_base64: state.capturedImageBase64
  };

  try {
    const res = await fetch(`${API_BASE}/api/inspect/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      throw new Error(`HTTP_${res.status}`);
    }

    const saved = await res.json();
    state.lastSavedInspectionId = saved.id;
    state.inspectionSavedForCurrentRun = true;
    showToast("success", `✅ Inspection logged successfully! Status: ${saved.final_status}`);
    await refreshDashboard();
  } catch (err) {
    console.error("Error saving inspection:", err);
    showToast("error", "❌ SAVE FAILED: Inspection could not be saved. Please try again.");
  } finally {
    if (btnSave) btnSave.disabled = false;
  }
}

/* Dashboard UI Render Helpers */
function renderRecentActivity(list) {
  const tbody = document.getElementById("table-recent-inspections");
  if (!tbody) return;
  if (!list.length) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-dim);">No inspections logged yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(item => {
    const isDemo = item.data_source === 'DEMO';
    const sourceBadge = isDemo
      ? `<span style="font-size:0.7rem; padding: 2px 6px; border-radius: 4px; background: rgba(255,193,7,0.15); color: #ffc107; font-weight:600;">DEMO</span>`
      : `<span style="font-size:0.7rem; padding: 2px 6px; border-radius: 4px; background: rgba(33,150,243,0.15); color: #2196f3; font-weight:600;">LIVE</span>`;
    return `
    <tr>
      <td>#${item.id}</td>
      <td>${item.batch_number}</td>
      <td>${item.product}</td>
      <td><span class="status-pill ${item.status}">${item.status}</span></td>
      <td>${sourceBadge}</td>
      <td>${formatTimestamp(item.created_at)}</td>
    </tr>
  `;
  }).join("");
}

function renderAlertsFeed(alerts) {
  const feed = document.getElementById("alerts-feed-container");
  if (!feed) return;
  if (!alerts || !alerts.length) {
    feed.innerHTML = `<div style="font-size:0.8rem; color:var(--text-dim); padding:1rem; text-align:center;">All systems normal. No active HOLD/REJECT alerts.</div>`;
    return;
  }

  feed.innerHTML = alerts.map(a => `
    <div style="background: rgba(255,255,255,0.03); border-left: 3px solid var(--${a.status.toLowerCase()}-color); padding: 0.75rem; border-radius: 6px; margin-bottom: 0.6rem;">
      <div style="display:flex; justify-content:space-between; font-size:0.75rem;">
        <span class="status-pill ${a.status}">${a.status}</span>
        <span style="color:var(--text-dim);">${formatTimestamp(a.created_at)}</span>
      </div>
      <div style="font-weight:600; font-size:0.85rem; margin-top:0.3rem;">${a.product_name} (${a.batch_number || 'Batch'})</div>
      <div style="font-size:0.78rem; color:var(--text-muted);">${a.reason}</div>
      <div style="font-size:0.72rem; color:var(--accent); margin-top:0.25rem;">Action: ${a.recommended_action || 'Inspect'}</div>
    </div>
  `).join("");
}

function renderStockAtRiskTable(list) {
  const tbody = document.getElementById("table-stock-at-risk");
  if (!tbody) return;
  if (!list || !list.length) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--text-dim);">No stock currently at risk. All active batches normal.</td></tr>`;
    return;
  }

  // Sort by urgency: EXPIRED first, then earliest EXPIRING_SOON
  const sortedList = [...list].sort((a, b) => {
    if (a.expiry_status === "EXPIRED" && b.expiry_status !== "EXPIRED") return -1;
    if (a.expiry_status !== "EXPIRED" && b.expiry_status === "EXPIRED") return 1;
    return (a.days_remaining ?? 9999) - (b.days_remaining ?? 9999);
  });

  tbody.innerHTML = sortedList.map(item => {
    const isExpired = item.expiry_status === "EXPIRED";
    const statusPill = isExpired
      ? `<span class="status-pill REJECT">EXPIRED</span>`
      : `<span class="status-pill WARNING">EXPIRING SOON</span>`;

    return `
      <tr>
        <td style="font-weight:600;">${item.product_name}</td>
        <td>${item.batch_number}</td>
        <td>${item.expiry_date || 'N/A'}</td>
        <td style="color:${isExpired ? 'var(--reject-color)' : 'var(--warn-color)'}; font-weight:600;">${item.days_remaining_text}</td>
        <td>${statusPill}</td>
      </tr>
    `;
  }).join("");
}

/* Batch Management */
function renderBatchesTable(batches) {
  const tbody = document.getElementById("table-batches-body");
  if (!tbody) return;

  if (!batches || !batches.length) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--text-dim);">No production batches registered.</td></tr>`;
    return;
  }

  tbody.innerHTML = batches.map(b => {
    const statusClass = b.expiry_status === 'NORMAL' ? 'PASS' : (b.expiry_status === 'EXPIRING_SOON' ? 'WARNING' : (b.expiry_status === 'EXPIRED' ? 'REJECT' : 'HOLD'));
    const expiryBadge = `<span class="status-pill ${statusClass}">${b.expiry_status || 'UNKNOWN'}</span>`;
    const daysText = b.days_remaining_text || 'Unknown expiry';

    const isActive = b.status === 'ACTIVE';
    const actionCell = isActive
      ? `<div style="display:flex; gap:0.3rem; align-items:center;">
           <span style="color:var(--pass-color); font-weight:700; font-size:0.75rem;">● ACTIVE</span>
           <button class="btn" style="padding:0.2rem 0.5rem; font-size:0.72rem; border:1px solid var(--accent); color:var(--accent);" onclick="viewBatchDetails(${b.id})">Details</button>
         </div>`
      : `<div style="display:flex; gap:0.3rem; align-items:center;">
           <button class="btn" style="padding:0.2rem 0.5rem; font-size:0.72rem;" onclick="activateBatch(${b.id})">ACTIVATE</button>
           <button class="btn" style="padding:0.2rem 0.5rem; font-size:0.72rem; border:1px solid var(--accent); color:var(--accent);" onclick="viewBatchDetails(${b.id})">Details</button>
         </div>`;

    return `
      <tr class="${isActive ? 'row-active-batch' : ''}">
        <td style="font-weight:600;">${b.batch_number}</td>
        <td>${b.product_name}</td>
        <td>${b.mfg_date || 'N/A'}</td>
        <td>${b.exp_date || 'N/A'}</td>
        <td><span style="font-weight:600; font-size:0.8rem;">${daysText}</span></td>
        <td>${expiryBadge}</td>
        <td>${b.inspection_count}</td>
        <td>${actionCell}</td>
      </tr>
    `;
  }).join("");
}

function viewBatchDetails(batchId) {
  const batch = state.batches.find(b => b.id === batchId);
  if (!batch) return;

  const modal = document.getElementById("batch-details-modal");
  if (!modal) return;

  document.getElementById("bmodal-product-name").innerText = batch.product_name || "Unknown";
  document.getElementById("bmodal-batch-number").innerText = batch.batch_number || "--";
  document.getElementById("bmodal-mfg-date").innerText = batch.mfg_date || "N/A";
  document.getElementById("bmodal-exp-date").innerText = batch.exp_date || "N/A";
  document.getElementById("bmodal-rule-type").innerText = batch.expiry_rule_type || "EXPLICIT_DATE";
  document.getElementById("bmodal-days-remaining").innerText = batch.days_remaining_text || "Unknown";
  document.getElementById("bmodal-expiry-status").innerText = batch.expiry_status || "UNKNOWN";
  document.getElementById("bmodal-inspection-count").innerText = batch.inspection_count || 0;

  document.getElementById("btimeline-mfg").innerText = batch.mfg_date || "N/A";
  document.getElementById("btimeline-exp").innerText = batch.exp_date || "N/A";

  const dotNorm = document.getElementById("btimeline-dot-normal");
  const dotSoon = document.getElementById("btimeline-dot-soon");
  const dotExp = document.getElementById("btimeline-dot-expired");

  if (dotNorm) dotNorm.style.opacity = batch.expiry_status === "NORMAL" ? "1" : "0.3";
  if (dotSoon) dotSoon.style.opacity = batch.expiry_status === "EXPIRING_SOON" ? "1" : "0.3";
  if (dotExp) dotExp.style.opacity = batch.expiry_status === "EXPIRED" ? "1" : "0.3";

  modal.style.display = "flex";
}

async function activateBatch(batchId) {
  try {
    const res = await fetch(`${API_BASE}/api/batches/${batchId}/activate`, { method: "PUT" });
    if (res.ok) {
      showToast("success", "✅ Batch activated!");
      await loadBatches();
      await refreshDashboard();
    } else {
      showToast("error", "❌ Failed to activate batch.");
    }
  } catch (err) {
    console.error("Failed to activate batch:", err);
    showToast("error", "❌ Failed to activate batch.");
  }
}


async function createNewBatch(e) {
  e.preventDefault();
  const batch_number = document.getElementById("batch-number-input").value;
  const product_id = parseInt(document.getElementById("batch-product-select").value);
  const expiry_rule_type = document.getElementById("batch-rule-type-select")?.value || "EXPLICIT_DATE";
  const mfg_date = document.getElementById("batch-mfg-input").value;
  const exp_date = document.getElementById("batch-exp-input").value;
  const expiry_duration_months = parseInt(document.getElementById("batch-duration-input")?.value) || 4;

  const payload = {
    batch_number,
    product_id,
    mfg_date,
    exp_date,
    manufacture_date: mfg_date,
    expiry_date: exp_date,
    expiry_rule_type,
    expiry_duration_months,
    expiry_source: expiry_rule_type === "MONTHS_FROM_MANUFACTURE" ? "PRODUCT_SHELF_LIFE_RULE" : "USER_MANUAL"
  };

  try {
    const res = await fetch(`${API_BASE}/api/batches`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      showToast("success", "✅ New batch created & set as active!");
      document.getElementById("create-batch-form").reset();
      await loadBatches();
      await refreshDashboard();
    } else {
      const err = await res.json();
      showToast("error", `❌ Error: ${err.detail}`);
    }
  } catch (err) {
    console.error("Failed to create batch:", err);
    showToast("error", "❌ Failed to create batch.");
  }
}


/* History */
async function loadInspectionHistory() {
  try {
    const res = await fetch(`${API_BASE}/api/inspect/history`);
    const history = await res.json();
    const tbody = document.getElementById("table-history-body");
    if (!tbody) return;

    if (!history.length) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-dim);">No inspection records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = history.map(h => `
      <tr>
        <td>#${h.id}</td>
        <td>${h.batch_number}</td>
        <td>${h.detected_product} (${(h.product_confidence * 100).toFixed(0)}%)</td>
        <td>${h.packaging_condition}</td>
        <td><span class="status-pill ${h.final_status}">${h.final_status}</span></td>
        <td>${formatTimestamp(h.created_at)}</td>
        <td>
          <button class="btn" style="padding:0.25rem 0.6rem; font-size:0.75rem;" onclick="viewPrintableReport(${h.id})">Report</button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to load history:", err);
  }
}

async function viewPrintableReport(inspectionId) {
  try {
    const res = await fetch(`${API_BASE}/api/inspect/${inspectionId}`);
    const data = await res.json();

    const modal = document.getElementById("report-modal");
    const content = document.getElementById("report-modal-content");

    content.innerHTML = `
      <div style="border-bottom:1px solid var(--border-color); padding-bottom:1rem; margin-bottom:1rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <h2 style="font-family:var(--font-heading);">INSPECTION AUDIT REPORT #${data.id}</h2>
          <span class="status-pill ${data.final_status}" style="font-size:1rem; padding:0.4rem 1rem;">${data.final_status}</span>
        </div>
        <p style="font-size:0.8rem; color:var(--text-dim); margin-top:0.25rem;">Timestamp: ${formatTimestamp(data.created_at)} | Batch: ${data.batch_number}</p>
      </div>

      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:1rem; margin-bottom:1rem;">
        <div style="background:rgba(255,255,255,0.03); padding:0.85rem; border-radius:8px;">
          <h4 style="font-size:0.85rem; color:var(--accent);">AI Classification Details</h4>
          <p style="font-size:0.8rem; margin-top:0.4rem;">Expected Product: <strong>${data.expected_product}</strong></p>
          <p style="font-size:0.8rem;">Detected Product: <strong>${data.detected_product}</strong> (${(data.product_confidence * 100).toFixed(1)}%)</p>
          <p style="font-size:0.8rem;">Package Condition: <strong>${data.packaging_condition}</strong> (${(data.condition_confidence * 100).toFixed(1)}%)</p>
        </div>

        <div style="background:rgba(255,255,255,0.03); padding:0.85rem; border-radius:8px;">
          <h4 style="font-size:0.85rem; color:var(--accent);">Label OCR Information</h4>
          <p style="font-size:0.8rem; margin-top:0.4rem;">Batch No: <strong>${data.ocr_extracted?.batch_number || 'N/A'}</strong></p>
          <p style="font-size:0.8rem;">Expiry Date: <strong>${data.ocr_extracted?.exp_date || 'N/A'}</strong></p>
          <p style="font-size:0.8rem;">Net Weight: <strong>${data.ocr_extracted?.net_weight || 'N/A'}</strong></p>
          <p style="font-size:0.8rem;">Serving Size: <strong>${data.ocr_extracted?.serving_size || 'N/A'}</strong></p>
        </div>
      </div>

      ${data.milk_lab_params ? `
        <div style="background:rgba(255,255,255,0.03); padding:0.85rem; border-radius:8px; margin-bottom:1rem;">
          <h4 style="font-size:0.85rem; color:var(--accent);">Milk Quality Parameters</h4>
          <div style="display:flex; gap:1.5rem; font-size:0.8rem; margin-top:0.4rem;">
            <span>Fat: <strong>${data.milk_lab_params.fat}%</strong></span>
            <span>SNF: <strong>${data.milk_lab_params.snf}%</strong></span>
            <span>pH: <strong>${data.milk_lab_params.ph}</strong></span>
            <span>Temp: <strong>${data.milk_lab_params.temperature}°C</strong></span>
          </div>
        </div>
      ` : ''}

      <div style="background:rgba(255,255,255,0.03); padding:0.85rem; border-radius:8px; margin-bottom:1rem;">
        <h4 style="font-size:0.85rem; color:var(--text-muted);">Evaluation Rationale & Reasons</h4>
        <ul style="font-size:0.8rem; padding-left:1.2rem; margin-top:0.4rem;">
          ${data.status_reasons.map(r => `<li>${r}</li>`).join("")}
        </ul>
      </div>

      ${data.human_review_status ? `
        <div style="background:rgba(245, 158, 11, 0.1); border:1px solid var(--warn-color); padding:0.85rem; border-radius:8px; margin-bottom:1rem;">
          <h4 style="font-size:0.85rem; color:var(--warn-color);">Human Operator Review Record</h4>
          <p style="font-size:0.8rem; margin-top:0.4rem;">Decision: <strong>${data.human_review_status}</strong></p>
          <p style="font-size:0.8rem;">Reviewer: <strong>${data.human_reviewer}</strong></p>
          <p style="font-size:0.8rem;">Comment: <em>${data.human_comment || 'No comment'}</em></p>
        </div>
      ` : ''}

      <div style="font-size:0.7rem; color:var(--text-dim); margin-bottom:1rem; font-style:italic;">
        "Nutrition values are checked against configured reference values and product records. This does not independently certify food safety."
      </div>

      <div style="display:flex; justify-content:flex-end; gap:0.75rem;">
        <button class="btn btn-primary" onclick="window.print()"><i class="ph ph-printer"></i> Print / Save PDF</button>
        <button class="btn" onclick="document.getElementById('report-modal').classList.remove('active')">Close</button>
      </div>
    `;

    modal.classList.add("active");
  } catch (err) {
    console.error("Error displaying report:", err);
  }
}

