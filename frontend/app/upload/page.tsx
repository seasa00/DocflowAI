"use client";

import { ChangeEvent, DragEvent, FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "../components/AppShell";
import { LocalDocument, saveDocument } from "../../lib/documents";

const acceptedFiles = ".pdf,.png,.jpg,.jpeg";
const maxBytes = 10 * 1024 * 1024;

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  function chooseFile(nextFile: File | undefined) {
    setError("");
    if (!nextFile) return;
    if (!/\.(pdf|png|jpe?g)$/i.test(nextFile.name)) return setError("Choose a PDF, PNG, or JPEG file.");
    if (nextFile.size > maxBytes) return setError("This file exceeds the 10 MB upload limit.");
    setFile(nextFile);
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (!file) return setError("Select a file before uploading.");
    const form = new FormData(event.currentTarget); form.set("file", file); setIsSubmitting(true);
    try {
      const response = await fetch("/api/documents", { method: "POST", body: form });
      const payload = (await response.json()) as LocalDocument | { detail?: string };
      if (!response.ok) throw new Error("detail" in payload ? payload.detail : "Upload failed. Please try again.");
      saveDocument(payload as LocalDocument); router.push("/documents");
    } catch (uploadError) { setError(uploadError instanceof Error ? uploadError.message : "Upload failed. Please try again."); } finally { setIsSubmitting(false); }
  }
  return <AppShell><main className="mx-auto max-w-3xl px-5 py-12 sm:px-8 sm:py-16"><p className="text-sm font-semibold uppercase tracking-[0.16em] text-blue-700">New document</p><h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">Upload a document</h1><p className="mt-3 max-w-2xl text-slate-600">Send an invoice or other configured document to your secure DocFlow workspace.</p><form onSubmit={submit} className="mt-9 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><label onDragEnter={() => setIsDragging(true)} onDragLeave={() => setIsDragging(false)} onDragOver={(event) => event.preventDefault()} onDrop={(event: DragEvent<HTMLLabelElement>) => { event.preventDefault(); setIsDragging(false); chooseFile(event.dataTransfer.files[0]); }} className={`flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${isDragging ? "border-blue-500 bg-blue-50" : "border-slate-200 bg-slate-50 hover:border-blue-400 hover:bg-blue-50/40"}`}><input aria-label="Choose document" className="sr-only" type="file" accept={acceptedFiles} onChange={(event: ChangeEvent<HTMLInputElement>) => chooseFile(event.target.files?.[0])} /><span className="grid h-12 w-12 place-items-center rounded-full bg-blue-100 text-2xl text-blue-700">↑</span><span className="mt-4 font-semibold text-slate-900">{file ? file.name : "Drop your file here"}</span><span className="mt-1 text-sm text-slate-500">or browse files · PDF, PNG, JPEG · up to 10 MB</span></label><div className="mt-7 grid gap-5 sm:grid-cols-2"><Field label="Owner user ID" name="owner_user_id" placeholder="UUID" required /><Field label="Document type ID" name="document_type_id" placeholder="UUID" required /><Field label="Schema ID" name="schema_id" placeholder="UUID" required /></div><p className="mt-3 text-xs leading-5 text-slate-500">These IDs must refer to an active user, enabled document type, and enabled matching schema in the API.</p>{error && <p role="alert" className="mt-5 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}<div className="mt-7 flex items-center justify-between gap-4 border-t border-slate-100 pt-6"><span className="text-sm text-slate-500">Files are stored privately.</span><button disabled={isSubmitting} className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300" type="submit">{isSubmitting ? "Uploading…" : "Upload document"}</button></div></form></main></AppShell>;
}

function Field({ label, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) { return <label className="block text-sm font-medium text-slate-700"><span>{label}</span><input className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-slate-900 outline-none placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100" {...props} /></label>; }
