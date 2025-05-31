"""
Conversation routes for OpenReplica matching OpenHands exactly
"""
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.events.event_filter import EventFilter
from app.events.serialization.event import event_to_dict
from app.runtime.base import Runtime
from app.server.dependencies import get_dependencies
from app.server.shared import conversation_manager

logger = get_logger(__name__)

app = APIRouter(prefix='/api/conversations/{conversation_id}', dependencies=get_dependencies())


@app.get('/config')
async def get_remote_runtime_config(request: Request) -> JSONResponse:
    """Retrieve the runtime configuration.

    Currently, this is the session ID and runtime ID (if available).
    """
    runtime = request.state.conversation.runtime
    runtime_id = runtime.runtime_id if hasattr(runtime, 'runtime_id') else None
    session_id = runtime.sid if hasattr(runtime, 'sid') else None
    return JSONResponse(
        content={
            'runtime_id': runtime_id,
            'session_id': session_id,
        }
    )


@app.get('/vscode-url')
async def get_vscode_url(request: Request) -> JSONResponse:
    """Get the VSCode URL.

    This endpoint allows getting the VSCode URL.

    Args:
        request (Request): The incoming FastAPI request object.

    Returns:
        JSONResponse: A JSON response indicating the success of the operation.
    """
    try:
        runtime: Runtime = request.state.conversation.runtime
        logger.debug(f'Runtime type: {type(runtime)}')
        logger.debug(f'Runtime VSCode URL: {runtime.vscode_url}')
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={'vscode_url': runtime.vscode_url}
        )
    except Exception as e:
        logger.error(f'Error getting VSCode URL: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                'vscode_url': None,
                'error': f'Error getting VSCode URL: {e}',
            },
        )


@app.get('/web-hosts')
async def get_hosts(request: Request) -> JSONResponse:
    """Get the hosts used by the runtime.

    This endpoint allows getting the hosts used by the runtime.

    Args:
        request (Request): The incoming FastAPI request object.

    Returns:
        JSONResponse: A JSON response indicating the success of the operation.
    """
    try:
        if not hasattr(request.state, 'conversation'):
            return JSONResponse(
                status_code=500,
                content={'error': 'No conversation found in request state'},
            )

        if not hasattr(request.state.conversation, 'runtime'):
            return JSONResponse(
                status_code=500, content={'error': 'No runtime found in conversation'}
            )

        runtime: Runtime = request.state.conversation.runtime
        logger.debug(f'Runtime type: {type(runtime)}')
        logger.debug(f'Runtime hosts: {runtime.web_hosts}')
        return JSONResponse(status_code=200, content={'hosts': runtime.web_hosts})
    except Exception as e:
        logger.error(f'Error getting runtime hosts: {e}')
        return JSONResponse(
            status_code=500,
            content={
                'hosts': None,
                'error': f'Error getting runtime hosts: {e}',
            },
        )


@app.get('/events')
async def search_events(
    request: Request,
    start_id: int = 0,
    end_id: int | None = None,
    reverse: bool = False,
    filter: EventFilter | None = None,
    limit: int = 20,
):
    """Search through the event stream with filtering and pagination.
    Args:
        request: The incoming request object
        start_id: Starting ID in the event stream. Defaults to 0
        end_id: Ending ID in the event stream
        reverse: Whether to retrieve events in reverse order. Defaults to False.
        filter: Filter for events
        limit: Maximum number of events to return. Must be between 1 and 100. Defaults to 20
    Returns:
        dict: Dictionary containing:
            - events: List of matching events
            - has_more: Whether there are more matching events after this batch
    Raises:
        HTTPException: If conversation is not found
        ValueError: If limit is less than 1 or greater than 100
    """
    if not request.state.conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='ServerConversation not found'
        )
    if limit < 0 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid limit'
        )

    # Get matching events from the stream
    event_stream = request.state.conversation.event_stream
    events = list(
        event_stream.search_events(
            start_id=start_id,
            end_id=end_id,
            reverse=reverse,
            filter=filter,
            limit=limit + 1,
        )
    )

    # Check if there are more events
    has_more = len(events) > limit
    if has_more:
        events = events[:limit]  # Remove the extra event

    events = [event_to_dict(event) for event in events]
    return {
        'events': events,
        'has_more': has_more,
    }


