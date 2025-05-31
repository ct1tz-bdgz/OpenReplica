"""
Microagent storage implementation for OpenReplica matching OpenHands exactly
"""
import json
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.core.logging import get_logger
from app.microagent import (
    BaseMicroagent,
    KnowledgeMicroagent,
    RepoMicroagent,
    MicroagentMetadata,
    MicroagentType,
    load_microagents_from_dir,
)

logger = get_logger(__name__)


class MicroagentStore(ABC):
    """Abstract base class for microagent storage"""
    
    @abstractmethod
    async def get_builtin_microagents(self) -> List[BaseMicroagent]:
        """Get all built-in microagents"""
        pass
    
    @abstractmethod
    async def list_custom_microagents(self) -> List[BaseMicroagent]:
        """List custom microagents for the user"""
        pass
    
    @abstractmethod
    async def get_custom_microagent(self, name: str) -> Optional[BaseMicroagent]:
        """Get a specific custom microagent"""
        pass
    
    @abstractmethod
    async def create_custom_microagent(
        self,
        name: str,
        content: str,
        metadata: MicroagentMetadata,
        microagent_type: MicroagentType
    ) -> BaseMicroagent:
        """Create a new custom microagent"""
        pass
    
    @abstractmethod
    async def update_custom_microagent(
        self,
        name: str,
        new_name: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[MicroagentMetadata] = None
    ) -> BaseMicroagent:
        """Update a custom microagent"""
        pass
    
    @abstractmethod
    async def delete_custom_microagent(self, name: str) -> None:
        """Delete a custom microagent"""
        pass
    
    @abstractmethod
    async def search_microagents(
        self,
        query: str,
        microagent_type: Optional[MicroagentType] = None,
        include_builtin: bool = True
    ) -> List[BaseMicroagent]:
        """Search microagents by content or triggers"""
        pass


