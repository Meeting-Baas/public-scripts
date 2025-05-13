#!/usr/bin/env python3
"""Analyze OpenAPI schema changes and generate a structured Markdown report."""

import os
import json
import argparse
from datetime import datetime
from deepdiff import DeepDiff
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Tuple
from openai import OpenAI

load_dotenv()

OPEN_API_KEY = os.getenv("OPEN_API_KEY")

def load_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def classify_changes(diff_text: str) -> str:
    """Classify changes based on plain text differences.
    
    Args:
        diff_text: Plain text containing the differences between schemas
        
    Returns:
        Classification string: "API Change" or "Production Update"
    """
    # Check if there are any differences
    if not diff_text.strip():
        return "No Changes"

    client = OpenAI(api_key=OPEN_API_KEY)

    # Prepare the prompt
    prompt = f"""Analyze these changes and classify them as either "API Change" or "Production Update".
    
Changes detected:
{diff_text}

Rules for classification:
- "API Change" if there are:
  * New endpoints
  * Removed endpoints
  * Modified endpoints
  * Security scheme changes
  * Authentication changes
  * Breaking changes
- "Production Update" if there are only:
  * Documentation updates
  * Example changes
  * Internal implementation details
  * Non-breaking changes

Provide your classification in JSON format:
{{
    "classification": "API Change" or "Production Update"
}}"""

    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an API change analyzer. Your task is to classify API changes."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
        )

        # Parse the response
        result = json.loads(response.choices[0].message.content)
        return result["classification"]

    except json.JSONDecodeError as e:
        print(f"Error parsing OpenAI response: {e}")
        return "Error"
    except Exception as e:
        print(f"Error in OpenAI classification: {e}")
        # Fallback to basic classification based on text content

        if "paths" in diff_text.lower() or "endpoint" in diff_text.lower():
            return "API Change"
        else:
            return "Production Update"

def analyze_changes(old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> Dict[str, Any]:
    try:
        diff = DeepDiff(old_schema, new_schema, view='tree')
        
        # Convert diff to plain text format
        diff_text = []
        for change_type, changes in diff.items():
            diff_text.append(f"{change_type.upper()}:")
            for change in changes:
                try:
                    diff_text.append(f"  {change.path()} -> {getattr(change, 't2', 'REMOVED')}")
                except Exception as e:
                    diff_text.append(f"  Error processing change: {e}")
        
        diff_text = "\n".join(diff_text)

        # Get classification from OpenAI
        classification = classify_changes(diff_text) 

        # Build Markdown content
        summary_lines = [
            f"# {classification}\n"
        ]
        
        if classification != "No Changes":
            if "paths" in diff:
                summary_lines.append("## API Changes")
                paths_diff = diff.get("paths", {})
                if "dictionary_item_added" in paths_diff:
                    summary_lines.append(f"- **New endpoints:** {[p.path() for p in paths_diff['dictionary_item_added']]}")
                if "dictionary_item_removed" in paths_diff:
                    summary_lines.append(f"- **Removed endpoints:** {[p.path() for p in paths_diff['dictionary_item_removed']]}")
                if "values_changed" in paths_diff:
                    summary_lines.append(f"- **Modified endpoints:** {[p.path() for p in paths_diff['values_changed']]}")
            
            if "components" in diff:
                summary_lines.append("## Security Changes")
                sec_diff = diff.get("components", {}).get("securitySchemes", {})
                if sec_diff:
                    summary_lines.append(f"- **Security scheme changes:** {sec_diff}")
            
            if "info" in diff:
                summary_lines.append("## Documentation Changes")
                info_diff = diff.get("info", {})
                if "values_changed" in info_diff:
                    for change in info_diff["values_changed"]:
                        summary_lines.append(f"- **{change.path()}:** {change.t1} -> {change.t2}")

        summary_lines.append("\n---\n## Raw Differences\n")
        summary_lines.append("```diff")
        summary_lines.append(diff_text)
        summary_lines.append("```")

        return classification, "\n".join(summary_lines)


    except Exception as e:
        print(f"Error analyzing changes: {e}")
        return "Error", f"Failed to analyze changes: {str(e)}"

def save_markdown(summary_md: str, output_dir: str, repo_name: str, date: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    
    md_file = os.path.join(output_dir, f"{repo_name}-{date}-open-api-diff.md")

    with open(md_file, 'w') as f:
        f.write(summary_md)

    print(f"Markdown summary saved to {md_file}")

def main():
    parser = argparse.ArgumentParser(description='Analyze OpenAPI changes and generate a Markdown summary.')
    parser.add_argument('old_file', help='Path to the old OpenAPI schema file')
    parser.add_argument('new_file', help='Path to the new OpenAPI schema file')
    parser.add_argument('--output-dir', default='updates', help='Directory to save the markdown summary')
    parser.add_argument('--repo-name', required=True, help='Repository name to use in the output filename')
    parser.add_argument("--date", help="Commit date in YYYY-MM-DD format")

    args = parser.parse_args()

    old_schema = load_json_file(args.old_file)
    new_schema = load_json_file(args.new_file)

    if old_schema and new_schema:
        _, summary_md = analyze_changes(old_schema, new_schema)
        save_markdown(summary_md, args.output_dir, args.repo_name, args.date)

if __name__ == '__main__':
    main()
