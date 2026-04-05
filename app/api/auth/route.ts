/**
 * app/api/auth/route.ts — self-contained, no lib/auth import.
 * POST /api/auth  — login
 * DELETE /api/auth — logout  
 * GET /api/auth   — get session
 */
import { NextRequest, NextResponse } from 'next/server';

const BACKEND        = process.env.PYTHON_BACKEND_URL ?? 'http://localhost:8000';
const SESSION_COOKIE = 'polarix_session';
const COOKIE_OPTIONS = {
  httpOnly: true,
  secure:   process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  maxAge:   60 * 60 * 24,
  path:     '/',
};

// Demo credentials — work when backend is offline
const DEMO: Record<string, { password: string; name: string; role: string }> = {
  'doctor@antonrx.com':  { password: 'demo1234', name: 'Dr. Smith',    role: 'doctor'  },
  'admin@antonrx.com':   { password: 'demo1234', name: 'Admin User',   role: 'admin'   },
  'analyst@antonrx.com': { password: 'demo1234', name: 'Jane Analyst', role: 'analyst' },
};

function serialize(user: object): string { return btoa(JSON.stringify(user)); }
function parse(cookie: string)           { try { return JSON.parse(atob(cookie)); } catch { return null; } }

// ─── GET — current session ────────────────────────────────────────────────────
export async function GET(req: NextRequest) {
  const cookie = req.cookies.get(SESSION_COOKIE)?.value;
  if (!cookie) return NextResponse.json({ user: null }, { status: 401 });
  const user = parse(cookie);
  if (!user)  return NextResponse.json({ user: null }, { status: 401 });

  // Verify token with backend if available
  if (user.token && user.token !== 'demo_token' && user.token_id) {
    try {
      const res = await fetch(`${BACKEND}/tokens/verify`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token_id: user.token_id, token: user.token }),
      });
      if (!res.ok) {
        const out = NextResponse.json({ user: null, error: 'Session expired' }, { status: 401 });
        out.cookies.set(SESSION_COOKIE, '', { ...COOKIE_OPTIONS, maxAge: 0 });
        return out;
      }
    } catch { /* backend offline — trust local session */ }
  }

  const { token: _t, token_id: _ti, ...safe } = user;
  void _t; void _ti;
  return NextResponse.json({ user: safe });
}

// ─── POST — login ─────────────────────────────────────────────────────────────
export async function POST(req: NextRequest) {
  const { email, password, role } = await req.json();
  if (!email || !password) {
    return NextResponse.json({ error: 'Email and password required' }, { status: 400 });
  }

  let user = null;

  // Try Python backend for doctor/admin
  if (role === 'doctor' || role === 'admin') {
    try {
      const endpoint = role === 'doctor' ? '/doctors/login' : '/admin/login';
      const res  = await fetch(`${BACKEND}${endpoint}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (res.ok) {
        const data = await res.json();
        user = {
          id:       data.doctor_id ?? data.admin_id ?? '',
          email,
          name:     data.name ?? email,
          role,
          token:    data.token    ?? 'demo_token',
          token_id: data.token_id ?? null,
        };
      }
    } catch { /* backend offline */ }
  }

  // Fallback to demo credentials
  if (!user) {
    const demo = DEMO[email];
    if (!demo || demo.password !== password) {
      return NextResponse.json(
        { error: 'Invalid credentials. Demo: doctor@antonrx.com / demo1234' },
        { status: 401 }
      );
    }
    user = { id: `demo_${role}`, email, name: demo.name, role: demo.role, token: 'demo_token' };
  }

  const res = NextResponse.json({
    success: true,
    user: { id: user.id, email: user.email, name: user.name, role: user.role },
  });
  res.cookies.set(SESSION_COOKIE, serialize(user), COOKIE_OPTIONS);
  return res;
}

// ─── DELETE — logout ──────────────────────────────────────────────────────────
export async function DELETE(req: NextRequest) {
  const cookie = req.cookies.get(SESSION_COOKIE)?.value;
  if (cookie) {
    const user = parse(cookie);
    if (user?.token_id && user?.token !== 'demo_token') {
      try { await fetch(`${BACKEND}/tokens/${user.token_id}/revoke`, { method: 'POST' }); }
      catch { /* backend offline */ }
    }
  }
  const res = NextResponse.json({ success: true });
  res.cookies.set(SESSION_COOKIE, '', { ...COOKIE_OPTIONS, maxAge: 0 });
  return res;
}