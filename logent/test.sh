#!/usr/bin/env bash
# 같은 원본 자산으로 Python·JVM 테스트와 Android lint를 실행해요.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s logent-plugin/src/test/python -p 'test_*.py'
./logent/gradle.sh :logent-plugin:testDebugUnitTest :logent-plugin:lint "$@"
