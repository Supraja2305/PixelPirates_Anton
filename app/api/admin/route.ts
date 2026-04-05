/**
 * Next.js API proxy for all /api/admin/* endpoints.
 * Maps the full AntonRX OpenAPI admin spec to Next.js route handlers.
 *
 * GET  ?action=summary      → /api/admin/audit-summary + /admin/dashboard
 * GET  ?action=audit        → /api/admin/audit-logs
 * GET  ?action=queue        → /api/admin/queue
 * GET  ?action=rankings     → /api/admin/analytics/payer-rankings
 * GET  ?action=gaps         → /api/admin/analytics/gaps
 * GET  ?action=outliers     → /api/admin/analytics/outliers
 * GET  ?action=statistics   → /api/admin/analytics/statistics
 * GET  ?action=report&year=&quarter= → /api/admin/reports/quarterly
 * POST action=soft_delete, restore, override_field, re_extract, bulk_archive
 *
 * Falls back to local in-memory demo data when Python backend is offline.
 * Directory: app/api/admin/route.ts
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.PYTHON_BACKEND_URL ?? 'http://localhost:8000';

// ─── Auth guard ───────────────────────────────────────────────────────────────
// ★ Security fix: verify caller is an admin before serving any admin data.
// Reads the x-user-role header injected by proxy.ts (our route protector).
// Also accepts a valid session cookie as fallback for direct API calls.

function assertAdmin(req: NextRequest): NextResponse | null {
  // proxy.ts sets this header after validating the session cookie
  const roleHeader = req.headers.get('x-user-role');
  if (roleHeader === 'admin') return null; // ✓ authorised

  // Fallback: parse session cookie directly (e.g. server-to-server calls)
  const cookie = req.cookies.get('polarix_session')?.value;
  if (cookie) {
    try {
      const user = JSON.parse(atob(cookie)) as { role?: string };
      if (user?.role === 'admin') return null; // ✓ authorised
    } catch { /* invalid cookie */ }
  }

  return NextResponse.json(
    { error: 'Forbidden — admin role required.' },
    { status: 403 }
  );
}


// ─── Proxy helper ─────────────────────────────────────────────────────────────

async function proxyGet<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${BACKEND}${path}`, {
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return null;
    return res.json() as Promise<T>;
  } catch {
    return null;
  }
}

async function proxyPost<T>(path: string, body: unknown): Promise<T | null> {
  try {
    const res = await fetch(`${BACKEND}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    return res.json() as Promise<T>;
  } catch {
    return null;
  }
}

// ─── In-memory fallback stores ────────────────────────────────────────────────
// Used when Python backend is offline. Mirrors admin_service.py state.

interface AuditEntry {
  id: string; action: string; admin_email: string; entity_type: string;
  entity_id: string; changes: Record<string, unknown>; reason?: string; created_at: string;
}

interface PolicyRecord {
  id: string; name: string; payer: string; drug: string;
  is_active: boolean; deactivated_at?: string; deactivation_reason?: string;
  field_overrides: Record<string, unknown>;
}

const auditStore  = new Map<string, AuditEntry>();
const policyStore = new Map<string, PolicyRecord>([
  ['pol_uhc_rituximab',    { id:'pol_uhc_rituximab',    name:'Rituximab — UHC',    payer:'UnitedHealthcare', drug:'Rituximab',    is_active:true,  field_overrides:{} }],
  ['pol_cigna_rituximab',  { id:'pol_cigna_rituximab',  name:'Rituximab — Cigna',  payer:'Cigna',            drug:'Rituximab',    is_active:true,  field_overrides:{} }],
  ['pol_aetna_adalimumab', { id:'pol_aetna_adalimumab', name:'Adalimumab — Aetna', payer:'Aetna',            drug:'Adalimumab',   is_active:true,  field_overrides:{} }],
  ['pol_bcbs_bevacizumab', { id:'pol_bcbs_bevacizumab', name:'Bevacizumab — BCBS', payer:'BCBS',             drug:'Bevacizumab',  is_active:false, field_overrides:{} }],
  ['pol_uhc_denosumab',    { id:'pol_uhc_denosumab',    name:'Denosumab — UHC',    payer:'UnitedHealthcare', drug:'Denosumab',    is_active:true,  field_overrides:{} }],
  ['pol_cigna_adalimumab', { id:'pol_cigna_adalimumab', name:'Adalimumab — Cigna', payer:'Cigna',            drug:'Adalimumab',   is_active:true,  field_overrides:{} }],
]);

