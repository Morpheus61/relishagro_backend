// src/routes/flavorcore.ts
import express from 'express';

const router = express.Router();

router.get('/', (req, res) => {
  res.json({ message: 'FlavorCore API is working' });
});

export default router;