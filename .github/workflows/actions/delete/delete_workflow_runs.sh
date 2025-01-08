#!/bin/bash

# Ensure the repo argument is provided
repo=$1

# Check if the repository argument is empty
if [[ -z "$repo" ]]; then
  echo "Usage: ./delete_workflow_runs.sh <owner/repo>"
  exit 1
fi

# Fetch all workflow runs for the given repository (using GitHub API)
runs=$(gh api repos/$repo/actions/runs --paginate | jq -r '.workflow_runs[] | .id')

# Loop over the runs and delete each one
while IFS= read -r run; do
  echo "Deleting workflow run $run..."
  gh api -X DELETE repos/$repo/actions/runs/$run --silent
done <<< "$runs"

echo "All workflow runs for repository $repo have been deleted."
