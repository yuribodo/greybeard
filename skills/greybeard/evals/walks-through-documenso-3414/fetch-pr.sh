#!/usr/bin/env bash
# Check out the PR's code (shallow) so the run can trace callers, like a real local checkout.
set -eu
oid=$(gh pr view 3414 -R documenso/documenso --json mergeCommit -q .mergeCommit.oid)
repo=https://github.com/documenso/documenso.git
git init -q && git remote add origin "$repo" && git fetch -q --depth 1 origin "$oid" && git checkout -q FETCH_HEAD
