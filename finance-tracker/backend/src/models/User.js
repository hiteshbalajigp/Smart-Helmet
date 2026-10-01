import mongoose from 'mongoose';
import bcrypt from 'bcryptjs';

const userSchema = new mongoose.Schema(
  {
    name: { type: String, required: true, trim: true },
    email: { type: String, required: true, unique: true, lowercase: true },
    password: { type: String, select: false },
    avatar: { type: String, default: '' },
    googleId: { type: String, sparse: true },
    isVerified: { type: Boolean, default: false },
    verificationToken: String,
    verificationTokenExpires: Date,
    resetPasswordToken: String,
    resetPasswordExpires: Date,
    refreshToken: { type: String, select: false },
    settings: {
      currency: { type: String, default: 'INR' },
      theme: { type: String, enum: ['light', 'dark', 'system'], default: 'dark' },
      notifications: { type: Boolean, default: true },
      language: { type: String, default: 'en' },
    },
    financialHealthScore: { type: Number, default: 0 },
    streak: { type: Number, default: 0 },
    badges: [{ type: String }],
    lastActive: Date,
  },
  { timestamps: true }
);

userSchema.pre('save', async function (next) {
  if (!this.isModified('password') || !this.password) return next();
  this.password = await bcrypt.hash(this.password, 12);
  next();
});

userSchema.methods.comparePassword = async function (candidate) {
  return bcrypt.compare(candidate, this.password);
};

export default mongoose.model('User', userSchema);
