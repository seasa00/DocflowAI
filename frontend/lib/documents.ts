export type ReviewDraft = {
  supplier_name: string;
  invoice_number: string;
  issue_date: string;
  due_date: string;
  currency: string;
  subtotal: string;
  tax_amount: string;
  total_amount: string;
};

export type LocalDocument = {
  id: string;
  owner_user_id: string;
  document_type_id: string;
  schema_id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  processing_status: string;
  created_at: string;
  review?: ReviewDraft;
};

const storageKey = "docflow-documents";

export const emptyReview: ReviewDraft = { supplier_name: "", invoice_number: "", issue_date: "", due_date: "", currency: "", subtotal: "", tax_amount: "", total_amount: "" };

export function readDocuments(): LocalDocument[] {
  try { const stored = window.localStorage.getItem(storageKey); return stored ? (JSON.parse(stored) as LocalDocument[]) : []; } catch { return []; }
}

export function saveDocument(document: LocalDocument) {
  const documents = readDocuments().filter(({ id }) => id !== document.id);
  window.localStorage.setItem(storageKey, JSON.stringify([document, ...documents]));
}

export function updateReview(id: string, review: ReviewDraft) {
  window.localStorage.setItem(storageKey, JSON.stringify(readDocuments().map((document) => document.id === id ? { ...document, review } : document)));
}

export function formatSize(bytes: number) { return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`; }

export function exportDocument(document: LocalDocument) {
  const review = document.review ?? emptyReview;
  const columns = ["document_id", "filename", "status", ...Object.keys(review)];
  const values = [document.id, document.original_filename, document.processing_status, ...Object.values(review)];
  const csv = `${columns.join(",")}\n${values.map((value) => `"${value.replaceAll('"', '""')}"`).join(",")}\n`;
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = window.document.createElement("a");
  link.href = url; link.download = `${document.original_filename.replace(/\.[^.]+$/, "") || "document"}.csv`; link.click(); URL.revokeObjectURL(url);
}
