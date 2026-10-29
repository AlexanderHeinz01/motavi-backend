import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;
const HOST = '0.0.0.0';

app.use(cors());
app.use(express.json());

// Request logger for Developer Observability
interface ApiLog {
  id: string;
  timestamp: string;
  method: string;
  path: string;
  statusCode: number;
  durationMs: number;
  ip: string;
}

const apiLogs: ApiLog[] = [];
const MAX_LOGS = 100;

app.use((req: Request, res: Response, next: NextFunction) => {
  const start = Date.now();
  res.on('finish', () => {
    if (req.path.startsWith('/api') && req.path !== '/api/system/logs') {
      const logEntry: ApiLog = {
        id: Math.random().toString(36).substring(2, 9),
        timestamp: new Date().toISOString(),
        method: req.method,
        path: req.path,
        statusCode: res.statusCode,
        durationMs: Date.now() - start,
        ip: req.ip || '127.0.0.1',
      };
      apiLogs.unshift(logEntry);
      if (apiLogs.length > MAX_LOGS) apiLogs.pop();
    }
  });
  next();
});

// Seed Data
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
  category: 'Health' | 'Focus' | 'Mindset' | 'Fitness';
  history: string[]; // YYYY-MM-DD
  reminderTime: string;
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
  category: 'Career' | 'Fitness' | 'Skills' | 'Financial';
  targetDate: string;
  progress: number; // 0 - 100
  status: 'in_progress' | 'completed' | 'on_hold';
  milestones: Milestone[];
}

function getInitialTasks(): Task[] {
  return [
    {
      id: 'task-1',
      title: 'Finish Motavi API documentation and test endpoints',
      description: 'Ensure Swagger/OpenAPI endpoints and curl snippets are accessible',
      category: 'Work',
      priority: 'high',
      completed: true,
      dueDate: new Date().toISOString().split('T')[0],
      createdAt: new Date(Date.now() - 86400000 * 2).toISOString(),
    },
    {
      id: 'task-2',
      title: 'Morning 30-minute cardio & stretch routine',
      description: 'Zone 2 running or brisk walking followed by hip mobility',
      category: 'Health',
      priority: 'medium',
      completed: true,
      dueDate: new Date().toISOString().split('T')[0],
      createdAt: new Date(Date.now() - 86400000).toISOString(),
    },
    {
      id: 'task-3',
      title: 'Review weekly progress report and calibrate quarterly goals',
      description: 'Assess velocity, habit adherence, and sprint priorities',
      category: 'Work',
      priority: 'high',
      completed: false,
      dueDate: new Date(Date.now() + 86400000).toISOString().split('T')[0],
      createdAt: new Date().toISOString(),
    },
    {
      id: 'task-4',
      title: 'Read 20 pages of "Atomic Habits"',
      description: 'Focus on identity-based habit loops and environment design',
      category: 'Learning',
      priority: 'low',
      completed: false,
      dueDate: new Date(Date.now() + 86400000 * 2).toISOString().split('T')[0],
      createdAt: new Date().toISOString(),
    },
  ];
}

function getInitialHabits(): Habit[] {
  const today = new Date().toISOString().split('T')[0];
  const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
  const twoDaysAgo = new Date(Date.now() - 86400000 * 2).toISOString().split('T')[0];
  const threeDaysAgo = new Date(Date.now() - 86400000 * 3).toISOString().split('T')[0];

  return [
    {
      id: 'habit-1',
      name: 'Deep Work Sprint (90 min)',
      description: 'Uninterrupted creative/engineering focus session with zero notifications',
      frequency: 'daily',
      targetDaysPerWeek: 5,
      streakCount: 7,
      bestStreak: 18,
      category: 'Focus',
      history: [threeDaysAgo, twoDaysAgo, yesterday, today],
      reminderTime: '09:00',
    },
    {
      id: 'habit-2',
      name: 'Drink 2.5L Water & Hydrate',
      description: 'Electrolyte water upon waking, minimum 2.5 liters throughout the day',
      frequency: 'daily',
      targetDaysPerWeek: 7,
      streakCount: 12,
      bestStreak: 21,
      category: 'Health',
      history: [threeDaysAgo, twoDaysAgo, yesterday, today],
      reminderTime: '08:00',
    },
    {
      id: 'habit-3',
      name: 'Evening Reflection & Gratitude',
      description: 'Write down 3 wins and plan top 3 priorities for tomorrow',
      frequency: 'daily',
      targetDaysPerWeek: 7,
      streakCount: 4,
      bestStreak: 14,
      category: 'Mindset',
      history: [threeDaysAgo, twoDaysAgo, yesterday],
      reminderTime: '21:30',
    },
    {
      id: 'habit-4',
      name: 'Strength Training Session',
      description: 'Full-body resistance training with progressive overload',
      frequency: 'weekly',
      targetDaysPerWeek: 4,
      streakCount: 3,
      bestStreak: 9,
      category: 'Fitness',
      history: [twoDaysAgo, today],
      reminderTime: '17:30',
    },
  ];
}

