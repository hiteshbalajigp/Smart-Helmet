import Income from '../models/Income.js';
import Expense from '../models/Expense.js';
import Budget from '../models/Budget.js';
import Goal from '../models/Goal.js';
import Investment from '../models/Investment.js';
import { buildDateFilter, paginate } from '../utils/helpers.js';

const createCrudController = (Model, options = {}) => ({
  create: async (req, res, next) => {
    try {
      const data = { ...req.body, user: req.user._id };
      if (data.date) data.date = new Date(data.date);
      const item = await Model.create(data);

      if (options.onCreate) await options.onCreate(item, req.user._id);

      res.status(201).json({ success: true, data: item });
    } catch (error) {
      next(error);
    }
  },

  getAll: async (req, res, next) => {
    try {
      const { page, limit, skip } = paginate(req.query);
      const filter = { user: req.user._id, ...buildDateFilter(req.query) };
      if (req.query.category) filter.category = req.query.category;
      if (req.query.search) filter.$text = { $search: req.query.search };

      const [items, total] = await Promise.all([
        Model.find(filter).sort({ date: -1 }).skip(skip).limit(limit),
        Model.countDocuments(filter),
      ]);

      res.json({
        success: true,
        data: items,
        pagination: { page, limit, total, pages: Math.ceil(total / limit) },
      });
    } catch (error) {
      next(error);
    }
  },

  getOne: async (req, res, next) => {
    try {
      const item = await Model.findOne({ _id: req.params.id, user: req.user._id });
      if (!item) return res.status(404).json({ success: false, message: 'Not found' });
      res.json({ success: true, data: item });
    } catch (error) {
      next(error);
    }
  },

  update: async (req, res, next) => {
    try {
      const data = { ...req.body };
      if (data.date) data.date = new Date(data.date);
      const item = await Model.findOneAndUpdate(
        { _id: req.params.id, user: req.user._id },
        data,
        { new: true, runValidators: true }
      );
      if (!item) return res.status(404).json({ success: false, message: 'Not found' });
      res.json({ success: true, data: item });
    } catch (error) {
      next(error);
    }
  },

  delete: async (req, res, next) => {
    try {
      const item = await Model.findOneAndDelete({ _id: req.params.id, user: req.user._id });
      if (!item) return res.status(404).json({ success: false, message: 'Not found' });
      res.json({ success: true, message: 'Deleted successfully' });
    } catch (error) {
      next(error);
    }
  },
});

const updateBudgetSpending = async (expense, userId) => {
  const budgets = await Budget.find({
    user: userId,
    isActive: true,
    startDate: { $lte: expense.date },
    endDate: { $gte: expense.date },
  });

  for (const budget of budgets) {
    budget.spentAmount += expense.amount;
    const catBudget = budget.categories.find((c) => c.category === expense.category);
    if (catBudget) catBudget.spent += expense.amount;
    await budget.save();
  }
};

export const incomeController = createCrudController(Income);
export const expenseController = createCrudController(Expense, {
  onCreate: updateBudgetSpending,
});
export const budgetController = createCrudController(Budget);
export const goalController = createCrudController(Goal);
export const investmentController = createCrudController(Investment);

export const contributeToGoal = async (req, res, next) => {
  try {
    const { amount } = req.body;
    const goal = await Goal.findOne({ _id: req.params.id, user: req.user._id });
    if (!goal) return res.status(404).json({ success: false, message: 'Goal not found' });

    goal.currentAmount += amount;
    if (goal.currentAmount >= goal.targetAmount) {
      goal.isCompleted = true;
      goal.currentAmount = goal.targetAmount;
    }
    await goal.save();

    res.json({ success: true, data: goal });
  } catch (error) {
    next(error);
  }
};

export const globalSearch = async (req, res, next) => {
  try {
    const { q, type } = req.query;
    const userId = req.user._id;
    const results = { income: [], expenses: [], goals: [], investments: [] };

    if (!q) return res.json({ success: true, data: results });

    const searchFilter = { user: userId, $text: { $search: q } };
    const amountFilter = { user: userId, amount: parseFloat(q) || -1 };

    if (!type || type === 'income') {
      results.income = await Income.find(
        isNaN(parseFloat(q)) ? searchFilter : amountFilter
      ).limit(10).sort({ date: -1 });
    }
    if (!type || type === 'expense') {
      results.expenses = await Expense.find(
        isNaN(parseFloat(q)) ? searchFilter : amountFilter
      ).limit(10).sort({ date: -1 });
    }
    if (!type || type === 'goal') {
      results.goals = await Goal.find({ user: userId, name: { $regex: q, $options: 'i' } }).limit(10);
    }
    if (!type || type === 'investment') {
      results.investments = await Investment.find({ user: userId, name: { $regex: q, $options: 'i' } }).limit(10);
    }

    res.json({ success: true, data: results });
  } catch (error) {
    next(error);
  }
};
