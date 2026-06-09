---
comet_change: simplify-code-entry
role: technical-design
canonical_spec: openspec
---

# 简化代码入口与整体逻辑 — Technical Design

## Overview

SVC-DASH Player 当前有 5 个入口点、2 套并行窗口实现。本设计将项目精简为单一入口 + 单一窗口实现，删除 ~10 个废弃/重复文件，清理 BufferManager 中约 100 行死代码。

## Architecture (After)

```
run.sh  ──→  dash_qt/simple_main.py  （唯一入口）
                  │
                  ▼
          QApplication
                  │
                  ▼
          SimpleWindow  （协调层）
            │         │
   ┌───────┘         └───────┐
   ▼                         ▼
SimpleControl            VideoWidget
（控制面板）              （视频渲染）

   下载线程 (threading.Thread)      播放线程 (threading.Thread)
┌──────────────────┐          ┌──────────────────┐
│ _download()      │          │ _player()        │
│ ParseMpd →       │          │ FFmpeg subprocess│
│ BufferManager →  │──seg_buf─→│ → frame_buf     │
│ svc_merge        │  (FIFO)  │ → QImage render  │
└──────────────────┘          └──────────────────┘
```

## Key Decisions

### 1. Single Entry: `simple_main.py`

保留 SimpleWindow（功能完整且经过验证），删除 MainWindow（未完成且逻辑重复）。SimpleWindow 是唯一经过实际播放验证的窗口实现。

### 2. Keep threading.Thread (No QThread)

当前 SimpleWindow 使用 Python threading.Thread + queue.Queue 已经实现非阻塞下载/播放。引入 QThread + Worker 分离会增加代码量但不带来实质收益。

### 3. BufferManager Slimming

删除仅服务于废弃 CLI 路径的方法：
- `download_all_segments()` — 旧 CLI 主循环
- `_start_playback()` / `_wait_for_completion()` — MplayerControl 播放协调
- `_init_context()` — 旧 strategy context 初始化
- `self.mplayer` — MplayerControl 依赖

保留 GUI 路径使用的方法：`download_init_segment()`, `download_segment()`, `download_segment_layer()`, `generate_h264()`, `download_wget()`。

### 4. run.sh Fix

```bash
# Before (hardcoded wrong path):
cd /Users/yrj/yrj/RF_DASH_By_Buffer
python3 dash_qt/simple_main.py 2>/dev/null &

# After (auto-locate project root):
cd "$(dirname "$0")/.."
python3 dash_qt/simple_main.py 2>/dev/null &
```

## Deletion Checklist

| File | Reason |
|------|--------|
| `Client.py` | DEPRECATED CLI entry, superseded by simple_main.py |
| `runclient.sh` | Loops deprecated Client.py |
| `MplayerControl.py` | Only used by deleted paths |
| `dash_qt/main.py` | Incomplete, duplicates simple_main.py |
| `dash_qt/main_window.py` | Incomplete, duplicates simple_window.py |
| `dash_qt/widgets/control_panel.py` | Only used by MainWindow |
| `dash_qt/workers/download_worker.py` | Only used by MainWindow |
| `dash_qt/workers/playback_worker.py` | Only used by MainWindow |
| `dash_qt/models/stream_session.py` | Only used by MainWindow |
| `dash_qt/models/app_config.py` | Only used by MainWindow |

## BufferManager — Methods to Remove

```python
# REMOVE: download_all_segments() — ~80 lines
#   Old CLI main loop with MplayerControl coordination

# REMOVE: _start_playback() — ~8 lines
#   Spawns MplayerControl thread

# REMOVE: _wait_for_completion() — ~5 lines
#   Busy-waits on mplayer.thread_live

# REMOVE: _init_context() — ~10 lines
#   Creates StrategyContext (GUI path does this inline)

# REMOVE: self.mplayer attribute + MplayerControl import — ~5 lines
```

## Testing Strategy

- **Existing tests** (`pytest tests/`): covers ParseMpd and svc_merge — both critical to the download pipeline
- **No new tests**: deletion/cleanup change; regressions caught by existing tests
- **Manual smoke test**: `python3 dash_qt/simple_main.py` starts without crash

## Risks

| Risk | Mitigation |
|------|------------|
| MplayerControl deleted but something still imports it | Global grep before deletion; confirm only Client.py + BufferManager reference it |
| run.sh path breaks | `$(dirname "$0")` is POSIX; point is always the script's own directory |
| SimpleWindow breaks after BufferManager change | Only individual methods are called; none of the removed methods are touched by SimpleWindow |
