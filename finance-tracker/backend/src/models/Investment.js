import mongoose from 'mongoose';

const investmentSchema = new mongoose.Schema(
  {
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, index: true },
    name: { type: String, required: true },
    type: {
      type: String,
      enum: ['stocks', 'mutual_funds', 'gold', 'crypto', 'fd', 'ppf', 'nps', 'other'],
      default: 'mutual_funds',
    },
    investedAmount: { type: Number, required: true, min: 0 },
    currentValue: { type: Number, required: true, min: 0 },
    purchaseDate: { type: Date, default: Date.now },
    units: { type: Number, default: 0 },
    symbol: { type: String, default: '' },
    notes: { type: String, default: '' },
    isActive: { type: Boolean, default: true },
  },
  { timestamps: true }
);

investmentSchema.virtual('returns').get(function () {
  return this.currentValue - this.investedAmount;
});

investmentSchema.virtual('returnsPercent').get(function () {
  return this.investedAmount > 0
    ? ((this.currentValue - this.investedAmount) / this.investedAmount) * 100
    : 0;
});

export default mongoose.model('Investment', investmentSchema);
