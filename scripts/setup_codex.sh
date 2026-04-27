#!/usr/bin/env bash
# setup_codex.sh — Ensure Codex + Gemini CLI are always callable from any Node version.
#
# Problem: Claude Code shells may activate nvm v14 (no codex) before PATH
#          reaches /opt/homebrew/bin where the native codex binary lives.
#
# Fix 1 (primary):  symlink ~/.local/bin/codex → /opt/homebrew/bin/codex
#                   ~/.local/bin is prepended to PATH in .zshrc, so it wins.
# Fix 2 (fallback): if homebrew codex is absent, ensure nvm default is 24.
#
# Run once at machine setup, or from start.sh / install.sh (idempotent).

set -euo pipefail

HOMEBREW_CODEX="/opt/homebrew/bin/codex"
LOCAL_BIN="$HOME/.local/bin"
SYMLINK="$LOCAL_BIN/codex"

echo "[setup_codex] Checking Codex availability..."

mkdir -p "$LOCAL_BIN"

# ── Fix 1: native Homebrew binary ────────────────────────────────────────────
if [ -f "$HOMEBREW_CODEX" ]; then
  if [ -L "$SYMLINK" ] && [ "$(readlink "$SYMLINK")" = "$HOMEBREW_CODEX" ]; then
    echo "[setup_codex] ✓ ~/.local/bin/codex already points to Homebrew native binary."
  else
    ln -sf "$HOMEBREW_CODEX" "$SYMLINK"
    echo "[setup_codex] ✓ Symlinked ~/.local/bin/codex → $HOMEBREW_CODEX"
  fi
  # Verify
  if "$SYMLINK" --version >/dev/null 2>&1; then
    echo "[setup_codex] ✓ codex OK: $("$SYMLINK" --version 2>&1 | head -1)"
    exit 0
  fi
fi

# ── Fix 2: nvm fallback ───────────────────────────────────────────────────────
echo "[setup_codex] Homebrew codex not found or broken — checking nvm..."

# Load nvm if available
NVM_SH="${NVM_DIR:-$HOME/.nvm}/nvm.sh"
if [ -s "$NVM_SH" ]; then
  # shellcheck source=/dev/null
  source "$NVM_SH"
  CURRENT=$(nvm current 2>/dev/null || echo "none")
  DEFAULT_VER=$(nvm alias default 2>/dev/null | grep -oE 'v[0-9]+' | head -1 || echo "")

  if [ "$CURRENT" = "v24."* ] || nvm use 24 >/dev/null 2>&1; then
    NVM_CODEX="$HOME/.nvm/versions/node/$(nvm current)/bin/codex"
    if [ -f "$NVM_CODEX" ]; then
      ln -sf "$NVM_CODEX" "$SYMLINK"
      echo "[setup_codex] ✓ Symlinked ~/.local/bin/codex → $NVM_CODEX"
    fi
  fi

  # Ensure nvm default is 24 so future shells get the right Node
  if [ "$DEFAULT_VER" != "v24" ]; then
    nvm alias default 24 2>/dev/null && echo "[setup_codex] ✓ nvm default set to 24"
  fi
fi

# ── Gemini CLI wrapper (forces Node v24 to avoid ??= SyntaxError) ─────────────
# Gemini uses ??= (ES2021) but #!/usr/bin/env node may resolve to v14.
# Solution: a wrapper in ~/.local/bin/gemini that explicitly uses node v24.
NODE24=""
for candidate in \
  "/opt/homebrew/bin/node" \
  "$HOME/.nvm/versions/node/v24.14.1/bin/node" \
  "$(nvm which 24 2>/dev/null)"; do
  [ -x "$candidate" ] && NODE24="$candidate" && break
done

GEMINI_REAL="$($NODE24 -e "require('child_process').execSync('which gemini 2>/dev/null || echo /dev/null').toString().trim()" 2>/dev/null || true)"
# More portable: just look in nvm v24 bin
GEMINI_NVM="$HOME/.nvm/versions/node/v24.14.1/bin/gemini"
if [ -z "$GEMINI_REAL" ] && [ -f "$GEMINI_NVM" ]; then
  GEMINI_REAL="$GEMINI_NVM"
fi

if [ -n "$NODE24" ] && [ -f "$GEMINI_REAL" ]; then
  GEMINI_WRAPPER="$LOCAL_BIN/gemini"
  cat > "$GEMINI_WRAPPER" << GEMINI_EOF
#!/usr/bin/env bash
exec $NODE24 $GEMINI_REAL "\$@"
GEMINI_EOF
  chmod +x "$GEMINI_WRAPPER"
  echo "[setup_codex] ✓ Gemini wrapper → uses $NODE24"
fi

# ── Final check ───────────────────────────────────────────────────────────────
echo ""
if command -v codex >/dev/null 2>&1; then
  echo "[setup_codex] ✓ codex reachable: $(codex --version 2>&1 | head -1)"
else
  echo "[setup_codex] ✗ codex NOT found. Install with:"
  echo "    brew install codex"
  echo "  or: nvm use 24 && npm install -g @openai/codex@latest"
  exit 1
fi
if command -v gemini >/dev/null 2>&1; then
  echo "[setup_codex] ✓ gemini reachable: $(gemini --version 2>&1 | head -1)"
else
  echo "[setup_codex] ⚠ gemini not found. Install: nvm use 24 && npm i -g @google/gemini-cli"
fi
