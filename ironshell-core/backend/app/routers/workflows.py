"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    WORKFLOW ROUTER - N8N DOCUMENTATION API                   ║
║                                                                              ║
║  IRON SHELL EXTENSION:                                                       ║
║  High-performance API for workflow documentation with security features.     ║
║  Integrates with the Data Flywheel for workflow-based corrections.           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import re
import urllib.parse
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app.services.workflow_db import WorkflowDatabase

router = APIRouter()

# Initialize workflow database
workflow_db = WorkflowDatabase()

# Security: Rate limiting storage
rate_limit_storage = defaultdict(list)
MAX_REQUESTS_PER_MINUTE = 60


# ══════════════════════════════════════════════════════════════════════════════
# SECURITY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit."""
    current_time = time.time()
    rate_limit_storage[client_ip] = [
        ts for ts in rate_limit_storage[client_ip]
        if current_time - ts < 60
    ]
    if len(rate_limit_storage[client_ip]) >= MAX_REQUESTS_PER_MINUTE:
        return False
    rate_limit_storage[client_ip].append(current_time)
    return True


def validate_filename(filename: str) -> bool:
    """
    Validate filename to prevent path traversal attacks.

    IRON SHELL SECURITY:
    Multiple layers of validation to prevent directory traversal.
    """
    decoded = filename
    for _ in range(3):
        try:
            decoded = urllib.parse.unquote(decoded, errors="strict")
        except:
            return False

    dangerous_patterns = [
        "..", "..\\", "../", "\\", "/", "\x00", "\n", "\r",
        "~", ":", "|", "<", ">", "*", "?", "$", ";", "&"
    ]

    for pattern in dangerous_patterns:
        if pattern in decoded:
            return False

    if decoded.startswith("/") or decoded.startswith("\\"):
        return False

    if len(decoded) >= 2 and decoded[1] == ":":
        return False

    if not re.match(r"^[a-zA-Z0-9_\-]+\.json$", decoded):
        return False

    return True


# ══════════════════════════════════════════════════════════════════════════════
# RESPONSE MODELS
# ══════════════════════════════════════════════════════════════════════════════

class WorkflowSummary(BaseModel):
    """Summary of a workflow for list views."""
    id: Optional[int] = None
    filename: str
    name: str
    active: bool = False
    description: str = ""
    trigger_type: str = "Manual"
    complexity: str = "low"
    node_count: int = 0
    integrations: List[str] = []
    tags: List[str] = []
    category: str = "general"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator("active", mode="before")
    @classmethod
    def convert_active(cls, v):
        if isinstance(v, int):
            return bool(v)
        return v


class WorkflowSearchResponse(BaseModel):
    """Response for workflow search."""
    workflows: List[WorkflowSummary]
    total: int
    page: int
    per_page: int
    pages: int
    query: str
    filters: Dict[str, Any]


class WorkflowStatsResponse(BaseModel):
    """Statistics about the workflow database."""
    total: int
    active: int
    inactive: int
    triggers: Dict[str, int]
    complexity: Dict[str, int]
    total_nodes: int
    unique_integrations: int
    last_indexed: str


class WorkflowDetailResponse(BaseModel):
    """Detailed workflow with raw JSON."""
    metadata: WorkflowSummary
    raw_json: Dict[str, Any]
    diagram: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/stats", response_model=WorkflowStatsResponse)
async def get_workflow_stats():
    """
    Get workflow database statistics.

    IRON SHELL METRICS:
    Shows the scope of your workflow automation library.
    """
    try:
        stats = workflow_db.get_stats()
        return WorkflowStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@router.get("/", response_model=WorkflowSearchResponse)
