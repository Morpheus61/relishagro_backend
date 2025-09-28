// src/routes/harvestflow.ts
import express from 'express';

const router = express.Router();

router.get('/', (req, res) => {
  res.json({ message: 'HarvestFlow API is working' });
});

export default router;