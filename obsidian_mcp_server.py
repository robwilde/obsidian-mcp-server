#!/usr/bin/env python3
"""
MCP Server for saving Claude Code responses to Obsidian
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool


def get_project_config() -> Dict[str, Any]:
    """Get project-specific Obsidian configuration from .claude/obsidian.json"""
    try:
        # Look for .claude/obsidian.json in current directory and parents
        current_path = Path.cwd()
        
        for path in [current_path] + list(current_path.parents):
            config_file = path / ".claude" / "obsidian.json"
            if config_file.exists():
                with open(config_file, "r") as f:
                    return json.load(f)
        
        # Default configuration if no project config found
        return {
            "folder": "Claude Code",
            "templates": {
                "report": "# {title}\n\n**Generated:** {timestamp}\n**Project:** {project}\n\n{content}",
                "review": "# Code Review: {title}\n\n**Generated:** {timestamp}\n**Project:** {project}\n\n{content}",
                "note": "# {title}\n\n**Created:** {timestamp}\n**Project:** {project}\n\n{content}"
            }
        }
    except Exception:
        # Fallback to default
        return {
            "folder": "Claude Code",
            "templates": {
                "report": "# {title}\n\n**Generated:** {timestamp}\n**Project:** {project}\n\n{content}",
                "review": "# Code Review: {title}\n\n**Generated:** {timestamp}\n**Project:** {project}\n\n{content}",
                "note": "# {title}\n\n**Created:** {timestamp}\n**Project:** {project}\n\n{content}"
            }
        }


def get_vault_path() -> Path:
    """Get Obsidian vault path from environment or config"""
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
    if not vault_path:
        vault_path = os.path.expanduser("~/Documents/ObsidianVault")

    path = Path(vault_path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

    return path


def generate_frontmatter(tags: List[str]) -> str:
    """Generate YAML frontmatter for Obsidian note"""
    timestamp = datetime.now().isoformat()
    
    frontmatter = "---\n"
    frontmatter += f"created: {timestamp}\n"
    frontmatter += f"source: claude-code\n"
    frontmatter += f"tags: {tags}\n"
    frontmatter += "---\n\n"
    
    return frontmatter


# Create the server
server = Server("obsidian-claude-code")

@server.list_tools()
async def handle_list_tools():
    """List available tools."""
    return [
        Tool(
            name="save_to_obsidian",
            description="Save content to Obsidian using project configuration. Use this when Claude Code should save reports, reviews, or other content to the user's Obsidian vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The content to save"
                    },
                    "title": {
                        "type": "string",
                        "description": "Title for the document"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["report", "review", "note"],
                        "description": "Type of content (determines template)",
                        "default": "note"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional tags for the note",
                        "default": []
                    }
                },
                "required": ["content", "title"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """Handle tool calls."""
    if name == "save_to_obsidian":
        return await save_to_obsidian(
            arguments.get("content", ""),
            arguments.get("title", "Untitled"),
            arguments.get("type", "note"),
            arguments.get("tags", [])
        )
    else:
        raise ValueError(f"Unknown tool: {name}")


async def save_to_obsidian(content: str, title: str, content_type: str, tags: List[str]):
    """Save content to Obsidian using project configuration and templates"""
    try:
        # Get configuration and paths
        config = get_project_config()
        vault_path = get_vault_path()
        project_name = Path.cwd().name
        
        # Prepare template variables
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Select template based on content type
        template = config.get("templates", {}).get(content_type, "{content}")
        
        # Format content using template
        formatted_content = template.format(
            title=title,
            timestamp=timestamp,
            project=project_name,
            content=content
        )
        
        # Create filename (sanitize title for filesystem)
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        timestamp_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp_prefix}_{safe_title}.md"
        
        # Determine target folder
        project_folder = config.get("folder", "Claude Code")
        target_path = vault_path / project_folder
        
        # Ensure target folder exists
        target_path.mkdir(parents=True, exist_ok=True)
        
        # Create full file path
        file_path = target_path / filename
        
        # Combine all tags
        all_tags = ["claude-code", content_type, project_name.lower()] + tags
        
        # Generate frontmatter
        frontmatter = generate_frontmatter(all_tags)
        
        # Combine frontmatter and formatted content
        full_content = frontmatter + formatted_content
        
        # Write file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        return [
            {
                "type": "text",
                "text": f"Successfully saved {content_type} '{title}' to {file_path}\nProject: {project_name}\nFolder: {project_folder}"
            }
        ]
    except Exception as e:
        raise Exception(f"Failed to save to Obsidian: {str(e)}")


async def main():
    """Main entry point for the MCP server"""
    async with stdio_server() as streams:
        await server.run(
            streams[0], 
            streams[1], 
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())