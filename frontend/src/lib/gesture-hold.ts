// One deliberate hold, on one cue, produces one action; release before another dismissal.
export class GestureHold {
  private since: number | null = null;
  private latched = false;
  private firedAt = -Infinity;
  private releaseSince: number | null = null;
  private target: string | null = null;
  constructor(
    private holdMs = 330,
    private cooldownMs = 1500,
    private releaseMs = 0,
  ) {}
  get waitingForRelease() { return this.latched; }
  blockUntilRelease() { this.latched = true; this.since = null; this.releaseSince = null; }
  update(
    thumb: boolean,
    now: number,
    target: string | null = "unscoped",
  ): boolean {
    if (!thumb) {
      this.releaseSince ??= now;
      this.since = null;
      if (now - this.releaseSince >= this.releaseMs) {
        this.latched = false;
        this.target = null;
      }
      return false;
    }
    this.releaseSince = null;
    if (this.latched) return false;
    if (this.since === null) {
      this.since = now;
      this.target = target;
    }
    // A hand already up before an alert, or spanning a cue change, must be lowered first.
    if (target === null || this.target !== target) {
      this.latched = true;
      return false;
    }
    if (now - this.since < this.holdMs || now - this.firedAt < this.cooldownMs)
      return false;
    this.latched = true;
    this.firedAt = now;
    return true;
  }
}
