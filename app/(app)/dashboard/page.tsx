/**
 * Dashboard — pure search landing. Nothing shown until user types.
 * Flow: Search → /results → /compare → /chat → /changes
 * Directory: app/(app)/dashboard/page.tsx
 */
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Loader2, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SearchResult } from '@/lib/backend';

// The 4-step flow shown beneath the search bar
const FLOW_STEPS = [
  { step: 1, label: 'Drug results',   color: 'bg-accent-blue'   },
  { step: 2, label: 'Compare payers', color: 'bg-covered'       },
  { step: 3, label: 'AI chat',        color: 'bg-conditional'   },
  { step: 4, label: 'Policy changes', color: 'bg-restricted/80' },
];

export default function DashboardPage() {
  const router = useRouter();
  const [query,       setQuery]       = useState('');
  const [isFocused,   setIsFocused]   = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [suggestions, setSuggestions] = useState<SearchResult[]>([]);

  // Live suggestions as user types
  useEffect(() => {
    if (query.trim().length < 2) { setSuggestions([]); return; }
    const t = setTimeout(() => {
      setIsSearching(true);
      fetch(`/api/search?q=${encodeURIComponent(query)}`)
        .then(r => r.json())
        .then(d => setSuggestions(d.results ?? []))
        .catch(() => setSuggestions([]))
        .finally(() => setIsSearching(false));
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  const go = (drug: string) => {
    setSuggestions([]);
    setQuery('');
    router.push(`/results?drug=${encodeURIComponent(drug)}`);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) go(query.trim());
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-56px)] px-6">
      <div className="w-full max-w-[600px]">

        {/* ── Brand mark ─────────────────────────────────────────── */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-accent-blue rounded-xl mb-4">
            <span className="text-white font-bold text-2xl">Rx</span>
          </div>
          <h1 className="font-serif text-3xl text-ink mb-2">Medical benefit drug policy</h1>
          <p className="text-muted-text text-sm">
            Search any drug to see payer coverage, prior auth, and policy changes.
          </p>
        </div>

        {/* ── Search bar ─────────────────────────────────────────── */}
        <div className="relative">
          <form onSubmit={handleSubmit}>
            <div className={cn(
              'flex items-center bg-white rounded-xl border-2 shadow-sm transition-all duration-200',
              isFocused ? 'border-accent-blue shadow-md' : 'border-border-light'
            )}>
              <div className="pl-4">
                {isSearching
                  ? <Loader2 className="w-5 h-5 text-muted-text animate-spin" />
                  : <Search   className="w-5 h-5 text-muted-text" />}
              </div>
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setTimeout(() => { setIsFocused(false); setSuggestions([]); }, 150)}
                placeholder="Drug name or J-code — e.g. Rituximab, J9312"
                className="flex-1 h-[56px] px-4 text-ink placeholder:text-hint bg-transparent outline-none text-base"
                autoFocus
                aria-label="Search drugs"
              />
              <button
                type="submit"
                disabled={!query.trim()}
                className={cn(
                  'h-10 px-6 mr-2 font-semibold text-sm rounded-lg transition-colors',
                  query.trim()
                    ? 'bg-accent-blue text-white hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                )}
              >
                Search
              </button>
            </div>
          </form>

          {/* ── Live suggestions dropdown ───────────────────────── */}
          {suggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 z-50 mt-2 bg-white border border-border-light rounded-xl shadow-lg overflow-hidden">
              {suggestions.map(s => (
                <button
                  key={s.drug}
                  onMouseDown={() => go(s.drug)}
                  className="w-full px-4 py-3.5 text-left hover:bg-off-white flex items-center justify-between group border-b border-border-light last:border-b-0"
                >
                  <div>
                    <span className="font-medium text-ink capitalize">{s.drug}</span>
                    <span className="ml-2 text-muted-text text-sm">{s.drug_class}</span>
                    {s.condition && <span className="ml-1 text-hint text-xs">· {s.condition}</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    {s.j_code && <span className="font-mono text-xs text-muted-text bg-off-white px-2 py-0.5 rounded">{s.j_code}</span>}
                    <ArrowRight className="w-4 h-4 text-hint group-hover:text-accent-blue transition-colors" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* ── Flow steps ─────────────────────────────────────────── */}
        <div className="flex items-center justify-center gap-2 mt-8 flex-wrap">
          {FLOW_STEPS.map((s, i) => (
            <div key={s.step} className="flex items-center gap-2">
              <div className="flex items-center gap-2">
                <span className={cn('w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0', s.color)}>
                  {s.step}
                </span>
                <span className="text-sm text-muted-text">{s.label}</span>
              </div>
              {i < FLOW_STEPS.length - 1 && (
                <ArrowRight className="w-3.5 h-3.5 text-border-light shrink-0" />
              )}
            </div>
          ))}
        </div>

        {/* ── Quick picks ─────────────────────────────────────────── */}
        <div className="flex items-center justify-center gap-2 mt-5 flex-wrap">
          <span className="text-hint text-xs">Popular:</span>
          {['Rituximab','Adalimumab','Bevacizumab','Denosumab'].map(d => (
            <button
              key={d}
              onClick={() => go(d)}
              className="px-3 py-1.5 text-xs bg-white text-muted-text border border-border-light rounded-full hover:border-accent-blue hover:text-accent-blue transition-colors"
            >
              {d}
            </button>
          ))}
        </div>

      </div>
    </div>
  );
}