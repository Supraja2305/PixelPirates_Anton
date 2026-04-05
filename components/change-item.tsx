/**
 * ChangeItem Component
 * Displays a single policy change entry
 */
import { cn } from '@/lib/utils';
import type { PolicyChange, ChangeType } from '@/types';

interface ChangeItemProps {
  change: PolicyChange;
}

const CHANGE_TYPE_CONFIG: Record<ChangeType, { label: string; bg: string; text: string; border: string }> = {
  narrowed: {
    label: 'Coverage narrowed',
    bg: 'bg-red-100',
    text: 'text-red-800',
    border: 'border-l-restricted',
  },
  expanded: {
    label: 'Coverage expanded',
    bg: 'bg-green-100',
    text: 'text-green-800',
    border: 'border-l-covered',
  },
  step: {
    label: 'Step therapy added',
    bg: 'bg-amber-100',
    text: 'text-amber-800',
    border: 'border-l-conditional',
  },
  admin: {
    label: 'Administrative change',
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    border: 'border-l-gray-400',
  },
};

export function ChangeItem({ change }: ChangeItemProps) {
  const config = CHANGE_TYPE_CONFIG[change.type];

  return (
    <div
      className={cn(
        'bg-white rounded-lg border border-border-light overflow-hidden',
        'border-l-4',
        config.border,
        'hover:bg-off-white/30 transition-colors'
      )}
    >
      <div className="p-5">
        {/* Header Row */}
        <div className="flex flex-wrap items-center gap-3 mb-3">
          <span
            className={cn(
              'inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium',
              config.bg,
              config.text
            )}
          >
            {config.label}
          </span>
          <span className="font-semibold text-ink">
            {change.payer} · {change.drug}
          </span>
          <span className="text-hint text-sm ml-auto">
            {change.date}
          </span>
        </div>

        {/* Summary */}
        <p className="text-ink text-sm leading-relaxed mb-3">
          {change.summary}
        </p>

        {/* Fields Changed */}
        <p className="text-hint text-sm">
          Fields changed: {change.fieldsChanged.join(' · ')}
        </p>
      </div>
    </div>
  );
}
