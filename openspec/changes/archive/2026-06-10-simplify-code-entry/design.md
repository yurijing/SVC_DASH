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

### 数据流（保持不变）

```
1. 用户输入 MPD URL + 策略 → 点击 Start

2. 下载线程 (Python Thread):
   ParseMpd → 获取层/阈值/段URL
   BufferManager → 下载SVC层 → svc_merge合并为H.264段
   每个段 → seg_buf.put() (FIFO, max=10)

3. 播放线程 (Python Thread):
   seg_buf.get() → 获取段文件路径
   FFmpeg子进程 → 解码.264 → 输出RGB到stdout管道
   每帧 → frame_buf.put() (max=96)

4. 主线程 (Qt Event Loop):
   帧定时器 → frame_buf.get_nowait() → QImage → VideoWidget.paintEvent()
   轮询定时器 → 更新Speed/Bandwidth/Buffer/Segment
```
