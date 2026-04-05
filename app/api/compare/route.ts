/**
 * GET /api/compare?drug=rituximab
 * Returns side-by-side payer comparison for a drug.
 * Directory: app/api/compare/route.ts
 */
import { NextRequest, NextResponse } from 'next/server';
import { getDrugCoverage } from '@/lib/backend';

export async function GET(req: NextRequest) {
  const drug = req.nextUrl.searchParams.get('drug') ?? 'rituximab';
  const data = await getDrugCoverage(drug);
  if (!data) {
    return NextResponse.json({ error: `Drug "${drug}" not found` }, { status: 404 });
  }
  return NextResponse.json(data);
}