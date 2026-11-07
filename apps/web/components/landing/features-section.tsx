"use client";

import { useEffect, useRef, useState } from "react";

const features = [
  {
    number: "01",
    title: "Context-Aware Investigation",
    description: "The agent retrieves order, payment, and shipment records through secure tools before crafting a response. No assumptions, only verified facts.",
    stats: { tag: "Tool-based retrieval", label: "Automated record inspection" },
  },
  {
    number: "02",
    title: "Policy-Bounded Autonomy",
    description: "Refund limits, return windows, and approval rules are set directly by the seller and strictly enforced in deterministic code.",
    stats: { tag: "Seller-defined limits", label: "Zero hallucinated decisions" },
  },
  {
    number: "03",
    title: "Evidence-Backed Resolution",
    description: "Photos and courier delivery proof are requested when needed. Outcomes are verified against courier APIs, and ambiguous cases escalate to the seller.",
    stats: { tag: "Verified outcomes", label: "Human escalation fallback" },
  },
  {
    number: "04",
    title: "Proactive Exception Monitoring",
    description: "Shipments delayed beyond policy thresholds are detected in the background, updating customers early before complaints arise.",
    stats: { tag: "Background checks", label: "Automated status alerts" },
  },
];

// Floating dot particles visualization
function ParticleVisualization() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let frameId: number;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener("resize", resize);

    const particles: Array<{ x: number; y: number; vx: number; vy: number; radius: number }> = [];
    const count = 30;
    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;

    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        radius: Math.random() * 2 + 1,
      });
    }

    const render = () => {
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = "rgba(103, 232, 249, 0.25)";

      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fill();
      });

      frameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(frameId);
    };
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />;
}

export function FeaturesSection() {
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.1 }
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section
      id="features"
      ref={sectionRef}
      className="relative py-24 lg:py-32 overflow-hidden"
    >
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header - Full width with diagonal layout */}
        <div className="relative mb-24 lg:mb-32">
          <div className="grid lg:grid-cols-12 gap-8 items-end">
            <div className="lg:col-span-7">
              <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6">
                <span className="w-12 h-px bg-foreground/30" />
                Capabilities
              </span>
              <h2
                className={`text-6xl md:text-7xl lg:text-[128px] font-display tracking-tight leading-[0.9] transition-all duration-1000 ${
                  isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
                }`}
              >
                Policy-aware
                <br />
                <span className="text-muted-foreground">resolution.</span>
              </h2>
            </div>
            <div className="lg:col-span-5 lg:pb-4">
              <p className={`text-xl text-muted-foreground leading-relaxed transition-all duration-1000 delay-200 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}>
                An autonomous, policy-aware support agent that investigates customer issues, executes authorized resolutions, and verifies outcomes within seller-defined boundaries.
              </p>
            </div>
          </div>
        </div>

        {/* Bento Grid Layout */}
        <div className="grid lg:grid-cols-12 gap-4 lg:gap-6">
          {/* Feature 01: Large card */}
          <div 
            className={`lg:col-span-12 relative bg-black border border-foreground/10 min-h-[460px] overflow-hidden group transition-all duration-700 flex flex-col lg:flex-row ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-12"
            }`}
          >
            {/* Left: text content */}
            <div className="relative flex-1 p-8 lg:p-12 bg-black flex flex-col justify-between">
              <ParticleVisualization />
              <div className="relative z-10">
                <span className="font-mono text-sm text-muted-foreground">{features[0].number}</span>
                <h3 className="text-3xl lg:text-4xl font-display mt-4 mb-6 group-hover:translate-x-2 transition-transform duration-500">
                  {features[0].title}
                </h3>
                <p className="text-lg text-muted-foreground leading-relaxed max-w-xl mb-8">
                  {features[0].description}
                </p>
              </div>
              <div className="relative z-10 pt-4 border-t border-foreground/10">
                <span className="text-xl lg:text-2xl font-mono text-cyan-300 font-medium">{features[0].stats.tag}</span>
                <span className="block text-sm text-muted-foreground font-mono mt-1">{features[0].stats.label}</span>
              </div>
            </div>

            {/* Right: graphic */}
            <div className="relative w-full lg:w-[42%] min-h-[260px] lg:min-h-full shrink-0 overflow-hidden bg-black/60">
              <img
                src="/visuals/investigation-flow.svg"
                alt=""
                aria-hidden="true"
                className="absolute inset-0 w-full h-full object-cover object-center"
                style={{ transform: "scaleX(-1)" }}
              />
              <div className="absolute inset-0 bg-gradient-to-r from-black via-transparent to-transparent pointer-events-none" />
            </div>
          </div>

          {/* Features 02, 03, 04: Three-column subgrid */}
          {features.slice(1).map((feature, i) => (
            <div
              key={feature.number}
              className={`lg:col-span-4 relative bg-black border border-foreground/10 p-8 lg:p-10 flex flex-col justify-between group transition-all duration-700 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-12"
              }`}
              style={{ transitionDelay: `${(i + 1) * 150}ms` }}
            >
              <div>
                <span className="font-mono text-sm text-muted-foreground">{feature.number}</span>
                <h3 className="text-2xl lg:text-3xl font-display mt-4 mb-4 group-hover:translate-x-1 transition-transform duration-500">
                  {feature.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed mb-8">
                  {feature.description}
                </p>
              </div>
              <div className="pt-4 border-t border-foreground/10">
                <span className="text-base font-mono text-cyan-300 font-medium">{feature.stats.tag}</span>
                <span className="block text-xs text-muted-foreground font-mono mt-1">{feature.stats.label}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
