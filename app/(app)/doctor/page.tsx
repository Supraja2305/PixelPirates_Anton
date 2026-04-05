/**
 * Doctor View — clinical coverage summary for a drug.
 * Accessed via the green "Doctor view" button in the navbar.
 * Reads ?drug= from URL; empty state if no drug selected.
 * Directory: app/(app)/doctor/page.tsx
 */
'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Stethoscope, CheckCircle2, AlertCircle, XCircle, ChevronDown, ChevronUp, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { DrugResult, PayerCoverage } from '@/lib/backend';

const STATUS_MAP: Record<string, 'covered' | 'conditional' | 'restricted'> = {
  covered: 'covered', pa_required: 'conditional', step_therapy: 'conditional',
  not_covered: 'restricted', conditional: 'conditional', restricted: 'restricted',
};

const STATUS_CONFIG = {
  covered:     { icon: CheckCircle2, label: 'Covered',     bg: 'bg-green-50',  border: 'border-covered/30',     text: 'text-covered',     iconColor: 'text-covered' },
  conditional: { icon: AlertCircle,  label: 'PA Required', bg: 'bg-amber-50',  border: 'border-conditional/30', text: 'text-conditional', iconColor: 'text-conditional' },
  restricted:  { icon: XCircle,      label: 'Restricted',  bg: 'bg-red-50',    border: 'border-restricted/30',  text: 'text-restricted',  iconColor: 'text-restricted' },
};

// ─── Payer clinical card ──────────────────────────────────────────────────────

