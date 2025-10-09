# backend/routes/workers.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from database import supabase
from models.person import PersonRecord

router = APIRouter()

@router.get("/")
def get_workers():
    try:
        response = supabase.table('person_records').select('*').execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))