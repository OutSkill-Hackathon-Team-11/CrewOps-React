import { useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import gsap from 'gsap';
import {
  Home,
  BarChart3,
  Sliders,
  ChevronDown,
  Activity,
  Server,
  Ticket,
  Bot,
} from 'lucide-react';
import { useStore } from '../store';

import CustomSelect from './CustomSelect';
import { AVAILABLE_MODELS } from '../data/tuningConfig';

const navItems = [
  { path: '/', label: 'Home', icon: Home },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
  { path: '/rag', label: 'RAG Tuning', icon: Sliders },
];

const connections = [
  { name: 'OpenRouter', status: 'green' },
  { name: 'LangSmith', status: 'green' },
  { name: 'JIRA', status: 'red' },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setActivePage, activePage, tuning, updateTuning, models, userApiKey, setUserApiKey } = useStore();
  const sidebarRef = useRef(null);
  const itemsRef = useRef([]);

  const fastModels = models.length > 0 
    ? models.filter(m => m.category === 'fast') 
    : AVAILABLE_MODELS.filter(m => m.includes('mini') || m.includes('haiku') || m.includes('flash')).map(m => ({ id: m, name: m }));

  const reasoningModels = models.length > 0 
    ? models.filter(m => m.category === 'reasoning') 
    : AVAILABLE_MODELS.filter(m => !(m.includes('mini') || m.includes('haiku') || m.includes('flash'))).map(m => ({ id: m, name: m }));

  useEffect(() => {
    gsap.fromTo(
      sidebarRef.current,
      { x: -280, opacity: 0 },
      { x: 0, opacity: 1, duration: 0.6, ease: 'power3.out' }
    );
    gsap.fromTo(
      itemsRef.current.filter(Boolean),
      { x: -20, opacity: 0 },
      { x: 0, opacity: 1, duration: 0.4, stagger: 0.06, ease: 'power2.out', delay: 0.2 }
    );
  }, []);

  const handleNav = (path, label) => {
    setActivePage(label.toLowerCase());
    navigate(path);
  };

  return (
    <aside
      ref={sidebarRef}
      className="fixed left-0 top-0 h-screen w-64 z-50 flex flex-col glass border-r border-white/[0.06]"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 h-16 border-b border-white/[0.06] shrink-0">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center">
          <Bot size={18} className="text-white" />
        </div>
        <div>
          <span className="text-sm font-semibold text-slate-100">CrewOps</span>
          <span className="text-[10px] font-medium text-slate-500 block leading-none mt-0.5">AI Incident Platform</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <p className="px-2 text-[11px] font-semibold uppercase tracking-widest text-slate-500 mb-3">Navigation</p>
        {navItems.map((item, i) => {
          const isActive = location.pathname === item.path;
          const Icon = item.icon;
          return (
            <button
              key={item.path}
              ref={(el) => (itemsRef.current[i] = el)}
              onClick={() => handleNav(item.path, item.label)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-white/[0.08] text-slate-100 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
              }`}
            >
              <Icon size={17} strokeWidth={1.5} />
              {item.label}
            </button>
          );
        })}

        {/* Configuration */}
        <div className="pt-5 mt-5 border-t border-white/[0.06]">
          <p className="px-2 text-[11px] font-semibold uppercase tracking-widest text-slate-500 mb-4">Configuration</p>

          <div className="px-2 space-y-4">
            <CustomSelect 
              label="Fast Model"
              value={tuning.fast_model}
              options={fastModels}
              onChange={(v) => updateTuning({ fast_model: v })}
              icon={Server}
            />
            <CustomSelect 
              label="Reasoning Model"
              value={tuning.reasoning_model}
              options={reasoningModels}
              onChange={(v) => updateTuning({ reasoning_model: v })}
              icon={Bot}
            />
          </div>
        </div>

        {/* Status Indicators */}
        <div className="pt-5 mt-5 border-t border-white/[0.06]">
          <p className="px-2 text-[11px] font-semibold uppercase tracking-widest text-slate-500 mb-3">Connections</p>
          <div className="space-y-2 px-2">
            {connections.map((conn) => (
              <div key={conn.name} className="flex items-center justify-between">
                <span className="text-xs text-slate-400">{conn.name}</span>
                <span className={`pulse-dot ${conn.status} animate`} />
              </div>
            ))}
          </div>
        </div>
      </nav>

      {/* BYOK Section */}
      <div className="px-3 pb-4">
        <div className="glass-card p-3 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">BYOK</span>
            {userApiKey && (
              <button 
                onClick={() => setUserApiKey('')}
                className="text-[9px] text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                Reset
              </button>
            )}
          </div>
          <div className="relative">
            <input
              type="password"
              placeholder="Enter OpenRouter Key"
              value={userApiKey}
              onChange={(e) => setUserApiKey(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-[11px] text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-all placeholder:text-slate-600"
            />
            {!userApiKey && (
              <div className="absolute right-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-amber-500/40" title="Using default key" />
            )}
            {userApiKey && (
              <div className="absolute right-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" title="Using custom key" />
            )}
          </div>
          <p className="text-[9px] text-slate-500 leading-tight">
            {userApiKey ? "Using your custom API key for all LLM calls." : "Using the system's default OpenRouter API key."}
          </p>
        </div>
      </div>

      {/* System Health */}
      <div className="px-3 pb-4 shrink-0">
        <div className="glass-card px-4 py-3 flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-slate-300">System Status</p>
            <p className="text-[11px] text-emerald-400/80">Operational</p>
          </div>
          <Activity size={14} className="text-slate-500" />
        </div>
      </div>
    </aside>
  );
}
