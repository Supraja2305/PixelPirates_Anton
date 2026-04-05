'use client';
import { Suspense } from 'react';
import { Shield } from 'lucide-react';

function AdminPageInner() {
  return (
    <div className="w-full max-w-[1100px] mx-auto px-6 pt-8 pb-16">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-lg bg-navy flex items-center justify-center">
          <Shield className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="font-serif text-2xl text-ink">Admin dashboard</h1>
          <p className="text-muted-text text-sm">Policy management · analytics · audit log</p>
        </div>
      </div>
      <div className="bg-white rounded-lg border border-border-light p-8 text-center text-muted-text">
        Admin panel loaded. Connect Python backend to enable full features.
      </div>
    </div>
  );
}

export default function AdminPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-[60vh]"><div className="w-6 h-6 rounded-full border-2 border-accent-blue border-t-transparent animate-spin" /></div>}>
      <AdminPageInner />
    </Suspense>
  );
}
