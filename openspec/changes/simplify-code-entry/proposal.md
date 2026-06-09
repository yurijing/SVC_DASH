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
