---
name: weekly-report-generator
description: Generate a structured weekly report in Markdown by scanning the current user's Git commits and TODO changes from the past week. Use this skill whenever the user wants to create a weekly report, status update, or work summary from git history — or mentions reviewing their week's work, writing a standup summary, or generating a progress report from commits.
---

# Weekly Report Generator

Generate a structured weekly report in Markdown by scanning the current user's Git commits and TODO changes from the past 7 days.

## When to use this skill

Use this skill whenever the user asks for:
- A weekly report or weekly summary based on their work
- "What did I do this week?" style questions
- Generating a progress report from git commits
- Writing a standup summary or sprint review
- Producing a work journal from version control

If the user mentions a different time range (e.g. "monthly report"), adapt the date window accordingly but follow the same structure.

## How it works

The skill gathers data from three sources, then composes a structured Markdown report:

1. **Git commit history** — commits authored by the current user in the past 7 days
2. **TODO changes in code** — `TODO`/`FIXME`/`HACK`/`OPTIMIZE` comments added or removed this week (detected via `git diff` between now and 7 days ago)
3. **Standalone TODO files** — changes to files like `TODO.md`, `ROADMAP.md`, `BACKLOG.md`, `task.md` in the past week

## Step-by-step workflow

### Step 1: Determine the report window

Calculate dates for the past 7 days. The report covers from 7 days ago to today.

In Bash:
```bash
SINCE=$(date -d "7 days ago" +%Y-%m-%d)
UNTIL=$(date +%Y-%m-%d)
```

On macOS, use `date -v-7d +%Y-%m-%d` instead.

### Step 2: Detect the current user's Git identity

Run `git config user.name` and `git config user.email` to identify the current user. Use both for accurate author matching in `git log --author`.

### Step 3: Gather Git commit history

Run the following commands from the repository root:

**Commit summary (one line per commit):**
```bash
git log --author="<user.name>" --since="<SINCE>" --until="<UNTIL> 23:59:59" \
  --oneline --no-merges --format="%h %ad %s" --date=short
```

**Files changed per commit (for richer detail):**
```bash
git log --author="<user.name>" --since="<SINCE>" --until="<UNTIL> 23:59:59" \
  --no-merges --stat --format="---COMMIT---%n%h %ad %s" --date=short
```

**Daily commit count (for summary stats):**
```bash
git log --author="<user.name>" --since="<SINCE>" --until="<UNTIL> 23:59:59" \
  --no-merges --format="%ad" --date=short | sort | uniq -c
```

### Step 4: Gather TODO changes

**Code comment TODOs added/removed this week:**

Use `git diff` to find TODO-related comment changes between now and 7 days ago:

```bash
# Find lines added containing TODO markers
git diff "@{7 days ago}" -- | grep "^+" | grep -iE "(TODO|FIXME|HACK|OPTIMIZE|XXX)" || echo "No new TODOs added"

# Find lines removed containing TODO markers  
git diff "@{7 days ago}" -- | grep "^-" | grep -iE "(TODO|FIXME|HACK|OPTIMIZE|XXX)" || echo "No TODOs removed"
```

Then use Grep to scan the current codebase for all remaining TODOs:
```
grep -rn "(TODO|FIXME|HACK|OPTIMIZE)" --include="*.ts" --include="*.js" --include="*.py" \
  --include="*.java" --include="*.go" --include="*.rs" --include="*.rb" --include="*.c" \
  --include="*.cpp" --include="*.h" --include="*.swift" --include="*.kt" --include="*.vue" \
  --include="*.tsx" --include="*.jsx"
```

Adapt the `--include` patterns to match the project's languages. The skill should auto-detect by checking common file extensions in the repo.

**Standalone TODO file changes:**

Check if any of these files exist and have been modified in the past week:
```bash
git log --author="<user.name>" --since="<SINCE>" --until="<UNTIL> 23:59:59" \
  --oneline -- "TODO.md" "ROADMAP.md" "BACKLOG.md" "task.md" "tasks.md" "CHANGELOG.md"
```

If present, use Read to inspect the current state of those files and note relevant sections.

### Step 5: Compose the report

Write the report to `WEEKLY_REPORT.md` in the repository root. Use the exact template below.

## Report template

The report must follow this structure exactly:

```markdown
# 周报 — <start-date> 至 <end-date>

> 自动生成于 <generation-timestamp> | 作者: <git-user-name>

---

## 📊 本周概览

| 指标 | 数值 |
|------|------|
| 提交次数 | <total-commits> |
| 修改文件数 | <total-files-changed> |
| 新增 TODO | <new-todos-count> |
| 解决 TODO | <resolved-todos-count> |

---

## 📝 Git 提交记录

### <YYYY-MM-DD (星期X)>

| 提交 | 说明 |
|------|------|
| `<short-hash>` | <commit-message> |

*(Group commits by day. If no commits on a day, write "无提交记录")*

---

## ✅ TODO 变更

### 新增的 TODO
<!-- List newly added TODOs with file paths and descriptions -->
- **`<file-path>:<line>`** — <todo-description>

### 已解决的 TODO  
<!-- List TODOs that were removed/resolved this week -->
- **`<file-path>`** — <todo-description>

### 仍待处理的 TODO
<!-- Key remaining TODOs in the codebase (limit to top 15 by relevance) -->
- **`<file-path>:<line>`** — <todo-description>

---

## 🔍 重点事项

<!-- Summarize the 3-5 most significant pieces of work this week.
     Identify patterns from commit messages and TODO changes. -->

1. **<topic>** — <brief description>
2. **<topic>** — <brief description>
3. **<topic>** — <brief description>

---

## 📅 下周计划

<!-- Based on remaining TODOs and recent work patterns, suggest next-week priorities -->

- [ ] <suggested-task-1>
- [ ] <suggested-task-2>
- [ ] <suggested-task-3>

---

*报告由 [weekly-report-generator](skill) 自动生成*
```

## Important guidelines

- **No fabricated data**: Every commit and TODO listed must come from actual git output. If a section has no data, write "无" or "暂无" rather than inventing content.
- **Commit grouping**: Group commits by calendar day. For each day, show the day of the week in Chinese (星期一 through 星期日).
- **TODO relevance**: When listing remaining TODOs, prioritize those in recently modified files. Limit to 15 entries max to keep the report focused.
- **Key highlights**: Read through the commit messages and TODO changes to identify themes — don't just list them mechanically. Synthesis matters.
- **Plans**: Base next-week suggestions on unresolved TODOs and the obvious next steps from this week's work. These are suggestions, not commitments — phrase them accordingly.
- **File location**: Always write the report to `WEEKLY_REPORT.md` in the repository root directory. Overwrite the previous week's report.
- **Path display**: Use repository-relative paths when referencing files (e.g., `src/utils/parser.ts:42`), not absolute paths.
- **Language**: Section headers and labels use Chinese since the target audience is Chinese-speaking. Commit messages retain their original language.
