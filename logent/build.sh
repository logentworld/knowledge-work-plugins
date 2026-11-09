#!/usr/bin/env bash
# AAR를 D8로 변환하고 운영 키 또는 설치 불가 CI 키로 서명해요.
set -euo pipefail
cd "$(dirname "$0")/.."
./logent/gradle.sh :logent-plugin:pluginArtifacts "$@"
version="$(tr -d '[:space:]' < VERSION)"
name="logent-knowledge-work-v$version"
dist="$PWD/build/dist"
mkdir -p "$dist"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
suffix=""
key="${LOGENT_CONTENT_SIGNING_KEY_FILE:-}"
if [[ -z "$key" ]]; then
    suffix="-ci"
    key="$work/ci-signing.pem"
    umask 077
    openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$key"
    public="$work/ci-public.der"
    openssl ec -in "$key" -pubout -outform DER -conv_form uncompressed -param_enc named_curve -out "$public" 2>/dev/null
    printf '%s\n' 'CI 임시 서명이라 앱에 설치할 수 없어요. 운영 키를 지정해 주세요.' > "$dist/INSTALL-NOTE.txt"
else
    # 앱이 신뢰하는 공개키와 다른 키로 서명한 패키지는 게시 전에 거부해요.
    public="$work/content-public.der"
    base64 --decode content-public-key.der.b64 > "$public"
    printf '%s\n' '운영 서명 키로 서명했어요. 앱에 설치할 수 있어요.' > "$dist/INSTALL-NOTE.txt"
fi
python3 logent/plugin-pack.py build --definition "$PWD/logent-plugin.json" --version "$version" \
    --aar "$dist/$name.aar" --key "$key" --public-key "$public" --output "$dist/$name$suffix.lpg"
python3 - "$dist" "$name.aar" "$name-assets-source.zip" "$name$suffix.lpg" INSTALL-NOTE.txt <<'PY'
import hashlib
from pathlib import Path
import sys
root = Path(sys.argv[1])
with (root / 'SHA256SUMS').open('w', encoding='ascii') as output:
    for name in sys.argv[2:]:
        with (root / name).open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        output.write(f'{digest}  {name}\n')
PY
printf '산출물을 만들었어요: %s\n' "$dist"
