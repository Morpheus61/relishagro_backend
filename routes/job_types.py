@router.get("/jobs")
async def get_jobs(
    current_user = Depends(get_current_user)
):
    """Get all daily jobs"""
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            id,
            job_name,
            category,
            unit_of_measurement,
            expected_output_per_worker,
            created_at
        FROM daily_job_types
        ORDER BY job_name
        """
        
        rows = await conn.fetch(query)
        await conn.close()
        
        jobs = []
        for row in rows:
            jobs.append({
                "id": str(row['id']),
                "name": row['job_name'],
                "category": row['category'],
                "unit": row['unit_of_measurement'],
                "expected_output": float(row['expected_output_per_worker']) if row['expected_output_per_worker'] else 0
            })
        
        return {
            "success": True,
            "data": jobs
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching jobs: {str(e)}")