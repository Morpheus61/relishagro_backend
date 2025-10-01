// src/routes/auth.ts

import { Router, Request, Response } from 'express';
import { Pool } from 'pg';

// Initialize router
const router = Router();

// Assume you have a DB connection pool passed in or imported
// Option 1: Import pool from server.ts (recommended)
import { pool } from '../server'; // ✅ Make sure this matches your export

// Option 2: Or pass pool as dependency (better for testing)
// const authRouter = (pool: Pool) => {
//   const router = Router();
//   ...
//   return router;
// };

// POST /api/auth/login
router.post('/login', async (req: Request, res: Response) => {
  const { staff_id } = req.body;

  if (!staff_id || typeof staff_id !== 'string') {
    return res.status(400).json({ error: 'Valid Staff ID is required' });
  }

  try {
    // Query person_records by staff_id
    const result = await pool.query(
      `SELECT 
        pr.id,
        pr.first_name,
        pr.last_name,
        pr.full_name,
        pr.designation,
        pr.person_type,
        pr.status,
        pr.system_account_id
      FROM person_records pr
      WHERE pr.staff_id = $1`,
      [staff_id]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid Staff ID' });
    }

    const user = result.rows[0];

    if (user.status !== 'active') {
      return res.status(403).json({ error: 'Account is not active' });
    }

    // Determine role based on staff_id format
    let role: string;
    if (staff_id.startsWith('Admin-')) {
      role = 'admin';
    } else if (staff_id.startsWith('HarvestFlow-')) {
      role = 'harvestflow_manager';
    } else if (staff_id.startsWith('FlavorCore-')) {
      role = 'flavorcore_manager';
    } else if (staff_id.startsWith('HarvestSup-')) {
      role = 'harvest_supervisor';
    } else if (staff_id.startsWith('FlavorSup-')) {
      role = 'flavorcore_supervisor';
    } else if (staff_id.startsWith('Staff-')) {
      role = 'staff';
    } else {
      role = 'staff'; // fallback
    }

    // Return success response
    return res.json({
      authenticated: true,
      user: {
        id: user.id,
        full_name: user.full_name,
        role,
        designation: user.designation,
        person_type: user.person_type
      }
    });
  } catch (err) {
    console.error('Login error:', err);
    return res.status(500).json({ error: 'Authentication failed' });
  }
});

export default router;