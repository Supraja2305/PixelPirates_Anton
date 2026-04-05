/**
 * lib/backend.ts
 * ─────────────────────────────────────────────────────────────
 * Central API client for all pages.
 * Priority: Python backend (localhost:8000) → demo data fallback.
 * Set PYTHON_BACKEND_URL in .env.local to point to deployed backend.
 */

const BACKEND = process.env.PYTHON_BACKEND_URL ?? 'http://localhost:8000';

// ─── Drug normalizer (ported from backend/normalizers/drug_normalizer.py) ────

const ALIASES: Record<string, string> = {
  humira: 'adalimumab', adalimumab: 'adalimumab',
  rituxan: 'rituximab', rituximab: 'rituximab',
  truxima: 'rituximab', ruxience: 'rituximab', 'rituximab-pvvr': 'rituximab',
  avastin: 'bevacizumab', bevacizumab: 'bevacizumab', mvasi: 'bevacizumab',
  keytruda: 'pembrolizumab', pembrolizumab: 'pembrolizumab',
  prolia: 'denosumab', denosumab: 'denosumab', xgeva: 'denosumab',
  metformin: 'metformin', glucophage: 'metformin',
  lisinopril: 'lisinopril', zestril: 'lisinopril',
  atorvastatin: 'atorvastatin', lipitor: 'atorvastatin',
};

