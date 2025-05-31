"""
Files routes for OpenReplica matching OpenHands exactly
"""
import os
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import FileResponse, JSONResponse
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from starlette.background import BackgroundTask

from app.core.exceptions import AgentRuntimeUnavailableError
from app.core.logging import get_logger
from app.events.action import FileReadAction
from app.events.observation import ErrorObservation, FileReadObservation
from app.runtime.base import Runtime
from app.server.dependencies import get_dependencies
from app.server.file_config import FILES_TO_IGNORE
from app.server.shared import ConversationStoreImpl, config
from app.server.user_auth import get_user_id
from app.server.utils import get_conversation_store
from app.storage.conversation.conversation_store import ConversationStore
from app.utils.async_utils import call_sync_from_async

logger = get_logger(__name__)

app = APIRouter(prefix='/api/conversations/{conversation_id}', dependencies=get_dependencies())


@app.get(
    '/list-files',
    response_model=list[str],
    responses={
        404: {'description': 'Runtime not initialized', 'model': dict},
        500: {'description': 'Error listing or filtering files', 'model': dict},
    },
)
async def list_files(
    request: Request, path: str | None = None
) -> list[str] | JSONResponse:
    """List files in the specified path.

    This function retrieves a list of files from the agent's runtime file store,
    excluding certain system and hidden files/directories.

    To list files:
    ```sh
    curl http://localhost:3000/api/conversations/{conversation_id}/list-files
    ```

    Args:
        request (Request): The incoming request object.
        path (str, optional): The path to list files from. Defaults to None.

    Returns:
        list: A list of file names in the specified path.

    Raises:
        HTTPException: If there's an error listing the files.
    """
    if not request.state.conversation.runtime:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={'error': 'Runtime not yet initialized'},
        )

    runtime: Runtime = request.state.conversation.runtime
    try:
        file_list = await call_sync_from_async(runtime.list_files, path)
    except AgentRuntimeUnavailableError as e:
        logger.error(f'Error listing files: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error listing files: {e}'},
        )
    if path:
        file_list = [os.path.join(path, f) for f in file_list]

    file_list = [f for f in file_list if f not in FILES_TO_IGNORE]

    async def filter_for_gitignore(file_list: list[str], base_path: str) -> list[str]:
        gitignore_path = os.path.join(base_path, '.gitignore')
        try:
            read_action = FileReadAction(gitignore_path)
            observation = await call_sync_from_async(runtime.run_action, read_action)
            if isinstance(observation, FileReadObservation):
                spec = PathSpec.from_lines(
                    GitWildMatchPattern, observation.content.splitlines()
                )
                return [f for f in file_list if not spec.match_file(f)]
        except Exception:
            pass
        return file_list

    try:
        file_list = await filter_for_gitignore(
            file_list, runtime.config.workspace_mount_path_in_sandbox
        )
    except Exception as e:
        logger.error(f'Error filtering files with gitignore: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error filtering files: {e}'},
        )

    return file_list


@app.get(
    '/read-file',
    response_model=str,
    responses={
        404: {'description': 'File not found or runtime not initialized', 'model': dict},
        500: {'description': 'Error reading file', 'model': dict},
    },
)
async def read_file(request: Request, path: str) -> str | JSONResponse:
    """Read the content of a file.

    Args:
        request (Request): The incoming request object.
        path (str): The path to the file to read.

    Returns:
        str: The content of the file.

    Raises:
        HTTPException: If there's an error reading the file.
    """
    if not request.state.conversation.runtime:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={'error': 'Runtime not yet initialized'},
        )

    runtime: Runtime = request.state.conversation.runtime
    try:
        read_action = FileReadAction(path)
        observation = await call_sync_from_async(runtime.run_action, read_action)
        
        if isinstance(observation, ErrorObservation):
            if 'File not found' in observation.content:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={'error': f'File not found: {path}'},
                )
            else:
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={'error': observation.content},
                )
        elif isinstance(observation, FileReadObservation):
            return observation.content
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={'error': 'Unexpected observation type'},
            )
    except AgentRuntimeUnavailableError as e:
        logger.error(f'Runtime unavailable when reading file: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Runtime unavailable: {e}'},
        )
    except Exception as e:
        logger.error(f'Error reading file {path}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error reading file: {e}'},
        )


@app.get(
    '/download-file',
    response_class=FileResponse,
    responses={
        404: {'description': 'File not found or runtime not initialized', 'model': dict},
        500: {'description': 'Error downloading file', 'model': dict},
    },
)
async def download_file(request: Request, path: str) -> FileResponse | JSONResponse:
    """Download a file from the runtime.

    Args:
        request (Request): The incoming request object.
        path (str): The path to the file to download.

    Returns:
        FileResponse: The file to download.

    Raises:
        HTTPException: If there's an error downloading the file.
    """
    if not request.state.conversation.runtime:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={'error': 'Runtime not yet initialized'},
        )

    runtime: Runtime = request.state.conversation.runtime
    try:
        # Get file from runtime
        local_path = await call_sync_from_async(runtime.copy_from, path)
        
        if not os.path.exists(local_path):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={'error': f'File not found: {path}'},
            )

        filename = os.path.basename(path)
        return FileResponse(
            path=local_path,
            filename=filename,
            background=BackgroundTask(lambda: os.unlink(local_path)),
        )
    except AgentRuntimeUnavailableError as e:
        logger.error(f'Runtime unavailable when downloading file: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Runtime unavailable: {e}'},
        )
    except Exception as e:
        logger.error(f'Error downloading file {path}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error downloading file: {e}'},
        )


