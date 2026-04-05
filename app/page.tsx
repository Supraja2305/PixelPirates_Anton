/**
 * Landing / Role Selection Page
 * Clicking role cards → /login?role=...
 * Demo mode link → /dashboard
 */
'use client';

import Link from 'next/link';
import { MapPin, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';

const ROLES = [
  {
    id: 'clinician',
    icon: MapPin,
    title: "I'm a clinician",
    description: 'Clinical criteria and coverage by diagnosis',
  },
  {
    id: 'analyst',
    icon: BarChart3,
    title: "I'm a payer analyst",
    description: 'Compare policies and track changes across plans',
  },
] as const;

export default function LandingPage() {
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
            <li className="flex items-center gap-3 text-white/80 text-sm">
              <span className="w-2 h-2 rounded-full bg-accent-blue" />
              Coverage across 8 major payers
            </li>
            <li className="flex items-center gap-3 text-white/80 text-sm">
              <span className="w-2 h-2 rounded-full bg-accent-blue" />
              AI-grounded policy Q&A
            </li>
            <li className="flex items-center gap-3 text-white/80 text-sm">
              <span className="w-2 h-2 rounded-full bg-accent-blue" />
              Real-time change monitoring
            </li>
          </ul>
        </div>
      </div>

      {/* Right Panel - Role Selection */}
      <div className="flex-1 flex flex-col justify-center items-center px-8 py-12 bg-white">
        <div className="w-full max-w-lg">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-8">
            <span className="flex items-center justify-center w-12 h-12 bg-accent-blue rounded-xl text-white font-bold text-xl">
              Rx
            </span>
            <span className="text-navy font-semibold text-xl tracking-tight">
              Polarix
            </span>
          </div>

          <h2 className="text-ink text-3xl font-bold mb-2">Welcome back</h2>
          <p className="text-muted-text mb-10">Select your role to continue</p>

          {/* Role Cards → login page */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {ROLES.map((role) => (
              <Link
                key={role.id}
                href={`/login?role=${role.id}`}
                prefetch={false}
                className={cn(
                  'flex flex-col items-start p-6 rounded-lg border border-border-light',
                  'bg-white hover:border-accent-blue hover:shadow-md',
                  'transition-all duration-200 text-left group',
                  'focus:outline-none focus:ring-2 focus:ring-accent-blue focus:ring-offset-2'
                )}
                aria-label={`Continue as ${role.title}`}
              >
                <div
                  className={cn(
                    'w-10 h-10 rounded-lg flex items-center justify-center mb-4',
                    role.id === 'clinician'
                      ? 'bg-accent-blue/10'
                      : 'bg-covered/10'
                  )}
                >
                  <role.icon
                    className={cn(
                      'w-5 h-5',
                      role.id === 'clinician'
                        ? 'text-accent-blue'
                        : 'text-covered'
                    )}
                    strokeWidth={2}
                    aria-hidden="true"
                  />
                </div>
                <h3 className="text-ink font-semibold text-base mb-1">
                  {role.title}
                </h3>
                <p className="text-muted-text text-sm leading-snug">
                  {role.description}
                </p>
              </Link>
            ))}
          </div>

          {/* Demo Mode → goes directly to dashboard */}
          <div className="text-center mt-10">
            <Link
              href="/dashboard"
              className="text-conditional text-sm hover:underline"
            >
              Demo mode — no credentials required →
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}