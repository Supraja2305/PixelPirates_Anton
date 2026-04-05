/**
 * Policy Changes — empty state until drug param is set.
 * Directory: app/(app)/changes/page.tsx
 */
'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { ArrowLeft, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PolicyChange } from '@/lib/backend';

type ChangeType = 'narrowed' | 'expanded' | 'step' | 'admin';
const TYPE_STYLES: Record<ChangeType, { bg: string; text: string; label: string; border: string }> = {
  narrowed: { bg:'bg-red-100',   text:'text-red-800',   label:'Coverage narrowed',    border:'border-l-restricted'  },
  expanded: { bg:'bg-green-100', text:'text-green-800', label:'Coverage expanded',    border:'border-l-covered'     },
  step:     { bg:'bg-amber-100', text:'text-amber-800', label:'Step therapy added',   border:'border-l-conditional' },
  admin:    { bg:'bg-gray-100',  text:'text-gray-700',  label:'Administrative change',border:'border-l-gray-400'    },
};
const FILTER_OPTIONS: { id: ChangeType; label: string }[] = [
  { id:'narrowed', label:'Coverage narrowed' },
  { id:'expanded', label:'Coverage expanded' },
  { id:'step',     label:'Step therapy added' },
  { id:'admin',    label:'Administrative' },
];

function ChangeCard({ change }: { change: PolicyChange }) {
  const style = TYPE_STYLES[change.type] ?? TYPE_STYLES.admin;
  return (
    <div className={cn('bg-white rounded-lg border border-border-light border-l-4 p-5', style.border)}>
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-3">
        <div className="flex items-center gap-3 flex-wrap">
          <span className={cn('text-xs font-medium px-2.5 py-1 rounded-full', style.bg, style.text)}>{style.label}</span>
          <span className="text-ink font-semibold">{change.payer}</span>
          <span className="text-muted-text text-sm">·</span>
          <span className="text-ink text-sm capitalize">{change.drug}</span>
        </div>
        <span className="text-muted-text text-sm whitespace-nowrap">{change.date}</span>
      </div>
      <p className="text-ink text-sm leading-relaxed mb-3">{change.summary}</p>
      <div className="flex flex-wrap gap-2">
        {change.fields_changed.map(f => (
          <span key={f} className="text-xs text-muted-text bg-off-white border border-border-light px-2 py-0.5 rounded">{f}</span>
        ))}
      </div>
    </div>
  );
}

function EmptyState({ onSearch }: { onSearch: (q: string) => void }) {
  const [q, setQ] = useState('');
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
      <div className="w-16 h-16 rounded-full bg-conditional/10 flex items-center justify-center mb-6">
        <Clock className="w-8 h-8 text-conditional" />
      </div>
      <h2 className="font-serif text-2xl text-ink mb-2">Track policy changes</h2>
      <p className="text-muted-text text-sm max-w-sm mb-8">
        Search a drug name to see recent coverage changes across all payers.
      </p>
      <form onSubmit={e => { e.preventDefault(); if (q.trim()) onSearch(q.trim()); }}
        className="flex gap-2 w-full max-w-md">
        <input value={q} onChange={e => setQ(e.target.value)}
          placeholder="e.g. Rituximab, Adalimumab…"
          className="flex-1 h-11 px-4 bg-white border border-border-light rounded-lg text-ink placeholder:text-hint outline-none focus:border-accent-blue text-sm" />
        <button type="submit"
          className="h-11 px-5 bg-accent-blue text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
          Search
        </button>
      </form>
      <div className="flex flex-wrap gap-2 mt-5 justify-center">
        {['Rituximab','Adalimumab','Bevacizumab','Denosumab'].map(d => (
          <button key={d} onClick={() => onSearch(d)}
            className="px-3 py-1.5 text-sm bg-white text-muted-text border border-border-light rounded-full hover:border-accent-blue hover:text-accent-blue transition-colors">
            {d}
          </button>
        ))}
      </div>
    </div>
  );
}

function ChangesPageInner() {
  const params    = useSearchParams();
  const router    = useRouter();
  const drugParam = params.get('drug');

  const [all,     setAll]     = useState<PolicyChange[]>([]);
  const [loading, setLoading] = useState(false);
  const [active,  setActive]  = useState<Set<ChangeType>>(new Set());

  useEffect(() => {
    if (!drugParam) { setAll([]); return; }
    setLoading(true);
    const url = `/api/changes?drug=${encodeURIComponent(drugParam)}`;
    fetch(url).then(r => r.json()).then(d => setAll(d.changes ?? [])).catch(() => setAll([])).finally(() => setLoading(false));
  }, [drugParam]);

  const toggle = (id: ChangeType) =>
    setActive(p => { const s = new Set(p); s.has(id) ? s.delete(id) : s.add(id); return s; });

  const filtered  = active.size === 0 ? all : all.filter(c => active.has(c.type));
  const navigate  = (drug: string) => router.push(`/changes?drug=${encodeURIComponent(drug)}`);

  if (!drugParam && !loading) {
    return <div className="w-full max-w-[960px] mx-auto"><EmptyState onSearch={navigate} /></div>;
  }

  return (
    <div className="w-full max-w-[960px] mx-auto px-6 pt-8 pb-16">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push(`/results?drug=${encodeURIComponent(drugParam ?? '')}`)}
            className="flex items-center gap-1.5 text-muted-text hover:text-ink text-sm transition-colors">
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <h1 className="font-serif text-2xl text-ink capitalize">
            Policy changes — <span className="text-accent-blue">{drugParam}</span>
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          {FILTER_OPTIONS.map(f => {
            const style = TYPE_STYLES[f.id]; const isActive = active.has(f.id);
            return (
              <button key={f.id} onClick={() => toggle(f.id)} aria-pressed={isActive}
                className={cn('px-3 py-1.5 text-sm font-medium rounded-full border transition-colors',
                  isActive ? `${style.bg} ${style.text} border-transparent` : `bg-white ${style.text} border-border-light hover:border-current`)}>
                {f.label}
              </button>
            );
          })}
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col gap-4">
          {[1,2,3].map(i => <div key={i} className="h-28 bg-white border border-border-light rounded-lg animate-pulse" />)}
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {filtered.length > 0
            ? filtered.map(c => <ChangeCard key={c.id} change={c} />)
            : <p className="text-center py-12 text-muted-text">No policy changes found for {drugParam}.</p>
          }
        </div>
      )}
    </div>
  );
}

export default function ChangesPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-[60vh]"><div className="w-6 h-6 rounded-full border-2 border-accent-blue border-t-transparent animate-spin" /></div>}>
      <ChangesPageInner />
    </Suspense>
  );
}
