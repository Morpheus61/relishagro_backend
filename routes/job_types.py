# backend/routes/job_types.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from database import supabase

router = APIRouter()

@router.get("/")
def get_job_types():
    try:
        response = supabase.table('job_types').select('*').execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))