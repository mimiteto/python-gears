#!/bin/bash

# Define the directories to check for new files (replace with your desired directories)

export PACKAGE_DIRS
export VERSION_FILE
export DEFAULT_BRANCH="${DEFAULT_BRANCH:-master}"
VERSION_FILE="$(dirname "${0}")/../VERSION"

# Function to check for new files in a directory
function check_directory() {
        local directory="$1"
        local new_files
        new_files=$(git diff --diff-filter=A --name-only master | grep "^${directory}.*")

        if [ -n "$new_files" ]; then
                echo "New files found in $directory:"
                echo "$new_files"
                return 0
        fi
        return 1
}

# Bump correspongind component of the version
# in the VERSION file
function bump_version() {
        local component="${1}" # minor or patch

        if [ "${component}" = "minor" ]; then
                awk -i inplace -F '.' '{ $2++; OFS="."; print $1,$2,$3 }' "${VERSION_FILE}"
        elif [ "${component}" = "patch" ]; then
                awk -i inplace -F '.' '{ $3++; OFS="."; print $1,$2,$3 }' "${VERSION_FILE}"
        else
                echo "Invalid component. Please specify 'minor' or 'patch'."
                exit 1
        fi
}

# Main function to iterate through specified directories and check for new files
function main() {
        if ! git diff --diff-filter=M --name-only master | grep "^${VERSION_FILE}$"; then
                echo "Version file has been modified. Nothing to do here"
                exit 0
        fi

        for pkg_dir in $PACKAGE_DIRS; do
                if check_directory "${pkg_dir}"; then
                        bump_version minor
                        return 0
                fi
        done
        bump_version patch
}

main
