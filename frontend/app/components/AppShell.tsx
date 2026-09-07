import Link from "next/link";

export function AppShell({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen bg-slate-50"><header className="border-b border-slate-200 bg-white"><div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8"><Link href="/upload" className="flex items-center gap-3 font-semibold text-slate-950"><span className="grid h-9 w-9 place-items-center rounded-lg bg-blue-600 text-lg text-white">D</span><span>DocFlow AI</span></Link><nav aria-label="Main navigation" className="flex items-center gap-1 text-sm font-medium"><Link className="rounded-md px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-950" href="/upload">Upload</Link><Link className="rounded-md px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-950" href="/documents">Documents</Link></nav></div></header>{children}</div>;
}