function logAudit(action: string, adminEmail: string, entityType: string, entityId: string,
  changes: Record<string, unknown>, reason?: string): AuditEntry {
  const entry: AuditEntry = {
    id: crypto.randomUUID(), action, admin_email: adminEmail,
    entity_type: entityType, entity_id: entityId, changes, reason,
    created_at: new Date().toISOString(),
  };
  auditStore.set(entry.id, entry);
  return entry;
}

// ─── Demo fallback data ───────────────────────────────────────────────────────

const DEMO_RANKINGS = [
  { payer_name:'Aetna',           rank:1, restrictiveness_score:85, avg_pa_required_pct:95, avg_step_therapy_steps:3.2, policies_analyzed:28 },
  { payer_name:'Cigna',           rank:2, restrictiveness_score:72, avg_pa_required_pct:88, avg_step_therapy_steps:2.4, policies_analyzed:32 },
  { payer_name:'BCBS',            rank:3, restrictiveness_score:45, avg_pa_required_pct:70, avg_step_therapy_steps:1.3, policies_analyzed:38 },
  { payer_name:'UnitedHealthcare',rank:4, restrictiveness_score:28, avg_pa_required_pct:42, avg_step_therapy_steps:0.9, policies_analyzed:45 },
];

const DEMO_GAPS = [
  { drug:'adalimumab',  payer:'Aetna', gap_type:'site_restriction',   severity:'high',   description:'Restricted to hospital outpatient — limits patient access' },
  { drug:'rituximab',   payer:'Cigna', gap_type:'missing_indication', severity:'high',   description:'RA indication removed — patients with RA cannot access coverage' },
  { drug:'bevacizumab', payer:'Aetna', gap_type:'missing_indication', severity:'medium', description:'Only CRC covered — other FDA indications not available' },
  { drug:'denosumab',   payer:'Cigna', gap_type:'not_covered',        severity:'medium', description:'Bone metastases not covered — restricted to osteoporosis only' },
];

const DEMO_OUTLIERS = [
  { policy_id:'pol_aetna_adalimumab', payer:'Aetna', drug:'Adalimumab', metric:'step_therapy_steps', metric_value:3,  average_value:1.4, z_score:2.8, severity:'critical' },
  { policy_id:'pol_aetna_rituximab',  payer:'Aetna', drug:'Rituximab',  metric:'restrictiveness',    metric_value:82, average_value:44,  z_score:2.3, severity:'critical' },
  { policy_id:'pol_cigna_rituximab',  payer:'Cigna', drug:'Rituximab',  metric:'step_therapy_steps', metric_value:2,  average_value:1.4, z_score:1.9, severity:'warning'  },
];

const DEMO_STATS = {
  total_policies:143, avg_restrictiveness_score:52, payers_count:8,
  drugs_count:34, pa_required_pct:74, step_therapy_pct:48,
};

// ─── GET handler ──────────────────────────────────────────────────────────────

