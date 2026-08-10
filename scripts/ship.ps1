<#
.SYNOPSIS
  Push the current branch, open a PR if there isn't one, and queue auto-merge.

.DESCRIPTION
  Replaces the push -> open PR -> wait -> remember to come back -> click merge
  loop with a single command. The merge is QUEUED, not performed: GitHub holds
  it until every required status check passes, then squashes it in. If CI goes
  red, nothing merges and the PR sits there waiting for you.

  That last property is the entire point. A red PR merged by hand is what took
  main down on 2026-08-10 (#9, a Tailwind 4 major hidden in a dev-dependency
  group). Auto-merge is the safer path, not the reckless one, because it is
  the only one that cannot skip the gate.

  What makes this safe is NOT this script. It is the ruleset on main
  ("main: require CI gate") marking "All checks passed" as required. With no
  required checks, --auto merges instantly and this becomes a footgun. If that
  ruleset is ever removed, delete this script in the same commit.

.PARAMETER Title
  PR title. Defaults to the subject line of your last commit.

.PARAMETER NoMerge
  Push and open the PR, but do not queue the merge. Use when you want eyes on
  it first.

.EXAMPLE
  .\scripts\ship.ps1
  .\scripts\ship.ps1 -Title "fix(agent): rename Down to name the orchestrator"
  .\scripts\ship.ps1 -NoMerge
#>
[CmdletBinding()]
param(
    [string] $Title,
    [switch] $NoMerge
)

$ErrorActionPreference = 'Stop'

$branch = git rev-parse --abbrev-ref HEAD
if ($branch -in @('main', 'master')) {
    throw "You are on '$branch'. Ship from a feature branch — this script opens a PR, and a branch cannot PR into itself."
}

# Uncommitted work is the most common way to ship a half-finished change:
# the commit looks right, the working tree is where the rest of it lives.
$dirty = git status --porcelain
if ($dirty) {
    Write-Host "Uncommitted changes — these will NOT be included:" -ForegroundColor Yellow
    $dirty | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    if ((Read-Host "Continue anyway? (y/N)") -ne 'y') { return }
}

Write-Host "==> pushing $branch" -ForegroundColor Cyan
git push -u origin $branch

# gh pr view exits non-zero when no PR exists, which is a normal outcome here
# rather than a failure, so it must not trip ErrorActionPreference.
$existing = $null
try { $existing = gh pr view --json number,url 2>$null | ConvertFrom-Json } catch { }

if (-not $existing) {
    if (-not $Title) { $Title = git log -1 --pretty=%s }
    Write-Host "==> opening PR: $Title" -ForegroundColor Cyan
    # --fill takes the body from the commit message, so a commit that explains
    # itself produces a PR that explains itself.
    gh pr create --base main --head $branch --title $Title --fill
    $existing = gh pr view --json number,url | ConvertFrom-Json
} else {
    Write-Host "==> PR #$($existing.number) already open" -ForegroundColor Cyan
}

if ($NoMerge) {
    Write-Host "==> auto-merge skipped (-NoMerge). $($existing.url)" -ForegroundColor Yellow
    return
}

Write-Host "==> queueing auto-merge (squash)" -ForegroundColor Cyan
gh pr merge $existing.number --auto --squash

Write-Host ""
Write-Host "Queued. It merges when CI is green, and not before." -ForegroundColor Green
Write-Host "  $($existing.url)"
Write-Host "  watch:  gh pr checks $($existing.number) --watch"
Write-Host "  cancel: gh pr merge $($existing.number) --disable-auto"
