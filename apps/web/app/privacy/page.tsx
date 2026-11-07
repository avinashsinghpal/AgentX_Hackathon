import Link from "next/link";
import { legalConfig } from "@/lib/legal.config";
import { ArrowLeft } from "lucide-react";

{/* DISCLAIMER: This document is a product prototype template and requires formal review and customization by qualified legal counsel licensed in India before production deployment under Indian law. */}

export const metadata = {
  title: "Privacy Policy | SellerResolve",
  description: "Privacy policy complying with the Digital Personal Data Protection Act, 2023 (DPDP Act) and AI model disclosures.",
};

const sections = [
  { id: "dpdp-scope", title: "1. Scope & DPDP Act 2023 Applicability" },
  { id: "data-collected", title: "2. Personal Data We Collect" },
  { id: "consent-basis", title: "3. Legal Basis & Notice Framework" },
  { id: "fiduciary-processor", title: "4. Data Fiduciary vs Data Processor Roles" },
  { id: "ai-disclosures", title: "5. AI Model & Sub-processor Disclosures" },
  { id: "retention-audit", title: "6. Retention & Cryptographic Audit Logs" },
  { id: "security-measures", title: "7. Technical & Organizational Safeguards" },
  { id: "principal-rights", title: "8. Rights of Data Principals" },
  { id: "grievance-officer", title: "9. Grievance Redressal Officer" },
];

