---
change: simplify-code-entry
design-doc: docs/superpowers/specs/2026-06-09-simplify-code-entry-design.md
base-ref: dbd62febe0f3cbee2a1c7e108830e7b68b62da01
archived-with: 2026-06-10-simplify-code-entry
---

# 简化代码入口与整体逻辑 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete 10 deprecated/duplicate files, clean ~100 lines of dead code from BufferManager, fix run.sh hardcoded path.

**Architecture:** Pure subtraction — delete unused files, strip dead methods from BufferManager, fix one script. No new code, no API changes.

**Tech Stack:** Python 3.9+, Bash, git

archived-with: 2026-06-10-simplify-code-entry
---

## File Map

| Action | File | Reason |
|--------|------|--------|
| DELETE | `Client.py` | Deprecated CLI entry |
| DELETE | `runclient.sh` | Loops deprecated Client.py |
| DELETE | `MplayerControl.py` | Only used by deleted paths |
| DELETE | `dash_qt/main.py` | Duplicate entry, incomplete |
| DELETE | `dash_qt/main_window.py` | Duplicate window, incomplete |
| DELETE | `dash_qt/widgets/control_panel.py` | Only used by MainWindow |
| DELETE | `dash_qt/workers/download_worker.py` | Only used by MainWindow |
| DELETE | `dash_qt/workers/playback_worker.py` | Only used by MainWindow |
| DELETE | `dash_qt/models/stream_session.py` | Only used by MainWindow |
| DELETE | `dash_qt/models/app_config.py` | Only used by MainWindow |
| MODIFY | `BufferManager.py` | Remove dead code |
| MODIFY | `run.sh` | Fix hardcoded path |
| MODIFY | `dash_qt/simple_main.py` | Remove dead-process kill logic (optional, keep if useful) |

archived-with: 2026-06-10-simplify-code-entry
---

### Task 1: Delete deprecated files (Phase 1)

**Files:** DELETE all 10 files listed above

- [ ] **Step 1: Verify no unexpected references to files being deleted**

```bash
# Check that only expected paths reference MplayerControl
grep -r "MplayerControl" --include="*.py" . | grep -v ".claude/" | grep -v "openspec/"
# Expected: only BufferManager.py (we'll clean in Task 3) and MplayerControl.py itself

# Check nothing else imports from deleted dash_qt modules
grep -r "from dash_qt.models" --include="*.py" . | grep -v ".claude/" | grep -v "openspec/"
grep -r "from dash_qt.workers" --include="*.py" . | grep -v ".claude/" | grep -v "openspec/"
grep -r "from dash_qt.widgets.control_panel" --include="*.py" . | grep -v ".claude/" | grep -v "openspec/"
grep -r "from dash_qt.main_window" --include="*.py" . | grep -v ".claude/" | grep -v "openspec/"
# Expected: only within the files being deleted themselves
```

- [ ] **Step 2: Delete the 10 files**

```bash
rm Client.py
rm runclient.sh
rm MplayerControl.py
rm dash_qt/main.py
rm dash_qt/main_window.py
rm dash_qt/widgets/control_panel.py
rm dash_qt/workers/download_worker.py
rm dash_qt/workers/playback_worker.py
rm dash_qt/models/stream_session.py
rm dash_qt/models/app_config.py
```

- [ ] **Step 3: Verify deletions**

```bash
# Confirm all 10 files are gone
for f in Client.py runclient.sh MplayerControl.py \
  dash_qt/main.py dash_qt/main_window.py \
  dash_qt/widgets/control_panel.py \
  dash_qt/workers/download_worker.py dash_qt/workers/playback_worker.py \
  dash_qt/models/stream_session.py dash_qt/models/app_config.py; do
  [ ! -f "$f" ] && echo "DELETED: $f" || echo "STILL EXISTS: $f"
done
```

- [ ] **Step 4: Commit**

```bash
git add -A Client.py runclient.sh MplayerControl.py dash_qt/main.py dash_qt/main_window.py \
  dash_qt/widgets/control_panel.py dash_qt/workers/download_worker.py \
  dash_qt/workers/playback_worker.py dash_qt/models/stream_session.py \
  dash_qt/models/app_config.py
git commit -m "chore: delete 10 deprecated/duplicate files

- Remove Client.py (deprecated CLI entry)
- Remove runclient.sh (loops deprecated Client.py)
- Remove MplayerControl.py (only used by deleted paths)
- Remove dash_qt/main.py, main_window.py (duplicate, incomplete)
- Remove associated widgets/workers/models (only used by MainWindow)

Part of: simplify-code-entry"
```

archived-with: 2026-06-10-simplify-code-entry
---

### Task 2: Fix run.sh

**Files:** Modify `run.sh`

- [ ] **Step 1: Read current run.sh to confirm content**

```bash
cat run.sh
```

- [ ] **Step 2: Replace with corrected version**

Write `run.sh`:

```bash
#!/bin/bash
# Kill all existing DASH player instances before starting
for pid in $(ps aux | grep -E "simple_main|ffmpeg" | grep -v grep | awk '{print $2}'); do
    kill -9 $pid 2>/dev/null
done
sleep 1
rm -rf BBB-I-360p 2>/dev/null
cd "$(dirname "$0")"
python3 dash_qt/simple_main.py 2>/dev/null &
sleep 3
echo "SVC-DASH Player ready"
```

