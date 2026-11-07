/**
 * Legal configuration for SellerResolve
 * Production-bound prototype legal entity and compliance metadata.
 */

export interface LegalConfig {
  companyLegalName: string;
  companyName: string;
  brandName: string;
  registeredAddress: string;
  jurisdiction: string;
  jurisdictionCity: string;
  jurisdictionState: string;
  jurisdictionCountry: string;
  governingLaw: string;
  disputeResolutionCourts: string;
  grievanceOfficerName: string;
  grievanceOfficerEmail: string;
  grievanceOfficerPhone: string;
  grievanceOfficerAddress: string;
  supportEmail: string;
  privacyEmail: string;
  termsVersion: string;
  termsLastUpdated: string;
  privacyVersion: string;
  privacyLastUpdated: string;
  effectiveDate: string;
  lastUpdated: string;
  aiModelProvider: string;
  dataRetentionDays: number;
}

export const legalConfig: LegalConfig = {
  companyLegalName: "SellerResolve Technologies Private Limited",
  companyName: "SellerResolve Technologies",
  brandName: "SellerResolve",
  registeredAddress: "Indiranagar, Bengaluru, Karnataka 560038, India",
  jurisdiction: "Bengaluru, Karnataka, India",
  jurisdictionCity: "Bengaluru",
  jurisdictionState: "Karnataka",
  jurisdictionCountry: "India",
  governingLaw: "Laws of the Republic of India",
  disputeResolutionCourts: "Courts of competent jurisdiction in Bengaluru, Karnataka",
  grievanceOfficerName: "Legal & Data Protection Desk",
  grievanceOfficerEmail: "grievance@sellerresolve.example",
  grievanceOfficerPhone: "+91 80 0000 0000",
  grievanceOfficerAddress: "SellerResolve Operations, Indiranagar, Bengaluru, Karnataka 560038, India",
  supportEmail: "support@sellerresolve.example",
  privacyEmail: "privacy@sellerresolve.example",
  termsVersion: "1.0",
  termsLastUpdated: "November 6, 2026",
  privacyVersion: "1.0",
  privacyLastUpdated: "November 6, 2026",
  effectiveDate: "November 6, 2026",
  lastUpdated: "November 6, 2026",
  aiModelProvider: "Anthropic PBC (Claude API)",
  dataRetentionDays: 90,
};

export function isPlaceholder(val: string): boolean {
  return typeof val === 'string' && val.includes('[PLACEHOLDER');
}
