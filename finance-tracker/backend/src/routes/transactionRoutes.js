import { Router } from 'express';
import {
  incomeController, expenseController, budgetController,
  goalController, investmentController, contributeToGoal, globalSearch,
} from '../controllers/transactionController.js';
import { protect } from '../middleware/auth.js';
import { validate, transactionSchemas } from '../validation/schemas.js';
import { upload } from '../middleware/upload.js';

const router = Router();
router.use(protect);

router.get('/search', globalSearch);

router.route('/income')
  .get(incomeController.getAll)
  .post(validate(transactionSchemas.income), incomeController.create);
router.route('/income/:id')
  .get(incomeController.getOne)
  .put(incomeController.update)
  .delete(incomeController.delete);

router.route('/expenses')
  .get(expenseController.getAll)
  .post(validate(transactionSchemas.expense), expenseController.create);
router.route('/expenses/:id')
  .get(expenseController.getOne)
  .put(expenseController.update)
  .delete(expenseController.delete);

router.route('/budgets')
  .get(budgetController.getAll)
  .post(validate(transactionSchemas.budget), budgetController.create);
router.route('/budgets/:id')
  .get(budgetController.getOne)
  .put(budgetController.update)
  .delete(budgetController.delete);

router.route('/goals')
  .get(goalController.getAll)
  .post(validate(transactionSchemas.goal), goalController.create);
router.route('/goals/:id')
  .get(goalController.getOne)
  .put(goalController.update)
  .delete(goalController.delete);
router.post('/goals/:id/contribute', contributeToGoal);

router.route('/investments')
  .get(investmentController.getAll)
  .post(validate(transactionSchemas.investment), investmentController.create);
router.route('/investments/:id')
  .get(investmentController.getOne)
  .put(investmentController.update)
  .delete(investmentController.delete);

export default router;
