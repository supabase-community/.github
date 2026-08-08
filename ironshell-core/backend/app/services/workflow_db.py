"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    WORKFLOW DATABASE - N8N INTEGRATION                       ║
║                                                                              ║
║  IRON SHELL EXTENSION:                                                       ║
║  Adds workflow automation documentation and management capabilities.         ║
║  Workflows can be linked to trading strategies for automated execution.      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
import re


class WorkflowDatabase:
    """
    SQLite-based database for workflow documentation and search.

    IRON SHELL INTEGRATION:
    - Stores N8N workflow metadata for fast searching
    - Enables workflow categorization and tagging
    - Supports full-text search across workflow descriptions
    - Tracks workflow complexity and integrations
    """

    def __init__(self, db_path: str = "data/workflows.db"):
        """Initialize the workflow database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Main workflows table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    active INTEGER DEFAULT 0,
                    trigger_type TEXT DEFAULT 'Manual',
                    complexity TEXT DEFAULT 'low',
                    node_count INTEGER DEFAULT 0,
                    integrations TEXT DEFAULT '[]',
                    tags TEXT DEFAULT '[]',
                    category TEXT DEFAULT 'Uncategorized',
                    raw_json TEXT,
                    file_hash TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    indexed_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Full-text search table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS workflows_fts USING fts5(
                    filename,
                    name,
                    description,
                    integrations,
                    tags,
                    content='workflows',
                    content_rowid='id'
                )
            """)

            # Triggers to keep FTS in sync
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS workflows_ai AFTER INSERT ON workflows BEGIN
                    INSERT INTO workflows_fts(rowid, filename, name, description, integrations, tags)
                    VALUES (new.id, new.filename, new.name, new.description, new.integrations, new.tags);
                END
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS workflows_ad AFTER DELETE ON workflows BEGIN
                    INSERT INTO workflows_fts(workflows_fts, rowid, filename, name, description, integrations, tags)
                    VALUES ('delete', old.id, old.filename, old.name, old.description, old.integrations, old.tags);
                END
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS workflows_au AFTER UPDATE ON workflows BEGIN
                    INSERT INTO workflows_fts(workflows_fts, rowid, filename, name, description, integrations, tags)
                    VALUES ('delete', old.id, old.filename, old.name, old.description, old.integrations, old.tags);
                    INSERT INTO workflows_fts(rowid, filename, name, description, integrations, tags)
                    VALUES (new.id, new.filename, new.name, new.description, new.integrations, new.tags);
                END
            """)

            # Indexes for faster queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_trigger ON workflows(trigger_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_complexity ON workflows(complexity)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_active ON workflows(active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_category ON workflows(category)")

            conn.commit()

    def index_workflow(self, workflow_data: Dict[str, Any], filename: str) -> bool:
        """
        Index a single workflow into the database.

        IRON SHELL NOTE:
        Workflow indexing extracts metadata for fast searching while
        storing the full JSON for detailed views.
        """
        try:
            # Extract metadata
            name = workflow_data.get("name", filename.replace(".json", ""))
            nodes = workflow_data.get("nodes", [])
            connections = workflow_data.get("connections", {})

            # Determine trigger type
            trigger_type = self._detect_trigger_type(nodes)

            # Calculate complexity
            complexity = self._calculate_complexity(nodes, connections)

            # Extract integrations
            integrations = self._extract_integrations(nodes)

            # Extract tags from workflow settings or generate from integrations
            tags = workflow_data.get("tags", [])
            if not tags:
                tags = self._generate_tags(nodes, name)

            # Build description
            description = workflow_data.get("description", "")
            if not description:
                description = self._generate_description(name, nodes, trigger_type)

            # Determine category
            category = self._determine_category(integrations, trigger_type)

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO workflows
                    (filename, name, description, active, trigger_type, complexity,
                     node_count, integrations, tags, category, raw_json, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    filename,
                    name,
                    description,
                    1 if workflow_data.get("active", False) else 0,
                    trigger_type,
                    complexity,
                    len(nodes),
                    json.dumps(integrations),
                    json.dumps(tags),
                    category,
                    json.dumps(workflow_data),
                    datetime.utcnow().isoformat()
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error indexing workflow {filename}: {e}")
            return False

    def _detect_trigger_type(self, nodes: List[Dict]) -> str:
        """Detect the trigger type from workflow nodes."""
        trigger_keywords = {
            "webhook": "Webhook",
            "cron": "Schedule",
            "schedule": "Schedule",
            "trigger": "Trigger",
            "manual": "Manual",
            "start": "Manual",
            "email": "Email",
            "http": "HTTP",
            "mqtt": "MQTT",
            "kafka": "Kafka",
        }

        for node in nodes:
            node_type = node.get("type", "").lower()
            for keyword, trigger in trigger_keywords.items():
                if keyword in node_type:
                    return trigger

        return "Manual"

    def _calculate_complexity(self, nodes: List[Dict], connections: Dict) -> str:
        """Calculate workflow complexity based on structure."""
        node_count = len(nodes)
        connection_count = sum(
            len(conns.get("main", [[]])[0]) if isinstance(conns, dict) else 0
            for conns in connections.values()
        )

        # Check for conditional logic
        has_conditionals = any(
            any(kw in node.get("type", "").lower() for kw in ["if", "switch", "filter"])
            for node in nodes
        )

        # Check for loops
        has_loops = any(
            any(kw in node.get("type", "").lower() for kw in ["loop", "splitinbatches"])
            for node in nodes
        )

        # Calculate score
        score = node_count + (connection_count * 0.5)
        if has_conditionals:
            score += 5
        if has_loops:
            score += 10

        if score <= 5:
            return "low"
        elif score <= 15:
            return "medium"
        elif score <= 30:
            return "high"
        else:
            return "enterprise"

    def _extract_integrations(self, nodes: List[Dict]) -> List[str]:
        """Extract unique integrations from workflow nodes."""
        integrations = set()

        for node in nodes:
            node_type = node.get("type", "")
            # Clean up node type to get integration name
            if "n8n-nodes-base." in node_type:
                integration = node_type.replace("n8n-nodes-base.", "")
                integrations.add(integration)
            elif node_type:
                integrations.add(node_type)

        return sorted(list(integrations))

    def _generate_tags(self, nodes: List[Dict], name: str) -> List[str]:
        """Generate tags from workflow content."""
        tags = set()

        # Extract from node types
        for node in nodes:
            node_type = node.get("type", "").lower()
            if "http" in node_type:
                tags.add("api")
            if "database" in node_type or "postgres" in node_type or "mysql" in node_type:
                tags.add("database")
            if "email" in node_type or "gmail" in node_type:
                tags.add("email")
            if "slack" in node_type or "discord" in node_type or "telegram" in node_type:
                tags.add("messaging")
            if "ai" in node_type or "openai" in node_type or "llm" in node_type:
                tags.add("ai")

        # Extract from name
        name_lower = name.lower()
        if "sync" in name_lower:
            tags.add("sync")
        if "backup" in name_lower:
            tags.add("backup")
        if "notification" in name_lower or "alert" in name_lower:
            tags.add("notification")

        return sorted(list(tags))

    def _generate_description(self, name: str, nodes: List[Dict], trigger_type: str) -> str:
        """Generate a description from workflow metadata."""
        integrations = self._extract_integrations(nodes)[:3]

        description = f"Workflow '{name}' with {len(nodes)} nodes. "
        description += f"Triggered by: {trigger_type}. "
        if integrations:
            description += f"Uses: {', '.join(integrations)}."

        return description

    def _determine_category(self, integrations: List[str], trigger_type: str) -> str:
        """Determine workflow category based on integrations."""
        category_keywords = {
            "messaging": ["slack", "discord", "telegram", "teams", "mattermost"],
            "database": ["postgres", "mysql", "mongodb", "redis", "supabase"],
            "ai_ml": ["openai", "anthropic", "huggingface", "langchain"],
            "email": ["gmail", "outlook", "sendgrid", "mailchimp"],
            "crm": ["salesforce", "hubspot", "pipedrive", "zoho"],
            "devops": ["github", "gitlab", "jenkins", "docker", "kubernetes"],
            "ecommerce": ["shopify", "woocommerce", "stripe", "paypal"],
            "productivity": ["notion", "airtable", "asana", "trello", "jira"],
            "social": ["twitter", "facebook", "linkedin", "instagram"],
            "storage": ["s3", "dropbox", "google drive", "onedrive"],
        }

        integrations_lower = [i.lower() for i in integrations]

        for category, keywords in category_keywords.items():
            if any(kw in " ".join(integrations_lower) for kw in keywords):
                return category

        if trigger_type == "Webhook":
            return "api"
        elif trigger_type == "Schedule":
            return "automation"

        return "general"

    def index_all_workflows(self, workflows_dir: str = "data/workflows", force_reindex: bool = False):
        """Index all workflows from a directory."""
        workflows_path = Path(workflows_dir)
        if not workflows_path.exists():
            print(f"Workflows directory not found: {workflows_path}")
            return

        indexed = 0
        errors = 0

        for json_file in workflows_path.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    workflow_data = json.load(f)

                if self.index_workflow(workflow_data, json_file.name):
                    indexed += 1
                else:
                    errors += 1
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                errors += 1

        print(f"Indexed {indexed} workflows, {errors} errors")

    def search_workflows(
        self,
        query: str = "",
        trigger_filter: str = "all",
        complexity_filter: str = "all",
        active_only: bool = False,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search workflows with filtering and pagination.

        Returns tuple of (workflows, total_count)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Build WHERE clause
            conditions = []
            params = []

            if query:
                # Check for special search syntax
                if query.startswith('filename:'):
                    filename = query.replace('filename:', '').strip('"\'')
                    conditions.append("filename = ?")
                    params.append(filename)
                else:
                    # Full-text search
                    conditions.append("id IN (SELECT rowid FROM workflows_fts WHERE workflows_fts MATCH ?)")
                    params.append(query)

            if trigger_filter and trigger_filter != "all":
                conditions.append("trigger_type = ?")
                params.append(trigger_filter)

            if complexity_filter and complexity_filter != "all":
                conditions.append("complexity = ?")
                params.append(complexity_filter)

            if active_only:
                conditions.append("active = 1")

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Get total count
            count_query = f"SELECT COUNT(*) FROM workflows WHERE {where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # Get paginated results
            select_query = f"""
                SELECT id, filename, name, description, active, trigger_type,
                       complexity, node_count, integrations, tags, category,
                       created_at, updated_at
                FROM workflows
                WHERE {where_clause}
                ORDER BY name
                LIMIT ? OFFSET ?
            """
            cursor.execute(select_query, params + [limit, offset])

            workflows = []
            for row in cursor.fetchall():
                workflow = dict(row)
                # Parse JSON fields
                workflow["integrations"] = json.loads(workflow.get("integrations", "[]"))
                workflow["tags"] = json.loads(workflow.get("tags", "[]"))
                workflows.append(workflow)

            return workflows, total

    def search_by_category(
        self,
        category: str,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Search workflows by category."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get total count
            cursor.execute("SELECT COUNT(*) FROM workflows WHERE category = ?", (category,))
            total = cursor.fetchone()[0]

            # Get paginated results
            cursor.execute("""
                SELECT id, filename, name, description, active, trigger_type,
                       complexity, node_count, integrations, tags, category,
                       created_at, updated_at
                FROM workflows
                WHERE category = ?
                ORDER BY name
                LIMIT ? OFFSET ?
            """, (category, limit, offset))

            workflows = []
            for row in cursor.fetchall():
                workflow = dict(row)
                workflow["integrations"] = json.loads(workflow.get("integrations", "[]"))
                workflow["tags"] = json.loads(workflow.get("tags", "[]"))
                workflows.append(workflow)

            return workflows, total

    def get_workflow_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get a single workflow by filename."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM workflows WHERE filename = ?
            """, (filename,))

            row = cursor.fetchone()
            if row:
                workflow = dict(row)
                workflow["integrations"] = json.loads(workflow.get("integrations", "[]"))
                workflow["tags"] = json.loads(workflow.get("tags", "[]"))
                if workflow.get("raw_json"):
                    workflow["raw_json"] = json.loads(workflow["raw_json"])
                return workflow
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Total workflows
            cursor.execute("SELECT COUNT(*) FROM workflows")
            total = cursor.fetchone()[0]

            # Active/Inactive
            cursor.execute("SELECT COUNT(*) FROM workflows WHERE active = 1")
            active = cursor.fetchone()[0]

            # By trigger type
            cursor.execute("SELECT trigger_type, COUNT(*) FROM workflows GROUP BY trigger_type")
            triggers = dict(cursor.fetchall())

            # By complexity
            cursor.execute("SELECT complexity, COUNT(*) FROM workflows GROUP BY complexity")
            complexity = dict(cursor.fetchall())

            # Total nodes
            cursor.execute("SELECT SUM(node_count) FROM workflows")
            total_nodes = cursor.fetchone()[0] or 0

            # Unique integrations
            cursor.execute("SELECT integrations FROM workflows")
            all_integrations = set()
            for row in cursor.fetchall():
                integrations = json.loads(row[0] or "[]")
                all_integrations.update(integrations)

            # Last indexed
            cursor.execute("SELECT MAX(indexed_at) FROM workflows")
            last_indexed = cursor.fetchone()[0] or "Never"

            return {
                "total": total,
                "active": active,
                "inactive": total - active,
                "triggers": triggers,
                "complexity": complexity,
                "total_nodes": total_nodes,
                "unique_integrations": len(all_integrations),
                "last_indexed": last_indexed
            }

    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM workflows ORDER BY category")
            return [row[0] for row in cursor.fetchall()]

    def delete_workflow(self, filename: str) -> bool:
        """Delete a workflow by filename."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM workflows WHERE filename = ?", (filename,))
            conn.commit()
            return cursor.rowcount > 0
