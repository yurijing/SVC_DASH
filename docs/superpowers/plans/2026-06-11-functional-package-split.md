---
change: functional-package-split
design-doc: docs/superpowers/specs/2026-06-11-functional-package-split-design.md
base-ref: ac91518bcdaa9ac43f56a82cf82f2093a2b41518
---

# 按功能分包 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan.

**Goal:** 将根目录散落模块按功能移入 streaming/ decoder/ utils/ scripts/，更新所有跨包 import。

**Architecture:** 纯文件移动 + import 路径替换，无逻辑改动。

**Tech Stack:** Python 3.9+

---

### Task 1: 创建新目录

- [ ] **Step 1: 创建 streaming/ decoder/ utils/ scripts/**

```bash
mkdir -p streaming decoder utils scripts
for d in streaming decoder utils; do touch "$d/__init__.py"; done
ls -d streaming decoder utils scripts
```

- [ ] **Step 2: Commit**

```bash
git add streaming/ decoder/ utils/ scripts/ && git commit -m "feat: create functional package directories

streaming/ - DASH streaming download layer
decoder/  - video decode and playback layer
utils/    - utility modules
scripts/  - auxiliary scripts"
```

### Task 2: 移动 streaming/ 模块

- [ ] **Step 1: 移动 BufferManager, ParseMpd, svc_merge**

```bash
git mv BufferManager.py streaming/buffer_manager.py
git mv ParseMpd.py streaming/parse_mpd.py
git mv svc_merge.py streaming/svc_merge.py
```

- [ ] **Step 2: 更新 streaming/buffer_manager.py 的 import**

```python
# 变更:
# from logger import *          → from utils.logger import *
# from log_utils import timestamp → from utils.log_utils import timestamp

# 变更 subprocess:
# ["python3", "svc_merge.py"]    → ["python3", "streaming/svc_merge.py"]
```

- [ ] **Step 3: 更新 streaming/parse_mpd.py 的 import**

```python
# 变更:
# from logger import *            → from utils.logger import *
# from log_utils import timestamp  → from utils.log_utils import timestamp
```

- [ ] **Step 4: Commit**

```bash
git add streaming/ && git commit -m "refactor: move streaming modules to streaming/ package

- BufferManager.py → streaming/buffer_manager.py
- ParseMpd.py → streaming/parse_mpd.py
- svc_merge.py → streaming/svc_merge.py
- Update internal imports to use utils.logger and utils.log_utils
- Update subprocess path for svc_merge.py"
```

### Task 3: 移动 decoder/ 模块

- [ ] **Step 1: 移动解码相关文件**

```bash
git mv dash_qt/h264_decoder.py decoder/h264_decoder.py
git mv dash_qt/vt_decoder.py decoder/vt_decoder.py
git mv dash_qt/vlc_player.py decoder/vlc_player.py
git mv dash_qt/yuv2rgb.c decoder/yuv2rgb.c
git mv dash_qt/yuv2rgb.dylib decoder/yuv2rgb.dylib
git mv dash_qt/vt_decode decoder/vt_decode
git mv dash_qt/vt_decode.m decoder/vt_decode.m
git mv dash_qt/vt_decode.swift decoder/vt_decode.swift
```

- [ ] **Step 2: Commit**

```bash
git add decoder/ dash_qt/ && git commit -m "refactor: move decoder modules to decoder/ package

- h264_decoder.py, vt_decoder.py, vlc_player.py
- yuv2rgb.c/dylib, vt_decode, vt_decode.m, vt_decode.swift"
```

### Task 4: 移动 utils/ 和 scripts/

- [ ] **Step 1: 移动工具模块**

```bash
git mv logger.py utils/logger.py
git mv log_utils.py utils/log_utils.py
git mv pykeyboard.py utils/pykeyboard.py
git mv bandwidth.sh scripts/bandwidth.sh
```

- [ ] **Step 2: Commit**

```bash
git add utils/ scripts/ && git commit -m "refactor: move utility modules to utils/ and scripts/

- logger.py, log_utils.py, pykeyboard.py → utils/
- bandwidth.sh → scripts/"
```

### Task 5: 更新外部 import

- [ ] **Step 1: 更新 dash_qt/simple_window.py**

```python
# from ParseMpd import ParseMpd           → from streaming.parse_mpd import ParseMpd
# from BufferManager import BufferManager → from streaming.buffer_manager import BufferManager
# from logger import initialize_logger    → from utils.logger import initialize_logger
```

- [ ] **Step 2: 更新 tests/test_parse_mpd.py**

```python
# from ParseMpd import ParseMpd → from streaming.parse_mpd import ParseMpd
```

- [ ] **Step 3: 更新 tests/test_svc_merge.py** — 更新 exec 加载路径

- [ ] **Step 4: Commit**

```bash
git add dash_qt/ tests/ && git commit -m "refactor: update cross-package imports after functional split

- dash_qt/simple_window.py → streaming.parse_mpd, streaming.buffer_manager, utils.logger
- tests/test_parse_mpd.py → streaming.parse_mpd
- tests/test_svc_merge.py → updated svc_merge path"
```

### Task 6: 更新 README + 验证

- [ ] **Step 1: 更新 README.md** — 架构图改为 Mermaid，项目结构更新

- [ ] **Step 2: 运行测试**

```bash
python3 -m pytest tests/ -v
```
Expected: 16 passed

- [ ] **Step 3: 验证跨包 import**

```bash
python3 -c "
from streaming.buffer_manager import BufferManager
from streaming.parse_mpd import ParseMpd
from utils.logger import initialize_logger
from dash_qt.simple_window import SimpleWindow
print('All imports OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add README.md && git commit -m "docs: update README with Mermaid diagrams and new project structure"
```
