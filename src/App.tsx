import React, { useState, useEffect } from 'react';
import {
  Server,
  Activity,
  CheckCircle2,
  Flame,
  Target,
  ListTodo,
  Terminal,
  Code2,
  RefreshCw,
  Plus,
  Trash2,
  ExternalLink,
  Copy,
  Check,
  Zap,
  Cpu,
  Clock,
  Sparkles,
  Layers,
  ArrowRight
} from 'lucide-react';

interface HealthData {
  status: string;
  service: string;
  version: string;
  uptimeSeconds: number;
  timestamp: string;
  environment: string;
  systemMetrics: {
    heapUsedMb: number;
    heapTotalMb: number;
    rssMb: number;
  };
  counts: {
    tasks: number;
    habits: number;
    goals: number;
    logs: number;
  };
}

interface Task {
  id: string;
  title: string;
  description?: string;
  category: 'Work' | 'Health' | 'Learning' | 'Personal';
  priority: 'low' | 'medium' | 'high';
  completed: boolean;
  dueDate: string;
  createdAt: string;
}

interface Habit {
  id: string;
  name: string;
  description: string;
  frequency: 'daily' | 'weekly';
  targetDaysPerWeek: number;
  streakCount: number;
  bestStreak: number;
  category: string;
  history: string[];
  reminderTime: string;
  completedToday?: boolean;
}

interface Milestone {
  id: string;
  title: string;
  completed: boolean;
}

interface Goal {
  id: string;
  title: string;
  description: string;
  category: string;
  targetDate: string;
  progress: number;
  status: 'in_progress' | 'completed' | 'on_hold';
  milestones: Milestone[];
}

interface MotivationData {
  date: string;
  quote: string;
  author: string;
  theme: string;
  dailyPrompt: string;
  streakTip: string;
}

interface ApiLog {
  id: string;
  timestamp: string;
  method: string;
  path: string;
  statusCode: number;
  durationMs: number;
  ip: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'explorer' | 'data' | 'logs' | 'docs'>('overview');
  const [health, setHealth] = useState<HealthData | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [habits, setHabits] = useState<Habit[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [motivation, setMotivation] = useState<MotivationData | null>(null);
  const [logs, setLogs] = useState<ApiLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [copiedText, setCopiedText] = useState<string | null>(null);

  // Playground state
  const [selectedEndpoint, setSelectedEndpoint] = useState<string>('GET /api/health');
  const [requestMethod, setRequestMethod] = useState<'GET' | 'POST' | 'PUT' | 'DELETE'>('GET');
  const [requestPath, setRequestPath] = useState<string>('/api/health');
  const [requestBody, setRequestBody] = useState<string>('');
  const [responseStatus, setResponseStatus] = useState<number | null>(null);
  const [responseDuration, setResponseDuration] = useState<number | null>(null);
  const [responseData, setResponseData] = useState<any>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  // New task form state
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskCategory, setNewTaskCategory] = useState<'Work' | 'Health' | 'Learning' | 'Personal'>('Work');
  const [newTaskPriority, setNewTaskPriority] = useState<'low' | 'medium' | 'high'>('medium');

  // New habit form state
  const [newHabitName, setNewHabitName] = useState('');
  const [newHabitCategory, setNewHabitCategory] = useState('Focus');