function getInitialGoals(): Goal[] {
  return [
    {
      id: 'goal-1',
      title: 'Launch Motavi Cloud Platform v1.0',
      description: 'Complete backend microservices, robust API test suite, and client SDKs',
      category: 'Career',
      targetDate: new Date(Date.now() + 86400000 * 30).toISOString().split('T')[0],
      progress: 75,
      status: 'in_progress',
      milestones: [
        { id: 'm-1', title: 'Define data models and REST endpoints', completed: true },
        { id: 'm-2', title: 'Implement developer test suite & console', completed: true },
        { id: 'm-3', title: 'Load testing & rate limit validation', completed: true },
        { id: 'm-4', title: 'Deploy public documentation & SDKs', completed: false },
      ],
    },
    {
      id: 'goal-2',
      title: 'Achieve 100 Consecutive Days of Habit Consistency',
      description: 'Maintain deep work and morning wellness habits without breaking the chain',
      category: 'Fitness',
      targetDate: new Date(Date.now() + 86400000 * 60).toISOString().split('T')[0],
      progress: 42,
      status: 'in_progress',
      milestones: [
        { id: 'm-5', title: 'Reach 30-day milestone', completed: true },
        { id: 'm-6', title: 'Reach 60-day milestone', completed: false },
        { id: 'm-7', title: 'Reach 100-day milestone', completed: false },
      ],
    },
  ];
}

// In-Memory State
let tasks: Task[] = getInitialTasks();
let habits: Habit[] = getInitialHabits();
let goals: Goal[] = getInitialGoals();

// Quotes Database
const MOTIVATIONAL_QUOTES = [
  {
    quote: "We are what we repeatedly do. Excellence, then, is not an act, but a habit.",
    author: "Will Durant (summarizing Aristotle)",
    theme: "Consistency",
  },
  {
    quote: "You do not rise to the level of your goals. You fall to the level of your systems.",
    author: "James Clear",
    theme: "Systems",
  },
  {
    quote: "Small disciplines repeated with consistency every day lead to great achievements gained slowly over time.",
    author: "John C. Maxwell",
    theme: "Progress",
  },
  {
    quote: "Action isn't just the effect of motivation; it's also the cause of it.",
    author: "Mark Manson",
    theme: "Momentum",
  },
  {
    quote: "Focus is a muscle. The more you protect it, the stronger your output becomes.",
    author: "Motavi Mindset",
    theme: "Focus",
  },
];

// --- API ROUTES ---

// 1. Health & Status
app.get('/api/health', (req: Request, res: Response) => {
  const mem = process.memoryUsage();
  res.json({
    status: 'healthy',
    service: 'motavi-backend',
    version: '1.2.0',
    uptimeSeconds: Math.floor(process.uptime()),
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development',
    systemMetrics: {
      heapUsedMb: Math.round(mem.heapUsed / 1024 / 1024 * 100) / 100,
      heapTotalMb: Math.round(mem.heapTotal / 1024 / 1024 * 100) / 100,
      rssMb: Math.round(mem.rss / 1024 / 1024 * 100) / 100,
    },
    counts: {
      tasks: tasks.length,
      habits: habits.length,
      goals: goals.length,
      logs: apiLogs.length,
    },
  });
});

// 2. Auth Endpoints
app.post('/api/auth/login', (req: Request, res: Response) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password are required' });
  }

  // Demo user authentication
  res.json({
    token: 'motavi_tok_' + Math.random().toString(36).substring(2, 15),
    user: {
      id: 'usr_motavi_1',
      name: email.split('@')[0],
      email: email,
      role: 'developer',
      avatarUrl: `https://api.dicebear.com/7.x/identicon/svg?seed=${email}`,
      joinedAt: '2026-01-15T10:00:00.000Z',
    },
  });
});

