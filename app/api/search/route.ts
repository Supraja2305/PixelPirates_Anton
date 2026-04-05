/**
 * GET /api/search?q=adalimumab
 * Keyword + semantic drug search.
 * Directory: app/api/search/route.ts
 */
import { NextRequest, NextResponse } from 'next/server';
import { searchDrugs } from '@/lib/backend';

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get('q') ?? '';
  if (q.trim().length < 2) {
    return NextResponse.json({ results: [], query: q });
  }
  const results = await searchDrugs(q);
  return NextResponse.json({ query: q, results });
}