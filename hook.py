#!/usr/bin/env python3
"""
Claude Code Hook Script to capture responses and send to Obsidian MCP Server
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def extract_response_content(hook_data: dict) -> str:
    """Extract the actual response content from Claude Code hook data"""

    if "tool_output" in hook_data:
        # PostToolUse event
        output = hook_data.get("tool_output", {})
        if isinstance(output, dict):
            return output.get("content", str(output))
        return str(output)

    elif "response" in hook_data:
        # Stop event - full response
        response = hook_data.get("response", {})
        if isinstance(response, dict):
            return response.get("content", str(response))
        return str(response)

    # Fallback
    return json.dumps(hook_data, indent=2)


def main():
    """Main hook handler"""
    try:
        hook_data = json.load(sys.stdin)
        content = extract_response_content(hook_data)

        # Skip if content is too short
        if len(content.strip()) < 10:
            print(json.dumps({"allow": True, "message": "Content too short, skipping"}))
            return

        # Queue for MCP processing
        temp_dir = Path.home() / ".claude" / "mcp_queue"
        temp_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = temp_dir / f"response_{timestamp}.json"

        mcp_request = {
            "content": content,
            "filename": f"claude_response_{timestamp}",
            "tags": ["claude-code", "ai-response"]
        }

        with open(temp_file, "w") as f:
            json.dump(mcp_request, f, indent=2)

        print(json.dumps({"allow": True, "message": f"Response queued: {temp_file}"}))

    except Exception as e:
        print(json.dumps({"allow": True, "message": f"Hook error: {str(e)}"}))


if __name__ == "__main__":
    main()