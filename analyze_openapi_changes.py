#!/usr/bin/env python3
"""Analyze OpenAPI schema changes and generate a structured Markdown report."""

import os
import json
import argparse
from datetime import datetime
from deepdiff import DeepDiff
from typing import Dict, Any, Optional

def load_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def analyze_changes(old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> Dict[str, Any]:
    diff = DeepDiff(old_schema, new_schema, view='tree')

    api_changes = {
        "new_endpoints": [],
        "removed_endpoints": [],
        "modified_endpoints": [],
        "security_changes": []
    }

    production_changes = {
        "documentation_updates": [],
        "example_updates": [],
        "internal_changes": []
    }

    # API endpoint analysis
    old_paths = old_schema.get("paths", {})
    new_paths = new_schema.get("paths", {})

    for path in new_paths:
        if path not in old_paths:
            api_changes["new_endpoints"].append(path)

    for path in old_paths:
        if path not in new_paths:
            api_changes["removed_endpoints"].append(path)

    for path in old_paths:
        if path in new_paths and old_paths[path] != new_paths[path]:
            api_changes["modified_endpoints"].append(path)

    # Security analysis
    old_sec = old_schema.get("components", {}).get("securitySchemes", {})
    new_sec = new_schema.get("components", {}).get("securitySchemes", {})
    if old_sec != new_sec:
        api_changes["security_changes"].append("Security schemes have been modified")

    # Version/documentation updates
    old_version = old_schema.get("info", {}).get("version", "")
    new_version = new_schema.get("info", {}).get("version", "")
    if old_version != new_version:
        production_changes["documentation_updates"].append(
            f"API version changed from {old_version} to {new_version}"
        )

    # Determine classification
    has_api_changes = any(api_changes[k] for k in api_changes)
    has_prod_changes = any(production_changes[k] for k in production_changes)

    classification = "API Change" if has_api_changes else "Production Update" if has_prod_changes else "Production Update"

    # Build Markdown content
    summary_lines = [f"# {classification}\n"]
    if has_api_changes:
        summary_lines.append("## API Changes")
        summary_lines.append(f"- **New endpoints:** {api_changes['new_endpoints'] or 'None'}")
        summary_lines.append(f"- **Removed endpoints:** {api_changes['removed_endpoints'] or 'None'}")
        summary_lines.append(f"- **Modified endpoints:** {api_changes['modified_endpoints'] or 'None'}")
        summary_lines.append(f"- **Security changes:** {api_changes['security_changes'] or 'None'}\n")
    if has_prod_changes:
        summary_lines.append("## Production Changes")
        summary_lines.append(f"- **Documentation updates:** {production_changes['documentation_updates'] or 'None'}")
        summary_lines.append(f"- **Example updates:** {production_changes['example_updates'] or 'None'}")
        summary_lines.append(f"- **Internal changes:** {production_changes['internal_changes'] or 'None'}\n")

    return classification, "\n".join(summary_lines)

def save_markdown(summary_md: str, output_dir: str, repo_name: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    current_date = datetime.now().strftime('%Y-%m-%d')
    md_file = os.path.join(output_dir, f"{repo_name}-{current_date}-open-api-diff.md")

    with open(md_file, 'w') as f:
        f.write(summary_md)

    print(f"Markdown summary saved to {md_file}")

def main():
    parser = argparse.ArgumentParser(description='Analyze OpenAPI changes and generate a Markdown summary.')
    parser.add_argument('old_file', help='Path to the old OpenAPI schema file')
    parser.add_argument('new_file', help='Path to the new OpenAPI schema file')
    parser.add_argument('--output-dir', default='updates', help='Directory to save the markdown summary')
    parser.add_argument('--repo-name', required=True, help='Repository name to use in the output filename')

    args = parser.parse_args()

    old_schema = load_json_file(args.old_file)
    new_schema = load_json_file(args.new_file)

    if old_schema and new_schema:
        _, summary_md = analyze_changes(old_schema, new_schema)
        save_markdown(summary_md, args.output_dir, args.repo_name)

if __name__ == '__main__':
    main()
