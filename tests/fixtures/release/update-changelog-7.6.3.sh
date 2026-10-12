DATE=$(date -u +%Y-%m-%d)

# Build the new section.
{
  echo "## [${NEW_VERSION}] — ${DATE}"
  echo ""
  echo "### Changes"
  echo ""
  while IFS= read -r line; do
    [ -n "$line" ] && echo "- ${line}"
  done <<< "$COMMITS"
  echo ""
} > /tmp/new_section.md

# Insert the new section after the leading "# Changelog" header
# paragraph but before the first existing version section.
awk -v section_file=/tmp/new_section.md '
  BEGIN {
    while ((getline line < section_file) > 0) section = section line "\n"
    close(section_file)
    inserted = 0
  }
  /^## \[/ && !inserted { print section; inserted = 1 }
  { print }
  END {
    if (!inserted) print section
  }
' CHANGELOG.md > CHANGELOG.md.new
mv CHANGELOG.md.new CHANGELOG.md
# The same section is the GitHub release notes (public repository
# standard: release notes come from the CHANGELOG). Kept outside the
# workspace so the release commit can never include it.
cp /tmp/new_section.md "$RUNNER_TEMP/RELEASE_NOTES.md"
