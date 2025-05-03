#!/usr/bin/env python3
import json
import os
import subprocess
import sys


# ANSI color codes
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 50}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 50}{Colors.ENDC}\n")


def print_section(text):
    """Print a formatted section header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}▶ {text}{Colors.ENDC}")


def print_success(text):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_warning(text):
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text):
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print an info message."""
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")


def get_all_repos(org):
    """Fetch all repositories for a given GitHub organization using GitHub CLI."""
    try:
        # Check if GitHub CLI is installed
        subprocess.run(
            ["gh", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        print_error("GitHub CLI (gh) is not installed or not in PATH.")
        print_info("Please install it from: https://cli.github.com/")
        sys.exit(1)

    # Check if user is authenticated
    try:
        subprocess.run(
            ["gh", "auth", "status"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError:
        print_error("Not authenticated with GitHub CLI.")
        print_info("Please run 'gh auth login' to authenticate.")
        sys.exit(1)

    print_info(f"Fetching repositories for organization: {org}")

    # Fetch all repos for the organization
    try:
        result = subprocess.run(
            [
                "gh",
                "repo",
                "list",
                org,
                "--limit",
                "1000",
                "--json",
                "name,url,sshUrl,visibility",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        repos = json.loads(result.stdout)

        if not repos:
            print_warning(f"No repositories found for organization: {org}")
            return []

        return repos
    except subprocess.CalledProcessError as e:
        print_error(f"Error fetching repositories: {e}")
        print_error(f"Error details: {e.stderr}")
        sys.exit(1)


def filter_repos_by_visibility(repos, visibility):
    """Filter repositories by visibility."""
    if visibility.lower() == "all":
        return repos

    return [repo for repo in repos if repo["visibility"].lower() == visibility.lower()]


def is_git_repository(path):
    """Check if the specified path is a git repository."""
    git_dir = os.path.join(path, ".git")
    return os.path.exists(git_dir) and os.path.isdir(git_dir)


def get_repo_remote_url(repo_path):
    """Get the remote URL of a repository."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def update_repository(repo_path):
    """Update an existing repository by fetching the latest changes without merging."""
    print_info(f"Updating repository: {os.path.basename(repo_path)}")
    try:
        # Fetch the latest changes without merging
        subprocess.run(
            ["git", "-C", repo_path, "fetch", "--all"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Get current branch
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        current_branch = result.stdout.strip()

        # Show commit difference information
        result = subprocess.run(
            [
                "git",
                "-C",
                repo_path,
                "rev-list",
                "--count",
                f"{current_branch}..origin/{current_branch}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        commit_diff = result.stdout.strip()

        if commit_diff and int(commit_diff) > 0:
            print_success(
                f"Fetched {os.path.basename(repo_path)} ({commit_diff} new commits available)"
            )
        else:
            print_success(f"Fetched {os.path.basename(repo_path)} (already up to date)")

        return True
    except subprocess.CalledProcessError as e:
        # Handle the error message correctly based on whether it's bytes or string
        error_msg = e.stderr if isinstance(e.stderr, str) else e.stderr.decode().strip()
        print_error(f"Failed to update {os.path.basename(repo_path)}: {error_msg}")
        return False


def clone_or_update_repos(repos, output_dir=None, use_ssh=True):
    """Clone or update repositories."""
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        os.chdir(output_dir)

    working_dir = os.getcwd()
    new_repos = 0
    updated_repos = 0
    failed_repos = 0
    skipped_repos = 0

    print_header("Starting Repository Operations")

    for repo in repos:
        name = repo["name"]
        # Choose between SSH and HTTPS URL
        url = repo["sshUrl"] if use_ssh else repo["url"]
        repo_path = os.path.join(working_dir, name)

        if os.path.exists(repo_path):
            if is_git_repository(repo_path):
                remote_url = get_repo_remote_url(repo_path)

                # Check if the remote URL matches (ignoring .git suffix variations)
                remote_base = remote_url.rstrip(".git") if remote_url else ""
                url_base = url.rstrip(".git")

                if remote_base == url_base:
                    # Repository exists and has the correct remote, update it
                    if update_repository(repo_path):
                        updated_repos += 1
                    else:
                        failed_repos += 1
                else:
                    print_warning(
                        f"Skipping {name}: Directory exists but has different remote URL"
                    )
                    skipped_repos += 1
            else:
                print_warning(
                    f"Skipping {name}: Directory exists but is not a git repository"
                )
                skipped_repos += 1
        else:
            # Directory doesn't exist, clone the repository
            print_info(f"Cloning: {name} ({repo['visibility']})")
            try:
                # Clone without setting up tracking branches
                subprocess.run(
                    ["git", "clone", "--no-checkout", url, name],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                # Setup the repo without automatic tracking
                subprocess.run(
                    ["git", "-C", name, "config", "remote.origin.fetch", ""],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                # Manually fetch the main branch
                subprocess.run(
                    ["git", "-C", name, "fetch", "origin", "main"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                # Create local main branch without tracking
                subprocess.run(
                    [
                        "git",
                        "-C",
                        name,
                        "checkout",
                        "-b",
                        "main",
                        "origin/main",
                        "--no-track",
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                print_success(f"Cloned {name} (without tracking remote branches)")
                new_repos += 1
            except subprocess.CalledProcessError as e:
                error_msg = (
                    e.stderr if isinstance(e.stderr, str) else e.stderr.decode().strip()
                )
                print_error(f"Failed to clone {name}: {error_msg}")
                failed_repos += 1

    print_header("Operation Summary")
    print_success(f"New repositories cloned:     {new_repos}")
    print_success(f"Existing repositories updated: {updated_repos}")
    print_error(f"Failed operations:            {failed_repos}")
    print_warning(f"Skipped repositories:         {skipped_repos}")


def is_in_master_repository():
    """Check if we're currently in what appears to be a master repository.

    This checks if we're in a directory that contains multiple git repositories.
    """
    current_dir = os.getcwd()
    subdirs = [f for f in os.listdir(current_dir) if os.path.isdir(f)]
    git_repos = [d for d in subdirs if is_git_repository(os.path.join(current_dir, d))]

    # If there are multiple git repositories in the current directory,
    # it's likely we're in a master repository
    return len(git_repos) > 1


def get_input_with_default(prompt, default):
    """Get user input with a default value if the user just presses Enter."""
    formatted_prompt = f"{Colors.BLUE}{prompt}{Colors.ENDC}"
    response = input(formatted_prompt).strip()
    return response if response else default


def main():
    if len(sys.argv) < 2:
        print_header("GitHub Repository Manager")
        print_error("Usage: fetch_github_repos.py <organization> [output_directory]")
        print_info("Example: fetch_github_repos.py microsoft ./microsoft-repos")
        sys.exit(1)

    print_header("GitHub Repository Manager")

    # Enhanced tip message with spacers and green coloring
    print(f"\n{Colors.GREEN}{Colors.BOLD}{'*' * 70}{Colors.ENDC}")
    print(
        f"{Colors.GREEN}{Colors.BOLD}{'*' * 5}{'':^5}TIP: PRESS ENTER TO SELECT DEFAULT OPTIONS (IN BRACKETS){'':^5}{'*' * 5}{Colors.ENDC}"
    )
    print(f"{Colors.GREEN}{Colors.BOLD}{'*' * 70}{Colors.ENDC}\n")

    org = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    # Check if we're already in what appears to be a master repository
    if output_dir is None and is_in_master_repository():
        print_info("Detected multiple git repositories in current directory.")
        choice = get_input_with_default(
            "Use current directory as master repository? [Y/n]: ", "y"
        ).lower()
        if choice != "y":
            output_dir = get_input_with_default(
                "Enter output directory (or leave empty to use current directory): ", ""
            )
            if not output_dir:
                output_dir = None

    repos = get_all_repos(org)

    print_section(f"Repository Analysis for {org}")
    print_info(f"Found {len(repos)} repositories")

    visibility_count = {}
    for repo in repos:
        repo_visibility = repo["visibility"]
        visibility_count[repo_visibility] = visibility_count.get(repo_visibility, 0) + 1

    for repo_visibility, count in visibility_count.items():
        if repo_visibility == "public":
            print_info(f"🌎 Public: {count}")
        else:
            print_info(f"🔒 Private: {count}")

    # Let user choose which visibility to clone
    print_section("Repository Visibility Selection")
    print_info("Which repositories would you like to clone or update?")
    print(f"  1. 🌎 Public (default)")
    print(f"  2. 🔒 Private")
    print(f"  3. 🌐 All")

    visibility_choice = get_input_with_default("Enter your choice (1-3) [1]: ", "1")

    # Map input choice to visibility type
    visibility_map = {"1": "public", "2": "private", "3": "all"}
    visibility_emoji = {"public": "🌎", "private": "🔒", "all": "🌐"}

    visibility = visibility_map.get(visibility_choice, "public")

    # Filter repositories by visibility
    if visibility != "all":
        filtered_repos = filter_repos_by_visibility(repos, visibility)
        print_info(
            f"Filtered to {len(filtered_repos)} {visibility_emoji[visibility]} {visibility} repositories"
        )
    else:
        filtered_repos = repos

    # Let user choose between SSH and HTTPS
    print_section("Connection Protocol Selection")
    print_info("How would you like to clone the repositories?")
    print(f"  1. 🔑 SSH (default)")
    print(f"  2. 🔗 HTTPS")

    protocol_choice = get_input_with_default("Enter your choice (1-2) [1]: ", "1")

    # Determine if SSH should be used
    use_ssh = protocol_choice != "2"

    if filtered_repos:
        # Default to "y" if user just presses Enter
        print_section("Confirmation")
        choice = get_input_with_default(
            f"Do you want to clone/update these {visibility_emoji[visibility]} {visibility} repositories? [Y/n]: ",
            "y",
        ).lower()

        if choice == "y":
            clone_or_update_repos(filtered_repos, output_dir, use_ssh)
        else:
            # Just print the repo list if not cloning
            print_section(f"{visibility.capitalize()} Repository List")
            for repo in filtered_repos:
                url_to_show = repo["sshUrl"] if use_ssh else repo["url"]
                print_info(f"{repo['name']}: {url_to_show}")


if __name__ == "__main__":
    main()
