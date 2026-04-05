/**
 * GET /api/stats
 * Returns dashboard statistics (payers, policies, drugs, changes).
 * Directory: app/api/stats/route.ts
 */
import { NextResponse } from 'next/server';
import { getStats } from '@/lib/backend';

export async function GET() {
  const stats = await getStats();
  return NextResponse.json(stats);
}