export function normalizeDrug(name: string): string {
  return ALIASES[name.toLowerCase().trim()] ?? name.toLowerCase().trim();
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PayerCoverage {
  payer: string;
  status: 'covered' | 'pa_required' | 'step_therapy' | 'not_covered' | 'conditional' | 'restricted';
  prior_auth: string;
  step_therapy: string;
  indications: string;
  site_of_care: string;
  effective_date: string;
  score: number;
  pa_criteria?: string[];
  updated?: boolean;
}

export interface DrugResult {
  drug: string;
  j_code: string | null;
  aliases: string[];
  drug_class: string;
  condition: string;
  generic_available: boolean;
  payers: PayerCoverage[];
}

export interface SearchResult {
  drug: string;
  j_code: string | null;
  drug_class: string;
  condition: string;
  generic_available: boolean;
}

export interface PolicyChange {
  id: string;
  type: 'narrowed' | 'expanded' | 'step' | 'admin';
  payer: string;
  drug: string;
  date: string;
  summary: string;
  fields_changed: string[];
}

export interface DashboardStats {
  payers_tracked: number;
  policies_indexed: number;
  changes_this_quarter: number;
  drugs_monitored: number;
}

// ─── Proxy fetch ──────────────────────────────────────────────────────────────

async function backendFetch<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${BACKEND}${path}`, {
      next: { revalidate: 60 },
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return null;
    return res.json() as Promise<T>;
  } catch (_) {
    return null; // backend not running → fall through to demo data
  }
}

// ─── Demo data (mirrors Python DRUG_COVERAGE_MAP + main.py data) ─────────────

const DEMO_DRUGS: Record<string, DrugResult> = {
  adalimumab: {
    drug: 'adalimumab', j_code: 'J0135',
    aliases: ['Humira', 'Hadlima', 'Hyrimoz', 'Cyltezo'],
    drug_class: 'TNF Inhibitor', condition: 'Rheumatoid Arthritis', generic_available: false,
    payers: [
      { payer: 'UnitedHealthcare', status: 'covered',      prior_auth: 'Not required', step_therapy: '1 prior drug', indications: 'RA, PsA, AS, CD', site_of_care: 'Any approved', effective_date: 'Jan 2026', score: 82 },
      { payer: 'Cigna',           status: 'pa_required',   prior_auth: 'Required',     step_therapy: '2 prior drugs', indications: 'RA, PsA only', site_of_care: 'Physician only', effective_date: 'Mar 2026', score: 41, updated: true, pa_criteria: ['Diagnosis of moderate-to-severe RA', 'Failure of ≥2 DMARDs', 'Prescriber is rheumatologist'] },
      { payer: 'BCBS',            status: 'covered',       prior_auth: 'Required',     step_therapy: '1 prior drug', indications: 'RA, PsA, AS, CD, UC', site_of_care: 'Any approved', effective_date: 'Feb 2026', score: 74 },
      { payer: 'Aetna',           status: 'step_therapy',  prior_auth: 'Required',     step_therapy: '3 prior drugs', indications: 'RA only', site_of_care: 'Hospital outpt. only', effective_date: 'Jan 2026', score: 18 },
    ],
  },
  rituximab: {
    drug: 'rituximab', j_code: 'J9312',
    aliases: ['Rituxan', 'Truxima', 'Ruxience', 'MabThera'],
    drug_class: 'Anti-CD20 monoclonal antibody', condition: 'Non-Hodgkin Lymphoma / RA', generic_available: false,
    payers: [
      { payer: 'UnitedHealthcare', status: 'covered',     prior_auth: 'Not required', step_therapy: '1 prior drug', indications: 'RA, NHL, CLL, GPA', site_of_care: 'Any approved', effective_date: 'Jan 2026', score: 82 },
      { payer: 'Cigna',           status: 'pa_required',  prior_auth: 'Required',     step_therapy: '2 prior drugs', indications: 'NHL, CLL only', site_of_care: 'Physician only', effective_date: 'Mar 2026', score: 41, updated: true, pa_criteria: ['Confirmed NHL or CLL diagnosis', 'Failure of prior conventional chemotherapy'] },
      { payer: 'BCBS',            status: 'covered',      prior_auth: 'Required',     step_therapy: '1 prior drug', indications: 'RA, NHL, CLL, GPA, PV', site_of_care: 'Any approved', effective_date: 'Feb 2026', score: 74 },
      { payer: 'Aetna',           status: 'step_therapy', prior_auth: 'Required',     step_therapy: '3 prior drugs', indications: 'NHL only', site_of_care: 'Hospital outpt. only', effective_date: 'Jan 2026', score: 18 },
    ],
  },
  bevacizumab: {
    drug: 'bevacizumab', j_code: 'J9035',
    aliases: ['Avastin', 'Mvasi', 'Zirabev', 'Vegzelma'],
    drug_class: 'VEGF Inhibitor', condition: 'Colorectal Cancer / NSCLC', generic_available: false,
    payers: [
      { payer: 'UnitedHealthcare', status: 'covered',    prior_auth: 'Required', step_therapy: 'None', indications: 'CRC, NSCLC, GBM, RCC', site_of_care: 'Infusion center', effective_date: 'Jan 2026', score: 78 },
      { payer: 'Cigna',           status: 'covered',    prior_auth: 'Required', step_therapy: 'None', indications: 'CRC, NSCLC', site_of_care: 'Physician office', effective_date: 'Feb 2026', score: 65 },
      { payer: 'BCBS',            status: 'pa_required', prior_auth: 'Required', step_therapy: '1 prior regimen', indications: 'CRC, NSCLC, GBM', site_of_care: 'Any approved', effective_date: 'Jan 2026', score: 60 },
      { payer: 'Aetna',           status: 'covered',    prior_auth: 'Required', step_therapy: 'None', indications: 'CRC only', site_of_care: 'Hospital outpt. only', effective_date: 'Jan 2026', score: 45 },
    ],
  },
  denosumab: {
    drug: 'denosumab', j_code: 'J0897',
    aliases: ['Prolia', 'Xgeva'],
    drug_class: 'RANK Ligand Inhibitor', condition: 'Osteoporosis / Bone Metastases', generic_available: false,
    payers: [
      { payer: 'UnitedHealthcare', status: 'covered',    prior_auth: 'Not required', step_therapy: '1 prior drug', indications: 'Osteoporosis, Bone mets', site_of_care: 'Any approved', effective_date: 'Jan 2026', score: 75 },
      { payer: 'Cigna',           status: 'pa_required', prior_auth: 'Required',     step_therapy: '2 prior drugs', indications: 'Osteoporosis only', site_of_care: 'Physician only', effective_date: 'Jan 2026', score: 50 },
      { payer: 'BCBS',            status: 'covered',    prior_auth: 'Required',     step_therapy: '1 prior drug', indications: 'Osteoporosis, Bone mets, GCTB', site_of_care: 'Any approved', effective_date: 'Jan 2026', score: 72 },
      { payer: 'Aetna',           status: 'step_therapy', prior_auth: 'Required',   step_therapy: '3 prior drugs', indications: 'Osteoporosis only', site_of_care: 'Hospital outpt. only', effective_date: 'Jan 2026', score: 22 },
    ],
  },
};

const DEMO_CHANGES: PolicyChange[] = [
  { id: '1', type: 'narrowed',  payer: 'Cigna',  drug: 'Rituximab',    date: 'Mar 15, 2026', summary: 'Removed Rheumatoid Arthritis indication. Step therapy increased from 1 to 2 required prior treatment failures.', fields_changed: ['Covered indications', 'Step therapy'] },
  { id: '2', type: 'expanded',  payer: 'BCBS',   drug: 'Rituximab',    date: 'Feb 1, 2026',  summary: 'Added Pemphigus Vulgaris (PV) as a newly covered indication. No change to prior authorization requirements.', fields_changed: ['Covered indications'] },
  { id: '3', type: 'step',      payer: 'Aetna',  drug: 'Denosumab',    date: 'Jan 8, 2026',  summary: 'Now requires documented failure of both methotrexate AND leflunomide before approval will be granted.', fields_changed: ['Step therapy'] },
  { id: '4', type: 'admin',     payer: 'UHC',    drug: 'Bevacizumab',  date: 'Jan 3, 2026',  summary: 'Formatting update to clinical criteria section. No change to coverage or PA requirements.', fields_changed: ['Formatting only'] },
  { id: '5', type: 'narrowed',  payer: 'Aetna',  drug: 'Adalimumab',   date: 'Dec 1, 2025',  summary: 'Site of care restricted to hospital outpatient only. Removed physician office administration option.', fields_changed: ['Site of care'] },
  { id: '6', type: 'expanded',  payer: 'Cigna',  drug: 'Bevacizumab',  date: 'Nov 15, 2025', summary: 'Expanded covered indications to include cervical cancer. Step therapy requirements remain unchanged.', fields_changed: ['Covered indications'] },
];

const DEMO_STATS: DashboardStats = {
  payers_tracked: 8,
  policies_indexed: 143,
  changes_this_quarter: 12,
  drugs_monitored: 34,
};

// ─── Public API ───────────────────────────────────────────────────────────────

export async function getDrugCoverage(rawName: string): Promise<DrugResult | null> {
  const name = normalizeDrug(rawName);

  // Try Python backend first
  const live = await backendFetch<{ drug: string; policies: PayerCoverage[] }>(`/api/drug/${name}`);
  if (live?.policies?.length) {
    return { drug: name, j_code: null, aliases: [], drug_class: '', condition: '', generic_available: false, payers: live.policies };
  }

  // Also try the demo endpoint in the Python backend
  const demo = await backendFetch<{ drug: string; coverage_by_payer: PayerCoverage[] }>(`/drugs/${name}`);
  if (demo?.coverage_by_payer?.length) {
    return { drug: name, j_code: null, aliases: [], drug_class: '', condition: '', generic_available: false, payers: demo.coverage_by_payer };
  }

  return DEMO_DRUGS[name] ?? null;
}

export async function searchDrugs(query: string): Promise<SearchResult[]> {
  const q = query.toLowerCase().trim();

  const live = await backendFetch<{ results: SearchResult[] }>(`/api/search?q=${encodeURIComponent(q)}`);
  if (live?.results?.length) return live.results;

  // Keyword match against demo data
  return Object.entries(DEMO_DRUGS)
    .filter(([name, d]) =>
      name.includes(q) ||
      d.aliases.some(a => a.toLowerCase().includes(q)) ||
      d.condition.toLowerCase().includes(q) ||
      d.drug_class.toLowerCase().includes(q)
    )
    .map(([, d]) => ({
      drug: d.drug,
      j_code: d.j_code,
      drug_class: d.drug_class,
      condition: d.condition,
      generic_available: d.generic_available,
    }));
}

export async function getChanges(): Promise<PolicyChange[]> {
  const live = await backendFetch<{ alerts: PolicyChange[] }>('/alerts');
  if (live?.alerts?.length) return live.alerts;
  return DEMO_CHANGES;
}

export async function getStats(): Promise<DashboardStats> {
  const live = await backendFetch<{ total_payers: number; total_policies: number; total_drugs: number }>('/admin/dashboard');
  if (live?.total_payers) {
    return {
      payers_tracked:        live.total_payers   ?? DEMO_STATS.payers_tracked,
      policies_indexed:      live.total_policies ?? DEMO_STATS.policies_indexed,
      changes_this_quarter:  DEMO_STATS.changes_this_quarter,
      drugs_monitored:       live.total_drugs    ?? DEMO_STATS.drugs_monitored,
    };
  }
  return DEMO_STATS;
}

export function getAllDrugNames(): string[] {
  return Object.keys(DEMO_DRUGS);
}