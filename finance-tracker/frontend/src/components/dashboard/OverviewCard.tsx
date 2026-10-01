import { motion } from 'framer-motion';
import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { cn, formatCurrency, formatPercent } from '@/lib/utils';

interface OverviewCardProps {
  title: string;
  value: number;
  change: number;
  sparkline: number[];
  icon: LucideIcon;
  gradient: string;
  delay?: number;
}

export function OverviewCard({ title, value, change, sparkline, icon: Icon, gradient, delay = 0 }: OverviewCardProps) {
  const chartData = sparkline.map((v, i) => ({ value: v, index: i }));
  const isPositive = change >= 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className="glass-card p-5 hover:border-white/20 transition-all duration-300 group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className={cn('p-2.5 rounded-xl bg-gradient-to-br', gradient)}>
          <Icon className="h-5 w-5 text-white" />
        </div>
        <div className={cn(
          'flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full',
          isPositive ? 'text-emerald-400 bg-emerald-400/10' : 'text-red-400 bg-red-400/10'
        )}>
          {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
          {formatPercent(change)}
        </div>
      </div>
      <p className="text-sm text-muted-foreground mb-1">{title}</p>
      <p className="text-2xl font-bold tracking-tight mb-3">{formatCurrency(value)}</p>
      <div className="h-12 opacity-60 group-hover:opacity-100 transition-opacity">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id={`grad-${title}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} fill={`url(#grad-${title})`} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