@app.post('/events')
async def add_event(request: Request):
    """Add an event to the conversation stream"""
    data = await request.json()
    conversation_manager.send_to_event_stream(request.state.sid, data)
    return JSONResponse({'success': True})


@app.get('/runtime-logs')
async def get_runtime_logs(
    request: Request,
    lines: int = 100,
    since_id: int | None = None
) -> JSONResponse:
    """Get runtime logs for debugging.

    Args:
        request: The incoming request object
        lines: Number of log lines to return
        since_id: Return logs since this ID

    Returns:
        JSONResponse: Runtime logs and metadata
    """
    try:
        runtime: Runtime = request.state.conversation.runtime
        
        if not runtime:
            return JSONResponse(
                status_code=404,
                content={'error': 'Runtime not found'}
            )
        
        # Get logs from runtime
        logs = []
        if hasattr(runtime, 'get_logs'):
            logs = await runtime.get_logs(lines=lines, since_id=since_id)
        
        return JSONResponse({
            'logs': logs,
            'runtime_id': getattr(runtime, 'runtime_id', None),
            'session_id': getattr(runtime, 'sid', None),
            'total_lines': len(logs)
        })
        
    except Exception as e:
        logger.error(f'Error getting runtime logs: {e}')
        return JSONResponse(
            status_code=500,
            content={'error': f'Error getting runtime logs: {e}'}
        )


@app.get('/agent-state')
async def get_agent_state(request: Request) -> JSONResponse:
    """Get current agent state and metadata.

    Returns:
        JSONResponse: Agent state information
    """
    try:
        conversation = request.state.conversation
        
        if not conversation:
            return JSONResponse(
                status_code=404,
                content={'error': 'Conversation not found'}
            )
        
        # Get agent state
        agent_state = {
            'agent_cls': getattr(conversation, 'agent_cls', None),
            'state': getattr(conversation, 'state', None),
            'iteration': getattr(conversation, 'iteration', 0),
            'max_iterations': getattr(conversation, 'max_iterations', 100),
            'is_running': getattr(conversation, 'is_running', False),
            'agent_task': getattr(conversation, 'agent_task', None),
        }
        
        # Get LLM info if available
        llm_info = {}
        if hasattr(conversation, 'llm'):
            llm = conversation.llm
            llm_info = {
                'model': getattr(llm, 'model', None),
                'provider': getattr(llm, 'provider', None),
                'total_cost': getattr(llm, 'total_cost', 0),
                'total_tokens': getattr(llm, 'total_tokens', 0),
            }
        
        # Get runtime info
        runtime_info = {}
        if hasattr(conversation, 'runtime'):
            runtime = conversation.runtime
            runtime_info = {
                'runtime_id': getattr(runtime, 'runtime_id', None),
                'status': getattr(runtime, 'status', 'unknown'),
                'container_image': getattr(runtime, 'container_image', None),
            }
        
        return JSONResponse({
            'agent': agent_state,
            'llm': llm_info,
            'runtime': runtime_info,
            'conversation_id': getattr(conversation, 'conversation_id', None),
        })
        
    except Exception as e:
        logger.error(f'Error getting agent state: {e}')
        return JSONResponse(
            status_code=500,
            content={'error': f'Error getting agent state: {e}'}
        )


