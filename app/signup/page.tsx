/**
 * Sign-Up Page — Supabase Auth
 * directory: app/signup/page.tsx
 */
'use client';

import { useState, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { MapPin, BarChart3, Eye, EyeOff, ArrowLeft, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { createClient } from '@/lib/supabase/client';

function SignupForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const role = searchParams.get('role') || 'clinician';

  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    organization: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
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

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const passwordRequirements = [
    { label: 'At least 8 characters', met: formData.password.length >= 8 },
    { label: 'Contains a number', met: /\d/.test(formData.password) },
    { label: 'Contains uppercase letter', met: /[A-Z]/.test(formData.password) },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    const supabase = createClient();

    const { error: signUpError } = await supabase.auth.signUp({
      email: formData.email,
      password: formData.password,
      options: {
        data: {
          first_name: formData.firstName,
          last_name: formData.lastName,
          organization: formData.organization,
          role,
        },
      },
    });

    if (signUpError) {
      setError(signUpError.message);
      setIsLoading(false);
      return;
    }

    // Sign in immediately after sign-up so session is active
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email: formData.email,
      password: formData.password,
    });

    if (signInError) {
      setError(signInError.message);
      setIsLoading(false);
      return;
    }

    router.push('/dashboard');
  };

  return (
    <main className="min-h-screen flex" role="main">
      {/* Left Panel */}
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

      {/* Right Panel */}
      <div className="flex-1 flex flex-col justify-center items-center px-8 py-12 bg-white overflow-y-auto">
        <div className="w-full max-w-md">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-muted-text hover:text-ink mb-6 text-sm transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to role selection
          </Link>

          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-6">
            <span className="flex items-center justify-center w-12 h-12 bg-accent-blue rounded-xl text-white font-bold text-xl">
              Rx
            </span>
            <span className="text-navy font-semibold text-xl tracking-tight">
              Polarix
            </span>
          </div>

          {/* Role Badge */}
          <div className="flex items-center gap-2 mb-4">
            <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', currentRole.color)}>
              <RoleIcon className="w-4 h-4" strokeWidth={2} />
            </div>
            <span className="text-sm text-muted-text">
              Creating account as <span className="font-medium text-ink">{currentRole.title}</span>
            </span>
          </div>

          <h2 className="text-ink text-3xl font-bold mb-2">Get started</h2>
          <p className="text-muted-text mb-6">Create your account to access drug policy intelligence</p>

          {/* Error */}
          {error && (
            <div className="mb-5 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Name Row */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="firstName" className="block text-sm font-medium text-ink mb-1.5">
                  First name
                </label>
                <Input
                  id="firstName"
                  name="firstName"
                  type="text"
                  value={formData.firstName}
                  onChange={handleChange}
                  placeholder="John"
                  required
                  className="h-10"
                />
              </div>
              <div>
                <label htmlFor="lastName" className="block text-sm font-medium text-ink mb-1.5">
                  Last name
                </label>
                <Input
                  id="lastName"
                  name="lastName"
                  type="text"
                  value={formData.lastName}
                  onChange={handleChange}
                  placeholder="Doe"
                  required
                  className="h-10"
                />
              </div>
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-ink mb-1.5">
                Work email
              </label>
              <Input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="you@company.com"
                required
                className="h-10"
              />
            </div>

            <div>
              <label htmlFor="organization" className="block text-sm font-medium text-ink mb-1.5">
                Organization
              </label>
              <Input
                id="organization"
                name="organization"
                type="text"
                value={formData.organization}
                onChange={handleChange}
                placeholder="Your hospital or company"
                required
                className="h-10"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-ink mb-1.5">
                Password
              </label>
              <div className="relative">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Create a strong password"
                  required
                  className="h-10 pr-10"
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
              {formData.password && (
                <ul className="mt-2 space-y-1">
                  {passwordRequirements.map((req, i) => (
                    <li
                      key={i}
                      className={cn(
                        'flex items-center gap-2 text-xs',
                        req.met ? 'text-covered' : 'text-muted-text'
                      )}
                    >
                      <Check className={cn('w-3 h-3', !req.met && 'opacity-30')} />
                      {req.label}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-ink mb-1.5">
                Confirm password
              </label>
              <Input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="Re-enter your password"
                required
                className="h-10"
              />
            </div>

            {/* Terms */}
            <div className="flex items-start gap-3 pt-2">
              <input
                type="checkbox"
                id="terms"
                checked={agreedToTerms}
                onChange={(e) => setAgreedToTerms(e.target.checked)}
                className="mt-1 w-4 h-4 rounded border-border-light text-accent-blue focus:ring-accent-blue"
                required
              />
              <label htmlFor="terms" className="text-sm text-muted-text">
                I agree to the{' '}
                <Link href="/terms" className="text-accent-blue hover:underline">
                  Terms of Service
                </Link>{' '}
                and{' '}
                <Link href="/privacy" className="text-accent-blue hover:underline">
                  Privacy Policy
                </Link>
              </label>
            </div>

            <Button
              type="submit"
              className="w-full h-11 bg-accent-blue hover:bg-accent-blue/90 text-white mt-4"
              disabled={isLoading || !agreedToTerms}
            >
              {isLoading ? 'Creating account...' : 'Create account'}
            </Button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-4 my-6">
            <div className="flex-1 h-px bg-border-light" />
            <span className="text-muted-text text-sm">or</span>
            <div className="flex-1 h-px bg-border-light" />
          </div>

          <p className="text-center text-muted-text">
            Already have an account?{' '}
            <Link
              href={`/login?role=${role}`}
              className="text-accent-blue font-medium hover:underline"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}

export default function SignupPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-white">
          <div className="animate-pulse text-muted-text">Loading...</div>
        </div>
      }
    >
      <SignupForm />
    </Suspense>
  );
}