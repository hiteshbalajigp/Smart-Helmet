import { z } from 'zod';

export const validate = (schema) => (req, res, next) => {
  try {
    schema.parse({ body: req.body, query: req.query, params: req.params });
    next();
  } catch (error) {
    const messages = error.errors?.map((e) => `${e.path.join('.')}: ${e.message}`) || [error.message];
    return res.status(400).json({ success: false, message: messages.join(', ') });
  }
};

export const authSchemas = {
  register: z.object({
    body: z.object({
      name: z.string().min(2).max(100),
      email: z.string().email(),
      password: z.string().min(8).max(128),
    }),
  }),
  login: z.object({
    body: z.object({
      email: z.string().email(),
      password: z.string().min(1),
    }),
  }),
  forgotPassword: z.object({
    body: z.object({ email: z.string().email() }),
  }),
  resetPassword: z.object({
    body: z.object({
      token: z.string(),
      password: z.string().min(8).max(128),
    }),
  }),
};

export const transactionSchemas = {
  income: z.object({
    body: z.object({
      amount: z.number().positive(),
      category: z.string().optional(),
      description: z.string().optional(),
      date: z.string().or(z.date()).optional(),
      paymentMethod: z.string().optional(),
      tags: z.array(z.string()).optional(),
      notes: z.string().optional(),
      isRecurring: z.boolean().optional(),
      recurringFrequency: z.string().optional(),
    }),
  }),
  expense: z.object({
    body: z.object({
      amount: z.number().positive(),
      category: z.string().optional(),
      description: z.string().optional(),
      date: z.string().or(z.date()).optional(),
      paymentMethod: z.string().optional(),
      tags: z.array(z.string()).optional(),
      notes: z.string().optional(),
      location: z.object({ name: z.string().optional() }).optional(),
      isRecurring: z.boolean().optional(),
    }),
  }),
  budget: z.object({
    body: z.object({
      name: z.string().min(1),
      type: z.string().optional(),
      totalAmount: z.number().positive(),
      startDate: z.string().or(z.date()),
      endDate: z.string().or(z.date()),
      categories: z.array(z.object({
        category: z.string(),
        limit: z.number().positive(),
      })).optional(),
    }),
  }),
  goal: z.object({
    body: z.object({
      name: z.string().min(1),
      targetAmount: z.number().positive(),
      targetDate: z.string().or(z.date()),
      category: z.string().optional(),
      monthlyContribution: z.number().optional(),
    }),
  }),
  investment: z.object({
    body: z.object({
      name: z.string().min(1),
      type: z.string().optional(),
      investedAmount: z.number().positive(),
      currentValue: z.number().positive(),
      purchaseDate: z.string().or(z.date()).optional(),
    }),
  }),
};
