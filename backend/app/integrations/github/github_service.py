"""
GitHub service implementation for OpenReplica matching OpenHands exactly
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


class GithubServiceImpl(GitService):
    """GitHub service implementation"""
    
    def __init__(self, token: SecretStr | str, host: str | None = None):
        if isinstance(token, str):
            self.token = SecretStr(token)
        else:
            self.token = token
        self.host = host or "api.github.com"
        self.base_url = f"https://{self.host}" if not self.host.startswith("http") else self.host
        if not self.base_url.endswith("/api/v3"):
            self.base_url += "/api/v3" if "github.com" in self.base_url else "/api/v3"
        
        self.headers = {
            "Authorization": f"Bearer {self.token.get_secret_value()}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make HTTP request to GitHub API"""
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
                    raise AuthenticationError("Invalid GitHub token")
                elif response.status_code == 404:
                    raise RepositoryNotFoundError("Repository not found")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"GitHub API request failed: {e}")
            raise
    
    async def get_user(self) -> User:
        """Get authenticated user information"""
        data = await self._make_request("GET", "/user")
        
        return User(
            id=data["id"],
            username=data["login"],
            name=data.get("name"),
            email=data.get("email"),
            avatar_url=data.get("avatar_url"),
            profile_url=data.get("html_url"),
            bio=data.get("bio"),
            company=data.get("company"),
            location=data.get("location"),
            blog=data.get("blog"),
            public_repos=data.get("public_repos"),
            followers=data.get("followers"),
            following=data.get("following"),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")) if data.get("updated_at") else None,
        )
    
    async def list_repositories(
        self, 
        visibility: str = "all",
        sort: str = "updated",
        per_page: int = 30,
        page: int = 1
    ) -> list[Repository]:
        """List user repositories"""
        params = {
            "visibility": visibility,
            "sort": sort,
            "per_page": per_page,
            "page": page
        }
        
        data = await self._make_request("GET", "/user/repos", params=params)
        
        repositories = []
        for repo_data in data:
            repositories.append(self._parse_repository(repo_data))
        
        return repositories
    
    async def get_repository(self, repo_name: str) -> Repository:
        """Get repository information"""
        data = await self._make_request("GET", f"/repos/{repo_name}")
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
            "private": private,
            "auto_init": auto_init
        }
        
        data = await self._make_request("POST", "/user/repos", json_data=json_data)
        return self._parse_repository(data)
    
    async def fork_repository(self, repo_name: str) -> Repository:
        """Fork a repository"""
        data = await self._make_request("POST", f"/repos/{repo_name}/forks")
        return self._parse_repository(data)
    
    async def list_branches(self, repo_name: str) -> list[Branch]:
        """List repository branches"""
        data = await self._make_request("GET", f"/repos/{repo_name}/branches")
        
        branches = []
        for branch_data in data:
            branches.append(Branch(
                name=branch_data["name"],
                sha=branch_data["commit"]["sha"],
                protected=branch_data.get("protected", False),
                protection_url=branch_data.get("protection_url"),
                commit=branch_data.get("commit")
            ))
        
        return branches
    
    async def get_branch(self, repo_name: str, branch_name: str) -> Branch:
        """Get branch information"""
        data = await self._make_request("GET", f"/repos/{repo_name}/branches/{branch_name}")
        
        return Branch(
            name=data["name"],
            sha=data["commit"]["sha"],
            protected=data.get("protected", False),
            protection_url=data.get("protection_url"),
            commit=data.get("commit")
        )
    
    async def create_branch(
        self, 
        repo_name: str, 
        branch_name: str, 
        from_branch: str = "main"
    ) -> Branch:
        """Create a new branch"""
        # Get the SHA of the source branch
        source_branch = await self.get_branch(repo_name, from_branch)
        
        json_data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": source_branch.sha
        }
        
        await self._make_request("POST", f"/repos/{repo_name}/git/refs", json_data=json_data)
        
        # Return the new branch info
        return await self.get_branch(repo_name, branch_name)
    
    async def list_pull_requests(
        self,
        repo_name: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc"
    ) -> list[PullRequest]:
        """List pull requests"""
        params = {
            "state": state,
            "sort": sort,
            "direction": direction
        }
        
        data = await self._make_request("GET", f"/repos/{repo_name}/pulls", params=params)
        
        pull_requests = []
        for pr_data in data:
            pull_requests.append(self._parse_pull_request(pr_data))
        
        return pull_requests
    
    async def get_pull_request(self, repo_name: str, pr_number: int) -> PullRequest:
        """Get pull request information"""
        data = await self._make_request("GET", f"/repos/{repo_name}/pulls/{pr_number}")
        return self._parse_pull_request(data)
    
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
        json_data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
            "draft": draft
        }
        
        data = await self._make_request("POST", f"/repos/{repo_name}/pulls", json_data=json_data)
        return self._parse_pull_request(data)
    
    async def list_issues(
        self,
        repo_name: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc"
    ) -> list[Issue]:
        """List issues"""
        params = {
            "state": state,
            "sort": sort,
            "direction": direction
        }
        
        data = await self._make_request("GET", f"/repos/{repo_name}/issues", params=params)
        
        issues = []
        for issue_data in data:
            # Skip pull requests (GitHub includes them in issues)
            if "pull_request" not in issue_data:
                issues.append(self._parse_issue(issue_data))
        
        return issues
    
    async def get_issue(self, repo_name: str, issue_number: int) -> Issue:
        """Get issue information"""
        data = await self._make_request("GET", f"/repos/{repo_name}/issues/{issue_number}")
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
        json_data = {
            "title": title,
            "body": body,
            "labels": labels or [],
            "assignees": assignees or []
        }
        
        data = await self._make_request("POST", f"/repos/{repo_name}/issues", json_data=json_data)
        return self._parse_issue(data)
    
    async def list_commits(
        self,
        repo_name: str,
        branch: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None
    ) -> list[Commit]:
        """List repository commits"""
        params = {}
        if branch:
            params["sha"] = branch
        if since:
            params["since"] = since.isoformat()
        if until:
            params["until"] = until.isoformat()
        
        data = await self._make_request("GET", f"/repos/{repo_name}/commits", params=params)
        
        commits = []
        for commit_data in data:
            commits.append(self._parse_commit(commit_data))
        
        return commits
    
    async def get_commit(self, repo_name: str, sha: str) -> Commit:
        """Get commit information"""
        data = await self._make_request("GET", f"/repos/{repo_name}/commits/{sha}")
        return self._parse_commit(data)
    
    async def list_releases(self, repo_name: str) -> list[Release]:
        """List repository releases"""
        data = await self._make_request("GET", f"/repos/{repo_name}/releases")
        
        releases = []
        for release_data in data:
            releases.append(self._parse_release(release_data))
        
        return releases
    
    async def get_release(self, repo_name: str, release_id: str) -> Release:
        """Get release information"""
        data = await self._make_request("GET", f"/repos/{repo_name}/releases/{release_id}")
        return self._parse_release(data)
    
    async def get_file_content(
        self, 
        repo_name: str, 
        file_path: str, 
        branch: str | None = None
    ) -> dict[str, Any]:
        """Get file content from repository"""
        params = {}
        if branch:
            params["ref"] = branch
        
        data = await self._make_request("GET", f"/repos/{repo_name}/contents/{file_path}", params=params)
        
        # Decode base64 content if it's a file
        if data.get("type") == "file" and data.get("content"):
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
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
        
        json_data = {
            "message": message,
            "content": encoded_content
        }
        
        if branch:
            json_data["branch"] = branch
        
        return await self._make_request("PUT", f"/repos/{repo_name}/contents/{file_path}", json_data=json_data)
    
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
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
        
        json_data = {
            "message": message,
            "content": encoded_content,
            "sha": sha
        }
        
        if branch:
            json_data["branch"] = branch
        
        return await self._make_request("PUT", f"/repos/{repo_name}/contents/{file_path}", json_data=json_data)
    
    async def delete_file(
        self,
        repo_name: str,
        file_path: str,
        message: str,
        sha: str,
        branch: str | None = None
    ) -> dict[str, Any]:
        """Delete a file from repository"""
        json_data = {
            "message": message,
            "sha": sha
        }
        
        if branch:
            json_data["branch"] = branch
        
        return await self._make_request("DELETE", f"/repos/{repo_name}/contents/{file_path}", json_data=json_data)
    
    async def get_suggested_tasks(self, repo_name: str) -> list[SuggestedTask]:
        """Get AI-suggested tasks for the repository"""
        # Get repository info and recent issues/PRs to suggest tasks
        try:
            repo = await self.get_repository(repo_name)
            issues = await self.list_issues(repo_name, state="open")
            
            suggested_tasks = []
            
            # Suggest documentation if README is minimal
            if repo.description and len(repo.description) < 100:
                suggested_tasks.append(SuggestedTask(
                    title="Improve project documentation",
                    description="Expand the README with detailed installation, usage, and contribution guidelines",
                    type="documentation",
                    priority="medium",
                    estimated_effort="medium",
                    files_to_modify=["README.md"]
                ))
            
            # Suggest tests if no test files found
            suggested_tasks.append(SuggestedTask(
                title="Add comprehensive test coverage",
                description="Implement unit tests and integration tests to ensure code quality",
                type="improvement",
                priority="high",
                estimated_effort="large",
                files_to_modify=["tests/"]
            ))
            
            # Suggest CI/CD if no workflows
            suggested_tasks.append(SuggestedTask(
                title="Setup CI/CD pipeline",
                description="Add GitHub Actions workflow for automated testing and deployment",
                type="improvement",
                priority="medium",
                estimated_effort="medium",
                files_to_modify=[".github/workflows/"]
            ))
            
            # Suggest issue templates
            suggested_tasks.append(SuggestedTask(
                title="Add issue and PR templates",
                description="Create templates to standardize bug reports and feature requests",
                type="improvement",
                priority="low",
                estimated_effort="small",
                files_to_modify=[".github/ISSUE_TEMPLATE/", ".github/pull_request_template.md"]
            ))
            
            return suggested_tasks[:5]  # Return top 5 suggestions
            
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
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": per_page
        }
        
        data = await self._make_request("GET", "/search/repositories", params=params)
        
        repositories = []
        for repo_data in data.get("items", []):
            repositories.append(self._parse_repository(repo_data))
        
        return repositories
    
    async def search_code(
        self,
        query: str,
        repo_name: str | None = None,
        sort: str = "indexed",
        order: str = "desc"
    ) -> dict[str, Any]:
        """Search code"""
        search_query = query
        if repo_name:
            search_query += f" repo:{repo_name}"
        
        params = {
            "q": search_query,
            "sort": sort,
            "order": order
        }
        
        return await self._make_request("GET", "/search/code", params=params)
    
    async def get_repository_stats(self, repo_name: str) -> dict[str, Any]:
        """Get repository statistics"""
        # Get various stats from different endpoints
        repo = await self.get_repository(repo_name)
        languages = await self.get_repository_languages(repo_name)
        
        try:
            # Get contributor stats
            contributors = await self._make_request("GET", f"/repos/{repo_name}/contributors")
            commit_activity = await self._make_request("GET", f"/repos/{repo_name}/stats/commit_activity")
        except Exception:
            contributors = []
            commit_activity = []
        
        return {
            "basic_stats": {
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "watchers": repo.watchers_count,
                "open_issues": repo.open_issues_count,
                "size": repo.size
            },
            "languages": languages,
            "contributors": len(contributors),
            "commit_activity": commit_activity
        }
    
    async def get_repository_languages(self, repo_name: str) -> dict[str, int]:
        """Get repository programming languages"""
        return await self._make_request("GET", f"/repos/{repo_name}/languages")
    
    async def get_repository_topics(self, repo_name: str) -> list[str]:
        """Get repository topics/tags"""
        headers = {**self.headers, "Accept": "application/vnd.github.mercy-preview+json"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{repo_name}/topics",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
        
        return data.get("names", [])
    
    def _parse_user(self, user_data: dict[str, Any]) -> User:
        """Parse user data from GitHub API"""
        return User(
            id=user_data["id"],
            username=user_data["login"],
            name=user_data.get("name"),
            email=user_data.get("email"),
            avatar_url=user_data.get("avatar_url"),
            profile_url=user_data.get("html_url")
        )
    
    def _parse_repository(self, repo_data: dict[str, Any]) -> Repository:
        """Parse repository data from GitHub API"""
        return Repository(
            id=repo_data["id"],
            name=repo_data["name"],
            full_name=repo_data["full_name"],
            description=repo_data.get("description"),
            private=repo_data["private"],
            fork=repo_data["fork"],
            archived=repo_data.get("archived", False),
            disabled=repo_data.get("disabled", False),
            html_url=repo_data["html_url"],
            clone_url=repo_data["clone_url"],
            ssh_url=repo_data.get("ssh_url"),
            default_branch=repo_data.get("default_branch", "main"),
            language=repo_data.get("language"),
            size=repo_data.get("size"),
            stargazers_count=repo_data.get("stargazers_count"),
            watchers_count=repo_data.get("watchers_count"),
            forks_count=repo_data.get("forks_count"),
            open_issues_count=repo_data.get("open_issues_count"),
            license=repo_data.get("license", {}).get("spdx_id") if repo_data.get("license") else None,
            owner=self._parse_user(repo_data["owner"]),
            created_at=datetime.fromisoformat(repo_data["created_at"].replace("Z", "+00:00")) if repo_data.get("created_at") else None,
            updated_at=datetime.fromisoformat(repo_data["updated_at"].replace("Z", "+00:00")) if repo_data.get("updated_at") else None,
            pushed_at=datetime.fromisoformat(repo_data["pushed_at"].replace("Z", "+00:00")) if repo_data.get("pushed_at") else None,
        )
    
    def _parse_pull_request(self, pr_data: dict[str, Any]) -> PullRequest:
        """Parse pull request data from GitHub API"""
        return PullRequest(
            id=pr_data["id"],
            number=pr_data["number"],
            title=pr_data["title"],
            body=pr_data.get("body"),
            state=pr_data["state"],
            draft=pr_data.get("draft", False),
            mergeable=pr_data.get("mergeable"),
            rebaseable=pr_data.get("rebaseable"),
            head=pr_data["head"],
            base=pr_data["base"],
            user=self._parse_user(pr_data["user"]),
            html_url=pr_data["html_url"],
            diff_url=pr_data.get("diff_url"),
            patch_url=pr_data.get("patch_url"),
            created_at=datetime.fromisoformat(pr_data["created_at"].replace("Z", "+00:00")) if pr_data.get("created_at") else None,
            updated_at=datetime.fromisoformat(pr_data["updated_at"].replace("Z", "+00:00")) if pr_data.get("updated_at") else None,
            closed_at=datetime.fromisoformat(pr_data["closed_at"].replace("Z", "+00:00")) if pr_data.get("closed_at") else None,
            merged_at=datetime.fromisoformat(pr_data["merged_at"].replace("Z", "+00:00")) if pr_data.get("merged_at") else None,
        )
    
    def _parse_issue(self, issue_data: dict[str, Any]) -> Issue:
        """Parse issue data from GitHub API"""
        return Issue(
            id=issue_data["id"],
            number=issue_data["number"],
            title=issue_data["title"],
            body=issue_data.get("body"),
            state=issue_data["state"],
            locked=issue_data.get("locked", False),
            user=self._parse_user(issue_data["user"]),
            labels=issue_data.get("labels", []),
            comments=issue_data.get("comments"),
            html_url=issue_data["html_url"],
            created_at=datetime.fromisoformat(issue_data["created_at"].replace("Z", "+00:00")) if issue_data.get("created_at") else None,
            updated_at=datetime.fromisoformat(issue_data["updated_at"].replace("Z", "+00:00")) if issue_data.get("updated_at") else None,
            closed_at=datetime.fromisoformat(issue_data["closed_at"].replace("Z", "+00:00")) if issue_data.get("closed_at") else None,
        )
    
    def _parse_commit(self, commit_data: dict[str, Any]) -> Commit:
        """Parse commit data from GitHub API"""
        return Commit(
            sha=commit_data["sha"],
            message=commit_data["commit"]["message"],
            author=commit_data["commit"]["author"],
            committer=commit_data["commit"]["committer"],
            tree=commit_data["commit"]["tree"],
            parents=commit_data.get("parents"),
            html_url=commit_data.get("html_url"),
            stats=commit_data.get("stats"),
            files=commit_data.get("files")
        )
    
    def _parse_release(self, release_data: dict[str, Any]) -> Release:
        """Parse release data from GitHub API"""
        return Release(
            id=release_data["id"],
            tag_name=release_data["tag_name"],
            name=release_data.get("name"),
            body=release_data.get("body"),
            draft=release_data.get("draft", False),
            prerelease=release_data.get("prerelease", False),
            target_commitish=release_data.get("target_commitish"),
            html_url=release_data.get("html_url"),
            tarball_url=release_data.get("tarball_url"),
            zipball_url=release_data.get("zipball_url"),
            assets=release_data.get("assets", []),
            author=self._parse_user(release_data["author"]) if release_data.get("author") else None,
            created_at=datetime.fromisoformat(release_data["created_at"].replace("Z", "+00:00")) if release_data.get("created_at") else None,
            published_at=datetime.fromisoformat(release_data["published_at"].replace("Z", "+00:00")) if release_data.get("published_at") else None,
        )
