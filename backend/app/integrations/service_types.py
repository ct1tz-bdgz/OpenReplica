"""
Service types for OpenReplica matching OpenHands exactly
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Supported provider types"""
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    AZURE_DEVOPS = "azure_devops"


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class RepositoryNotFoundError(Exception):
    """Raised when repository is not found"""
    pass


class User(BaseModel):
    """User information from git providers"""
    id: int | str
    username: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    profile_url: str | None = None
    bio: str | None = None
    company: str | None = None
    location: str | None = None
    blog: str | None = None
    public_repos: int | None = None
    followers: int | None = None
    following: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Repository(BaseModel):
    """Repository information from git providers"""
    id: int | str
    name: str
    full_name: str
    description: str | None = None
    private: bool = False
    fork: bool = False
    archived: bool = False
    disabled: bool = False
    html_url: str
    clone_url: str
    ssh_url: str | None = None
    default_branch: str = "main"
    language: str | None = None
    languages: dict[str, int] | None = None
    topics: list[str] | None = None
    size: int | None = None
    stargazers_count: int | None = None
    watchers_count: int | None = None
    forks_count: int | None = None
    open_issues_count: int | None = None
    license: str | None = None
    owner: User
    permissions: dict[str, bool] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    pushed_at: datetime | None = None


class Branch(BaseModel):
    """Branch information from git providers"""
    name: str
    sha: str
    protected: bool = False
    protection_url: str | None = None
    commit: dict[str, Any] | None = None


class PullRequest(BaseModel):
    """Pull request information from git providers"""
    id: int | str
    number: int
    title: str
    body: str | None = None
    state: str  # open, closed, merged
    draft: bool = False
    mergeable: bool | None = None
    rebaseable: bool | None = None
    head: dict[str, Any]
    base: dict[str, Any]
    user: User
    assignees: list[User] | None = None
    reviewers: list[User] | None = None
    labels: list[dict[str, Any]] | None = None
    milestone: dict[str, Any] | None = None
    html_url: str
    diff_url: str | None = None
    patch_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    closed_at: datetime | None = None
    merged_at: datetime | None = None


class Issue(BaseModel):
    """Issue information from git providers"""
    id: int | str
    number: int
    title: str
    body: str | None = None
    state: str  # open, closed
    locked: bool = False
    user: User
    assignees: list[User] | None = None
    labels: list[dict[str, Any]] | None = None
    milestone: dict[str, Any] | None = None
    comments: int | None = None
    html_url: str
    repository_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    closed_at: datetime | None = None


class SuggestedTask(BaseModel):
    """Suggested task for a repository"""
    title: str
    description: str
    type: str  # "feature", "bug", "improvement", "documentation", etc.
    priority: str = "medium"  # "low", "medium", "high", "critical"
    estimated_effort: str | None = None  # "small", "medium", "large"
    labels: list[str] | None = None
    files_to_modify: list[str] | None = None
    related_issues: list[int] | None = None
    context: dict[str, Any] | None = None


class Commit(BaseModel):
    """Commit information from git providers"""
    sha: str
    message: str
    author: dict[str, Any]
    committer: dict[str, Any]
    tree: dict[str, Any]
    parents: list[dict[str, Any]] | None = None
    html_url: str | None = None
    stats: dict[str, Any] | None = None
    files: list[dict[str, Any]] | None = None
    created_at: datetime | None = None


class Comment(BaseModel):
    """Comment information from git providers"""
    id: int | str
    body: str
    user: User
    html_url: str | None = None
    issue_url: str | None = None
    pull_request_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Release(BaseModel):
    """Release information from git providers"""
    id: int | str
    tag_name: str
    name: str | None = None
    body: str | None = None
    draft: bool = False
    prerelease: bool = False
    target_commitish: str | None = None
    html_url: str | None = None
    tarball_url: str | None = None
    zipball_url: str | None = None
    assets: list[dict[str, Any]] | None = None
    author: User | None = None
    created_at: datetime | None = None
    published_at: datetime | None = None


