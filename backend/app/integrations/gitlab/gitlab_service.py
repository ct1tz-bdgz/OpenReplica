"""
GitLab service implementation for OpenReplica matching OpenHands exactly
"""
from __future__ import annotations

import base64
from datetime import datetime
from typing import Any
import httpx
from pydantic import SecretStr

from app.core.logging import get_logger
from app.integrations.service_types import (
    AuthenticationError,
    Branch,
    Comment,
    Commit,
    GitService,
    Issue,
    PullRequest,
    Release,
    Repository,
    RepositoryNotFoundError,
    SuggestedTask,
    User,
)

logger = get_logger(__name__)


class GitLabServiceImpl(GitService):
    """GitLab service implementation"""
    
    def __init__(self, token: SecretStr | str, host: str | None = None):
        if isinstance(token, str):
            self.token = SecretStr(token)
        else:
            self.token = token
        self.host = host or "gitlab.com"
        self.base_url = f"https://{self.host}" if not self.host.startswith("http") else self.host
        if not self.base_url.endswith("/api/v4"):
            self.base_url += "/api/v4"
        
        self.headers = {
            "Authorization": f"Bearer {self.token.get_secret_value()}",
            "Content-Type": "application/json",
        }
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make HTTP request to GitLab API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json_data,
                    timeout=30.0
                )
                
                if response.status_code == 401:
                    raise AuthenticationError("Invalid GitLab token")
                elif response.status_code == 404:
                    raise RepositoryNotFoundError("Repository not found")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"GitLab API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"GitLab API request failed: {e}")
            raise
    
    async def get_user(self) -> User:
        """Get authenticated user information"""
        data = await self._make_request("GET", "/user")
        
        return User(
            id=data["id"],
            username=data["username"],
            name=data.get("name"),
            email=data.get("email"),
            avatar_url=data.get("avatar_url"),
            profile_url=data.get("web_url"),
            bio=data.get("bio"),
            company=data.get("organization"),
            location=data.get("location"),
            blog=data.get("website_url"),
            public_repos=data.get("public_repos"),
            followers=data.get("followers"),
            following=data.get("following"),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else None,
        )
    
    async def list_repositories(
        self, 
        visibility: str = "all",
        sort: str = "updated_at",
        per_page: int = 30,
        page: int = 1
    ) -> list[Repository]:
        """List user repositories"""
        params = {
            "visibility": visibility if visibility != "all" else None,
            "order_by": sort,
            "sort": "desc",
            "per_page": per_page,
            "page": page,
            "owned": True
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        data = await self._make_request("GET", "/projects", params=params)
        
        repositories = []
        for repo_data in data:
            repositories.append(self._parse_repository(repo_data))
        
        return repositories
    
    async def get_repository(self, repo_name: str) -> Repository:
        """Get repository information"""
        # GitLab uses project ID or namespace/project format
        encoded_name = repo_name.replace("/", "%2F")
        data = await self._make_request("GET", f"/projects/{encoded_name}")
        return self._parse_repository(data)
    
    async def create_repository(
        self, 
        name: str, 
        description: str | None = None,
        private: bool = True,
        auto_init: bool = False
    ) -> Repository:
        """Create a new repository"""
        json_data = {
            "name": name,
            "description": description,
            "visibility": "private" if private else "public",
            "initialize_with_readme": auto_init
        }
        
        data = await self._make_request("POST", "/projects", json_data=json_data)
        return self._parse_repository(data)
    
    async def fork_repository(self, repo_name: str) -> Repository:
        """Fork a repository"""
        encoded_name = repo_name.replace("/", "%2F")
        data = await self._make_request("POST", f"/projects/{encoded_name}/fork")
        return self._parse_repository(data)
    
    async def list_branches(self, repo_name: str) -> list[Branch]:
        """List repository branches"""
        encoded_name = repo_name.replace("/", "%2F")
        data = await self._make_request("GET", f"/projects/{encoded_name}/repository/branches")
        
        branches = []
        for branch_data in data:
            branches.append(Branch(
                name=branch_data["name"],
                sha=branch_data["commit"]["id"],
                protected=branch_data.get("protected", False),
                commit=branch_data.get("commit")
            ))
        
        return branches
    
    async def get_branch(self, repo_name: str, branch_name: str) -> Branch:
        """Get branch information"""
        encoded_name = repo_name.replace("/", "%2F")
        encoded_branch = branch_name.replace("/", "%2F")
        data = await self._make_request("GET", f"/projects/{encoded_name}/repository/branches/{encoded_branch}")
        
        return Branch(
            name=data["name"],
            sha=data["commit"]["id"],
            protected=data.get("protected", False),
            commit=data.get("commit")
        )
    
    async def create_branch(
        self, 
        repo_name: str, 
        branch_name: str, 
        from_branch: str = "main"
    ) -> Branch:
        """Create a new branch"""
        encoded_name = repo_name.replace("/", "%2F")
        
        json_data = {
            "branch": branch_name,
            "ref": from_branch
        }
        
        data = await self._make_request("POST", f"/projects/{encoded_name}/repository/branches", json_data=json_data)
        
        return Branch(
            name=data["name"],
            sha=data["commit"]["id"],
            protected=data.get("protected", False),
            commit=data.get("commit")
        )
    
    async def list_pull_requests(
        self,
        repo_name: str,
        state: str = "opened",
        sort: str = "created_at",
        direction: str = "desc"
    ) -> list[PullRequest]:
        """List merge requests (GitLab's equivalent of pull requests)"""
        encoded_name = repo_name.replace("/", "%2F")
        
        params = {
            "state": state,
            "order_by": sort,
            "sort": direction
        }
        
        data = await self._make_request("GET", f"/projects/{encoded_name}/merge_requests", params=params)
        
        pull_requests = []
        for mr_data in data:
            pull_requests.append(self._parse_merge_request(mr_data))
        
        return pull_requests
    
    async def get_pull_request(self, repo_name: str, pr_number: int) -> PullRequest:
        """Get merge request information"""
        encoded_name = repo_name.replace("/", "%2F")
        data = await self._make_request("GET", f"/projects/{encoded_name}/merge_requests/{pr_number}")
        return self._parse_merge_request(data)
    
    async def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        draft: bool = False
    ) -> PullRequest:
        """Create a merge request"""
        encoded_name = repo_name.replace("/", "%2F")
        
        json_data = {
            "title": title,
            "description": body,
            "source_branch": head_branch,
            "target_branch": base_branch,
            "draft": draft
        }
        
        data = await self._make_request("POST", f"/projects/{encoded_name}/merge_requests", json_data=json_data)
        return self._parse_merge_request(data)
    
    async def list_issues(
        self,
        repo_name: str,
        state: str = "opened",
        sort: str = "created_at",
        direction: str = "desc"
    ) -> list[Issue]:
        """List issues"""
        encoded_name = repo_name.replace("/", "%2F")
        
        params = {
            "state": state,
            "order_by": sort,
            "sort": direction
        }
        
        data = await self._make_request("GET", f"/projects/{encoded_name}/issues", params=params)
        
        issues = []
        for issue_data in data:
            issues.append(self._parse_issue(issue_data))
        
        return issues
    
    async def get_issue(self, repo_name: str, issue_number: int) -> Issue:
        """Get issue information"""
        encoded_name = repo_name.replace("/", "%2F")
        data = await self._make_request("GET", f"/projects/{encoded_name}/issues/{issue_number}")
        return self._parse_issue(data)
    
    async def create_issue(
        self,
        repo_name: str,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None
    ) -> Issue:
        """Create an issue"""
        encoded_name = repo_name.replace("/", "%2F")
        
        json_data = {
            "title": title,
            "description": body,
            "labels": ",".join(labels) if labels else None,
            "assignee_ids": assignees  # GitLab uses user IDs for assignees
        }
        
        # Remove None values
        json_data = {k: v for k, v in json_data.items() if v is not None}
        
        data = await self._make_request("POST", f"/projects/{encoded_name}/issues", json_data=json_data)
        return self._parse_issue(data)
    
    async def list_commits(
        self,
        repo_name: str,
        branch: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None
    ) -> list[Commit]:
        """List repository commits"""
        encoded_name = repo_name.replace("/", "%2F")
        
        params = {}
        if branch:
            params["ref_name"] = branch
        if since:
            params["since"] = since.isoformat()
        if until:
            params["until"] = until.isoformat()
        
        data = await self._make_request("GET", f"/projects/{encoded_name}/repository/commits", params=params)
        
        commits = []
        for commit_data in data:
            commits.append(self._parse_commit(commit_data))
        
        return commits
    
    async def get_commit(self, repo_name: str, sha: str) -> Commit:
        """Get commit information"""
        encoded_name = repo_name.replace("/", "%2F")
        data = await self._make_request("GET", f"/projects/{encoded_name}/repository/commits/{sha}")
        return self._parse_commit(data)
    
    async def list_releases(self, repo_name: str) -> list[Release]:
        """List repository releases"""
        encoded_name = repo_name.replace("/", "%2F")
        data = await self._make_request("GET", f"/projects/{encoded_name}/releases")
        
        releases = []
        for release_data in data:
            releases.append(self._parse_release(release_data))
        
        return releases
    
    async def get_release(self, repo_name: str, release_id: str) -> Release:
        """Get release information"""
        encoded_name = repo_name.replace("/", "%2F")
        data = await self._make_request("GET", f"/projects/{encoded_name}/releases/{release_id}")
        return self._parse_release(data)
    
    async def get_file_content(
        self, 
        repo_name: str, 
        file_path: str, 
        branch: str | None = None
    ) -> dict[str, Any]:
        """Get file content from repository"""
        encoded_name = repo_name.replace("/", "%2F")
        encoded_path = file_path.replace("/", "%2F")
        
        params = {}
        if branch:
            params["ref"] = branch
        
        data = await self._make_request("GET", f"/projects/{encoded_name}/repository/files/{encoded_path}", params=params)
        
        # Decode base64 content
        if data.get("content"):
            content = base64.b64decode(data["content"]).decode("utf-8")
            data["decoded_content"] = content
        
        return data
    
    async def create_file(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        message: str,
        branch: str | None = None
    ) -> dict[str, Any]:
        """Create a file in repository"""
        encoded_name = repo_name.replace("/", "%2F")
        encoded_path = file_path.replace("/", "%2F")
        
        json_data = {
            "commit_message": message,
            "content": content,
            "branch": branch or "main"
        }
        
        return await self._make_request("POST", f"/projects/{encoded_name}/repository/files/{encoded_path}", json_data=json_data)
    
    async def update_file(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        message: str,
        sha: str,  # GitLab doesn't use SHA for file updates like GitHub
        branch: str | None = None
    ) -> dict[str, Any]:
        """Update a file in repository"""
        encoded_name = repo_name.replace("/", "%2F")
        encoded_path = file_path.replace("/", "%2F")
        
        json_data = {
            "commit_message": message,
            "content": content,
            "branch": branch or "main"
        }
        
        return await self._make_request("PUT", f"/projects/{encoded_name}/repository/files/{encoded_path}", json_data=json_data)
    
    async def delete_file(
        self,
        repo_name: str,
        file_path: str,
        message: str,
        sha: str,  # GitLab doesn't use SHA for file deletion like GitHub
        branch: str | None = None
    ) -> dict[str, Any]:
        """Delete a file from repository"""
        encoded_name = repo_name.replace("/", "%2F")
        encoded_path = file_path.replace("/", "%2F")
        
        json_data = {
            "commit_message": message,
            "branch": branch or "main"
        }
        
        return await self._make_request("DELETE", f"/projects/{encoded_name}/repository/files/{encoded_path}", json_data=json_data)
    
    async def get_suggested_tasks(self, repo_name: str) -> list[SuggestedTask]:
        """Get AI-suggested tasks for the repository"""
        try:
            repo = await self.get_repository(repo_name)
            issues = await self.list_issues(repo_name, state="opened")
            
            suggested_tasks = []
            
            # Suggest documentation improvements
            if repo.description and len(repo.description) < 100:
                suggested_tasks.append(SuggestedTask(
                    title="Enhance project documentation",
                    description="Improve README.md with comprehensive installation, usage, and contribution guidelines",
                    type="documentation",
                    priority="medium",
                    estimated_effort="medium",
                    files_to_modify=["README.md", "docs/"]
                ))
            
            # Suggest CI/CD pipeline
            suggested_tasks.append(SuggestedTask(
                title="Setup GitLab CI/CD pipeline",
                description="Add .gitlab-ci.yml for automated testing, building, and deployment",
                type="improvement",
                priority="high",
                estimated_effort="large",
                files_to_modify=[".gitlab-ci.yml"]
            ))
            
            # Suggest security improvements
            suggested_tasks.append(SuggestedTask(
                title="Add security scanning",
                description="Enable GitLab security features like SAST, dependency scanning, and container scanning",
                type="security",
                priority="high",
                estimated_effort="medium",
                files_to_modify=[".gitlab-ci.yml"]
            ))
            
            # Suggest testing framework
            suggested_tasks.append(SuggestedTask(
                title="Implement comprehensive testing",
                description="Add unit tests, integration tests, and test coverage reporting",
                type="improvement",
                priority="high",
                estimated_effort="large",
                files_to_modify=["tests/", "spec/"]
            ))
            
            # Suggest merge request templates
            suggested_tasks.append(SuggestedTask(
                title="Add merge request templates",
                description="Create templates to standardize merge requests and code reviews",
                type="improvement",
                priority="low",
                estimated_effort="small",
                files_to_modify=[".gitlab/merge_request_templates/"]
            ))
            
            return suggested_tasks[:5]
            
        except Exception as e:
            logger.warning(f"Failed to generate suggested tasks: {e}")
            return []
    
    async def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 30
    ) -> list[Repository]:
        """Search repositories"""
        params = {
            "search": query,
            "order_by": sort,
            "sort": order,
            "per_page": per_page
        }
        
        data = await self._make_request("GET", "/projects", params=params)
        
        repositories = []
        for repo_data in data:
            repositories.append(self._parse_repository(repo_data))
        
        return repositories
    
    async def search_code(
        self,
        query: str,
        repo_name: str | None = None,
        sort: str = "created_at",
        order: str = "desc"
    ) -> dict[str, Any]:
        """Search code"""
        params = {
            "search": query,
            "scope": "blobs"
        }
        
        if repo_name:
            encoded_name = repo_name.replace("/", "%2F")
            endpoint = f"/projects/{encoded_name}/search"
        else:
            endpoint = "/search"
        
        return await self._make_request("GET", endpoint, params=params)
    
    async def get_repository_stats(self, repo_name: str) -> dict[str, Any]:
        """Get repository statistics"""
        encoded_name = repo_name.replace("/", "%2F")
        
        # Get basic repository info
        repo = await self.get_repository(repo_name)
        
        try:
            # Get contributor stats
            contributors = await self._make_request("GET", f"/projects/{encoded_name}/repository/contributors")
            languages = await self.get_repository_languages(repo_name)
        except Exception:
            contributors = []
            languages = {}
        
        return {
            "basic_stats": {
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
            },
            "languages": languages,
            "contributors": len(contributors),
        }
    
    async def get_repository_languages(self, repo_name: str) -> dict[str, int]:
        """Get repository programming languages"""
        encoded_name = repo_name.replace("/", "%2F")
        try:
            return await self._make_request("GET", f"/projects/{encoded_name}/languages")
        except Exception:
            return {}
    
    async def get_repository_topics(self, repo_name: str) -> list[str]:
        """Get repository topics/tags"""
        encoded_name = repo_name.replace("/", "%2F")
        try:
            data = await self._make_request("GET", f"/projects/{encoded_name}")
            return data.get("topics", [])
        except Exception:
            return []
    
    def _parse_user(self, user_data: dict[str, Any]) -> User:
        """Parse user data from GitLab API"""
        return User(
            id=user_data["id"],
            username=user_data["username"],
            name=user_data.get("name"),
            email=user_data.get("email"),
            avatar_url=user_data.get("avatar_url"),
            profile_url=user_data.get("web_url")
        )
    
    def _parse_repository(self, repo_data: dict[str, Any]) -> Repository:
        """Parse repository data from GitLab API"""
        return Repository(
            id=repo_data["id"],
            name=repo_data["name"],
            full_name=repo_data["path_with_namespace"],
            description=repo_data.get("description"),
            private=repo_data.get("visibility") == "private",
            fork=repo_data.get("forked_from_project") is not None,
            archived=repo_data.get("archived", False),
            disabled=False,  # GitLab doesn't have disabled concept
            html_url=repo_data["web_url"],
            clone_url=repo_data["http_url_to_repo"],
            ssh_url=repo_data.get("ssh_url_to_repo"),
            default_branch=repo_data.get("default_branch", "main"),
            language=None,  # GitLab doesn't provide single language
            size=None,  # GitLab doesn't provide size in project info
            stargazers_count=repo_data.get("star_count"),
            forks_count=repo_data.get("forks_count"),
            open_issues_count=repo_data.get("open_issues_count"),
            owner=self._parse_user(repo_data.get("owner", repo_data.get("namespace", {}))),
            created_at=datetime.fromisoformat(repo_data["created_at"].replace("Z", "+00:00")) if repo_data.get("created_at") else None,
            updated_at=datetime.fromisoformat(repo_data["last_activity_at"].replace("Z", "+00:00")) if repo_data.get("last_activity_at") else None,
        )
    
    def _parse_merge_request(self, mr_data: dict[str, Any]) -> PullRequest:
        """Parse merge request data from GitLab API"""
        return PullRequest(
            id=mr_data["id"],
            number=mr_data["iid"],  # GitLab uses iid for internal ID
            title=mr_data["title"],
            body=mr_data.get("description"),
            state=mr_data["state"],
            draft=mr_data.get("draft", False),
            mergeable=mr_data.get("merge_status") == "can_be_merged",
            head={
                "ref": mr_data["source_branch"],
                "sha": mr_data.get("sha"),
            },
            base={
                "ref": mr_data["target_branch"],
            },
            user=self._parse_user(mr_data["author"]),
            html_url=mr_data["web_url"],
            created_at=datetime.fromisoformat(mr_data["created_at"].replace("Z", "+00:00")) if mr_data.get("created_at") else None,
            updated_at=datetime.fromisoformat(mr_data["updated_at"].replace("Z", "+00:00")) if mr_data.get("updated_at") else None,
            merged_at=datetime.fromisoformat(mr_data["merged_at"].replace("Z", "+00:00")) if mr_data.get("merged_at") else None,
        )
    
    def _parse_issue(self, issue_data: dict[str, Any]) -> Issue:
        """Parse issue data from GitLab API"""
        return Issue(
            id=issue_data["id"],
            number=issue_data["iid"],
            title=issue_data["title"],
            body=issue_data.get("description"),
            state=issue_data["state"],
            locked=False,  # GitLab doesn't have locked concept for issues
            user=self._parse_user(issue_data["author"]),
            labels=issue_data.get("labels", []),
            html_url=issue_data["web_url"],
            created_at=datetime.fromisoformat(issue_data["created_at"].replace("Z", "+00:00")) if issue_data.get("created_at") else None,
            updated_at=datetime.fromisoformat(issue_data["updated_at"].replace("Z", "+00:00")) if issue_data.get("updated_at") else None,
            closed_at=datetime.fromisoformat(issue_data["closed_at"].replace("Z", "+00:00")) if issue_data.get("closed_at") else None,
        )
    
    def _parse_commit(self, commit_data: dict[str, Any]) -> Commit:
        """Parse commit data from GitLab API"""
        return Commit(
            sha=commit_data["id"],
            message=commit_data["message"],
            author={
                "name": commit_data.get("author_name"),
                "email": commit_data.get("author_email"),
                "date": commit_data.get("authored_date")
            },
            committer={
                "name": commit_data.get("committer_name"),
                "email": commit_data.get("committer_email"),
                "date": commit_data.get("committed_date")
            },
            tree={},  # GitLab doesn't provide tree info in commit list
            parents=commit_data.get("parent_ids", []),
            html_url=commit_data.get("web_url"),
            stats=commit_data.get("stats")
        )
    
    def _parse_release(self, release_data: dict[str, Any]) -> Release:
        """Parse release data from GitLab API"""
        return Release(
            id=release_data["name"],  # GitLab uses name as ID
            tag_name=release_data["tag_name"],
            name=release_data.get("name"),
            body=release_data.get("description"),
            draft=False,  # GitLab doesn't have draft releases
            prerelease=False,  # GitLab doesn't distinguish prereleases
            html_url=release_data.get("_links", {}).get("self"),
            created_at=datetime.fromisoformat(release_data["created_at"].replace("Z", "+00:00")) if release_data.get("created_at") else None,
            published_at=datetime.fromisoformat(release_data["released_at"].replace("Z", "+00:00")) if release_data.get("released_at") else None,
        )
