#!/bin/sh
# Stage the workspace (cwd): git repo, cos set up, seed "running".
set -e
exec python3 "$(cd "$(dirname "$0")" && pwd)/../lib/seed.py" running
