import Income from '../models/Income.js';
import Expense from '../models/Expense.js';
import Budget from '../models/Budget.js';
import Goal from '../models/Goal.js';
import Investment from '../models/Investment.js';
import Notification from '../models/Notification.js';
import { getDateRange } from '../utils/helpers.js';

const getMonthlyTrend = async (Model, userId, months = 6) => {
  const trends = [];
  const now = new Date();

  for (let i = months - 1; i >= 0; i--) {
    const start = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const end = new Date(now.getFullYear(), now.getMonth() - i + 1, 0, 23, 59, 59);
    const result = await Model.aggregate([
      { $match: { user: userId, date: { $gte: start, $lte: end } } },
      { $group: { _id: null, total: { $sum: '$amount' } } },
    ]);
    trends.push({
      month: start.toLocaleString('default', { month: 'short' }),
      value: result[0]?.total || 0,
    });
  }
  return trends;
};

const getSparkline = async (Model, userId, days = 7) => {
  const data = [];
  const now = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const start = new Date(now);
    start.setDate(now.getDate() - i);
    start.setHours(0, 0, 0, 0);
    const end = new Date(start);
    end.setHours(23, 59, 59, 999);
    const result = await Model.aggregate([
      { $match: { user: userId, date: { $gte: start, $lte: end } } },
      { $group: { _id: null, total: { $sum: '$amount' } } },
    ]);
    data.push(result[0]?.total || 0);
  }
  return data;
};

export const getDashboard = async (req, res, next) => {
  try {
    const userId = req.user._id;
    const { start, end } = getDateRange('this_month');
    const prevStart = new Date(start);
    prevStart.setMonth(prevStart.getMonth() - 1);
    const prevEnd = new Date(end);
    prevEnd.setMonth(prevEnd.getMonth() - 1);

    const [
      currentIncome, prevIncome,
      currentExpenses, prevExpenses,
      budgets, goals, investments,
      categoryBreakdown,
    ] = await Promise.all([
      Income.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        { $group: { _id: null, total: { $sum: '$amount' } } },
      ]),
      Income.aggregate([
        { $match: { user: userId, date: { $gte: prevStart, $lte: prevEnd } } },
        { $group: { _id: null, total: { $sum: '$amount' } } },
      ]),
      Expense.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        { $group: { _id: null, total: { $sum: '$amount' } } },
      ]),
      Expense.aggregate([
        { $match: { user: userId, date: { $gte: prevStart, $lte: prevEnd } } },
        { $group: { _id: null, total: { $sum: '$amount' } } },
      ]),
      Budget.find({ user: userId, isActive: true }),
      Goal.find({ user: userId, isCompleted: false }),
      Investment.find({ user: userId, isActive: true }),
      Expense.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        { $group: { _id: '$category', total: { $sum: '$amount' } } },
        { $sort: { total: -1 } },
      ]),
    ]);

    const income = currentIncome[0]?.total || 0;
    const prevInc = prevIncome[0]?.total || 0;
    const expenses = currentExpenses[0]?.total || 0;
    const prevExp = prevExpenses[0]?.total || 0;
    const savings = income - expenses;
    const budgetTotal = budgets.reduce((a, b) => a + b.totalAmount, 0);
    const budgetSpent = budgets.reduce((a, b) => a + b.spentAmount, 0);
    const budgetLeft = budgetTotal - budgetSpent;
    const investmentValue = investments.reduce((a, i) => a + i.currentValue, 0);
    const investmentInvested = investments.reduce((a, i) => a + i.investedAmount, 0);
    const netWorth = savings + investmentValue;
    const monthlyGoal = goals.reduce((a, g) => a + g.monthlyContribution, 0);

    const pctChange = (current, previous) =>
      previous === 0 ? (current > 0 ? 100 : 0) : ((current - previous) / previous) * 100;

    const [incomeSpark, expenseSpark, savingsSpark] = await Promise.all([
      getSparkline(Income, userId),
      getSparkline(Expense, userId),
      getSparkline(Expense, userId, 7).then(async () => {
        const inc = await getSparkline(Income, userId);
        const exp = await getSparkline(Expense, userId);
        return inc.map((v, i) => v - exp[i]);
      }),
    ]);

    const incomeTrend = await getMonthlyTrend(Income, userId);
    const expenseTrend = await getMonthlyTrend(Expense, userId);

    res.json({
      success: true,
      data: {
        overview: {
          income: { value: income, change: pctChange(income, prevInc), sparkline: incomeSpark },
          expenses: { value: expenses, change: pctChange(expenses, prevExp), sparkline: expenseSpark },
          savings: { value: savings, change: pctChange(savings, prevInc - prevExp), sparkline: savingsSpark },
          budgetLeft: { value: budgetLeft, change: 0, sparkline: expenseSpark },
          investments: {
            value: investmentValue,
            change: investmentInvested > 0 ? ((investmentValue - investmentInvested) / investmentInvested) * 100 : 0,
            sparkline: incomeSpark,
          },
          netWorth: { value: netWorth, change: pctChange(netWorth, netWorth * 0.95), sparkline: savingsSpark },
          cashFlow: { value: income - expenses, change: pctChange(income - expenses, prevInc - prevExp), sparkline: savingsSpark },
          monthlyGoal: { value: monthlyGoal, change: 0, sparkline: incomeSpark },
        },
        charts: {
          incomeVsExpense: incomeTrend.map((inc, i) => ({
            month: inc.month,
            income: inc.value,
            expense: expenseTrend[i]?.value || 0,
          })),
          categoryBreakdown: categoryBreakdown.map((c) => ({
            category: c._id,
            amount: c.total,
          })),
          savingsGrowth: incomeTrend.map((inc, i) => ({
            month: inc.month,
            savings: inc.value - (expenseTrend[i]?.value || 0),
          })),
        },
        goals: goals.slice(0, 5),
        recentExpenses: await Expense.find({ user: userId }).sort({ date: -1 }).limit(5),
        budgets: budgets.slice(0, 3),
      },
    });
  } catch (error) {
    next(error);
  }
};

