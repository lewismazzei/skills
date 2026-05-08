#!/usr/bin/env bash
set -u

repo="${SKILLS_REPO:-$HOME/skills}"
agents="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"
codex="${CODEX_SKILLS_DIR:-$HOME/.codex/skills}"

errors=0
warnings=0

info() {
  printf 'INFO  %s\n' "$*"
}

warn() {
  warnings=$((warnings + 1))
  printf 'WARN  %s\n' "$*"
}

error() {
  errors=$((errors + 1))
  printf 'ERROR %s\n' "$*"
}

section() {
  printf '\n## %s\n' "$*"
}

skill_name_from_file() {
  sed -n 's/^name:[[:space:]]*//p' "$1" | head -n 1 | tr -d '"' | tr -d "'"
}

is_ignored_codex_entry() {
  case "$1" in
    .backup|.git|.gitignore|.system|README.md)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

has_readme_section() {
  grep -Eq "^##[[:space:]]+$1$" "$repo/README.md"
}

compare_personal_install() {
  local skill=$1
  local source_dir="$repo/$skill"
  local install_dir="$agents/$skill"

  if ! diff -qr \
    -x node_modules \
    -x prototype-analysis-error.log \
    -x '*.log' \
    -x '.DS_Store' \
    "$source_dir" "$install_dir" >/tmp/manage-personal-skills-diff.$$ 2>&1; then
    error "$skill install differs from source repo"
    sed 's/^/      /' /tmp/manage-personal-skills-diff.$$
  fi
  rm -f /tmp/manage-personal-skills-diff.$$
}

section "Personal Source Skills"

if [ ! -d "$repo" ]; then
  error "personal skills repo missing: $repo"
elif [ ! -f "$repo/README.md" ]; then
  error "personal skills README missing: $repo/README.md"
fi

personal_count=0
if [ -d "$repo" ]; then
  while IFS= read -r skill_dir; do
    skill=${skill_dir##*/}
    personal_count=$((personal_count + 1))
    skill_file="$skill_dir/SKILL.md"
    declared_name=$(skill_name_from_file "$skill_file")

    info "personal: $skill"

    if [ "$declared_name" != "$skill" ]; then
      error "$skill SKILL.md name is '$declared_name'"
    fi

    if [ -f "$repo/README.md" ] && ! has_readme_section "$skill"; then
      error "$skill missing README section"
    fi

    if [ ! -d "$agents/$skill" ]; then
      error "$skill missing active install: $agents/$skill"
    else
      compare_personal_install "$skill"
    fi

    if [ ! -L "$codex/$skill" ]; then
      error "$skill missing Codex symlink: $codex/$skill"
    else
      target=$(readlink "$codex/$skill")
      expected="../../.agents/skills/$skill"
      if [ "$target" != "$expected" ]; then
        error "$skill Codex symlink target is '$target', expected '$expected'"
      fi
    fi
  done < <(find "$repo" -maxdepth 2 -mindepth 2 -name SKILL.md -printf '%h\n' | sort)
fi

if [ "$personal_count" -eq 0 ]; then
  warn "no personal source skills found in $repo"
fi

section "Codex Runtime Entries"

if [ ! -d "$codex" ]; then
  error "Codex skills dir missing: $codex"
else
  while IFS= read -r entry; do
    name=${entry##*/}
    if is_ignored_codex_entry "$name"; then
      continue
    fi

    if [ -L "$entry" ]; then
      target=$(readlink "$entry")
      case "$target" in
        ../../.agents/skills/*)
          info "codex symlink: $name -> $target"
          ;;
        *)
          error "$name Codex symlink points outside .agents: $target"
          ;;
      esac
    elif [ -d "$entry" ]; then
      error "$name is a direct Codex skill directory; move to .agents and symlink"
    else
      warn "$name is an unexpected Codex runtime entry"
    fi
  done < <(find "$codex" -maxdepth 1 -mindepth 1 -printf '%p\n' | sort)
fi

section "Installed Skills Not In Personal Repo"

if [ -d "$agents" ]; then
  while IFS= read -r install_dir; do
    skill=${install_dir##*/}
    if [ ! -d "$repo/$skill" ]; then
      info "third-party or tool-managed: $skill"
      if [ ! -L "$codex/$skill" ]; then
        warn "$skill installed in .agents but missing Codex symlink"
      fi
    fi
  done < <(find "$agents" -maxdepth 1 -mindepth 1 -type d -printf '%p\n' | sort)
else
  error "agents skills dir missing: $agents"
fi

section "Summary"

printf 'errors=%d warnings=%d\n' "$errors" "$warnings"

if [ "$errors" -gt 0 ]; then
  exit 1
fi

exit 0
