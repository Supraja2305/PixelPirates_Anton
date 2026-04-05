/**
 * Login Page — Supabase Auth
 * directory: app/login/page.tsx
 */
'use client';

import { useState, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { MapPin, BarChart3, Eye, EyeOff, ArrowLeft } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { createClient } from '@/lib/supabase/client';

function LoginForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const role = searchParams.get('role') || 'clinician';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const roleInfo = {
    clinician: {
      icon: MapPin,
      title: 'Clinician',
      color: 'bg-accent-blue/10 text-accent-blue',
    },
    analyst: {
      icon: BarChart3,
      title: 'Payer Analyst',
      color: 'bg-covered/10 text-covered',
    },
  };

  const currentRole = roleInfo[role as keyof typeof roleInfo] || roleInfo.clinician;
  const RoleIcon = currentRole.icon;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (authError) {
      setError(authError.message);
      setIsLoading(false);
      return;
    }

    router.push('/dashboard');
  };

  return (
    <main className="min-h-screen flex" role="main">
      {/* Left Panel - Branding */}
      <div
        className="hidden lg:flex lg:w-1/2 bg-navy relative overflow-hidden"
        aria-hidden="true"
      >
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.08) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.08) 1px, transparent 1px)
            `,
            backgroundSize: '60px 60px',
          }}
        />
        <div className="relative z-10 flex flex-col justify-center px-16">
          <div className="flex items-center gap-3 mb-8">
            <span className="flex items-center justify-center w-14 h-14 bg-accent-blue rounded-xl text-white font-bold text-2xl">
              Rx
            </span>
            <span className="text-white font-semibold text-2xl tracking-tight">
              Polarix
            </span>
          </div>
          <h1 className="text-white text-3xl max-w-sm leading-snug mb-10">
            <span className="text-accent-blue">Drug policy intelligence,</span>{' '}
            <span className="font-semibold">in real time.</span>
          </h1>
          <ul className="space-y-4">
            {[
              'Coverage across 8 major payers',
              'AI-grounded policy Q&A',
              'Real-time change monitoring',
            ].map((f) => (
              <li key={f} className="flex items-center gap-3 text-white/80 text-sm">
                <span className="w-2 h-2 rounded-full bg-accent-blue" />
                {f}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex flex-col justify-center items-center px-8 py-12 bg-white">
        <div className="w-full max-w-md">
          {/* Back Link */}
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-muted-text hover:text-ink mb-8 text-sm transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to role selection
          </Link>

          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-8">
            <span className="flex items-center justify-center w-12 h-12 bg-accent-blue rounded-xl text-white font-bold text-xl">
              Rx
            </span>
            <span className="text-navy font-semibold text-xl tracking-tight">
              Polarix
            </span>
          </div>

          {/* Role Badge */}
          <div className="flex items-center gap-2 mb-6">
            <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', currentRole.color)}>
              <RoleIcon className="w-4 h-4" strokeWidth={2} />
            </div>
            <span className="text-sm text-muted-text">
              Signing in as <span className="font-medium text-ink">{currentRole.title}</span>
            </span>
          </div>

          <h2 className="text-ink text-3xl font-bold mb-2">Sign in</h2>
          <p className="text-muted-text mb-8">Enter your credentials to access your account</p>

          {/* Error message */}
          {error && (
            <div className="mb-5 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
              {error}
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-ink mb-2">
                Email address
              </label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
                className="h-11"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label htmlFor="password" className="block text-sm font-medium text-ink">
                  Password
                </label>
                <Link href="/forgot-password" className="text-sm text-accent-blue hover:underline">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  className="h-11 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-text hover:text-ink transition-colors"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              className="w-full h-11 bg-accent-blue hover:bg-accent-blue/90 text-white"
              disabled={isLoading}
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </Button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-4 my-8">
            <div className="flex-1 h-px bg-border-light" />
            <span className="text-muted-text text-sm">or</span>
            <div className="flex-1 h-px bg-border-light" />
          </div>

          {/* Create account */}
          <p className="text-center text-muted-text">
            {"Don't have an account?"}{' '}
            <Link
              href={`/signup?role=${role}`}
              className="text-accent-blue font-medium hover:underline"
            >
              Create an account
            </Link>
          </p>

          {/* Demo Mode */}
          <Link
            href="/dashboard"
            className="block w-full mt-6 text-conditional text-sm hover:underline text-center"
          >
            Continue in demo mode →
          </Link>
        </div>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-white">
          <div className="animate-pulse text-muted-text">Loading...</div>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}