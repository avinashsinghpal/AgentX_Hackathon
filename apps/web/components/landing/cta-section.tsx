"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, Store, ShoppingBag } from "lucide-react";

export function CtaSection() {
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLDivElement>(null);
  const [mousePosition, setMousePosition] = useState({ x: 50, y: 50 });

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.2 }
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setMousePosition({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    });
  };

  return (
    <section ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div
          className={`relative border border-foreground/20 rounded-sm transition-all duration-1000 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
          onMouseMove={handleMouseMove}
        >
          {/* Mouse-following spotlight effect */}
          <div
            className="absolute inset-0 opacity-20 pointer-events-none transition-opacity duration-300"
            style={{
              background: `radial-gradient(600px circle at ${mousePosition.x}% ${mousePosition.y}%, rgba(236,168,214,0.15), transparent 45%)`,
            }}
          />

          <div className="relative z-10 px-8 lg:px-16 py-16 lg:py-24">
            <div className="flex flex-col lg:flex-row items-center justify-between gap-12">
              {/* Left content */}
              <div className="flex-1">
                <span className="inline-flex items-center gap-3 text-xs font-mono uppercase tracking-wider text-muted-foreground mb-6">
                  <span className="w-8 h-px bg-foreground/20" />
                  Get Started
                </span>

                <h2 className="text-5xl md:text-6xl lg:text-[76px] font-display tracking-tight mb-6 leading-[0.95]">
                  Ready to resolve,
                  <br />
                  <span className="text-muted-foreground">not just reply?</span>
                </h2>

                <p className="text-lg text-muted-foreground mb-10 leading-relaxed max-w-xl">
                  Connect your store and define your resolution boundaries in under ten minutes,
                  or resolve an active order claim with full transparency.
                </p>

                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
                  <Link
                    href="/login/seller"
                    className="inline-flex items-center justify-center gap-2 bg-foreground hover:bg-foreground/90 text-background px-8 h-14 text-base rounded-full font-medium transition-all group"
                  >
                    <Store className="w-4 h-4" />
                    I am a seller
                    <ArrowRight className="w-4 h-4 ml-1 transition-transform group-hover:translate-x-1" />
                  </Link>
                  <Link
                    href="/login/buyer"
                    className="inline-flex items-center justify-center gap-2 border border-foreground/30 hover:border-foreground text-foreground px-8 h-14 text-base rounded-full font-medium transition-all"
                  >
                    <ShoppingBag className="w-4 h-4" />
                    I am a buyer
                  </Link>
                </div>

                <p className="text-xs text-muted-foreground mt-8 font-mono">
                  Autonomous investigation • Seller-governed policies • Tamper-evident audit log
                </p>
              </div>

              {/* Right decorative visual */}
              <div className="hidden lg:flex items-center justify-center w-[480px] h-[360px]">
                <img
                  src="/visuals/policy-shield.svg"
                  alt=""
                  aria-hidden="true"
                  className="w-full h-full object-contain"
                />
              </div>
            </div>
          </div>

          {/* Decorative corners */}
          <div className="absolute top-0 right-0 w-24 h-24 border-b border-l border-foreground/10 pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-24 h-24 border-t border-r border-foreground/10 pointer-events-none" />
        </div>
      </div>
    </section>
  );
}
