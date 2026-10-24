// One deliberate hold produces one action. A held hand cannot clear the next queued cue.
export class GestureHold {
  private since: number | null = null;
  private latched = false;
  private firedAt = -Infinity;
  constructor(
    private holdMs = 330,
    private cooldownMs = 1500,
  ) {}
  update(thumb: boolean, now: number): boolean {
    if (!thumb) {
      this.since = null;
      this.latched = false;
      return false;
    }
    this.since ??= now;
    if (
      this.latched ||
      now - this.since < this.holdMs ||
      now - this.firedAt < this.cooldownMs
    )
      return false;
    this.latched = true;
    this.firedAt = now;
    return true;
  }
}
