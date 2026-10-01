import mongoose from 'mongoose';

const reportSchema = new mongoose.Schema(
  {
    user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, index: true },
    type: { type: String, enum: ['monthly', 'yearly', 'custom'], default: 'monthly' },
    title: { type: String, required: true },
    startDate: Date,
    endDate: Date,
    data: { type: mongoose.Schema.Types.Mixed },
    aiSummary: { type: String, default: '' },
    format: { type: String, enum: ['pdf', 'excel', 'csv'], default: 'pdf' },
    fileUrl: { type: String, default: '' },
  },
  { timestamps: true }
);

export default mongoose.model('Report', reportSchema);