app.get('/api/auth/me', (req: Request, res: Response) => {
  res.json({
    user: {
      id: 'usr_motavi_1',
      name: 'Alexander Heinz',
      email: 'alexander84.heinz@gmail.com',
      tier: 'Pro Builder',
      streakDays: 14,
      points: 1840,
    },
  });
});

// 3. Tasks Endpoints
app.get('/api/tasks', (req: Request, res: Response) => {
  let filtered = [...tasks];
  const { completed, category, priority } = req.query;

  if (completed !== undefined) {
    const isComp = completed === 'true';
    filtered = filtered.filter((t) => t.completed === isComp);
  }
  if (category) {
    filtered = filtered.filter((t) => t.category.toLowerCase() === String(category).toLowerCase());
  }
  if (priority) {
    filtered = filtered.filter((t) => t.priority.toLowerCase() === String(priority).toLowerCase());
  }

  res.json({
    total: filtered.length,
    data: filtered,
  });
});

app.post('/api/tasks', (req: Request, res: Response) => {
  const { title, description, category, priority, dueDate } = req.body;
  if (!title) {
    return res.status(400).json({ error: 'Title is required' });
  }

  const newTask: Task = {
    id: 'task-' + Date.now(),
    title: String(title).trim(),
    description: description ? String(description).trim() : '',
    category: category || 'Work',
    priority: priority || 'medium',
    completed: false,
    dueDate: dueDate || new Date().toISOString().split('T')[0],
    createdAt: new Date().toISOString(),
  };

  tasks.unshift(newTask);
  res.status(201).json(newTask);
});

app.put('/api/tasks/:id', (req: Request, res: Response) => {
  const index = tasks.findIndex((t) => t.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ error: `Task with id '${req.params.id}' not found` });
  }

  tasks[index] = { ...tasks[index], ...req.body, id: tasks[index].id };
  res.json(tasks[index]);
});

app.post('/api/tasks/:id/toggle', (req: Request, res: Response) => {
  const task = tasks.find((t) => t.id === req.params.id);
  if (!task) {
    return res.status(404).json({ error: `Task with id '${req.params.id}' not found` });
  }

  task.completed = !task.completed;
  res.json({ message: 'Task completion toggled', task });
});

app.delete('/api/tasks/:id', (req: Request, res: Response) => {
  const index = tasks.findIndex((t) => t.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ error: `Task with id '${req.params.id}' not found` });
  }

  const removed = tasks.splice(index, 1)[0];
  res.json({ message: 'Task deleted successfully', task: removed });
});

// 4. Habits Endpoints
app.get('/api/habits', (req: Request, res: Response) => {
  const today = new Date().toISOString().split('T')[0];
  const habitsWithStatus = habits.map((h) => ({
    ...h,
    completedToday: h.history.includes(today),
  }));
  res.json({
    total: habits.length,
    data: habitsWithStatus,
  });
});

app.post('/api/habits', (req: Request, res: Response) => {
  const { name, description, frequency, targetDaysPerWeek, category, reminderTime } = req.body;
  if (!name) {
    return res.status(400).json({ error: 'Habit name is required' });
  }

  const newHabit: Habit = {
    id: 'habit-' + Date.now(),
    name: String(name).trim(),
    description: description ? String(description).trim() : '',
    frequency: frequency === 'weekly' ? 'weekly' : 'daily',
    targetDaysPerWeek: Number(targetDaysPerWeek) || 7,
    streakCount: 0,
    bestStreak: 0,
    category: category || 'Focus',
    history: [],
    reminderTime: reminderTime || '09:00',
  };

  habits.push(newHabit);
  res.status(201).json(newHabit);
});

app.post('/api/habits/:id/check-in', (req: Request, res: Response) => {
  const habit = habits.find((h) => h.id === req.params.id);
  if (!habit) {
    return res.status(404).json({ error: `Habit with id '${req.params.id}' not found` });
  }

  const today = new Date().toISOString().split('T')[0];
  const alreadyChecked = habit.history.includes(today);

  if (alreadyChecked) {
    // Un-check
    habit.history = habit.history.filter((d) => d !== today);
    habit.streakCount = Math.max(0, habit.streakCount - 1);
    return res.json({
      message: 'Habit check-in removed for today',
      completedToday: false,
      streakCount: habit.streakCount,
      habit,
    });
  } else {
    // Check-in
    habit.history.push(today);
    habit.streakCount += 1;
    if (habit.streakCount > habit.bestStreak) {
      habit.bestStreak = habit.streakCount;
    }
    return res.json({
      message: 'Habit completed for today! Streak extended!',
      completedToday: true,
      streakCount: habit.streakCount,
      habit,
    });
  }
});

