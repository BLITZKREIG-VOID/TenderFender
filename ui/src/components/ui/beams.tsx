import { useEffect, useRef } from "react";

interface BeamsProps {
  className?: string;
}

// Decorative animated light beams on a 2D canvas (ported from p4/app). Purely visual: aria-hidden,
// no pointer events. Honors prefers-reduced-motion with a single static frame.
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
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const beams = Array.from({ length: 6 }, (_, i) => ({
      angle: (Math.PI * (i + 1)) / 7,
      speed: 0.004 + i * 0.0015,
      widthFactor: 0.006 + i * 0.002,
      hue: 190 + i * 12,
      alpha: 0.55 - i * 0.05,
    }));

    let width = 0;
    let height = 0;
    let elapsed = 0;
    let rafId: number | undefined;
    let startTime: number | null = null;

    const resize = () => {
      width = container.clientWidth;
      height = container.clientHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = "lighter";
      const length = Math.min(width, height) * 1.2;
      const ox = width / 2;
      const oy = height / 2;
      for (const beam of beams) {
        const t = elapsed * beam.speed;
        const spread = Math.PI * 0.5 * beam.angle;
        const x0 = ox - Math.cos(t) * length;
        const y0 = oy - Math.sin(t) * length;
        const x1 = ox + Math.cos(t + spread) * length;
        const y1 = oy + Math.sin(t + spread) * length;
        const gradient = ctx.createLinearGradient(x0, y0, x1, y1);
        gradient.addColorStop(0, `hsla(${beam.hue}, 85%, 65%, ${beam.alpha})`);
        gradient.addColorStop(1, `hsla(${beam.hue + 30}, 85%, 55%, ${beam.alpha * 0.4})`);
        ctx.strokeStyle = gradient;
        ctx.lineWidth = beam.widthFactor * Math.min(width, height);
        ctx.beginPath();
        ctx.moveTo(x0, y0);
        ctx.lineTo(x1, y1);
        ctx.stroke();
      }
      ctx.globalCompositeOperation = "source-over";
    };

    const loop = (timestamp: number) => {
      if (startTime === null) startTime = timestamp;
      elapsed = (timestamp - startTime) / 1000;
      draw();
      rafId = requestAnimationFrame(loop);
    };

    // Size changes (window resize, layout) redraw at the new size; the static frame stays visible too.
    const observer = new ResizeObserver(() => {
      resize();
      draw();
    });
    observer.observe(container);

    resize();
    if (reducedMotion) draw();
    else rafId = requestAnimationFrame(loop);

    return () => {
      if (rafId !== undefined) cancelAnimationFrame(rafId);
      observer.disconnect();
    };
  }, []);

  return (
    <div ref={containerRef} aria-hidden="true" className={`pointer-events-none overflow-hidden ${className}`}>
      <canvas ref={canvasRef} className="block h-full w-full" />
    </div>
  );
}
