# spektrafilm 汉化 + GPU 分支交接表

> 用途：换电脑后按本表恢复环境、验证现状、继续做 GPU 阶段二。
> 本文件随 `zh-cn-gpu` 分支一起提交；最后更新：2026-11-24（含本机 RAW 加载与色彩链矩阵化实测）。

## 1. 项目与分支

| 项目 | 内容 |
|---|---|
| 仓库（fork） | https://github.com/jjingith/spektrafilm |
| 工作分支 | `zh-cn-gpu` |
| 上游 | https://github.com/andreavolpato/spektrafilm |
| 基线提交 | `3bb2c2d`（上游 `main`，版本 0.3.4） |
| 本分支提交 | `fc052ce` 汉化 + GPU 光谱加速；`d92dcf4` 数字格式修复；`be9132d` 自动启用 GPU |
| 许可证 | GPL-3.0-or-later；profiles/LUT 为 CC BY-SA 4.0 |
| 旧电脑工作目录 | `z:\personal\trae\03-滤镜与调色\spektrafilm` |
| 说明 | 非官方分支，与上游作者无隶属/背书关系 |

## 2. 新电脑准备

| 依赖 | 要求 |
|---|---|
| 系统 | Windows 11 x64（macOS/Linux 未验证本分支） |
| Python | **3.13**（上游 `requires-python ~=3.13`，3.14 不兼容） |
| uv | 用于建环境；建议 ≥0.12 |
| Git | 用于克隆/推送 |
| GPU | NVIDIA + CUDA 12.x；驱动需支持 CUDA 12.6（旧机 RTX 3070 / 621.35） |
| CUDA Toolkit | 需要 `cudart/cublas/cufft` 等 DLL；旧机为 CUDA 12.6。`CUDA_PATH` 应指向 Toolkit，或把 `...\CUDA\v12.x\bin` 加入 `PATH` |
| 认证 | 克隆公开仓库不需要登录；推送需要在新机执行 `gh auth login`，不要复制旧机 token |

## 3. 克隆与安装

```powershell
git clone https://github.com/jjingith/spektrafilm.git
cd spektrafilm
git checkout zh-cn-gpu

uv venv --python 3.13
uv pip install -e ".[gpu,dev]"

# 启动
spektrafilm
```

说明：

- `[gpu]` 安装 `cupy-cuda12x>=14.0`；不装则自动走 CPU。
- `[dev]` 安装 pytest/opencolorio，便于跑测试。
- 安装后默认中文界面；GPU 默认自动检测（`SPEKTRAFILM_GPU` 未设置即 auto）。
- 旧机的 `uv tool` 全局安装和桌面快捷方式只属于旧机，新机无需照搬；直接 `uv pip install -e` 后运行即可。

## 4. 环境变量

| 变量 | 作用 |
|---|---|
| `SPEKTRAFILM_LANG` | 默认 `zh_CN`；设为 `en` 恢复英文界面 |
| `SPEKTRAFILM_GPU` | 未设置/`auto`：有 CuPy+CUDA 就用 GPU；`0/false/off/no/cpu`：强制 CPU |

```powershell
$env:SPEKTRAFILM_LANG = "en"   # 英文
$env:SPEKTRAFILM_GPU = "0"     # 强制 CPU
spektrafilm
```

## 5. 当前完成状态

### 5.1 汉化（已完成）

- 默认简体中文，覆盖：主界面标签、按钮、选项卡、下拉显示值、工具提示、状态栏、错误弹窗、文件对话框。
- Qt 标准按钮（确定/取消）通过 `qtbase_zh_CN.qm` / `qt_zh_CN.qm` 翻译。
- 审核意见 44 条已落实：
  - 29 条界面措辞（display transform → 显示变换、halation → 胶片光晕、测光模式改为相机行业叫法、MAIN → 主界面、CONFIG → 设置等）。
  - 9 条状态/弹窗；`off → 关闭`。
  - 5 条 napari 欢迎区/快捷操作：实测 `QtWelcomeWidget` 子控件 `isVisible()` 全为 False，确认不显示，保持英文。
- 术语保留英文：胶片/相纸型号、色彩空间、算法代号（`cam16ucs`、`hanatos2025` 等）。
- 英文回退已验证：`SPEKTRAFILM_LANG=en` 时选项卡恢复 MAIN/FILM/PRINT/ADVANCED/CONFIG。
- 数字显示修复：`QLocale` 固定为拉丁数字，避免 Windows `zh_CN` 默认 locale 的杭州码数字（〇〡〢）。

