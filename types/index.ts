/**
 * MedPolicy Tracker - Type Definitions
 * Contains all shared types and mock data for the application
 */

export type UserRole = 'doctor' | 'analyst';

export type CoverageStatus = 'covered' | 'conditional' | 'restricted';

export type ChangeType = 'narrowed' | 'expanded' | 'step' | 'admin';

export interface Payer {
  id: string;
  name: string;
  status: CoverageStatus;
  priorAuth: string;
  stepTherapy: string;
  indications: string;
  siteOfCare: string;
  effectiveDate: string;
  score: number;
  updated?: boolean;
}

export interface Drug {
  id: string;
  name: string;
  jCode: string;
  aliases: string[];
  drugClass: string;
}

export interface PolicyChange {
  id: string;
  type: ChangeType;
  payer: string;
  drug: string;
  date: string;
  summary: string;
  fieldsChanged: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'ai';
  content: string;
  citation?: {
    source: string;
    quote: string;
  };
}

export interface DnaDataPoint {
  dimension: string;
  UHC: number;
  Cigna: number;
  BCBS: number;
}

// Status styling configuration
export const STATUS_STYLES: Record<CoverageStatus, { bg: string; text: string; border: string }> = {
  covered: {
    bg: 'bg-green-50',
    text: 'text-covered',
    border: 'border-covered',
  },
  conditional: {
    bg: 'bg-amber-50',
    text: 'text-conditional',
    border: 'border-conditional',
  },
  restricted: {
    bg: 'bg-red-50',
    text: 'text-restricted',
    border: 'border-restricted',
  },
};

export const CHANGE_TYPE_STYLES: Record<ChangeType, { bg: string; text: string; label: string; border: string }> = {
  narrowed: {
    bg: 'bg-red-100',
    text: 'text-red-800',
    label: 'Coverage narrowed',
    border: 'border-l-restricted',
  },
  expanded: {
    bg: 'bg-green-100',
    text: 'text-green-800',
    label: 'Coverage expanded',
    border: 'border-l-covered',
  },
  step: {
    bg: 'bg-amber-100',
    text: 'text-amber-800',
    label: 'Step therapy added',
    border: 'border-l-conditional',
  },
  admin: {
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    label: 'Administrative change',
    border: 'border-l-gray-400',
  },
};

// Mock Data
export const CURRENT_DRUG: Drug = {
  id: 'rituximab',
  name: 'Rituximab',
  jCode: 'J9312',
  aliases: ['Rituxan', 'Truxima', 'Ruxience', 'MabThera'],
  drugClass: 'Anti-CD20 monoclonal antibody',
};

export const PAYERS: Payer[] = [
  {
    id: 'uhc',
    name: 'UnitedHealthcare',
    status: 'covered',
    priorAuth: 'Not required',
    stepTherapy: '1 prior drug',
    indications: 'RA, NHL, CLL, GPA',
    siteOfCare: 'Any approved',
    effectiveDate: 'Effective Jan 2026',
    score: 82,
  },
  {
    id: 'cigna',
    name: 'Cigna',
    status: 'conditional',
    priorAuth: 'Required',
    stepTherapy: '2 prior drugs',
    indications: 'NHL, CLL only',
    siteOfCare: 'Physician only',
    effectiveDate: 'Effective Mar 2026',
    score: 41,
    updated: true,
  },
  {
    id: 'bcbs',
    name: 'BCBS NC',
    status: 'covered',
    priorAuth: 'Required',
    stepTherapy: '1 prior drug',
    indications: 'RA, NHL, CLL, GPA, PV',
    siteOfCare: 'Any approved',
    effectiveDate: 'Effective Feb 2026',
    score: 74,
  },
  {
    id: 'aetna',
    name: 'Aetna',
    status: 'restricted',
    priorAuth: 'Required',
    stepTherapy: '3 prior drugs',
    indications: 'NHL only',
    siteOfCare: 'Hospital outpt. only',
    effectiveDate: 'Effective Jan 2026',
    score: 18,
  },
];

export const POLICY_CHANGES: PolicyChange[] = [
  {
    id: '1',
    type: 'narrowed',
    payer: 'Cigna',
    drug: 'Rituximab',
    date: 'Mar 15, 2026',
    summary: 'Removed Rheumatoid Arthritis indication. Step therapy increased from 1 to 2 required prior treatment failures.',
    fieldsChanged: ['Covered indications', 'Step therapy'],
  },
  {
    id: '2',
    type: 'expanded',
    payer: 'BCBS NC',
    drug: 'Rituximab',
    date: 'Feb 1, 2026',
    summary: 'Added Pemphigus Vulgaris (PV) as a newly covered indication. No change to prior authorization requirements.',
    fieldsChanged: ['Covered indications'],
  },
  {
    id: '3',
    type: 'step',
    payer: 'Aetna',
    drug: 'Denosumab',
    date: 'Jan 8, 2026',
    summary: 'Now requires documented failure of both methotrexate AND leflunomide before approval will be granted.',
    fieldsChanged: ['Step therapy'],
  },
  {
    id: '4',
    type: 'admin',
    payer: 'UHC',
    drug: 'Bevacizumab',
    date: 'Jan 3, 2026',
    summary: 'Formatting update to clinical criteria section. No change to coverage or PA requirements.',
    fieldsChanged: ['Formatting only'],
  },
];

export const DNA_DATA: DnaDataPoint[] = [
  { dimension: 'PA burden', UHC: 25, Cigna: 85, BCBS: 60 },
  { dimension: 'Step therapy', UHC: 40, Cigna: 70, BCBS: 40 },
  { dimension: 'Narrowness', UHC: 30, Cigna: 65, BCBS: 25 },
  { dimension: 'Site restrict', UHC: 20, Cigna: 80, BCBS: 20 },
  { dimension: 'Update freq', UHC: 35, Cigna: 50, BCBS: 45 },
];

export const RECENT_SEARCHES = [
  { drug: 'Rituximab', jCode: 'J9312' },
  { drug: 'Bevacizumab', jCode: 'J9035' },
  { drug: 'Denosumab', jCode: 'J0897' },
];

export const STATS = [
  { label: 'Payers tracked', value: '8', highlight: false },
  { label: 'Policies indexed', value: '143', highlight: false },
  { label: 'Changes this quarter', value: '12', highlight: true },
  { label: 'Drugs monitored', value: '34', highlight: false },
];

export const SAMPLE_CHAT: ChatMessage[] = [
  {
    id: '1',
    role: 'ai',
    content: 'Ask me anything about drug coverage across payers. Try: "Does UHC cover Rituximab for RA?" or "What changed in Cigna\'s policy this quarter?"',
  },
  {
    id: '2',
    role: 'user',
    content: 'Does UHC cover Rituximab for rheumatoid arthritis?',
  },
  {
    id: '3',
    role: 'ai',
    content: 'Yes — UHC covers Rituximab for Rheumatoid Arthritis. The patient must show an inadequate response to at least one conventional DMARD. Prior authorization is not required for this indication.',
    citation: {
      source: 'UHC Medical Benefit Drug Policy: Rituximab — Page 3 §2.1',
      quote: '"Coverage is approved for adult patients with moderately to severely active RA who have had an inadequate response to one or more DMARDs..."',
    },
  },
];

export const CHAT_SUGGESTIONS = [
  '"What changed in Cigna\'s policy?"',
  '"Compare UHC vs Aetna step therapy"',
  '"Which plan covers GPA?"',
];
