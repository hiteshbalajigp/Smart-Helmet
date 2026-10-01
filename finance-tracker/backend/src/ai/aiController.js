import OpenAI from 'openai';
import AIChat from '../models/AIChat.js';
import Income from '../models/Income.js';
import Expense from '../models/Expense.js';
import Budget from '../models/Budget.js';
import Goal from '../models/Goal.js';
import Investment from '../models/Investment.js';
import Notification from '../models/Notification.js';
import { getDateRange } from '../utils/helpers.js';

let openai = null;

const getOpenAI = () => {
  if (!openai && process.env.OPENAI_API_KEY && process.env.OPENAI_API_KEY !== 'your-openai-api-key') {
    openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  }
  return openai;
};

const buildFinancialContext = async (userId) => {
  const { start, end } = getDateRange('this_month');
  const [income, expenses, budgets, goals, investments, recentExpenses] = await Promise.all([
    Income.aggregate([
      { $match: { user: userId, date: { $gte: start, $lte: end } } },
      { $group: { _id: '$category', total: { $sum: '$amount' } } },
    ]),
    Expense.aggregate([
      { $match: { user: userId, date: { $gte: start, $lte: end } } },
      { $group: { _id: '$category', total: { $sum: '$amount' }, count: { $sum: 1 } } },
    ]),
    Budget.find({ user: userId, isActive: true }).lean(),
    Goal.find({ user: userId }).lean(),
    Investment.find({ user: userId, isActive: true }).lean(),
    Expense.find({ user: userId }).sort({ date: -1 }).limit(10).lean(),
  ]);

  const totalIncome = income.reduce((a, i) => a + i.total, 0);
  const totalExpenses = expenses.reduce((a, e) => a + e.total, 0);

  return `
User Financial Context (Current Month):
- Total Income: ₹${totalIncome.toLocaleString('en-IN')}
- Total Expenses: ₹${totalExpenses.toLocaleString('en-IN')}
- Savings: ₹${(totalIncome - totalExpenses).toLocaleString('en-IN')}
- Income Breakdown: ${JSON.stringify(income)}
- Expense Breakdown: ${JSON.stringify(expenses)}
- Active Budgets: ${JSON.stringify(budgets.map((b) => ({ name: b.name, total: b.totalAmount, spent: b.spentAmount })))}
- Savings Goals: ${JSON.stringify(goals.map((g) => ({ name: g.name, target: g.targetAmount, current: g.currentAmount, progress: ((g.currentAmount / g.targetAmount) * 100).toFixed(1) + '%' })))}
- Investments: ${JSON.stringify(investments.map((i) => ({ name: i.name, type: i.type, value: i.currentValue })))}
- Recent Expenses: ${JSON.stringify(recentExpenses.map((e) => ({ amount: e.amount, category: e.category, description: e.description, date: e.date })))}
`;
};

const SYSTEM_PROMPT = `You are FinAI, an expert personal finance assistant for Indian users. You help with budgeting, saving, investing basics, expense analysis, and goal planning.

Guidelines:
- Use ₹ (INR) for currency
- Be concise, actionable, and friendly
- Reference the user's actual financial data when provided
- Give specific numbers and percentages when possible
- Suggest practical Indian context tips (UPI, SIP, PPF, etc.)
- Never give specific stock/crypto buy/sell advice
- Format responses with markdown when helpful`;

