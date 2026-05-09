import { useRef, useEffect, useState } from 'react';
import gsap from 'gsap';
import { Upload, FileText, Terminal, Brain, ArrowRight } from 'lucide-react';
import { useStore } from '../store';
import { sampleLogs, severityColors } from '../data/mockData';
import PipelineProgress from '../components/PipelineProgress';

export default function Home() {
  const { activeTab, setActiveTab, selectedSample, setSelectedSample, logContent, setLogContent, startPipeline, pipelineStatus } = useStore();
  const heroRef = useRef(null);
  const subtitleRef = useRef(null);
  const inputAreaRef = useRef(null);
  const pipelineRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    gsap.fromTo(heroRef.current, { y: 40, opacity: 0 }, { y: 0, opacity: 1, duration: 0.7, ease: 'power3.out' });
    gsap.fromTo(subtitleRef.current, { y: 20, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, ease: 'power2.out', delay: 0.2 });
    gsap.fromTo(inputAreaRef.current, { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, ease: 'power2.out', delay: 0.35 });
    gsap.fromTo(pipelineRef.current, { y: 40, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, ease: 'power2.out', delay: 0.5 });
  }, []);

  const handleDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = () => setDragOver(false);
  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => setLogContent(reader.result);
      reader.readAsText(file);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-10 pb-16">
      {/* Hero */}
      <div ref={heroRef} className="text-center pt-2">
        <h1 className="text-5xl font-extrabold tracking-tight text-balance leading-[1.1]">
          Observability.{' '}
          <span className="gradient-text">Triage.</span>{' '}
          <span className="gradient-text">Automate.</span>
        </h1>
        <p ref={subtitleRef} className="mt-4 text-base text-slate-500 max-w-xl mx-auto leading-relaxed">
          Let AI agents classify, diagnose, and resolve infrastructure incidents in seconds — not hours.
        </p>
      </div>

      {/* Input Area */}
      <div ref={inputAreaRef}>
        {/* Tabs */}
        <div className="flex gap-1 p-1 glass rounded-xl w-fit mx-auto mb-6">
          {[
            { id: 'log', label: 'Log Input', icon: Terminal },
            { id: 'sample', label: 'Sample Logs', icon: FileText },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-white/[0.08] text-slate-200 shadow-sm'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                <Icon size={16} strokeWidth={1.5} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className="glass rounded-2xl p-6">
          {activeTab === 'log' ? (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 ${
                dragOver
                  ? 'border-blue-500/50 bg-blue-500/5'
                  : 'border-white/[0.08] hover:border-white/[0.12]'
              }`}
            >
              <Upload size={32} className="mx-auto text-slate-600 mb-3" />
              <p className="text-sm text-slate-400 mb-1">Drop a log file here, or paste directly</p>
              <p className="text-xs text-slate-600">Supports .log, .txt, .json (max 10MB)</p>
              <textarea
                value={logContent}
                onChange={(e) => setLogContent(e.target.value)}
                placeholder="Or paste your log content here..."
                rows={5}
                className="mt-4 w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-4 py-3 text-sm text-slate-300 font-mono placeholder:text-slate-600 focus:outline-none focus:border-blue-500/30 resize-none"
              />
              {logContent && (
                <div className="mt-3 flex items-center justify-center gap-2 text-xs text-emerald-400">
                  <ArrowRight size={12} />
                  <span>{logContent.split('\n').length} lines loaded</span>
                </div>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-3">
              {sampleLogs.map((log) => {
                const isSelected = selectedSample === log.id;
                const colors = severityColors[log.severity];
                return (
                  <button
                    key={log.id}
                    onClick={() => setSelectedSample(isSelected ? null : log.id)}
                    className={`text-left p-4 rounded-xl border transition-all duration-200 ${
                      isSelected
                        ? 'border-blue-500/40 bg-blue-500/5'
                        : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="pulse-dot" style={{ backgroundColor: colors.dot }} />
                      <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: colors.text }}>
                        {log.severity}
                      </span>
                      <span className="text-[10px] text-slate-600 ml-auto">{log.source}</span>
                    </div>
                    <p className="text-sm font-medium text-slate-300 leading-snug">{log.title}</p>
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">{log.description}</p>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Pipeline */}
      <div ref={pipelineRef}>
        <PipelineProgress />
      </div>

      {/* Bottom CTA when done */}
      {pipelineStatus === 'completed' && (
        <div className="text-center animate-fade-in">
          <div className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl glass border-emerald-500/20">
            <Brain size={18} className="text-emerald-400" />
            <span className="text-sm text-slate-300">Pipeline complete — all agents have processed the incident</span>
          </div>
        </div>
      )}
    </div>
  );
}
