/**
 * Camera & Image Capture Handler
 */

class CameraHandler {
  constructor(videoElementId, canvasElementId, previewElementId) {
    this.video = document.getElementById(videoElementId);
    this.canvas = document.getElementById(canvasElementId);
    this.preview = document.getElementById(previewElementId);
    this.stream = null;
    this.currentMode = "upload"; // "camera" or "upload"
    this.capturedBase64 = null;
  }

  async startCamera() {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        this.stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "environment" }
        });
        if (this.video) {
          this.video.srcObject = this.stream;
          this.video.style.display = "block";
          if (this.preview) this.preview.style.display = "none";
          this.currentMode = "camera";
        }
        return true;
      }
    } catch (err) {
      console.error("Camera access error:", err);
      let msg = "Camera unavailable.";
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        msg = "Camera permission denied.";
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        msg = "Camera unavailable.";
      } else if (err.name === "NotReadableError" || err.name === "TrackStartError") {
        msg = "Camera is currently in use by another application.";
      }
      if (window.showToast) {
        window.showToast("error", msg);
      } else {
        alert(msg);
      }
      return false;
    }
  }

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    if (this.video) {
      this.video.style.display = "none";
    }
  }

  captureFrame() {
    if (this.currentMode === "camera" && this.video && this.canvas) {
      const context = this.canvas.getContext("2d");
      this.canvas.width = this.video.videoWidth || 640;
      this.canvas.height = this.video.videoHeight || 480;
      context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
      
      this.capturedBase64 = this.canvas.toDataURL("image/jpeg", 0.9);
      if (this.preview) {
        this.preview.src = this.capturedBase64;
        this.preview.style.display = "block";
      }
      return this.capturedBase64;
    }
    return this.capturedBase64;
  }

  loadImageFromFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        this.capturedBase64 = e.target.result;
        if (this.preview) {
          this.preview.src = this.capturedBase64;
          this.preview.style.display = "block";
        }
        if (this.video) this.video.style.display = "none";
        this.stopCamera();
        this.currentMode = "upload";
        resolve(this.capturedBase64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  resetViewport() {
    this.stopCamera();
    this.capturedBase64 = null;
    if (this.preview) {
      this.preview.src = "";
      this.preview.style.display = "none";
    }
    const dropZone = document.getElementById("drag-drop-zone");
    if (dropZone) dropZone.style.display = "flex";
  }
}

window.cameraHandler = new CameraHandler("webcam-video", "capture-canvas", "image-preview");