class GitService:
    """Base interface for git service integrations"""
    
    async def get_user(self) -> User:
        """Get authenticated user information"""
        raise NotImplementedError
    
    async def list_repositories(
        self, 
        visibility: str = "all",
        sort: str = "updated",
        per_page: int = 30,
        page: int = 1
    ) -> list[Repository]:
        """List user repositories"""
        raise NotImplementedError
    
    async def get_repository(self, repo_name: str) -> Repository:
        """Get repository information"""
        raise NotImplementedError
    
    async def create_repository(
        self, 
        name: str, 
        description: str | None = None,
        private: bool = True,
        auto_init: bool = False
    ) -> Repository:
        """Create a new repository"""
        raise NotImplementedError
    
    async def fork_repository(self, repo_name: str) -> Repository:
        """Fork a repository"""
        raise NotImplementedError
    
    async def list_branches(self, repo_name: str) -> list[Branch]:
        """List repository branches"""
        raise NotImplementedError
    
    async def get_branch(self, repo_name: str, branch_name: str) -> Branch:
        """Get branch information"""
        raise NotImplementedError
    
    async def create_branch(
        self, 
        repo_name: str, 
        branch_name: str, 
        from_branch: str = "main"
    ) -> Branch:
        """Create a new branch"""
        raise NotImplementedError
    
    async def list_pull_requests(
        self,
        repo_name: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc"
    ) -> list[PullRequest]:
        """List pull requests"""
        raise NotImplementedError
    
    async def get_pull_request(self, repo_name: str, pr_number: int) -> PullRequest:
        """Get pull request information"""
        raise NotImplementedError
    
    async def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        draft: bool = False
    ) -> PullRequest:
        """Create a pull request"""
        raise NotImplementedError
    
    async def list_issues(
        self,
        repo_name: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc"
    ) -> list[Issue]:
        """List issues"""
        raise NotImplementedError
    
    async def get_issue(self, repo_name: str, issue_number: int) -> Issue:
        """Get issue information"""
        raise NotImplementedError
    
    async def create_issue(
        self,
        repo_name: str,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None
    ) -> Issue:
        """Create an issue"""
        raise NotImplementedError
    
    async def list_commits(
        self,
        repo_name: str,
        branch: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None
    ) -> list[Commit]:
        """List repository commits"""
        raise NotImplementedError
    
    async def get_commit(self, repo_name: str, sha: str) -> Commit:
        """Get commit information"""
        raise NotImplementedError
    
    async def list_releases(self, repo_name: str) -> list[Release]:
        """List repository releases"""
        raise NotImplementedError
    
    async def get_release(self, repo_name: str, release_id: str) -> Release:
        """Get release information"""
        raise NotImplementedError
    
    async def get_file_content(
        self, 
        repo_name: str, 
        file_path: str, 
        branch: str | None = None
    ) -> dict[str, Any]:
        """Get file content from repository"""
        raise NotImplementedError
    
    async def create_file(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        message: str,
        branch: str | None = None
    ) -> dict[str, Any]:
        """Create a file in repository"""
        raise NotImplementedError
    
    async def update_file(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        message: str,
        sha: str,
        branch: str | None = None
    ) -> dict[str, Any]:
        """Update a file in repository"""
        raise NotImplementedError
    
    async def delete_file(
        self,
        repo_name: str,
        file_path: str,
        message: str,
        sha: str,
        branch: str | None = None
    ) -> dict[str, Any]:
        """Delete a file from repository"""
        raise NotImplementedError
    
    async def get_suggested_tasks(self, repo_name: str) -> list[SuggestedTask]:
        """Get AI-suggested tasks for the repository"""
        # Default implementation returns empty list
        # Subclasses can override to provide intelligent suggestions
        return []
    
    async def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 30
    ) -> list[Repository]:
        """Search repositories"""
        raise NotImplementedError
    
    async def search_code(
        self,
        query: str,
        repo_name: str | None = None,
        sort: str = "indexed",
        order: str = "desc"
    ) -> dict[str, Any]:
        """Search code"""
        raise NotImplementedError
    
    async def get_repository_stats(self, repo_name: str) -> dict[str, Any]:
        """Get repository statistics"""
        raise NotImplementedError
    
    async def get_repository_languages(self, repo_name: str) -> dict[str, int]:
        """Get repository programming languages"""
        raise NotImplementedError
    
    async def get_repository_topics(self, repo_name: str) -> list[str]:
        """Get repository topics/tags"""
        raise NotImplementedError


class WebhookEvent(BaseModel):
    """Webhook event from git providers"""
    event_type: str
    action: str | None = None
    repository: Repository | None = None
    sender: User | None = None
    organization: dict[str, Any] | None = None
    installation: dict[str, Any] | None = None
    pull_request: PullRequest | None = None
    issue: Issue | None = None
    comment: Comment | None = None
    commit: Commit | None = None
    branch: Branch | None = None
    release: Release | None = None
    payload: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class GitServiceFactory:
    """Factory for creating git service instances"""
    
    @staticmethod
    def create_service(provider_type: ProviderType, token: str, host: str | None = None) -> GitService:
        """Create git service instance"""
        if provider_type == ProviderType.GITHUB:
            from app.integrations.github.github_service import GithubServiceImpl
            return GithubServiceImpl(token, host)
        elif provider_type == ProviderType.GITLAB:
            from app.integrations.gitlab.gitlab_service import GitLabServiceImpl
            return GitLabServiceImpl(token, host)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
