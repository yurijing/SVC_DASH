# SVC-DASH Player

DASH (Dynamic Adaptive Streaming over HTTP) 客户端播放器，支持 SVC (Scalable Video Coding) 多层自适应码率视频流。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    SVC-DASH Player                           │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│  │ 下载线程  │───▶│ Seg Buf  │───▶│ 播放线程  │               │
│  │ urllib   │    │ (FIFO 10)│    │ FFmpeg   │               │
│  └──────────┘    └──────────┘    └────┬─────┘               │
│                                       │ RGB frames           │
│                                  ┌────▼─────┐               │
│                                  │ Frame Buf │              │
│                                  │ (max 96)  │              │
│                                  └────┬─────┘               │
│                                       │                     │
│  ┌───────────────────────────────────▼──────────────────┐   │
│  │              Main Thread (Qt Event Loop)              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────────────┐   │   │
│  │  │ Poll     │  │ Frame    │  │  VideoWidget      │   │   │
│  │  │ Timer    │  │ Timer    │  │  (QPainter)       │   │   │
│  │  │ (200ms)  │  │ (24fps)  │  │  embedded display │   │   │
│  │  └──────────┘  └──────────┘  └───────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  SimpleControl (Left Panel)                           │   │
│  │  MPD URL | Strategy ▼ | ▶ Start | ⏯ Pause | ⏹ Stop  │   │
│  │  Speed | Bandwidth | Buffer(0-10) | Segment           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 数据流

```
1. 用户输入 MPD URL + 策略 → 点击 Start

2. 下载线程 (Python Thread, urllib):
   ParseMpd → 获取层/阈值/段URL
   BufferManager → 下载SVC层(L0,L1,L2,L3) → svc_merge合并为H.264段
   每个段 → seg_buf.put() (FIFO, max=10, 满则阻塞)

3. 播放线程 (Python Thread):
   seg_buf.get() → 获取段文件路径
   FFmpeg子进程 → 解码.264 → 输出RGB到stdout管道
   每帧 → frame_buf.put() (max=96, 满则阻塞)

4. 主线程 (Qt Event Loop):
   帧定时器 (24fps) → frame_buf.get_nowait() → QImage → VideoWidget.paintEvent()
   轮询定时器 (200ms) → 更新Speed/Bandwidth/Buffer/Segment
```

## 主要功能

- **自适应码率**: 策略模式支持多种自适应算法 (threshold / qlearning / fixed)
- **边下边播**: 段级FIFO缓冲，段0开始即可播放，无需等待全部下载
- **SVC多层合并**: `svc_merge.py` 合并 L0+L1+L2+L3 增强层为 H.264 可解码流
- **暂停/继续**: ⏯ 冻结帧显示 + 暂停FFmpeg解码
- **停止/重载**: ⏹ 终止FFmpeg、清空队列、删除临时文件、重置UI
- **Seek跳转**: 拖拽滑块跳转到任意段，自动重建缓冲并恢复播放
- **本地文件服务器**: 支持 `http://127.0.0.1:8087` 数据集
- **实时统计**: 下载速度、带宽、缓冲占用、段进度实时显示

## 快速开始

```bash
# 安装依赖
pip install PySide6

# 启动本地文件服务器（如使用本地数据集）
python3 -m http.server 8087 --bind 127.0.0.1

# 启动播放器
python3 dash_qt/simple_main.py

# 或使用脚本
bash run.sh
```

## 项目结构

```
SVC_DASH/
├── dash_qt/                # Qt GUI 应用
│   ├── simple_main.py      # 入口点
│   ├── simple_window.py    # 主窗口（下载/播放协调）
│   ├── simple_control.py   # 左侧控制面板
│   ├── video_widget.py     # 视频渲染控件
│   ├── vlc_player.py       # VLC 播放器后端
│   ├── vt_decoder.py       # VideoToolbox 硬件解码 (macOS)
│   ├── h264_decoder.py     # H.264 软件解码
│   ├── web_server.py       # 本地文件服务器
│   └── yuv2rgb.c/dylib     # YUV→RGB 转换
├── strategy/               # 自适应策略模块
│   ├── base.py             # 策略基类
│   ├── context.py          # 策略上下文
│   └── fixed.py            # 固定质量策略
├── BufferManager.py        # 段下载与缓冲管理
├── ParseMpd.py             # MPD 清单解析
├── svc_merge.py            # SVC 多层合并工具
├── run.sh                  # 启动脚本
└── tests/                  # 测试
```

## 引用的第三方软件

| 软件 | 版本 | 用途 | 许可证 | 链接方式 |
|------|------|------|--------|----------|
| **FFmpeg** | 7.0.2 | H.264解码 (.264→RGB) | LGPL 2.1+ / GPL 2+ | 子进程 (stdout管道) |
| **PySide6** | 6.10+ | Qt GUI框架 | LGPL 3.0 | Python import |
| **Python** | 3.9+ | 运行环境 | PSF License | 系统安装 |

### FFmpeg 许可说明

FFmpeg 通过**独立子进程**调用 (`subprocess.Popen`)，Python 与 FFmpeg 之间通过 stdout 管道通信，属于"独立进程间通信"而非代码链接。根据 FFmpeg 官方许可 FAQ 和 LGPL 条款，此类用法不触发 LGPL 的 copyleft 义务，无需开源本项目代码。

### PySide6 许可说明

PySide6 (Qt for Python) 使用 **LGPL v3** 许可证，可免费用于商业闭源项目。与 PyQt6 (GPL/商业双许可) 不同，PySide6 是 Qt 官方 LGPL 版本，闭源商用无需购买许可。

## 自研组件

| 组件 | 说明 |
|------|------|
| `yuv2rgb.c` / `yuv2rgb.dylib` | YUV420→RGB888 C语言转换库，无第三方依赖 |
| `svc_merge.py` | SVC多层NAL单元合并为H.264可解码流 |
| `ParseMpd.py` | DASH MPD清单XML解析器 |
| `strategy/` | 自适应码率策略框架 |
| 其余Python代码 | SVC下载/缓冲/GUI，均为自研 |

## 运行测试

```bash
pytest tests/ -v
```

## 许可

MIT License
