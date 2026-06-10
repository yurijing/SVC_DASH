---
comet_change: functional-package-split
role: technical-design
canonical_spec: openspec
---

# 按功能分包 — Technical Design

## Overview

将根目录散落的模块按功能归入独立包：`streaming/`(DASH流媒体下载)、`decoder/`(视频解码播放)、`utils/`(工具)、`scripts/`(辅助脚本)。

## File Mapping

| 原路径 | 新路径 | 功能域 |
|--------|--------|--------|
| `BufferManager.py` | `streaming/buffer_manager.py` | 段下载+缓冲 |
| `ParseMpd.py` | `streaming/parse_mpd.py` | MPD解析 |
| `svc_merge.py` | `streaming/svc_merge.py` | SVC合并 |
| `dash_qt/h264_decoder.py` | `decoder/h264_decoder.py` | 软件解码 |
| `dash_qt/vt_decoder.py` | `decoder/vt_decoder.py` | VT硬解码 |
| `dash_qt/vlc_player.py` | `decoder/vlc_player.py` | VLC后端 |
| `dash_qt/yuv2rgb.c` | `decoder/yuv2rgb.c` | 色彩转换 |
| `dash_qt/yuv2rgb.dylib` | `decoder/yuv2rgb.dylib` | 色彩转换 |
| `dash_qt/vt_decode` | `decoder/vt_decode` | VT原生 |
| `dash_qt/vt_decode.m` | `decoder/vt_decode.m` | VT源码 |
| `dash_qt/vt_decode.swift` | `decoder/vt_decode.swift` | VT源码 |
| `logger.py` | `utils/logger.py` | 日志 |
| `log_utils.py` | `utils/log_utils.py` | 日志工具 |
| `pykeyboard.py` | `utils/pykeyboard.py` | 键盘模拟 |
| `bandwidth.sh` | `scripts/bandwidth.sh` | 带宽测试 |

## Import Changes

- `dash_qt/simple_window.py`: `ParseMpd`→`streaming.parse_mpd`, `BufferManager`→`streaming.buffer_manager`, `logger`→`utils.logger`
- `streaming/buffer_manager.py`: `logger`→`utils.logger`, `log_utils`→`utils.log_utils`, subprocess `"svc_merge.py"`→`"streaming/svc_merge.py"`
- `streaming/parse_mpd.py`: `logger`→`utils.logger`, `log_utils`→`utils.log_utils`
- `tests/test_parse_mpd.py`: `ParseMpd`→`streaming.parse_mpd`
- `tests/test_svc_merge.py`: 更新 svc_merge 路径引用

## README Update

同步更新 README.md: 架构图改用 Mermaid 绘制，项目结构反映新的功能分包。
