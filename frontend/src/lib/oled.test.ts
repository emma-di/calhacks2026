import test from "node:test";
import assert from "node:assert/strict";
import fixtures from "../../../hardware/render-fixtures.json";
import { hex, render } from "./oled.ts";

test("browser glasses preview is byte-identical to the Python SSD1306 renderer", () => {
  for (const f of fixtures) {
    const label = `${f.icon_id} tier ${f.effective_tier} labels ${f.show_labels} ${(f as { direction?: string }).direction ?? ""}`;
    const cue = f.effective_tier ? f : null;
    assert.equal(hex(render(cue, f.show_labels)), f.frame, label);
  }
});
