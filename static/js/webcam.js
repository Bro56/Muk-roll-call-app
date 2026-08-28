/**
 * Minimal webcam helper. Usage:
 *   const cam = new RollCallCamera(videoEl);
 *   await cam.start();
 *   const dataUrl = cam.captureFrame();   // 'data:image/jpeg;base64,...'
 *   cam.stop();
 */
class RollCallCamera {
  constructor(videoEl) {
    this.video = videoEl;
    this.stream = null;
  }

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      audio: false,
    });
    this.video.srcObject = this.stream;
    await this.video.play();
  }

  captureFrame(quality = 0.85) {
    const canvas = document.createElement("canvas");
    canvas.width = this.video.videoWidth || 640;
    canvas.height = this.video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(this.video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", quality);
  }

  stop() {
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
  }
}
