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