export const getAnalytics = async (req, res, next) => {
  try {
    const userId = req.user._id;
    const period = req.query.period || 'this_year';
    const { start, end } = getDateRange(period === 'this_year' ? 'this_year' : period);

    const [
      monthlySpending,
      categoryBreakdown,
      weeklyTrend,
      cashFlow,
      budgetUsage,
      investmentAllocation,
      heatmapData,
    ] = await Promise.all([
      Expense.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        {
          $group: {
            _id: { month: { $month: '$date' }, year: { $year: '$date' } },
            total: { $sum: '$amount' },
          },
        },
        { $sort: { '_id.year': 1, '_id.month': 1 } },
      ]),
      Expense.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        { $group: { _id: '$category', total: { $sum: '$amount' }, count: { $sum: 1 } } },
        { $sort: { total: -1 } },
      ]),
      Expense.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        {
          $group: {
            _id: { week: { $week: '$date' } },
            total: { $sum: '$amount' },
          },
        },
        { $sort: { '_id.week': 1 } },
      ]),
      Promise.all([
        Income.aggregate([
          { $match: { user: userId, date: { $gte: start, $lte: end } } },
          { $group: { _id: { month: { $month: '$date' } }, total: { $sum: '$amount' } } },
        ]),
        Expense.aggregate([
          { $match: { user: userId, date: { $gte: start, $lte: end } } },
          { $group: { _id: { month: { $month: '$date' } }, total: { $sum: '$amount' } } },
        ]),
      ]),
      Budget.find({ user: userId, isActive: true }),
      Investment.aggregate([
        { $match: { user: userId, isActive: true } },
        { $group: { _id: '$type', total: { $sum: '$currentValue' } } },
      ]),
      Expense.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        {
          $group: {
            _id: { day: { $dayOfMonth: '$date' }, month: { $month: '$date' } },
            total: { $sum: '$amount' },
          },
        },
      ]),
    ]);

    const [incomeByMonth, expenseByMonth] = cashFlow;
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    res.json({
      success: true,
      data: {
        monthlySpending: monthlySpending.map((m) => ({
          month: months[m._id.month - 1],
          amount: m.total,
        })),
        categoryBreakdown: categoryBreakdown.map((c) => ({
          category: c._id,
          amount: c.total,
          count: c.count,
        })),
        weeklyTrend: weeklyTrend.map((w) => ({ week: `W${w._id.week}`, amount: w.total })),
        cashFlow: months.map((month, i) => ({
          month,
          income: incomeByMonth.find((m) => m._id.month === i + 1)?.total || 0,
          expense: expenseByMonth.find((m) => m._id.month === i + 1)?.total || 0,
        })),
        budgetUsage: budgetUsage.map((b) => ({
          name: b.name,
          total: b.totalAmount,
          spent: b.spentAmount,
          remaining: b.totalAmount - b.spentAmount,
          percent: b.totalAmount > 0 ? (b.spentAmount / b.totalAmount) * 100 : 0,
        })),
        investmentAllocation: investmentAllocation.map((i) => ({
          type: i._id,
          value: i.total,
        })),
        heatmap: heatmapData.map((h) => ({
          day: h._id.day,
          month: h._id.month,
          amount: h.total,
        })),
      },
    });
  } catch (error) {
    next(error);
  }
};

