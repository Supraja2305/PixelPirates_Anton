/**
 * Admin Dashboard — full OpenAPI coverage.
 * Tabs: Policies | Audit log | Analytics | Queue | Report
 * Uses all /api/admin/* endpoints from the AntonRX spec.
 * Directory: app/(app)/admin/page.tsx
 */
'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Shield, Trash2, RotateCcw, Edit3, ClipboardList, Activity,
  AlertTriangle, CheckCircle2, Loader2, BarChart2, TrendingDown,
  AlertCircle, RefreshCw, ChevronDown, FileText,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── Types ────────────────────────────────────────────────────────────────────

interface PolicyRow  { id:string; name:string; payer:string; drug:string; is_active:boolean; field_overrides?:Record<string,unknown> }
interface AuditLog   { id:string; action:string; admin_email:string; entity_type:string; entity_id:string; changes:Record<string,unknown>; reason?:string; created_at:string }
interface Ranking    { payer_name:string; rank:number; restrictiveness_score:number; avg_pa_required_pct:number; avg_step_therapy_steps:number; policies_analyzed:number }
interface Gap        { drug:string; payer:string; gap_type:string; severity:string; description:string }
interface Outlier    { policy_id:string; payer:string; drug:string; metric:string; metric_value:number; average_value:number; z_score:number; severity:string }
interface QueueStatus{ total_pending:number; total_extracting:number; total_success:number; total_failed:number }
interface Report     { year:number; quarter:number; total_changes:number; by_type:Record<string,number>; by_payer:Record<string,number>; top_drugs:string[]; summary:string }

// ─── Severity / action styles ─────────────────────────────────────────────────

const ACTION_STYLES: Record<string, string> = {
  POLICY_SOFT_DELETED:    'bg-red-50 text-red-700 border-red-200',
  POLICY_RESTORED:        'bg-green-50 text-green-700 border-green-200',
  POLICY_FIELD_OVERRIDDEN:'bg-amber-50 text-amber-700 border-amber-200',
  POLICY_RE_EXTRACTED:    'bg-blue-50 text-blue-700 border-blue-200',
  PAYER_BULK_ARCHIVED:    'bg-purple-50 text-purple-700 border-purple-200',
};
const SEV: Record<string,string> = {
  critical:'bg-red-50 text-red-700 border-red-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  high:    'bg-red-50 text-red-700 border-red-200',
  medium:  'bg-amber-50 text-amber-700 border-amber-200',
  low:     'bg-gray-50 text-gray-600 border-gray-200',
};

// ─── Override modal ───────────────────────────────────────────────────────────

function OverrideModal({ policyId, onClose, onDone }: { policyId:string; onClose:()=>void; onDone:()=>void }) {
  const [f,setF]=useState(''); const [ov,setOv]=useState(''); const [nv,setNv]=useState(''); const [r,setR]=useState(''); const [busy,setBusy]=useState(false);
  const submit = async (e:React.FormEvent) => {
    e.preventDefault(); setBusy(true);
    await fetch('/api/admin',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action:'override_field',policy_id:policyId,field_name:f,old_value:ov,new_value:nv,reason:r})});
    setBusy(false); onDone(); onClose();
  };
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h3 className="font-semibold text-ink mb-4 flex items-center gap-2"><Edit3 className="w-4 h-4 text-accent-blue"/>Override field</h3>
        <form onSubmit={submit} className="flex flex-col gap-3">
          {[['Field name',f,setF,'e.g. prior_auth'],['Old value',ov,setOv,'Current value'],['New value',nv,setNv,'Corrected value'],['Reason',r,setR,'Why this correction?']] .map(([label,val,set,ph]) => (
            <div key={String(label)}>
              <label className="text-xs text-muted-text font-medium mb-1 block">{String(label)}</label>
              <input value={String(val)} onChange={e=>(set as (v:string)=>void)(e.target.value)} placeholder={String(ph)} required className="w-full h-9 px-3 border border-border-light rounded-lg text-sm outline-none focus:border-accent-blue"/>
            </div>
          ))}
          <div className="flex gap-2 mt-2">
            <button type="button" onClick={onClose} className="flex-1 h-9 border border-border-light rounded-lg text-sm text-muted-text hover:border-muted-text">Cancel</button>
            <button type="submit" disabled={busy} className="flex-1 h-9 bg-accent-blue text-white rounded-lg text-sm font-medium disabled:opacity-60 flex items-center justify-center gap-2">
              {busy&&<Loader2 className="w-4 h-4 animate-spin"/>} Save override
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Re-extract modal ─────────────────────────────────────────────────────────

