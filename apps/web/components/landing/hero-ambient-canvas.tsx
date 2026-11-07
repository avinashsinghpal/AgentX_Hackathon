"use client";

import { useEffect, useRef } from "react";

export function HeroAmbientCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let width = 0;
    let height = 0;

    const handleResize = () => {
      width = canvas.parentElement?.clientWidth || window.innerWidth;
      height = canvas.parentElement?.clientHeight || window.innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.scale(dpr, dpr);
    };

    handleResize();
    window.addEventListener("resize", handleResize);

    const particles: Array<{
      x: number;
      y: number;
      radius: number;
      vx: number;
      vy: number;
      color: string;
      alpha: number;
    }> = [];

    const colors = ["#eca8d6", "#a78bfa", "#67e8f9", "#fbbf24"];
    const count = 40;

    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        radius: Math.random() * 2 + 1,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        color: colors[i % colors.length],
        alpha: Math.random() * 0.4 + 0.1,
      });
    }

    let t = 0;

    const render = () => {
      t += 0.01;
      ctx.clearRect(0, 0, width, height);

      // Deep dark background
      ctx.fillStyle = "#06060c";
      ctx.fillRect(0, 0, width, height);

      // Radial ambient glow
      const grad = ctx.createRadialGradient(
        width * 0.65,
        height * 0.45,
        50,
        width * 0.65,
        height * 0.45,
        Math.max(width, height) * 0.6
      );
      grad.addColorStop(0, "rgba(103, 232, 249, 0.08)");
      grad.addColorStop(0.35, "rgba(167, 139, 250, 0.05)");
      grad.addColorStop(0.7, "rgba(236, 168, 214, 0.02)");
      grad.addColorStop(1, "rgba(6, 6, 12, 0)");

      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, width, height);

      // Floating particles
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.alpha * (0.8 + 0.2 * Math.sin(t + p.x));
        ctx.fill();
      });

      ctx.globalAlpha = 1.0;
      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full object-cover object-center opacity-90 block"
      aria-hidden="true"
    />
  );
}

