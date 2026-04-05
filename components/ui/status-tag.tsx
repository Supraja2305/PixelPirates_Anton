/**
 * StatusTag Component
 * Displays coverage status with appropriate styling
 */
import { cn } from '@/lib/utils';
import type { CoverageStatus } from '@/types';

interface StatusTagProps {
  status: CoverageStatus;
  className?: string;
}

const STATUS_CONFIG: Record<CoverageStatus, { label: string; bg: string; text: string }> = {
  covered: {
    label: 'Covered',
    bg: 'bg-green-100',
    text: 'text-green-800',
  },
  conditional: {
    label: 'Conditional',
    bg: 'bg-amber-100',
    text: 'text-amber-800',
  },
  restricted: {
    label: 'Restricted',
    bg: 'bg-red-100',
    text: 'text-red-800',
  },
};

export function StatusTag({ status, className }: StatusTagProps) {
  const config = STATUS_CONFIG[status];
  
  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium',
        config.bg,
        config.text,
        className
      )}
    >
      {config.label}
    </span>
  );
}