export default function PrivacyPage() {
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
          <span className="text-xs font-mono text-muted-foreground">DPDP Act, 2023 &bull; India</span>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-6 lg:px-12 py-16 lg:py-24">
        {/* Page Header */}
        <div className="max-w-3xl mb-16">
          <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-4">
            <span className="w-8 h-px bg-foreground/20" />
            Data Protection &amp; AI Transparency
          </span>
          <h1 className="text-5xl md:text-6xl font-display tracking-tight mb-4">
            Privacy Policy
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
          This document is an architectural prototype template prepared for the AgentX Hackathon 2026. While drafted to align with the Digital Personal Data Protection Act, 2023 (DPDP Act), it requires legal review and validation by qualified Indian counsel prior to commercial use.
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
            <section id="dpdp-scope" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                1. Scope &amp; DPDP Act 2023 Applicability
              </h2>
              <p className="mb-3">
                {legalConfig.companyName} (&ldquo;we&rdquo;, &ldquo;us&rdquo;, or &ldquo;our&rdquo;) operates {legalConfig.brandName}. This Privacy Policy explains our practices regarding the collection, processing, storage, and transfer of digital personal data in accordance with the Digital Personal Data Protection Act, 2023 (&ldquo;DPDP Act&rdquo;) and relevant rules framed thereunder.
              </p>
              <p>
                This policy applies to personal data processed digitally when small online merchants (&ldquo;Sellers&rdquo;) and purchasing consumers (&ldquo;Buyers&rdquo;) engage with dispute resolution services.
              </p>
            </section>

            <section id="data-collected" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                2. Personal Data We Collect
              </h2>
              <p className="mb-3">We collect and process the following categories of data strictly for resolving e-commerce disputes:</p>
              <ul className="list-disc pl-5 space-y-2 mb-3">
                <li><strong className="text-foreground">Identity &amp; Contact:</strong> Full name, verified mobile number, email address.</li>
                <li><strong className="text-foreground">Order &amp; Fulfillment Context:</strong> Order identifier, line items, SKU, payment status, delivery address, postal PIN code, and carrier tracking milestones.</li>
                <li><strong className="text-foreground">Dispute Submissions:</strong> Customer chat narratives, claimed issue categories, and photographic evidence (e.g. damaged goods or packaging).</li>
                <li><strong className="text-foreground">Technical &amp; Audit Logs:</strong> IP address, device user-agent, session identifiers, tool execution timestamps, and cryptographic hash chain records.</li>
              </ul>
            </section>

            <section id="consent-basis" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                3. Legal Basis &amp; Notice Framework
              </h2>
              <p className="mb-3">
                Personal data is processed pursuant to free, specific, informed, unconditional, and unambiguous consent obtained under Section 6 of the DPDP Act 2023, or for legitimate uses such as voluntary provision of data by the Data Principal for dispute resolution.
              </p>
              <p>
                Data Principals may withdraw consent at any time through our Grievance Desk, subject to legal and regulatory retention obligations.
              </p>
            </section>

            <section id="fiduciary-processor" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                4. Data Fiduciary vs Data Processor Roles
              </h2>
              <p className="mb-3">
                In the context of the platform:
              </p>
              <ul className="list-disc pl-5 space-y-2 mb-3">
                <li>The <strong className="text-foreground">Seller</strong> functions as the primary <strong className="text-foreground">Data Fiduciary</strong>, determining the business purpose of customer order processing and setting store dispute policies.</li>
                <li>{legalConfig.brandName} functions as a <strong className="text-foreground">Data Processor</strong> engaged by the Seller under a valid data processing agreement to evaluate and resolve complaints according to the Seller&rsquo;s deterministic rules.</li>
              </ul>
            </section>

            <section id="ai-disclosures" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                5. AI Model &amp; Sub-processor Disclosures
              </h2>
              <p className="mb-3">
                To facilitate natural language conversations, complaint narratives may be processed using enterprise large language model (LLM) APIs, such as Anthropic Claude.
              </p>
              <p className="mb-3">
                We enforce the following strict guarantees:
              </p>
              <ul className="list-disc pl-5 space-y-2 mb-3">
                <li><strong className="text-foreground">Zero Model Training:</strong> Customer data is processed solely in real-time inference and is never used to train or fine-tune public foundation models.</li>
                <li><strong className="text-foreground">Deterministic Guardrails:</strong> The language model never determines customer eligibility, refund amounts, or access boundaries. Eligibility is computed entirely by deterministic server code.</li>
                <li><strong className="text-foreground">Identity Scoping:</strong> Only data belonging to the authenticated customer and the specific linked order is provided in agent context.</li>
              </ul>
            </section>

            <section id="retention-audit" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                6. Retention &amp; Cryptographic Audit Logs
              </h2>
              <p className="mb-3">
                Case interaction histories, investigation traces, and resolution outcomes are retained for the period necessary to complete the resolution and fulfill statutory accounting, taxation, and limitation periods under Indian law.
              </p>
              <p>
                Every resolution step is preserved in a tamper-evident, SHA-256 hash-chained audit record to ensure mathematical verifiability in the event of customer or merchant appeals.
              </p>
            </section>

            <section id="security-measures" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                7. Technical &amp; Organizational Safeguards
              </h2>
              <p className="mb-3">
                We implement robust security practices under Section 8(5) of the DPDP Act 2023, including TLS 1.3 encryption in transit, AES-256 encryption at rest, argon2-cffi password hashing, rate limiting, and server-side tenant isolation.
              </p>
            </section>

            <section id="principal-rights" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                8. Rights of Data Principals
              </h2>
              <p className="mb-3">
                Under Chapter III of the DPDP Act 2023, you hold the following statutory rights regarding your personal data:
              </p>
              <ul className="list-disc pl-5 space-y-2 mb-3">
                <li><strong className="text-foreground">Right to Access:</strong> Request a summary of personal data processed and third parties with whom it was shared.</li>
                <li><strong className="text-foreground">Right to Correction &amp; Erasure:</strong> Rectify inaccurate data or request deletion where processing is no longer necessary.</li>
                <li><strong className="text-foreground">Right of Grievance Redressal:</strong> Submit a complaint regarding processing to our designated Grievance Officer.</li>
                <li><strong className="text-foreground">Right to Nominate:</strong> Nominate an individual to exercise rights on your behalf in the event of death or incapacity.</li>
              </ul>
            </section>

            <section id="grievance-officer" className="scroll-mt-28">
              <h2 className="text-xl font-display text-foreground mb-3">
                9. Grievance Redressal Officer
              </h2>
              <p className="mb-3">
                In compliance with Section 8(10) of the DPDP Act 2023 and the Information Technology Rules, 2021, the contact details of our Grievance Officer are set forth below:
              </p>
              <div className="p-5 border border-border bg-card/60 rounded-sm font-mono text-xs space-y-2">
                <div><span className="text-muted-foreground">Designation:</span> {legalConfig.grievanceOfficerName}</div>
                <div><span className="text-muted-foreground">Entity:</span> {legalConfig.companyName}</div>
                <div><span className="text-muted-foreground">Email:</span> {legalConfig.grievanceOfficerEmail}</div>
                <div><span className="text-muted-foreground">Phone:</span> {legalConfig.grievanceOfficerPhone}</div>
                <div><span className="text-muted-foreground">Address:</span> {legalConfig.grievanceOfficerAddress}</div>
                <div className="pt-2 text-muted-foreground">
                  Response SLA: Inquiries will be acknowledged within 24 hours and addressed within 15 business days.
                </div>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}

