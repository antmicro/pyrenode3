#!/usr/bin/env bash

set -euo pipefail

TEST_DIR="$(dirname "$0")"

clean_test_artifacts()
{
    rm -rf example.elf example.repl
}

trap "clean_test_artifacts; exit 1" EXIT
for i in "$TEST_DIR/"*.py ; do
    echo "Running test $i..."
    timeout -v 300 python "$i"
    echo
done
trap - EXIT

clean_test_artifacts
