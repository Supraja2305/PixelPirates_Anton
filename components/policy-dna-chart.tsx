/**
 * PolicyDNAChart Component
 * Radar chart showing payer restriction fingerprint
 */
'use client';

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { DNA_DATA } from '@/types';

const PAYER_COLORS = {
  UHC: '#16A34A',   // covered green
  Cigna: '#DC2626', // restricted red
  BCBS: '#D97706',  // conditional amber
};

export function PolicyDNAChart() {
  return (
    <div className="bg-white rounded-lg border border-border-light p-6">
      <h3 className="font-semibold text-ink mb-1">
        Policy DNA — payer restriction fingerprint
      </h3>
      <p className="text-muted-text text-sm mb-4">
        Higher value = more restrictive on that dimension (scale 0–100)
      </p>
      
      {/* Legend */}
      <div className="flex flex-wrap gap-4 mb-4">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-sm bg-covered" />
          <span className="text-sm text-ink">UHC (score 82)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-sm bg-restricted" />
          <span className="text-sm text-ink">Cigna (score 41)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-sm bg-conditional" />
          <span className="text-sm text-ink">BCBS (score 74)</span>
        </div>
      </div>

      {/* Chart */}
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="70%" data={DNA_DATA}>
            <PolarGrid stroke="#E5E7EB" />
            <PolarAngleAxis 
              dataKey="dimension" 
              tick={{ fill: '#6B7280', fontSize: 12 }}
              tickLine={false}
            />
            <PolarRadiusAxis 
              angle={90} 
              domain={[0, 100]} 
              tick={{ fill: '#9CA3AF', fontSize: 10 }}
              tickCount={5}
              axisLine={false}
            />
            <Radar
              name="UHC"
              dataKey="UHC"
              stroke={PAYER_COLORS.UHC}
              fill={PAYER_COLORS.UHC}
              fillOpacity={0.15}
              strokeWidth={2}
            />
            <Radar
              name="Cigna"
              dataKey="Cigna"
              stroke={PAYER_COLORS.Cigna}
              fill={PAYER_COLORS.Cigna}
              fillOpacity={0.15}
              strokeWidth={2}
            />
            <Radar
              name="BCBS"
              dataKey="BCBS"
              stroke={PAYER_COLORS.BCBS}
              fill={PAYER_COLORS.BCBS}
              fillOpacity={0.15}
              strokeWidth={2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
