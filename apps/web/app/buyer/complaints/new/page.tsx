"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Package,
  AlertTriangle,
  UploadCloud,
  FileImage,
  Trash2,
  CheckCircle2,
  ArrowRight,
  Truck,
  RotateCcw,
} from "lucide-react";
import { toast } from "sonner";

interface OrderOption {
  id: string;
  order_number: string;
  seller_name: string;
  total_amount: number;
  currency: string;
  order_status: string;
}

const ISSUE_CATEGORIES = [
  {
    id: "damaged",
    label: "Damaged / Defective Item",
    desc: "Item arrived broken, punctured, cracked, or inoperable.",
    icon: AlertTriangle,
  },
  {
    id: "return",
    label: "Return or Exchange",
    desc: "Standard return or size exchange within merchant policy window.",
    icon: RotateCcw,
  },
  {
    id: "delay",
    label: "Delivery Delay / Overdue",
    desc: "Shipment is in transit and has passed its promised delivery date.",
    icon: Truck,
  },
  {
    id: "missing_item",
    label: "Missing or Wrong Item",
    desc: "Box arrived empty, missing components, or incorrect SKU delivered.",
    icon: Package,
  },
];

function ComplaintForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedOrderId = searchParams.get("order_id");

  const [orders, setOrders] = useState<OrderOption[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState<string>(preselectedOrderId || "");
  const [category, setCategory] = useState<string>("damaged");
  const [narrative, setNarrative] = useState("");
  const [uploadingFile, setUploadingFile] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<
    Array<{ id: string; filename: string; size: number }>
  >([]);
  const [submitting, setSubmitting] = useState(false);
  const [loadingOrders, setLoadingOrders] = useState(true);

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        setLoadingOrders(true);
        const res = await fetch("/api/v1/buyer/orders");
        if (res.ok) {
          const data = await res.json();
          setOrders(data);
          if (!selectedOrderId && data.length > 0) {
            setSelectedOrderId(data[0].id);
          }
        }
      } catch {
        toast.error("Failed to load orders");
      } finally {
        setLoadingOrders(false);
      }
    };

    fetchOrders();
  }, [selectedOrderId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    if (file.size > 5 * 1024 * 1024) {
      toast.error("File exceeds 5MB size limit");
      return;
    }

    try {
      setUploadingFile(true);
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/api/v1/files/upload", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setUploadedFiles([
          ...uploadedFiles,
          {
            id: data.id,
            filename: file.name,
            size: file.size,
          },
        ]);
        toast.success(`Uploaded ${file.name}`);
      } else {
        const err = await res.json();
        toast.error(err.error?.message || "Failed to upload file");
      }
    } catch {
      toast.error("Network error uploading photo");
    } finally {
      setUploadingFile(false);
      e.target.value = "";
    }
  };

  const removeFile = (idToRemove: string) => {
    setUploadedFiles(uploadedFiles.filter((f) => f.id !== idToRemove));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrderId) {
      toast.error("Please select an order");
      return;
    }
    if (narrative.trim().length < 5) {
      toast.error("Please provide at least 5 characters describing the issue");
      return;
    }

    try {
      setSubmitting(true);
      const res = await fetch("/api/v1/buyer/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: selectedOrderId,
          issue_category: category,
          customer_narrative: narrative.trim(),
          evidence_urls: uploadedFiles.map((f) => f.id),
        }),
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(`Case ${data.case_number} opened with autonomous agent`);
        router.push("/buyer/cases");
      } else {
        const err = await res.json();
        toast.error(err.error?.message || "Failed to create complaint case");
      }
    } catch {
      toast.error("Network error submitting complaint");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Step 1: Order Selection */}
      <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
        <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground block">
          Step 1 &bull; Select Order
        </span>

        {loadingOrders ? (
          <div className="text-xs font-mono text-muted-foreground">Loading orders...</div>
        ) : orders.length === 0 ? (
          <div className="p-4 rounded border border-border bg-background text-xs font-mono text-muted-foreground">
            No orders found. Please claim an order in the Orders tab first.
          </div>
        ) : (
          <div>
            <label htmlFor="order-select" className="sr-only">Select Order</label>
            <select
              id="order-select"
              value={selectedOrderId}
              onChange={(e) => setSelectedOrderId(e.target.value)}
              className="w-full h-11 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
            >
              {orders.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.order_number} &bull; {o.seller_name} &bull; {o.currency}{" "}
                  {Number(o.total_amount ?? 0).toFixed(2)} ({o.order_status})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Step 2: Issue Category */}
      <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
        <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground block">
          Step 2 &bull; What is the nature of the issue?
        </span>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {ISSUE_CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            const isSelected = category === cat.id;
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => setCategory(cat.id)}
                className={`p-4 rounded-md border text-left transition-all space-y-2 ${
                  isSelected
                    ? "border-foreground bg-foreground/[0.04] text-foreground"
                    : "border-border bg-background hover:border-foreground/30 text-muted-foreground"
                }`}
              >
                <div className="flex items-center justify-between">
                  <Icon className="w-4 h-4 text-foreground" />
                  {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                </div>
                <div>
                  <span className="text-xs font-mono font-medium block text-foreground">
                    {cat.label}
                  </span>
                  <span className="text-[11px] font-mono text-muted-foreground leading-snug block mt-0.5">
                    {cat.desc}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Step 3: Problem Description */}
      <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
        <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground block">
          Step 3 &bull; Describe the problem in detail
        </span>

        <textarea
          required
          rows={5}
          placeholder="Please detail what occurred (e.g., package condition on delivery, defect details, missing components)..."
          value={narrative}
          onChange={(e) => setNarrative(e.target.value)}
          className="w-full p-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50 leading-relaxed"
        />
      </div>

      {/* Step 4: Photo / Evidence Upload */}
      <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground block">
            Step 4 &bull; Photo Evidence (JPEG, PNG, WebP)
          </span>
          <span className="text-[10px] font-mono text-muted-foreground">Max 5MB per image</span>
        </div>

        <div className="border border-dashed border-border rounded-md p-6 text-center hover:bg-foreground/[0.02] transition-colors">
          <input
            type="file"
            id="file-upload"
            accept=".jpg,.jpeg,.png,.webp"
            onChange={handleFileUpload}
            disabled={uploadingFile}
            className="hidden"
          />
          <label htmlFor="file-upload" className="cursor-pointer space-y-2 block">
            <UploadCloud className="w-8 h-8 text-muted-foreground mx-auto" />
            <div className="text-xs font-mono text-foreground">
              {uploadingFile ? "Uploading and verifying..." : "Click to upload damage or label photos"}
            </div>
            <p className="text-[11px] font-mono text-muted-foreground">
              Cryptographically hashed and stored on self-hosted storage.
            </p>
          </label>
        </div>

        {uploadedFiles.length > 0 && (
          <div className="space-y-2 pt-2">
            <span className="text-[11px] font-mono uppercase text-muted-foreground">
              Attached Evidence Files ({uploadedFiles.length})
            </span>
            <div className="space-y-1.5">
              {uploadedFiles.map((file) => (
                <div
                  key={file.id}
                  className="p-2.5 rounded border border-border bg-background flex items-center justify-between text-xs font-mono"
                >
                  <div className="flex items-center gap-2 text-foreground">
                    <FileImage className="w-4 h-4 text-emerald-400" />
                    <span className="truncate max-w-xs">{file.filename}</span>
                    <span className="text-[10px] text-muted-foreground">
                      ({(file.size / 1024).toFixed(1)} KB)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeFile(file.id)}
                    className="text-muted-foreground hover:text-destructive"
                    aria-label={`Remove file ${file.filename}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Submit Button */}
      <div className="flex justify-end pt-2">
        <button
          type="submit"
          disabled={submitting || !selectedOrderId || narrative.trim().length < 5}
          className="h-11 px-8 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity flex items-center gap-2 disabled:opacity-50"
        >
          <span>{submitting ? "Opening Case..." : "Submit to Autonomous Agent"}</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </form>
  );
}

export default function NewComplaintPage() {
  return (
    <div className="space-y-8 max-w-3xl">
      {/* Header */}
      <div className="border-b border-border pb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span className="text-[11px] font-mono uppercase text-muted-foreground tracking-wider">
            Autonomous Resolution Intake
          </span>
        </div>
        <h1 className="font-display text-3xl md:text-4xl tracking-tight text-foreground">
          File a Complaint or Claim
        </h1>
        <p className="text-xs text-muted-foreground font-mono mt-1">
          The merchant resolution agent will immediately verify order dispatch records and policy parameters.
        </p>
      </div>

      <Suspense fallback={<div className="text-xs font-mono text-muted-foreground">Loading form...</div>}>
        <ComplaintForm />
      </Suspense>
    </div>
  );
}