const generateFallbackResponse = (message, context) => {
  const lower = message.toLowerCase();
  if (lower.includes('spend') || lower.includes('spending')) {
    return `Based on your current month data:\n\n${context.includes('Total Expenses') ? context.split('Recent Expenses')[0] : ''}\n\n**Tips to reduce spending:**\n1. Review subscription services\n2. Set category-wise limits\n3. Use the 50/30/20 rule (Needs/Wants/Savings)`;
  }
  if (lower.includes('save') || lower.includes('saving')) {
    return `**Savings Recommendations:**\n1. Automate transfers on salary day\n2. Start a SIP with ₹500/month minimum\n3. Build 6-month emergency fund first\n4. Review your top 3 expense categories for cuts`;
  }
  if (lower.includes('budget')) {
    return `**Suggested Budget Framework (50/30/20):**\n- 50% Needs (rent, bills, groceries)\n- 30% Wants (entertainment, dining)\n- 20% Savings & Investments\n\nCreate category budgets in the Budget module for better tracking.`;
  }
  if (lower.includes('invest')) {
    return `**Investment Basics for Beginners:**\n1. Emergency fund first (3-6 months expenses)\n2. PPF/FD for safe returns\n3. Index mutual funds via SIP for long-term\n4. Keep crypto allocation under 5%\n\nCheck your Investment tracker for current allocation.`;
  }
  if (lower.includes('laptop') || lower.includes('buy')) {
    return `To determine if you can afford a purchase:\n1. Check your savings after this month's expenses\n2. Ensure emergency fund isn't touched\n3. If purchase > 1 month income, consider saving for 2-3 months\n\nShare the amount and I can analyze your cash flow!`;
  }
  return `I'm your AI finance assistant! I can help you with:\n- 📊 Spending analysis\n- 💰 Savings tips\n- 📈 Budget planning\n- 🎯 Goal tracking\n- 🔮 Expense predictions\n\nAsk me anything about your finances!`;
};

export const chat = async (req, res, next) => {
  try {
    const { message, chatId } = req.body;
    const userId = req.user._id;
    const context = await buildFinancialContext(userId);

    let chat = chatId
      ? await AIChat.findOne({ _id: chatId, user: userId })
      : null;

    if (!chat) {
      chat = await AIChat.create({
        user: userId,
        title: message.slice(0, 50),
        messages: [{ role: 'system', content: SYSTEM_PROMPT + '\n\n' + context }],
      });
    } else {
      chat.messages.push({ role: 'user', content: message });
    }

    let assistantMessage;
    const client = getOpenAI();

    if (client) {
      const messages = [
        { role: 'system', content: SYSTEM_PROMPT + '\n\n' + context },
        ...chat.messages.filter((m) => m.role !== 'system').slice(-10).map((m) => ({
          role: m.role,
          content: m.content,
        })),
        { role: 'user', content: message },
      ];

      const completion = await client.chat.completions.create({
        model: 'gpt-4o-mini',
        messages,
        max_tokens: 1000,
        temperature: 0.7,
      });
      assistantMessage = completion.choices[0].message.content;
    } else {
      assistantMessage = generateFallbackResponse(message, context);
    }

    chat.messages.push({ role: 'assistant', content: assistantMessage });
    await chat.save();

    res.json({
      success: true,
      data: {
        chatId: chat._id,
        message: assistantMessage,
        title: chat.title,
      },
    });
  } catch (error) {
    next(error);
  }
};

export const getChatHistory = async (req, res, next) => {
  try {
    const chats = await AIChat.find({ user: req.user._id, isActive: true })
      .select('title createdAt updatedAt messages')
      .sort({ updatedAt: -1 })
      .limit(20);
    res.json({ success: true, data: chats });
  } catch (error) {
    next(error);
  }
};

export const getChat = async (req, res, next) => {
  try {
    const chat = await AIChat.findOne({ _id: req.params.id, user: req.user._id });
    if (!chat) return res.status(404).json({ success: false, message: 'Chat not found' });
    res.json({ success: true, data: chat });
  } catch (error) {
    next(error);
  }
};

export const generateMonthlyReport = async (req, res, next) => {
  try {
    const userId = req.user._id;
    const { start, end } = getDateRange('this_month');
    const context = await buildFinancialContext(userId);

    let summary;
    const client = getOpenAI();

    if (client) {
      const completion = await client.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: `Generate a comprehensive monthly financial report based on this data:\n${context}\n\nInclude: summary, top insights, recommendations, and next month predictions.` },
        ],
        max_tokens: 1500,
      });
      summary = completion.choices[0].message.content;
    } else {
      summary = `## Monthly Financial Report\n\n${context}\n\n**Recommendations:**\n1. Track daily expenses\n2. Review budget allocations\n3. Increase savings rate by 5%`;
    }

    await Notification.create({
      user: userId,
      type: 'monthly_report',
      title: 'Monthly Report Ready',
      message: 'Your AI-generated monthly financial report is available.',
      link: '/insights',
    });

    res.json({ success: true, data: { summary, period: { start, end } } });
  } catch (error) {
    next(error);
  }
};

