"use client";

import React, { useEffect, useState } from "react";
import {
  SlidersHorizontal,
  Plus,
  Trash2,
  Save,
  RefreshCw,
  Truck,
  Mail,
  MapPin,
  CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";

export default function SellerOperationsPage() {
  const [warehousePins, setWarehousePins] = useState<string[]>(["560001"]);
  const [newPin, setNewPin] = useState("");
  const [courierPartners, setCourierPartners] = useState<string[]>([
    "Delhivery",
    "Bluedart",
    "Shadowfax",
  ]);
  const [newCourier, setNewCourier] = useState("");
  const [codEnabled, setCodEnabled] = useState(true);
  const [supportEmail, setSupportEmail] = useState("");
  const [supportPhone, setSupportPhone] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchOperations = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/v1/seller/operations");
      if (res.ok) {
        const data = await res.json();
        setWarehousePins(data.warehouse_pincodes || ["560001"]);
        setCourierPartners(data.courier_partners || ["Delhivery", "Bluedart", "Shadowfax"]);
        setCodEnabled(Boolean(data.cod_enabled));
        setSupportEmail(data.support_email || "");
        setSupportPhone(data.support_phone || "");
      } else {
        toast.error("Failed to load operations configuration");
      }
    } catch {
      toast.error("Network error loading operations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOperations();
  }, []);

  const addPin = () => {
    const cleaned = newPin.trim();
    if (!cleaned) return;
    if (warehousePins.includes(cleaned)) {
      toast.error("PIN code already added");
      return;
    }
    setWarehousePins([...warehousePins, cleaned]);
    setNewPin("");
  };

  const removePin = (pinToRemove: string) => {
    if (warehousePins.length <= 1) {
      toast.error("At least one warehouse PIN code is required");
      return;
    }
    setWarehousePins(warehousePins.filter((p) => p !== pinToRemove));
  };

  const addCourier = () => {
    const cleaned = newCourier.trim();
    if (!cleaned) return;
    if (courierPartners.includes(cleaned)) {
      toast.error("Carrier already in list");
      return;
    }
    setCourierPartners([...courierPartners, cleaned]);
    setNewCourier("");
  };

  const removeCourier = (carrierToRemove: string) => {
    if (courierPartners.length <= 1) {
      toast.error("At least one courier partner is required");
      return;
    }
    setCourierPartners(courierPartners.filter((c) => c !== carrierToRemove));
  };

  const handleSave = async () => {
    if (warehousePins.length === 0) {
      toast.error("Please add at least one warehouse PIN code");
      return;
    }

    try {
      setSaving(true);
      const res = await fetch("/api/v1/seller/operations", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          warehouse_pincodes: warehousePins,
          courier_partners: courierPartners,
          cod_enabled: codEnabled,
          support_email: supportEmail.trim() || undefined,
          support_phone: supportPhone.trim() || undefined,
        }),
      });

      if (res.ok) {
        toast.success("Operations configuration updated successfully");
      } else {
        const err = await res.json();
        toast.error(err.error?.message || "Failed to update operations");
      }
    } catch {
      toast.error("Network error updating operations");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-[11px] font-mono uppercase text-muted-foreground tracking-wider">
              Logistics & Fulfillment
            </span>
          </div>
          <h1 className="font-display text-3xl md:text-4xl tracking-tight text-foreground">
            Operations Calibration
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchOperations}
            disabled={loading}
            className="h-10 px-4 rounded-full border border-border text-xs font-mono text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Reload</span>
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="h-10 px-6 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{saving ? "Saving..." : "Save Operations"}</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Warehouse PINs */}
        <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
          <div className="flex items-center gap-2 border-b border-border pb-3">
            <MapPin className="w-4 h-4 text-muted-foreground" />
            <div>
              <h2 className="font-display text-lg tracking-tight text-foreground">
                Warehouse Dispatch PINs
              </h2>
              <p className="text-xs font-mono text-muted-foreground">
                Origins used to compute return freight liability and transit ETAs.
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              placeholder="e.g. 560001"
              value={newPin}
              onChange={(e) => setNewPin(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addPin()}
              className="flex-1 h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
            />
            <button
              type="button"
              onClick={addPin}
              className="h-10 px-4 rounded-md border border-border text-xs font-mono text-foreground hover:bg-foreground/[0.04] transition-colors flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add</span>
            </button>
          </div>

          <div className="flex flex-wrap gap-2 pt-2">
            {warehousePins.map((pin) => (
              <span
                key={pin}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded border border-border bg-foreground/[0.03] text-xs font-mono text-foreground"
              >
                <span>{pin}</span>
                <button
                  type="button"
                  onClick={() => removePin(pin)}
                  className="text-muted-foreground hover:text-destructive transition-colors"
                  aria-label={`Remove PIN ${pin}`}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* Courier Partners */}
        <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
          <div className="flex items-center gap-2 border-b border-border pb-3">
            <Truck className="w-4 h-4 text-muted-foreground" />
            <div>
              <h2 className="font-display text-lg tracking-tight text-foreground">
                Integrated Courier Partners
              </h2>
              <p className="text-xs font-mono text-muted-foreground">
                Logistics carriers queried during shipment verification and tracking.
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              placeholder="e.g. Delhivery, Bluedart"
              value={newCourier}
              onChange={(e) => setNewCourier(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addCourier()}
              className="flex-1 h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
            />
            <button
              type="button"
              onClick={addCourier}
              className="h-10 px-4 rounded-md border border-border text-xs font-mono text-foreground hover:bg-foreground/[0.04] transition-colors flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add</span>
            </button>
          </div>

          <div className="flex flex-wrap gap-2 pt-2">
            {courierPartners.map((carrier) => (
              <span
                key={carrier}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded border border-border bg-foreground/[0.03] text-xs font-mono text-foreground"
              >
                <span>{carrier}</span>
                <button
                  type="button"
                  onClick={() => removeCourier(carrier)}
                  className="text-muted-foreground hover:text-destructive transition-colors"
                  aria-label={`Remove carrier ${carrier}`}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* Escalation & Contact Channels */}
        <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
          <div className="flex items-center gap-2 border-b border-border pb-3">
            <Mail className="w-4 h-4 text-muted-foreground" />
            <div>
              <h2 className="font-display text-lg tracking-tight text-foreground">
                Escalation Notifications
              </h2>
              <p className="text-xs font-mono text-muted-foreground">
                Direct channels alerted when high-risk claims require human approval.
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-mono uppercase text-muted-foreground block mb-1.5">
                Support & Escalation Email
              </label>
              <input
                type="email"
                value={supportEmail}
                onChange={(e) => setSupportEmail(e.target.value)}
                placeholder="support@merchant.com"
                className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
              />
            </div>

            <div>
              <label className="text-xs font-mono uppercase text-muted-foreground block mb-1.5">
                Urgent Escalation Phone (Optional)
              </label>
              <input
                type="tel"
                value={supportPhone}
                onChange={(e) => setSupportPhone(e.target.value)}
                placeholder="+91 98765 43210"
                className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
              />
            </div>
          </div>
        </div>

        {/* Payment & Settlement Workflows */}
        <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
          <div className="flex items-center gap-2 border-b border-border pb-3">
            <SlidersHorizontal className="w-4 h-4 text-muted-foreground" />
            <div>
              <h2 className="font-display text-lg tracking-tight text-foreground">
                Payment Workflows
              </h2>
              <p className="text-xs font-mono text-muted-foreground">
                Payment channel support and Cash on Delivery parameters.
              </p>
            </div>
          </div>

          <div className="space-y-4 pt-2">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={codEnabled}
                onChange={(e) => setCodEnabled(e.target.checked)}
                className="rounded border-border text-foreground focus:ring-0"
              />
              <span className="text-xs font-mono text-foreground">
                Enable Cash on Delivery (COD) specific settlement & bank verification
              </span>
            </label>
            <p className="text-xs text-muted-foreground leading-relaxed pl-7">
              When COD orders are returned, customer bank account IFSC details are securely collected and verified prior to payout execution.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
