import Link from "next/link";
import { legalConfig } from "@/lib/legal.config";
import { ArrowLeft } from "lucide-react";

{/* DISCLAIMER: This document is a product prototype template and requires formal review and customization by qualified legal counsel licensed in India before production deployment under Indian law. */}

export const metadata = {
  title: "Terms of Service | SellerResolve",
  description: "Terms and conditions governing the use of the SellerResolve autonomous dispute resolution platform.",
};

const sections = [
  { id: "acceptance", title: "1. Acceptance of Terms & Eligibility" },
  { id: "role", title: "2. Role of the Platform as an Intermediary" },
  { id: "accounts", title: "3. User Accounts & Responsibilities" },
  { id: "policies", title: "4. Seller Policies & Autonomous Resolution Scope" },
  { id: "buyer-submissions", title: "5. Buyer Submissions & Evidence Authenticity" },
  { id: "financial-settlements", title: "6. Financial Settlements & Refunds" },
  { id: "prohibited-uses", title: "7. Prohibited Uses & Abuse Prevention" },
  { id: "liability", title: "8. Disclaimers & Limitation of Liability" },
  { id: "governing-law", title: "9. Governing Law & Dispute Resolution" },
  { id: "amendments", title: "10. Contact & Regulatory Inquiries" },
];

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Top Navigation Bar */}
      <header className="border-b border-border bg-background/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-12 h-16 flex items-center justify-between">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm font-mono text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </Link>
          <span className="font-display text-lg tracking-tight">SellerResolve</span>
          <span className="text-xs font-mono text-muted-foreground">Legal &bull; India</span>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-6 lg:px-12 py-16 lg:py-24">
        {/* Page Header */}
        <div className="max-w-3xl mb-16">
          <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-4">
            <span className="w-8 h-px bg-foreground/20" />
            Legal Agreement
          </span>
          <h1 className="text-5xl md:text-6xl font-display tracking-tight mb-4">
            Terms of Service
          </h1>
          <p className="text-sm font-mono text-muted-foreground">
            Effective Date: {legalConfig.effectiveDate} &bull; Last Revised: {legalConfig.lastUpdated}
          </p>
        </div>

        {/* Prototype Legal Disclaimer Notice Box */}
        <div className="p-6 mb-16 rounded-sm border border-amber-500/30 bg-amber-500/5 text-amber-200/90 text-sm leading-relaxed">
          <span className="font-mono text-xs uppercase tracking-wider block font-semibold mb-1 text-amber-300">
            Prototype Disclaimer
          </span>
          This document is a product prototype template for the AgentX Hackathon 2026. Prior to commercial production deployment, this document requires formal legal review and adaptation by qualified counsel admitted to practice in {legalConfig.jurisdictionCountry}.
        </div>

        <div className="grid lg:grid-cols-12 gap-12 items-start">
          {/* Table of Contents Sticky Sidebar */}
          <aside className="lg:col-span-4 sticky top-24 border border-border p-6 rounded-sm bg-card/40">
            <h2 className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-4">
              Table of Contents
            </h2>
            <nav className="space-y-2">
              {sections.map((sec) => (
                <a
                  key={sec.id}
                  href={`#${sec.id}`}
                  className="block text-xs font-mono text-muted-foreground hover:text-foreground transition-colors py-1"
                >
                  {sec.title}
                </a>
              ))}
            </nav>
          </aside>

          {/* Legal Text Body */}
          <div className="lg:col-span-8 space-y-12 leading-relaxed text-sm text-muted-foreground">
            <section id="acceptance" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                1. Acceptance of Terms &amp; Eligibility
              </h2>
              <p className="mb-3">
                These Terms of Service (&ldquo;Terms&rdquo;) govern your access to and use of {legalConfig.brandName} (&ldquo;Platform&rdquo;), operated by {legalConfig.companyName} (&ldquo;Company&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;, or &ldquo;our&rdquo;). By accessing the Platform as an online merchant (&ldquo;Seller&rdquo;) or as a purchasing customer (&ldquo;Buyer&rdquo;), you agree to be bound by these Terms.
              </p>
              <p>
                You must be at least 18 years of age and competent to enter into a legally binding contract under the Indian Contract Act, 1872. If acting on behalf of a corporate entity, you represent and warrant that you hold express authority to bind said entity.
              </p>
            </section>

            <section id="role" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                2. Role of the Platform as an Intermediary
              </h2>
              <p className="mb-3">
                {legalConfig.brandName} is an automated dispute resolution software platform operating as an &ldquo;intermediary&rdquo; under Section 2(1)(w) of the Information Technology Act, 2000, read with the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021.
              </p>
              <p>
                {legalConfig.brandName} is not a merchant of record, common carrier, financial institution, or insurer. The contract of sale for all underlying goods remains strictly bilateral between the Buyer and the respective Seller.
              </p>
            </section>

            <section id="accounts" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                3. User Accounts &amp; Responsibilities
              </h2>
              <p className="mb-3">
                Sellers must complete verification and configure their store operations truthfully. Buyers must register using accurate mobile and identity credentials matching their storefront order history.
              </p>
              <p>
                Users are solely responsible for maintaining the confidentiality of session credentials. Any resolution request or policy instruction executed under your authenticated session shall be deemed authorized by you.
              </p>
            </section>

            <section id="policies" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                4. Seller Policies &amp; Autonomous Resolution Scope
              </h2>
              <p className="mb-3">
                Sellers configure resolution policies (including return windows, refund limits, allowable delay tolerances, and photo evidence requirements). By activating an agent, the Seller explicitly authorizes {legalConfig.brandName} to evaluate claims and execute actions strictly within the bounds of said policies.
              </p>
              <p>
                Any resolution exceeding configured autonomous thresholds requires manual confirmation via the Seller&rsquo;s approval queue. The language model never determines policy or spending caps.
              </p>
            </section>

            <section id="buyer-submissions" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                5. Buyer Submissions &amp; Evidence Authenticity
              </h2>
              <p className="mb-3">
                Buyers submitting claims regarding damaged, defective, or missing goods agree to provide authentic, unedited photographic or video evidence.
              </p>
              <p>
                Submitting falsified, manipulated, or duplicate evidence constitutes a material breach of these Terms, resulting in immediate case termination, account restriction, and potential referral to relevant authorities under applicable fraud statutes.
              </p>
            </section>

            <section id="financial-settlements" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                6. Financial Settlements &amp; Refunds
              </h2>
              <p className="mb-3">
                {legalConfig.brandName} coordinates resolution logic with the Seller&rsquo;s integrated payment gateway or store credit mechanism. {legalConfig.brandName} does not hold customer funds in escrow or operate a payment aggregator system under Reserve Bank of India (RBI) regulations.
              </p>
              <p>
                Refund turnaround times depend entirely on the originating bank, UPI network, or card network once the refund instruction is triggered.
              </p>
            </section>

            <section id="prohibited-uses" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                7. Prohibited Uses &amp; Abuse Prevention
              </h2>
              <p className="mb-3">
                Users shall not: (a) submit duplicate claims for the same order item; (b) attempt prompt injection or adversarial attacks against agent endpoints; (c) reverse engineer, decompile, or scrape platform data; or (d) misuse communication channels to transmit unlawful or harassing content.
              </p>
              <p>
                All actions are cryptographically logged in an append-only audit trail to detect and prevent automated abuse.
              </p>
            </section>

            <section id="liability" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                8. Disclaimers &amp; Limitation of Liability
              </h2>
              <p className="mb-3">
                The Platform is provided on an &ldquo;AS IS&rdquo; and &ldquo;AS AVAILABLE&rdquo; basis. To the maximum extent permitted by applicable law, {legalConfig.companyName} disclaims all warranties of merchantability, fitness for a particular purpose, and non-infringement.
              </p>
              <p>
                In no event shall {legalConfig.companyName} be liable for indirect, incidental, punitive, or consequential damages resulting from courier transit delays, third-party gateway downtime, or merchant policy disputes.
              </p>
            </section>

            <section id="governing-law" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                9. Governing Law &amp; Dispute Resolution
              </h2>
              <p className="mb-3">
                These Terms shall be governed by and construed in accordance with the laws of the Republic of India.
              </p>
              <p>
                Any dispute, claim, or controversy arising out of or relating to these Terms shall be subject to the exclusive jurisdiction of the competent courts situated in {legalConfig.jurisdictionCity}, {legalConfig.jurisdictionState}, {legalConfig.jurisdictionCountry}.
              </p>
            </section>

            <section id="amendments" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                10. Contact &amp; Regulatory Inquiries
              </h2>
              <p className="mb-3">
                For questions regarding these Terms or regulatory compliance, contact our legal desk:
              </p>
              <div className="p-4 border border-border bg-card/60 rounded-sm font-mono text-xs space-y-1">
                <div>Entity: {legalConfig.companyName}</div>
                <div>Support Desk: {legalConfig.supportEmail}</div>
                <div>Location: {legalConfig.jurisdictionCity}, {legalConfig.jurisdictionState}, {legalConfig.jurisdictionCountry}</div>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}

