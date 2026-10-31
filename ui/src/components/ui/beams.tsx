import { useEffect, useRef } from "react";

interface BeamsProps {
  className?: string;
}

export function Beams({ className = "" }: BeamsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = container.clientWidth;
    const height = container.clientHeight;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const beams = Array.from({ length: 6 }, (_, i) => ({
      angle: (Math.PI * (i + 1)) / 7,
      speed: 0.004 + i * 0.0015,
      widthFactor: 0.006 + i * 0.002,
      hue: 190 + i * 12,
      alpha: 0.55 - i * 0.05,
    }));

    let rafId: number | undefined;
    let startTime: number | null = null;

    const draw = (timestamp: number) => {
      if (startTime === null) startTime = timestamp;
      const elapsed = (timestamp - startTime) / 1000;
      const w = width;
      const h = height;

      ctx.clearRect(0, 0, w, h);
      ctx.globalCompositeOperation = "lighter";

      for (const beam of beams) {
        const t = elapsed * beam.speed;
        const spread = Math.PI * 0.5 * beam.angle;
        const length = Math.min(w, h) * 1.2;
        const ox = w / 2;
        const oy = h / 2;

        const x0 = ox - Math.cos(t) * length;
        const y0 = oy - Math.sin(t) * length;
        const x1 = ox + Math.cos(t + spread) * length;
        const y1 = oy + Math.sin(t + spread) * length;

        const gradient = ctx.createLinearGradient(x0, y0, x1, y1);
        gradient.addColorStop(0, `hsla(${beam.hue}, 85%, 65%, ${beam.alpha})`);
        gradient.addColorStop(1, `hsla(${beam.hue + 30}, 85%, 55%, ${beam.alpha * 0.4})`);

        ctx.strokeStyle = gradient;
        ctx.lineWidth = beam.widthFactor * Math.min(w, h);
        ctx.beginPath();
        ctx.moveTo(x0, y0);
        ctx.lineTo(x1, y1);
        ctx.stroke();
      }

      ctx.globalCompositeOperation = "source-over";
    };

    const loop = (timestamp: number) => {
      draw(timestamp);
      rafId = requestAnimationFrame(loop);
    };

    if (reducedMotion) {
      draw(16);
    } else {
      rafId = requestAnimationFrame(loop);
    }

    const handleResize = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
    };

    window.addEventListener("resize", handleResize);
    return () => {
      if (rafId !== undefined) cancelAnimationFrame(rafId);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={`pointer-events-none overflow-hidden ${className}`}
    >
      <canvas ref={canvasRef} className="block h-full w-full" />
    </div>
  );
}
