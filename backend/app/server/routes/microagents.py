"""
Microagents routes for OpenReplica matching OpenHands exactly
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.logging import get_logger
from app.microagent import (
    BaseMicroagent,
    KnowledgeMicroagent,
    RepoMicroagent,
    MicroagentMetadata,
    MicroagentType,
    load_microagents_from_dir,
)
from app.server.dependencies import get_dependencies
from app.server.user_auth import get_user_id
from app.storage.microagents.microagent_store import get_microagent_store

logger = get_logger(__name__)

app = APIRouter(prefix='/api/microagents', dependencies=get_dependencies())


class CreateMicroagentRequest(BaseModel):
    """Request model for creating a microagent"""
    name: str
    content: str
    metadata: Dict[str, Any]
    type: MicroagentType


class UpdateMicroagentRequest(BaseModel):
    """Request model for updating a microagent"""
    name: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MicroagentResponse(BaseModel):
    """Response model for microagent data"""
    name: str
    content: str
    metadata: Dict[str, Any]
    source: str
    type: MicroagentType
    is_custom: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@app.get('/', response_model=List[MicroagentResponse])
async def list_microagents(
    user_id: str = Depends(get_user_id),
    microagent_type: Optional[MicroagentType] = None
) -> List[MicroagentResponse]:
    """List all microagents for the user"""
    try:
        store = get_microagent_store(user_id)
        
        # Get built-in microagents
        builtin_agents = await store.get_builtin_microagents()
        
        # Get custom microagents
        custom_agents = await store.list_custom_microagents()
        
        # Combine and filter
        all_agents = []
        
        for agent in builtin_agents:
            if microagent_type is None or agent.type == microagent_type:
                all_agents.append(MicroagentResponse(
                    name=agent.name,
                    content=agent.content,
                    metadata=agent.metadata.model_dump(),
                    source=agent.source,
                    type=agent.type,
                    is_custom=False
                ))
        
        for agent in custom_agents:
            if microagent_type is None or agent.type == microagent_type:
                all_agents.append(MicroagentResponse(
                    name=agent.name,
                    content=agent.content,
                    metadata=agent.metadata.model_dump(),
                    source=agent.source,
                    type=agent.type,
                    is_custom=True,
                    created_at=getattr(agent, 'created_at', None),
                    updated_at=getattr(agent, 'updated_at', None)
                ))
        
        return all_agents
        
    except Exception as e:
        logger.error(f"Error listing microagents for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing microagents: {e}"
        )


@app.get('/{microagent_name}', response_model=MicroagentResponse)
async def get_microagent(
    microagent_name: str,
    user_id: str = Depends(get_user_id)
) -> MicroagentResponse:
    """Get a specific microagent"""
    try:
        store = get_microagent_store(user_id)
        
        # Try to find in custom agents first
        agent = await store.get_custom_microagent(microagent_name)
        is_custom = True
        
        # If not found in custom, check built-in
        if agent is None:
            builtin_agents = await store.get_builtin_microagents()
            for builtin_agent in builtin_agents:
                if builtin_agent.name == microagent_name:
                    agent = builtin_agent
                    is_custom = False
                    break
        
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Microagent '{microagent_name}' not found"
            )
        
        return MicroagentResponse(
            name=agent.name,
            content=agent.content,
            metadata=agent.metadata.model_dump(),
            source=agent.source,
            type=agent.type,
            is_custom=is_custom,
            created_at=getattr(agent, 'created_at', None),
            updated_at=getattr(agent, 'updated_at', None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting microagent {microagent_name} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting microagent: {e}"
        )


@app.post('/', response_model=MicroagentResponse)
async def create_microagent(
    request: CreateMicroagentRequest,
    user_id: str = Depends(get_user_id)
) -> MicroagentResponse:
    """Create a new custom microagent"""
    try:
        store = get_microagent_store(user_id)
        
        # Create metadata object
        metadata = MicroagentMetadata(**request.metadata)
        
        # Create the microagent
        agent = await store.create_custom_microagent(
            name=request.name,
            content=request.content,
            metadata=metadata,
            microagent_type=request.type
        )
        
        return MicroagentResponse(
            name=agent.name,
            content=agent.content,
            metadata=agent.metadata.model_dump(),
            source=agent.source,
            type=agent.type,
            is_custom=True,
            created_at=getattr(agent, 'created_at', None),
            updated_at=getattr(agent, 'updated_at', None)
        )
        
    except Exception as e:
        logger.error(f"Error creating microagent for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating microagent: {e}"
        )


@app.put('/{microagent_name}', response_model=MicroagentResponse)
async def update_microagent(
    microagent_name: str,
    request: UpdateMicroagentRequest,
    user_id: str = Depends(get_user_id)
) -> MicroagentResponse:
    """Update a custom microagent"""
    try:
        store = get_microagent_store(user_id)
        
        # Check if microagent exists and is custom
        agent = await store.get_custom_microagent(microagent_name)
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Custom microagent '{microagent_name}' not found"
            )
        
        # Update the microagent
        updated_agent = await store.update_custom_microagent(
            microagent_name,
            name=request.name,
            content=request.content,
            metadata=MicroagentMetadata(**request.metadata) if request.metadata else None
        )
        
        return MicroagentResponse(
            name=updated_agent.name,
            content=updated_agent.content,
            metadata=updated_agent.metadata.model_dump(),
            source=updated_agent.source,
            type=updated_agent.type,
            is_custom=True,
            created_at=getattr(updated_agent, 'created_at', None),
            updated_at=getattr(updated_agent, 'updated_at', None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating microagent {microagent_name} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating microagent: {e}"
        )


@app.delete('/{microagent_name}')
async def delete_microagent(
    microagent_name: str,
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Delete a custom microagent"""
    try:
        store = get_microagent_store(user_id)
        
        # Check if microagent exists and is custom
        agent = await store.get_custom_microagent(microagent_name)
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Custom microagent '{microagent_name}' not found"
            )
        
        # Delete the microagent
        await store.delete_custom_microagent(microagent_name)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"Microagent '{microagent_name}' deleted successfully"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting microagent {microagent_name} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting microagent: {e}"
        )