### 5.2 GPU 阶段一（已完成）

- 加速对象：印放曝光与扫描的**光谱密度投影**（逐像素 81 波长积分）。
- 实现：CuPy，按行分块，显存预算控制；`<=1MP` 用 float64 保证对齐，大图用 float32。
- 无 CuPy/CUDA 或未设置时自动回退 CPU。
- 数值对齐（0.79MP，float64）：最大绝对误差 `5.3e-14`，平均 `8.6e-16`。
- 4.2MP 实测（关闭颗粒/眩光，确定性）：

| 阶段 | CPU | GPU |
|---|---:|---:|
| 印放光谱积分 | 7.95 s | 2.09 s |
| 扫描光谱积分 | 8.29 s | 0.29 s |
| 整次模拟 | 34.2 s | 24.3 s |

> 整次模拟只有约 1.4 倍，因为其余阶段仍在 CPU；光谱阶段本身约 4–28 倍。

### 5.3 色彩链矩阵化加速（2026-11-24，本机实测）

发现 colour-science 的高层色彩函数在整幅大图上被数组 reshape/domain 缩放开销主导，
而它们在关闭 CCTF 时本质是 3×3 线性矩阵。改为「用 3×3 单位阵探针让 colour 构建一次
组合矩阵 → 用 einsum 应用到整图」，**数值逐位一致**（最大误差 ≤9e-16），无需 GPU。

| 位置 | 加速 | 说明 |
|---|---|---|
| RAW 白平衡色适应 | ~18× | `_wb_adaptation_matrix` 合并 RGB→XYZ→VonKries→XYZ→RGB |
| RAW ACES→输出色彩空间 | ~20× | `_output_transform_matrix`，CCTF 编码单独施加 |
| RAW 完整加载（61MP ARW） | **9.75s→4.89s (2.0×)** | as_shot→sRGB；自定义 3200K 11.0s→5.92s |
| 扫描色彩链 RGB↔XYZ | ~1.2× | `fast_color.py`，覆盖 gamut_compression + scanning |
| 扫描 XYZ→RGB（动态光源） | ~15× | 复用 `fast_color.xyz_to_rgb`（默认 CAT02 与 colour 一致） |

- 新增 `src/spektrafilm/utils/fast_color.py`：`rgb_to_xyz()` / `xyz_to_rgb()`，
  默认色适应为 **CAT02**（与 colour-science 默认一致）；illuminant 与色彩空间白点
  不同时 CAT02 生效，必须保留，否则数值会错（实测差 0.26）。
- 测试环境：本机 venv 在 `测试版本/spektrafilm/`，`pyvenv.cfg` 的 home 已从旧机
  `C:\Users\imzjj` 改指本机 Python 3.13（`C:\Users\Administrator\.workbuddy\...\3.13.12`）；
  使用该 venv 的 python 时须设 `PYTHONPATH=<仓库>/src` 才会加载本工作区源码（venv 内是
  be9132d 的拷贝安装）。
- 验证：`tests/test_fast_color.py`（25 passed）；真实 RAW 用
  `D:\屠库\导入\20260328 樱花园\DSC08046.ARW`（61MP，9564×6376）。
- **既有失败 26 项**（与本次改动无关，HEAD 基线同样失败）：GUI 布局/persistence、
  `test_lut_mode`（`GrainParams.mult_usm_amount` 属性缺失）、3 项 regression snapshot
  （源码与 baseline 快照版本不一致）。改动前后均为 753 passed / 26 failed。

### 5.4 GUI 功能增强（2026-11-24）

| 功能 | 位置 | 说明 |
|---|---|---|
| 图像信息栏 | 窗口左下角状态栏 | 显示 `宽 × 高（ppi）`；PPI 读 EXIF `XResolution`，缺失回退 72 |
| EXIF 按钮 | 底部工具栏（`EXIF`） | 弹出当前输入图像的完整 EXIF/IPTC/XMP 列表 |
| 前后对比 | 底部 `A/B` 开关 + 滑条 | 一张图上竖直分割线：左=输入、右=输出；滑条 0=全输出，100=全输入 |
| 系统设置 | 设置页新增「系统」类别 | 语言（默认/简中/English）与 GPU（自动/开/关），**重启生效** |
| 窗口/任务栏图标 | `napari_layout._app_window_icon()` | `assets/app_icon.ico`（多尺寸），同时用于窗口与任务栏 |
| RAW 分级加载 | `controller.load_raw_image()` | 先 half_size+linear 快速预览（~1s），后台线程全尺寸替换 |
| 字体路径修复 | `spektrafilm_gui/font_fix.py` | freetype 打不开中文路径字体 → 复制到 ASCII 目录并重定向；**内置，打包版同样生效** |

