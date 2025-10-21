from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime
from database import get_db_connection
from routes.auth import get_current_user

router = APIRouter()

@router.get("/yields")
async def get_yields(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    lot_id: Optional[str] = Query(None),
    current_user = Depends(get_current_user)
):
    """Get yield data with optional filters"""
    try:
        conn = await get_db_connection()
        
        where_conditions = []
        params = []
        param_count = 1
        
        if date_from:
            where_conditions.append(f"date_harvested >= ${param_count}")
            params.append(date_from)
            param_count += 1
        
        if date_to:
            where_conditions.append(f"date_harvested <= ${param_count}")
            params.append(date_to)
            param_count += 1
        
        if lot_id:
            where_conditions.append(f"lot_id = ${param_count}")
            params.append(lot_id)
            param_count += 1
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
        
        query = f"""
        SELECT 
            lot_id,
            crop,
            raw_weight,
            threshed_weight,
            estate_yield_pct,
            date_harvested,
            created_by
        FROM lots
        {where_clause}
        ORDER BY date_harvested DESC
        """
        
        rows = await conn.fetch(query, *params)
        await conn.close()
        
        yields = []
        for row in rows:
            yields.append({
                "lot_id": row['lot_id'],
                "crop": row['crop'],
                "raw_weight": float(row['raw_weight']) if row['raw_weight'] else 0,
                "threshed_weight": float(row['threshed_weight']) if row['threshed_weight'] else 0,
                "yield_percentage": float(row['estate_yield_pct']) if row['estate_yield_pct'] else 0,
                "date": row['date_harvested'].isoformat() if row['date_harvested'] else None
            })
        
        return {
            "success": True,
            "data": yields,
            "count": len(yields)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching yields: {str(e)}")