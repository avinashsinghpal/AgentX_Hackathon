"use client";

import { useEffect, useState, useRef } from "react";
import { Store, ShoppingBag, Truck, CreditCard, Layers, Database } from "lucide-react";

interface Connector {
  name: string;
  category: string;
  status: "Active" | "Planned";
  statusColor: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

const connectors: Connector[] = [
  {
    name: "SellerResolve Demo Store",
    category: "Storefront",
    status: "Active",
    statusColor: "border-emerald-500/30 text-emerald-400 bg-emerald-500/10",
    description: "Built-in mock commerce engine with pre-seeded test orders, shipments, and tracking events.",
    icon: Store,
  },
  {
    name: "Shopify Storefront API",
    category: "E-Commerce",
    status: "Planned",
    statusColor: "border-white/10 text-white/50 bg-white/[0.02]",
    description: "Read orders, fulfillments, customer records, and trigger native draft refund orders.",
    icon: ShoppingBag,
  },
  {
    name: "WooCommerce REST API",
    category: "E-Commerce",
    status: "Planned",
    statusColor: "border-white/10 text-white/50 bg-white/[0.02]",
    description: "Sync order statuses, line item metadata, customer history, and webhook events.",
    icon: Layers,
  },
  {
    name: "Shiprocket / Delhivery",
    category: "Logistics",
    status: "Planned",
    statusColor: "border-white/10 text-white/50 bg-white/[0.02]",
    description: "Fetch live scan checkpoints, reverse pickup AWB generation, and delivery SLA tracking.",
    icon: Truck,
  },
  {
    name: "Razorpay / Cashfree",
    category: "Payments",
    status: "Planned",
    statusColor: "border-white/10 text-white/50 bg-white/[0.02]",
    description: "Pre-act payment verification and policy-capped instant refund settlement triggers.",
    icon: CreditCard,
  },
  {
    name: "Custom Webhook Connector",
    category: "Internal ERP",
    status: "Planned",
    statusColor: "border-white/10 text-white/50 bg-white/[0.02]",
    description: "Direct JSON payload ingestion for custom inventory and order management systems.",
    icon: Database,
  },
];

export function IntegrationsSection() {
  const [isVisible, setIsVisible] = useState(false);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
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
    <section id="connectors" ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden border-t border-foreground/10">
      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12 text-center">
        <span
          className={`inline-flex items-center gap-4 text-sm font-mono text-muted-foreground mb-6 transition-all duration-700 justify-center ${
            isVisible ? "opacity-100" : "opacity-0"
          }`}
        >
          <span className="w-12 h-px bg-foreground/20" />
          Store &amp; Carrier Connectors
          <span className="w-12 h-px bg-foreground/20" />
        </span>

        <h2
          className={`text-5xl md:text-6xl lg:text-[100px] font-display tracking-tight leading-[0.92] transition-all duration-1000 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
        >
          Connect your
          <br />
          <span className="text-muted-foreground">operations stack.</span>
        </h2>

        <p
          className={`mt-6 text-lg lg:text-xl text-muted-foreground leading-relaxed max-w-xl mx-auto transition-all duration-1000 delay-100 ${
            isVisible ? "opacity-100" : "opacity-0"
          }`}
        >
          Start immediately with our native Demo Store connector. Connect external platforms
          as your storefront scales.
        </p>
      </div>

      {/* Visual background element */}
      <div
        className={`max-w-[1200px] mx-auto px-6 my-8 transition-all duration-1000 delay-200 ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}
      >
        <img
          src="/visuals/store-connect.svg"
          alt=""
          aria-hidden="true"
          className="w-full h-auto object-contain max-h-[320px] mx-auto"
        />
      </div>

      {/* Connectors grid */}
      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
          {connectors.map((connector, index) => {
            const Icon = connector.icon;
            return (
              <div
                key={connector.name}
                className={`group relative overflow-hidden p-8 border rounded-sm transition-all duration-300 text-left ${
                  hoveredIndex === index
                    ? "border-foreground/40 bg-foreground/[0.04]"
                    : "border-foreground/10 bg-foreground/[0.01]"
                } ${isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}
                style={{
                  transitionDelay: `${index * 50 + 200}ms`,
                }}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
              >
                <div className="flex items-center justify-between mb-6">
                  <div className="w-10 h-10 rounded-sm border border-foreground/10 flex items-center justify-center text-foreground/80">
                    <Icon className="w-5 h-5" />
                  </div>
                  <span
                    className={`text-[11px] font-mono px-2.5 py-1 rounded border ${connector.statusColor}`}
                  >
                    {connector.status}
                  </span>
                </div>

                <span className="text-xs font-mono text-muted-foreground block mb-1">
                  {connector.category}
                </span>
                <h3 className="text-xl font-display mb-3">{connector.name}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {connector.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
