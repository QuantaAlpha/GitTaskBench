#!/usr/bin/env python3
"""
Convert OpenCode session.json (from `opencode export`) to readable markdown.

Usage:
    python session_to_markdown.py session.json output.md [--task-id TASK_ID] [--status STATUS]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def format_timestamp(ts_ms: int) -> str:
    """Convert millisecond timestamp to readable string."""
    if not ts_ms:
        return "N/A"
    return datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def format_duration(start_ms: int, end_ms: int) -> str:
    """Format duration between two timestamps."""
    if not start_ms or not end_ms:
        return "N/A"
    duration = (end_ms - start_ms) / 1000
    if duration < 60:
        return f"{duration:.1f}s"
    minutes = int(duration // 60)
    seconds = duration % 60
    return f"{minutes}m {seconds:.1f}s"


def truncate_text(text: str, max_lines: int = 50, max_chars: int = 5000) -> str:
    """Truncate long text for readability."""
    if not text:
        return ""
    
    lines = text.split("\n")
    if len(lines) > max_lines:
        text = "\n".join(lines[:max_lines]) + f"\n\n... ({len(lines) - max_lines} more lines)"
    
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n... ({len(text) - max_chars} more chars)"
    
    return text


def render_tool_call(part: dict) -> str:
    """Render a tool call part to markdown."""
    tool = part.get("tool", "unknown")
    state = part.get("state", {})
    status = state.get("status", "unknown")
    
    lines = [f"\n### Tool: `{tool}` ({status})\n"]
    
    # Input
    input_data = state.get("input", {})
    if input_data:
        lines.append("**Input:**")
        lines.append("```json")
        lines.append(json.dumps(input_data, indent=2, ensure_ascii=False))
        lines.append("```\n")
    
    # Output (truncated)
    output = state.get("output", "")
    if output:
        lines.append("**Output:**")
        lines.append("```")
        lines.append(truncate_text(str(output)))
        lines.append("```\n")
    
    return "\n".join(lines)


def render_message(msg: dict, msg_index: int) -> str:
    """Render a single message to markdown."""
    info = msg.get("info", {})
    parts = msg.get("parts", [])
    role = info.get("role", "unknown")
    
    lines = []
    
    # Message header
    if role == "user":
        lines.append(f"\n## User Message\n")
    else:
        model = f"{info.get('providerID', '')}/{info.get('modelID', '')}"
        tokens = info.get("tokens", {})
        token_str = f"In: {tokens.get('input', 0)} | Out: {tokens.get('output', 0)}"
        if tokens.get("reasoning", 0) > 0:
            token_str += f" | Reasoning: {tokens.get('reasoning', 0)}"
        lines.append(f"\n## Assistant Response ({model})\n")
        lines.append(f"*Tokens: {token_str}*\n")
    
    # Render parts
    for part in parts:
        part_type = part.get("type", "")
        
        if part_type == "text":
            text = part.get("text", "")
            if text and text.strip():
                lines.append(text)
                lines.append("")
        
        elif part_type == "reasoning":
            text = part.get("text", "")
            if text and text.strip():
                lines.append("> **Thinking:**")
                for line in text.split("\n"):
                    lines.append(f"> {line}")
                lines.append("")
        
        elif part_type == "tool":
            lines.append(render_tool_call(part))
        
        elif part_type in ("step-start", "step-finish"):
            # Skip these meta parts
            pass
    
    return "\n".join(lines)


def session_to_markdown(
    session_data: dict,
    task_id: str = None,
    status: str = None,
    tokens: dict = None,
    duration: float = None,
) -> str:
    """Convert session data to markdown."""
    info = session_data.get("info", {})
    messages = session_data.get("messages", [])
    
    # Header
    session_id = info.get("id", "unknown")
    title = task_id or info.get("title", "Untitled")
    time_info = info.get("time", {})
    created = time_info.get("created", 0)
    updated = time_info.get("updated", 0)
    
    # Calculate totals from messages if not provided
    if tokens is None:
        tokens = {"input": 0, "output": 0, "reasoning": 0}
        for msg in messages:
            msg_tokens = msg.get("info", {}).get("tokens", {})
            tokens["input"] += msg_tokens.get("input", 0)
            tokens["output"] += msg_tokens.get("output", 0)
            tokens["reasoning"] += msg_tokens.get("reasoning", 0)
    
    # Get model from first assistant message
    model = "unknown"
    for msg in messages:
        if msg.get("info", {}).get("role") == "assistant":
            provider = msg.get("info", {}).get("providerID", "")
            model_id = msg.get("info", {}).get("modelID", "")
            if provider and model_id:
                model = f"{provider}/{model_id}"
                break
    
    lines = [
        f"# Task: {title}",
        "",
        f"**Session:** `{session_id}`  ",
        f"**Model:** {model}  ",
        f"**Duration:** {duration or format_duration(created, updated)}  ",
        f"**Tokens:** Input: {tokens['input']} | Output: {tokens['output']} | Reasoning: {tokens['reasoning']}  ",
        f"**Status:** {status or 'completed'}",
        "",
        "---",
    ]
    
    # Render messages
    for i, msg in enumerate(messages):
        lines.append(render_message(msg, i))
        lines.append("---")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Convert OpenCode session.json to markdown")
    parser.add_argument("input", help="Input session.json file")
    parser.add_argument("output", help="Output markdown file")
    parser.add_argument("--task-id", help="Task ID for the header")
    parser.add_argument("--status", help="Task status (success, failed, timeout)")
    parser.add_argument("--tokens-json", help="Path to tokens.json for accurate token counts")
    parser.add_argument("--duration", type=float, help="Duration in seconds")
    
    args = parser.parse_args()
    
    # Read session data
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    with open(input_path, "r", encoding="utf-8") as f:
        session_data = json.load(f)
    
    # Read tokens if provided
    tokens = None
    if args.tokens_json:
        tokens_path = Path(args.tokens_json)
        if tokens_path.exists():
            with open(tokens_path, "r") as f:
                tokens = json.load(f)
    
    # Convert
    markdown = session_to_markdown(
        session_data,
        task_id=args.task_id,
        status=args.status,
        tokens=tokens,
        duration=f"{args.duration:.1f}s" if args.duration else None,
    )
    
    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    
    print(f"Converted {args.input} -> {args.output}")


if __name__ == "__main__":
    main()
