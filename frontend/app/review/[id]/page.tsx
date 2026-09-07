"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "../../components/AppShell";
import { LocalDocument, ReviewDraft, emptyReview, exportDocument, readDocuments, updateReview } from "../../../lib/documents";

const fields: Array<{ key: keyof ReviewDraft; label: string; type?: string }> = [
  { key: "supplier_name", label: "Supplier name" }, { key: "invoice_number", label: "Invoice number" }, { key: "issue_date", label: "Issue date", type: "date" }, { key: "due_date", label: "Due date", type: "date" }, { key: "currency", label: "Currency" }, { key: "subtotal", label: "Subtotal", type: "number" }, { key: "tax_amount", label: "Tax amount", type: "number" }, { key: "total_amount", label: "Total amount", type: "number" },
];

export default function ReviewPage() {
  const params = useParams<{ id: string }>();
  const [document, setDocument] = useState<LocalDocument | null | undefined>(undefined);
  const [draft, setDraft] = useState<ReviewDraft>(emptyReview);
  const [saved, setSaved] = useState(false);
  useEffect(() => { const found = readDocuments().find(({ id }) => id === params.id) ?? null; setDocument(found); if (found?.review) setDraft(found.review); }, [params.id]);
  if (document === undefined) return null;
  if (!document) return <AppShell><main className="mx-auto max-w-3xl px-5 py-16"><h1 className="text-2xl font-bold">Document not found</h1><Link className="mt-4 inline-block text-blue-700" href="/documents">Return to documents</Link></main></AppShell>;
  function save() { if (!document) return; const reviewed: LocalDocument = { ...document, review: draft }; updateReview(reviewed.id, draft); setDocument(reviewed); setSaved(true); }
  return <AppShell><main className="mx-auto max-w-6xl px-5 py-12 sm:px-8 sm:py-16"><Link href="/documents" className="text-sm font-semibold text-blue-700 hover:text-blue-900">← Documents</Link><div className="mt-5 flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-semibold uppercase tracking-[0.16em] text-blue-700">Review</p><h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{document.original_filename}</h1></div><button onClick={() => exportDocument({ ...document, review: draft })} className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">Export CSV</button></div><div className="mt-8 grid gap-7 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]"><aside className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="font-semibold text-slate-900">Document status</h2><p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm font-medium capitalize text-amber-700">{document.processing_status.replaceAll("_", " ")}</p><div className="mt-6 border-t border-slate-100 pt-5 text-sm text-slate-600"><p className="font-medium text-slate-900">Original file</p><p className="mt-1 break-all">{document.original_filename}</p><p className="mt-4 text-xs leading-5">Original files remain private. A document preview and extraction result will appear here when those API endpoints are available.</p></div></aside><section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold text-slate-900">Extracted data</h2><p className="mt-1 text-sm text-slate-500">Review and correct the draft before exporting.</p></div>{saved && <span className="text-sm font-medium text-emerald-700">Saved locally</span>}</div><div className="mt-6 grid gap-5 sm:grid-cols-2">{fields.map(({ key, label, type }) => <label key={key} className="text-sm font-medium text-slate-700"><span>{label}</span><input value={draft[key]} onChange={(event) => { setSaved(false); setDraft({ ...draft, [key]: event.target.value }); }} type={type ?? "text"} step={type === "number" ? "0.01" : undefined} className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /></label>)}</div><div className="mt-7 flex justify-end border-t border-slate-100 pt-6"><button onClick={save} className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700">Save review</button></div></section></div></main></AppShell>;
}
