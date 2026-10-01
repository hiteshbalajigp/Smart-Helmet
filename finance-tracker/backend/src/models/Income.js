import mongoose from 'mongoose';

const incomeSchema = new mongoose.Schema(
  {
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, index: true },
    amount: { type: Number, required: true, min: 0 },
    category: {
      type: String,
      enum: ['salary', 'business', 'freelancing', 'rental', 'passive', 'other'],
      default: 'salary',
    },
    description: { type: String, default: '' },
    date: { type: Date, required: true, default: Date.now },
    paymentMethod: {
      type: String,
      enum: ['cash', 'bank_transfer', 'upi', 'card', 'cheque', 'other'],
      default: 'bank_transfer',
    },
    tags: [{ type: String }],
    notes: { type: String, default: '' },
    attachment: { type: String, default: '' },
    isRecurring: { type: Boolean, default: false },
    recurringFrequency: {
      type: String,
      enum: ['daily', 'weekly', 'monthly', 'yearly'],
    },
    recurringEndDate: Date,
  },
  { timestamps: true }
);

incomeSchema.index({ user: 1, date: -1 });
incomeSchema.index({ description: 'text', notes: 'text', tags: 'text' });

export default mongoose.model('Income', incomeSchema);