@app.post('/{microagent_name}/test')
async def test_microagent_triggers(
    microagent_name: str,
    request: Dict[str, str],
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Test microagent trigger matching"""
    try:
        message = request.get("message", "")
        
        store = get_microagent_store(user_id)
        
        # Get the microagent
        agent = await store.get_custom_microagent(microagent_name)
        if agent is None:
            # Try built-in agents
            builtin_agents = await store.get_builtin_microagents()
            for builtin_agent in builtin_agents:
                if builtin_agent.name == microagent_name:
                    agent = builtin_agent
                    break
        
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Microagent '{microagent_name}' not found"
            )
        
        # Test trigger matching for knowledge agents
        if isinstance(agent, KnowledgeMicroagent):
            matched_trigger = agent.match_trigger(message)
            return JSONResponse({
                "triggered": matched_trigger is not None,
                "matched_trigger": matched_trigger,
                "all_triggers": agent.triggers
            })
        else:
            # Repo agents are always active
            return JSONResponse({
                "triggered": True,
                "matched_trigger": None,
                "message": "Repo microagents are always active"
            })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing microagent {microagent_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing microagent: {e}"
        )


@app.get('/builtin/templates')
async def get_builtin_templates() -> JSONResponse:
    """Get templates for creating new microagents"""
    templates = {
        "knowledge": {
            "name": "new_knowledge_agent",
            "type": "knowledge",
            "metadata": {
                "name": "new_knowledge_agent",
                "type": "knowledge",
                "version": "1.0.0",
                "agent": "CodeActAgent",
                "triggers": ["python", "debugging", "testing"]
            },
            "content": """# Knowledge Microagent Template

This is a knowledge microagent that provides specialized expertise.

## Purpose
Describe what this microagent helps with.

## Guidelines
- Provide specific guidelines
- Include best practices
- Add common patterns

## Examples
```python
# Example code here
```

## Tips
- Add helpful tips
- Include common pitfalls to avoid
"""
        },
        "repo": {
            "name": "repo_agent",
            "type": "repo",
            "metadata": {
                "name": "repo_agent",
                "type": "repo",
                "version": "1.0.0",
                "agent": "CodeActAgent",
                "triggers": []
            },
            "content": """# Repository Microagent

This microagent contains repository-specific knowledge and guidelines.

## Project Overview
Describe the project structure and purpose.

## Development Guidelines
- Coding standards
- Testing requirements
- Deployment process

## Common Tasks
- How to set up development environment
- How to run tests
- How to deploy changes

## Resources
- Link to documentation
- Team contacts
- Important notes
"""
        }
    }
    
    return JSONResponse(templates)


@app.post('/import')
async def import_microagent_from_file(
    request: Dict[str, str],
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Import a microagent from file content"""
    try:
        file_content = request.get("content", "")
        file_name = request.get("name", "imported_agent")
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content is required"
            )
        
        store = get_microagent_store(user_id)
        
        # Parse the microagent from content
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Load the microagent
            agent = BaseMicroagent.load(tmp_file_path, file_content=file_content)
            
            # Save as custom microagent
            custom_agent = await store.create_custom_microagent(
                name=file_name,
                content=agent.content,
                metadata=agent.metadata,
                microagent_type=agent.type
            )
            
            return JSONResponse({
                "message": f"Microagent '{file_name}' imported successfully",
                "agent": {
                    "name": custom_agent.name,
                    "type": custom_agent.type.value,
                    "triggers": custom_agent.metadata.triggers
                }
            })
            
        finally:
            os.unlink(tmp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing microagent for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importing microagent: {e}"
        )


@app.post('/{microagent_name}/export')
async def export_microagent(
    microagent_name: str,
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Export a microagent as markdown with frontmatter"""
    try:
        store = get_microagent_store(user_id)
        
        # Get the microagent
        agent = await store.get_custom_microagent(microagent_name)
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Custom microagent '{microagent_name}' not found"
            )
        
        # Generate markdown with frontmatter
        import frontmatter
        
        post = frontmatter.Post(agent.content, **agent.metadata.model_dump())
        markdown_content = frontmatter.dumps(post)
        
        return JSONResponse({
            "name": agent.name,
            "content": markdown_content,
            "filename": f"{agent.name}.md"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting microagent {microagent_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting microagent: {e}"
        )
