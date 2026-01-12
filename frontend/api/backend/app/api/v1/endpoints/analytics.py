from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.api import deps
from app.models.user import User
from app.services.conversation_logger import conversation_logger
import io

router = APIRouter()

@router.get("/conversation-logs")
async def get_conversation_logs(
    current_user: User = Depends(deps.get_current_admin),
    user_id: Optional[str] = Query(None),
    conversation_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get conversation logs (admin only).
    """
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        user_uuid = UUID(user_id) if user_id else None
        conv_uuid = UUID(conversation_id) if conversation_id else None
        
        logs = conversation_logger.get_conversation_logs(
            user_id=user_uuid,
            conversation_id=conv_uuid,
            start_date=start_dt,
            end_date=end_dt,
            limit=limit,
            offset=offset
        )
        
        return {
            "logs": logs,
            "count": len(logs),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}")

@router.get("/analytics")
async def get_analytics(
    current_user: User = Depends(deps.get_current_admin),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    Get conversation analytics (admin only).
    """
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        analytics = conversation_logger.get_analytics(
            start_date=start_dt,
            end_date=end_dt
        )
        
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate analytics: {str(e)}")

@router.get("/export/jsonl")
async def export_jsonl(
    current_user: User = Depends(deps.get_current_admin),
    user_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    Export conversation logs to JSONL format (admin only).
    """
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        user_uuid = UUID(user_id) if user_id else None
        
        jsonl_data = conversation_logger.export_to_jsonl(
            user_id=user_uuid,
            start_date=start_dt,
            end_date=end_dt
        )
        
        # Generate filename
        filename = f"conversation_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        return StreamingResponse(
            io.BytesIO(jsonl_data.encode('utf-8')),
            media_type="application/x-ndjson",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export JSONL: {str(e)}")

@router.get("/export/csv")
async def export_csv(
    current_user: User = Depends(deps.get_current_admin),
    user_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    Export conversation logs to CSV format (admin only).
    """
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        user_uuid = UUID(user_id) if user_id else None
        
        csv_data = conversation_logger.export_to_csv(
            user_id=user_uuid,
            start_date=start_dt,
            end_date=end_dt
        )
        
        # Generate filename
        filename = f"conversation_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            io.BytesIO(csv_data.encode('utf-8')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export CSV: {str(e)}")

