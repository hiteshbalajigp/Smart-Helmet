export const INCOME_CATEGORIES = [
  { value: 'salary', label: 'Salary', icon: '💼' },
  { value: 'business', label: 'Business', icon: '🏢' },
  { value: 'freelancing', label: 'Freelancing', icon: '💻' },
  { value: 'rental', label: 'Rental', icon: '🏠' },
  { value: 'passive', label: 'Passive Income', icon: '📈' },
  { value: 'other', label: 'Other', icon: '📦' },
];

export const EXPENSE_CATEGORIES = [
  { value: 'food', label: 'Food', icon: '🍔', color: '#f97316' },
  { value: 'travel', label: 'Travel', icon: '✈️', color: '#3b82f6' },
  { value: 'fuel', label: 'Fuel', icon: '⛽', color: '#eab308' },
  { value: 'entertainment', label: 'Entertainment', icon: '🎬', color: '#a855f7' },
  { value: 'shopping', label: 'Shopping', icon: '🛍️', color: '#ec4899' },
  { value: 'medical', label: 'Medical', icon: '🏥', color: '#ef4444' },
  { value: 'bills', label: 'Bills', icon: '📄', color: '#6b7280' },
  { value: 'education', label: 'Education', icon: '📚', color: '#14b8a6' },
  { value: 'investment', label: 'Investment', icon: '📊', color: '#10b981' },
  { value: 'rent', label: 'Rent', icon: '🏠', color: '#8b5cf6' },
  { value: 'emi', label: 'EMI', icon: '🏦', color: '#f59e0b' },
  { value: 'insurance', label: 'Insurance', icon: '🛡️', color: '#06b6d4' },
  { value: 'subscription', label: 'Subscription', icon: '📱', color: '#6366f1' },
  { value: 'others', label: 'Others', icon: '📦', color: '#94a3b8' },
];

export const INVESTMENT_TYPES = [
  { value: 'stocks', label: 'Stocks', icon: '📈' },
  { value: 'mutual_funds', label: 'Mutual Funds', icon: '📊' },
  { value: 'gold', label: 'Gold', icon: '🥇' },
  { value: 'crypto', label: 'Crypto', icon: '₿' },
  { value: 'fd', label: 'Fixed Deposit', icon: '🏦' },
  { value: 'ppf', label: 'PPF', icon: '🛡️' },
  { value: 'nps', label: 'NPS', icon: '🎯' },
  { value: 'other', label: 'Other', icon: '📦' },
];

export const GOAL_CATEGORIES = [
  { value: 'bike', label: 'Buy Bike', icon: '🏍️' },
  { value: 'trip', label: 'Trip', icon: '✈️' },
  { value: 'emergency', label: 'Emergency Fund', icon: '🛡️' },
  { value: 'laptop', label: 'Laptop', icon: '💻' },
  { value: 'car', label: 'Car', icon: '🚗' },
  { value: 'wedding', label: 'Wedding', icon: '💒' },
  { value: 'house', label: 'House', icon: '🏠' },
  { value: 'vacation', label: 'Vacation', icon: '🏖️' },
  { value: 'other', label: 'Other', icon: '🎯' },
];

export const PAYMENT_METHODS = [
  { value: 'cash', label: 'Cash' },
  { value: 'bank_transfer', label: 'Bank Transfer' },
  { value: 'upi', label: 'UPI' },
  { value: 'card', label: 'Card' },
  { value: 'wallet', label: 'Wallet' },
  { value: 'cheque', label: 'Cheque' },
  { value: 'other', label: 'Other' },
];

export const DATE_FILTERS = [
  { value: 'today', label: 'Today' },
  { value: 'yesterday', label: 'Yesterday' },
  { value: 'this_week', label: 'This Week' },
  { value: 'last_week', label: 'Last Week' },
  { value: 'this_month', label: 'This Month' },
  { value: 'last_month', label: 'Last Month' },
];

export const CHART_COLORS = [
  '#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899',
  '#f97316', '#eab308', '#22c55e', '#14b8a6', '#06b6d4',
  '#3b82f6', '#64748b',
];

export const NAV_ITEMS = [
  { path: '/dashboard', label: 'Dashboard', icon: 'LayoutDashboard' },
  { path: '/income', label: 'Income', icon: 'TrendingUp' },
  { path: '/expenses', label: 'Expenses', icon: 'TrendingDown' },
  { path: '/budget', label: 'Budget', icon: 'PieChart' },
  { path: '/goals', label: 'Goals', icon: 'Target' },
  { path: '/investments', label: 'Investments', icon: 'LineChart' },
  { path: '/recurring', label: 'Recurring', icon: 'Repeat' },
  { path: '/analytics', label: 'Analytics', icon: 'BarChart3' },
  { path: '/insights', label: 'AI Insights', icon: 'Sparkles' },
  { path: '/reports', label: 'Reports', icon: 'FileText' },
  { path: '/settings', label: 'Settings', icon: 'Settings' },
];