  const fetchAllData = async () => {
    try {
      setLoading(true);
      const [healthRes, tasksRes, habitsRes, goalsRes, motivRes, logsRes] = await Promise.all([
        fetch('/api/health').then((r) => r.json()),
        fetch('/api/tasks').then((r) => r.json()),
        fetch('/api/habits').then((r) => r.json()),
        fetch('/api/goals').then((r) => r.json()),
        fetch('/api/motivation/daily').then((r) => r.json()),
        fetch('/api/system/logs').then((r) => r.json()),
      ]);

      setHealth(healthRes);
      setTasks(tasksRes.data || []);
      setHabits(habitsRes.data || []);
      setGoals(goalsRes.data || []);
      setMotivation(motivRes);
      setLogs(logsRes.logs || []);
    } catch (err) {
      console.error('Failed to fetch data from Motavi Backend:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(() => {
      fetch('/api/health').then((r) => r.json()).then(setHealth).catch(() => {});
      fetch('/api/system/logs').then((r) => r.json()).then((res) => setLogs(res.logs || [])).catch(() => {});
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(text);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const handleToggleTask = async (id: string) => {
    try {
      await fetch(`/api/tasks/${id}/toggle`, { method: 'POST' });
      const res = await fetch('/api/tasks').then((r) => r.json());
      setTasks(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteTask = async (id: string) => {
    try {
      await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
      const res = await fetch('/api/tasks').then((r) => r.json());
      setTasks(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;
    try {
      await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTaskTitle.trim(),
          category: newTaskCategory,
          priority: newTaskPriority,
        }),
      });
      setNewTaskTitle('');
      const res = await fetch('/api/tasks').then((r) => r.json());
      setTasks(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCheckInHabit = async (id: string) => {
    try {
      await fetch(`/api/habits/${id}/check-in`, { method: 'POST' });
      const res = await fetch('/api/habits').then((r) => r.json());
      setHabits(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateHabit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHabitName.trim()) return;
    try {
      await fetch('/api/habits', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newHabitName.trim(),
          category: newHabitCategory,
          frequency: 'daily',
          targetDaysPerWeek: 7,
        }),
      });
      setNewHabitName('');
      const res = await fetch('/api/habits').then((r) => r.json());
      setHabits(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleMilestone = async (goalId: string, milestoneId: string) => {
    try {
      await fetch(`/api/goals/${goalId}/milestones/${milestoneId}/toggle`, { method: 'POST' });
      const res = await fetch('/api/goals').then((r) => r.json());
      setGoals(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleResetSeeds = async () => {
    try {
      await fetch('/api/system/reset', { method: 'POST' });
      await fetchAllData();
    } catch (err) {
      console.error(err);
    }
  };

  const executePlaygroundRequest = async () => {
    setIsExecuting(true);
    setResponseData(null);
    setResponseStatus(null);
    setResponseDuration(null);

    const start = performance.now();
    try {
      const options: RequestInit = {
        method: requestMethod,
        headers: { 'Content-Type': 'application/json' },
      };
      if (['POST', 'PUT'].includes(requestMethod) && requestBody.trim()) {
        options.body = requestBody;
      }

      const res = await fetch(requestPath, options);
      const duration = Math.round(performance.now() - start);
      setResponseStatus(res.status);
      setResponseDuration(duration);

      const json = await res.json().catch(() => ({ message: 'Non-JSON response' }));
      setResponseData(json);
    } catch (err: any) {
      const duration = Math.round(performance.now() - start);
      setResponseStatus(500);
      setResponseDuration(duration);
      setResponseData({ error: err.message || 'Execution failed' });
    } finally {
      setIsExecuting(false);
      // Update logs
      fetch('/api/system/logs').then((r) => r.json()).then((res) => setLogs(res.logs || [])).catch(() => {});
    }
  };

  const selectPredefinedEndpoint = (method: 'GET' | 'POST' | 'PUT' | 'DELETE', path: string, defaultBody?: any) => {
    setRequestMethod(method);
    setRequestPath(path);
    setSelectedEndpoint(`${method} ${path}`);
    if (defaultBody) {
      setRequestBody(JSON.stringify(defaultBody, null, 2));
    } else {
      setRequestBody('');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Flame className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-bold tracking-tight text-white">Motavi Backend</h1>
                <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  v1.2.0 Node/Express
                </span>
              </div>
              <p className="text-xs text-slate-400">High-performance Motivation & Habit Orchestration API</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Health pill */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-slate-300 font-medium">0.0.0.0:3000</span>
              <span className="text-slate-500">|</span>
              <span className="text-emerald-400 font-mono">200 OK</span>
            </div>

            <button
              onClick={fetchAllData}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
              title="Refresh Telemetry"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>

            <button
              onClick={handleResetSeeds}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-rose-950/60 hover:text-rose-300 border border-slate-700 hover:border-rose-800/60 text-slate-300 transition-colors"
              title="Reset sample data"
            >
              Reset Seed Data
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-1 border-t border-slate-800/60">
          {[
            { id: 'overview', label: 'Overview & Diagnostics', icon: Activity },
            { id: 'explorer', label: 'API Playground', icon: Terminal },
            { id: 'data', label: 'Live Data Manager', icon: Layers },
            { id: 'logs', label: 'Server Logs', icon: Cpu, badge: logs.length },
            { id: 'docs', label: 'SDK & Client Specs', icon: Code2 },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 py-3 px-3.5 text-sm font-medium border-b-2 transition-all cursor-pointer ${
                  isActive
                    ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
                {tab.badge !== undefined && (
                  <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* TAB 1: OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Daily Motivation Card */}
            {motivation && (
              <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-950/70 via-slate-900 to-slate-900 border border-indigo-500/30 p-6 shadow-xl">
                <div className="absolute top-0 right-0 -mr-8 -mt-8 w-44 h-44 rounded-full bg-indigo-500/10 blur-2xl pointer-events-none"></div>
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                        {motivation.theme} Routine
                      </span>
                      <span className="text-xs text-slate-400">Endpoint: /api/motivation/daily</span>
                    </div>
                    <blockquote className="text-lg md:text-xl font-medium text-slate-100 italic">
                      "{motivation.quote}"
                    </blockquote>
                    <p className="text-sm text-slate-400">— {motivation.author}</p>
                  </div>
                  <div className="bg-slate-800/80 rounded-xl p-4 border border-slate-700/60 max-w-md">
                    <div className="flex items-center gap-2 text-xs font-semibold text-amber-400 mb-1">
                      <Sparkles className="w-4 h-4" />
                      <span>Daily Execution Prompt</span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">{motivation.dailyPrompt}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-slate-900/90 rounded-xl p-5 border border-slate-800 hover:border-slate-700 transition-all">
                <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
                  <span>ACTIVE HABITS</span>
                  <Flame className="w-4 h-4 text-orange-400" />
                </div>
                <div className="text-3xl font-bold text-white">{habits.length}</div>
                <div className="mt-2 text-xs text-slate-400 flex items-center gap-1">
                  <span className="text-emerald-400 font-medium">
                    {habits.filter((h) => h.completedToday).length} checked in
                  </span>{' '}
                  today
                </div>
              </div>

              <div className="bg-slate-900/90 rounded-xl p-5 border border-slate-800 hover:border-slate-700 transition-all">
                <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
                  <span>PENDING TASKS</span>
                  <ListTodo className="w-4 h-4 text-indigo-400" />
                </div>
                <div className="text-3xl font-bold text-white">
                  {tasks.filter((t) => !t.completed).length}{' '}
                  <span className="text-sm font-normal text-slate-500">/ {tasks.length} total</span>
                </div>
                <div className="mt-2 text-xs text-slate-400">
                  {tasks.filter((t) => t.completed).length} completed in sprint
                </div>
              </div>

              <div className="bg-slate-900/90 rounded-xl p-5 border border-slate-800 hover:border-slate-700 transition-all">
                <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
                  <span>STRATEGIC GOALS</span>
                  <Target className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-3xl font-bold text-white">{goals.length}</div>
                <div className="mt-2 text-xs text-slate-400">
                  Avg progress:{' '}
                  <span className="text-indigo-400 font-medium">
                    {goals.length > 0 ? Math.round(goals.reduce((a, g) => a + g.progress, 0) / goals.length) : 0}%
                  </span>
                </div>
              </div>

              <div className="bg-slate-900/90 rounded-xl p-5 border border-slate-800 hover:border-slate-700 transition-all">
                <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
                  <span>SYSTEM RUNTIME</span>
                  <Cpu className="w-4 h-4 text-purple-400" />
                </div>
                <div className="text-3xl font-bold text-white">
                  {health ? `${health.uptimeSeconds}s` : '—'}
                </div>
                <div className="mt-2 text-xs text-slate-400">
                  Memory:{' '}
                  <span className="font-mono text-purple-300">
                    {health?.systemMetrics.heapUsedMb ?? 0} MB
                  </span>
                </div>
              </div>
            </div>

            {/* Architecture & Endpoints Preview */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 bg-slate-900/80 rounded-2xl border border-slate-800 p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold text-white flex items-center gap-2">
                    <Server className="w-4 h-4 text-indigo-400" />
                    Motavi API Architecture & Routing
                  </h3>
                  <button
                    onClick={() => setActiveTab('explorer')}
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
                  >
                    Open API Playground <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  The backend provides high-frequency motivational telemetry, habit check-ins, task queues, and goal
                  milestone tracking. Ready for integration with iOS, Android (Kotlin/Compose), Flutter, and Web clients.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                  {[
                    { method: 'GET', path: '/api/health', desc: 'Heartbeat, uptime & memory' },
                    { method: 'GET', path: '/api/tasks', desc: 'Task catalog with filters' },
                    { method: 'POST', path: '/api/tasks', desc: 'Create new task items' },
                    { method: 'POST', path: '/api/tasks/:id/toggle', desc: 'Toggle completion state' },
                    { method: 'GET', path: '/api/habits', desc: 'Habits list with streak counters' },
                    { method: 'POST', path: '/api/habits/:id/check-in', desc: 'Instant check-in toggle' },
                    { method: 'GET', path: '/api/goals', desc: 'Strategic milestones & progress' },
                    { method: 'GET', path: '/api/analytics/summary', desc: 'Velocity & weekly metrics' },
                  ].map((ep, i) => (
                    <div
                      key={i}
                      onClick={() => {
                        selectPredefinedEndpoint(ep.method as any, ep.path);
                        setActiveTab('explorer');
                      }}
                      className="group p-3 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-800 hover:border-indigo-500/40 transition-all cursor-pointer"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                            ep.method === 'GET'
                              ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                              : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          }`}
                        >
                          {ep.method}
                        </span>
                        <code className="text-xs font-mono text-slate-200 group-hover:text-indigo-300 transition-colors">
                          {ep.path}
                        </code>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1">{ep.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Server Diagnostics Side Card */}
              <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 space-y-4">
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  Container Diagnostics
                </h3>
                <div className="space-y-3 text-xs">
                  <div className="flex justify-between py-2 border-b border-slate-800">
                    <span className="text-slate-400">Node Runtime</span>
                    <span className="font-mono text-slate-200">v22 (Linux x64)</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-slate-800">
                    <span className="text-slate-400">Port & Binding</span>
                    <span className="font-mono text-emerald-400">0.0.0.0:3000</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-slate-800">
                    <span className="text-slate-400">CORS Policy</span>
                    <span className="font-mono text-indigo-400">Enabled (Wildcard)</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-slate-800">
                    <span className="text-slate-400">Database Layer</span>
                    <span className="font-mono text-amber-300">In-Memory Mock Store</span>
                  </div>
                  <div className="flex justify-between py-2">
                    <span className="text-slate-400">Cloud SQL Ready</span>
                    <span className="text-emerald-400 font-medium">Compatible (Unix Socket)</span>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/40 text-[11px] text-slate-400 space-y-2">
                  <p className="font-medium text-slate-300">Persistence Note</p>
                  <p>
                    Data is kept in-memory for instant boot and live testing. When you're ready to store persistent
                    records in production, connect Cloud SQL PostgreSQL or Firebase.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: API PLAYGROUND */}
        {activeTab === 'explorer' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Endpoint Selector Left Column */}
            <div className="lg:col-span-4 space-y-3">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
                API Endpoint Catalog
              </h3>
              <div className="space-y-1.5 max-h-[640px] overflow-y-auto pr-1">
                {[
                  { m: 'GET', p: '/api/health', b: null, label: 'Health Check' },
                  { m: 'GET', p: '/api/tasks', b: null, label: 'List Tasks' },
                  {
                    m: 'POST',
                    p: '/api/tasks',
                    b: {
                      title: 'Ship new Motavi mobile widget',
                      category: 'Work',
                      priority: 'high',
                      dueDate: new Date().toISOString().split('T')[0],
                    },
                    label: 'Create Task',
                  },
                  { m: 'POST', p: '/api/tasks/task-1/toggle', b: null, label: 'Toggle Task (task-1)' },
                  { m: 'DELETE', p: '/api/tasks/task-4', b: null, label: 'Delete Task (task-4)' },
                  { m: 'GET', p: '/api/habits', b: null, label: 'List Habits' },
                  {
                    m: 'POST',
                    p: '/api/habits',
                    b: {
                      name: 'Cold Shower & Breathwork',
                      category: 'Health',
                      frequency: 'daily',
                      targetDaysPerWeek: 7,
                    },
                    label: 'Create Habit',
                  },
                  { m: 'POST', p: '/api/habits/habit-1/check-in', b: null, label: 'Check-in Habit (habit-1)' },
                  { m: 'GET', p: '/api/goals', b: null, label: 'List Goals' },
                  {
                    m: 'POST',
                    p: '/api/goals',
                    b: {
                      title: 'Run a 10K Marathon in under 45 minutes',
                      category: 'Fitness',
                      targetDate: '2026-12-31',
                      milestones: [
                        { id: 'm-10', title: '5K in 22 mins', completed: true },
                        { id: 'm-11', title: '10K under 45 mins', completed: false },
                      ],
                    },
                    label: 'Create Goal',
                  },
                  { m: 'GET', p: '/api/motivation/daily', b: null, label: 'Daily Motivation' },
                  { m: 'GET', p: '/api/analytics/summary', b: null, label: 'Analytics Summary' },
                  { m: 'GET', p: '/api/auth/me', b: null, label: 'Current User Profile' },
                  { m: 'GET', p: '/api/docs/spec', b: null, label: 'OpenAPI 3.0 Spec' },
                  { m: 'POST', p: '/api/system/reset', b: null, label: 'Reset Store Seeds' },
                ].map((item, idx) => {
                  const isCur = selectedEndpoint === `${item.m} ${item.p}`;
                  return (
                    <button
                      key={idx}
                      onClick={() => selectPredefinedEndpoint(item.m as any, item.p, item.b)}
                      className={`w-full text-left p-2.5 rounded-xl border text-xs flex items-center justify-between transition-all cursor-pointer ${
                        isCur
                          ? 'bg-indigo-950/60 border-indigo-500/60 text-white font-medium'
                          : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-800/80 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.5 rounded font-mono ${
                            item.m === 'GET'
                              ? 'bg-blue-500/20 text-blue-300'
                              : item.m === 'POST'
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : item.m === 'DELETE'
                              ? 'bg-rose-500/20 text-rose-300'
                              : 'bg-amber-500/20 text-amber-300'
                          }`}
                        >
                          {item.m}
                        </span>
                        <span className="truncate">{item.label}</span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono hidden sm:inline">{item.p}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Request & Response Right Column */}
            <div className="lg:col-span-8 space-y-4">
              {/* URL & Method Bar */}
              <div className="bg-slate-900 rounded-2xl border border-slate-800 p-4 space-y-4">
                <div className="flex flex-col sm:flex-row gap-2">
                  <select
                    value={requestMethod}
                    onChange={(e) => setRequestMethod(e.target.value as any)}
                    className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs font-bold font-mono text-indigo-400 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="DELETE">DELETE</option>
                  </select>

                  <div className="flex-1 relative">
                    <input
                      type="text"
                      value={requestPath}
                      onChange={(e) => setRequestPath(e.target.value)}
                      placeholder="/api/tasks"
                      className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <button
                    onClick={executePlaygroundRequest}
                    disabled={isExecuting}
                    className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
                  >
                    {isExecuting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                    <span>Send Request</span>
                  </button>
                </div>

                {/* Body editor if POST or PUT */}
                {['POST', 'PUT'].includes(requestMethod) && (
                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center text-xs text-slate-400">
                      <span>Request Payload (JSON)</span>
                      <button
                        onClick={() => {
                          try {
                            setRequestBody(JSON.stringify(JSON.parse(requestBody), null, 2));
                          } catch (_) {}
                        }}
                        className="text-[11px] text-indigo-400 hover:underline"
                      >
                        Format JSON
                      </button>
                    </div>
                    <textarea
                      rows={5}
                      value={requestBody}
                      onChange={(e) => setRequestBody(e.target.value)}
                      placeholder="{ ... }"
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs font-mono text-slate-300 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                )}

                {/* Quick Curl Snippet */}
                <div className="flex items-center justify-between text-[11px] text-slate-400 bg-slate-950 px-3 py-2 rounded-lg border border-slate-800 font-mono">
                  <div className="truncate mr-2">
                    curl -X {requestMethod} "http://localhost:3000{requestPath}"{' '}
                    {requestBody ? `-H "Content-Type: application/json" -d '${requestBody.replace(/\n/g, '')}'` : ''}
                  </div>
                  <button
                    onClick={() =>
                      copyToClipboard(
                        `curl -X ${requestMethod} "http://localhost:3000${requestPath}" ${
                          requestBody
                            ? `-H "Content-Type: application/json" -d '${requestBody.replace(/\n/g, '')}'`
                            : ''
                        }`
                      )
                    }
                    className="text-slate-400 hover:text-white transition-colors"
                    title="Copy cURL"
                  >
                    {copiedText ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Response Panel */}
              <div className="bg-slate-900 rounded-2xl border border-slate-800 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300">Server Response</span>
                  {responseStatus !== null && (
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${
                          responseStatus >= 200 && responseStatus < 300
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        }`}
                      >
                        {responseStatus}
                      </span>
                      {responseDuration !== null && (
                        <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                          <Clock className="w-3 h-3 text-slate-500" />
                          {responseDuration}ms
                        </span>
                      )}
                    </div>
                  )}
                </div>

                <div className="relative">
                  <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-[380px] leading-relaxed">
                    {responseData !== null ? (
                      JSON.stringify(responseData, null, 2)
                    ) : (
                      <span className="text-slate-600">// Click "Send Request" to invoke this endpoint</span>
                    )}
                  </pre>
                  {responseData !== null && (
                    <button
                      onClick={() => copyToClipboard(JSON.stringify(responseData, null, 2))}
                      className="absolute top-3 right-3 p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700"
                      title="Copy Response"
                    >
                      {copiedText ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: LIVE DATA MANAGER */}
        {activeTab === 'data' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* TASKS COLUMN */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ListTodo className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-sm font-semibold text-white">Tasks Catalog</h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">{tasks.length} items</span>
              </div>

              {/* Add Task Form */}
              <form onSubmit={handleCreateTask} className="p-3 bg-slate-900 rounded-xl border border-slate-800 space-y-2">
                <input
                  type="text"
                  placeholder="New task title..."
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
                <div className="flex gap-2">
                  <select
                    value={newTaskCategory}
                    onChange={(e) => setNewTaskCategory(e.target.value as any)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-300"
                  >
                    <option value="Work">Work</option>
                    <option value="Health">Health</option>
                    <option value="Learning">Learning</option>
                    <option value="Personal">Personal</option>
                  </select>
                  <select
                    value={newTaskPriority}
                    onChange={(e) => setNewTaskPriority(e.target.value as any)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-300"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                  <button
                    type="submit"
                    className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add</span>
                  </button>
                </div>
              </form>

              {/* Tasks List */}
              <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                {tasks.map((task) => (
                  <div
                    key={task.id}
                    className={`p-3 rounded-xl border transition-all ${
                      task.completed
                        ? 'bg-slate-900/40 border-slate-800/60 opacity-60'
                        : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2.5">
                        <button
                          onClick={() => handleToggleTask(task.id)}
                          className="mt-0.5 text-slate-400 hover:text-emerald-400 transition-colors"
                        >
                          <CheckCircle2
                            className={`w-4 h-4 ${task.completed ? 'text-emerald-400 fill-emerald-400/20' : ''}`}
                          />
                        </button>
                        <div>
                          <p
                            className={`text-xs font-medium ${
                              task.completed ? 'line-through text-slate-400' : 'text-slate-200'
                            }`}
                          >
                            {task.title}
                          </p>
                          {task.description && (
                            <p className="text-[11px] text-slate-400 mt-0.5">{task.description}</p>
                          )}
                          <div className="flex items-center gap-2 mt-2">
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                              {task.category}
                            </span>
                            <span
                              className={`text-[10px] px-1.5 py-0.5 rounded ${
                                task.priority === 'high'
                                  ? 'bg-rose-500/10 text-rose-400'
                                  : task.priority === 'medium'
                                  ? 'bg-amber-500/10 text-amber-400'
                                  : 'bg-blue-500/10 text-blue-400'
                              }`}
                            >
                              {task.priority}
                            </span>
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteTask(task.id)}
                        className="text-slate-500 hover:text-rose-400 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* HABITS COLUMN */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Flame className="w-4 h-4 text-orange-400" />
                  <h3 className="text-sm font-semibold text-white">Habits & Streaks</h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">{habits.length} habits</span>
              </div>

              {/* Add Habit Form */}
              <form onSubmit={handleCreateHabit} className="p-3 bg-slate-900 rounded-xl border border-slate-800 space-y-2">
                <input
                  type="text"
                  placeholder="New habit name..."
                  value={newHabitName}
                  onChange={(e) => setNewHabitName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
                <div className="flex gap-2">
                  <select
                    value={newHabitCategory}
                    onChange={(e) => setNewHabitCategory(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-300"
                  >
                    <option value="Focus">Focus</option>
                    <option value="Health">Health</option>
                    <option value="Mindset">Mindset</option>
                    <option value="Fitness">Fitness</option>
                  </select>
                  <button
                    type="submit"
                    className="px-3 py-1 bg-orange-600 hover:bg-orange-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Track</span>
                  </button>
                </div>
              </form>

              {/* Habits List */}
              <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                {habits.map((habit) => (
                  <div key={habit.id} className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2.5">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="text-xs font-semibold text-slate-100">{habit.name}</h4>
                        <p className="text-[11px] text-slate-400 mt-0.5">{habit.description}</p>
                      </div>
                      <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-orange-500/10 border border-orange-500/20 text-orange-400 text-xs font-bold font-mono">
                        <Flame className="w-3.5 h-3.5 fill-orange-400" />
                        <span>{habit.streakCount}d</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <div className="text-[10px] text-slate-400">
                        Best: <span className="text-slate-300 font-semibold">{habit.bestStreak}d</span> •{' '}
                        {habit.frequency} ({habit.targetDaysPerWeek}x/wk)
                      </div>
                      <button
                        onClick={() => handleCheckInHabit(habit.id)}
                        className={`px-3 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all cursor-pointer ${
                          habit.completedToday
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
                        }`}
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>{habit.completedToday ? 'Done Today' : 'Check In'}</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* GOALS COLUMN */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-emerald-400" />
                  <h3 className="text-sm font-semibold text-white">Strategic Goals</h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">{goals.length} goals</span>
              </div>

              {/* Goals List */}
              <div className="space-y-3 max-h-[570px] overflow-y-auto pr-1">
                {goals.map((goal) => (
                  <div key={goal.id} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="text-xs font-bold text-slate-100">{goal.title}</h4>
                        <p className="text-[11px] text-slate-400 mt-0.5">{goal.description}</p>
                      </div>
                      <span className="text-xs font-mono font-bold text-indigo-400">{goal.progress}%</span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-indigo-500 to-emerald-400 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${goal.progress}%` }}
                      ></div>
                    </div>

                    {/* Milestones */}
                    <div className="space-y-1.5 pt-1">
                      <p className="text-[10px] uppercase tracking-wider font-semibold text-slate-500">Milestones</p>
                      {goal.milestones.map((m) => (
                        <div
                          key={m.id}
                          onClick={() => handleToggleMilestone(goal.id, m.id)}
                          className="flex items-center gap-2 text-xs text-slate-300 hover:text-white cursor-pointer select-none group"
                        >
                          <div
                            className={`w-3.5 h-3.5 rounded border flex items-center justify-center transition-colors ${
                              m.completed
                                ? 'bg-indigo-600 border-indigo-500 text-white'
                                : 'border-slate-700 bg-slate-950 group-hover:border-slate-500'
                            }`}
                          >
                            {m.completed && <Check className="w-2.5 h-2.5" />}
                          </div>
                          <span className={`text-[11px] ${m.completed ? 'line-through text-slate-500' : ''}`}>
                            {m.title}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: SERVER LOGS */}
        {activeTab === 'logs' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-purple-400" />
                  Live HTTP Telemetry Stream
                </h3>
                <p className="text-xs text-slate-400">
                  Real-time incoming requests captured by the Express backend middleware
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-slate-400">{logs.length} logged events</span>
              </div>
            </div>

            <div className="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
              <div className="max-h-[580px] overflow-y-auto divide-y divide-slate-800/60 font-mono text-xs">
                {logs.length === 0 ? (
                  <div className="p-8 text-center text-slate-500">
                    No requests captured yet. Trigger endpoints in the API Playground!
                  </div>
                ) : (
                  logs.map((log) => (
                    <div
                      key={log.id}
                      className="p-3 px-4 flex flex-wrap items-center justify-between gap-3 hover:bg-slate-800/40 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            log.statusCode >= 200 && log.statusCode < 300
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          }`}
                        >
                          {log.statusCode}
                        </span>
                        <span
                          className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                            log.method === 'GET'
                              ? 'text-blue-400'
                              : log.method === 'POST'
                              ? 'text-emerald-400'
                              : 'text-amber-400'
                          }`}
                        >
                          {log.method}
                        </span>
                        <span className="text-slate-200">{log.path}</span>
                      </div>

                      <div className="flex items-center gap-4 text-[11px] text-slate-400">
                        <span>{log.durationMs}ms</span>
                        <span className="text-slate-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: SDK & CLIENT DOCS */}
        {activeTab === 'docs' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <Code2 className="w-4 h-4 text-indigo-400" />
                Client Integration & SDK Guide
              </h3>
              <p className="text-xs text-slate-400">
                Code examples for connecting your frontend applications (React, Flutter, Android, Swift) to Motavi Backend
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* React / TypeScript Client */}
              <div className="bg-slate-900 rounded-2xl border border-slate-800 p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">React / TypeScript Client</h4>
                  <button
                    onClick={() =>
                      copyToClipboard(`// Motavi API Client
const MOTAVI_API_BASE = 'https://ais-dev-...run.app';

export async function fetchDailyHabits() {
  const res = await fetch(\`\${MOTAVI_API_BASE}/api/habits\`);
  if (!res.ok) throw new Error('Failed to fetch habits');
  return res.json();
}

export async function checkInHabit(habitId: string) {
  const res = await fetch(\`\${MOTAVI_API_BASE}/api/habits/\${habitId}/check-in\`, {
    method: 'POST',
  });
  return res.json();
}`)
                    }
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                  >
                    <Copy className="w-3 h-3" /> Copy
                  </button>
                </div>
                <pre className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80 text-[11px] font-mono text-slate-300 overflow-x-auto">
{`// Motavi API Client (TypeScript)
const MOTAVI_API_BASE = 'http://localhost:3000';

export async function fetchDailyHabits() {
  const res = await fetch(\`\${MOTAVI_API_BASE}/api/habits\`);
  if (!res.ok) throw new Error('Failed to fetch habits');
  return res.json();
}

export async function checkInHabit(habitId: string) {
  const res = await fetch(\`\${MOTAVI_API_BASE}/api/habits/\${habitId}/check-in\`, {
    method: 'POST',
  });
  return res.json();
}`}
                </pre>
              </div>

              {/* Dart / Flutter Client */}
              <div className="bg-slate-900 rounded-2xl border border-slate-800 p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Flutter / Dart Client</h4>
                  <button
                    onClick={() =>
                      copyToClipboard(`import 'dart:convert';
import 'package:http/http.dart' as http;

class MotaviService {
  static const String baseUrl = 'http://10.0.2.2:3000/api';

  static Future<List<dynamic>> getTasks() async {
    final response = await http.get(Uri.parse('$baseUrl/tasks'));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['data'];
    }
    throw Exception('Failed to load tasks');
  }
}`)
                    }
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                  >
                    <Copy className="w-3 h-3" /> Copy
                  </button>
                </div>
                <pre className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80 text-[11px] font-mono text-slate-300 overflow-x-auto">
{`import 'dart:convert';
import 'package:http/http.dart' as http;

class MotaviService {
  static const String baseUrl = 'http://10.0.2.2:3000/api';

  static Future<List<dynamic>> getTasks() async {
    final response = await http.get(Uri.parse('$baseUrl/tasks'));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['data'];
    }
    throw Exception('Failed to load tasks');
  }
}`}
                </pre>
              </div>
            </div>

            {/* Cloud SQL / Production Database Migration Guide */}
            <div className="p-5 rounded-2xl bg-indigo-950/20 border border-indigo-500/20 space-y-3">
              <h4 className="text-sm font-semibold text-indigo-300 flex items-center gap-2">
                <Server className="w-4 h-4 text-indigo-400" />
                Connecting Persistent Cloud SQL (PostgreSQL)
              </h4>
              <p className="text-xs text-slate-300 leading-relaxed">
                When you're ready to persist user data, habits, and tasks to an enterprise relational database, ask AI
                Studio to provision Cloud SQL or Firebase. Motavi Backend is architected so standard ORMs (such as
                Drizzle ORM or Prisma) connect directly over Unix Domain Sockets without code disruption.
              </p>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 py-4 text-center text-xs text-slate-500">
        Motavi Backend Engine • Express 4.x + Vite SPA • Ready for Production & API Consumers
      </footer>
    </div>
  );
}
