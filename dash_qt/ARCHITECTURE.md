# SVC-DASH Player — Architecture & License

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    SVC-DASH Player                           │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│  │ Download │───▶│ Seg Buf  │───▶│  Player  │               │
│  │  Thread  │    │ (FIFO 10)│    │  Thread  │               │
│  │ urllib   │    │          │    │ FFmpeg   │               │
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

## 核心文件

| 文件 | 行数 | 职责 |
|------|------|------|
| `simple_main.py` | 31 | 入口：杀旧进程、QApplication、显示窗口 |
| `simple_window.py` | 172 | 主窗口：生产者消费者协调、下载/播放线程管理 |
| `simple_control.py` | 145 | 左侧控制面板：MPD URL、策略选择、按钮、数据展示 |
| `video_widget.py` | 49 | 视频渲染控件：QPainter绘制RGB帧、状态叠加层 |
| `yuv2rgb.c` | 28 | C语言YUV420→RGB888转换（编译为.dylib） |
| `run.sh` | 11 | 启动脚本：自动杀旧进程、清理缓存 |

## 数据流

```
1. 用户输入MPD URL + 策略 → 点击Start

2. 下载线程 (Python Thread, urllib):
   ParseMpd → 获取层/阈值/段URL
   BufferManager → 下载SVC层(L0,L1,L2,L3) → svc_merge合并为H.264段
   每个段 → seg_buf.put() (FIFO, max=10, 满则阻塞)

3. 播放线程 (Python Thread):
   seg_buf.get() → 获取段文件路径
   FFmpeg子进程 → 解码.264 → 输出RGB到stdout管道
   每帧 → frame_buf.put() (max=96, 满则阻塞)
   段播完 → 删除临时文件 → 取下一段

4. 主线程 (Qt Event Loop):
   帧定时器 (24fps) → frame_buf.get_nowait() → QImage → VideoWidget.paintEvent()
   轮询定时器 (200ms) → 更新Speed/Bandwidth/Buffer/Segment
```

## 缓冲管理

```
seg_buf (FIFO, max=10):  等待FFmpeg解码的段文件路径
frame_buf (FIFO, max=96):  已解码的RGB帧(691,200字节/帧)

Buffer显示 = seg_buf.qsize() + frame_buf.qsize() / 48

缓冲=10 → 下载阻塞(seg_buf满)
缓冲=0  → 等待数据或播放完毕
下载完成 + 缓冲=0 → "Finishing..." → 播完剩余帧 → "Finished"
```

## 功能特性

- **自适应码率**: 5种策略 (threshold / qlearning / fixed / threshold-legacy / qlearning-legacy)
- **边下边播**: 段级FIFO缓冲, 段0开始即可播放, 无需等待全部下载
- **暂停/继续**: ⏯ 冻结帧显示 + 暂停FFmpeg解码
- **停止/重载**: ⏹ 杀FFmpeg、清队列、删临时文件、重置UI
- **SVC多层合并**: svc_merge.py 合并L0+L1+L2+L3增强层为H.264
- **本地文件服务器**: 支持http://127.0.0.1:8087数据集
- **自动清理**: 启动时杀旧进程、清缓存段文件

## 第三方开源软件

| 软件 | 版本 | 用途 | 许可证 | 链接方式 |
|------|------|------|--------|----------|
| **FFmpeg** | 7.0.2 | H.264解码(.264→RGB) | LGPL 2.1+ / GPL 2+ | 子进程(stdout管道) |
| **PySide6** | 6.10.3 | Qt GUI框架 | LGPL 3.0 | Python import |
| **Python** | 3.9 | 运行环境 | PSF License | 系统安装 |

### FFmpeg许可说明

FFmpeg通过**独立子进程**调用(`subprocess.Popen`)，Python与FFmpeg之间通过stdout管道通信，属于"独立进程间通信"而非代码链接。根据FFmpeg官方许可FAQ和LGPL条款，此类用法不触发LGPL的copyleft义务，无需开源本项目代码。

二进制来源: [evermeet.cx/ffmpeg](https://evermeet.cx/ffmpeg/) (GPL构建)

### PySide6 许可说明 (商业化分析)

PySide6 (Qt for Python) 使用 **LGPL v3** 许可证（非 GPL），可免费用于商业闭源项目：

| 合规项 | 状态 | 说明 |
|--------|------|------|
| 闭源商用 | ✅ | LGPLv3 允许不需购买许可 |
| Python import 动态链接 | ✅ | 天然符合 LGPL 要求 |
| 用户可替换库 | ✅ | pip install PySide6 即可替换 |
| 未使用 GPL 模块 | ✅ | 未用 QtCharts/QtDataViz 等 GPL 模块 |
| 打包要求 | ⚠️ | PyInstaller 需用 one-folder 模式 |
| 许可声明 | 已包含 | 本项目 LICENSE 文件需提及 LGPL |

与 PyQt6 对比：PyQt6 是 GPL/商业双许可，闭源需购买 Riverbank 商业许可。PySide6 是 Qt 官方 LGPL 版本，免费商用。

### 商业化总结

| 组件 | 许可 | 商业化风险 |
|------|------|-----------|
| PySide6 | LGPLv3 | ✅ 无风险，免费商用 |
| FFmpeg | LGPL/GPL | ✅ 子进程隔离，无 copyleft 义务 |
| yuv2rgb.c | 自研 | ✅ 自有代码 |
| Python 代码 | 自研 | ✅ 自有代码 |

**结论**：本项目可**直接商业化**，无需购买任何第三方许可。PySide6（LGPL）→ 免费商用；FFmpeg（子进程）→ 不触发 copyleft；其余代码自研。

### 自研组件

| 组件 | 许可 | 说明 |
|------|------|------|
| yuv2rgb.c / yuv2rgb.dylib | 本项目自有 | YUV→RGB C转换库，无第三方依赖 |
| 其余Python代码 | 本项目自有 | SVC下载/合并/策略/GUI |

## 启动方式

```bash
# 方式1: 直接启动 (自动杀旧进程)
python3 dash_qt/simple_main.py

# 方式2: 使用脚本
bash run.sh

# 预先启动本地文件服务器
python3 -m http.server 8087 --bind 127.0.0.1
```
