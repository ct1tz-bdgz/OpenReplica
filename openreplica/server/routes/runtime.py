"""Runtime management routes."""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Form, File, UploadFile
from pydantic import BaseModel
from openreplica.runtime.manager import runtime_manager
from openreplica.core.logger import logger

router = APIRouter()


class CodeExecutionRequest(BaseModel):
    """Request model for code execution."""
    code: str
    language: str = "python"
    timeout: int = 300


class CodeExecutionResponse(BaseModel):
    """Response model for code execution."""
    output: str
    success: bool
    exit_code: int
    language: str
    execution_time: str = None


class FileOperationRequest(BaseModel):
    """Request model for file operations."""
    filepath: str
    content: str = None


@router.post("/{session_id}/execute", response_model=CodeExecutionResponse)
async def execute_code(
    session_id: str,
    request: CodeExecutionRequest
):
    """Execute code in the session's runtime environment."""
    try:
        result = await runtime_manager.execute_code(
            session_id=session_id,
            code=request.code,
            language=request.language,
            timeout=request.timeout
        )
        
        return CodeExecutionResponse(**result)
        
    except Exception as e:
        logger.error("Code execution failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code execution failed: {str(e)}"
        )


@router.post("/{session_id}/files", status_code=status.HTTP_201_CREATED)
async def write_file(
    session_id: str,
    request: FileOperationRequest
):
    """Write a file in the session's workspace."""
    try:
        await runtime_manager.write_file(
            session_id=session_id,
            filepath=request.filepath,
            content=request.content
        )
        
        return {"message": "File written successfully", "filepath": request.filepath}
        
    except Exception as e:
        logger.error("File write failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File write failed: {str(e)}"
        )


@router.get("/{session_id}/files/{filepath:path}")
async def read_file(
    session_id: str,
    filepath: str
):
    """Read a file from the session's workspace."""
    try:
        content = await runtime_manager.read_file(session_id, filepath)
        return {"filepath": filepath, "content": content}
        
    except Exception as e:
        logger.error("File read failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File read failed: {str(e)}"
        )


@router.get("/{session_id}/files", response_model=List[str])
async def list_files(
    session_id: str,
    directory: str = "."
):
    """List files in the session's workspace."""
    try:
        return await runtime_manager.list_files(session_id, directory)
        
    except Exception as e:
        logger.error("File listing failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File listing failed: {str(e)}"
        )


@router.post("/{session_id}/upload")
async def upload_file(
    session_id: str,
    file: UploadFile = File(...),
    filepath: str = Form(...)
):
    """Upload a file to the session's workspace."""
    try:
        content = await file.read()
        await runtime_manager.write_file(
            session_id=session_id,
            filepath=filepath,
            content=content.decode('utf-8')
        )
        
        return {
            "message": "File uploaded successfully",
            "filepath": filepath,
            "size": len(content)
        }
        
    except Exception as e:
        logger.error("File upload failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@router.get("/{session_id}/workspace")
async def get_workspace_info(session_id: str):
    """Get workspace information for a session."""
    workspace_path = runtime_manager.get_workspace_path(session_id)
    
    if not workspace_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
        
    return {
        "workspace_path": workspace_path,
        "session_id": session_id
    }
