#!/usr/bin/env bash
# Check out the PR's code (shallow) so the run can trace callers, like a real local checkout.
set -eu
oid=$(gh pr view 9789 -R formbricks/formbricks --json headRefOid -q .headRefOid)
repo=https://github.com/formbricks/formbricks.git
git init -q && git remote add origin "$repo" && git fetch -q --depth 1 origin "$oid" && git checkout -q FETCH_HEAD
