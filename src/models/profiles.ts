// src/models/profiles.ts
export interface Profile {
  id: string;
  email: string;
  full_name: string;
  role: 'admin' | 'harvestflow_manager' | 'flavorcore_manager' | 'staff';
  created_at: Date;
}