function ReExtractModal({ policyId, onClose, onDone }: { policyId:string; onClose:()=>void; onDone:()=>void }) {
  const [prompt,setPrompt]=useState(''); const [busy,setBusy]=useState(false);
  const submit = async (e:React.FormEvent) => {
    e.preventDefault(); setBusy(true);
    await fetch('/api/admin',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action:'re_extract',policy_id:policyId,updated_prompt:prompt||undefined})});
    setBusy(false); onDone(); onClose();
  };
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h3 className="font-semibold text-ink mb-2 flex items-center gap-2"><RefreshCw className="w-4 h-4 text-accent-blue"/>Re-extract policy</h3>
        <p className="text-muted-text text-xs mb-4">Optionally provide an updated extraction prompt. Leave blank to use the default.</p>
        <form onSubmit={submit} className="flex flex-col gap-3">
          <textarea value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="Updated extraction prompt (optional)…" rows={4}
            className="w-full px-3 py-2 border border-border-light rounded-lg text-sm outline-none focus:border-accent-blue resize-none"/>
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="flex-1 h-9 border border-border-light rounded-lg text-sm text-muted-text">Cancel</button>
            <button type="submit" disabled={busy} className="flex-1 h-9 bg-accent-blue text-white rounded-lg text-sm font-medium disabled:opacity-60 flex items-center justify-center gap-2">
              {busy&&<Loader2 className="w-4 h-4 animate-spin"/>} Trigger re-extraction
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Policy table row ─────────────────────────────────────────────────────────

