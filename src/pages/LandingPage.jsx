import React, { useEffect } from "react";
import Chart from "chart.js/auto";
import { useNavigate } from "react-router-dom";
import "./LandingPage.css";

export default function LandingPage() {
    const navigate = useNavigate();

    useEffect(() => {
        const container = document.getElementById('architecture');
        const svgGroup = document.getElementById('links-group');
        const nodesGroup = document.getElementById('nodes-group');

        function getNodes() {
            const isMobile = window.innerWidth < 768;
            if (isMobile) {
                return [
                    { id: 'input', label: 'CloudWatch Logs', icon: '📝', x: 50, y: 8, color: '#00f2fe' },
                    { id: 'analyzer', label: 'Log Analyzer', icon: '🔍', x: 25, y: 22, color: '#4facfe' },
                    { id: 'remediation', label: 'Remediation Agent', icon: '🔧', x: 75, y: 22, color: '#4facfe' },
                    { id: 'runbook', label: 'Runbook Gen', icon: '📖', x: 50, y: 40, color: '#b026ff' },
                    { id: 'langsmith', label: 'LangSmith Tracing', icon: '📊', x: 50, y: 56, color: '#ff9900' },
                    { id: 'jira', label: 'JIRA Ticket', icon: '🎫', x: 25, y: 72, color: '#00f260' },
                    { id: 'n8n', label: 'n8n Orchestrator', icon: '🔄', x: 75, y: 72, color: '#ff4b2b' },
                    { id: 'slack', label: 'Slack Alert', icon: '💬', x: 50, y: 88, color: '#00f260' }
                ];
            }
            return [
                { id: 'input', label: 'CloudWatch Logs', icon: '📝', x: 12, y: 50, color: '#00f2fe' },
                { id: 'analyzer', label: 'Log Analyzer', icon: '🔍', x: 32, y: 32, color: '#4facfe' },
                { id: 'remediation', label: 'Remediation Agent', icon: '🔧', x: 32, y: 68, color: '#4facfe' },
                { id: 'runbook', label: 'Runbook Gen', icon: '📖', x: 52, y: 50, color: '#b026ff' },
                { id: 'langsmith', label: 'LangSmith Tracing', icon: '📊', x: 52, y: 15, color: '#ff9900' },
                { id: 'jira', label: 'JIRA Ticket', icon: '🎫', x: 72, y: 32, color: '#00f260' },
                { id: 'n8n', label: 'n8n Orchestrator', icon: '🔄', x: 72, y: 68, color: '#ff4b2b' },
                { id: 'slack', label: 'Slack Alert', icon: '💬', x: 88, y: 50, color: '#00f260' }
            ];
        }

        let nodes = getNodes();

        const links = [
            { source: 'input', target: 'analyzer', color: '#00f2fe' },
            { source: 'input', target: 'remediation', color: '#00f2fe' },
            { source: 'analyzer', target: 'runbook', color: '#4facfe' },
            { source: 'remediation', target: 'runbook', color: '#4facfe' },
            { source: 'analyzer', target: 'langsmith', color: '#ff9900', curve: true },
            { source: 'remediation', target: 'langsmith', color: '#ff9900', curve: true },
            { source: 'runbook', target: 'langsmith', color: '#ff9900' },
            { source: 'runbook', target: 'jira', color: '#b026ff' },
            { source: 'jira', target: 'n8n', color: '#00f260' },
            { source: 'n8n', target: 'slack', color: '#ff4b2b', label: 'Alert Trigger' },
            { source: 'slack', target: 'input', color: '#00f260', curve: true, reverseAnim: true }
        ];

        function hexToRgb(hex) {
            const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
            return result ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : '255, 255, 255';
        }

        function highlightNodes(sourceId, targetId, color) {
            const allNodes = document.querySelectorAll('.node-card');
            allNodes.forEach(node => {
                const id = node.getAttribute('data-id');
                if (id === sourceId || id === targetId) {
                    node.style.borderColor = color;
                    node.style.boxShadow = `0 10px 30px rgba(${hexToRgb(color)}, 0.5)`;
                    node.style.transform = 'scale(1.1)';
                } else {
                    node.style.opacity = '0.3';
                }
            });
        }

        function resetNodes() {
            const allNodes = document.querySelectorAll('.node-card');
            allNodes.forEach(node => {
                const nodeData = nodes.find(n => n.id === node.getAttribute('data-id'));
                node.style.borderColor = `rgba(${hexToRgb(nodeData.color)}, 0.3)`;
                node.style.boxShadow = `0 4px 20px rgba(${hexToRgb(nodeData.color)}, 0.1)`;
                node.style.opacity = '1';
                node.style.transform = 'scale(1)';
            });
        }

        function highlightLinks(nodeId, linkIdx = null) {
            const lights = document.querySelectorAll('.tube-light');
            const bases = document.querySelectorAll('.tube-base');
            lights.forEach((light, idx) => {
                let isConnected = false;
                if (linkIdx !== null) {
                    isConnected = (idx === linkIdx);
                } else {
                    isConnected = (light.getAttribute('data-source') === nodeId || light.getAttribute('data-target') === nodeId);
                    if (isConnected) {
                        const otherNodeId = light.getAttribute('data-source') === nodeId ? light.getAttribute('data-target') : light.getAttribute('data-source');
                        const otherNode = document.querySelector(`.node-card[data-id="${otherNodeId}"]`);
                        const color = light.getAttribute('data-color');
                        if (otherNode) {
                            otherNode.style.borderColor = color;
                            otherNode.style.boxShadow = `0 10px 30px rgba(${hexToRgb(color)}, 0.4)`;
                        }
                    }
                }
                if (isConnected) {
                    light.style.opacity = '1';
                    light.style.strokeWidth = '6px';
                    bases[idx].style.opacity = '0.5';
                } else {
                    light.style.opacity = '0.05';
                    bases[idx].style.opacity = '0.05';
                }
            });
        }

        function resetLinks() {
            const lights = document.querySelectorAll('.tube-light');
            const bases = document.querySelectorAll('.tube-base');
            lights.forEach(light => light.style.opacity = '1');
            bases.forEach(base => base.style.opacity = '0.15');
        }

        function renderNodes() {
            nodes = getNodes();
            nodesGroup.innerHTML = '';
            nodes.forEach(node => {
                const el = document.createElement('div');
                el.className = 'node-card';
                el.setAttribute('data-id', node.id);
                el.style.left = `${node.x}%`;
                el.style.top = `${node.y}%`;
                el.style.borderColor = `rgba(${hexToRgb(node.color)}, 0.3)`;
                el.style.boxShadow = `0 4px 20px rgba(${hexToRgb(node.color)}, 0.1)`;
                el.innerHTML = `
                    <div class="node-icon" style="color: ${node.color}; text-shadow: 0 0 15px ${node.color};">${node.icon}</div>
                    <div class="node-label">${node.label}</div>
                `;
                el.addEventListener('mouseenter', () => {
                    el.style.borderColor = node.color;
                    el.style.boxShadow = `0 10px 30px rgba(${hexToRgb(node.color)}, 0.5)`;
                    highlightLinks(node.id);
                });
                el.addEventListener('mouseleave', () => {
                    resetNodes();
                    resetLinks();
                });
                nodesGroup.appendChild(el);
            });
        }

        function renderLinks() {
            svgGroup.innerHTML = '';
            const rect = container.getBoundingClientRect();
            links.forEach((link, idx) => {
                const sourceNode = nodes.find(n => n.id === link.source);
                const targetNode = nodes.find(n => n.id === link.target);
                const sx = (sourceNode.x / 100) * rect.width;
                const sy = (sourceNode.y / 100) * rect.height;
                const tx = (targetNode.x / 100) * rect.width;
                const ty = (targetNode.y / 100) * rect.height;
                let pathD = '';
                if (link.curve) {
                    const curveHeight = sourceNode.id === 'langsmith' || targetNode.id === 'langsmith' ? 80 : Math.min(220, rect.height * 0.45);
                    pathD = `M ${sx} ${sy} C ${sx} ${sy - curveHeight}, ${tx} ${ty - curveHeight}, ${tx} ${ty}`;
                } else {
                    const dx = tx - sx;
                    const dy = ty - sy;
                    if (Math.abs(dx) < 20) {
                        pathD = `M ${sx} ${sy} C ${sx + 15} ${sy + dy / 2}, ${tx - 15} ${sy + dy / 2}, ${tx} ${ty}`;
                    } else if (Math.abs(dy) < 10) {
                        pathD = `M ${sx} ${sy} C ${sx + dx / 2} ${sy + 15}, ${tx - dx / 2} ${ty - 15}, ${tx} ${ty}`;
                    } else {
                        pathD = `M ${sx} ${sy} C ${sx + dx / 2} ${sy}, ${tx - dx / 2} ${ty}, ${tx} ${ty}`;
                    }
                }
                const baseNode = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                baseNode.setAttribute('d', pathD);
                baseNode.setAttribute('class', 'tube-base');
                baseNode.setAttribute('stroke', link.color);
                const lightNode = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                lightNode.setAttribute('d', pathD);
                let lightClass = 'tube-light';
                if (link.reverseAnim) lightClass += ' reverse';
                lightNode.setAttribute('class', lightClass);
                lightNode.setAttribute('stroke', link.color);
                lightNode.setAttribute('filter', 'url(#glow-strong)');
                lightNode.setAttribute('data-source', link.source);
                lightNode.setAttribute('data-target', link.target);
                lightNode.setAttribute('data-color', link.color);
                lightNode.addEventListener('mouseenter', () => {
                    highlightNodes(link.source, link.target, link.color);
                    highlightLinks(null, idx);
                });
                lightNode.addEventListener('mouseleave', () => {
                    resetNodes();
                    resetLinks();
                });
                svgGroup.appendChild(baseNode);
                svgGroup.appendChild(lightNode);
            });
        }

        const terminalLines = [
            { time: "17:10:01", entity: "system", class: "orchestrator", text: "Initializing CrewOps Multi-Agent Analytics..." },
            { time: "17:10:02", entity: "observability", class: "warning", text: "[LangSmith] Project 'crewops-prod' connected." },
            { time: "17:10:03", entity: "log-agent", class: "agent", text: "[Log Analyzer] Scanning production logs..." },
            { time: "17:10:04", entity: "observability", class: "success", text: "[LangSmith] Trace 'log-analysis-sq-1' started." },
            { time: "17:10:05", entity: "log-agent", class: "error", text: "CRITICAL: Memory pressure on node k8s-worker-3." },
            { time: "17:10:06", entity: "jira", class: "success", text: "JIRA Ticket OPS-892 created (Severity: CRITICAL)." },
            { time: "17:10:07", entity: "n8n-flow", class: "orchestrator", text: "[n8n] Workflow triggered: Slack Alert dispatched." },
            { time: "17:10:08", entity: "remediation", class: "agent", text: "[Remediation] Generating fix: HPA scaling update." },
            { time: "17:10:09", entity: "runbook-gen", class: "agent", text: "[Runbook] Synthesizing SRE cookbook #442..." },
            { time: "17:10:10", entity: "observability", class: "success", text: "[LangSmith] Trace complete. Latency: 1.2s." },
            { time: "17:10:11", entity: "system", class: "orchestrator", text: "System stabilized. Monitoring next cycle..." }
        ];

        const terminalBody = document.getElementById('typing-terminal');
        let currentLineIndex = 0;
        let typeTimeout;
        const MAX_TERMINAL_LINES = 12;

        function typeLine() {
            if (!terminalBody) return;
            const line = terminalLines[currentLineIndex % terminalLines.length];
            const lineEl = document.createElement('div');
            lineEl.className = 'terminal-line fade-in-line';
            const now = new Date();
            const timeStr = now.toTimeString().split(' ')[0];
            lineEl.innerHTML = `<span class="time">[${timeStr}]</span> <span class="${line.class}">[${line.entity}]</span> <span class="text">${line.text}</span>`;
            terminalBody.appendChild(lineEl);
            if (terminalBody.children.length > MAX_TERMINAL_LINES) terminalBody.removeChild(terminalBody.firstChild);
            terminalBody.scrollTop = terminalBody.scrollHeight;
            currentLineIndex++;
            typeTimeout = setTimeout(typeLine, 1000);
        }

        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const target = btn.getAttribute('data-tab');
                tabBtns.forEach(b => b.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById(target).classList.add('active');
            });
        });

        function initCharts() {
            const mttrChartEl = document.getElementById('mttrChart');
            if (mttrChartEl) {
                new Chart(mttrChartEl.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: ['Manual SRE', 'Legacy Automation', 'CrewOps'],
                        datasets: [{
                            label: 'MTTR (min)',
                            data: [120, 45, 4],
                            backgroundColor: ['rgba(148, 163, 184, 0.2)', 'rgba(79, 172, 254, 0.2)', 'rgba(0, 242, 254, 0.6)'],
                            borderColor: ['#94a3b8', '#4facfe', '#00f2fe'],
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                            x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                        },
                        plugins: { legend: { display: false } }
                    }
                });
            }
            const costChartEl = document.getElementById('costChart');
            if (costChartEl) {
                new Chart(costChartEl.getContext('2d'), {
                    type: 'line',
                    data: {
                        labels: ['W1', 'W2', 'W3', 'W4'],
                        datasets: [{
                            label: 'Accuracy (%)',
                            data: [82, 89, 94, 98],
                            borderColor: '#00f260',
                            backgroundColor: 'rgba(0, 242, 96, 0.1)',
                            fill: true,
                            tension: 0.4
                        }, {
                            label: 'Cost ($)',
                            data: [40, 32, 28, 22],
                            borderColor: '#ff4b2b',
                            borderDash: [5, 5],
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                            x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                        },
                        plugins: { legend: { labels: { color: '#94a3b8' } } }
                    }
                });
            }
        }

        let resizeTimer;
        let linkTimeout;
        const handleResize = () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                renderNodes();
                renderLinks();
            }, 100);
        };
        window.addEventListener('resize', handleResize);
        renderNodes();
        linkTimeout = setTimeout(renderLinks, 50);
        typeLine();
        initCharts();

        return () => {
            window.removeEventListener('resize', handleResize);
            clearTimeout(typeTimeout);
            clearTimeout(resizeTimer);
            clearTimeout(linkTimeout);
            const mttrCanvas = document.getElementById('mttrChart');
            if (mttrCanvas) {
                const chartInstance = Chart.getChart(mttrCanvas);
                if (chartInstance) chartInstance.destroy();
            }
            const costCanvas = document.getElementById('costChart');
            if (costCanvas) {
                const chartInstance = Chart.getChart(costCanvas);
                if (chartInstance) chartInstance.destroy();
            }
        };
    }, []);

    return (
        <div className="landing-page-wrapper">
            <style>{`
                .landing-page-wrapper {
                    min-height: 100vh;
                    overflow-x: hidden;
                    position: relative;
                }
            `}</style>
            <div className="background-grid"></div>
            <div className="ambient-glow glow-1"></div>
            <div className="ambient-glow glow-2"></div>
            <div className="ambient-glow glow-3"></div>
            <header className="navbar">
                <div className="logo">
                    <img src="logo_nobg.png" alt="CrewOps Logo" />
                    <span className="logo-text">CrewOps</span>
                </div>
                <nav>
                    <a href="#architecture">Architecture</a>
                    <a href="#market">Why CrewOps</a>
                    <a href="#terminal-section">Live Action</a>
                    <a href="#team">The Team</a>
                </nav>
                <button className="cta-button" onClick={() => navigate("/dashboard")}>View Main Product</button>
            </header>
            <main>
                <section className="hero">
                    <div className="hero-content">
                        <div className="badge">
                            <span className="badge-dot"></span> 24-Hour Sprint Ready
                        </div>
                        <h1>Automating DevOps<br />with <span className="gradient-text">Agentic Intelligence</span></h1>
                        <p>Detect production failures in real-time. Our Multi-Agent Suite explains root causes, generates SRE cookbooks, and automatically orchestrates fixes via Slack and JIRA.</p>
                        <div className="hero-buttons">
                            <button className="primary-btn" onClick={() => navigate("/dashboard")}>View Main Product</button>
                            <button className="secondary-btn">Read the Whitepaper</button>
                        </div>
                        <div className="stats-container">
                            <div className="stat-item">
                                <span className="stat-value">8</span>
                                <span className="stat-label">AI Agents</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-value">4</span>
                                <span className="stat-label">Squads</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-value">&lt;2s</span>
                                <span className="stat-label">Response Time</span>
                            </div>
                        </div>
                    </div>
                    <div className="architecture-visual" id="architecture">
                        <svg id="network-svg">
                            <defs>
                                <filter id="glow-strong" x="-50%" y="-50%" width="200%" height="200%">
                                    <feGaussianBlur stdDeviation="6" result="blur" />
                                    <feMerge>
                                        <feMergeNode in="blur" />
                                        <feMergeNode in="blur" />
                                        <feMergeNode in="SourceGraphic" />
                                    </feMerge>
                                </filter>
                            </defs>
                            <g id="links-group"></g>
                        </svg>
                        <div id="nodes-group"></div>
                    </div>
                </section>
                <section className="blueprint-section" id="blueprint">
                    <div className="section-title">
                        <h2>Technical <span>Blueprint</span></h2>
                        <p>A deep dive into the orchestration, data models, and agent workflows.</p>
                    </div>
                    <div className="blueprint-tabs-container">
                        <div className="blueprint-tabs">
                            <button className="tab-btn active" data-tab="performance">Performance</button>
                            <button className="tab-btn" data-tab="flow">Workflows</button>
                            <button className="tab-btn" data-tab="agents">Agent Logic</button>
                            <button className="tab-btn" data-tab="swot">SWOT Analysis</button>
                        </div>
                        <div className="tab-content-container">
                            <div className="tab-content active" id="performance">
                                <div className="chart-grid">
                                    <div className="chart-item">
                                        <h3>MTTR Comparison (Minutes)</h3>
                                        <canvas id="mttrChart"></canvas>
                                    </div>
                                    <div className="chart-item">
                                        <h3>Agent Accuracy vs Cost</h3>
                                        <canvas id="costChart"></canvas>
                                    </div>
                                </div>
                            </div>
                            <div className="tab-content" id="flow">
                                <div className="diagram-grid">
                                    <div className="diagram-item blueprint-card">
                                        <h3>Use Case Architecture</h3>
                                        <div className="blueprint-flow vertical">
                                            <div className="bp-node actor">SRE Engineer</div>
                                            <div className="bp-arrow">↓</div>
                                            <div className="bp-node process">Log Analysis</div>
                                            <div className="bp-arrow">↓</div>
                                            <div className="bp-split">
                                                <div className="bp-node ticket">JIRA Ops</div>
                                                <div className="bp-node alert">Slack Alert</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="diagram-item blueprint-card">
                                        <h3>Incident Process Flow</h3>
                                        <div className="blueprint-flow">
                                            <div className="bp-step">Ingestion</div>
                                            <div className="bp-arrow">→</div>
                                            <div className="bp-step highlight">Analysis</div>
                                            <div className="bp-arrow">→</div>
                                            <div className="bp-step">Ticket</div>
                                            <div className="bp-arrow">→</div>
                                            <div className="bp-step">Orchestration</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="tab-content" id="agents">
                                <div className="diagram-grid">
                                    <div className="diagram-item blueprint-card">
                                        <h3>Sequence Logic</h3>
                                        <div className="sequence-box">
                                            <div className="seq-line"><span>1. Log Push</span></div>
                                            <div className="seq-line"><span>2. AI Analysis</span></div>
                                            <div className="seq-line"><span>3. JIRA Ticket</span></div>
                                            <div className="seq-line"><span>4. n8n Slack Trigger</span></div>
                                        </div>
                                    </div>
                                    <div className="diagram-item blueprint-card">
                                        <h3>Squad Swimlanes</h3>
                                        <div className="swimlane-box">
                                            <div className="lane">
                                                <h5>Log Squad</h5>
                                                <div className="lane-node">Analyzer</div>
                                            </div>
                                            <div className="lane">
                                                <h5>Action Squad</h5>
                                                <div className="lane-node highlight">Remediation</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="tab-content" id="swot">
                                <div className="swot-grid">
                                    <div className="swot-card strength">
                                        <h4>Strengths</h4>
                                        <ul>
                                            <li>Multi-agent parallel processing</li>
                                            <li>Real-time n8n orchestration</li>
                                        </ul>
                                    </div>
                                    <div className="swot-card weakness">
                                        <h4>Weaknesses</h4>
                                        <ul>
                                            <li>High initial LLM token cost</li>
                                        </ul>
                                    </div>
                                    <div className="swot-card opportunity">
                                        <h4>Opportunities</h4>
                                        <ul>
                                            <li>Automated infrastructure self-healing</li>
                                        </ul>
                                    </div>
                                    <div className="swot-card threat">
                                        <h4>Threats</h4>
                                        <ul>
                                            <li>LLM hallucination risks</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
                <section className="market-section" id="market">
                    <div className="section-title">
                        <h2>Empowering Teams, <span>Not Replacing Jobs</span></h2>
                        <p>Autonomous squads orchestrated via <strong>n8n</strong> for intelligent incident response.</p>
                    </div>
                    <div className="market-content">
                        <div className="market-text">
                            <h3>The Noise Problem</h3>
                            <p>In a rapidly evolving tech landscape, true DevOps efficiency isn't about replacing engineers—it's about removing the noise. Incident response is currently plagued by "alert fatigue" and repetitive log parsing, which leads to burnout and slow resolution times.</p>
                            <br />
                            <h3>The CrewOps Solution</h3>
                            <p>Our multi-agent architecture acts as a highly-skilled SRE team. It digests complex logs in parallel, generates remediation playbooks, and orchestrates response via <strong>n8n</strong>, Slack, and JIRA.</p>
                            <ul className="market-list">
                                <li><span className="check">🔍</span> <strong>Log Analyzer Agent:</strong> Automatically parses gigabytes of logs to find root causes and timeline of events.</li>
                                <li><span className="check">🔧</span> <strong>Remediation Agent:</strong> Suggests immediate fixes, shell commands, and kubectl procedures to stabilize systems.</li>
                                <li><span className="check">📖</span> <strong>Runbook Generator:</strong> Synthesizes complete, operational SRE cookbooks for every detected incident.</li>
                                <li><span className="check">📊</span> <strong>LangSmith Tracing:</strong> Full observability suite for tracking agent performance, latency, and cost in real-time.</li>
                                <li><span className="check">🔄</span> <strong>n8n Orchestration:</strong> Intelligently routes alerts. Critical issues hit Slack <strong>instantly</strong>, while Low/Medium issues are queued for tomorrow's review.</li>
                            </ul>
                        </div>
                        <div className="market-visual">
                            <div className="stat-card">
                                <div className="stat-circle">
                                    <span>85%</span>
                                </div>
                                <h4>Reduction in MTTR</h4>
                                <p>Mean Time To Resolution drops significantly when humans don't have to search through gigabytes of logs manually.</p>
                            </div>
                        </div>
                    </div>
                </section>
                <section className="terminal-section" id="terminal-section">
                    <div className="section-title">
                        <h2>Watch the Agents <span>In Action</span></h2>
                        <p>Real-time collaboration across our 4 agent squads.</p>
                    </div>
                    <div className="terminal-window">
                        <div className="terminal-header">
                            <div className="terminal-buttons">
                                <span className="btn close"></span>
                                <span className="btn minimize"></span>
                                <span className="btn maximize"></span>
                            </div>
                            <div className="terminal-title">crewops-agent-runner ~ bash</div>
                        </div>
                        <div className="terminal-body" id="typing-terminal"></div>
                    </div>
                </section>
                <section className="team-section" id="team">
                    <div className="section-title">
                        <h2>Meet the <span>Crew</span></h2>
                        <p>The minds behind the orchestration.</p>
                    </div>
                    <div className="team-grid">
                        {[
                            { name: "Avin", initial: "A", colors: "#00f2fe, #4facfe" },
                            { name: "Charchit Bansal", initial: "CB", colors: "#4facfe, #b026ff" },
                            { name: "Monalisa Das", initial: "MD", colors: "#b026ff, #f8b500" },
                            { name: "Prakash Patil", initial: "PP", colors: "#f8b500, #00f260" },
                            { name: "Prathiba", initial: "P", colors: "#00f260, #00f2fe" },
                            { name: "Purushotham", initial: "P", colors: "#00f2fe, #b026ff" },
                            { name: "Rakshit Rangarajan", initial: "R", colors: "#b026ff, #00f260" },
                            { name: "Sannith K K", initial: "S", colors: "#f8b500, #4facfe" }
                        ].map(member => (
                            <div className="team-member" key={member.name}>
                                <div className="member-avatar" style={{ '--bg-gradient': `linear-gradient(135deg, ${member.colors})` }}>{member.initial}</div>
                                <h4>{member.name}</h4>
                            </div>
                        ))}
                    </div>
                </section>
            </main>
        </div>
    );
}
