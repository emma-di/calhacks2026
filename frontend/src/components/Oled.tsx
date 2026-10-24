import { useEffect, useRef } from "react";
import type { SoundEvent } from "../lib/events";
import type { Appearance } from "../lib/appearance";
import { SoundIcon } from "./Cue";
import { cuePresentation } from "../lib/presentation";

// Same semantic icon and display policy as Cue; rasterized to exactly 128x64 one-bit pixels.
export default function Oled({
  event,
  appearance,
  direction,
}: {
  event: SoundEvent | null;
  appearance: Appearance;
  direction: Appearance["direction"];
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const iconSource = useRef<SVGSVGElement>(null);
  const presentation = cuePresentation(event, appearance, direction);
  useEffect(() => {
    const ctx = canvas.current?.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;
    let cancelled = false;
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, 128, 64);
    const finish = () => {
      const pixels = ctx.getImageData(0, 0, 128, 64);
      for (let i = 0; i < pixels.data.length; i += 4) {
        const value = pixels.data[i] >= 128 ? 255 : 0;
        pixels.data[i] = value;
        pixels.data[i + 1] = value;
        pixels.data[i + 2] = value;
        pixels.data[i + 3] = 255;
      }
      ctx.putImageData(pixels, 0, 0);
    };
    if (!presentation) {
      ctx.fillStyle = "#fff";
      ctx.font = "7px monospace";
      ctx.textAlign = "center";
      ctx.fillText("No active alerts", 64, 36);
      finish();
      return;
    }
    const iconSize = presentation.tier === 1 ? 14 : 18;
    ctx.font = "8px monospace";
    const label = presentation.label;
    const labelWidth = label ? Math.min(82, ctx.measureText(label).width) : 0;
    const width = label
      ? Math.min(120, iconSize + labelWidth + 15)
      : iconSize + 12;
    const height = presentation.tier === 4 ? 34 : iconSize + 12;
    let x = (128 - width) / 2,
      y = 64 * 0.76 - height / 2;
    if (presentation.direction === "left") {
      x = 4;
      y = (64 - height) / 2;
    }
    if (presentation.direction === "right") {
      x = 124 - width;
      y = (64 - height) / 2;
    }
    if (presentation.direction === "front") {
      x = (128 - width) / 2;
      y = 4;
    }
    if (presentation.direction === "behind") {
      x = (128 - width) / 2;
      y = 60 - height;
    }
    x = Math.round(x);
    y = Math.max(2, Math.round(y));
    const draw = (image?: HTMLImageElement) => {
      if (cancelled) return;
      ctx.strokeStyle = "#fff";
      ctx.fillStyle = "#fff";
      ctx.lineWidth = presentation.tier === 3 ? 2 : 1;
      ctx.beginPath();
      if (label) ctx.roundRect(x + 0.5, y + 0.5, width - 1, height - 1, 4);
      else
        ctx.ellipse(
          x + width / 2,
          y + height / 2,
          (width - 1) / 2,
          (height - 1) / 2,
          0,
          0,
          Math.PI * 2,
        );
      ctx.stroke();
      if (presentation.tier === 4)
        ctx.strokeRect(x + 2.5, y + 2.5, width - 5, height - 5);
      if (image)
        ctx.drawImage(
          image,
          x + 6,
          y + (height - iconSize) / 2,
          iconSize,
          iconSize,
        );
      if (label) {
        ctx.textAlign = "left";
        ctx.font = "8px monospace";
        ctx.fillText(label, x + iconSize + 10, y + height / 2 + 3, labelWidth);
      }
      finish();
    };
    if (!iconSource.current) {
      draw();
      return;
    }
    const image = new Image();
    image.onload = () => draw(image);
    image.onerror = () => draw();
    image.src =
      "data:image/svg+xml;charset=utf-8," +
      encodeURIComponent(
        new XMLSerializer().serializeToString(iconSource.current),
      );
    return () => {
      cancelled = true;
    };
  }, [event, appearance, direction]);
  return (
    <>
      <span hidden aria-hidden="true">
        {presentation && (
          <svg
            ref={iconSource}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            style={{ color: "#fff" }}
          >
            <SoundIcon type={presentation.icon} size={24} />
          </svg>
        )}
      </span>
      <canvas
        ref={canvas}
        width={128}
        height={64}
        className="oled-bitmap"
        role="img"
        aria-label={`128 by 64 monochrome preview: ${presentation?.description ?? "no active alerts"}${presentation && direction !== "unknown" ? `, simulated ${direction}` : ""}`}
      />
    </>
  );
}
