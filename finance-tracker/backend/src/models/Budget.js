import mongoose from 'mongoose';

const budgetSchema = new mongoose.Schema(
  {
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, index: true },
    name: { type: String, required: true },
    type: {
      type: String,
      enum: ['monthly', 'weekly', 'daily', 'custom'],
      default: 'monthly',
    },
    totalAmount: { type: Number, required: true, min: 0 },
    spentAmount: { type: Number, default: 0 },
    startDate: { type: Date, required: true },
    endDate: { type: Date, required: true },
    categories: [{
      category: { type: String, required: true },
      limit: { type: Number, required: true },
      spent: { type: Number, default: 0 },
    }],
    alerts: {
      enabled: { type: Boolean, default: true },
      threshold: { type: Number, default: 80 },
    },
    isActive: { type: Boolean, default: true },
  },
  { timestamps: true }
);

budgetSchema.virtual('remaining').get(function () {
  return Math.max(0, this.totalAmount - this.spentAmount);
});

budgetSchema.virtual('usagePercent').get(function () {
  return this.totalAmount > 0 ? (this.spentAmount / this.totalAmount) * 100 : 0;
});

export default mongoose.model('Budget', budgetSchema);
