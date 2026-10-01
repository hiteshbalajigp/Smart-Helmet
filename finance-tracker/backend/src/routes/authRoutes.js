import { Router } from 'express';
import {
  register, login, googleLogin, refreshAccessToken, logout,
  forgotPassword, resetPassword, verifyEmail, getMe, updateProfile, deleteAccount,
} from '../controllers/authController.js';
import { protect } from '../middleware/auth.js';
import { validate, authSchemas } from '../validation/schemas.js';

const router = Router();

router.post('/register', validate(authSchemas.register), register);
router.post('/login', validate(authSchemas.login), login);
router.post('/google', googleLogin);
router.post('/refresh', refreshAccessToken);
router.post('/logout', protect, logout);
router.post('/forgot-password', validate(authSchemas.forgotPassword), forgotPassword);
router.post('/reset-password', validate(authSchemas.resetPassword), resetPassword);
router.get('/verify-email/:token', verifyEmail);
router.get('/me', protect, getMe);
router.put('/profile', protect, updateProfile);
router.delete('/account', protect, deleteAccount);

export default router;
