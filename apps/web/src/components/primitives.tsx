import type { ReactNode } from "react";

type PanelSpan = "wide" | "full" | "chart" | "side" | "compact";
type PanelCategory = "decision" | "safety" | "governance" | "infra" | "ai_ops";
type PanelTab = "trade" | "evidence" | "execution" | "vault";

export function Panel({
  title,
  badge,
  span,
  category,
  tab,
  children,
}: {
  title: string;
  badge?: string;
  span?: PanelSpan;
  category?: PanelCategory;
  tab?: PanelTab;
  children: ReactNode;
}) {
  return <section className={`panel ${span ?? ""}`} data-category={category} data-tab={tab}><header><h2>{title}</h2>{badge && <b>{badge}</b>}</header>{children}</section>;
}

export function Card({ title, value, note }: { title: string; value: string; note: string }) {
  return <div className="card"><b>{title}</b><strong>{value}</strong><span>{note}</span></div>;
}

export function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric"><span>{label}</span><b>{value}</b></div>;
}

export function Status({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" }) {
  return <div className={`status ${tone ?? ""}`}><span>{label}</span><b>{value}</b></div>;
}

export function pct(value?: number) {
  if (typeof value !== "number") return "0%";
  return `${Math.round(value * 100)}%`;
}

export function money(value?: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value ?? 0);
}