app.delete('/api/habits/:id', (req: Request, res: Response) => {
  const idx = habits.findIndex((h) => h.id === req.params.id);
  if (idx === -1) {
    return res.status(404).json({ error: `Habit with id '${req.params.id}' not found` });
  }
  const removed = habits.splice(idx, 1)[0];
  res.json({ message: 'Habit deleted', habit: removed });
});

// 5. Goals Endpoints
app.get('/api/goals', (req: Request, res: Response) => {
  res.json({
    total: goals.length,
    data: goals,
  });
});

app.post('/api/goals', (req: Request, res: Response) => {
  const { title, description, category, targetDate, milestones } = req.body;
  if (!title) {
    return res.status(400).json({ error: 'Goal title is required' });
  }

  const formattedMilestones: Milestone[] = Array.isArray(milestones)
    ? milestones.map((m: any, idx: number) => ({
        id: 'm-' + Date.now() + '-' + idx,
        title: typeof m === 'string' ? m : m.title,
        completed: Boolean(m.completed),
      }))
    : [];

  const newGoal: Goal = {
    id: 'goal-' + Date.now(),
    title: String(title).trim(),
    description: description ? String(description).trim() : '',
    category: category || 'Career',
    targetDate: targetDate || new Date(Date.now() + 86400000 * 30).toISOString().split('T')[0],
    progress: 0,
    status: 'in_progress',
    milestones: formattedMilestones,
  };

  goals.push(newGoal);
  res.status(201).json(newGoal);
});

app.put('/api/goals/:id', (req: Request, res: Response) => {
  const index = goals.findIndex((g) => g.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ error: `Goal '${req.params.id}' not found` });
  }

  goals[index] = { ...goals[index], ...req.body, id: goals[index].id };
  // Recalculate progress if milestones present
  if (goals[index].milestones.length > 0) {
    const done = goals[index].milestones.filter((m) => m.completed).length;
    goals[index].progress = Math.round((done / goals[index].milestones.length) * 100);
  }

  res.json(goals[index]);
});

app.post('/api/goals/:id/milestones/:mId/toggle', (req: Request, res: Response) => {
  const goal = goals.find((g) => g.id === req.params.id);
  if (!goal) {
    return res.status(404).json({ error: `Goal '${req.params.id}' not found` });
  }
  const milestone = goal.milestones.find((m) => m.id === req.params.mId);
  if (!milestone) {
    return res.status(404).json({ error: `Milestone '${req.params.mId}' not found` });
  }

  milestone.completed = !milestone.completed;
  const done = goal.milestones.filter((m) => m.completed).length;
  goal.progress = Math.round((done / goal.milestones.length) * 100);

  if (goal.progress === 100) {
    goal.status = 'completed';
  } else if (goal.status === 'completed' && goal.progress < 100) {
    goal.status = 'in_progress';
  }

  res.json({ message: 'Milestone updated', goal });
});

app.delete('/api/goals/:id', (req: Request, res: Response) => {
  const idx = goals.findIndex((g) => g.id === req.params.id);
  if (idx === -1) {
    return res.status(404).json({ error: `Goal '${req.params.id}' not found` });
  }
  const removed = goals.splice(idx, 1)[0];
  res.json({ message: 'Goal removed', goal: removed });
});

// 6. Motivation & Reflections
app.get('/api/motivation/daily', (req: Request, res: Response) => {
  const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000);
  const selectedQuote = MOTIVATIONAL_QUOTES[dayOfYear % MOTIVATIONAL_QUOTES.length];

  res.json({
    date: new Date().toISOString().split('T')[0],
    quote: selectedQuote.quote,
    author: selectedQuote.author,
    theme: selectedQuote.theme,
    dailyPrompt: "What is the single highest-impact action you will execute today to advance your vision?",
    streakTip: "Habits are identity votes. Each completion casts a ballot for the person you strive to become.",
  });
});

