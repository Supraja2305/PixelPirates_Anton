/**
 * Drug Results Page
 * Empty state when no drug selected. Data only loads after a search.
 * Directory: app/(app)/results/page.tsx
 */
'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Search, ArrowRight, BarChart2, Clock, Pill } from 'lucide-react';
import { cn } from '@/lib/utils';
import { StatusTag } from '@/components/ui/status-tag';
import { GraphRAGVisualization } from '@/components/graph-rag-visualization';
import { PolicyDNAChart } from '@/components/policy-dna-chart';
import type { DrugResult, PayerCoverage } from '@/lib/backend';

const STATUS_MAP: Record<string, 'covered' | 'conditional' | 'restricted'> = {
  covered: 'covered', pa_required: 'conditional', step_therapy: 'conditional',
  not_covered: 'restricted', conditional: 'conditional', restricted: 'restricted',
};
const SCORE_COLOR = (n: number) =>
  n >= 70 ? 'text-covered' : n >= 45 ? 'text-conditional' : 'text-restricted';

// ─── Payer card ───────────────────────────────────────────────────────────────

function PayerCard({ payer }: { payer: PayerCoverage }) {
  const status    = STATUS_MAP[payer.status] ?? 'conditional';
  const borderTop = status === 'covered' ? 'border-t-covered'
                  : status === 'conditional' ? 'border-t-conditional'
                  : 'border-t-restricted';
  return (
    <div className={cn('bg-white rounded-lg border border-border-light overflow-hidden border-t-[3px]', borderTop, 'hover:shadow-sm transition-shadow')}>
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-light">
        <h3 className="font-semibold text-ink">{payer.payer}</h3>
        <StatusTag status={status} />
      </div>
      <div className="px-5 py-4 grid gap-3 text-sm">
        {([
          ['Prior auth',   payer.prior_auth,   payer.prior_auth === 'Required'],
          ['Step therapy', payer.step_therapy,  parseInt(payer.step_therapy) > 1],
          ['Indications',  payer.indications,  false],
          ['Site of care', payer.site_of_care, false],
        ] as [string, string, boolean][]).map(([label, value, warn]) => (
          <div key={label} className="flex justify-between gap-4">
            <span className="text-muted-text shrink-0">{label}</span>
            <span className={cn('font-medium text-right', warn ? 'text-restricted' : 'text-ink')}>{value}</span>
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between px-5 py-3 bg-off-white/50 border-t border-border-light">
        <span className="text-hint text-sm">{payer.effective_date}{payer.updated ? ' · Updated' : ''}</span>
        <span className={cn('font-semibold', SCORE_COLOR(payer.score))}>Score {payer.score}</span>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-lg border border-border-light overflow-hidden animate-pulse">
      <div className="px-5 py-4 border-b border-border-light flex justify-between">
        <div className="h-5 w-36 bg-gray-100 rounded" />
        <div className="h-5 w-20 bg-gray-100 rounded" />
      </div>
      <div className="px-5 py-4 grid gap-3">
        {[1,2,3,4].map(i => (
          <div key={i} className="flex justify-between">
            <div className="h-4 w-20 bg-gray-100 rounded" />
            <div className="h-4 w-32 bg-gray-100 rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({ onSearch }: { onSearch: (q: string) => void }) {
  const [q, setQ] = useState('');
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center">
      <div className="w-16 h-16 rounded-full bg-accent-blue/10 flex items-center justify-center mb-6">
        <Pill className="w-8 h-8 text-accent-blue" />
      </div>
      <h2 className="font-serif text-2xl text-ink mb-2">Search for a drug</h2>
      <p className="text-muted-text text-sm max-w-sm mb-8">
        Enter a drug name or J-code to see payer coverage, prior auth requirements, and access scores.
      </p>
      <form onSubmit={e => { e.preventDefault(); if (q.trim()) onSearch(q.trim()); }}
        className="flex gap-2 w-full max-w-md">
        <div className="flex-1 flex items-center bg-white rounded-lg border border-border-light focus-within:border-accent-blue px-3 h-11">
          <Search className="w-4 h-4 text-muted-text mr-2 shrink-0" />
          <input value={q} onChange={e => setQ(e.target.value)}
            placeholder="e.g. Rituximab, Adalimumab, J9312…"
            className="flex-1 bg-transparent text-ink placeholder:text-hint outline-none text-sm" />
        </div>
        <button type="submit"
          className="h-11 px-5 bg-accent-blue text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
          Search
        </button>
      </form>
      <div className="flex flex-wrap items-center gap-2 mt-5 justify-center">
        <span className="text-hint text-sm">Try:</span>
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

// ─── Main ─────────────────────────────────────────────────────────────────────

function ResultsPageInner() {
  const params    = useSearchParams();
  const router    = useRouter();
  const drugParam = params.get('drug'); // null = empty state

  const [data,    setData]    = useState<DrugResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  useEffect(() => {
    if (!drugParam) { setData(null); return; }
    setLoading(true); setError('');
    fetch(`/api/drug?name=${encodeURIComponent(drugParam)}`)
      .then(r => r.ok ? r.json() : Promise.reject('Not found'))
      .then(setData)
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, [drugParam]);

  const navigate = (drug: string) =>
    router.push(`/results?drug=${encodeURIComponent(drug)}`);

  // ── Empty state ─────────────────────────────────────────────────────────────
  if (!drugParam && !loading) {
    return (
      <div className="w-full max-w-[1200px] mx-auto">
        <EmptyState onSearch={navigate} />
      </div>
    );
  }

  const drug = data?.drug ?? drugParam ?? '';

  return (
    <div className="w-full max-w-[1200px] mx-auto px-6 pt-8 pb-16">

      {/* ── Drug header ─────────────────────────────────────────── */}
      {loading && (
        <div className="mb-8 space-y-2">
          <div className="h-9 w-52 bg-gray-100 rounded animate-pulse" />
          <div className="h-4 w-80 bg-gray-100 rounded animate-pulse" />
        </div>
      )}
      {!loading && data && (
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2 flex-wrap">
            <h1 className="font-serif text-3xl text-ink capitalize">{data.drug}</h1>
            {data.j_code && <span className="px-2.5 py-1 bg-gray-100 text-ink font-mono text-sm rounded">{data.j_code}</span>}
          </div>
          {(data.aliases.length > 0 || data.drug_class) && (
            <p className="text-muted-text text-sm">
              {data.aliases.length > 0 && `Also known as: ${data.aliases.join(' · ')}`}
              {data.drug_class && ` · ${data.drug_class}`}
            </p>
          )}
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-restricted/20 rounded-lg px-5 py-4 text-restricted text-sm mb-8">
          {error} — try a different drug name or J-code.
        </div>
      )}

      {/* ── Knowledge graph ─────────────────────────────────────── */}
      {!loading && !error && <div className="mb-10"><GraphRAGVisualization /></div>}

      {/* ── Payer cards ─────────────────────────────────────────── */}
      {(loading || data) && (
        <>
          <h2 className="font-serif text-xl text-ink mb-4">Payer coverage</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
            {loading
              ? [1,2,3,4].map(i => <SkeletonCard key={i} />)
              : data?.payers.map((p, i) => (
                  <div key={p.payer} className="animate-in fade-in slide-in-from-bottom-2"
                    style={{ animationDelay: `${i * 80}ms`, animationFillMode: 'both' }}>
                    <PayerCard payer={p} />
                  </div>
                ))
            }
          </div>
        </>
      )}

      {/* ── Policy DNA ──────────────────────────────────────────── */}
      {!loading && data && <PolicyDNAChart />}

      {/* ── Next steps ──────────────────────────────────────────── */}
      {!loading && !error && data && (
        <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <button onClick={() => router.push(`/compare?drug=${encodeURIComponent(drug)}`)}
            className="flex items-center justify-between bg-white border border-border-light rounded-lg px-5 py-4 hover:border-accent-blue hover:shadow-sm transition-all group">
            <div className="flex items-center gap-3">
              <BarChart2 className="w-5 h-5 text-accent-blue" />
              <div className="text-left">
                <p className="font-semibold text-ink">Compare payers</p>
                <p className="text-muted-text text-sm">Side-by-side table for {drug}</p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-hint group-hover:text-accent-blue transition-colors" />
          </button>
          <button onClick={() => router.push(`/changes?drug=${encodeURIComponent(drug)}`)}
            className="flex items-center justify-between bg-white border border-border-light rounded-lg px-5 py-4 hover:border-accent-blue hover:shadow-sm transition-all group">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-conditional" />
              <div className="text-left">
                <p className="font-semibold text-ink">Policy changes</p>
                <p className="text-muted-text text-sm">Recent updates for {drug}</p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-hint group-hover:text-accent-blue transition-colors" />
          </button>
        </div>
      )}
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-[60vh]"><div className="w-6 h-6 rounded-full border-2 border-accent-blue border-t-transparent animate-spin" /></div>}>
      <ResultsPageInner />
    </Suspense>
  );
}
