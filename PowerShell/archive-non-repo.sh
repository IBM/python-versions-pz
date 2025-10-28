git clean -xdf --dry-run | sed 's/^Would remove //' | \
  grep -vE '/(bin|obj)/' | \
  while read path; do
    if [ -e "$path" ]; then
      echo "$path"
    fi
  done | tar -czf ../powershell-gen.tar.gz -T -

