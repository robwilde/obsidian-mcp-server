#!/usr/bin/env python3
"""
Obsidian MCP Server Installer for Claude Code
Interactive installer that sets up the Obsidian MCP integration
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


def get_claude_config_dir() -> Path:
    """Get the Claude configuration directory"""
    claude_dir = Path.home() / ".claude"
    claude_dir.mkdir(exist_ok=True)
    return claude_dir


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


def install_mcp_server(vault_path: Path) -> bool:
    """Install the MCP server to global Claude directory"""
    claude_dir = get_claude_config_dir()
    
    # Copy the server file
    source_file = Path(__file__).parent / "obsidian_mcp_server.py"
    target_file = claude_dir / "obsidian_mcp_server.py"
    
    if not source_file.exists():
        print_error(f"Source file not found: {source_file}")
        return False
    
    try:
        shutil.copy2(source_file, target_file)
        target_file.chmod(0o755)  # Make executable
        print_success(f"Installed MCP server to: {target_file}")
        
        # Set environment variable for vault path
        env_file = claude_dir / "obsidian.env"
        with open(env_file, "w") as f:
            f.write(f"OBSIDIAN_VAULT_PATH={vault_path}\n")
        print_success(f"Created environment config: {env_file}")
        
        return True
    except Exception as e:
        print_error(f"Failed to install MCP server: {e}")
        return False


def get_claude_settings_path() -> Path:
    """Get Claude Code settings file path"""
    return get_claude_config_dir() / "settings.json"


def update_claude_settings(server_path: Path, vault_path: Path) -> bool:
    """Update Claude Code settings to include the MCP server"""
    settings_file = get_claude_settings_path()
    
    # Load existing settings or create new
    if settings_file.exists():
        try:
            with open(settings_file, "r") as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            print_warning("Invalid JSON in settings file, creating backup")
            shutil.copy2(settings_file, settings_file.with_suffix(".bak"))
            settings = {}
    else:
        settings = {}
    
    # Ensure mcpServers section exists
    if "mcpServers" not in settings:
        settings["mcpServers"] = {}
    
    # Add our Obsidian MCP server
    server_config = {
        "command": "python3",
        "args": [str(server_path)],
        "env": {
            "OBSIDIAN_VAULT_PATH": str(vault_path)
        }
    }
    
    settings["mcpServers"]["obsidian-claude-code"] = server_config
    
    try:
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)
        print_success(f"Updated Claude Code settings: {settings_file}")
        return True
    except Exception as e:
        print_error(f"Failed to update settings: {e}")
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


def main():
    """Main installation process"""
    print_header("Obsidian MCP Server Installer for Claude Code")
    
    # Check requirements
    print_header("Checking Requirements")
    
    if not check_python_version():
        sys.exit(1)
    
    if not check_mcp_installed():
        if not install_mcp():
            print_error("Cannot proceed without MCP package")
            sys.exit(1)
    
    # Get Obsidian vault path
    print_header("Obsidian Configuration")
    vault_path = get_obsidian_vault_path()
    if not vault_path:
        print_error("Cannot proceed without vault path")
        sys.exit(1)
    
    # Install MCP server globally
    print_header("Installing MCP Server")
    claude_dir = get_claude_config_dir()
    server_path = claude_dir / "obsidian_mcp_server.py"
    
    if not install_mcp_server(vault_path):
        sys.exit(1)
    
    # Update Claude Code settings
    print_header("Configuring Claude Code")
    if not update_claude_settings(server_path, vault_path):
        sys.exit(1)
    
    # Offer to create project config
    print_header("Project Configuration")
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
    print_info("To add project configs to other directories, run:")
    print(f"  python3 {Path(__file__).absolute()} --project-config")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--project-config":
        print_header("Project Configuration Setup")
        create_project_config()
    else:
        main()