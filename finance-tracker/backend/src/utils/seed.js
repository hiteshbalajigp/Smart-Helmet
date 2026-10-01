import dotenv from 'dotenv';
import mongoose from 'mongoose';
import bcrypt from 'bcryptjs';
import User from './models/User.js';
import Income from './models/Income.js';
import Expense from './models/Expense.js';
import Budget from './models/Budget.js';
import Goal from './models/Goal.js';
import Investment from './models/Investment.js';
import RecurringTransaction from './models/RecurringTransaction.js';
import Notification from './models/Notification.js';

dotenv.config();

const seed = async () => {
  await mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/finance-tracker');
  console.log('Connected to MongoDB for seeding...');

  await Promise.all([
    User.deleteMany({}),
    Income.deleteMany({}),
    Expense.deleteMany({}),
    Budget.deleteMany({}),
    Goal.deleteMany({}),
    Investment.deleteMany({}),
    RecurringTransaction.deleteMany({}),
    Notification.deleteMany({}),
  ]);

  const user = await User.create({
    name: 'Demo User',
    email: 'demo@financetracker.com',
    password: 'Demo@12345',
    isVerified: true,
    settings: { currency: 'INR', theme: 'dark' },
    financialHealthScore: 72,
    streak: 15,
    badges: ['first_budget', 'saver', 'week_streak'],
  });

  const now = new Date();
  const monthsAgo = (n) => {
    const d = new Date(now);
    d.setMonth(d.getMonth() - n);
    return d;
  };

  const incomes = [];
  for (let i = 0; i < 6; i++) {
    incomes.push({
      user: user._id,
      amount: 85000 + Math.random() * 5000,
      category: 'salary',
      description: 'Monthly Salary',
      date: monthsAgo(i),
      paymentMethod: 'bank_transfer',
      isRecurring: true,
      recurringFrequency: 'monthly',
    });
    if (i % 2 === 0) {
      incomes.push({
        user: user._id,
        amount: 5000 + Math.random() * 10000,
        category: 'freelancing',
        description: 'Freelance Project',
        date: monthsAgo(i),
        paymentMethod: 'upi',
      });
    }
  }
  await Income.insertMany(incomes);

  const expenseCategories = [
    { cat: 'food', min: 300, max: 800, count: 15 },
    { cat: 'travel', min: 200, max: 2000, count: 8 },
    { cat: 'fuel', min: 1500, max: 3000, count: 4 },
    { cat: 'entertainment', min: 500, max: 2000, count: 6 },
    { cat: 'shopping', min: 1000, max: 5000, count: 5 },
    { cat: 'bills', min: 2000, max: 5000, count: 3 },
    { cat: 'rent', min: 15000, max: 15000, count: 1 },
    { cat: 'subscription', min: 199, max: 999, count: 4 },
    { cat: 'medical', min: 500, max: 3000, count: 2 },
    { cat: 'emi', min: 8000, max: 8000, count: 1 },
  ];

  const expenses = [];
  for (let m = 0; m < 6; m++) {
    for (const { cat, min, max, count } of expenseCategories) {
      for (let c = 0; c < count; c++) {
        const date = monthsAgo(m);
        date.setDate(Math.floor(Math.random() * 28) + 1);
        expenses.push({
          user: user._id,
          amount: Math.round(min + Math.random() * (max - min)),
          category: cat,
          description: `${cat.charAt(0).toUpperCase() + cat.slice(1)} expense`,
          date,
          paymentMethod: ['upi', 'card', 'cash'][Math.floor(Math.random() * 3)],
          tags: [cat],
        });
      }
    }
  }
  await Expense.insertMany(expenses);

  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);

  await Budget.create({
    user: user._id,
    name: 'Monthly Budget',
    type: 'monthly',
    totalAmount: 50000,
    spentAmount: 32500,
    startDate: monthStart,
    endDate: monthEnd,
    categories: [
      { category: 'food', limit: 8000, spent: 5500 },
      { category: 'travel', limit: 5000, spent: 3200 },
      { category: 'entertainment', limit: 3000, spent: 2800 },
      { category: 'shopping', limit: 10000, spent: 7500 },
      { category: 'bills', limit: 5000, spent: 4500 },
    ],
    alerts: { enabled: true, threshold: 80 },
  });

  await Goal.insertMany([
    {
      user: user._id,
      name: 'Emergency Fund',
      targetAmount: 300000,
      currentAmount: 125000,
      targetDate: new Date(now.getFullYear() + 1, 5, 1),
      category: 'emergency',
      icon: '🛡️',
      color: '#10b981',
      monthlyContribution: 15000,
      priority: 'high',
    },
    {
      user: user._id,
      name: 'MacBook Pro',
      targetAmount: 150000,
      currentAmount: 45000,
      targetDate: new Date(now.getFullYear(), 11, 1),
      category: 'laptop',
      icon: '💻',
      color: '#6366f1',
      monthlyContribution: 12000,
      priority: 'medium',
    },
    {
      user: user._id,
      name: 'Goa Trip',
      targetAmount: 50000,
      currentAmount: 28000,
      targetDate: new Date(now.getFullYear(), 9, 1),
      category: 'vacation',
      icon: '🏖️',
      color: '#f59e0b',
      monthlyContribution: 8000,
      priority: 'low',
    },
  ]);

  await Investment.insertMany([
    { user: user._id, name: 'Nifty 50 Index Fund', type: 'mutual_funds', investedAmount: 100000, currentValue: 118500, symbol: 'NIFTY50' },
    { user: user._id, name: 'Reliance Industries', type: 'stocks', investedAmount: 50000, currentValue: 54200, symbol: 'RELIANCE' },
    { user: user._id, name: 'SBI Gold ETF', type: 'gold', investedAmount: 30000, currentValue: 34500 },
    { user: user._id, name: 'PPF Account', type: 'ppf', investedAmount: 150000, currentValue: 168000 },
    { user: user._id, name: 'Bitcoin', type: 'crypto', investedAmount: 20000, currentValue: 18500, symbol: 'BTC' },
    { user: user._id, name: 'HDFC FD', type: 'fd', investedAmount: 200000, currentValue: 212000 },
  ]);

  await RecurringTransaction.insertMany([
    { user: user._id, type: 'income', amount: 85000, category: 'salary', description: 'Monthly Salary', frequency: 'monthly', nextDate: new Date(now.getFullYear(), now.getMonth() + 1, 1), paymentMethod: 'bank_transfer' },
    { user: user._id, type: 'expense', amount: 15000, category: 'rent', description: 'House Rent', frequency: 'monthly', nextDate: new Date(now.getFullYear(), now.getMonth() + 1, 1), paymentMethod: 'bank_transfer' },
    { user: user._id, type: 'expense', amount: 8000, category: 'emi', description: 'Car EMI', frequency: 'monthly', nextDate: new Date(now.getFullYear(), now.getMonth() + 1, 5), paymentMethod: 'bank_transfer' },
    { user: user._id, type: 'expense', amount: 999, category: 'subscription', description: 'Netflix', frequency: 'monthly', nextDate: new Date(now.getFullYear(), now.getMonth() + 1, 15), paymentMethod: 'card' },
    { user: user._id, type: 'expense', amount: 299, category: 'subscription', description: 'Spotify', frequency: 'monthly', nextDate: new Date(now.getFullYear(), now.getMonth() + 1, 20), paymentMethod: 'upi' },
  ]);

  await Notification.insertMany([
    { user: user._id, type: 'budget_exceeded', title: 'Budget Alert', message: 'Entertainment budget is at 93% capacity', isRead: false },
    { user: user._id, type: 'ai_suggestion', title: 'AI Tip', message: 'You could save ₹2,400/month by reducing food delivery orders', isRead: false },
    { user: user._id, type: 'upcoming_emi', title: 'EMI Due', message: 'Car EMI of ₹8,000 due in 5 days', isRead: false },
    { user: user._id, type: 'goal_achieved', title: 'Goal Progress', message: 'Emergency Fund is 42% complete!', isRead: true },
  ]);

  console.log('Seed data created successfully!');
  console.log('Demo login: demo@financetracker.com / Demo@12345');
  process.exit(0);
};

seed().catch((err) => {
  console.error('Seed failed:', err);
  process.exit(1);
});