- [ ] **Step 3: Verify script is executable**

```bash
chmod +x run.sh
bash -n run.sh  # syntax check
echo "exit code: $?"  # Expected: 0
```

- [ ] **Step 4: Commit**

```bash
git add run.sh
git commit -m "fix: correct run.sh project path

Replace hardcoded /Users/yrj/yrj/RF_DASH_By_Buffer with
$(dirname \"$0\") for portable project root detection.

Part of: simplify-code-entry"
```

archived-with: 2026-06-10-simplify-code-entry
---

### Task 3: Clean BufferManager dead code

**Files:** Modify `BufferManager.py`

- [ ] **Step 1: Remove MplayerControl import and attribute**

In `BufferManager.py`, delete lines 24-27 (the try/except MplayerControl import):

```python
# DELETE these lines:
try:
    from MplayerControl import MplayerControl
except ImportError:
    MplayerControl = None
```

In `__init__`, delete lines 64-67 (mplayer init):

```python
# DELETE these lines:
        if MplayerControl is not None:
            self.mplayer = MplayerControl(self.logger_buf_layer)
        else:
            self.mplayer = None
```

- [ ] **Step 2: Delete download_all_segments() method**

Delete the entire `download_all_segments()` method (lines 167-243 in current file).

- [ ] **Step 3: Delete _start_playback() method**

Delete the `_start_playback()` method (lines 148-158 in current file).

- [ ] **Step 4: Delete _wait_for_completion() method**

Delete the `_wait_for_completion()` method (lines 160-165 in current file).

- [ ] **Step 5: Delete _init_context() method**

Delete the `_init_context()` method (lines 128-146 in current file).

- [ ] **Step 6: Clean unused imports**

In the import section (lines 1-23), remove imports that are no longer needed. Specifically:
- Remove `from multiprocessing import Process` (line 18) — only used by deleted `download_all_segments`
- Remove `import datetime` (line 19) — only used by deleted methods
- Keep `from threading import Thread` (line 23) — still used if referenced elsewhere; verify

```bash
# After editing, verify remaining imports are used
python3 -c "import ast, sys; tree=ast.parse(open('BufferManager.py').read()); print('Syntax OK')"
```

- [ ] **Step 7: Verify BufferManager still works for GUI path**

```bash
# Check that download_init_segment, download_segment, download_segment_layer,
# generate_h264, download_wget all still exist
python3 -c "
from BufferManager import BufferManager
bm = BufferManager('http://example.com/', 'example')
# Verify key methods exist
assert hasattr(bm, 'download_init_segment'), 'missing download_init_segment'
assert hasattr(bm, 'download_segment'), 'missing download_segment'
assert hasattr(bm, 'download_segment_layer'), 'missing download_segment_layer'
assert hasattr(bm, 'generate_h264'), 'missing generate_h264'
assert hasattr(bm, 'download_wget'), 'missing download_wget'
# Verify dead methods are gone
assert not hasattr(bm, 'download_all_segments'), 'download_all_segments not removed'
assert not hasattr(bm, 'mplayer'), 'mplayer attribute not removed'
print('BufferManager: OK - all required methods present, dead code removed')
"
```

- [ ] **Step 8: Commit**

```bash
git add BufferManager.py
git commit -m "refactor: remove dead code from BufferManager

- Remove MplayerControl import and self.mplayer attribute
- Remove download_all_segments() (old CLI path, ~80 lines)
- Remove _start_playback(), _wait_for_completion(), _init_context()
- Clean unused imports (Process, datetime)

GUI path methods preserved: download_init_segment, download_segment,
download_segment_layer, generate_h264, download_wget.

Part of: simplify-code-entry"
```

archived-with: 2026-06-10-simplify-code-entry
---

### Task 4: Run tests and verify

**Files:** None (verification only)

- [ ] **Step 1: Run existing test suite**

```bash
python3 -m pytest tests/ -v --tb=short
```
Expected: All existing tests pass (ParseMpd + svc_merge tests).

- [ ] **Step 2: Verify simple_main.py imports succeed (no crash on missing modules)**

```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from dash_qt.simple_main import *  # Should import without error
print('simple_main.py imports: OK')
"
```

- [ ] **Step 3: Verify dash_qt package imports cleanly**

```bash
python3 -c "
from dash_qt.simple_window import SimpleWindow
from dash_qt.simple_control import SimpleControl
from dash_qt.video_widget import VideoWidget
print('dash_qt package imports: OK')
"
```

- [ ] **Step 4: Commit (if needed)**

No code changes expected — this is verification only. Only commit if Step 2 or Step 3 required import fixes.

archived-with: 2026-06-10-simplify-code-entry
---

### Task 5: Update tasks.md checkboxes

**Files:** Modify `openspec/changes/simplify-code-entry/tasks.md`

- [ ] **Step 1: Mark all completed tasks as checked**

Update `tasks.md` — change all `- [ ]` to `- [x]` for completed tasks.

- [ ] **Step 2: Commit**

```bash
git add openspec/changes/simplify-code-entry/tasks.md
git commit -m "chore: mark all tasks complete for simplify-code-entry"
```