class FileMicroagentStore(MicroagentStore):
    """File-based microagent storage"""
    
    def __init__(self, user_id: str, base_path: str = "/tmp/openreplica/microagents"):
        self.user_id = user_id
        self.base_path = base_path
        self.user_path = os.path.join(base_path, user_id)
        self.custom_path = os.path.join(self.user_path, "custom")
        self.builtin_path = os.path.join(os.path.dirname(__file__), "builtin")
        
        # Ensure directories exist
        os.makedirs(self.custom_path, exist_ok=True)
        os.makedirs(self.builtin_path, exist_ok=True)
        
        # Initialize built-in microagents if not exists
        self._initialize_builtin_microagents()
    
    def _initialize_builtin_microagents(self):
        """Initialize built-in microagents"""
        builtin_agents = {
            "python_expert.md": {
                "metadata": {
                    "name": "python_expert",
                    "type": "knowledge",
                    "version": "1.0.0",
                    "agent": "CodeActAgent",
                    "triggers": ["python", "py", "django", "flask", "fastapi", "pandas", "numpy"]
                },
                "content": """# Python Expert Microagent

I am a Python expert microagent that provides guidance on Python best practices, common patterns, and troubleshooting.

## Python Best Practices

### Code Style
- Follow PEP 8 style guide
- Use meaningful variable and function names
- Keep functions small and focused
- Use type hints for better code documentation

### Common Patterns
- Use list comprehensions for simple transformations
- Use context managers (with statements) for resource management
- Prefer f-strings for string formatting
- Use dataclasses or Pydantic for data structures

### Testing
- Write unit tests with pytest
- Use mocks for external dependencies
- Aim for high test coverage
- Test edge cases and error conditions

### Performance
- Profile before optimizing
- Use appropriate data structures
- Consider using generators for large datasets
- Cache expensive computations when appropriate

## Common Issues
- IndentationError: Check for mixed tabs and spaces
- ModuleNotFoundError: Check your import paths and virtual environment
- AttributeError: Verify object types and available methods
- KeyError: Use dict.get() or check if key exists

## Debugging Tips
- Use print() statements for quick debugging
- Use pdb or ipdb for interactive debugging
- Check logs and error messages carefully
- Use IDE debugger for complex issues
"""
            },
            "web_development.md": {
                "metadata": {
                    "name": "web_development",
                    "type": "knowledge",
                    "version": "1.0.0",
                    "agent": "CodeActAgent",
                    "triggers": ["web", "html", "css", "javascript", "react", "vue", "angular", "frontend"]
                },
                "content": """# Web Development Microagent

I specialize in web development best practices, frameworks, and modern web technologies.

## Frontend Best Practices

### HTML
- Use semantic HTML elements
- Include proper meta tags
- Ensure accessibility with ARIA attributes
- Validate HTML markup

### CSS
- Use CSS Grid and Flexbox for layouts
- Follow BEM methodology for naming
- Use CSS custom properties (variables)
- Implement responsive design with mobile-first approach

### JavaScript
- Use modern ES6+ features
- Avoid global variables
- Use strict mode
- Handle errors properly with try-catch

## Framework Guidance

### React
- Use functional components with hooks
- Implement proper state management
- Use React.memo for performance optimization
- Follow component composition patterns

### Vue.js
- Use Vue 3 Composition API
- Implement proper reactive data
- Use computed properties for derived state
- Follow single-file component structure

### Angular
- Use TypeScript for type safety
- Implement dependency injection
- Use observables for async operations
- Follow Angular style guide

## Performance Tips
- Minimize HTTP requests
- Optimize images and assets
- Use CDN for static resources
- Implement lazy loading
- Bundle and minify code

## Security
- Validate all user inputs
- Use HTTPS everywhere
- Implement proper authentication
- Protect against XSS and CSRF attacks
"""
            },
            "devops_helper.md": {
                "metadata": {
                    "name": "devops_helper",
                    "type": "knowledge",
                    "version": "1.0.0",
                    "agent": "CodeActAgent",
                    "triggers": ["docker", "kubernetes", "aws", "azure", "gcp", "deployment", "ci/cd", "devops"]
                },
                "content": """# DevOps Helper Microagent

I provide guidance on DevOps practices, containerization, cloud platforms, and deployment strategies.

## Containerization

### Docker Best Practices
- Use multi-stage builds to reduce image size
- Run containers as non-root users
- Use .dockerignore to exclude unnecessary files
- Pin specific versions in base images
- Use COPY instead of ADD when possible

### Kubernetes
- Use namespaces for resource isolation
- Implement resource limits and requests
- Use ConfigMaps and Secrets for configuration
- Implement health checks and readiness probes
- Use Horizontal Pod Autoscaler for scaling

## CI/CD Pipeline

### Best Practices
- Automate everything
- Use infrastructure as code
- Implement proper testing stages
- Use feature flags for safer deployments
- Monitor deployment metrics

### Common Tools
- GitHub Actions for CI/CD
- Jenkins for complex pipelines
- GitLab CI for integrated workflows
- CircleCI for fast builds

## Cloud Platforms

### AWS
- Use IAM roles instead of access keys
- Implement proper VPC networking
- Use CloudFormation or Terraform for infrastructure
- Monitor with CloudWatch

### Azure
- Use Azure Resource Manager templates
- Implement proper network security groups
- Use Azure Monitor for observability
- Follow Azure Well-Architected Framework

### GCP
- Use Cloud Deployment Manager
- Implement proper IAM policies
- Use Cloud Monitoring and Logging
- Follow GCP best practices

## Monitoring & Observability
- Implement the three pillars: metrics, logs, traces
- Use Prometheus and Grafana for metrics
- Centralize logging with ELK stack
- Implement distributed tracing
- Set up proper alerting
"""
            },
            "database_expert.md": {
                "metadata": {
                    "name": "database_expert",
                    "type": "knowledge",
                    "version": "1.0.0",
                    "agent": "CodeActAgent",
                    "triggers": ["database", "sql", "mysql", "postgresql", "mongodb", "redis", "orm"]
                },
                "content": """# Database Expert Microagent

I provide expertise on database design, optimization, and best practices for various database systems.

## Database Design

### Relational Databases
- Normalize to 3NF but denormalize for performance when needed
- Use appropriate data types and constraints
- Design proper indexes for query performance
- Implement foreign key relationships
- Use transactions for data consistency

### NoSQL Databases
- Choose the right NoSQL type for your use case
- Design documents/collections for your query patterns
- Implement proper sharding strategies
- Consider consistency vs availability trade-offs

## SQL Best Practices

### Query Optimization
- Use EXPLAIN to analyze query plans
- Avoid N+1 query problems
- Use appropriate joins instead of subqueries when possible
- Limit result sets with proper WHERE clauses
- Use indexes effectively

### Common Patterns
```sql
-- Use EXISTS instead of IN for better performance
SELECT * FROM orders o 
WHERE EXISTS (SELECT 1 FROM customers c WHERE c.id = o.customer_id);

-- Use LIMIT for pagination
SELECT * FROM products ORDER BY created_at DESC LIMIT 20 OFFSET 40;

-- Use proper joins
SELECT p.name, c.name 
FROM products p 
INNER JOIN categories c ON p.category_id = c.id;
```

## Database-Specific Tips

### PostgreSQL
- Use JSONB for semi-structured data
- Implement proper connection pooling
- Use pg_stat_statements for query analysis
- Consider partitioning for large tables

### MySQL
- Choose appropriate storage engines (InnoDB vs MyISAM)
- Use proper character sets (utf8mb4)
- Implement query caching when appropriate
- Monitor slow query log

### MongoDB
- Design schemas for your query patterns
- Use appropriate indexes including compound indexes
- Implement proper aggregation pipelines
- Consider sharding for horizontal scaling

### Redis
- Use appropriate data structures for your use case
- Implement proper expiration policies
- Use Redis Cluster for high availability
- Monitor memory usage and performance

## Performance Optimization
- Monitor query performance regularly
- Implement proper indexing strategies
- Use connection pooling
- Consider read replicas for read-heavy workloads
- Implement caching layers appropriately
"""
            }
        }
        
        # Create built-in microagent files
        for filename, agent_data in builtin_agents.items():
            file_path = os.path.join(self.builtin_path, filename)
            if not os.path.exists(file_path):
                # Create frontmatter content
                import frontmatter
                post = frontmatter.Post(agent_data["content"], **agent_data["metadata"])
                content = frontmatter.dumps(post)
                
                with open(file_path, 'w') as f:
                    f.write(content)
    
    async def get_builtin_microagents(self) -> List[BaseMicroagent]:
        """Get all built-in microagents"""
        try:
            builtin_path = Path(self.builtin_path)
            if not builtin_path.exists():
                return []
            
            repo_agents, knowledge_agents = load_microagents_from_dir(builtin_path)
            
            # Combine all agents
            all_agents = []
            all_agents.extend(repo_agents.values())
            all_agents.extend(knowledge_agents.values())
            
            return all_agents
            
        except Exception as e:
            logger.error(f"Error loading built-in microagents: {e}")
            return []
    
    async def list_custom_microagents(self) -> List[BaseMicroagent]:
        """List custom microagents for the user"""
        try:
            custom_path = Path(self.custom_path)
            if not custom_path.exists():
                return []
            
            repo_agents, knowledge_agents = load_microagents_from_dir(custom_path)
            
            # Combine all agents and add timestamps
            all_agents = []
            for agent in list(repo_agents.values()) + list(knowledge_agents.values()):
                # Add creation/modification timestamps from file system
                file_path = Path(agent.source)
                if file_path.exists():
                    stat = file_path.stat()
                    agent.created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
                    agent.updated_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
                all_agents.append(agent)
            
            return all_agents
            
        except Exception as e:
            logger.error(f"Error listing custom microagents for user {self.user_id}: {e}")
            return []
    
    async def get_custom_microagent(self, name: str) -> Optional[BaseMicroagent]:
        """Get a specific custom microagent"""
        try:
            agents = await self.list_custom_microagents()
            for agent in agents:
                if agent.name == name:
                    return agent
            return None
            
        except Exception as e:
            logger.error(f"Error getting custom microagent {name}: {e}")
            return None
    
    async def create_custom_microagent(
        self,
        name: str,
        content: str,
        metadata: MicroagentMetadata,
        microagent_type: MicroagentType
    ) -> BaseMicroagent:
        """Create a new custom microagent"""
        try:
            # Ensure name is unique
            existing = await self.get_custom_microagent(name)
            if existing:
                raise ValueError(f"Microagent with name '{name}' already exists")
            
            # Create file path
            filename = f"{name}.md"
            file_path = os.path.join(self.custom_path, filename)
            
            # Create frontmatter content
            import frontmatter
            post = frontmatter.Post(content, **metadata.model_dump())
            markdown_content = frontmatter.dumps(post)
            
            # Write to file
            with open(file_path, 'w') as f:
                f.write(markdown_content)
            
            # Load the created agent
            agent = BaseMicroagent.load(file_path, Path(self.custom_path))
            
            # Add timestamps
            stat = os.stat(file_path)
            agent.created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
            agent.updated_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            logger.info(f"Created custom microagent '{name}' for user {self.user_id}")
            return agent
            
        except Exception as e:
            logger.error(f"Error creating custom microagent '{name}': {e}")
            raise
    
    async def update_custom_microagent(
        self,
        name: str,
        new_name: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[MicroagentMetadata] = None
    ) -> BaseMicroagent:
        """Update a custom microagent"""
        try:
            # Get existing agent
            existing_agent = await self.get_custom_microagent(name)
            if not existing_agent:
                raise ValueError(f"Microagent '{name}' not found")
            
            # Use existing values if not provided
            updated_name = new_name or name
            updated_content = content or existing_agent.content
            updated_metadata = metadata or existing_agent.metadata
            
            # If name changed, check uniqueness
            if new_name and new_name != name:
                name_conflict = await self.get_custom_microagent(new_name)
                if name_conflict:
                    raise ValueError(f"Microagent with name '{new_name}' already exists")
            
            # Delete old file if name changed
            old_file_path = existing_agent.source
            if new_name and new_name != name:
                os.remove(old_file_path)
            
            # Create new file
            filename = f"{updated_name}.md"
            file_path = os.path.join(self.custom_path, filename)
            
            # Create frontmatter content
            import frontmatter
            post = frontmatter.Post(updated_content, **updated_metadata.model_dump())
            markdown_content = frontmatter.dumps(post)
            
            # Write to file
            with open(file_path, 'w') as f:
                f.write(markdown_content)
            
            # Load the updated agent
            agent = BaseMicroagent.load(file_path, Path(self.custom_path))
            
            # Add timestamps
            stat = os.stat(file_path)
            agent.created_at = getattr(existing_agent, 'created_at', datetime.fromtimestamp(stat.st_ctime).isoformat())
            agent.updated_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            logger.info(f"Updated custom microagent '{name}' for user {self.user_id}")
            return agent
            
        except Exception as e:
            logger.error(f"Error updating custom microagent '{name}': {e}")
            raise
    
    async def delete_custom_microagent(self, name: str) -> None:
        """Delete a custom microagent"""
        try:
            agent = await self.get_custom_microagent(name)
            if not agent:
                raise ValueError(f"Microagent '{name}' not found")
            
            # Delete the file
            os.remove(agent.source)
            
            logger.info(f"Deleted custom microagent '{name}' for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Error deleting custom microagent '{name}': {e}")
            raise
    
    async def search_microagents(
        self,
        query: str,
        microagent_type: Optional[MicroagentType] = None,
        include_builtin: bool = True
    ) -> List[BaseMicroagent]:
        """Search microagents by content or triggers"""
        try:
            agents = []
            
            # Get custom agents
            custom_agents = await self.list_custom_microagents()
            agents.extend(custom_agents)
            
            # Get built-in agents if requested
            if include_builtin:
                builtin_agents = await self.get_builtin_microagents()
                agents.extend(builtin_agents)
            
            # Filter by type if specified
            if microagent_type:
                agents = [a for a in agents if a.type == microagent_type]
            
            # Search in content, name, and triggers
            query_lower = query.lower()
            matching_agents = []
            
            for agent in agents:
                # Search in name
                if query_lower in agent.name.lower():
                    matching_agents.append(agent)
                    continue
                
                # Search in content
                if query_lower in agent.content.lower():
                    matching_agents.append(agent)
                    continue
                
                # Search in triggers for knowledge agents
                if isinstance(agent, KnowledgeMicroagent):
                    if any(query_lower in trigger.lower() for trigger in agent.triggers):
                        matching_agents.append(agent)
                        continue
            
            return matching_agents
            
        except Exception as e:
            logger.error(f"Error searching microagents: {e}")
            return []


