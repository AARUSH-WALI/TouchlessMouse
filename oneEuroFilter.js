/**
 * One-Euro Filter for responsive, jitter-free hand gesture & cursor tracking in EditoDoc.
 * Ported from ACM CHI 2012 research by Géry Casiez et al.
 * 
 * Dynamically balances jitter elimination (low speed) and latency reduction (high speed):
 * - Slow / still hand: Heavy smoothing removes camera sensor noise.
 * - Fast sweep: Cutoff frequency rises adaptively so the cursor does not lag behind.
 */

export class OneEuroFilter {
  constructor(minCutoff = 1.0, beta = 0.007, dCutoff = 1.0) {
    this.minCutoff = minCutoff;
    this.beta = beta;
    this.dCutoff = dCutoff;
    this.xPrev = null;
    this.dxPrev = 0.0;
    this.tPrev = null;
  }

  _smoothingFactor(te, cutoff) {
    const r = 2.0 * Math.PI * cutoff * te;
    return r / (r + 1.0);
  }

  filter(x, timestamp = performance.now() / 1000) {
    if (this.tPrev === null || this.xPrev === null) {
      this.xPrev = x;
      this.dxPrev = 0.0;
      this.tPrev = timestamp;
      return x;
    }

    const te = timestamp - this.tPrev;
    if (te <= 0.0) return this.xPrev;

    // 1. Filter derivative dx
    const ad = this._smoothingFactor(te, this.dCutoff);
    const dx = (x - this.xPrev) / te;
    const dxHat = ad * dx + (1.0 - ad) * this.dxPrev;

    // 2. Adaptive cutoff frequency
    const cutoff = this.minCutoff + this.beta * Math.abs(dxHat);

    // 3. Filter position x
    const a = this._smoothingFactor(te, cutoff);
    const xHat = a * x + (1.0 - a) * this.xPrev;

    this.xPrev = xHat;
    this.dxPrev = dxHat;
    this.tPrev = timestamp;
    return xHat;
  }

  reset() {
    this.xPrev = null;
    this.dxPrev = 0.0;
    this.tPrev = null;
  }
}

export class PointFilter2D {
  constructor(minCutoff = 1.0, beta = 0.007, dCutoff = 1.0) {
    this.filterX = new OneEuroFilter(minCutoff, beta, dCutoff);
    this.filterY = new OneEuroFilter(minCutoff, beta, dCutoff);
  }

  filter(x, y, timestamp = performance.now() / 1000) {
    return {
      x: this.filterX.filter(x, timestamp),
      y: this.filterY.filter(y, timestamp),
    };
  }

  reset() {
    this.filterX.reset();
    this.filterY.reset();
  }
}
