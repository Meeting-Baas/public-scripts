import subprocess
import os
import json
from datetime import datetime
from typing import Optional, Tuple
from .models import ComparisonResult
from deepdiff import DeepDiff

class OpenAPIComparator:
    def __init__(self, script_path: str = "./compare_openapi.sh"):
        self.script_path = script_path
        self.updates_dir = "updates"
        os.makedirs(self.updates_dir, exist_ok=True)

    def compare_commits(
        self, 
        repo_path: str,
        old_commit: str, 
        new_commit: str, 
        repo_name: str
    ) -> ComparisonResult:
        """
        Compare OpenAPI specs between two commits.
        
        Args:
            repo_path: Path to the repository
            old_commit: The older commit hash
            new_commit: The newer commit hash
            repo_name: Name of the repository
            
        Returns:
            ComparisonResult containing diff content
        """
        try:
            # Run the comparison script
            result = subprocess.run(
                [self.script_path, repo_path, old_commit, new_commit, repo_name],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Script failed: {result.stderr}")
            
            # Get the output file
            current_date = datetime.now().strftime('%Y-%m-%d')
            diff_file = f"{self.updates_dir}/{repo_name}-{current_date}-open-api-diff.md"
            
            # Read the diff content if file exists
            diff_content = ""
            if os.path.exists(diff_file):
                with open(diff_file, 'r') as f:
                    diff_content = f.read()
            
            return ComparisonResult(
                diff_content=diff_content,
                repo_name=repo_name,
                old_commit=old_commit,
                new_commit=new_commit
            )
            
        except Exception as e:
            raise Exception(f"Comparison failed: {str(e)}")

    def _generate_categorized_diff(self, old_file: str, new_file: str) -> str:
        """Generate a categorized diff of OpenAPI specs."""
        with open(old_file) as f1, open(new_file) as f2:
            old = json.load(f1)
            new = json.load(f2)

        diff = DeepDiff(old, new, view='tree')
        
        if not diff:
            return "# No Changes\nNo differences found in OpenAPI specs."
        
        # Initialize categories
        categories = {
            "API Changes": [],
            "Production Changes": []
        }
        
        # Categorize changes
        for change_type, changes in diff.items():
            for change in changes:
                path = change.path()
                old_val = self._get_by_path(old, change.path(output_format='list'))
                new_val = self._get_by_path(new, change.path(output_format='list'))
                
                # Determine category
                if self._is_api_change(path, old_val, new_val):
                    categories["API Changes"].append(
                        f"### {path}\n"
                        f"**Old:**\n```json\n{json.dumps(old_val, indent=2)}\n```\n"
                        f"**New:**\n```json\n{json.dumps(new_val, indent=2)}\n```\n"
                    )
                else:
                    categories["Production Changes"].append(
                        f"### {path}\n"
                        f"**Old:**\n```json\n{json.dumps(old_val, indent=2)}\n```\n"
                        f"**New:**\n```json\n{json.dumps(new_val, indent=2)}\n```\n"
                    )
        
        # Generate markdown content
        content = ["# OpenAPI Specification Changes\n"]
        
        for category, changes in categories.items():
            if changes:
                content.append(f"## {category}\n")
                content.extend(changes)
        
        return "\n".join(content)

    def _is_api_change(self, path: str, old_val: any, new_val: any) -> bool:
        """Determine if a change is an API change or production change."""
        api_paths = [
            "paths",
            "components.schemas",
            "components.securitySchemes",
            "components.parameters",
            "components.responses"
        ]
        
        return any(api_path in path for api_path in api_paths)

    def _get_by_path(self, data: dict, path_list: list) -> any:
        """Get value from nested dictionary using path list."""
        for key in path_list:
            if isinstance(data, dict):
                data = data.get(key)
            elif isinstance(data, list) and isinstance(key, int):
                data = data[key]
            else:
                return None
        return data 