# spektrafilm 简体中文 + GPU 加速分支（非官方）

本仓库是 [andreavolpato/spektrafilm](https://github.com/andreavolpato/spektrafilm) 的非官方分支，基于上游提交 `3bb2c2d`（0.3.4），保留 GPL-3.0-or-later 许可证与全部上游版权声明。

## 这个分支做了什么

- **界面简体中文化**：默认 `zh_CN`，覆盖主界面标签、按钮、选项卡、下拉显示值、工具提示、状态栏、错误弹窗和文件对话框；Qt 标准按钮（确定/取消）也使用中文。
- **可切回英文**：设置环境变量 `SPEKTRAFILM_LANG=en` 即可恢复英文界面，内部参数键与配置文件格式不变。
- **CUDA GPU 加速（可选）**：使用 CuPy 加速光谱密度投影，也就是印放曝光与扫描这两个最重的逐像素光谱积分阶段；没有 CuPy 或 CUDA 时自动回退 CPU。
- **数值对齐验证**：GPU 路径与 CPU 路径在小图上逐像素一致（float64 路径最大绝对误差 5.3e-14），大图使用 float32 以换取速度。

## 汉化范围

| 范围 | 状态 |
|---|---|
| spektrafilm 界面、状态栏、弹窗、文件对话框 | 已汉化 |
| Qt 标准对话框按钮（确定/取消等） | 已通过 Qt 中文翻译加载 |
| 胶片/相纸型号、色彩空间、算法代号（如 `kodak_portra_400`、`cam16ucs`） | 保留英文，便于与器材和上游文档对应 |
| napari 菜单栏、图层列表、图层控制面板 | 该应用在代码中隐藏了这些区域，界面上不显示，因此未修改 napari 本身 |

## 安装

```bash
git clone https://github.com/jjingith/spektrafilm.git
cd spektrafilm
git checkout zh-cn-gpu

# Python 3.13（上游要求 ~=3.13）
uv venv --python 3.13
# 需要 GPU 时安装可选依赖
uv pip install -e ".[gpu]"
# 不需要 GPU 时
# uv pip install -e .

spektrafilm
```

GPU 依赖：NVIDIA 显卡 + CUDA 12.x 驱动/运行时 + `cupy-cuda12x`。Windows 下需要 CUDA Toolkit 的 `bin` 在 `PATH` 或设置 `CUDA_PATH`。

## 使用

### 语言

```bash
# 默认中文
spektrafilm

# 英文
SPEKTRAFILM_LANG=en spektrafilm
```

Windows PowerShell：

```powershell
$env:SPEKTRAFILM_LANG = "en"
spektrafilm
```

### GPU

安装 `[gpu]` 可选依赖后默认自动使用 GPU；CuPy 不可用或没有 CUDA 设备时自动回退 CPU。

```bash
spektrafilm             # 自动：有 CuPy + CUDA 就用 GPU
SPEKTRAFILM_GPU=0 spektrafilm   # 强制 CPU
```

Windows PowerShell：

```powershell
$env:SPEKTRAFILM_GPU = "0"   # 强制 CPU；删除该变量恢复自动
spektrafilm
```

## 当前 GPU 覆盖范围与实测

当前版本只把**光谱密度投影**（印放曝光 `spectral_compute_enlarger`、扫描 `spectral_compute_scanner`）放到 GPU；显影曲线、DIR 成色剂、颗粒、光晕/柔光模糊、CAM16 色域压缩仍在 CPU。

实测环境：Ryzen 5 5600 + RTX 3070 + CUDA 12.6，4.2 MP 输入，关闭颗粒/眩光以得到确定性结果：

| 阶段 | CPU | GPU |
|---|---:|---:|
| 印放光谱积分 | 7.95 s | 2.09 s |
| 扫描光谱积分 | 8.29 s | 0.29 s |
| 整次模拟 | 34.2 s | 24.3 s |

小图数值对齐（0.79 MP，float64）：最大绝对误差 `5.3e-14`，平均 `8.6e-16`。

这说明光谱积分阶段本身有 4–28 倍加速，但整次模拟仍受其余 CPU 阶段限制。后续阶段计划继续 GPU 化色域压缩、颗粒和曲线/模糊，再提供 GUI 内的开关。

## 与上游同步

```bash
git remote add upstream https://github.com/andreavolpato/spektrafilm.git
git fetch upstream
git merge upstream/main
```

本分支的修改集中在：

- `src/spektrafilm_gui/i18n.py`
- `src/spektrafilm_gui/locale/`
- `src/spektrafilm/utils/gpu.py`
- `src/spektrafilm/runtime/stages/printing.py`
- `src/spektrafilm/runtime/stages/scanning.py`
- `src/spektrafilm_gui/app.py`、`widget_primitives.py`、`widget_editors.py`、`controller*.py`、`napari_layout.py`
- `pyproject.toml`（可选 `gpu` 依赖、`locale` 包数据）

## 许可证与致谢

- 代码：GPL-3.0-or-later，见 `LICENSE`。
- 胶片/相纸 profile 与 LUT：CC BY-SA 4.0，见 `SPEKTRAFILM_LICENSE.txt`。
- 上游项目与作者：Andrea Volpato，<https://github.com/andreavolpato/spektrafilm>。
- 本分支为非官方修改版，与上游作者无隶属或背书关系。
