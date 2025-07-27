#!/usr/bin/env python3
"""
MCP Server for saving Claude Code responses to Obsidian
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import McpServer, Tool
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
)
from mcp.server.stdio import stdio_server


class ObsidianMCPServer:
    def __init__(self):
        self.server_name = "obsidian-claude-code"
        self.obsidian_vault_path = self._get_vault_path()
        self.server = McpServer(self.server_name)
        self._register_tools()
    
    def _get_project_config(self) -> Dict[str, Any]:
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
                    "report": "## {title}\n\n**Generated:** {timestamp}\n**Project:** {project}\n\n{content}",
                    "review": "## Code Review: {title}\n\n**Generated:** {timestamp}\n**Project:** {project}\n\n{content}"
                }
            }
        except Exception:
            # Fallback to default
            return {
                "folder": "Claude Code",
                "templates": {
                    "report": "## {title}\n\n**Generated:** {timestamp}\n**Project:** {project}\n\n{content}",
                    "review": "## Code Review: {title}\n\n**Generated:** {timestamp}\n**Project:** {project}\n\n{content}"
                }
            }
    
    def _get_vault_path(self) -> Path:
        """Get Obsidian vault path from environment or config"""
        vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
        if not vault_path:
            vault_path = os.path.expanduser("~/Documents/ObsidianVault")

        path = Path(vault_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        return path
    
    def _generate_frontmatter(self, tags: List[str]) -> str:
        """Generate YAML frontmatter for Obsidian note"""
        timestamp = datetime.now().isoformat()
        
        frontmatter = "---\n"
        frontmatter += f"created: {timestamp}\n"
        frontmatter += f"source: claude-code\n"
        frontmatter += f"tags: {tags}\n"
        frontmatter += "---\n\n"
        
        return frontmatter
    
    def _register_tools(self):
        """Register MCP tools"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            return ListToolsResult(
                tools=[
                    Tool(
                        name="save_claude_response",
                        description="Save Claude Code response to Obsidian vault",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "The response content to save"
                                },
                                "filename": {
                                    "type": "string",
                                    "description": "Filename for the note (without .md extension)"
                                },
                                "tags": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Tags to add to the note",
                                    "default": ["claude-code"]
                                }
                            },
                            "required": ["content", "filename"]
                        }
                    ),
                    Tool(
                        name="list_vault_files",
                        description="List files in the Obsidian vault",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "folder": {
                                    "type": "string",
                                    "description": "Folder to list (optional, defaults to root)",
                                    "default": ""
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Maximum number of files to return",
                                    "default": 50
                                }
                            }
                        }
                    ),
                    Tool(
                        name="get_vault_structure",
                        description="Get the folder structure of the Obsidian vault",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "max_depth": {
                                    "type": "integer",
                                    "description": "Maximum depth to traverse",
                                    "default": 3
                                }
                            }
                        }
                    ),
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
            )
        
        @self.server.call_tool()
        async def handle_call_tool(request: CallToolRequest) -> CallToolResult:
            try:
                if request.params.name == "save_claude_response":
                    return await self._save_claude_response(
                        request.params.arguments.get("content"),
                        request.params.arguments.get("filename"),
                        request.params.arguments.get("tags", ["claude-code"])
                    )
                elif request.params.name == "list_vault_files":
                    return await self._list_vault_files(
                        request.params.arguments.get("folder", ""),
                        request.params.arguments.get("limit", 50)
                    )
                elif request.params.name == "get_vault_structure":
                    return await self._get_vault_structure(
                        request.params.arguments.get("max_depth", 3)
                    )
                elif request.params.name == "save_to_obsidian":
                    return await self._save_to_obsidian(
                        request.params.arguments.get("content"),
                        request.params.arguments.get("title"),
                        request.params.arguments.get("type", "note"),
                        request.params.arguments.get("tags", [])
                    )
                else:
                    raise ValueError(f"Unknown tool: {request.params.name}")
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )
    
    async def _save_claude_response(self, content: str, filename: str, tags: List[str]) -> CallToolResult:
        """Save Claude response to Obsidian vault"""
        try:
            # Ensure filename ends with .md
            if not filename.endswith(".md"):
                filename += ".md"
            
            # Create full file path
            file_path = self.obsidian_vault_path / filename
            
            # Generate frontmatter
            frontmatter = self._generate_frontmatter(tags)
            
            # Combine frontmatter and content
            full_content = frontmatter + content
            
            # Write file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_content)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Successfully saved response to {file_path}"
                )]
            )
        except Exception as e:
            raise Exception(f"Failed to save response: {str(e)}")
    
    async def _list_vault_files(self, folder: str, limit: int) -> CallToolResult:
        """List files in vault folder"""
        try:
            search_path = self.obsidian_vault_path
            if folder:
                search_path = search_path / folder
            
            if not search_path.exists():
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Folder not found: {search_path}"
                    )]
                )
            
            files = []
            for file_path in search_path.rglob("*.md"):
                if len(files) >= limit:
                    break
                relative_path = file_path.relative_to(self.obsidian_vault_path)
                files.append(str(relative_path))
            
            files_text = "\n".join(files) if files else "No markdown files found"
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Files in vault ({len(files)} found):\n{files_text}"
                )]
            )
        except Exception as e:
            raise Exception(f"Failed to list files: {str(e)}")
    
    async def _get_vault_structure(self, max_depth: int) -> CallToolResult:
        """Get vault folder structure"""
        try:
            def build_tree(path: Path, current_depth: int = 0, prefix: str = "") -> str:
                if current_depth > max_depth:
                    return ""
                
                result = ""
                if path.is_dir():
                    items = sorted([p for p in path.iterdir() if p.is_dir() or p.suffix == ".md"])
                    for i, item in enumerate(items):
                        is_last = i == len(items) - 1
                        current_prefix = "└── " if is_last else "├── "
                        result += f"{prefix}{current_prefix}{item.name}\n"
                        
                        if item.is_dir() and current_depth < max_depth:
                            next_prefix = prefix + ("    " if is_last else "│   ")
                            result += build_tree(item, current_depth + 1, next_prefix)
                
                return result
            
            structure = f"{self.obsidian_vault_path.name}/\n"
            structure += build_tree(self.obsidian_vault_path, 0)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Vault structure:\n{structure}"
                )]
            )
        except Exception as e:
            raise Exception(f"Failed to get vault structure: {str(e)}")
    
    async def _save_to_obsidian(self, content: str, title: str, content_type: str, tags: List[str]) -> CallToolResult:
        """Save content to Obsidian using project configuration and templates"""
        try:
            # Get project configuration
            config = self._get_project_config()
            
            # Get project name from current directory
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
            target_path = self.obsidian_vault_path / project_folder
            
            # Ensure target folder exists
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Create full file path
            file_path = target_path / filename
            
            # Combine all tags
            all_tags = ["claude-code", content_type, project_name.lower()] + tags
            
            # Generate frontmatter
            frontmatter = self._generate_frontmatter(all_tags)
            
            # Combine frontmatter and formatted content
            full_content = frontmatter + formatted_content
            
            # Write file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_content)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Successfully saved {content_type} '{title}' to {file_path}\nProject: {project_name}\nFolder: {project_folder}"
                )]
            )
        except Exception as e:
            raise Exception(f"Failed to save to Obsidian: {str(e)}")


async def main():
    """Run the MCP server"""
    server_instance = ObsidianMCPServer()
    
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            server_instance.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())