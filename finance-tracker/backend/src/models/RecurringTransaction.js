import mongoose from 'mongoose';

const recurringSchema = new mongoose.Schema(
  {
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, index: true },
    type: { type: String, enum: ['income', 'expense'], required: true },
    amount: { type: Number, required: true, min: 0 },
    category: { type: String, required: true },
    description: { type: String, default: '' },
    frequency: {
      type: String,
      enum: ['daily', 'weekly', 'monthly', 'yearly'],
      default: 'monthly',
    },
    nextDate: { type: Date, required: true },
    endDate: Date,
    paymentMethod: { type: String, default: 'bank_transfer' },
    isActive: { type: Boolean, default: true },
    autoGenerate: { type: Boolean, default: true },
    lastGenerated: Date,
  },
  { timestamps: true }
);

export default mongoose.model('RecurringTransaction', recurringSchema);
