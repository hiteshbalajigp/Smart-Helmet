import { Router } from 'express';
import RecurringTransaction from '../models/RecurringTransaction.js';
import Income from '../models/Income.js';
import Expense from '../models/Expense.js';
import Notification from '../models/Notification.js';
import { protect } from '../middleware/auth.js';

const router = Router();
router.use(protect);

router.get('/', async (req, res, next) => {
  try {
    const items = await RecurringTransaction.find({ user: req.user._id }).sort({ nextDate: 1 });
    res.json({ success: true, data: items });
  } catch (error) {
    next(error);
  }
});

router.post('/', async (req, res, next) => {
  try {
    const item = await RecurringTransaction.create({ ...req.body, user: req.user._id });
    res.status(201).json({ success: true, data: item });
  } catch (error) {
    next(error);
  }
});

router.put('/:id', async (req, res, next) => {
  try {
    const item = await RecurringTransaction.findOneAndUpdate(
      { _id: req.params.id, user: req.user._id },
      req.body,
      { new: true }
    );
    if (!item) return res.status(404).json({ success: false, message: 'Not found' });
    res.json({ success: true, data: item });
  } catch (error) {
    next(error);
  }
});

router.delete('/:id', async (req, res, next) => {
  try {
    await RecurringTransaction.findOneAndDelete({ _id: req.params.id, user: req.user._id });
    res.json({ success: true, message: 'Deleted' });
  } catch (error) {
    next(error);
  }
});

router.post('/generate', async (req, res, next) => {
  try {
    const due = await RecurringTransaction.find({
      user: req.user._id,
      isActive: true,
      autoGenerate: true,
      nextDate: { $lte: new Date() },
    });

    const generated = [];
    for (const item of due) {
      const data = {
        user: req.user._id,
        amount: item.amount,
        category: item.category,
        description: item.description,
        date: item.nextDate,
        paymentMethod: item.paymentMethod,
        isRecurring: true,
        recurringFrequency: item.frequency,
      };

      if (item.type === 'income') {
        await Income.create(data);
      } else {
        await Expense.create(data);
      }

      const next = new Date(item.nextDate);
      switch (item.frequency) {
        case 'daily': next.setDate(next.getDate() + 1); break;
        case 'weekly': next.setDate(next.getDate() + 7); break;
        case 'monthly': next.setMonth(next.getMonth() + 1); break;
        case 'yearly': next.setFullYear(next.getFullYear() + 1); break;
      }

      item.nextDate = next;
      item.lastGenerated = new Date();
      if (item.endDate && next > item.endDate) item.isActive = false;
      await item.save();

      await Notification.create({
        user: req.user._id,
        type: 'recurring_payment',
        title: `Recurring ${item.type} generated`,
        message: `${item.description || item.category}: ₹${item.amount}`,
      });

      generated.push(item);
    }

    res.json({ success: true, data: generated, count: generated.length });
  } catch (error) {
    next(error);
  }
});

export default router;
