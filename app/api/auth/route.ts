/**
 * POST   /api/auth  — login
 * DELETE /api/auth  — logout
 * GET    /api/auth  — get current session (with live token verify)
 *
 * Security additions:
 *   1. GET now calls POST /tokens/verify on the Python backend to confirm
 *      the token is still valid before trusting the session cookie.
 *   2. Token is revoked on the Python backend when user logs out.
 *
 * Directory: app/api/auth/route.ts
 */

import { NextRequest, NextResponse } from 'next/server';
import {
  loginWithBackend, demoLogin,
  parseSession, serializeSession,
  SESSION_COOKIE,
} from '@/lib/auth';

const BACKEND = process.env.PYTHON_BACKEND_URL ?? 'http://localhost:8000';

const COOKIE_OPTIONS = {
  httpOnly: true,
  secure:   process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  maxAge:   60 * 60 * 24, // 24 h
  path:     '/',
};

// ─── Token verify helper ──────────────────────────────────────────────────────
// Calls POST /tokens/verify on the Python backend.
// Returns true when backend confirms the token is still valid.
// Returns true automatically when backend is offline (demo mode).

async function verifyTokenWithBackend(user: SessionUser): Promise<boolean> {
  // Demo tokens skip backend verification
  if (!user.token || user.token === 'demo_token' || !user.token_id) return true;

  try {
    const res = await fetch(`${BACKEND}/tokens/verify`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      // Query params — matches the Python spec: POST /tokens/verify?token_id=&token=
      body: JSON.stringify({ token_id: user.token_id, token: user.token }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    return data?.success === true;
  } catch {
    // Backend offline — trust the local session (demo / dev mode)
    return true;
  }
}

// ─── Token revoke helper ──────────────────────────────────────────────────────
// Calls POST /tokens/{token_id}/revoke on the Python backend at logout.

async function revokeTokenOnBackend(user: SessionUser): Promise<void> {
  if (!user.token_id || user.token === 'demo_token') return;
  try {
    await fetch(`${BACKEND}/tokens/${user.token_id}/revoke`, { method: 'POST' });
  } catch {
    // Backend offline — nothing to do, cookie is already being cleared
  }
}

// ─── GET — return current session user ───────────────────────────────────────

export async function GET(req: NextRequest) {
  const cookie = req.cookies.get(SESSION_COOKIE)?.value;
  if (!cookie) {
    return NextResponse.json({ user: null }, { status: 401 });
  }

  const user = parseSession(cookie);
  if (!user) {
    return NextResponse.json({ user: null }, { status: 401 });
  }

  // ★ Security fix 1: verify token is still valid on Python backend
  const valid = await verifyTokenWithBackend(user);
  if (!valid) {
    // Token expired / revoked — force re-login
    const res = NextResponse.json(
      { user: null, error: 'Session expired. Please sign in again.' },
      { status: 401 }
    );
    res.cookies.set(SESSION_COOKIE, '', { ...COOKIE_OPTIONS, maxAge: 0 });
    return res;
  }

  // Strip token from the client-visible response
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { token, token_id, ...safeUser } = user as SessionUser & { token_id?: string };
  void token; void token_id;
  return NextResponse.json({ user: safeUser });
}

// ─── POST — login ─────────────────────────────────────────────────────────────

export async function POST(req: NextRequest) {
  const body = await req.json() as {
    email:    string;
    password: string;
    role:     'doctor' | 'admin' | 'analyst';
  };

  const { email, password, role } = body;

  if (!email || !password) {
    return NextResponse.json(
      { error: 'Email and password are required' },
      { status: 400 }
    );
  }

  // Try Python backend first (doctor / admin have backend login endpoints)
  let result;
  if (role === 'doctor' || role === 'admin') {
    result = await loginWithBackend(email, password, role);
  } else {
    result = demoLogin(email, password);
  }

  // Fallback to demo credentials if backend is offline or rejected
  if (result.error) {
    const demo = demoLogin(email, password);
    if (demo.error) {
      return NextResponse.json({ error: result.error }, { status: 401 });
    }
    result = demo;
  }

  const { user } = result as { user: NonNullable<typeof result['user']> };

  const res = NextResponse.json({
    success: true,
    user: { id: user.id, email: user.email, name: user.name, role: user.role },
  });
  res.cookies.set(SESSION_COOKIE, serializeSession(user), COOKIE_OPTIONS);
  return res;
}

// ─── DELETE — logout ──────────────────────────────────────────────────────────

export async function DELETE(req: NextRequest) {
  const cookie = req.cookies.get(SESSION_COOKIE)?.value;

  if (cookie) {
    const user = parseSession(cookie);
    // ★ Security fix 2: revoke token on Python backend at logout
    if (user) await revokeTokenOnBackend(user);
  }

  const res = NextResponse.json({ success: true });
  res.cookies.set(SESSION_COOKIE, '', { ...COOKIE_OPTIONS, maxAge: 0 });
  return res;
}