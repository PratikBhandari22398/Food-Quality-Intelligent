/**
 * AI Classifier Service - Centralized Google Teachable Machine Dual Model Engine
 */

window.AI_CONFIG = {
  MODEL1_PRODUCT_URL: "/static/models/model1-product",
  MODEL2_PACKAGING_URL: "/static/models/model2-packaging",
  CONFIDENCE_THRESHOLD: 0.65 // Configurable prototype confidence threshold (65%)
};

class AIClassifier {
  constructor() {
    this.productModel = null;
    this.packagingModel = null;
    this.productModelLoaded = false;
    this.packagingModelLoaded = false;
    this.productModelError = null;
    this.packagingModelError = null;
    this.productLabels = [];
    this.packagingLabels = [];
  }

  async init(
    productModelUrl = window.AI_CONFIG.MODEL1_PRODUCT_URL,
    packagingModelUrl = window.AI_CONFIG.MODEL2_PACKAGING_URL
  ) {
    console.log("--- Initializing Real Teachable Machine Browser Models ---");

    // 1. Load Product Classification Model (Model 1)
    try {
      if (window.tmImage) {
        const startTime = performance.now();
        this.productModel = await tmImage.load(
          `${productModelUrl}/model.json`,
          `${productModelUrl}/metadata.json`
        );
        this.productModelLoaded = true;
        this.productModelError = null;
        this.productLabels = this.productModel.getClassLabels();
        const duration = (performance.now() - startTime).toFixed(2);
        console.log(`[MODEL 1 LOADED] Path: ${productModelUrl}/model.json | Duration: ${duration}ms | Labels:`, this.productLabels);
      } else {
        throw new Error("Teachable Machine tmImage JS library unavailable.");
      }
    } catch (e) {
      this.productModelLoaded = false;
      this.productModelError = "Product AI model unavailable";
      console.error("[MODEL 1 LOAD ERROR] Path:", productModelUrl, e);
    }

    // 2. Load Packaging Condition Model (Model 2)
    try {
      if (window.tmImage) {
        const startTime = performance.now();
        this.packagingModel = await tmImage.load(
          `${packagingModelUrl}/model.json`,
          `${packagingModelUrl}/metadata.json`
        );
        this.packagingModelLoaded = true;
        this.packagingModelError = null;
        this.packagingLabels = this.packagingModel.getClassLabels();
        const duration = (performance.now() - startTime).toFixed(2);
        console.log(`[MODEL 2 LOADED] Path: ${packagingModelUrl}/model.json | Duration: ${duration}ms | Labels:`, this.packagingLabels);
      } else {
        throw new Error("Teachable Machine tmImage JS library unavailable.");
      }
    } catch (e) {
      this.packagingModelLoaded = false;
      this.packagingModelError = "Packaging AI model unavailable";
      console.error("[MODEL 2 LOAD ERROR] Path:", packagingModelUrl, e);
    }

    // Update Model Status Indicators in UI
    this.updateModelStatusUI();

    return {
      productLoaded: this.productModelLoaded,
      packagingLoaded: this.packagingModelLoaded
    };
  }

  updateModelStatusUI() {
    const pStatusEl = document.getElementById("status-model1-product");
    const kStatusEl = document.getElementById("status-model2-packaging");

    if (pStatusEl) {
      if (this.productModelLoaded) {
        pStatusEl.innerHTML = `<span style="color: var(--pass-color); font-weight: 600;">● Loaded</span>`;
      } else {
        pStatusEl.innerHTML = `<span style="color: var(--reject-color); font-weight: 600;">● Error</span>`;
      }
    }

    if (kStatusEl) {
      if (this.packagingModelLoaded) {
        kStatusEl.innerHTML = `<span style="color: var(--pass-color); font-weight: 600;">● Loaded</span>`;
      } else {
        kStatusEl.innerHTML = `<span style="color: var(--reject-color); font-weight: 600;">● Error</span>`;
      }
    }
  }

  async predict(imageElement) {
    const startTime = performance.now();

    // Image Input Validation (Requirement 13)
    if (!imageElement || (!imageElement.width && !imageElement.videoWidth && !imageElement.naturalWidth)) {
      throw new Error("Invalid image input provided for prediction.");
    }

    // Verify Model Availability (Requirement 13 & 15)
    if (!this.productModelLoaded || !this.productModel) {
      throw new Error(this.productModelError || "Product AI model unavailable");
    }
    if (!this.packagingModelLoaded || !this.packagingModel) {
      throw new Error(this.packagingModelError || "Packaging AI model unavailable");
    }

    // Preprocessing & Inference (Requirement 10 & 11)
    // Model 1: Product Classification
    const productPredictions = await this.productModel.predict(imageElement);
    const topProduct = productPredictions.reduce((prev, curr) =>
      curr.probability > prev.probability ? curr : prev
    );

    // Model 2: Packaging Condition
    const packagingPredictions = await this.packagingModel.predict(imageElement);
    const topPackaging = packagingPredictions.reduce((prev, curr) =>
      curr.probability > prev.probability ? curr : prev
    );

    const duration = (performance.now() - startTime).toFixed(2);
    const threshold = window.AI_CONFIG.CONFIDENCE_THRESHOLD;

    const isLowConfidence =
      topProduct.probability < threshold || topPackaging.probability < threshold;

    // Requirement 14: Developer console logging
    console.log("--- Real AI Inference Results ---");
    console.log(`[MODEL 1 PREDICTION] Result: '${topProduct.className}' | Confidence: ${(topProduct.probability * 100).toFixed(1)}%`);
    console.log(`[MODEL 2 PREDICTION] Result: '${topPackaging.className}' | Confidence: ${(topPackaging.probability * 100).toFixed(1)}%`);
    console.log(`[INFERENCE DURATION] Total time: ${duration}ms | Threshold: ${threshold * 100}%`);

    return {
      detectedProduct: topProduct.className,
      productConfidence: topProduct.probability,
      productTopPredictions: productPredictions,
      packagingCondition: topPackaging.className,
      conditionConfidence: topPackaging.probability,
      packagingTopPredictions: packagingPredictions,
      durationMs: duration,
      isLowConfidence: isLowConfidence,
      lowConfidenceMessage: isLowConfidence
        ? "Prediction unclear — please capture another image."
        : null
    };
  }
}

window.aiClassifier = new AIClassifier();