async def search_workflows(
    q: str = Query("", description="Search query"),
    trigger: str = Query("all", description="Filter by trigger type"),
    complexity: str = Query("all", description="Filter by complexity"),
    category: str = Query("all", description="Filter by category"),
    active_only: bool = Query(False, description="Show only active workflows"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    Search and filter workflows with pagination.

    IRON SHELL INTEGRATION:
    Workflows can be linked to trading strategies for automated execution.
    """
    try:
        offset = (page - 1) * per_page

        if category and category != "all":
            workflows, total = workflow_db.search_by_category(
                category=category,
                limit=per_page,
                offset=offset
            )
        else:
            workflows, total = workflow_db.search_workflows(
                query=q,
                trigger_filter=trigger,
                complexity_filter=complexity,
                active_only=active_only,
                limit=per_page,
                offset=offset,
            )

        workflow_summaries = []
        for workflow in workflows:
            try:
                clean_workflow = {
                    "id": workflow.get("id"),
                    "filename": workflow.get("filename", ""),
                    "name": workflow.get("name", ""),
                    "active": workflow.get("active", False),
                    "description": workflow.get("description", ""),
                    "trigger_type": workflow.get("trigger_type", "Manual"),
                    "complexity": workflow.get("complexity", "low"),
                    "node_count": workflow.get("node_count", 0),
                    "integrations": workflow.get("integrations", []),
                    "tags": workflow.get("tags", []),
                    "category": workflow.get("category", "general"),
                    "created_at": workflow.get("created_at"),
                    "updated_at": workflow.get("updated_at"),
                }
                workflow_summaries.append(WorkflowSummary(**clean_workflow))
            except Exception as e:
                print(f"Error converting workflow: {e}")
                continue

        pages = (total + per_page - 1) // per_page

        return WorkflowSearchResponse(
            workflows=workflow_summaries,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            query=q,
            filters={
                "trigger": trigger,
                "complexity": complexity,
                "category": category,
                "active_only": active_only,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching workflows: {str(e)}")


@router.get("/categories")
async def get_categories():
    """Get available workflow categories."""
    try:
        categories = workflow_db.get_categories()
        return {"categories": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")


@router.get("/{filename}", response_model=WorkflowDetailResponse)
async def get_workflow_detail(filename: str, request: Request):
    """
    Get detailed workflow information including raw JSON.

    IRON SHELL SECURITY:
    Validates filename to prevent path traversal attacks.
    """
    if not validate_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid filename format")

    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    try:
        workflow = workflow_db.get_workflow_by_filename(filename)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Generate diagram
        raw_json = workflow.get("raw_json", {})
        diagram = generate_mermaid_diagram(
            raw_json.get("nodes", []),
            raw_json.get("connections", {})
        )

        metadata = WorkflowSummary(
            id=workflow.get("id"),
            filename=workflow.get("filename", ""),
            name=workflow.get("name", ""),
            active=workflow.get("active", False),
            description=workflow.get("description", ""),
            trigger_type=workflow.get("trigger_type", "Manual"),
            complexity=workflow.get("complexity", "low"),
            node_count=workflow.get("node_count", 0),
            integrations=workflow.get("integrations", []),
            tags=workflow.get("tags", []),
            category=workflow.get("category", "general"),
        )

        return WorkflowDetailResponse(
            metadata=metadata,
            raw_json=raw_json,
            diagram=diagram
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading workflow: {str(e)}")


@router.get("/{filename}/diagram")
async def get_workflow_diagram(filename: str, request: Request):
    """Get Mermaid diagram code for workflow visualization."""
    if not validate_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid filename format")

    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    try:
        workflow = workflow_db.get_workflow_by_filename(filename)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        raw_json = workflow.get("raw_json", {})
        diagram = generate_mermaid_diagram(
            raw_json.get("nodes", []),
            raw_json.get("connections", {})
        )

        return {"diagram": diagram, "filename": filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating diagram: {str(e)}")


@router.get("/{filename}/download")
async def download_workflow(filename: str, request: Request):
    """Download workflow JSON file."""
    if not validate_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid filename format")

    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    try:
        workflow = workflow_db.get_workflow_by_filename(filename)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Return raw JSON as downloadable file
        raw_json = workflow.get("raw_json", {})
        return {
            "filename": filename,
            "content": raw_json
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading workflow: {str(e)}")


@router.post("/reindex")
async def reindex_workflows(
    background_tasks: BackgroundTasks,
    request: Request,
    force: bool = False,
    admin_token: Optional[str] = Query(None, description="Admin authentication token"),
):
    """
    Trigger workflow reindexing in the background.

    IRON SHELL SECURITY:
    Requires admin token to prevent abuse.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    expected_token = os.environ.get("ADMIN_TOKEN")
    if not expected_token:
        raise HTTPException(
            status_code=503,
            detail="Reindexing disabled. Set ADMIN_TOKEN to enable."
        )

    if admin_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    def run_indexing():
        try:
            workflow_db.index_all_workflows(force_reindex=force)
            print(f"Reindexing completed (requested by {client_ip})")
        except Exception as e:
            print(f"Error during reindexing: {e}")

    background_tasks.add_task(run_indexing)
    return {"message": "Reindexing started", "requested_by": client_ip}


@router.post("/import")
async def import_workflow(
    workflow_data: Dict[str, Any],
    filename: Optional[str] = None,
    request: Request = None,
):
    """
    Import a workflow into the database.

    IRON SHELL INTEGRATION:
    Allows adding custom trading automation workflows.
    """
    if request:
        client_ip = request.client.host if request.client else "unknown"
        if not check_rate_limit(client_ip):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    try:
        # Generate filename if not provided
        if not filename:
            name = workflow_data.get("name", "workflow")
            filename = f"{name.lower().replace(' ', '_')}.json"

        # Index the workflow
        success = workflow_db.index_workflow(workflow_data, filename)
        if success:
            return {
                "success": True,
                "message": f"Workflow '{filename}' imported successfully",
                "filename": filename
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to import workflow")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing workflow: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# MERMAID DIAGRAM GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def generate_mermaid_diagram(nodes: List[Dict], connections: Dict) -> str:
    """
    Generate Mermaid.js flowchart code from workflow nodes and connections.

    IRON SHELL VISUALIZATION:
    Creates visual diagrams for workflow documentation.
    """
    if not nodes:
        return "graph TD\n  EmptyWorkflow[No nodes found]"

    # Create mapping for node names to valid mermaid IDs
    mermaid_ids = {}
    for i, node in enumerate(nodes):
        node_id = f"node{i}"
        node_name = node.get("name", f"Node {i}")
        mermaid_ids[node_name] = node_id

    mermaid_code = ["graph TD"]

    # Add nodes with styling
    for node in nodes:
        node_name = node.get("name", "Unnamed")
        node_id = mermaid_ids[node_name]
        node_type = node.get("type", "").replace("n8n-nodes-base.", "")

        # Determine node style based on type
        if any(x in node_type.lower() for x in ["trigger", "webhook", "cron"]):
            style = "fill:#b3e0ff,stroke:#0066cc"
        elif any(x in node_type.lower() for x in ["if", "switch"]):
            style = "fill:#ffffb3,stroke:#e6e600"
        elif any(x in node_type.lower() for x in ["function", "code"]):
            style = "fill:#d9b3ff,stroke:#6600cc"
        elif "error" in node_type.lower():
            style = "fill:#ffb3b3,stroke:#cc0000"
        else:
            style = "fill:#d9d9d9,stroke:#666666"

        clean_name = node_name.replace('"', "'")
        clean_type = node_type.replace('"', "'")
        label = f"{clean_name}<br>({clean_type})"
        mermaid_code.append(f'  {node_id}["{label}"]')
        mermaid_code.append(f"  style {node_id} {style}")

    # Add connections
    for source_name, source_connections in connections.items():
        if source_name not in mermaid_ids:
            continue

        if isinstance(source_connections, dict) and "main" in source_connections:
            main_connections = source_connections["main"]

            for i, output_connections in enumerate(main_connections):
                if not isinstance(output_connections, list):
                    continue

                for connection in output_connections:
                    if not isinstance(connection, dict) or "node" not in connection:
                        continue

                    target_name = connection["node"]
                    if target_name not in mermaid_ids:
                        continue

                    label = f" -->|{i}| " if len(main_connections) > 1 else " --> "
                    mermaid_code.append(
                        f"  {mermaid_ids[source_name]}{label}{mermaid_ids[target_name]}"
                    )

    return "\n".join(mermaid_code)