export async function GET(req: NextRequest) {
  const authErr = assertAdmin(req);
  if (authErr) return authErr;

  const action  = req.nextUrl.searchParams.get('action') ?? 'summary';
  const year    = req.nextUrl.searchParams.get('year');
  const quarter = req.nextUrl.searchParams.get('quarter');

  // Try Python backend first, fall back to demo data

  if (action === 'audit') {
    const live = await proxyGet<{ logs: unknown[] }>('/api/admin/audit-logs');
    const logs = live?.logs?.length
      ? live.logs
      : Array.from(auditStore.values()).sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 100);
    return NextResponse.json({ logs, total: (logs as unknown[]).length });
  }

  if (action === 'queue') {
    const live = await proxyGet('/api/admin/queue');
    return NextResponse.json(live ?? { total_pending:0, total_extracting:0, total_success: policyStore.size, total_failed:0, recent_jobs:[] });
  }

  if (action === 'rankings') {
    const live = await proxyGet<{ rankings: unknown[] }>('/api/admin/analytics/payer-rankings');
    return NextResponse.json({ rankings: live?.rankings ?? DEMO_RANKINGS });
  }

  if (action === 'gaps') {
    const live = await proxyGet<{ gaps: unknown[] }>('/api/admin/analytics/gaps');
    return NextResponse.json({ gaps: live?.gaps ?? DEMO_GAPS });
  }

  if (action === 'outliers') {
    const live = await proxyGet<{ outliers: unknown[] }>('/api/admin/analytics/outliers');
    return NextResponse.json({ outliers: live?.outliers ?? DEMO_OUTLIERS });
  }

  if (action === 'statistics') {
    const live = await proxyGet('/api/admin/analytics/statistics');
    return NextResponse.json(live ?? DEMO_STATS);
  }

  if (action === 'report' && year && quarter) {
    const live = await proxyGet<{ report: unknown }>(`/api/admin/reports/quarterly?year=${year}&quarter=${quarter}`);
    return NextResponse.json(live ?? {
      report: {
        year: parseInt(year), quarter: parseInt(quarter), total_changes: 12,
        by_type: { narrowed:4, expanded:3, step:3, admin:2 },
        by_payer: { Cigna:5, Aetna:4, BCBS:2, UHC:1 },
        top_drugs: ['Rituximab','Adalimumab','Bevacizumab'],
        summary: `Q${quarter} ${year}: 12 policy changes detected. Cigna and Aetna led in restrictions.`,
      },
    });
  }

  if (action === 'policies') {
    const live = await proxyGet<{ results: unknown[] }>('/api/admin/search/policies');
    const localPolicies = Array.from(policyStore.values());
    return NextResponse.json({ policies: live?.results ?? localPolicies, total: localPolicies.length });
  }

  // Default: full summary (mirrors get_audit_summary + admin/dashboard)
  const [dashLive, summaryLive] = await Promise.all([
    proxyGet<{ total_payers: number; total_policies: number; total_drugs: number }>('/admin/dashboard'),
    proxyGet<{ total_actions: number; action_breakdown: unknown }>('/api/admin/audit-summary'),
  ]);

  const actionCounts: Record<string, number> = {};
  const adminActivity: Record<string, number> = {};
  for (const log of auditStore.values()) {
    actionCounts[log.action]       = (actionCounts[log.action] ?? 0) + 1;
    adminActivity[log.admin_email] = (adminActivity[log.admin_email] ?? 0) + 1;
  }

  return NextResponse.json({
    summary: summaryLive ?? { total_actions: auditStore.size, action_breakdown: actionCounts, admin_activity: adminActivity },
    queue_status: { total_pending:0, total_extracting:0, total_success: Array.from(policyStore.values()).filter(p=>p.is_active).length, total_failed:0 },
    active_policies: Array.from(policyStore.values()).filter(p => p.is_active).length,
    total_policies:  policyStore.size,
    dashboard: dashLive,
  });
}

// ─── POST handler ─────────────────────────────────────────────────────────────

