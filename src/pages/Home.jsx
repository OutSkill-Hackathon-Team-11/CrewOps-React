import { useRef, useEffect, useState } from 'react';
import gsap from 'gsap';
import { Upload, FileText, Terminal, Brain, ArrowRight, Activity } from 'lucide-react';

import { useStore } from '../store';
import { sampleLogs, severityColors } from '../data/mockData';
import PipelineProgress from '../components/PipelineProgress';

export default function Home() {
  const { 
    activeTab, setActiveTab, selectedSample, setSelectedSample, 
    logContent, setLogContent, startPipeline, pipelineStatus,
    liveLogs, addLiveLog, clearLiveLogs
  } = useStore();

  useEffect(() => {
    if (activeTab === 'live') {
      const socket = new WebSocket('ws://localhost:8000/ws/logs');
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        addLiveLog(data);
      };
      return () => socket.close();
    }
  }, [activeTab]);

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
            { id: 'live', label: 'Live Stream', icon: Activity },
            { id: 'sample', label: 'Sample Logs', icon: FileText },
          ].map((tab) => {
            const Icon = tab.icon || Terminal;
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
        <div className="glass rounded-2xl p-6 min-h-[340px]">
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
              <input
                type="file"
                id="log-upload"
                className="hidden"
                accept=".log,.txt,.json"
                onChange={(e) => {
                  const file = e.target.files[0];
                  if (file) {
                    const reader = new FileReader();
                    reader.onload = () => setLogContent(reader.result);
                    reader.readAsText(file);
                  }
                }}
              />
              <Upload size={32} className="mx-auto text-slate-600 mb-3" />
              <p className="text-sm text-slate-400 mb-1">
                Drop a log file here, or{' '}
                <label 
                  htmlFor="log-upload" 
                  className="text-blue-400 hover:text-blue-300 cursor-pointer underline underline-offset-4 decoration-blue-400/30 hover:decoration-blue-300 transition-all font-medium"
                >
                  browse
                </label>
              </p>
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
          ) : activeTab === 'live' ? (
            <div className="flex flex-col h-[300px]">
              <div className="flex items-center justify-between mb-4 px-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Real-time Feed</span>
                </div>
                <button 
                  onClick={clearLiveLogs}
                  className="text-[10px] font-bold text-slate-500 hover:text-slate-300 uppercase tracking-widest transition-colors"
                >
                  Clear Feed
                </button>
              </div>
              <div className="flex-1 bg-black/40 rounded-xl border border-white/[0.06] overflow-y-auto p-4 font-mono text-[11px] space-y-1 custom-scrollbar">
                {liveLogs.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-slate-600 italic">
                    Waiting for logs from stream_logs.py...
                  </div>
                ) : (
                  liveLogs.map((log) => {
                    const isError = log.content.includes('ERROR');
                    const isWarn = log.content.includes('WARN');
                    return (
                      <div 
                        key={log.id} 
                        onClick={() => setLogContent(log.content)}
                        className="group flex gap-3 hover:bg-white/[0.03] cursor-pointer rounded px-2 py-0.5 transition-all"
                      >
                        <span className="text-slate-600 shrink-0">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                        <span className={`break-all ${isError ? 'text-rose-400' : isWarn ? 'text-amber-400' : 'text-slate-300'}`}>
                          {log.content}
                        </span>
                        <ArrowRight size={10} className="ml-auto text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    );
                  })
                )}
              </div>
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
