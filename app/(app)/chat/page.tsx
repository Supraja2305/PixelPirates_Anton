/**
 * AI Chat Page
 * - Removed "Try:" suggestion chips from input bar
 * - When user types a drug name, shows inline coverage cards in chat
 * - Upload sidebar unchanged
 * Directory: app/(app)/chat/page.tsx
 */
'use client';

import { useState, useRef, useCallback } from 'react';
import { Upload, FileText, Loader2, X, AlertCircle, CheckCircle2, BarChart2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { ChatMessage } from '@/components/chat-message';
import { StatusTag } from '@/components/ui/status-tag';
import type { ChatMessage as ChatMessageType } from '@/types';

// Local extension — adds optional _drug tag to AI messages for inline cards.
// Using a separate type keeps ChatMessage in @/types clean.
type ExtendedMessage = ChatMessageType & { _drug?: string };
import type { DrugResult, PayerCoverage } from '@/lib/backend';

// ─── Types ────────────────────────────────────────────────────────────────────

type ExtractedDrug = Record<string, unknown>;
type UploadStep    = 'idle' | 'reading' | 'analyzing' | 'done' | 'error';

// ─── Drug coverage inline card ────────────────────────────────────────────────

const STATUS_MAP: Record<string, 'covered' | 'conditional' | 'restricted'> = {
  covered: 'covered', pa_required: 'conditional', step_therapy: 'conditional',
  not_covered: 'restricted', conditional: 'conditional', restricted: 'restricted',
};

function InlineDrugCard({ data, onCompare }: { data: DrugResult; onCompare: () => void }) {
  return (
    <div className="mt-3 border border-border-light rounded-xl overflow-hidden bg-white">
      {/* header */}
      <div className="flex items-center justify-between px-4 py-3 bg-off-white border-b border-border-light">
        <div>
          <span className="font-semibold text-ink capitalize">{data.drug}</span>
          {data.j_code && <span className="ml-2 font-mono text-xs text-muted-text">{data.j_code}</span>}
          {data.drug_class && <span className="ml-2 text-xs text-muted-text">{data.drug_class}</span>}
        </div>
        <button
          onClick={onCompare}
          className="flex items-center gap-1.5 text-xs text-accent-blue hover:underline"
        >
          <BarChart2 className="w-3.5 h-3.5" /> Full comparison
        </button>
      </div>
      {/* payer rows */}
      <div className="divide-y divide-border-light">
        {data.payers.map((p: PayerCoverage) => {
          const status = STATUS_MAP[p.status] ?? 'conditional';
          return (
            <div key={p.payer} className="flex items-center gap-3 px-4 py-2.5 text-sm">
              <span className="w-32 text-ink font-medium shrink-0">{p.payer.replace('UnitedHealthcare','UHC')}</span>
              <StatusTag status={status} />
              <span className="text-muted-text text-xs ml-auto">{p.prior_auth === 'Required' ? '⚠ PA required' : '✓ No PA'}</span>
              <span className={cn('font-semibold text-xs w-14 text-right', p.score >= 70 ? 'text-covered' : p.score >= 45 ? 'text-conditional' : 'text-restricted')}>
                {p.score}/100
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Upload progress ──────────────────────────────────────────────────────────

const STEPS = [
  { key: 'reading',   label: 'Reading file' },
  { key: 'analyzing', label: 'Analyzing policy' },
  { key: 'done',      label: 'Complete' },
];

function UploadProgress({ step, fileName }: { step: UploadStep; fileName: string }) {
  if (step === 'idle' || step === 'error') return null;
  return (
    <div className="mx-4 mt-3 bg-off-white border border-border-light rounded-lg p-3">
      <p className="text-xs text-muted-text truncate mb-2">{fileName}</p>
      <div className="flex flex-col gap-1.5">
        {STEPS.map(({ key, label }) => {
          const order   = ['reading','analyzing','done'];
          const cur     = order.indexOf(step);
          const idx     = order.indexOf(key);
          const isDone  = idx < cur || step === 'done';
          const isActive = key === step;
          return (
            <div key={key} className="flex items-center gap-2">
              <div className={cn('w-4 h-4 rounded-full flex items-center justify-center shrink-0',
                isDone ? 'bg-covered' : isActive ? 'bg-accent-blue' : 'bg-border-light')}>
                {isDone   ? <CheckCircle2 className="w-3 h-3 text-white" />
                 : isActive ? <Loader2 className="w-2.5 h-2.5 text-white animate-spin" />
                 : <span className="w-1.5 h-1.5 rounded-full bg-muted-text/30" />}
              </div>
              <span className={cn('text-xs', isDone ? 'text-covered line-through' : isActive ? 'text-ink font-medium' : 'text-hint')}>
                {label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Status badge ──────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { dot: string; label: string; badge: string }> = {
  covered:      { dot: 'bg-covered',     label: 'Covered',     badge: 'bg-green-50 text-covered border-covered/30' },
  pa_required:  { dot: 'bg-conditional', label: 'PA required', badge: 'bg-amber-50 text-conditional border-conditional/30' },
  step_therapy: { dot: 'bg-conditional', label: 'Step therapy',badge: 'bg-amber-50 text-conditional border-conditional/30' },
  not_covered:  { dot: 'bg-restricted',  label: 'Not covered', badge: 'bg-red-50 text-restricted border-restricted/30' },
  unknown:      { dot: 'bg-hint',        label: 'Unknown',     badge: 'bg-gray-50 text-muted-text border-border-light' },
};

function PolicyCard({ drug }: { drug: ExtractedDrug }) {
  const cfg    = STATUS_CONFIG[String(drug.coverage_status)] ?? STATUS_CONFIG.unknown;
  const brands = Array.isArray(drug.brand_names) ? (drug.brand_names as string[]).join(', ') : null;
  return (
    <div className="bg-white border border-border-light rounded-lg p-3 text-sm relative group hover:border-muted-text transition-colors">
      <div className="flex items-start gap-2 mb-1.5 pr-4">
        <span className={cn('w-2 h-2 rounded-full shrink-0 mt-1', cfg.dot)} />
        <div className="min-w-0">
          <p className="font-semibold text-ink truncate capitalize">{String(drug.drug_name ?? 'Unknown drug')}</p>
          {brands && <p className="text-hint text-xs truncate">{brands}</p>}
        </div>
      </div>
      <div className="pl-4 flex items-center gap-2 flex-wrap">
        <span className={cn('text-xs px-2 py-0.5 rounded-full border font-medium', cfg.badge)}>{cfg.label}</span>
        {drug.j_code && <span className="text-xs font-mono text-muted-text">{String(drug.j_code)}</span>}
      </div>
      <p className="pl-4 mt-1.5 text-xs text-muted-text truncate">{String(drug.payer ?? 'Unknown payer')}</p>
    </div>
  );
}

// ─── Welcome screen ───────────────────────────────────────────────────────────

function WelcomePrompt({ onSuggestion }: { onSuggestion: (s: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full py-16 px-8 text-center">
      <div className="w-14 h-14 rounded-full bg-accent-blue/10 flex items-center justify-center mb-5">
        <span className="text-accent-blue text-xl font-bold">Rx</span>
      </div>
      <h2 className="font-serif text-xl text-ink mb-2">Medical benefit drug policy assistant</h2>
      <p className="text-muted-text text-sm max-w-sm">
        Upload policy PDFs from the sidebar, then ask questions about coverage, prior auth, and step therapy.
        Or type a drug name to see instant coverage data.
      </p>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

// Detect if a message is asking about a specific drug
const KNOWN_DRUGS = ['rituximab','adalimumab','bevacizumab','denosumab','pembrolizumab','metformin','lisinopril','atorvastatin'];
const DRUG_ALIASES: Record<string,string> = {
  humira:'adalimumab', rituxan:'rituximab', avastin:'bevacizumab',
  keytruda:'pembrolizumab', prolia:'denosumab', xgeva:'denosumab',
};

function extractDrugFromMessage(msg: string): string | null {
  const lower = msg.toLowerCase();
  for (const [alias, canonical] of Object.entries(DRUG_ALIASES)) {
    if (lower.includes(alias)) return canonical;
  }
  for (const drug of KNOWN_DRUGS) {
    if (lower.includes(drug)) return drug;
  }
  return null;
}

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<ExtendedMessage[]>([]);
  const [input, setInput] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [drugCards, setDrugCards] = useState<Map<string, DrugResult>>(new Map());

  const [loadedDrugs, setLoadedDrugs]         = useState<ExtractedDrug[]>([]);
  const [uploadStep, setUploadStep]             = useState<UploadStep>('idle');
  const [uploadingFileName, setUploadingFile]   = useState('');
  const [uploadBanner, setUploadBanner]         = useState<{text:string; type:'success'|'error'}|null>(null);
  const [isDragging, setIsDragging]             = useState(false);

  const fileInputRef  = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // ── Upload ──────────────────────────────────────────────────────────────────
  const uploadFile = useCallback(async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!['pdf','png','jpg','jpeg','docx'].includes(ext)) {
      setUploadBanner({ text: `Unsupported: .${ext}`, type: 'error' }); return;
    }
    setUploadingFile(file.name); setUploadBanner(null); setUploadStep('reading');
    await new Promise(r => setTimeout(r, 300));
    setUploadStep('analyzing');
    const fd = new FormData(); fd.append('file', file);
    try {
      const res  = await fetch('/api/upload', { method: 'POST', body: fd });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      const incoming: ExtractedDrug[] = Array.isArray(data.policies) ? data.policies : data.policy ? [data.policy] : [];
      if (!incoming.length) throw new Error('No drug data extracted');
      setLoadedDrugs(p => [...p, ...incoming]);
      setUploadStep('done');
      setUploadBanner({ text: `${incoming.length} drug${incoming.length > 1 ? 's' : ''} extracted from ${file.name}`, type: 'success' });
      setTimeout(() => setUploadStep('idle'), 2000);
    } catch (e) {
      setUploadStep('error');
      setUploadBanner({ text: e instanceof Error ? e.message : 'Upload failed', type: 'error' });
    }
  }, []);

  // ── Chat ────────────────────────────────────────────────────────────────────
  const handleSubmit = async (question: string) => {
    const q = question.trim();
    if (!q || isAsking) return;

    setMessages(p => [...p, { id: Date.now().toString(), role: 'user', content: q }]);
    setInput('');
    setIsAsking(true);
    setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);

    // Check if message references a known drug → fetch coverage data in parallel
    const detectedDrug = extractDrugFromMessage(q);
    if (detectedDrug && !drugCards.has(detectedDrug)) {
      fetch(`/api/drug?name=${detectedDrug}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d) setDrugCards(m => new Map(m).set(detectedDrug, d)); })
        .catch(() => null);
    }

    try {
      const res  = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, policies: loadedDrugs }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      const aiMsg: ChatMessageType = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: data.answer,
        ...(data.source_citation && { citation: { source: 'Policy document', quote: data.source_citation } }),
      };
      setMessages(p => [...p, aiMsg]);

      // Tag AI message with detected drug so InlineDrugCard renders below it
      if (detectedDrug) {
        setMessages(p => p.map(m => m.id === aiMsg.id ? { ...m, _drug: detectedDrug } : m));
      }
    } catch (e) {
      setMessages(p => [...p, { id: (Date.now()+1).toString(), role: 'ai', content: `⚠ ${e instanceof Error ? e.message : 'Error'}` }]);
    } finally {
      setIsAsking(false);
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  };

  const isUploading = uploadStep === 'reading' || uploadStep === 'analyzing';
  const hasDrugs    = loadedDrugs.length > 0;

  return (
    <div className="flex h-[calc(100vh-56px)] overflow-hidden">

      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <aside className="w-[280px] shrink-0 bg-white border-r border-border-light flex flex-col">
        <div className="p-4 border-b border-border-light">
          <button
            onClick={() => fileInputRef.current?.click()} disabled={isUploading}
            className="w-full flex items-center justify-center gap-2 bg-navy text-off-white font-semibold text-sm py-2.5 px-4 rounded-lg hover:bg-navy-light transition-colors disabled:opacity-60"
          >
            {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            {isUploading ? 'Processing…' : 'Upload PDF, Word or PNG'}
          </button>
          <input ref={fileInputRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.docx" multiple className="hidden"
            onChange={e => { Array.from(e.target.files??[]).forEach(uploadFile); e.target.value=''; }} />
        </div>

        <div
          onDrop={e => { e.preventDefault(); setIsDragging(false); Array.from(e.dataTransfer.files).forEach(uploadFile); }}
          onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onClick={() => !isUploading && fileInputRef.current?.click()}
          className={cn('mx-4 mt-3 border-2 border-dashed rounded-lg p-4 text-center text-xs cursor-pointer transition-colors',
            isDragging ? 'border-accent-blue bg-blue-50 text-accent-blue' : 'border-border-light text-hint hover:border-muted-text')}
        >
          or drag &amp; drop here
        </div>

        {uploadStep !== 'idle' && uploadStep !== 'error' && (
          <UploadProgress step={uploadStep} fileName={uploadingFileName} />
        )}
        {uploadBanner && (
          <div className={cn('mx-4 mt-2 text-xs flex items-start gap-1.5 px-2.5 py-2 rounded-md border',
            uploadBanner.type === 'success' ? 'text-covered bg-green-50 border-covered/20' : 'text-restricted bg-red-50 border-restricted/20')}>
            {uploadBanner.type === 'success' ? <CheckCircle2 className="w-3 h-3 mt-0.5 shrink-0" /> : <AlertCircle className="w-3 h-3 mt-0.5 shrink-0" />}
            {uploadBanner.text}
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-2">
          {hasDrugs ? (
            <>
              <p className="text-xs text-muted-text font-medium uppercase tracking-wide mb-1">
                Loaded ({loadedDrugs.length})
              </p>
              {loadedDrugs.map((d, i) => (
                <div key={i} className="relative group">
                  <PolicyCard drug={d} />
                  <button onClick={() => setLoadedDrugs(p => p.filter((_,idx) => idx !== i))}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 text-muted-text hover:text-restricted transition-opacity">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-center text-hint">
              <FileText className="w-8 h-8 opacity-30" />
              <p className="text-xs leading-relaxed">Upload policy documents to begin</p>
            </div>
          )}
        </div>
      </aside>

      {/* ── Chat area ────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col bg-off-white overflow-hidden">
        <div className="px-6 py-4 border-b border-border-light bg-white shrink-0 flex items-center justify-between">
          <h1 className="font-serif text-xl text-ink">AI policy assistant</h1>
          {hasDrugs && (
            <span className="text-xs text-muted-text bg-off-white border border-border-light rounded-full px-3 py-1">
              {loadedDrugs.length} drug{loadedDrugs.length > 1 ? 's' : ''} loaded
            </span>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 ? (
            <WelcomePrompt onSuggestion={handleSubmit} />
          ) : (
            <div className="max-w-3xl mx-auto">
              <div className="bg-white rounded-lg border border-border-light p-6">
                <div className="flex flex-col gap-6">
                  {messages.map(message => (
                    <div key={message.id}>
                      <ChatMessage message={message} />
                      {/* Inline drug coverage card appears below AI message */}
                      {message.role === 'ai' && message._drug && (
                        (() => {
                          const d = drugCards.get(message._drug!);
                          return d ? (
                            <InlineDrugCard
                              data={d}
                              onCompare={() => router.push(`/compare?drug=${d.drug}`)}
                            />
                          ) : null;
                        })()
                      )}
                    </div>
                  ))}
                  {isAsking && (
                    <div className="flex gap-3">
                      <div className="w-8 h-8 rounded-full bg-accent-blue flex items-center justify-center shrink-0">
                        <span className="text-white text-xs font-bold">Rx</span>
                      </div>
                      <div className="bg-white border-l-2 border-l-accent-blue rounded-lg px-4 py-3">
                        <div className="flex gap-1 items-center">
                          {[0,150,300].map(d => (
                            <span key={d} className="w-2 h-2 bg-muted-text rounded-full animate-bounce" style={{ animationDelay: `${d}ms` }} />
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input — NO suggestion chips */}
        <div className="border-t border-border-light bg-white px-6 py-4 shrink-0">
          <div className="max-w-3xl mx-auto">
            {!hasDrugs && (
              <p className="text-xs text-conditional mb-3 flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" />
                Upload a policy document or type a drug name for live coverage data.
              </p>
            )}
            <form onSubmit={e => { e.preventDefault(); handleSubmit(input); }} className="flex gap-3">
              <input
                type="text" value={input} onChange={e => setInput(e.target.value)}
                placeholder={hasDrugs ? 'Ask about coverage, prior auth, step therapy…' : 'Ask a question or type a drug name (e.g. rituximab)…'}
                className="flex-1 h-11 px-4 bg-off-white border border-border-light rounded-lg text-ink placeholder:text-hint outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue text-sm"
                disabled={isAsking}
              />
              <button type="submit" disabled={!input.trim() || isAsking}
                className={cn('h-11 px-5 rounded-lg font-medium text-sm flex items-center gap-2 transition-colors',
                  input.trim() && !isAsking ? 'bg-accent-blue text-white hover:bg-blue-700' : 'bg-gray-100 text-gray-400 cursor-not-allowed')}>
                {isAsking ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Send'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}