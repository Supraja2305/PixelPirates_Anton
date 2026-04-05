/**
 * GET /api/drug?name=adalimumab
 * Returns full payer coverage for a drug.
 * Proxies to Python backend or falls back to demo data.
 * Directory: app/api/drug/route.ts
 */
import { NextRequest, NextResponse } from 'next/server';
import { getDrugCoverage } from '@/lib/backend';

export async function GET(req: NextRequest) {
  const name = req.nextUrl.searchParams.get('name') ?? '';
  if (!name.trim()) {
    return NextResponse.json({ error: 'name param required' }, { status: 400 });
  }
  const data = await getDrugCoverage(name);
  if (!data) {
    return NextResponse.json({ error: `Drug "${name}" not found` }, { status: 404 });
  }
  return NextResponse.json(data);
}