- 语言/GPU 偏好存 QSettings（`system/language`、`system/gpu`），启动时
  `system_prefs.apply_to_environment()` 写入环境变量，因此**不需改 launch_gui.py**。
- 对比图层常量 `COMPARE_LAYER_NAME`，由 `ViewerLayerService.set_compare_layer()` 拼合
  before/after 两个图层数据；输出更新后自动刷新。

## 6. 关键改动文件

| 文件 | 作用 | 注意事项 |
|---|---|---|
| `src/spektrafilm_gui/i18n.py` | 词典加载、`tr()`/`trf()`、控件树翻译 | 新增动态文本需在创建处调用 `tr`/`trf` |
| `src/spektrafilm_gui/locale/zh_CN.json` | 界面英文→中文词典 | 键必须与源码英文完全一致 |
| `src/spektrafilm_gui/locale/zh_CN_status.json` | 状态/弹窗模板 | 模板占位符必须保留 |
| `src/spektrafilm_gui/widget_primitives.py` | `normalize_ui_text()` 现为 `tr(text.lower())` | 新标签键用小写 |
| `src/spektrafilm_gui/widget_editors.py` | `EnumEditor` 显示中文、`itemData` 保存原值 | 不要改回 `currentText()`/`findText()` |
| `src/spektrafilm_gui/app.py` | 加载 Qt 中文翻译、固定 QLocale、启动时翻译控件 | `_set_numeric_locale()` 必须在建控件前 |
| `src/spektrafilm_gui/controller*.py` | 状态栏/弹窗/文件对话框汉化 | 动态消息用 `trf()` |
| `src/spektrafilm_gui/napari_layout.py` | `set_status()` 兜底翻译 | 格式化消息仍需源头 `trf()` |
| `src/spektrafilm/utils/gpu.py` | CuPy 检测、分块光谱投影 `project_log()` | 显存不足时调小分块上限 |
| `src/spektrafilm/runtime/stages/printing.py` | 印放曝光接入 GPU | GPU 返回 `None` 时走 CPU |
| `src/spektrafilm/runtime/stages/scanning.py` | 扫描投影接入 GPU | 同上 |
| `pyproject.toml` | 可选 `gpu` 依赖、`locale/*.json` 包数据 | 打包时勿漏 locale |
| `README.zh-CN.md` | 分支说明、安装、语言/GPU 用法、实测 | 上游 README 顶部已加导航 |
| `src/spektrafilm/utils/fast_color.py` | RGB↔XYZ 矩阵化（默认 CAT02） | 新增；勿改成 `chromatic_adaptation_transform=None` |
| `src/spektrafilm/utils/raw_file_processor.py` | WB 色适应 + ACES→输出转换矩阵化 | `_wb_adaptation_matrix` / `_output_transform_matrix` 有缓存；CCTF 编码须单独施加 |
| `src/spektrafilm/utils/gamut_compression.py` | 5 个压缩函数的 RGB↔XYZ 换用 fast_color | 建表处 `_build_polar_perceptual_c_max_table` 仍用 colour 原调用 |
| `src/spektrafilm/runtime/stages/scanning.py` | 场景 XYZ→RGB 换用 fast_color | 动态 illuminant + CAT02，勿丢 illuminant 参数 |
| `tests/test_fast_color.py` | 锁定 fast_color 与 colour 逐位一致 | 新增；含动态 illuminant/CAT02 场景 |
| `src/spektrafilm_gui/font_fix.py` | 中文路径字体修复 | 新增；`create_app()` 最早调用，勿删 |
| `src/spektrafilm_gui/system_prefs.py` | 语言/GPU 偏好（QSettings） | 新增；`apply_to_environment()` 须在控件创建前 |
| `src/spektrafilm_gui/options.py` → 用 `system_prefs` 的 Enum | 语言/GPU 枚举 | `AppLanguage` / `GpuMode` 定义在 system_prefs |
| `src/spektrafilm_gui/widget_sections.py` | `SystemSection`、`_build_button` 等 | 「系统」类别 |
| `src/spektrafilm_gui/controller_layers.py` | `set_compare_layer` / `remove_compare_layer` | 对比拼合图 |
| `src/spektrafilm_gui/controller.py` | 分级 RAW 加载、EXIF 弹窗、对比刷新 | `_on_raw_loaded` 用 generation 防竞态 |
| `src/spektrafilm/utils/io.py` | `read_image_ppi()` | 读 EXIF 分辨率 |
| `packaging/spektrafilm.spec` + `packaging/entry.py` | PyInstaller 绿色版 | 新增；`--onedir`，含 locale/assets/data |

