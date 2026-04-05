/**
 * NavBar — Admin link + Doctor view button navigates to /doctor
 * Directory: components/layout/navbar.tsx
 */
'use client';

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Shield, Stethoscope } from 'lucide-react';

const NAV_TABS = [
  { id: 'search',  label: 'Search',        href: '/dashboard' },
  { id: 'results', label: 'Drug results',   href: '/results'   },
  { id: 'compare', label: 'Compare payers', href: '/compare'   },
  { id: 'chat',    label: 'AI chat',        href: '/chat'      },
  { id: 'changes', label: 'Policy changes', href: '/changes'   },
];

export function NavBar() {
  const pathname = usePathname();
  const params   = useSearchParams();
  const drug     = params.get('drug') ?? '';
  const doctorHref = drug ? `/doctor?drug=${encodeURIComponent(drug)}` : '/doctor';

  return (
    <header className="sticky top-0 z-50 w-full bg-navy h-14" role="banner">
      <nav className="flex items-center justify-between h-full px-6 max-w-[1400px] mx-auto"
        role="navigation" aria-label="Main navigation">

        <div className="flex items-center gap-8">
          <Link href="/dashboard" prefetch={false} className="flex items-center gap-2" aria-label="MedPolicy Home">
            <span className="flex items-center justify-center w-8 h-8 bg-accent-blue rounded text-white font-semibold text-sm">Rx</span>
            <span className="text-off-white font-semibold text-lg tracking-tight">Polarix</span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {NAV_TABS.map(tab => {
              const isActive = pathname === tab.href || (tab.href === '/dashboard' && pathname === '/');
              const href = drug && ['results','compare','changes'].includes(tab.id)
                ? `${tab.href}?drug=${encodeURIComponent(drug)}` : tab.href;
              return (
                <Link key={tab.id} href={href} prefetch={false}
                  className={cn('relative px-3 py-2 text-sm font-medium transition-colors duration-200',
                    isActive ? 'text-white' : 'text-slate-400 hover:text-slate-200')}>
                  {tab.label}
                  {isActive && <span className="absolute bottom-0 left-3 right-3 h-0.5 bg-white rounded-full" aria-hidden />}
                </Link>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/admin" prefetch={false}
            className={cn('flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-full border transition-colors',
              pathname === '/admin'
                ? 'bg-white/20 text-white border-white/30'
                : 'text-slate-400 border-slate-600 hover:text-slate-200 hover:border-slate-400')}>
            <Shield className="w-3.5 h-3.5" /> Admin
          </Link>

          <Link href={doctorHref} prefetch={false}
            className={cn('flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-full border transition-colors',
              pathname === '/doctor'
                ? 'bg-covered text-white border-covered'
                : 'bg-green-900/30 text-green-400 border-green-700 hover:bg-green-800/40 hover:text-green-300')}>
            <Stethoscope className="w-3.5 h-3.5" /> Doctor view
          </Link>
        </div>
      </nav>
    </header>
  );
}

export default NavBar;