export const getInsights = async (req, res, next) => {
  try {
    const userId = req.user._id;
    const { start, end } = getDateRange('this_month');

    const [
      topCategory,
      topIncome,
      expensiveDay,
      expensiveMonth,
      budgets,
      goals,
      avgExpense,
    ] = await Promise.all([
      Expense.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        { $group: { _id: '$category', total: { $sum: '$amount' } } },
        { $sort: { total: -1 } },
        { $limit: 1 },
      ]),
      Income.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        { $group: { _id: '$category', total: { $sum: '$amount' } } },
        { $sort: { total: -1 } },
        { $limit: 1 },
      ]),
      Expense.aggregate([
        { $match: { user: userId } },
        {
          $group: {
            _id: { $dateToString: { format: '%Y-%m-%d', date: '$date' } },
            total: { $sum: '$amount' },
          },
        },
        { $sort: { total: -1 } },
        { $limit: 1 },
      ]),
      Expense.aggregate([
        { $match: { user: userId } },
        {
          $group: {
            _id: { $dateToString: { format: '%Y-%m', date: '$date' } },
            total: { $sum: '$amount' },
          },
        },
        { $sort: { total: -1 } },
        { $limit: 1 },
      ]),
      Budget.find({ user: userId, isActive: true }),
      Goal.find({ user: userId }),
      Expense.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        { $group: { _id: null, avg: { $avg: '$amount' }, total: { $sum: '$amount' } } },
      ]),
    ]);

    const totalIncome = await Income.aggregate([
      { $match: { user: userId, date: { $gte: start, $lte: end } } },
      { $group: { _id: null, total: { $sum: '$amount' } } },
    ]);
    const totalExpenses = avgExpense[0]?.total || 0;
    const income = totalIncome[0]?.total || 0;
    const savingsRate = income > 0 ? ((income - totalExpenses) / income) * 100 : 0;
    const budgetEfficiency = budgets.length > 0
      ? budgets.reduce((acc, b) => acc + (b.spentAmount <= b.totalAmount ? 1 : 0), 0) / budgets.length * 100
      : 100;

    const financialHealthScore = Math.min(100, Math.round(
      savingsRate * 0.4 + budgetEfficiency * 0.3 + (goals.filter((g) => g.isCompleted).length / Math.max(goals.length, 1)) * 100 * 0.3
    ));

    await req.user.constructor.findByIdAndUpdate(userId, { financialHealthScore });

    const moneyLeaks = await Expense.aggregate([
      { $match: { user: userId, date: { $gte: start, $lte: end } } },
      { $group: { _id: '$category', total: { $sum: '$amount' }, count: { $sum: 1 } } },
      { $match: { count: { $gte: 5 } } },
      { $sort: { total: -1 } },
      { $limit: 3 },
    ]);

    res.json({
      success: true,
      data: {
        topSpendingCategory: topCategory[0] ? { category: topCategory[0]._id, amount: topCategory[0].total } : null,
        highestIncomeSource: topIncome[0] ? { category: topIncome[0]._id, amount: topIncome[0].total } : null,
        mostExpensiveDay: expensiveDay[0] ? { date: expensiveDay[0]._id, amount: expensiveDay[0].total } : null,
        mostExpensiveMonth: expensiveMonth[0] ? { month: expensiveMonth[0]._id, amount: expensiveMonth[0].total } : null,
        savingsScore: Math.round(savingsRate),
        budgetEfficiency: Math.round(budgetEfficiency),
        financialHealthScore,
        moneyLeaks: moneyLeaks.map((m) => ({ category: m._id, amount: m.total, transactions: m.count })),
        possibleSavings: moneyLeaks.reduce((acc, m) => acc + m.total * 0.1, 0),
        goalsProgress: goals.map((g) => ({
          name: g.name,
          progress: g.targetAmount > 0 ? (g.currentAmount / g.targetAmount) * 100 : 0,
        })),
      },
    });
  } catch (error) {
    next(error);
  }
};

export const getNotifications = async (req, res, next) => {
  try {
    const notifications = await Notification.find({ user: req.user._id })
      .sort({ createdAt: -1 })
      .limit(50);
    const unreadCount = await Notification.countDocuments({ user: req.user._id, isRead: false });
    res.json({ success: true, data: { notifications, unreadCount } });
  } catch (error) {
    next(error);
  }
};

export const markNotificationRead = async (req, res, next) => {
  try {
    await Notification.findOneAndUpdate(
      { _id: req.params.id, user: req.user._id },
      { isRead: true }
    );
    res.json({ success: true });
  } catch (error) {
    next(error);
  }
};

export const markAllNotificationsRead = async (req, res, next) => {
  try {
    await Notification.updateMany({ user: req.user._id }, { isRead: true });
    res.json({ success: true });
  } catch (error) {
    next(error);
  }
};
