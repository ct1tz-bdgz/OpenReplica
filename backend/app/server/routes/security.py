"""
Security routes for OpenReplica matching OpenHands exactly
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from app.core.logging import get_logger
from app.server.dependencies import get_dependencies
from app.server.user_auth import get_user_id

logger = get_logger(__name__)

app = APIRouter(prefix='/api/security', dependencies=get_dependencies())


class SecurityScanRequest(BaseModel):
    """Request model for security scan"""
    file_path: str
    scan_type: str = "all"  # "all", "secrets", "vulnerabilities", "permissions"


class SecurityRule(BaseModel):
    """Security rule model"""
    id: str
    name: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    enabled: bool


@app.post('/scan/file')
async def scan_file_security(
    request: SecurityScanRequest,
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Scan a file for security issues"""
    try:
        # Mock security scan - in real implementation, use security scanning tools
        logger.info(f"Scanning file {request.file_path} for user {user_id}")
        
        scan_results = {
            "file_path": request.file_path,
            "scan_type": request.scan_type,
            "scan_completed": True,
            "issues": [
                {
                    "id": "SEC001",
                    "type": "secret_exposure",
                    "severity": "high",
                    "line": 42,
                    "message": "Potential API key hardcoded in source code",
                    "recommendation": "Move sensitive data to environment variables"
                }
            ],
            "summary": {
                "total_issues": 1,
                "critical": 0,
                "high": 1,
                "medium": 0,
                "low": 0
            }
        }
        
        return JSONResponse(scan_results)
        
    except Exception as e:
        logger.error(f"Error scanning file for security: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Security scan failed: {e}"}
        )


@app.post('/scan/workspace')
async def scan_workspace_security(
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Scan entire workspace for security issues"""
    try:
        # Mock workspace security scan
        logger.info(f"Scanning workspace for user {user_id}")
        
        scan_results = {
            "scan_completed": True,
            "files_scanned": 15,
            "total_issues": 3,
            "issues_by_file": {
                "app.py": [
                    {
                        "id": "SEC001",
                        "type": "secret_exposure",
                        "severity": "high",
                        "line": 42,
                        "message": "Potential API key hardcoded"
                    }
                ],
                "config.py": [
                    {
                        "id": "SEC002", 
                        "type": "insecure_configuration",
                        "severity": "medium",
                        "line": 15,
                        "message": "Debug mode enabled in production"
                    }
                ]
            },
            "summary": {
                "critical": 0,
                "high": 1,
                "medium": 2,
                "low": 0
            }
        }
        
        return JSONResponse(scan_results)
        
    except Exception as e:
        logger.error(f"Error scanning workspace for security: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Workspace security scan failed: {e}"}
        )


@app.get('/rules')
async def get_security_rules(
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Get security scanning rules"""
    try:
        # Mock security rules
        rules = [
            SecurityRule(
                id="SEC001",
                name="Secret Detection",
                description="Detect hardcoded secrets like API keys, passwords",
                severity="high",
                enabled=True
            ),
            SecurityRule(
                id="SEC002",
                name="Insecure Configuration",
                description="Detect insecure configuration settings",
                severity="medium", 
                enabled=True
            ),
            SecurityRule(
                id="SEC003",
                name="Dependency Vulnerabilities",
                description="Check for known vulnerabilities in dependencies",
                severity="high",
                enabled=True
            ),
            SecurityRule(
                id="SEC004",
                name="File Permissions",
                description="Check for overly permissive file permissions",
                severity="low",
                enabled=True
            )
        ]
        
        return JSONResponse({
            "rules": [rule.model_dump() for rule in rules],
            "total": len(rules),
            "enabled": sum(1 for rule in rules if rule.enabled)
        })
        
    except Exception as e:
        logger.error(f"Error getting security rules: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get security rules: {e}"}
        )


@app.put('/rules/{rule_id}')
async def update_security_rule(
    rule_id: str,
    rule_update: Dict[str, Any],
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Update a security rule"""
    try:
        # Mock rule update
        logger.info(f"Updating security rule {rule_id} for user {user_id}")
        
        return JSONResponse({
            "success": True,
            "message": f"Security rule {rule_id} updated successfully",
            "rule_id": rule_id,
            "updated_fields": list(rule_update.keys())
        })
        
    except Exception as e:
        logger.error(f"Error updating security rule: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to update security rule: {e}"}
        )


@app.get('/report')
async def get_security_report(
    user_id: str = Depends(get_user_id),
    days: int = 7
) -> JSONResponse:
    """Get security report for the specified time period"""
    try:
        # Mock security report
        report = {
            "period": f"Last {days} days",
            "scans_performed": 5,
            "total_issues_found": 12,
            "issues_resolved": 8,
            "trending": {
                "most_common_issue": "secret_exposure",
                "files_with_most_issues": ["app.py", "config.py"],
                "severity_distribution": {
                    "critical": 0,
                    "high": 3,
                    "medium": 6,
                    "low": 3
                }
            },
            "recommendations": [
                "Review hardcoded secrets in configuration files",
                "Update dependencies with known vulnerabilities",
                "Implement proper input validation"
            ]
        }
        
        return JSONResponse(report)
        
    except Exception as e:
        logger.error(f"Error getting security report: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get security report: {e}"}
        )


@app.post('/whitelist/add')
async def add_security_whitelist(
    whitelist_entry: Dict[str, str],
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Add an entry to security whitelist"""
    try:
        rule_id = whitelist_entry.get("rule_id")
        file_path = whitelist_entry.get("file_path")
        reason = whitelist_entry.get("reason", "")
        
        if not rule_id or not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rule_id and file_path are required"
            )
        
        # Mock whitelist addition
        logger.info(f"Adding security whitelist entry for user {user_id}")
        
        return JSONResponse({
            "success": True,
            "message": "Security whitelist entry added successfully",
            "entry": {
                "rule_id": rule_id,
                "file_path": file_path,
                "reason": reason,
                "added_by": user_id
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding security whitelist: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to add whitelist entry: {e}"}
        )


@app.get('/whitelist')
async def get_security_whitelist(
    user_id: str = Depends(get_user_id)
) -> JSONResponse:
    """Get security whitelist entries"""
    try:
        # Mock whitelist entries
        whitelist = [
            {
                "id": "wl001",
                "rule_id": "SEC001",
                "file_path": "tests/test_config.py",
                "reason": "Test file with mock API keys",
                "added_by": user_id,
                "added_at": "2024-01-01T12:00:00Z"
            }
        ]
        
        return JSONResponse({
            "whitelist": whitelist,
            "total": len(whitelist)
        })
        
    except Exception as e:
        logger.error(f"Error getting security whitelist: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get whitelist: {e}"}
        )