@app.get('/model-metadata')
async def get_model_metadata(request: Request) -> JSONResponse:
    """Get detailed model metadata and usage statistics.

    Returns:
        JSONResponse: Model metadata and statistics
    """
    try:
        conversation = request.state.conversation
        
        if not conversation:
            return JSONResponse(
                status_code=404,
                content={'error': 'Conversation not found'}
            )
        
        metadata = {
            'model_info': {},
            'usage_stats': {},
            'tools_used': [],
            'session_stats': {}
        }
        
        # Get LLM metadata
        if hasattr(conversation, 'llm'):
            llm = conversation.llm
            metadata['model_info'] = {
                'model_name': getattr(llm, 'model', None),
                'provider': getattr(llm, 'provider', None),
                'model_version': getattr(llm, 'model_version', None),
                'supports_function_calling': getattr(llm, 'supports_function_calling', False),
                'supports_vision': getattr(llm, 'supports_vision', False),
                'max_tokens': getattr(llm, 'max_tokens', None),
                'context_length': getattr(llm, 'context_length', None),
            }
            
            metadata['usage_stats'] = {
                'total_tokens': getattr(llm, 'total_tokens', 0),
                'prompt_tokens': getattr(llm, 'prompt_tokens', 0),
                'completion_tokens': getattr(llm, 'completion_tokens', 0),
                'total_cost': getattr(llm, 'total_cost', 0.0),
                'request_count': getattr(llm, 'request_count', 0),
                'average_response_time': getattr(llm, 'average_response_time', 0.0),
            }
        
        # Get tools used in this conversation
        if hasattr(conversation, 'agent') and hasattr(conversation.agent, 'tools'):
            tools = conversation.agent.tools
            metadata['tools_used'] = [
                {
                    'name': tool.get('function', {}).get('name', 'unknown'),
                    'description': tool.get('function', {}).get('description', ''),
                    'usage_count': 0  # Would track actual usage
                }
                for tool in tools
            ]
        
        # Session statistics
        metadata['session_stats'] = {
            'start_time': getattr(conversation, 'start_time', None),
            'duration': getattr(conversation, 'duration', 0),
            'iterations': getattr(conversation, 'iteration', 0),
            'files_modified': getattr(conversation, 'files_modified', 0),
            'commands_executed': getattr(conversation, 'commands_executed', 0),
        }
        
        return JSONResponse(metadata)
        
    except Exception as e:
        logger.error(f'Error getting model metadata: {e}')
        return JSONResponse(
            status_code=500,
            content={'error': f'Error getting model metadata: {e}'}
        )


@app.post('/stop')
async def stop_conversation(request: Request) -> JSONResponse:
    """Stop the current conversation/agent execution.

    Returns:
        JSONResponse: Success status
    """
    try:
        conversation = request.state.conversation
        
        if not conversation:
            return JSONResponse(
                status_code=404,
                content={'error': 'Conversation not found'}
            )
        
        # Stop the conversation
        if hasattr(conversation, 'stop'):
            await conversation.stop()
        
        return JSONResponse({
            'success': True,
            'message': 'Conversation stopped successfully'
        })
        
    except Exception as e:
        logger.error(f'Error stopping conversation: {e}')
        return JSONResponse(
            status_code=500,
            content={'error': f'Error stopping conversation: {e}'}
        )


@app.post('/pause')
async def pause_conversation(request: Request) -> JSONResponse:
    """Pause the current conversation/agent execution.

    Returns:
        JSONResponse: Success status
    """
    try:
        conversation = request.state.conversation
        
        if not conversation:
            return JSONResponse(
                status_code=404,
                content={'error': 'Conversation not found'}
            )
        
        # Pause the conversation
        if hasattr(conversation, 'pause'):
            await conversation.pause()
        
        return JSONResponse({
            'success': True,
            'message': 'Conversation paused successfully'
        })
        
    except Exception as e:
        logger.error(f'Error pausing conversation: {e}')
        return JSONResponse(
            status_code=500,
            content={'error': f'Error pausing conversation: {e}'}
        )


@app.post('/resume')
async def resume_conversation(request: Request) -> JSONResponse:
    """Resume the current conversation/agent execution.

    Returns:
        JSONResponse: Success status
    """
    try:
        conversation = request.state.conversation
        
        if not conversation:
            return JSONResponse(
                status_code=404,
                content={'error': 'Conversation not found'}
            )
        
        # Resume the conversation
        if hasattr(conversation, 'resume'):
            await conversation.resume()
        
        return JSONResponse({
            'success': True,
            'message': 'Conversation resumed successfully'
        })
        
    except Exception as e:
        logger.error(f'Error resuming conversation: {e}')
        return JSONResponse(
            status_code=500,
            content={'error': f'Error resuming conversation: {e}'}
        )
