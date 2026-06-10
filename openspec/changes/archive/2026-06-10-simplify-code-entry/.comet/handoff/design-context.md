# Comet Design Handoff

- Change: simplify-code-entry
- Phase: design
- Mode: compact
- Context hash: fd018e9a52bcf6334522e01db3472e02fbeaca8315e0b666a08a2a1916c47387

Generated-by: comet-handoff.sh

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/simplify-code-entry/proposal.md

- Source: openspec/changes/simplify-code-entry/proposal.md
- Lines: 1-30
- SHA256: db88bf2927d9583748d2b25f5e6ecdeea8944fa678c1542156fc1bf8c262ec91

```md
## Why

SVC-DASH Player 项目当前存在 **5个入口点、2套并行窗口实现**，导致代码入口混乱、维护成本高。`run.sh` 硬编码了错误的项目路径，`Client.py` 虽已标记 DEPRECATED 但仍存在且含硬编码 IP。`SimpleWindow`（功能完整但单体臃肿）与 `MainWindow`（结构化但不完整）两套实现并存，新增功能时不清楚该改哪个。现在项目处于早期阶段，是清理的最佳时机——越晚成本越高。

## What Changes

- **BREAKING**: 删除 `Client.py`（已标记 DEPRECATED 的 CLI 入口），连带删除 `runclient.sh`
- **BREAKING**: 删除 `MplayerControl.py`（仅被废弃的 CLI 路径使用）
- **BREAKING**: 删除 `dash_qt/main.py` 及其关联的 `MainWindow`/`ControlPanel`/`DownloadWorker`/`PlaybackWorker` 等未完成的新架构
- 修复 `run.sh`：更正项目路径、简化逻辑
- 保持 `SimpleWindow` 内联下载/播放逻辑（threading.Thread），`simple_main.py` 作为唯一入口
- 清理 `BufferManager` 中仅服务于废弃 CLI 路径的代码（`download_all_segments`、`_start_playback`、`_wait_for_completion`）
- 移除 `BufferManager` 对 `MplayerControl` 的依赖

## Capabilities

### New Capabilities

- `unified-entry-point`: 统一入口点 — `dash_qt/simple_main.py` 作为唯一启动入口，`run.sh` 作为唯一启动脚本

### Modified Capabilities

<!-- 当前 openspec/specs/ 为空，无已有 spec 需要修改 -->

## Impact

- **删除文件**: `Client.py`, `runclient.sh`, `MplayerControl.py`, `dash_qt/main.py`, `dash_qt/main_window.py`, `dash_qt/widgets/control_panel.py`, `dash_qt/workers/download_worker.py`, `dash_qt/workers/playback_worker.py`, `dash_qt/models/stream_session.py`, `dash_qt/models/app_config.py`
- **重写文件**: `run.sh`
- **重构文件**: `BufferManager.py`（删除废弃路径）, `dash_qt/simple_main.py`（小幅调整）
- **无外部 API 变更**，纯内部重构
```

## openspec/changes/simplify-code-entry/design.md

- Source: openspec/changes/simplify-code-entry/design.md
- Lines: 1-100
- SHA256: b72760847a700062cc250883b25a3b532c8dde98bfa3d4b40a84ebc50bc2b63d

[TRUNCATED]

```md
## Design: 简化代码入口与整体逻辑

### 目标架构

```
优化后 — 单一入口、清晰分层

run.sh  ──→  dash_qt/simple_main.py  （唯一入口）
                    │
                    ▼
            QApplication
                    │
                    ▼
            SimpleWindow  ─────────────────────────────┐
           （协调层，精简）                              │
              │         │                              │
     ┌───────┘         └───────┐                      │
     ▼                         ▼                       │
  SimpleControl            VideoWidget                 │
  （控制面板）              （视频渲染）                  │
                                                       │
     下载线程                        播放线程            │
  ┌──────────────┐            ┌──────────────┐         │
  │ 下载逻辑     │            │ 播放逻辑     │         │
  │ (内联，保持   │            │ (内联，保持   │         │
  │  现有模式)   │            │  现有模式)   │         │
  └──────┬───────┘            └──────┬───────┘         │
         │                           │                  │
         ▼                           ▼                  │
  ┌──────────────┐            ┌──────────────┐         │
  │ BufferManager│            │  FFmpeg 子进程│         │
  │ ParseMpd     │            │  frame_buf   │         │
  │ strategy     │            └──────────────┘         │
  │ svc_merge    │                                      │
  └──────────────┘                                      │