export async function POST(req: NextRequest) {
  const authErr = assertAdmin(req);
  if (authErr) return authErr;

  const body = await req.json() as {
    action: string;
    policy_id?: string;
    payer_id?: string;
    admin_email?: string;
    reason?: string;
    field_name?: string;
    old_value?: unknown;
    new_value?: unknown;
    updated_prompt?: string;
    payer_ids?: string[];
  };

  const adminEmail = body.admin_email ?? 'admin@antonrx.com';

  // ── soft_delete (DELETE /api/admin/policies/{id}) ──────────────────────────
  if (body.action === 'soft_delete' && body.policy_id) {
    const live = await proxyPost(`/api/admin/policies/${body.policy_id}`, { reason: body.reason });
    if (!live) {
      const p = policyStore.get(body.policy_id);
      if (p) { p.is_active = false; p.deactivated_at = new Date().toISOString(); p.deactivation_reason = body.reason; }
    }
    logAudit('POLICY_SOFT_DELETED', adminEmail, 'policy', body.policy_id,
      { is_active: { old: true, new: false } }, body.reason);
    return NextResponse.json({ success: true, policy_id: body.policy_id, is_active: false });
  }

  // ── restore (POST /api/admin/policies/{id}/restore) ────────────────────────
  if (body.action === 'restore' && body.policy_id) {
    const live = await proxyPost(`/api/admin/policies/${body.policy_id}/restore`, {});
    if (!live) {
      const p = policyStore.get(body.policy_id);
      if (p) { p.is_active = true; delete p.deactivated_at; delete p.deactivation_reason; }
    }
    logAudit('POLICY_RESTORED', adminEmail, 'policy', body.policy_id, { is_active: { old: false, new: true } });
    return NextResponse.json({ success: true, policy_id: body.policy_id, is_active: true });
  }

  // ── override_field (PUT /api/admin/policies/{id}/override-field) ───────────
  if (body.action === 'override_field' && body.policy_id && body.field_name) {
    const live = await fetch(`${BACKEND}/api/admin/policies/${body.policy_id}/override-field`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ field_name: body.field_name, new_value: body.new_value, reason: body.reason }),
    }).then(r => r.ok ? r.json() : null).catch(() => null);

    if (!live) {
      const p = policyStore.get(body.policy_id);
      if (p) p.field_overrides[body.field_name] = body.new_value;
    }
    logAudit('POLICY_FIELD_OVERRIDDEN', adminEmail, 'policy', body.policy_id,
      { [body.field_name]: { old: body.old_value, new: body.new_value } }, body.reason);
    return NextResponse.json({ success: true, field: body.field_name, new_value: body.new_value });
  }

  // ── re_extract (POST /api/admin/policies/{id}/re-extract) ─────────────────
  if (body.action === 're_extract' && body.policy_id) {
    const live = await proxyPost(`/api/admin/policies/${body.policy_id}/re-extract`,
      { updated_prompt: body.updated_prompt });
    logAudit('POLICY_RE_EXTRACTED', adminEmail, 'policy', body.policy_id,
      { has_custom_prompt: !!body.updated_prompt });
    return NextResponse.json(live ?? { success: true, job_id: crypto.randomUUID(), status: 'pending' });
  }

  // ── bulk_archive payer (POST /api/admin/payers/{id}/bulk-archive) ──────────
  if (body.action === 'bulk_archive' && body.payer_id) {
    const live = await proxyPost(`/api/admin/payers/${body.payer_id}/bulk-archive`, {});
    logAudit('PAYER_BULK_ARCHIVED', adminEmail, 'payer', body.payer_id,
      { policies_archived: 0 });
    return NextResponse.json(live ?? { success: true, payer_id: body.payer_id, policies_archived: 0 });
  }

  // ── bulk_archive multiple (POST /api/admin/payers/bulk-archive/multiple) ───
  if (body.action === 'bulk_archive_multiple' && body.payer_ids?.length) {
    const live = await proxyPost('/api/admin/payers/bulk-archive/multiple', { payer_ids: body.payer_ids });
    return NextResponse.json(live ?? { success: true, payers_archived: body.payer_ids.length });
  }

  return NextResponse.json({ error: `Unknown action: ${body.action}` }, { status: 400 });
}