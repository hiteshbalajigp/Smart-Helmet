import mongoose from 'mongoose';

const goalSchema = new mongoose.Schema(
  {
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, index: true },
    name: { type: String, required: true },
    targetAmount: { type: Number, required: true, min: 0 },
    currentAmount: { type: Number, default: 0, min: 0 },
    targetDate: { type: Date, required: true },
    category: {
      type: String,
      enum: ['bike', 'trip', 'emergency', 'laptop', 'car', 'wedding', 'house', 'vacation', 'other'],
      default: 'other',
    },
    icon: { type: String, default: '🎯' },
    color: { type: String, default: '#6366f1' },
    isCompleted: { type: Boolean, default: false },
    aiRecommendation: { type: String, default: '' },
    monthlyContribution: { type: Number, default: 0 },
    priority: { type: String, enum: ['low', 'medium', 'high'], default: 'medium' },
  },
  { timestamps: true }
);

goalSchema.virtual('progress').get(function () {
  return this.targetAmount > 0 ? (this.currentAmount / this.targetAmount) * 100 : 0;
});

goalSchema.virtual('remaining').get(function () {
  return Math.max(0, this.targetAmount - this.currentAmount);
});

export default mongoose.model('Goal', goalSchema);
