import { Router } from 'express';
import {
  getDashboard, getAnalytics, getInsights,
  getNotifications, markNotificationRead, markAllNotificationsRead,
} from '../controllers/dashboardController.js';
import { protect } from '../middleware/auth.js';

const router = Router();
router.use(protect);

router.get('/dashboard', getDashboard);
router.get('/analytics', getAnalytics);
router.get('/insights', getInsights);
router.get('/notifications', getNotifications);
router.put('/notifications/:id/read', markNotificationRead);
router.put('/notifications/read-all', markAllNotificationsRead);

export default router;
