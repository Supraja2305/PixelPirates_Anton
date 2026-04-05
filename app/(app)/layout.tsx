/**
 * App Layout — wraps all authenticated pages with NavBar.
 * Removed role prop (NavBar no longer accepts it).
 * Directory: app/(app)/layout.tsx
 */
import { NavBar } from '@/components/layout/navbar';

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-off-white">
      <NavBar />
      <main className="flex-1" role="main">
        {children}
      </main>
    </div>
  );
}