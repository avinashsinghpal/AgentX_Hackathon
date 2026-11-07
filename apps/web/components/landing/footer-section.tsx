"use client";

import Link from "next/link";
import { legalConfig } from "@/config/legal.config";
import { ArrowUpRight } from "lucide-react";

export function FooterSection() {
  return (
    <footer className="relative bg-black text-white">
      {/* Panoramic banner visual */}
      <div className="relative w-full h-[280px] md:h-[360px] overflow-hidden">
        <img
          src="/visuals/footer-glow.svg"
          alt=""
          className="w-full h-full object-cover object-center"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black" />
        <div className="absolute inset-0 bg-gradient-to-r from-black/50 via-transparent to-black/50" />
      </div>

      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Main Footer */}
        <div className="py-16 lg:py-20">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-12 lg:gap-8">
            {/* Brand Column (Spans 2) */}
            <div className="col-span-2">
              <Link href="/" className="inline-flex items-center gap-2 mb-4">
                <span className="text-2xl font-display text-white">SellerResolve</span>
                <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest px-1.5 py-0.5 border border-white/20 rounded">
                  Prototype
                </span>
              </Link>

              <p className="text-white/60 leading-relaxed mb-6 max-w-sm text-sm">
                Autonomous, policy-aware customer resolution engine for online sellers. Investigate. Decide. Act. Verify.
              </p>

              <p className="text-xs font-mono text-white/40">
                Built by Team &ldquo;Break The Bug&rdquo; &bull; AgentX Hackathon 2026
              </p>
            </div>

            {/* Product Column */}
            <div>
              <h3 className="text-xs font-mono uppercase tracking-wider text-white/50 mb-5">
                Product
              </h3>
              <ul className="space-y-3">
                <li>
                  <a href="#features" className="text-sm text-white/70 hover:text-white transition-colors">
                    Capabilities
                  </a>
                </li>
                <li>
                  <a href="#how-it-works" className="text-sm text-white/70 hover:text-white transition-colors">
                    Resolution Loop
                  </a>
                </li>
                <li>
                  <a href="#operations" className="text-sm text-white/70 hover:text-white transition-colors">
                    Operations
                  </a>
                </li>
                <li>
                  <a href="#security" className="text-sm text-white/70 hover:text-white transition-colors">
                    Safeguards
                  </a>
                </li>
              </ul>
            </div>

            {/* Portals Column */}
            <div>
              <h3 className="text-xs font-mono uppercase tracking-wider text-white/50 mb-5">
                Portals
              </h3>
              <ul className="space-y-3">
                <li>
                  <Link href="/login/seller" className="text-sm text-white/70 hover:text-white transition-colors">
                    Seller Portal
                  </Link>
                </li>
                <li>
                  <Link href="/login/buyer" className="text-sm text-white/70 hover:text-white transition-colors">
                    Buyer Portal
                  </Link>
                </li>
                <li>
                  <Link href="/register/seller" className="text-sm text-white/70 hover:text-white transition-colors">
                    Seller Registration
                  </Link>
                </li>
                <li>
                  <Link href="/register/buyer" className="text-sm text-white/70 hover:text-white transition-colors">
                    Buyer Registration
                  </Link>
                </li>
              </ul>
            </div>

            {/* Legal Column */}
            <div>
              <h3 className="text-xs font-mono uppercase tracking-wider text-white/50 mb-5">
                Legal
              </h3>
              <ul className="space-y-3">
                <li>
                  <Link href="/terms" className="text-sm text-white/70 hover:text-white transition-colors">
                    Terms of Service
                  </Link>
                </li>
                <li>
                  <Link href="/privacy" className="text-sm text-white/70 hover:text-white transition-colors">
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <a href="#security" className="text-sm text-white/70 hover:text-white transition-colors">
                    Security Principles
                  </a>
                </li>
              </ul>
            </div>

            {/* Support Column */}
            <div>
              <h3 className="text-xs font-mono uppercase tracking-wider text-white/50 mb-5">
                Contact
              </h3>
              <ul className="space-y-3">
                <li>
                  <a
                    href={`mailto:${legalConfig.supportEmail}`}
                    className="text-sm text-white/70 hover:text-white transition-colors inline-flex items-center gap-1 group"
                  >
                    <span>Support Email</span>
                    <ArrowUpRight className="w-3 h-3 opacity-60 group-hover:opacity-100 transition-opacity" />
                  </a>
                </li>
                <li>
                  <span className="text-xs font-mono text-white/40 block">
                    {legalConfig.jurisdictionCity}, {legalConfig.jurisdictionCountry}
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="py-8 border-t border-white/10 flex flex-col md:flex-row items-center justify-between gap-4 text-xs font-mono text-white/40">
          <p>
            &copy; 2026 SellerResolve. All rights reserved.
          </p>

          <div className="flex items-center gap-6">
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              Prototype build &bull; Hackathon 2026
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
