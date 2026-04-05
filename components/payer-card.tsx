/**
 * PayerCard Component
 * Displays individual payer coverage information
 */
import { cn } from '@/lib/utils';
import { StatusTag } from '@/components/ui/status-tag';
import type { Payer } from '@/types';

interface PayerCardProps {
  payer: Payer;
}

const BORDER_COLORS = {
  covered: 'border-t-covered',
  conditional: 'border-t-conditional',
  restricted: 'border-t-restricted',
};

const SCORE_COLORS = {
  high: 'text-covered',
  medium: 'text-conditional',
  low: 'text-restricted',
};

function getScoreColor(score: number): string {
  if (score >= 70) return SCORE_COLORS.high;
  if (score >= 45) return SCORE_COLORS.medium;
  return SCORE_COLORS.low;
}

export function PayerCard({ payer }: PayerCardProps) {
  const isHighlightedPriorAuth = payer.priorAuth === 'Required';
  const isHighlightedStepTherapy = parseInt(payer.stepTherapy) > 1;

  return (
    <div
      className={cn(
        'bg-white rounded-lg border border-border-light overflow-hidden',
        'hover:border-muted-text hover:shadow-sm transition-all duration-200',
        'border-t-[3px]',
        BORDER_COLORS[payer.status]
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-light">
        <h3 className="font-semibold text-ink">{payer.name}</h3>
        <StatusTag status={payer.status} />
      </div>

      {/* Data Rows */}
      <div className="px-5 py-4">
        <div className="grid gap-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-text">Prior auth</span>
            <span className={cn(
              'font-medium',
              isHighlightedPriorAuth ? 'text-restricted' : 'text-ink'
            )}>
              {payer.priorAuth}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-text">Step therapy</span>
            <span className={cn(
              'font-medium',
              isHighlightedStepTherapy ? 'text-restricted' : 'text-ink'
            )}>
              {payer.stepTherapy}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-text">Indications</span>
            <span className="font-medium text-ink text-right max-w-[180px]">
              {payer.indications}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-text">Site of care</span>
            <span className="font-medium text-ink">{payer.siteOfCare}</span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-5 py-3 bg-off-white/50 border-t border-border-light">
        <span className="text-hint text-sm">
          {payer.effectiveDate}
          {payer.updated && ' · Updated'}
        </span>
        <span className={cn('font-semibold', getScoreColor(payer.score))}>
          Score {payer.score}
        </span>
      </div>
    </div>
  );
}
