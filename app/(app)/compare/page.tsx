/**
 * Compare Payers — empty state until drug is in URL param.
 * Directory: app/(app)/compare/page.tsx
 */
'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { ArrowLeft, Clock, BarChart2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { StatusTag } from '@/components/ui/status-tag';
import type { DrugResult, PayerCoverage } from '@/lib/backend';

const ROWS: { key: keyof PayerCoverage; label: string }[] = [
  { key: 'status',         label: 'Status'         },
  { key: 'prior_auth',     label: 'Prior auth'     },
  { key: 'step_therapy',   label: 'Step therapy'   },
  { key: 'indications',    label: 'Indications'    },
  { key: 'site_of_care',   label: 'Site of care'   },
  { key: 'effective_date', label: 'Effective date' },
  { key: 'score',          label: 'Access score'   },
];
const STATUS_MAP: Record<string, 'covered' | 'conditional' | 'restricted'> = {
  covered: 'covered', pa_required: 'conditional', step_therapy: 'conditional',
  not_covered: 'restricted', conditional: 'conditional', restricted: 'restricted',
};
const scoreColor = (n: number) =>
  n >= 70 ? 'text-covered' : n >= 45 ? 'text-conditional' : 'text-restricted';
const isHighlighted = (key: string, val: unknown) =>
  (key === 'prior_auth' && val === 'Required') || (key === 'step_therapy' && parseInt(String(val)) > 1);

function EmptyState({ onSearch }: { onSearch: (q: string) => void }) {
  const [q, setQ] = useState('');
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
      <div className="w-16 h-16 rounded-full bg-accent-blue/10 flex items-center justify-center mb-6">
        <BarChart2 className="w-8 h-8 text-accent-blue" />
      </div>
      <h2 className="font-serif text-2xl text-ink mb-2">Compare payer policies</h2>
      <p className="text-muted-text text-sm max-w-sm mb-8">
        Search a drug to see a side-by-side comparison of how each payer covers it.
      </p>
      <form onSubmit={e => { e.preventDefault(); if (q.trim()) onSearch(q.trim()); }}
        className="flex gap-2 w-full max-w-md">
        <input value={q} onChange={e => setQ(e.target.value)}
          placeholder="e.g. Rituximab, Adalimumab…"
          className="flex-1 h-11 px-4 bg-white border border-border-light rounded-lg text-ink placeholder:text-hint outline-none focus:border-accent-blue text-sm" />
        <button type="submit"
          className="h-11 px-5 bg-accent-blue text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
          Compare
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

export default function ComparePage() {
  const params    = useSearchParams();
  const router    = useRouter();
  const drugParam = params.get('drug');

  const [data,    setData]    = useState<DrugResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  useEffect(() => {
    if (!drugParam) { setData(null); return; }
    setLoading(true); setError('');
    fetch(`/api/compare?drug=${encodeURIComponent(drugParam)}`)
      .then(r => r.ok ? r.json() : Promise.reject('Not found'))
      .then(setData)
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, [drugParam]);

  const navigate = (drug: string) => router.push(`/compare?drug=${encodeURIComponent(drug)}`);
  const drug     = data?.drug ?? drugParam ?? '';

  if (!drugParam && !loading) {
    return <div className="w-full max-w-[1200px] mx-auto"><EmptyState onSearch={navigate} /></div>;
  }

  return (
    <div className="w-full max-w-[1200px] mx-auto px-6 pt-8 pb-16">
      <div className="flex items-center gap-4 mb-8 flex-wrap">
        <button onClick={() => router.push(`/results?drug=${encodeURIComponent(drugParam ?? '')}`)}
          className="flex items-center gap-1.5 text-muted-text hover:text-ink text-sm transition-colors shrink-0">
          <ArrowLeft className="w-4 h-4" /> Back to results
        </button>
        <h1 className="font-serif text-2xl text-ink capitalize flex-1">
          {drug} — side-by-side payer comparison
        </h1>
        <button onClick={() => router.push(`/changes?drug=${encodeURIComponent(drugParam ?? '')}`)}
          className="flex items-center gap-1.5 text-sm text-muted-text hover:text-ink border border-border-light rounded-lg px-3 py-1.5 hover:border-muted-text transition-colors shrink-0">
          <Clock className="w-4 h-4" /> Policy changes
        </button>
      </div>

      {loading && <div className="bg-white rounded-lg border border-border-light p-8 text-center text-muted-text text-sm animate-pulse">Loading comparison…</div>}
      {error   && <div className="bg-red-50 border border-restricted/20 rounded-lg px-5 py-4 text-restricted text-sm">{error}</div>}

      {!loading && !error && data && (
        <>
          <div className="bg-white rounded-lg border border-border-light overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px]">
                <thead>
                  <tr className="bg-navy">
                    <th className="text-left py-4 px-5 text-off-white/70 font-medium text-sm w-[150px]">Criteria</th>
                    {data.payers.map(p => (
                      <th key={p.payer} className="text-center py-4 px-5 text-off-white font-semibold text-sm">
                        {p.payer.replace('UnitedHealthcare','UHC')}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {ROWS.map((row, ri) => (
                    <tr key={row.key} className={cn('border-b border-border-light last:border-b-0', ri % 2 === 1 ? 'bg-off-white/30' : 'bg-white')}>
                      <td className="py-4 px-5 text-muted-text text-sm">{row.label}</td>
                      {data.payers.map(p => {
                        const val = p[row.key];
                        if (row.key === 'status') return (
                          <td key={p.payer} className="py-4 px-5 text-center">
                            <StatusTag status={STATUS_MAP[String(val)] ?? 'conditional'} />
                          </td>
                        );
                        if (row.key === 'score') {
                          const n = Number(val);
                          return <td key={p.payer} className={cn('py-4 px-5 text-center font-bold text-lg', scoreColor(n))}>{n}/100</td>;
                        }
                        return (
                          <td key={p.payer} className={cn('py-4 px-5 text-center text-sm font-medium', isHighlighted(row.key, val) ? 'text-restricted' : 'text-ink')}>
                            {String(val ?? '—')}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <p className="mt-6 text-muted-text text-sm">
            Access score (0–100): higher = more patient-friendly. Composite of PA burden, step therapy, indication breadth, and site of care flexibility.
          </p>
        </>
      )}
    </div>
  );
}