## 7. 验证命令

```powershell
# 上游关键测试（旧机 16 passed）
python -m pytest tests/test_spectral_lut_service.py tests/test_pipeline_smoke.py `
  tests/test_runtime_api.py tests/test_filming_stage.py tests/test_emulsion.py -q

# GPU 是否可用
python -c "from spektrafilm.utils.gpu import gpu_available; print(gpu_available())"

# 界面冒烟：选项卡与数字
python -c "from qtpy.QtWidgets import QTabBar, QLineEdit; from spektrafilm_gui.app import create_app; app=create_app(); root=app.main_window; print([t.tabText(i) for t in root.findChildren(QTabBar) for i in range(t.count())]); print([w.text() for w in root.findChildren(QLineEdit) if w.text()][:8]); root.close()"
```

预期：选项卡为 `主界面/胶片/印放/高级/设置`；数字为 `0.03/640/0.00...`，无 〇/〡。

### 数值对齐复测方法

分别用 `SPEKTRAFILM_GPU=0` 和 `SPEKTRAFILM_GPU=1` 跑同一张确定性图像（关闭颗粒/眩光），比较输出：

```python
from spektrafilm import init_params, simulate
p = init_params()
p.film_render.grain.active = False
p.film_render.glare.active = False
p.print_render.glare.active = False
out = simulate(image, p)
```

小图（≤1MP）GPU 走 float64，应接近逐位一致；大图 float32 允许约 1e-6 量级差异。

## 8. 阶段二待办（GPU 化剩余瓶颈）

旧机 4.2MP GPU 路径的阶段耗时（关闭颗粒/眩光）：

| 阶段 | 耗时 | 主要工作 |
|---|---:|---|
| `scanning.scan_print` | 11.7 s | CAM16 色域压缩、`colour.XYZ_to_RGB`、CCTF 编码、模糊/USM |
| `filming.expose` | 4.9 s | Hanatos2025 LUT 上采样、镜头模糊、光晕/柔光 |
| `filming.develop` | 3.4 s | 密度曲线插值、DIR 成色剂、颗粒（本次关闭） |
| `printing.expose` | 2.9 s | 已含 GPU 光谱 2.1 s，其余为扩散/模糊 |
| `preprocess` | 0.7 s | 色彩空间转换/自动曝光 |

建议顺序（2026-11-24 本机剖析更新，4MP）：

| 步骤 | 实测耗时 | 备注 |
|---|---:|---|
| CAM16UCS 压缩（全流程） | 12.0 s | `XYZ_to_CAM16UCS` 3.7s + `CAM16UCS_to_XYZ` 3.8s + RGB↔XYZ 1.4s + 查表 0.57s |
| `fast_gaussian_filter` sigma=2 | 6.1 s | numba 并行 FIR，已高度优化，GPU 化需逐位复刻 IIR 边界/浮点顺序 |
| `XYZ_to_RGB` / `RGB_to_XYZ` | 0.68 s /call | **已矩阵化**（见 5.3），剩余为 CAM16/OkLab 内部调用 |

1. **扫描色彩链 — 部分完成**：预计算 RGB↔XYZ 矩阵已落地（`fast_color.py`，CPU 侧 ~15×，逐位一致），覆盖 `gamut_compression.py` 5 个压缩函数与 `scanning.py` 场景 XYZ→RGB。**剩余**：CAM16-UCS 正逆变换的 CuPy 移植（最重，需复刻 colour 的 domain-range 100/1 缩放 + 默认 `compute_H=False`，单独提交）；CuPy CCTF 编码。
2. **扫描/印放模糊**：`cupyx.scipy.ndimage.gaussian_filter` 或 CuPy FFT 替代 `fast_gaussian_filter`/`fftw`；注意边界与 sigma 单位。因现有 numba 实现已很快且用 float64，需评估数值对齐成本。
3. **Hanatos2025 上采样**：tc_lut 三线性/双三次查表移植到 CuPy，保留 CPU 回退。
4. **显影曲线/成色剂**：密度曲线 1D 插值可用 CuPy `searchsorted`/线性插值；DIR 扩散卷积走 CuPy。
5. **颗粒**：`cupy.random` 复现 lognormal/poisson；注意随机种子与 CPU 不完全一致，验收用统计/分布测试。
6. **GUI 开关/提示**：目前用环境变量；可在设置页加“使用 GPU”勾选与设备名显示。

阶段二验收标准：

- 确定性设置下 CPU/GPU 差异：float32 最大相对误差 ≤1e-6（或图像 8 位 ≤1 LSB）。
- 4.2MP 端到端 ≥2× 加速；42MP 不超 8GB 显存、不因分块产生接缝。
- 现有 pytest 全绿；新增 GPU 跳过逻辑（无 CUDA 时 skip）。
- 更新 `README.zh-CN.md` 覆盖范围与实测表。

## 9. 已知坑与约束

- **EnumEditor**：显示文本已中文，真实值存 `itemData`；任何新代码不要用 `currentText()` 当值。
- **normalize_ui_text**：会对标签小写后查词典；新增中文词条键必须是小写英文原文。
- **QLocale**：`create_app()` 里固定为中文/英文拉丁数字；不要再删 `_set_numeric_locale()`，否则杭州码数字会回来。
- **napari 外壳**：菜单栏、图层列表、图层控制在 `configure_napari_chrome()` 中被隐藏；若以后启用，需要单独做 napari language pack（`napari.languagepack` 入口 + `locale/zh_CN/LC_MESSAGES/napari.mo`）。
- **CUDA DLL**：`gpu.py` 会尝试 `os.add_dll_directory(CUDA_PATH\bin)`；仍失败时把 CUDA `bin` 加入 `PATH`，并确认 `cupy.cuda.runtime.getDeviceCount() > 0`。
- **float64 慢**：RTX 3070 的 FP64 吞吐低，当前只在 ≤1MP 用 float64；大图 float32。调整阈值前先测精度。
- **显存分块**：`_chunk_rows()` 以 1.5GB 上限估算；42MP 端到端尚未完整验证，先在 8GB 卡上跑 12–16MP 试。
- **上游合并**：`git fetch upstream && git merge upstream/main`；冲突集中在第 6 节列出的文件。合并后重跑汉化冒烟与 pytest。
- **不要提交** `.venv/`（已在 `.gitignore`）。
- **许可证**：保留 GPL-3.0 与 profiles 的 CC BY-SA 声明；发布衍生构建需继续开源并注明来源。

## 10. 发布与账号

- 分支已推送：https://github.com/jjingith/spektrafilm/tree/zh-cn-gpu
- 仓库公开，新机克隆无需认证；推送前在新机执行 `gh auth login`（账号 `jjingith`）。
- 旧机的 GitHub token 不要拷贝；旧机全局 `uv tool` 安装、桌面快捷方式均为机器本地状态。

## 11. 新电脑交接清单

- [ ] 安装 Git、uv、Python 3.13（uv 可自动下载）
- [ ] 安装 NVIDIA 驱动 + CUDA 12.x Toolkit，确认 `nvcc --version` 与 `CUDA_PATH`
- [ ] 克隆仓库并切到 `zh-cn-gpu`
- [ ] `uv venv --python 3.13` + `uv pip install -e ".[gpu,dev]"`
- [ ] 跑第 7 节 pytest，预期 16 passed
- [ ] 跑 GUI 冒烟，确认中文选项卡与正常数字
- [ ] 确认 `gpu_available()` 为 True；跑 4MP 对比复测性能
- [ ] 阅读第 8 节，从“扫描色彩链”开始阶段二
- [ ] 完成阶段二后更新 README、提交并推送分支

## 12. 参考

- 上游 README / 架构说明：https://github.com/andreavolpato/spektrafilm
- 分支说明：[README.zh-CN.md](README.zh-CN.md)
- 汉化审核表（旧机本地）：`z:\personal\trae\03-滤镜与调色\spektrafilm_汉化对照表.xlsx`；审核意见已落实到 `locale/*.json`，新机不需要该表即可继续。
