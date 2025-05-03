#!/usr/bin/env python3
"""
OpenAPI Diff Tool

This script compares two OpenAPI JSON files and outputs the differences.
It provides both a summary to console and a detailed report to a file.
"""

import argparse
import json

from deepdiff import DeepDiff


def get_by_path(data, path_list):
    """
    Access a nested element in data by following the path_list
    """
    for key in path_list:
        if isinstance(data, dict):
            data = data.get(key)
        elif isinstance(data, list) and isinstance(key, int):
            data = data[key]
        else:
            return None
    return data


def compare_openapi_files(old_file, new_file, output_file=None):
    """
    Compare two OpenAPI JSON files and output the differences

    Args:
        old_file (str): Path to the old OpenAPI JSON file
        new_file (str): Path to the new OpenAPI JSON file
        output_file (str, optional): Path to save detailed differences
    """
    # Load JSON files
    with open(old_file) as f1, open(new_file) as f2:
        old = json.load(f1)
        new = json.load(f2)

    # Generate diff
    diff = DeepDiff(old, new, view="tree")

    # Print summary to console
    if not diff:
        print("✅ No differences found in OpenAPI specs.")
    else:
        print("🔍 Differences found:\n")
        for change_type, changes in diff.items():
            print(f"{change_type.upper()}:")
            for change in changes:
                try:
                    print(f"  {change.path()} -> {getattr(change, 't2', 'REMOVED')}")
                except Exception as e:
                    print(f"  Error processing change: {e}")

    # Write detailed report to file if requested
    if output_file:
        with open(output_file, "w") as out:
            if not diff:
                out.write("✅ No differences found in OpenAPI specs.\n")
            else:
                out.write("🔍 Detailed Differences:\n\n")
                for change_type, changes in diff.items():
                    out.write(f"{change_type.upper()}:\n")
                    for change in changes:
                        path_str = change.path()
                        path_parts = change.path(output_format="list")
                        old_val = get_by_path(old, path_parts)
                        new_val = get_by_path(new, path_parts)
                        out.write(f"\n{path_str}:\n")
                        out.write(f"  OLD: {json.dumps(old_val, indent=2)}\n")
                        out.write(f"  NEW: {json.dumps(new_val, indent=2)}\n")

        print(f"Done. Detailed diff saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Compare two OpenAPI JSON files")
    parser.add_argument("old_file", help="Path to the old OpenAPI JSON file")
    parser.add_argument("new_file", help="Path to the new OpenAPI JSON file")
    parser.add_argument(
        "--output",
        "-o",
        default="openapi_diff.txt",
        help="Path to save detailed differences (default: openapi_diff.txt)",
    )

    args = parser.parse_args()
    compare_openapi_files(args.old_file, args.new_file, args.output)


if __name__ == "__main__":
    main()