export const predictExpenses = async (req, res, next) => {
  try {
    const userId = req.user._id;
    const threeMonthsAgo = new Date();
    threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);

    const monthlyExpenses = await Expense.aggregate([
      { $match: { user: userId, date: { $gte: threeMonthsAgo } } },
      {
        $group: {
          _id: { month: { $month: '$date' }, category: '$category' },
          total: { $sum: '$amount' },
        },
      },
    ]);

    const categoryTotals = {};
    monthlyExpenses.forEach((e) => {
      if (!categoryTotals[e._id.category]) categoryTotals[e._id.category] = [];
      categoryTotals[e._id.category].push(e.total);
    });

    const predictions = Object.entries(categoryTotals).map(([category, totals]) => {
      const avg = totals.reduce((a, b) => a + b, 0) / totals.length;
      return { category, predicted: Math.round(avg), trend: totals.length > 1 && totals[totals.length - 1] > totals[0] ? 'up' : 'stable' };
    });

    const totalPredicted = predictions.reduce((a, p) => a + p.predicted, 0);

    res.json({
      success: true,
      data: {
        totalPredicted,
        byCategory: predictions,
        confidence: monthlyExpenses.length > 6 ? 'high' : 'medium',
      },
    });
  } catch (error) {
    next(error);
  }
};

export const scanReceipt = async (req, res, next) => {
  try {
    const client = getOpenAI();
    if (!client || !req.file) {
      return res.json({
        success: true,
        data: {
          merchant: 'Unknown Merchant',
          amount: 0,
          date: new Date().toISOString(),
          category: 'others',
          note: 'OCR requires OpenAI API key and receipt image',
        },
      });
    }

    const base64 = req.file.buffer.toString('base64');
    const completion = await client.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        {
          role: 'user',
          content: [
            { type: 'text', text: 'Extract from this receipt: merchant name, total amount (number only), date (ISO format), and suggest expense category (food/travel/shopping/medical/bills/others). Return JSON only.' },
            { type: 'image_url', image_url: { url: `data:${req.file.mimetype};base64,${base64}` } },
          ],
        },
      ],
      max_tokens: 300,
    });

    let parsed;
    try {
      parsed = JSON.parse(completion.choices[0].message.content.replace(/```json\n?|\n?```/g, ''));
    } catch {
      parsed = { merchant: 'Unknown', amount: 0, category: 'others' };
    }

    res.json({ success: true, data: parsed });
  } catch (error) {
    next(error);
  }
};

export const whatIfSimulator = async (req, res, next) => {
  try {
    const { monthlySaving, targetAmount, itemName } = req.body;
    const userId = req.user._id;
    const { start, end } = getDateRange('this_month');

    const [income, expenses] = await Promise.all([
      Income.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        { $group: { _id: null, total: { $sum: '$amount' } } },
      ]),
      Expense.aggregate([
        { $match: { user: userId, date: { $gte: start, $lte: end } } },
        { $group: { _id: null, total: { $sum: '$amount' } } },
      ]),
    ]);

    const currentSavings = (income[0]?.total || 0) - (expenses[0]?.total || 0);
    const effectiveSaving = monthlySaving || Math.max(currentSavings, 0);
    const monthsToGoal = effectiveSaving > 0 ? Math.ceil(targetAmount / effectiveSaving) : Infinity;
    const completionDate = new Date();
    completionDate.setMonth(completionDate.getMonth() + monthsToGoal);

    res.json({
      success: true,
      data: {
        itemName: itemName || 'Purchase',
        targetAmount,
        monthlySaving: effectiveSaving,
        monthsToGoal: monthsToGoal === Infinity ? null : monthsToGoal,
        estimatedCompletion: monthsToGoal === Infinity ? null : completionDate,
        currentMonthlySavings: currentSavings,
        feasible: monthsToGoal <= 24,
      },
    });
  } catch (error) {
    next(error);
  }
};
