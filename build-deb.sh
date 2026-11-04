#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${1:-$(awk -F '"' '/"version"[[:space:]]*:/ { print $4; exit }' "$ROOT_DIR/package.json")}"
PACKAGE_ROOT="$(mktemp -d)"
OUTPUT_DIR="$ROOT_DIR/dist"
trap 'rm -rf "$PACKAGE_ROOT"' EXIT

if [[ -z "$VERSION" ]]; then
    printf 'Could not determine package version from package.json.\n' >&2
    exit 1
fi

APP_ROOT="$PACKAGE_ROOT/usr/share/idbiosys"
install -d "$APP_ROOT" "$PACKAGE_ROOT/usr/bin" \
    "$PACKAGE_ROOT/usr/share/applications" \
    "$PACKAGE_ROOT/usr/share/pixmaps" \
    "$PACKAGE_ROOT/usr/share/doc/idbiosys" \
    "$PACKAGE_ROOT/DEBIAN" "$OUTPUT_DIR"

install -m 0644 "$ROOT_DIR/app.py" "$ROOT_DIR/logger.py" \
    "$ROOT_DIR/wsgi.py" "$APP_ROOT/"
cp -a "$ROOT_DIR/templates" "$ROOT_DIR/static" "$APP_ROOT/"
rm -f "$APP_ROOT/static/custom-logo.png"

install -m 0755 "$ROOT_DIR/packaging/deb/idbiosys-kiosk" \
    "$PACKAGE_ROOT/usr/bin/idbiosys-kiosk"
install -m 0644 "$ROOT_DIR/packaging/deb/idbiosys.desktop" \
    "$PACKAGE_ROOT/usr/share/applications/idbiosys.desktop"
install -m 0644 "$APP_ROOT/static/CVAFPI-LOGO.png" \
    "$PACKAGE_ROOT/usr/share/pixmaps/idbiosys.png"
install -m 0644 "$ROOT_DIR/README.md" "$ROOT_DIR/ARCHITECTURE.md" \
    "$ROOT_DIR/LICENSE" \
    "$PACKAGE_ROOT/usr/share/doc/idbiosys/"
sed "s/@VERSION@/$VERSION/" "$ROOT_DIR/packaging/deb/control.in" \
    > "$PACKAGE_ROOT/DEBIAN/control"

find "$PACKAGE_ROOT" -type d -exec chmod 0755 {} +
find "$PACKAGE_ROOT" -type f -exec chmod 0644 {} +
chmod 0755 "$PACKAGE_ROOT/usr/bin/idbiosys-kiosk"

OUTPUT_FILE="$OUTPUT_DIR/idbiosys_${VERSION}_all.deb"
dpkg-deb --build --root-owner-group "$PACKAGE_ROOT" "$OUTPUT_FILE"
printf 'Built %s\n' "$OUTPUT_FILE"