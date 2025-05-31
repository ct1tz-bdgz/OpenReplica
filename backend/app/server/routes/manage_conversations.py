"""
Manage conversations routes for OpenReplica matching OpenHands exactly
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.server.dependencies import get_dependencies
from app.server.shared import ConversationStoreImpl, config
from app.server.user_auth import get_user_id
from app.storage.conversation.conversation_store import ConversationStore

logger = get_logger(__name__)

app = APIRouter(prefix='/api', dependencies=get_dependencies())


@app.get('/conversations')
async def list_conversations(
    user_id: str = Depends(get_user_id),
) -> list[dict[str, Any]]:
    """List all conversations for the user.

    Args:
        user_id: The user ID.

    Returns:
        List of conversation metadata.
    """
    try:
        conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
        conversations = await conversation_store.list_conversations()
        
        # Convert to list of dictionaries
        conversation_list = []
        for conv in conversations:
            conv_dict = {
                'conversation_id': conv.conversation_id,
                'title': conv.title or 'Untitled Conversation',
                'created_at': conv.created_at.isoformat() if conv.created_at else None,
                'updated_at': conv.updated_at.isoformat() if conv.updated_at else None,
                'agent_class': conv.agent_class,
                'llm_model': conv.llm_model,
                'status': conv.status or 'active',
                'last_message': conv.last_message,
                'message_count': conv.message_count or 0,
                'selected_repository': conv.selected_repository,
            }
            conversation_list.append(conv_dict)
        
        return conversation_list
        
    except Exception as e:
        logger.error(f'Error listing conversations for user {user_id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Error listing conversations: {e}'
        )


@app.post('/conversations')
async def create_conversation(
    request: Request,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Create a new conversation.

    Args:
        request: The request containing conversation data.
        user_id: The user ID.

    Returns:
        JSONResponse with the new conversation ID.
    """
    try:
        data = await request.json()
        
        conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
        
        # Create new conversation
        conversation_id = await conversation_store.create_conversation(
            title=data.get('title', 'New Conversation'),
            agent_class=data.get('agent_class', 'CodeActAgent'),
            llm_model=data.get('llm_model', 'claude-3-5-sonnet-20241022'),
            selected_repository=data.get('selected_repository'),
            initial_message=data.get('initial_message'),
        )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                'conversation_id': conversation_id,
                'message': 'Conversation created successfully'
            }
        )
        
    except Exception as e:
        logger.error(f'Error creating conversation for user {user_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error creating conversation: {e}'}
        )


@app.get('/conversations/{conversation_id}')
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_user_id),
) -> dict[str, Any]:
    """Get conversation metadata.

    Args:
        conversation_id: The conversation ID.
        user_id: The user ID.

    Returns:
        Conversation metadata.
    """
    try:
        conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
        metadata = await conversation_store.get_metadata(conversation_id)
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Conversation not found'
            )
        
        return {
            'conversation_id': metadata.conversation_id,
            'title': metadata.title or 'Untitled Conversation',
            'created_at': metadata.created_at.isoformat() if metadata.created_at else None,
            'updated_at': metadata.updated_at.isoformat() if metadata.updated_at else None,
            'agent_class': metadata.agent_class,
            'llm_model': metadata.llm_model,
            'status': metadata.status or 'active',
            'last_message': metadata.last_message,
            'message_count': metadata.message_count or 0,
            'selected_repository': metadata.selected_repository,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Error getting conversation {conversation_id} for user {user_id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Error getting conversation: {e}'
        )


@app.put('/conversations/{conversation_id}')
async def update_conversation(
    conversation_id: str,
    request: Request,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Update conversation metadata.

    Args:
        conversation_id: The conversation ID.
        request: The request containing updated data.
        user_id: The user ID.

    Returns:
        JSONResponse with success status.
    """
    try:
        data = await request.json()
        
        conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
        
        # Update conversation metadata
        await conversation_store.update_metadata(
            conversation_id=conversation_id,
            title=data.get('title'),
            status=data.get('status'),
            selected_repository=data.get('selected_repository'),
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': 'Conversation updated successfully'}
        )
        
    except Exception as e:
        logger.error(f'Error updating conversation {conversation_id} for user {user_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error updating conversation: {e}'}
        )


@app.delete('/conversations/{conversation_id}')
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Delete a conversation.

    Args:
        conversation_id: The conversation ID.
        user_id: The user ID.

    Returns:
        JSONResponse with success status.
    """
    try:
        conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
        
        # Delete the conversation
        await conversation_store.delete_conversation(conversation_id)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': 'Conversation deleted successfully'}
        )
        
    except Exception as e:
        logger.error(f'Error deleting conversation {conversation_id} for user {user_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error deleting conversation: {e}'}
        )


