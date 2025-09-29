// src/server.ts
import 'dotenv/config'; // ✅ Load .env into process.env

import express, { Request, Response } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import { Pool } from 'pg';

// Routes
import authRoutes from './routes/auth';
import attendanceRoutes from './routes/attendance';
import harvestFlowRoutes from './routes/harvestflow';
import flavorCoreRoutes from './routes/flavorcore';

const app = express();

app.use(helmet());
app.use(cors({ origin: process.env.FRONTEND_URL }));
app.use(morgan('dev'));
app.use(express.json());

// Database
export const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/attendance', attendanceRoutes);
app.use('/api/harvestflow', harvestFlowRoutes);
app.use('/api/flavorcore', flavorCoreRoutes);

app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
  console.log(`🚀 RelishAgro Backend running on port ${PORT}`);
});