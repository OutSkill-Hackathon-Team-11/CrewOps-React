import { forwardRef } from 'react';
import { Tag, AlertTriangle, Search, Wrench, BookOpen, Ticket, Bell, Check, Loader2 } from 'lucide-react';

const iconMap = {
  Tag, AlertTriangle, Search, Wrench, BookOpen, Ticket, Bell,
};

const statusConfig = {
  pending: { border: 'border-white/[0.04]', text: 'text-slate-600', icon: 'text-slate-700' },
  processing: { border: 'border-blue-500/30', text: 'text-blue-300', icon: 'text-blue-400' },
  done: { border: 'border-emerald-500/30', text: 'text-emerald-300', icon: 'text-emerald-400' },
};

const AgentCard = forwardRef(({ agent, index, isActive }, ref) => {
  const Icon = iconMap[agent.icon] || Tag;
  const cfg = statusConfig[agent.status];
  const elapsed = (agent.time / 1000).toFixed(1);

  return (
    <div
      ref={ref}
      data-agent-id={agent.id}
      className={`relative flex flex-col items-center gap-2.5 p-4 rounded-xl border transition-all duration-500 min-w-[100px] ${
        cfg.border
      } ${
        agent.status === 'processing'
          ? 'bg-blue-500/5 shadow-[0_0_20px_rgba(59,130,246,0.08)]'
          : agent.status === 'done'
          ? 'bg-emerald-500/5 shadow-[0_0_20px_rgba(52,211,153,0.06)]'
          : 'bg-white/[0.02]'
      } ${isActive ? 'scale-105' : ''}`}
    >
      {/* Icon */}
      <div className={`relative ${agent.status === 'done' ? cfg.icon : 'text-slate-500'}`}>
        {agent.status === 'processing' ? (
          <Loader2 size={22} className="animate-spin text-blue-400" />
        ) : agent.status === 'done' ? (
          <div className="w-[22px] h-[22px] rounded-full bg-emerald-500/20 flex items-center justify-center">
            <Check size={14} className="text-emerald-400" />
          </div>
        ) : (
          <Icon size={20} strokeWidth={1.5} />
        )}
      </div>

      {/* Label */}
      <span className={`text-[11px] font-medium leading-tight text-center ${cfg.text}`}>
        {agent.label}
      </span>

      {/* Time */}
      {agent.status === 'done' && (
        <span className="text-[10px] text-emerald-500/70 font-mono">{elapsed}s</span>
      )}

      {/* Progress bar */}
      {agent.status === 'processing' && (
        <div className="progress-bar w-full absolute bottom-2 left-3 right-3" style={{ width: 'calc(100% - 24px)' }}>
          <div
            className="progress-bar-fill"
            style={{
              width: `${Math.min((agent.time / 2000) * 100, 100)}%`,
            }}
          />
        </div>
      )}
    </div>
  );
});

AgentCard.displayName = 'AgentCard';
export default AgentCard;