```

### 关键决策

#### 1. 入口统一：保留 `simple_main.py` + `SimpleWindow`

- **选择 SimpleWindow 而非 MainWindow 的原因**：
  - SimpleWindow 功能完整且经过验证（能正常播放）
  - MainWindow 的 DownloadWorker/PlaybackWorker 存在逻辑缺陷（如 `DownloadWorker._do_run` 重新实现了 `BufferManager.download_all_segments` 但更冗长）
  - MainWindow 引用的 `StreamSession`/`AppConfig` 增加了不必要的抽象层
  - 保留 SimpleWindow 改动最小，风险最低

#### 2. 不引入 QThread + Worker 分离

- **理由**：当前 SimpleWindow 使用 Python threading.Thread 已经实现了非阻塞下载/播放，功能正常
- 引入 QThread + Signal/Slot 会增加代码量但不带来实质收益
- 如果未来需要更复杂的线程生命周期管理，可以再重构

#### 3. BufferManager 精简

删除 `download_all_segments()`, `_start_playback()`, `_wait_for_completion()` 三个仅服务于废弃 CLI 的方法
- `download_init_segment()`, `download_segment()`, `generate_h264()` 保留（GUI 路径使用）
- 移除 `MplayerControl` 依赖（`self.mplayer` 属性及相关逻辑）

#### 4. run.sh 修复

```bash
# 旧: cd /Users/yrj/yrj/RF_DASH_By_Buffer  ← 错误路径
# 新: cd $(dirname "$0")                    ← 自动定位项目根目录
```

### 删除清单及理由

| 文件 | 删除理由 |
|------|---------|
| `Client.py` | 已标记 DEPRECATED，被 `simple_main.py` 取代 |
| `runclient.sh` | 仅用于循环调用废弃的 `Client.py` |
| `MplayerControl.py` | 仅被 `Client.py` 和 `BufferManager.download_all_segments` 使用 |
| `dash_qt/main.py` | 未完成的替代入口，功能与 `simple_main.py` 重复 |
| `dash_qt/main_window.py` | 未完成，功能与 `simple_window.py` 重复 |
| `dash_qt/widgets/control_panel.py` | 仅被 `MainWindow` 使用 |
| `dash_qt/workers/download_worker.py` | 仅被 `MainWindow` 使用，且重新实现了 BufferManager 逻辑 |
| `dash_qt/workers/playback_worker.py` | 仅被 `MainWindow` 使用 |
| `dash_qt/models/stream_session.py` | 仅被 `MainWindow` 使用 |
| `dash_qt/models/app_config.py` | 仅被 `MainWindow` 使用 |
```

Full source: openspec/changes/simplify-code-entry/design.md

## openspec/changes/simplify-code-entry/tasks.md

- Source: openspec/changes/simplify-code-entry/tasks.md
- Lines: 1-33
- SHA256: e9da044660c4dfd472a8c0cd98b225901530ab9c8744a09413a57dc203ab752b

```md
## Tasks

### 阶段 1: 删除废弃代码

- [ ] **Task 1.1**: 删除 `Client.py`（已标记 DEPRECATED 的 CLI 入口）
- [ ] **Task 1.2**: 删除 `runclient.sh`（仅用于循环调用废弃的 Client.py）
- [ ] **Task 1.3**: 删除 `MplayerControl.py`（仅被废弃路径使用）
- [ ] **Task 1.4**: 删除 `dash_qt/main.py`（未完成的替代入口）以及关联文件：
  - `dash_qt/main_window.py`
  - `dash_qt/widgets/control_panel.py`
  - `dash_qt/workers/download_worker.py`
  - `dash_qt/workers/playback_worker.py`
  - `dash_qt/models/stream_session.py`
  - `dash_qt/models/app_config.py`

### 阶段 2: 清理 BufferManager

- [ ] **Task 2.1**: 从 `BufferManager` 移除 `MplayerControl` 导入和 `self.mplayer` 属性
- [ ] **Task 2.2**: 删除 `BufferManager.download_all_segments()` 方法（仅废弃 CLI 使用）
- [ ] **Task 2.3**: 删除 `BufferManager._start_playback()` 和 `BufferManager._wait_for_completion()` 方法
- [ ] **Task 2.4**: 删除 `BufferManager._init_context()` 方法
- [ ] **Task 2.5**: 清理 `BufferManager` 中不再需要的导入（`datetime`, `Thread`, `sleep` 等）

### 阶段 3: 修复入口脚本

- [ ] **Task 3.1**: 修复 `run.sh`：更正项目路径（使用 `$(dirname "$0")` 自动定位），移除硬编码路径

### 阶段 4: 验证

- [ ] **Task 4.1**: 确认 `python3 dash_qt/simple_main.py` 能正常启动 GUI
- [ ] **Task 4.2**: 确认 `bash run.sh` 能正常启动
- [ ] **Task 4.3**: 运行现有测试 `python3 -m pytest tests/ -v`（如果存在）
- [ ] **Task 4.4**: 确认 `svc_merge.py` 独立工具仍可正常使用
```

