import { useRef, useEffect } from 'react';
import gsap from 'gsap';
import { Play, RotateCcw } from 'lucide-react';
import { useStore } from '../store';
import { agentConfig } from '../data/mockData';
import AgentCard from './AgentCard';

export default function PipelineProgress() {
  const { pipelineStatus, agents, startPipeline, resetPipeline } = useStore();
  const containerRef = useRef(null);
  const cardsRef = useRef([]);
  const buttonRef = useRef(null);
  const connectorRef = useRef([]);

  useEffect(() => {
    if (pipelineStatus === 'running') {
      gsap.fromTo(
        cardsRef.current.filter(Boolean),
        { y: 30, opacity: 0, scale: 0.9 },
        {
          y: 0,
          opacity: 1,
          scale: 1,
          duration: 0.45,
          stagger: 0.08,
          ease: 'back.out(1.4)',
        }
      );
    }
    if (pipelineStatus === 'completed') {
      gsap.to(buttonRef.current, {
        scale: 1.05,
        duration: 0.3,
        yoyo: true,
        repeat: 1,
        ease: 'power2.inOut',
      });
    }
  }, [pipelineStatus]);

  return (
    <div ref={containerRef} className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">Pipeline Execution</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {pipelineStatus === 'idle' && 'Configure input and analyze to start the pipeline'}
            {pipelineStatus === 'running' && 'Agents are processing your incident...'}
            {pipelineStatus === 'completed' && 'All agents completed successfully'}
          </p>
        </div>
        <button
          ref={buttonRef}
          onClick={pipelineStatus === 'running' ? undefined : pipelineStatus === 'completed' ? resetPipeline : startPipeline}
          disabled={pipelineStatus === 'running'}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
            pipelineStatus === 'running'
              ? 'bg-slate-700/30 text-slate-500 cursor-not-allowed'
              : pipelineStatus === 'completed'
              ? 'bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 border border-amber-500/20'
              : 'bg-gradient-to-r from-blue-600 to-violet-600 text-white hover:from-blue-500 hover:to-violet-500 shadow-lg shadow-blue-600/20'
          }`}
        >
          {pipelineStatus === 'idle' && <><Play size={15} /> Analyze</>}
          {pipelineStatus === 'running' && 'Processing...'}
          {pipelineStatus === 'completed' && <><RotateCcw size={15} /> Reset</>}
        </button>
      </div>

      {/* Agent Cards */}
      <div className="flex items-center gap-0">
        {agentConfig.map((agent, i) => (
          <div key={agent.id} className="flex items-center">
            <AgentCard
              ref={(el) => (cardsRef.current[i] = el)}
              agent={{ ...agents[i], icon: agent.icon }}
              index={i}
              isActive={i === useStore.getState().currentAgentIndex}
            />
            {i < agentConfig.length - 1 && (
              <div
                ref={(el) => (connectorRef.current[i] = el)}
                className={`w-6 h-px transition-colors duration-500 ${
                  agents[i]?.status === 'done' ? 'bg-emerald-500/40' : 'bg-white/[0.06]'
                }`}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
