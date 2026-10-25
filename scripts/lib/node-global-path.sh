#!/usr/bin/env bash
# Source in launchers/installers so npm's configured executables reach children.
if command -v npm >/dev/null 2>&1; then
  _npm_prefix="$(npm prefix -g 2>/dev/null || true)"
  if [ -n "$_npm_prefix" ] && [ -d "$_npm_prefix/bin" ]; then
    case ":$PATH:" in
      *":$_npm_prefix/bin:"*) ;;
      *) export PATH="$_npm_prefix/bin:$PATH" ;;
    esac
    hash -r 2>/dev/null || true
  fi
  unset _npm_prefix
fi
