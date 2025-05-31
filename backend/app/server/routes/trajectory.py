"""
Trajectory routes for OpenReplica matching OpenHands exactly
"""
import json
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from app.core.logging import get_logger
from app.server.dependencies import get_dependencies
from app.server.user_auth import get_user_id
from app.storage.conversation.conversation_store import get_conversation_store

logger = get_logger(__name__)

app = APIRouter(prefix='/api/trajectories', dependencies=get_dependencies())


class TrajectoryMetadata(BaseModel):
    """Trajectory metadata model"""
    trajectory_id: str
    conversation_id: str
    agent_class: str
    llm_model: str
    start_time: str
    end_time: Optional[str] = None
    total_iterations: int
    final_state: Optional[str] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None


class TrajectoryEvent(BaseModel):
    """Trajectory event model"""
    event_id: str
    timestamp: str
    event_type: str
    content: Dict[str, Any]
    agent_state: Optional[Dict[str, Any]] = None


class TrajectoryExportRequest(BaseModel):
    """Request model for trajectory export"""
    format: str = "json"  # "json", "csv", "markdown"
    include_events: bool = True
    include_metadata: bool = True


@app.get('/')
async def list_trajectories(
    user_id: str = Depends(get_user_id),
    conversation_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> JSONResponse:
    """List trajectories for the user"""
    try:
        # Mock trajectories - in real implementation, query trajectory storage
        trajectories = [
            TrajectoryMetadata(
                trajectory_id="traj_001",
                conversation_id="conv_001",
                agent_class="CodeActAgent",
                llm_model="claude-3-5-sonnet-20241022",
                start_time="2024-01-01T12:00:00Z",
                end_time="2024-01-01T12:30:00Z",
                total_iterations=15,
                final_state="completed",
                success=True
            ),
            TrajectoryMetadata(
                trajectory_id="traj_002",
                conversation_id="conv_002",
                agent_class="CodeActAgent",
                llm_model="gpt-4",
                start_time="2024-01-01T13:00:00Z",
                end_time="2024-01-01T13:45:00Z",
                total_iterations=23,
                final_state="error",
                success=False,
                error_message="Runtime timeout"
            )
        ]
        
        # Filter by conversation_id if provided
        if conversation_id:
            trajectories = [t for t in trajectories if t.conversation_id == conversation_id]
        
        # Apply pagination
        total = len(trajectories)
        trajectories = trajectories[offset:offset + limit]
        
        return JSONResponse({
            "trajectories": [t.model_dump() for t in trajectories],
            "total": total,
            "limit": limit,
            "offset": offset
        })
        
    except Exception as e:
        logger.error(f"Error listing trajectories for user {user_id}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to list trajectories: {e}"}
        )


