"""
Runtime system for OpenReplica
Handles code execution, Docker containers, and sandboxed environments
"""
from .base import Runtime, RuntimeConfig
from .docker.runtime import DockerRuntime
from .local.runtime import LocalRuntime

# Runtime registry
RUNTIME_REGISTRY = {
    "docker": DockerRuntime,
    "local": LocalRuntime,
}


def create_runtime(runtime_type: str, config: RuntimeConfig) -> Runtime:
    """Factory function to create runtime instances"""
    if runtime_type not in RUNTIME_REGISTRY:
        raise ValueError(f"Unknown runtime type: {runtime_type}")
    
    runtime_class = RUNTIME_REGISTRY[runtime_type]
    return runtime_class(config)


def get_available_runtimes() -> list[str]:
    """Get list of available runtime types"""
    return list(RUNTIME_REGISTRY.keys())


__all__ = [
    "Runtime",
    "RuntimeConfig",
    "DockerRuntime", 
    "LocalRuntime",
    "create_runtime",
    "get_available_runtimes",
    "RUNTIME_REGISTRY"
]