function ClinicalCard({ payer }: { payer: PayerCoverage }) {
  const [open, setOpen] = useState(false);
  const status = STATUS_MAP[payer.status] ?? 'conditional';
  const cfg    = STATUS_CONFIG[status];
  const Icon   = cfg.icon;

  return (
    <div className={cn('rounded-xl border overflow-hidden', cfg.border)}>
      <button onClick={() => setOpen(o => !o)}
        className={cn('w-full flex items-center justify-between px-5 py-4', cfg.bg)}>
        <div className="flex items-center gap-3">
          <Icon className={cn('w-5 h-5 shrink-0', cfg.iconColor)} />
          <div className="text-left">
            <p className="font-semibold text-ink">{payer.payer}</p>
            <p className={cn('text-xs font-medium', cfg.text)}>{cfg.label}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={cn('font-bold text-lg', payer.score >= 70 ? 'text-covered' : payer.score >= 45 ? 'text-conditional' : 'text-restricted')}>
            {payer.score}/100
          </span>
          {open ? <ChevronUp className="w-4 h-4 text-muted-text" /> : <ChevronDown className="w-4 h-4 text-muted-text" />}
        </div>
      </button>

      {open && (
        <div className="bg-white px-5 py-4 border-t border-border-light grid gap-3 text-sm">
          {[
            { label: '📋 Prior authorization', value: payer.prior_auth,   warn: payer.prior_auth === 'Required' },
            { label: '🪜 Step therapy',         value: payer.step_therapy,  warn: parseInt(payer.step_therapy) > 1 },
            { label: '✅ Covered indications',  value: payer.indications,  warn: false },
            { label: '🏥 Site of care',         value: payer.site_of_care, warn: payer.site_of_care?.includes('Hospital') },
            { label: '📅 Effective',            value: payer.effective_date, warn: false },
          ].map(({ label, value, warn }) => (
            <div key={label} className="flex justify-between gap-4">
              <span className="text-muted-text shrink-0">{label}</span>
              <span className={cn('font-medium text-right', warn ? 'text-restricted' : 'text-ink')}>{value ?? '—'}</span>
            </div>
          ))}

          {payer.pa_criteria && payer.pa_criteria.length > 0 && (
            <div className="mt-1 pt-3 border-t border-border-light">
              <p className="text-muted-text text-xs font-medium uppercase tracking-wide mb-2">PA Criteria</p>
              <ul className="flex flex-col gap-1">
                {payer.pa_criteria.map((c, i) => (
                  <li key={i} className="text-xs text-ink flex gap-2">
                    <span className="text-accent-blue shrink-0">•</span> {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Summary banner ───────────────────────────────────────────────────────────

function CoverageSummary({ payers }: { payers: PayerCoverage[] }) {
  const covered    = payers.filter(p => STATUS_MAP[p.status] === 'covered').length;
  const restricted = payers.filter(p => STATUS_MAP[p.status] === 'restricted').length;
  const pa         = payers.filter(p => STATUS_MAP[p.status] === 'conditional').length;

  return (
    <div className="grid grid-cols-3 gap-3 mb-8">
      {[
        { label: 'Covered',     value: covered,    color: 'text-covered',     bg: 'bg-green-50 border-covered/20' },
        { label: 'PA required', value: pa,         color: 'text-conditional', bg: 'bg-amber-50 border-conditional/20' },
        { label: 'Restricted',  value: restricted, color: 'text-restricted',  bg: 'bg-red-50 border-restricted/20' },
      ].map(({ label, value, color, bg }) => (
        <div key={label} className={cn('rounded-lg border p-4 text-center', bg)}>
          <p className={cn('font-mono text-3xl font-bold', color)}>{value}</p>
          <p className="text-muted-text text-xs mt-1">{label}</p>
        </div>
      ))}
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({ onSearch }: { onSearch: (q: string) => void }) {
  const [q, setQ] = useState('');
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
      <div className="w-16 h-16 rounded-full bg-green-50 flex items-center justify-center mb-6 border border-green-200">
        <Stethoscope className="w-8 h-8 text-covered" />
      </div>
      <h2 className="font-serif text-2xl text-ink mb-2">Doctor view</h2>
      <p className="text-muted-text text-sm max-w-sm mb-8">
        Search a drug to see a clinical summary of payer coverage — PA criteria, step therapy, and site-of-care restrictions.
      </p>
      <form onSubmit={e => { e.preventDefault(); if (q.trim()) onSearch(q.trim()); }}
        className="flex gap-2 w-full max-w-md">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="e.g. Adalimumab, Rituximab…"
          className="flex-1 h-11 px-4 bg-white border border-border-light rounded-lg text-ink placeholder:text-hint outline-none focus:border-green-500 text-sm" />
        <button type="submit"
          className="h-11 px-5 bg-covered text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors">
          Look up
        </button>
      </form>
      <div className="flex flex-wrap gap-2 mt-5 justify-center">
        {['Adalimumab','Rituximab','Bevacizumab','Denosumab'].map(d => (
          <button key={d} onClick={() => onSearch(d)}
            className="px-3 py-1.5 text-sm bg-white text-muted-text border border-border-light rounded-full hover:border-covered hover:text-covered transition-colors">
            {d}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

function DoctorPageInner() {
  const params    = useSearchParams();
  const router    = useRouter();
  const drugParam = params.get('drug');

  const [data,    setData]    = useState<DrugResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  useEffect(() => {
    if (!drugParam) { setData(null); return; }
    setLoading(true); setError('');
    fetch(`/api/drug?name=${encodeURIComponent(drugParam)}`)
      .then(r => r.ok ? r.json() : Promise.reject('Drug not found'))
      .then(setData)
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, [drugParam]);

  const navigate = (drug: string) => router.push(`/doctor?drug=${encodeURIComponent(drug)}`);

  if (!drugParam && !loading) {
    return <div className="w-full max-w-[900px] mx-auto"><EmptyState onSearch={navigate} /></div>;
  }

  const drug = data?.drug ?? drugParam ?? '';

  return (
    <div className="w-full max-w-[900px] mx-auto px-6 pt-8 pb-16">

      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-green-50 border border-green-200 flex items-center justify-center shrink-0">
          <Stethoscope className="w-5 h-5 text-covered" />
        </div>
        <div>
          <p className="text-xs text-muted-text font-medium uppercase tracking-wide">Doctor view</p>
          {loading
            ? <div className="h-7 w-40 bg-gray-100 rounded animate-pulse mt-1" />
            : <h1 className="font-serif text-2xl text-ink capitalize">{drug}</h1>
          }
        </div>
        <button onClick={() => router.push(`/results?drug=${encodeURIComponent(drugParam ?? '')}`)}
          className="ml-auto flex items-center gap-1.5 text-sm text-muted-text border border-border-light rounded-lg px-3 py-1.5 hover:border-muted-text transition-colors">
          Full data <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-restricted/20 rounded-lg px-5 py-4 text-restricted text-sm mb-6">{error}</div>
      )}

      {/* Clinical summary */}
      {!loading && data && (
        <>
          {data.drug_class && (
            <p className="text-muted-text text-sm mb-6">
              <span className="font-medium text-ink">{data.drug_class}</span>
              {data.condition && ` · ${data.condition}`}
              {data.aliases.length > 0 && ` · Also: ${data.aliases.join(', ')}`}
            </p>
          )}

          <CoverageSummary payers={data.payers} />

          <h2 className="font-semibold text-ink mb-4 text-sm uppercase tracking-wide">Payer-by-payer breakdown</h2>
          <p className="text-muted-text text-sm mb-4">Click any payer to see full PA criteria and requirements.</p>

          <div className="flex flex-col gap-3">
            {data.payers
              .sort((a, b) => b.score - a.score)
              .map(p => <ClinicalCard key={p.payer} payer={p} />)
            }
          </div>

          <div className="mt-8 bg-amber-50 border border-conditional/20 rounded-lg px-5 py-4">
            <p className="text-xs text-conditional font-semibold uppercase tracking-wide mb-1">Clinical note</p>
            <p className="text-ink text-sm leading-relaxed">
              Prior authorization requirements and step therapy criteria change frequently. Always verify current requirements directly with the payer before prescribing. This data is sourced from uploaded policy documents.
            </p>
          </div>
        </>
      )}

      {loading && (
        <div className="flex flex-col gap-3">
          {[1,2,3,4].map(i => <div key={i} className="h-16 bg-white border border-border-light rounded-xl animate-pulse" />)}
        </div>
      )}
    </div>
  );
}

export default function DoctorPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-[60vh]"><div className="w-6 h-6 rounded-full border-2 border-accent-blue border-t-transparent animate-spin" /></div>}>
      <DoctorPageInner />
    </Suspense>
  );
}
