import { Router } from 'express';
import Income from '../models/Income.js';
import Expense from '../models/Expense.js';
import Budget from '../models/Budget.js';
import Goal from '../models/Goal.js';
import Investment from '../models/Investment.js';
import { protect } from '../middleware/auth.js';
import { getDateRange } from '../utils/helpers.js';

const router = Router();
router.use(protect);

router.get('/csv', async (req, res, next) => {
  try {
    const userId = req.user._id;
    const { start, end } = req.query.startDate
      ? { start: new Date(req.query.startDate), end: new Date(req.query.endDate) }
      : getDateRange('this_month');

    const [income, expenses] = await Promise.all([
      Income.find({ user: userId, date: { $gte: start, $lte: end } }),
      Expense.find({ user: userId, date: { $gte: start, $lte: end } }),
    ]);

    let csv = 'Type,Date,Category,Amount,Description,Payment Method\n';
    income.forEach((i) => {
      csv += `Income,${i.date.toISOString().split('T')[0]},${i.category},${i.amount},"${i.description}",${i.paymentMethod}\n`;
    });
    expenses.forEach((e) => {
      csv += `Expense,${e.date.toISOString().split('T')[0]},${e.category},${e.amount},"${e.description}",${e.paymentMethod}\n`;
    });

    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename=finance-report.csv');
    res.send(csv);
  } catch (error) {
    next(error);
  }
});

router.get('/summary', async (req, res, next) => {
  try {
    const userId = req.user._id;
    const period = req.query.period || 'this_month';
    const { start, end } = getDateRange(period);

    const [income, expenses, budgets, goals, investments] = await Promise.all([
      Income.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        { $group: { _id: null, total: { $sum: '$amount' } } },
      ]),
      Expense.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        { $group: { _id: '$category', total: { $sum: '$amount' } } },
      ]),
      Budget.find({ user: userId }),
      Goal.find({ user: userId }),
      Investment.find({ user: userId }),
    ]);

    res.json({
      success: true,
      data: {
        period: { start, end },
        totalIncome: income[0]?.total || 0,
        expensesByCategory: expenses,
        budgets,
        goals,
        investments,
      },
    });
  } catch (error) {
    next(error);
  }
});

export default router;