@app.post('/conversations/{conversation_id}/clone')
async def clone_conversation(
    conversation_id: str,
    request: Request,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Clone a conversation.

    Args:
        conversation_id: The conversation ID to clone.
        request: The request containing clone options.
        user_id: The user ID.

    Returns:
        JSONResponse with the new conversation ID.
    """
    try:
        data = await request.json()
        
        conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
        
        # Get original conversation
        original_metadata = await conversation_store.get_metadata(conversation_id)
        if not original_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Original conversation not found'
            )
        
        # Create cloned conversation
        new_conversation_id = await conversation_store.create_conversation(
            title=data.get('title', f"Copy of {original_metadata.title}"),
            agent_class=original_metadata.agent_class,
            llm_model=original_metadata.llm_model,
            selected_repository=original_metadata.selected_repository,
        )
        
        # Optionally copy events if requested
        if data.get('copy_events', False):
            events = await conversation_store.get_events(conversation_id)
            for event in events:
                await conversation_store.add_event(new_conversation_id, event)
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                'conversation_id': new_conversation_id,
                'message': 'Conversation cloned successfully'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Error cloning conversation {conversation_id} for user {user_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error cloning conversation: {e}'}
        )


@app.get('/conversations/{conversation_id}/events')
async def get_conversation_events(
    conversation_id: str,
    user_id: str = Depends(get_user_id),
    start_id: int = 0,
    limit: int = 100,
    event_type: str | None = None,
) -> JSONResponse:
    """Get events for a conversation.

    Args:
        conversation_id: The conversation ID.
        user_id: The user ID.
        start_id: Starting event ID.
        limit: Maximum number of events to return.
        event_type: Filter by event type.

    Returns:
        JSONResponse with events list.
    """
    try:
        conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
        
        events = await conversation_store.get_events(
            conversation_id=conversation_id,
            start_id=start_id,
            limit=limit,
            event_type=event_type,
        )
        
        # Convert events to dictionaries
        events_list = []
        for event in events:
            event_dict = {
                'id': event.id,
                'timestamp': event.timestamp.isoformat() if event.timestamp else None,
                'source': event.source,
                'message': event.message,
                'extras': event.extras,
                'action': getattr(event, 'action', None),
                'observation': getattr(event, 'observation', None),
            }
            events_list.append(event_dict)
        
        return JSONResponse({
            'events': events_list,
            'total_events': len(events_list),
            'conversation_id': conversation_id,
        })
        
    except Exception as e:
        logger.error(f'Error getting events for conversation {conversation_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error getting conversation events: {e}'}
        )


@app.post('/conversations/{conversation_id}/archive')
async def archive_conversation(
    conversation_id: str,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Archive a conversation.

    Args:
        conversation_id: The conversation ID.
        user_id: The user ID.

    Returns:
        JSONResponse with success status.
    """
    try:
        conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
        
        # Update conversation status to archived
        await conversation_store.update_metadata(
            conversation_id=conversation_id,
            status='archived'
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': 'Conversation archived successfully'}
        )
        
    except Exception as e:
        logger.error(f'Error archiving conversation {conversation_id} for user {user_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error archiving conversation: {e}'}
        )


@app.post('/conversations/{conversation_id}/unarchive')
async def unarchive_conversation(
    conversation_id: str,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Unarchive a conversation.

    Args:
        conversation_id: The conversation ID.
        user_id: The user ID.

    Returns:
        JSONResponse with success status.
    """
    try:
        conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
        
        # Update conversation status to active
        await conversation_store.update_metadata(
            conversation_id=conversation_id,
            status='active'
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': 'Conversation unarchived successfully'}
        )
        
    except Exception as e:
        logger.error(f'Error unarchiving conversation {conversation_id} for user {user_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error unarchiving conversation: {e}'}
        )
