import mongoose from 'mongoose';

const expenseSchema = new mongoose.Schema(
  {
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, index: true },
    amount: { type: Number, required: true, min: 0 },
    category: {
      type: String,
      enum: [
        'food', 'travel', 'fuel', 'entertainment', 'shopping', 'medical',
        'bills', 'education', 'investment', 'rent', 'emi', 'insurance',
        'subscription', 'others',
      ],
      default: 'others',
    },
    description: { type: String, default: '' },
    date: { type: Date, required: true, default: Date.now },
    paymentMethod: {
      type: String,
      enum: ['cash', 'bank_transfer', 'upi', 'card', 'wallet', 'other'],
      default: 'upi',
    },
    tags: [{ type: String }],
    notes: { type: String, default: '' },
    attachment: { type: String, default: '' },
    receipt: { type: String, default: '' },
    location: {
      name: String,
      lat: Number,
      lng: Number,
    },
    isRecurring: { type: Boolean, default: false },
    recurringFrequency: {
      type: String,
      enum: ['daily', 'weekly', 'monthly', 'yearly'],
    },
    recurringEndDate: Date,
    ocrData: {
      merchant: String,
      extractedAmount: Number,
      extractedDate: Date,
    },
  },
  { timestamps: true }
);

expenseSchema.index({ user: 1, date: -1 });
expenseSchema.index({ user: 1, category: 1 });
expenseSchema.index({ description: 'text', notes: 'text', tags: 'text' });

export default mongoose.model('Expense', expenseSchema);