@app.get('/{trajectory_id}')
async def get_trajectory(
    trajectory_id: str,
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Get detailed trajectory information"""
    try:
        # Mock trajectory details - in real implementation, load from storage
        trajectory = {
            "metadata": TrajectoryMetadata(
                trajectory_id=trajectory_id,
                conversation_id="conv_001",
                agent_class="CodeActAgent",
                llm_model="claude-3-5-sonnet-20241022",
                start_time="2024-01-01T12:00:00Z",
                end_time="2024-01-01T12:30:00Z",
                total_iterations=15,
                final_state="completed",
                success=True
            ).model_dump(),
            "events": [
                TrajectoryEvent(
                    event_id="evt_001",
                    timestamp="2024-01-01T12:00:00Z",
                    event_type="user_message",
                    content={"message": "Create a Python script to analyze data"},
                    agent_state={"iteration": 0, "mode": "planning"}
                ).model_dump(),
                TrajectoryEvent(
                    event_id="evt_002",
                    timestamp="2024-01-01T12:01:00Z",
                    event_type="agent_action",
                    content={"action": "create_file", "path": "analyze.py"},
                    agent_state={"iteration": 1, "mode": "coding"}
                ).model_dump()
            ],
            "statistics": {
                "total_tokens": 2500,
                "total_cost": 0.05,
                "avg_response_time": 1.2,
                "actions_taken": 8,
                "files_modified": 3
            }
        }
        
        return JSONResponse(trajectory)
        
    except Exception as e:
        logger.error(f"Error getting trajectory {trajectory_id}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get trajectory: {e}"}
        )


@app.post('/{trajectory_id}/export')
async def export_trajectory(
    trajectory_id: str,
    export_request: TrajectoryExportRequest,
    user_id: str = Depends(get_user_id)
) -> FileResponse:
    """Export trajectory in specified format"""
    try:
        # Get trajectory data
        # In real implementation, load from storage
        trajectory_data = {
            "trajectory_id": trajectory_id,
            "conversation_id": "conv_001",
            "agent_class": "CodeActAgent",
            "events": [],
            "metadata": {}
        }
        
        # Create export file based on format
        if export_request.format == "json":
            filename = f"trajectory_{trajectory_id}.json"
            content = json.dumps(trajectory_data, indent=2)
            media_type = "application/json"
        elif export_request.format == "csv":
            filename = f"trajectory_{trajectory_id}.csv"
            # Mock CSV content
            content = "event_id,timestamp,event_type,content\n"
            media_type = "text/csv"
        elif export_request.format == "markdown":
            filename = f"trajectory_{trajectory_id}.md"
            # Mock Markdown content
            content = f"# Trajectory {trajectory_id}\n\n## Events\n\n"
            media_type = "text/markdown"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {export_request.format}"
            )
        
        # Write to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f".{export_request.format}") as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        return FileResponse(
            path=tmp_file_path,
            filename=filename,
            media_type=media_type,
            background=lambda: os.unlink(tmp_file_path)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting trajectory {trajectory_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export trajectory: {e}"
        )


@app.get('/{trajectory_id}/events')
async def get_trajectory_events(
    trajectory_id: str,
    user_id: str = Depends(get_user_id),
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> JSONResponse:
    """Get events for a trajectory"""
    try:
        # Mock events - in real implementation, load from storage
        events = [
            TrajectoryEvent(
                event_id="evt_001",
                timestamp="2024-01-01T12:00:00Z",
                event_type="user_message",
                content={"message": "Create a Python script"},
                agent_state={"iteration": 0}
            ),
            TrajectoryEvent(
                event_id="evt_002", 
                timestamp="2024-01-01T12:01:00Z",
                event_type="agent_action",
                content={"action": "create_file"},
                agent_state={"iteration": 1}
            )
        ]
        
        # Filter by event type if provided
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Apply pagination
        total = len(events)
        events = events[offset:offset + limit]
        
        return JSONResponse({
            "events": [e.model_dump() for e in events],
            "total": total,
            "limit": limit,
            "offset": offset,
            "trajectory_id": trajectory_id
        })
        
    except Exception as e:
        logger.error(f"Error getting trajectory events: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get trajectory events: {e}"}
        )


@app.get('/{trajectory_id}/statistics')
async def get_trajectory_statistics(
    trajectory_id: str,
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Get detailed statistics for a trajectory"""
    try:
        # Mock statistics - in real implementation, calculate from events
        statistics = {
            "trajectory_id": trajectory_id,
            "basic_stats": {
                "total_events": 15,
                "duration_seconds": 1800,
                "total_iterations": 12,
                "success_rate": 0.85
            },
            "llm_usage": {
                "total_tokens": 2500,
                "prompt_tokens": 1800,
                "completion_tokens": 700,
                "total_cost": 0.05,
                "requests_count": 12,
                "avg_response_time": 1.2
            },
            "agent_actions": {
                "total_actions": 25,
                "action_types": {
                    "create_file": 3,
                    "edit_file": 8,
                    "run_command": 10,
                    "browse_web": 2,
                    "think": 2
                },
                "success_rate_by_action": {
                    "create_file": 1.0,
                    "edit_file": 0.9,
                    "run_command": 0.8
                }
            },
            "file_operations": {
                "files_created": 3,
                "files_modified": 8,
                "files_deleted": 1,
                "total_lines_added": 120,
                "total_lines_removed": 45
            },
            "errors": {
                "total_errors": 2,
                "error_types": {
                    "syntax_error": 1,
                    "runtime_error": 1
                },
                "recovery_attempts": 3,
                "recovery_success_rate": 0.67
            }
        }
        
        return JSONResponse(statistics)
        
    except Exception as e:
        logger.error(f"Error getting trajectory statistics: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get trajectory statistics: {e}"}
        )


@app.delete('/{trajectory_id}')
async def delete_trajectory(
    trajectory_id: str,
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Delete a trajectory"""
    try:
        # Mock deletion - in real implementation, delete from storage
        logger.info(f"Deleting trajectory {trajectory_id} for user {user_id}")
        
        return JSONResponse({
            "success": True,
            "message": f"Trajectory {trajectory_id} deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deleting trajectory: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to delete trajectory: {e}"}
        )


@app.post('/{trajectory_id}/replay')
async def replay_trajectory(
    trajectory_id: str,
    user_id: str = Depends(get_user_id),
    from_event: Optional[str] = None,
    to_event: Optional[str] = None
) -> JSONResponse:
    """Replay a trajectory or part of it"""
    try:
        # Mock replay - in real implementation, recreate agent execution
        logger.info(f"Replaying trajectory {trajectory_id} for user {user_id}")
        
        replay_info = {
            "trajectory_id": trajectory_id,
            "replay_started": True,
            "from_event": from_event,
            "to_event": to_event,
            "new_conversation_id": "conv_replay_001",
            "message": "Trajectory replay started successfully"
        }
        
        return JSONResponse(replay_info)
        
    except Exception as e:
        logger.error(f"Error replaying trajectory: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to replay trajectory: {e}"}
        )
