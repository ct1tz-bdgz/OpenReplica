"""
Feedback routes for OpenReplica matching OpenHands exactly
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.core.logging import get_logger
from app.server.dependencies import get_dependencies
from app.server.user_auth import get_user_id

logger = get_logger(__name__)

app = APIRouter(prefix='/api/feedback', dependencies=get_dependencies())


class FeedbackRequest(BaseModel):
    """Request model for user feedback"""
    type: str  # "bug", "feature", "general", "rating"
    message: str
    email: Optional[str] = None
    user_agent: Optional[str] = None
    url: Optional[str] = None
    conversation_id: Optional[str] = None
    rating: Optional[int] = None  # 1-5 stars
    metadata: Optional[Dict[str, Any]] = None


@app.post('/submit')
async def submit_feedback(
    feedback: FeedbackRequest,
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Submit user feedback"""
    try:
        # In a real implementation, this would save to a database or send to a service
        logger.info(
            f"Feedback submitted by user {user_id}",
            extra={
                "user_id": user_id,
                "feedback_type": feedback.type,
                "rating": feedback.rating,
                "conversation_id": feedback.conversation_id
            }
        )
        
        # For now, just log the feedback
        logger.info(f"Feedback content: {feedback.message}")
        
        return JSONResponse({
            "success": True,
            "message": "Thank you for your feedback! We appreciate your input."
        })
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to submit feedback"}
        )


@app.get('/stats')
async def get_feedback_stats(
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Get feedback statistics (admin only)"""
    try:
        # Mock statistics - in real implementation, query database
        stats = {
            "total_feedback": 0,
            "by_type": {
                "bug": 0,
                "feature": 0,
                "general": 0,
                "rating": 0
            },
            "average_rating": 0.0,
            "recent_feedback": []
        }
        
        return JSONResponse(stats)
        
    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to get feedback statistics"}
        )