function PolicyTableRow({ pol, onDelete, onRestore, onOverride, onReExtract }: {
  pol:PolicyRow; onDelete:(id:string)=>void; onRestore:(id:string)=>void;
  onOverride:(id:string)=>void; onReExtract:(id:string)=>void;
}) {
  const [busy,setBusy]=useState(false);
  const act=async(fn:()=>void)=>{setBusy(true);await new Promise(r=>setTimeout(r,400));fn();setBusy(false);};
  return (
    <tr className="border-b border-border-light last:border-b-0 hover:bg-off-white/40 transition-colors">
      <td className="py-3 px-5"><p className="font-medium text-ink text-sm">{pol.name}</p><p className="text-xs text-muted-text">{pol.payer}</p></td>
      <td className="py-3 px-5 text-sm text-muted-text capitalize">{pol.drug}</td>
      <td className="py-3 px-5">
        <span className={cn('inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border',
          pol.is_active?'bg-green-50 text-covered border-covered/30':'bg-red-50 text-restricted border-restricted/30')}>
          {pol.is_active?<CheckCircle2 className="w-3 h-3"/>:<AlertTriangle className="w-3 h-3"/>}
          {pol.is_active?'Active':'Archived'}
        </span>
      </td>
      <td className="py-3 px-5">
        <div className="flex items-center gap-1.5 flex-wrap">
          {pol.is_active
            ? <button onClick={()=>act(()=>onDelete(pol.id))} disabled={busy} className="flex items-center gap-1 text-xs text-restricted border border-restricted/30 bg-red-50 px-2 py-1.5 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50">{busy?<Loader2 className="w-3 h-3 animate-spin"/>:<Trash2 className="w-3 h-3"/>}Archive</button>
            : <button onClick={()=>act(()=>onRestore(pol.id))} disabled={busy} className="flex items-center gap-1 text-xs text-covered border border-covered/30 bg-green-50 px-2 py-1.5 rounded-lg hover:bg-green-100 transition-colors disabled:opacity-50">{busy?<Loader2 className="w-3 h-3 animate-spin"/>:<RotateCcw className="w-3 h-3"/>}Restore</button>
          }
          <button onClick={()=>onOverride(pol.id)} className="flex items-center gap-1 text-xs text-accent-blue border border-accent-blue/30 bg-blue-50 px-2 py-1.5 rounded-lg hover:bg-blue-100 transition-colors"><Edit3 className="w-3 h-3"/>Override</button>
          <button onClick={()=>onReExtract(pol.id)} className="flex items-center gap-1 text-xs text-muted-text border border-border-light bg-off-white px-2 py-1.5 rounded-lg hover:border-muted-text transition-colors"><RefreshCw className="w-3 h-3"/>Re-extract</button>
        </div>
      </td>
    </tr>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

type Tab = 'policies'|'audit'|'analytics'|'queue'|'report';

export default function AdminPage() {
  const [tab,          setTab]          = useState<Tab>('policies');
  const [policies,     setPolicies]     = useState<PolicyRow[]>([]);
  const [auditLogs,    setAuditLogs]    = useState<AuditLog[]>([]);
  const [rankings,     setRankings]     = useState<Ranking[]>([]);
  const [gaps,         setGaps]         = useState<Gap[]>([]);
  const [outliers,     setOutliers]     = useState<Outlier[]>([]);
  const [queue,        setQueue]        = useState<QueueStatus|null>(null);
  const [report,       setReport]       = useState<Report|null>(null);
  const [overrideId,   setOverrideId]   = useState<string|null>(null);
  const [reExtractId,  setReExtractId]  = useState<string|null>(null);
  const [loading,      setLoading]      = useState(true);
  const [reportYear,   setReportYear]   = useState(2026);
  const [reportQ,      setReportQ]      = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    const [sumRes, auditRes, polRes] = await Promise.all([
      fetch('/api/admin').then(r=>r.json()),
      fetch('/api/admin?action=audit').then(r=>r.json()),
      fetch('/api/admin?action=policies').then(r=>r.json()),
    ]);
    setAuditLogs(auditRes.logs ?? []);
    setPolicies(polRes.policies ?? []);
    setLoading(false);
    void sumRes; // summary used for stats below
  }, []);

  const loadAnalytics = useCallback(async () => {
    const [rankRes, gapRes, outRes, qRes] = await Promise.all([
      fetch('/api/admin?action=rankings').then(r=>r.json()),
      fetch('/api/admin?action=gaps').then(r=>r.json()),
      fetch('/api/admin?action=outliers').then(r=>r.json()),
      fetch('/api/admin?action=queue').then(r=>r.json()),
    ]);
    setRankings(rankRes.rankings ?? []);
    setGaps(gapRes.gaps ?? []);
    setOutliers(outRes.outliers ?? []);
    setQueue(qRes);
  }, []);

  const loadReport = useCallback(async () => {
    const res = await fetch(`/api/admin?action=report&year=${reportYear}&quarter=${reportQ}`).then(r=>r.json());
    setReport(res.report ?? res);
  }, [reportYear, reportQ]);

  useEffect(()=>{ load(); },[load]);
  useEffect(()=>{ if(tab==='analytics'||tab==='queue') loadAnalytics(); },[tab,loadAnalytics]);
  useEffect(()=>{ if(tab==='report') loadReport(); },[tab,loadReport]);

  const handleDelete  = async (id:string) => { await fetch('/api/admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'soft_delete',policy_id:id,reason:'Admin archive'})}); setPolicies(p=>p.map(pol=>pol.id===id?{...pol,is_active:false}:pol)); load(); };
  const handleRestore = async (id:string) => { await fetch('/api/admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'restore',policy_id:id})}); setPolicies(p=>p.map(pol=>pol.id===id?{...pol,is_active:true}:pol)); load(); };

  const STAT_CARDS = [
    { icon:Activity,      label:'Total policies',  value:String(policies.length),                        color:'text-accent-blue', bg:'bg-blue-50' },
    { icon:CheckCircle2,  label:'Active',           value:String(policies.filter(p=>p.is_active).length), color:'text-covered',     bg:'bg-green-50' },
    { icon:AlertTriangle, label:'Archived',         value:String(policies.filter(p=>!p.is_active).length),color:'text-restricted',  bg:'bg-red-50' },
    { icon:ClipboardList, label:'Audit events',     value:String(auditLogs.length),                       color:'text-conditional', bg:'bg-amber-50' },
  ];

  const TABS: {id:Tab; label:string}[] = [
    {id:'policies', label:'Policy management'},
    {id:'analytics',label:'Analytics'},
    {id:'audit',    label:'Audit log'},
    {id:'queue',    label:'Ingestion queue'},
    {id:'report',   label:'Quarterly report'},
  ];

  return (
    <div className="w-full max-w-[1100px] mx-auto px-6 pt-8 pb-16">

      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-lg bg-navy flex items-center justify-center shrink-0">
          <Shield className="w-5 h-5 text-off-white"/>
        </div>
        <div>
          <h1 className="font-serif text-2xl text-ink">Admin dashboard</h1>
          <p className="text-muted-text text-sm">Policy management · field overrides · audit log · analytics</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {STAT_CARDS.map(({icon:Icon,label,value,color,bg})=>(
          <div key={label} className="bg-white rounded-lg border border-border-light p-4 flex items-center gap-3">
            <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center shrink-0',bg)}><Icon className={cn('w-4 h-4',color)}/></div>
            <div><p className="text-muted-text text-xs">{label}</p><p className="font-mono text-2xl font-medium text-ink">{value}</p></div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-off-white border border-border-light rounded-lg p-1 overflow-x-auto">
        {TABS.map(t=>(
          <button key={t.id} onClick={()=>setTab(t.id)}
            className={cn('px-4 py-1.5 text-sm font-medium rounded-md transition-colors whitespace-nowrap',
              tab===t.id?'bg-white text-ink shadow-sm':'text-muted-text hover:text-ink')}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── POLICY MANAGEMENT ─────────────────────────────────────────────── */}
      {tab==='policies' && (
        <div className="bg-white rounded-lg border border-border-light overflow-hidden">
          <div className="px-5 py-4 border-b border-border-light flex items-center justify-between">
            <div><h2 className="font-semibold text-ink">Policies</h2><p className="text-muted-text text-xs mt-0.5">Archive, restore, override fields, or trigger re-extraction</p></div>
            {loading&&<Loader2 className="w-4 h-4 text-muted-text animate-spin"/>}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr className="border-b border-border-light bg-off-white/50">
                {['Policy','Drug','Status','Actions'].map(h=><th key={h} className="text-left py-3 px-5 text-xs font-medium text-muted-text uppercase tracking-wide">{h}</th>)}
              </tr></thead>
              <tbody>
                {policies.map(p=>(
                  <PolicyTableRow key={p.id} pol={p}
                    onDelete={handleDelete} onRestore={handleRestore}
                    onOverride={setOverrideId} onReExtract={setReExtractId}/>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── ANALYTICS ────────────────────────────────────────────────────── */}
      {tab==='analytics' && (
        <div className="flex flex-col gap-6">

          {/* Payer restrictiveness rankings */}
          <div className="bg-white rounded-lg border border-border-light overflow-hidden">
            <div className="px-5 py-4 border-b border-border-light flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-accent-blue"/>
              <h2 className="font-semibold text-ink">Payer restrictiveness ranking</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead><tr className="border-b border-border-light bg-off-white/50">
                  {['Rank','Payer','Restrictiveness','PA required %','Avg step therapy','Policies'].map(h=><th key={h} className="text-left py-3 px-5 text-xs font-medium text-muted-text uppercase tracking-wide">{h}</th>)}
                </tr></thead>
                <tbody>
                  {rankings.map(r=>(
                    <tr key={r.payer_name} className="border-b border-border-light last:border-b-0 hover:bg-off-white/30">
                      <td className="py-3 px-5 font-mono text-sm text-muted-text">#{r.rank}</td>
                      <td className="py-3 px-5 font-medium text-ink text-sm">{r.payer_name}</td>
                      <td className="py-3 px-5">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden w-20">
                            <div className={cn('h-full rounded-full',r.restrictiveness_score>=70?'bg-restricted':r.restrictiveness_score>=45?'bg-conditional':'bg-covered')} style={{width:`${r.restrictiveness_score}%`}}/>
                          </div>
                          <span className={cn('text-xs font-semibold',r.restrictiveness_score>=70?'text-restricted':r.restrictiveness_score>=45?'text-conditional':'text-covered')}>{r.restrictiveness_score}</span>
                        </div>
                      </td>
                      <td className="py-3 px-5 text-sm text-ink">{r.avg_pa_required_pct}%</td>
                      <td className="py-3 px-5 text-sm text-ink">{r.avg_step_therapy_steps}</td>
                      <td className="py-3 px-5 text-sm text-muted-text">{r.policies_analyzed}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Coverage gaps */}
          <div className="bg-white rounded-lg border border-border-light overflow-hidden">
            <div className="px-5 py-4 border-b border-border-light flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-conditional"/>
              <h2 className="font-semibold text-ink">Coverage gaps</h2>
            </div>
            <div className="flex flex-col divide-y divide-border-light">
              {gaps.map((g,i)=>(
                <div key={i} className="px-5 py-3.5 flex items-start gap-4">
                  <span className={cn('text-xs px-2.5 py-1 rounded-full border font-medium shrink-0 mt-0.5',SEV[g.severity])}>{g.severity}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-ink font-medium capitalize">{g.drug} — {g.payer}</p>
                    <p className="text-xs text-muted-text mt-0.5">{g.description}</p>
                  </div>
                  <span className="text-xs text-hint shrink-0 capitalize">{g.gap_type.replace(/_/g,' ')}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Outlier policies */}
          <div className="bg-white rounded-lg border border-border-light overflow-hidden">
            <div className="px-5 py-4 border-b border-border-light flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-restricted"/>
              <h2 className="font-semibold text-ink">Outlier policies</h2>
              <span className="text-xs text-muted-text ml-1">(≥2 std deviations from mean)</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead><tr className="border-b border-border-light bg-off-white/50">
                  {['Policy','Metric','Value','Average','Z-score','Severity'].map(h=><th key={h} className="text-left py-3 px-5 text-xs font-medium text-muted-text uppercase tracking-wide">{h}</th>)}
                </tr></thead>
                <tbody>
                  {outliers.map((o,i)=>(
                    <tr key={i} className="border-b border-border-light last:border-b-0 hover:bg-off-white/30">
                      <td className="py-3 px-5"><p className="font-medium text-ink text-sm capitalize">{o.drug}</p><p className="text-xs text-muted-text">{o.payer}</p></td>
                      <td className="py-3 px-5 text-sm text-muted-text">{o.metric.replace(/_/g,' ')}</td>
                      <td className="py-3 px-5 text-sm font-semibold text-restricted">{o.metric_value}</td>
                      <td className="py-3 px-5 text-sm text-muted-text">{o.average_value}</td>
                      <td className="py-3 px-5 font-mono text-sm text-ink">{o.z_score.toFixed(1)}</td>
                      <td className="py-3 px-5"><span className={cn('text-xs px-2.5 py-1 rounded-full border font-medium',SEV[o.severity])}>{o.severity}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── AUDIT LOG ─────────────────────────────────────────────────────── */}
      {tab==='audit' && (
        <div className="bg-white rounded-lg border border-border-light overflow-hidden">
          <div className="px-5 py-4 border-b border-border-light"><h2 className="font-semibold text-ink">Audit log</h2><p className="text-muted-text text-xs mt-0.5">All admin actions logged in real time</p></div>
          {auditLogs.length===0
            ? <div className="text-center py-12 text-muted-text text-sm">No events yet — actions appear here after archiving or overriding a policy.</div>
            : <div className="divide-y divide-border-light">
                {auditLogs.map(log=>(
                  <div key={log.id} className="px-5 py-3.5 flex items-start gap-4">
                    <span className={cn('text-xs px-2.5 py-1 rounded-full border font-medium shrink-0 mt-0.5',ACTION_STYLES[log.action]??'bg-gray-50 text-gray-600 border-gray-200')}>{log.action.replace(/_/g,' ')}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-ink"><span className="font-medium">{log.admin_email}</span> acted on {log.entity_type} <code className="text-xs bg-gray-100 px-1 rounded">{log.entity_id.slice(0,16)}…</code></p>
                      {log.reason&&<p className="text-xs text-muted-text mt-0.5">{log.reason}</p>}
                    </div>
                    <span className="text-xs text-hint shrink-0">{new Date(log.created_at).toLocaleTimeString()}</span>
                  </div>
                ))}
              </div>
          }
        </div>
      )}

      {/* ── QUEUE ─────────────────────────────────────────────────────────── */}
      {tab==='queue' && (
        <div className="flex flex-col gap-6">
          <div className="bg-white rounded-lg border border-border-light p-6">
            <h2 className="font-semibold text-ink mb-4">Ingestion queue status</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                {label:'Pending',    value:queue?.total_pending??0,    color:'text-conditional'},
                {label:'Extracting', value:queue?.total_extracting??0, color:'text-accent-blue'},
                {label:'Success',    value:queue?.total_success??0,    color:'text-covered'},
                {label:'Failed',     value:queue?.total_failed??0,     color:'text-restricted'},
              ].map(({label,value,color})=>(
                <div key={label} className="bg-off-white rounded-lg border border-border-light p-4 text-center">
                  <p className={cn('font-mono text-3xl font-bold',color)}>{value}</p>
                  <p className="text-muted-text text-sm mt-1">{label}</p>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-text mt-4">Queue updates as PDFs are uploaded via the AI chat sidebar. Failed jobs can be re-extracted from the Policy management tab.</p>
          </div>
        </div>
      )}

      {/* ── QUARTERLY REPORT ──────────────────────────────────────────────── */}
      {tab==='report' && (
        <div className="flex flex-col gap-6">
          <div className="bg-white rounded-lg border border-border-light p-6">
            <div className="flex items-center gap-4 mb-6 flex-wrap">
              <h2 className="font-semibold text-ink flex items-center gap-2"><FileText className="w-4 h-4 text-accent-blue"/>Quarterly report</h2>
              <div className="flex items-center gap-2 ml-auto flex-wrap">
                <select value={reportYear} onChange={e=>setReportYear(Number(e.target.value))}
                  className="h-8 px-3 border border-border-light rounded-lg text-sm text-ink outline-none focus:border-accent-blue">
                  {[2026,2025,2024].map(y=><option key={y}>{y}</option>)}
                </select>
                <select value={reportQ} onChange={e=>setReportQ(Number(e.target.value))}
                  className="h-8 px-3 border border-border-light rounded-lg text-sm text-ink outline-none focus:border-accent-blue">
                  {[1,2,3,4].map(q=><option key={q} value={q}>Q{q}</option>)}
                </select>
                <button onClick={loadReport} className="h-8 px-4 bg-accent-blue text-white text-sm rounded-lg hover:bg-blue-700 transition-colors">Generate</button>
              </div>
            </div>

            {report ? (
              <>
                <div className="bg-off-white rounded-lg border border-border-light px-5 py-4 mb-6">
                  <p className="text-sm text-ink leading-relaxed">{report.summary}</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div className="bg-white border border-border-light rounded-lg p-4">
                    <p className="text-muted-text text-xs mb-2 font-medium uppercase tracking-wide">By type</p>
                    {Object.entries(report.by_type).map(([k,v])=>(
                      <div key={k} className="flex justify-between text-sm py-1">
                        <span className="text-muted-text capitalize">{k}</span>
                        <span className="font-semibold text-ink">{v}</span>
                      </div>
                    ))}
                  </div>
                  <div className="bg-white border border-border-light rounded-lg p-4">
                    <p className="text-muted-text text-xs mb-2 font-medium uppercase tracking-wide">By payer</p>
                    {Object.entries(report.by_payer).map(([k,v])=>(
                      <div key={k} className="flex justify-between text-sm py-1">
                        <span className="text-muted-text">{k}</span>
                        <span className="font-semibold text-ink">{v}</span>
                      </div>
                    ))}
                  </div>
                  <div className="bg-white border border-border-light rounded-lg p-4">
                    <p className="text-muted-text text-xs mb-2 font-medium uppercase tracking-wide">Top drugs</p>
                    {report.top_drugs.map((d,i)=>(
                      <div key={d} className="flex items-center gap-2 py-1">
                        <span className="w-5 h-5 rounded-full bg-accent-blue/10 text-accent-blue text-xs font-bold flex items-center justify-center shrink-0">{i+1}</span>
                        <span className="text-sm text-ink capitalize">{d}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="flex items-center justify-between bg-amber-50 border border-conditional/20 rounded-lg px-5 py-3">
                  <p className="text-sm text-ink font-semibold">Total changes in Q{report.quarter} {report.year}</p>
                  <span className="font-mono text-2xl font-bold text-conditional">{report.total_changes}</span>
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-muted-text text-sm">Select a year and quarter then click Generate.</div>
            )}
          </div>
        </div>
      )}

      {/* Modals */}
      {overrideId  && <OverrideModal  policyId={overrideId}  onClose={()=>setOverrideId(null)}  onDone={load}/>}
      {reExtractId && <ReExtractModal policyId={reExtractId} onClose={()=>setReExtractId(null)} onDone={load}/>}
    </div>
  );
}