import { Router } from 'express';
import {
  chat, getChatHistory, getChat, generateMonthlyReport,
  predictExpenses, scanReceipt, whatIfSimulator,
} from '../ai/aiController.js';
import { protect } from '../middleware/auth.js';
import { upload } from '../middleware/upload.js';

const router = Router();
router.use(protect);

router.post('/chat', chat);
router.get('/chats', getChatHistory);
router.get('/chats/:id', getChat);
router.get('/monthly-report', generateMonthlyReport);
router.get('/predict-expenses', predictExpenses);
router.post('/scan-receipt', upload.single('receipt'), scanReceipt);
router.post('/what-if', whatIfSimulator);

export default router;
