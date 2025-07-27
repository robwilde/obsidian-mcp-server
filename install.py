#!/usr/bin/env python3
"""
Obsidian MCP Server Installer for Claude Code
Uses standard claude mcp add commands with proper scope configuration
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {text} ==={Colors.ENDC}")


def print_success(text: str):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")


def run_command(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result
    except subprocess.CalledProcessError as e:
        if check:
            print_error(f"Command failed: {cmd}")
            print_error(f"Error: {e.stderr}")
            raise
        return e


def check_claude_code_available() -> bool:
    """Check if Claude Code CLI is available"""
    try:
        result = run_command("claude --version", check=False)
        if result.returncode == 0:
            print_success("Claude Code CLI is available")
            return True
        else:
            print_error("Claude Code CLI not found")
            return False
    except Exception:
        print_error("Claude Code CLI not found")
        return False


def check_python_version() -> bool:
    """Check if Python 3.8+ is available"""
    if sys.version_info >= (3, 8):
        print_success(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} found")
        return True
    else:
        print_error(f"Python 3.8+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        return False


def check_mcp_installed() -> bool:
    """Check if MCP package is installed"""
    try:
        import mcp
        print_success("MCP package is installed")
        return True
    except ImportError:
        print_warning("MCP package not found")
        return False


def install_mcp() -> bool:
    """Install the MCP package"""
    print_info("Installing MCP package...")
    try:
        result = run_command("pip install mcp")
        if result.returncode == 0:
            print_success("MCP package installed successfully")
            return True
        else:
            print_error("Failed to install MCP package")
            return False
    except Exception as e:
        print_error(f"Error installing MCP: {e}")
        return False


def get_obsidian_vault_path() -> Optional[Path]:
    """Prompt user for Obsidian vault path"""
    print_info("Please provide your Obsidian vault path:")
    
    # Suggest common locations
    common_paths = [
        Path.home() / "Documents" / "Obsidian Vault",
        Path.home() / "Obsidian",
        Path.home() / "Documents" / "Notes",
    ]
    
    print("Common locations:")
    for i, path in enumerate(common_paths, 1):
        exists = "✓" if path.exists() else "✗"
        print(f"  {i}. {path} {exists}")
    
    while True:
        response = input(f"\nEnter vault path (or number 1-{len(common_paths)}): ").strip()
        
        # Check if it's a number
        if response.isdigit() and 1 <= int(response) <= len(common_paths):
            vault_path = common_paths[int(response) - 1]
        else:
            vault_path = Path(response).expanduser()
        
        if vault_path.exists():
            print_success(f"Found Obsidian vault at: {vault_path}")
            return vault_path
        else:
            create = input(f"Path doesn't exist. Create it? (y/n): ").lower().startswith('y')
            if create:
                vault_path.mkdir(parents=True, exist_ok=True)
                print_success(f"Created vault directory at: {vault_path}")
                return vault_path
            else:
                print("Please enter a valid path.")


def get_server_path() -> Path:
    """Get the absolute path to the MCP server file"""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    server_file = script_dir / "obsidian_mcp_server.py"
    
    if not server_file.exists():
        print_error(f"MCP server file not found: {server_file}")
        sys.exit(1)
    
    print_success(f"Found MCP server at: {server_file}")
    return server_file


def choose_scope() -> str:
    """Let user choose MCP server scope"""
    print_info("Choose MCP server scope:")
    print("  1. user - Available across all your projects (recommended)")
    print("  2. local - Only for this specific project")
    print("  3. project - Shared with team via version control")
    
    while True:
        choice = input("Enter choice (1-3) [1]: ").strip() or "1"
        
        if choice == "1":
            return "user"
        elif choice == "2":
            return "local"
        elif choice == "3":
            return "project"
        else:
            print_warning("Please enter 1, 2, or 3")


def add_mcp_server(server_path: Path, vault_path: Path, scope: str) -> bool:
    """Add MCP server using claude mcp add command"""
    try:
        # Build the command with correct syntax
        # Format: claude mcp add <name> <command> [args...] [flags]
        cmd = f'claude mcp add obsidian-claude-code python3 "{server_path}" -s {scope} -e OBSIDIAN_VAULT_PATH="{vault_path}"'
        
        print_info(f"Adding MCP server with {scope} scope...")
        result = run_command(cmd)
        
        if result.returncode == 0:
            print_success(f"MCP server added successfully with {scope} scope")
            return True
        else:
            print_error(f"Failed to add MCP server: {result.stderr}")
            return False
    except Exception as e:
        print_error(f"Error adding MCP server: {e}")
        return False


def create_project_config() -> bool:
    """Create project-specific Obsidian configuration"""
    current_dir = Path.cwd()
    claude_dir = current_dir / ".claude"
    config_file = claude_dir / "obsidian.json"
    
    if config_file.exists():
        print_info(f"Project config already exists: {config_file}")
        return True
    
    print_info(f"Setting up project configuration for: {current_dir.name}")
    
    # Prompt for folder name
    default_folder = f"Projects/{current_dir.name}"
    folder = input(f"Obsidian folder for this project [{default_folder}]: ").strip()
    if not folder:
        folder = default_folder
    
    # Create configuration
    config = {
        "folder": folder,
        "templates": {
            "report": f"# {{title}}\n\n**📋 Report Generated**\n- **Date:** {{timestamp}}\n- **Project:** {current_dir.name}\n- **Type:** Technical Report\n\n---\n\n{{content}}\n\n---\n\n*Generated by Claude Code*",
            "review": f"# Code Review: {{title}}\n\n**👀 Review Details**\n- **Date:** {{timestamp}}\n- **Project:** {current_dir.name}\n- **Reviewer:** Claude Code\n\n---\n\n## Summary\n\n{{content}}\n\n---\n\n*Automated review by Claude Code*",
            "note": f"# {{title}}\n\n**📝 Note**\n- **Created:** {{timestamp}}\n- **Project:** {current_dir.name}\n\n---\n\n{{content}}"
        }
    }
    
    try:
        claude_dir.mkdir(exist_ok=True)
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        print_success(f"Created project config: {config_file}")
        print_info(f"Claude Code will save files to: {folder}")
        return True
    except Exception as e:
        print_error(f"Failed to create project config: {e}")
        return False


def remove_existing_server() -> bool:
    """Remove existing obsidian-claude-code server if it exists"""
    try:
        # Try to remove from all scopes
        for scope in ["local", "user", "project"]:
            result = run_command(f"claude mcp remove obsidian-claude-code -s {scope}", check=False)
            if result.returncode == 0:
                print_success(f"Removed existing server from {scope} scope")
        return True
    except Exception as e:
        print_warning(f"Could not remove existing servers: {e}")
        return True  # Continue anyway


def main():
    """Main installation process"""
    print_header("Obsidian MCP Server Installer for Claude Code")
    print_info("Using standard claude mcp add commands with proper scope configuration")
    
    # Check requirements
    print_header("Checking Requirements")
    
    if not check_claude_code_available():
        print_error("Claude Code CLI is required but not found")
        print_info("Please ensure Claude Code is installed and available in your PATH")
        sys.exit(1)
    
    if not check_python_version():
        sys.exit(1)
    
    if not check_mcp_installed():
        if not install_mcp():
            print_error("Cannot proceed without MCP package")
            sys.exit(1)
    
    # Get configuration
    print_header("Configuration")
    
    server_path = get_server_path()
    vault_path = get_obsidian_vault_path()
    if not vault_path:
        print_error("Cannot proceed without vault path")
        sys.exit(1)
    
    scope = choose_scope()
    
    # Remove existing server
    print_header("Removing Existing Configuration")
    remove_existing_server()
    
    # Add MCP server
    print_header("Installing MCP Server")
    if not add_mcp_server(server_path, vault_path, scope):
        sys.exit(1)
    
    # Handle project configuration based on scope and location
    print_header("Project Configuration")
    
    if scope == "user":
        print_info("User-scoped MCP server installed successfully!")
        print_info("You can now use 'save to Obsidian' in any project directory.")
        print()
        print_info("To add project-specific configuration to any project:")
        print(f"  cd /path/to/your/project")
        print(f"  python3 {Path(__file__).absolute()} --project-config")
    else:
        # For local/project scope, offer to create config in current directory
        if input("Create project configuration for current directory? (y/n): ").lower().startswith('y'):
            create_project_config()
    
    # Final instructions
    print_header("Installation Complete!")
    print_success("Obsidian MCP server has been installed successfully")
    print_info("Next steps:")
    print(f"  1. Restart Claude Code to load the new MCP server")
    print(f"  2. Ask Claude Code to 'save to Obsidian' in any project")
    print(f"  3. Files will be saved to your vault at: {vault_path}")
    print()
    print_info("To view installed MCP servers:")
    print(f"  claude mcp list")
    print()
    print_info("To add project configs to other directories:")
    print(f"  python3 {Path(__file__).absolute()} --project-config")


def check_existing_mcp_server() -> bool:
    """Check if obsidian-claude-code MCP server is already installed"""
    try:
        result = run_command("claude mcp list", check=False)
        if result.returncode == 0 and "obsidian-claude-code" in result.stdout:
            return True
        return False
    except Exception:
        return False


def project_config_only():
    """Only create project configuration"""
    print_header("Project Configuration Setup")
    
    # Check if MCP server is already installed
    if not check_existing_mcp_server():
        print_error("Obsidian MCP server not found!")
        print_info("Please run the full installer first:")
        print(f"  python3 {Path(__file__).absolute()}")
        sys.exit(1)
    
    print_success("Found existing Obsidian MCP server")
    create_project_config()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--project-config":
        project_config_only()
    else:
        main()