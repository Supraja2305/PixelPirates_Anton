/**
 * GET /api/changes?type=narrowed&payer=Cigna
 * Returns policy change timeline with optional filters.
 * Directory: app/api/changes/route.ts
 */
import { NextRequest, NextResponse } from 'next/server';
import { getChanges } from '@/lib/backend';

export async function GET(req: NextRequest) {
  const typeFilter  = req.nextUrl.searchParams.get('type');
  const payerFilter = req.nextUrl.searchParams.get('payer');

  let changes = await getChanges();

  if (typeFilter)  changes = changes.filter(c => c.type  === typeFilter);
  if (payerFilter) changes = changes.filter(c => c.payer.toLowerCase().includes(payerFilter.toLowerCase()));

  return NextResponse.json({ changes, total: changes.length });
}