// 7. Analytics Summary
app.get('/api/analytics/summary', (req: Request, res: Response) => {
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter((t) => t.completed).length;
  const taskCompletionRate = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  const totalHabits = habits.length;
  const today = new Date().toISOString().split('T')[0];
  const habitsCheckedToday = habits.filter((h) => h.history.includes(today)).length;
  const habitAdherenceToday = totalHabits > 0 ? Math.round((habitsCheckedToday / totalHabits) * 100) : 0;

  const avgStreak = totalHabits > 0 ? Math.round(habits.reduce((acc, h) => acc + h.streakCount, 0) / totalHabits) : 0;
  const activeGoals = goals.filter((g) => g.status === 'in_progress').length;
  const avgGoalProgress = goals.length > 0 ? Math.round(goals.reduce((acc, g) => acc + g.progress, 0) / goals.length) : 0;

  res.json({
    metrics: {
      taskCompletionRate,
      completedTasks,
      totalTasks,
      habitsCheckedToday,
      totalHabits,
      habitAdherenceToday,
      avgStreak,
      activeGoals,
      avgGoalProgress,
    },
    weeklyActivity: [
      { day: 'Mon', completedItems: 8 },
      { day: 'Tue', completedItems: 11 },
      { day: 'Wed', completedItems: 9 },
      { day: 'Thu', completedItems: 14 },
      { day: 'Fri', completedItems: 12 },
      { day: 'Sat', completedItems: 7 },
      { day: 'Sun', completedItems: 6 },
    ],
  });
});

// 8. Developer Observability & Logs
app.get('/api/system/logs', (req: Request, res: Response) => {
  res.json({
    total: apiLogs.length,
    logs: apiLogs,
  });
});

app.post('/api/system/reset', (req: Request, res: Response) => {
  tasks = getInitialTasks();
  habits = getInitialHabits();
  goals = getInitialGoals();
  res.json({ message: 'State reset to default seeds successfully' });
});

// 9. Interactive API Catalog Specification
app.get('/api/docs/spec', (req: Request, res: Response) => {
  res.json({
    openapi: '3.0.0',
    info: {
      title: 'Motavi Backend API',
      version: '1.2.0',
      description: 'High-performance REST API for task management, habit streaks, goals, and productivity telemetry.',
    },
    endpoints: [
      { method: 'GET', path: '/api/health', desc: 'System health check and memory diagnostics' },
      { method: 'GET', path: '/api/tasks', desc: 'Fetch all tasks with optional ?completed=&category=&priority= filters' },
      { method: 'POST', path: '/api/tasks', desc: 'Create a new task with title, category, priority, and dueDate' },
      { method: 'POST', path: '/api/tasks/:id/toggle', desc: 'Toggle task completion state' },
      { method: 'DELETE', path: '/api/tasks/:id', desc: 'Delete a task by ID' },
      { method: 'GET', path: '/api/habits', desc: 'Fetch habits with active streaks and today completion flag' },
      { method: 'POST', path: '/api/habits', desc: 'Create a new tracking habit' },
      { method: 'POST', path: '/api/habits/:id/check-in', desc: 'Log a daily check-in (toggles today streak)' },
      { method: 'DELETE', path: '/api/habits/:id', desc: 'Delete a habit' },
      { method: 'GET', path: '/api/goals', desc: 'List strategic goals with milestone progress' },
      { method: 'POST', path: '/api/goals', desc: 'Create a new strategic goal with milestones' },
      { method: 'POST', path: '/api/goals/:id/milestones/:mId/toggle', desc: 'Toggle milestone completion' },
      { method: 'GET', path: '/api/motivation/daily', desc: 'Get rotating daily motivation, quote, and challenge prompt' },
      { method: 'GET', path: '/api/analytics/summary', desc: 'Summary metrics, velocity, and completion rates' },
      { method: 'GET', path: '/api/system/logs', desc: 'Fetch recent HTTP request telemetry logs' },
      { method: 'POST', path: '/api/system/reset', desc: 'Reset in-memory state back to original sample data' },
    ],
  });
});

// Production static file serving or Dev Vite middleware
async function setupApp() {
  const isDev = process.env.NODE_ENV !== 'production';

  if (isDev) {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.resolve(__dirname, 'dist')));
    app.get('*', (req: Request, res: Response) => {
      res.sendFile(path.resolve(__dirname, 'dist', 'index.html'));
    });
  }

  app.listen(PORT, HOST, () => {
    console.log(`[Motavi Backend] Server running on http://${HOST}:${PORT}`);
  });
}

setupApp().catch((err) => {
  console.error('[Motavi Backend] Failed to start server:', err);
  process.exit(1);
});