@app.get(
    '/download-workspace',
    response_class=FileResponse,
    responses={
        500: {'description': 'Error zipping workspace', 'model': dict},
    },
)
async def download_workspace(request: Request) -> FileResponse | JSONResponse:
    """Download the entire workspace as a zip file.

    Args:
        request (Request): The incoming request object.

    Returns:
        FileResponse: The workspace zip file.

    Raises:
        HTTPException: If there's an error creating the zip file.
    """
    try:
        runtime: Runtime = request.state.conversation.runtime
        path = runtime.config.workspace_mount_path_in_sandbox
        try:
            zip_file_path = await call_sync_from_async(runtime.copy_from, path)
        except AgentRuntimeUnavailableError as e:
            logger.error(f'Error zipping workspace: {e}')
            return JSONResponse(
                status_code=500,
                content={'error': f'Error zipping workspace: {e}'},
            )
        return FileResponse(
            path=zip_file_path,
            filename='workspace.zip',
            media_type='application/zip',
            background=BackgroundTask(lambda: os.unlink(zip_file_path)),
        )
    except Exception as e:
        logger.error(f'Error zipping workspace: {e}')
        raise HTTPException(
            status_code=500,
            detail='Failed to zip workspace',
        )


@app.get(
    '/conversation-history',
    response_model=dict,
    responses={
        500: {'description': 'Error exporting conversation', 'model': dict},
    },
)
async def download_conversation_history(
    request: Request,
    conversation_id: str,
    user_id: str = Depends(get_user_id),
) -> dict[str, Any] | JSONResponse:
    """Download conversation history as JSON.

    Args:
        request (Request): The incoming request object.
        conversation_id (str): The conversation ID.
        user_id (str): The user ID.

    Returns:
        dict: The conversation history.
    """
    try:
        conversation_store = await ConversationStoreImpl.get_instance(
            config, user_id
        )
        
        # Get conversation metadata
        metadata = await conversation_store.get_metadata(conversation_id)
        if not metadata:
            return JSONResponse(
                status_code=404,
                content={'error': 'Conversation not found'},
            )
        
        # Get conversation events
        events = await conversation_store.get_events(conversation_id)
        
        # Export conversation data
        conversation_data = {
            'conversation_id': conversation_id,
            'metadata': metadata.dict() if metadata else {},
            'events': [event.dict() for event in events],
            'export_timestamp': str(int(time.time())),
            'total_events': len(events)
        }
        
        return conversation_data
        
    except Exception as e:
        logger.error(f'Error exporting conversation {conversation_id}: {e}')
        return JSONResponse(
            status_code=500,
            content={'error': f'Error exporting conversation: {e}'},
        )


@app.get(
    '/git/changes',
    response_model=list[dict[str, str]],
    responses={
        404: {'description': 'Not a git repository', 'model': dict},
        500: {'description': 'Error getting changes', 'model': dict},
    },
)
async def git_changes(
    request: Request,
    conversation_id: str,
    user_id: str = Depends(get_user_id),
) -> list[dict[str, str]] | JSONResponse:
    runtime: Runtime = request.state.conversation.runtime
    conversation_store = await ConversationStoreImpl.get_instance(
        config,
        user_id,
    )

    cwd = await get_cwd(
        conversation_store,
        conversation_id,
        runtime.config.workspace_mount_path_in_sandbox,
    )
    logger.info(f'Getting git changes in {cwd}')

    try:
        changes = await call_sync_from_async(runtime.get_git_changes, cwd)
        if changes is None:
            return JSONResponse(
                status_code=404,
                content={'error': 'Not a git repository'},
            )
        return changes
    except AgentRuntimeUnavailableError as e:
        logger.error(f'Runtime unavailable: {e}')
        return JSONResponse(
            status_code=500,
            content={'error': f'Error getting changes: {e}'},
        )
    except Exception as e:
        logger.error(f'Error getting changes: {e}')
        return JSONResponse(
            status_code=500,
            content={'error': str(e)},
        )


@app.get(
    '/git/diff',
    response_model=dict[str, Any],
    responses={500: {'description': 'Error getting diff', 'model': dict}},
)
async def git_diff(
    request: Request,
    path: str,
    conversation_id: str,
    conversation_store: Any = Depends(get_conversation_store),
) -> dict[str, Any] | JSONResponse:
    runtime: Runtime = request.state.conversation.runtime

    cwd = await get_cwd(
        conversation_store,
        conversation_id,
        runtime.config.workspace_mount_path_in_sandbox,
    )

    try:
        diff = await call_sync_from_async(runtime.get_git_diff, path, cwd)
        return diff
    except AgentRuntimeUnavailableError as e:
        logger.error(f'Error getting diff: {e}')
        return JSONResponse(
            status_code=500,
            content={'error': f'Error getting diff: {e}'},
        )


async def get_cwd(
    conversation_store: ConversationStore,
    conversation_id: str,
    workspace_mount_path_in_sandbox: str,
) -> str:
    metadata = await conversation_store.get_metadata(conversation_id)
    cwd = workspace_mount_path_in_sandbox
    if metadata and metadata.selected_repository:
        repo_dir = metadata.selected_repository.split('/')[-1]
        cwd = os.path.join(cwd, repo_dir)

    return cwd