class MockMicroagentStore(MicroagentStore):
    """Mock microagent store for development"""
    
    _custom_agents: Dict[str, Dict[str, BaseMicroagent]] = {}
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        if user_id not in self._custom_agents:
            self._custom_agents[user_id] = {}
    
    async def get_builtin_microagents(self) -> List[BaseMicroagent]:
        """Get mock built-in microagents"""
        # Return empty list for mock
        return []
    
    async def list_custom_microagents(self) -> List[BaseMicroagent]:
        """List custom microagents for the user"""
        return list(self._custom_agents[self.user_id].values())
    
    async def get_custom_microagent(self, name: str) -> Optional[BaseMicroagent]:
        """Get a specific custom microagent"""
        return self._custom_agents[self.user_id].get(name)
    
    async def create_custom_microagent(
        self,
        name: str,
        content: str,
        metadata: MicroagentMetadata,
        microagent_type: MicroagentType
    ) -> BaseMicroagent:
        """Create a new custom microagent"""
        if name in self._custom_agents[self.user_id]:
            raise ValueError(f"Microagent with name '{name}' already exists")
        
        # Create agent based on type
        if microagent_type == MicroagentType.KNOWLEDGE:
            agent = KnowledgeMicroagent(
                name=name,
                content=content,
                metadata=metadata,
                source=f"mock://{name}.md",
                type=microagent_type
            )
        else:
            agent = RepoMicroagent(
                name=name,
                content=content,
                metadata=metadata,
                source=f"mock://{name}.md",
                type=microagent_type
            )
        
        # Add timestamps
        now = datetime.now().isoformat()
        agent.created_at = now
        agent.updated_at = now
        
        self._custom_agents[self.user_id][name] = agent
        return agent
    
    async def update_custom_microagent(
        self,
        name: str,
        new_name: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[MicroagentMetadata] = None
    ) -> BaseMicroagent:
        """Update a custom microagent"""
        if name not in self._custom_agents[self.user_id]:
            raise ValueError(f"Microagent '{name}' not found")
        
        agent = self._custom_agents[self.user_id][name]
        
        # Update fields
        if new_name:
            if new_name in self._custom_agents[self.user_id] and new_name != name:
                raise ValueError(f"Microagent with name '{new_name}' already exists")
            agent.name = new_name
        
        if content:
            agent.content = content
        
        if metadata:
            agent.metadata = metadata
        
        # Update timestamp
        agent.updated_at = datetime.now().isoformat()
        
        # If name changed, update the dictionary
        if new_name and new_name != name:
            del self._custom_agents[self.user_id][name]
            self._custom_agents[self.user_id][new_name] = agent
        
        return agent
    
    async def delete_custom_microagent(self, name: str) -> None:
        """Delete a custom microagent"""
        if name not in self._custom_agents[self.user_id]:
            raise ValueError(f"Microagent '{name}' not found")
        
        del self._custom_agents[self.user_id][name]
    
    async def search_microagents(
        self,
        query: str,
        microagent_type: Optional[MicroagentType] = None,
        include_builtin: bool = True
    ) -> List[BaseMicroagent]:
        """Search microagents by content or triggers"""
        agents = list(self._custom_agents[self.user_id].values())
        
        # Filter by type
        if microagent_type:
            agents = [a for a in agents if a.type == microagent_type]
        
        # Simple search
        query_lower = query.lower()
        return [a for a in agents if query_lower in a.name.lower() or query_lower in a.content.lower()]


def get_microagent_store(user_id: str, store_type: str = "file") -> MicroagentStore:
    """Factory function to get microagent store"""
    if store_type == "file":
        return FileMicroagentStore(user_id)
    elif store_type == "mock":
        return MockMicroagentStore(user_id)
    else:
        raise ValueError(f"Unknown store type: {store_type}")
