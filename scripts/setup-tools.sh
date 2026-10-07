#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/.benchmark-tools"
HUGO_VERSION=0.167.0
NIFT_VERSION="${NIFT_VERSION:-4.7.2}"
export NIFT_VERSION
mkdir -p "$TOOLS"

say() { printf '\n== %s\n' "$*"; }

say "Preparing .benchmark-tools/"
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64|Linux/amd64) hugo_asset="hugo_${HUGO_VERSION}_linux-amd64.tar.gz" ;;
  Linux/arm64|Linux/aarch64) hugo_asset="hugo_${HUGO_VERSION}_linux-arm64.tar.gz" ;;
  Darwin/arm64|Darwin/aarch64) hugo_asset="hugo_${HUGO_VERSION}_darwin-universal.tar.gz" ;;
  Darwin/x86_64|Darwin/amd64) hugo_asset="hugo_${HUGO_VERSION}_darwin-universal.tar.gz" ;;
  *) echo "Unsupported host for pinned Hugo binary: $(uname -s)/$(uname -m)" >&2; exit 2 ;;
esac

if [ ! -x "$TOOLS/hugo" ] || ! "$TOOLS/hugo" version | head -1 | grep -q "v${HUGO_VERSION}"; then
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/nift-benchmark-tools.XXXXXX")"
  trap 'rm -rf "$tmp"' EXIT HUP INT TERM
  url="https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/${hugo_asset}"
  echo "Downloading Hugo ${HUGO_VERSION} ($hugo_asset)..."
  curl -fL --max-time 300 "$url" -o "$tmp/hugo.tar.gz"
  curl -fL --max-time 60 "https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_${HUGO_VERSION}_checksums.txt" -o "$tmp/checksums.txt"
  expected=$(awk -v name="$hugo_asset" '$2 == name {print $1}' "$tmp/checksums.txt")
  [ -n "$expected" ] || { echo "Hugo checksum missing" >&2; exit 1; }
  if command -v sha256sum >/dev/null 2>&1; then actual=$(sha256sum "$tmp/hugo.tar.gz" | awk '{print $1}'); else actual=$(shasum -a 256 "$tmp/hugo.tar.gz" | awk '{print $1}'); fi
  [ "$actual" = "$expected" ] || { echo "Hugo checksum mismatch" >&2; exit 1; }
  tar -xzf "$tmp/hugo.tar.gz" -C "$tmp"
  cp "$tmp/hugo" "$TOOLS/hugo"
  chmod 0755 "$TOOLS/hugo"
fi

say "Installing the official Nift release (curl -fsSL https://nift.dev/install | sh)"
if [ ! -x "$TOOLS/nift" ] || ! "$TOOLS/nift" --version | grep -q "v${NIFT_VERSION}"; then
  curl -fsSL --max-time 60 https://nift.dev/install | NIFT_INSTALL_DIR="$TOOLS" sh
else
  echo "Nift already installed at $TOOLS/nift"
fi

say "Installing pinned Astro/VitePress dependencies (npm ci)"
echo "This downloads the pinned node_modules and can take a few minutes; it is not stuck."
cd "$ROOT"
npm ci --ignore-scripts --no-audit --no-fund

echo
echo "Pinned tools ready:"
"$TOOLS/nift" version
"$TOOLS/hugo" version | head -1
# Read the Node tool versions from package.json: `vitepress --version` starts
# the dev server instead of printing a version and exiting.
node -p "'astro ' + require('./node_modules/astro/package.json').version"
node -p "'vitepress ' + require('./node_modules/vitepress/package.json').version"
