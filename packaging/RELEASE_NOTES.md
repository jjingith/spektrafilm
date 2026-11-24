## spektrafilm 简体中文 + GPU 加速（绿色解压版）

免安装的 Windows x64 便携版：下载 zip、解压、双击 `spektrafilm.exe` 即可运行，无需 Python 环境。

### 本次新增

- **图像信息栏**：窗口左下角常驻显示 `宽 × 高（ppi）`，PPI 读取 EXIF 分辨率，缺失时显示 72。
- **EXIF 查看**：底部工具栏 `EXIF` 按钮，弹出当前输入图像的完整 EXIF / IPTC / XMP。
- **前后对比**：底部 `A/B` 开关 + 滑条，在同一画面上用竖直分割线对比原图与模拟结果；左=输入，右=输出。
- **系统设置**：「设置 → 系统」类别集中管理界面语言与 GPU 加速，修改后重启生效。
- **窗口与任务栏图标**：补齐多尺寸应用图标。
- **RAW 分级加载**：先以半尺寸快速预览显示（约 1 秒），后台线程再完成全分辨率加载，避免界面长时间无响应。

### 性能与正确性

- RAW 色彩链（白平衡色适应、ACES→输出色彩空间）改为预计算 3×3 矩阵 + einsum，**数值逐位一致**（最大误差 ≤9e-16）；真实 61 MP ARW 完整加载 9.75 s → 4.9 s。
- 扫描色彩链的 RGB↔XYZ 转换同样矩阵化，覆盖 5 种色域压缩算法。
- 新增 `test_fast_color.py` 锁定与 colour-science 的逐位一致性。

### 说明

- 语言与 GPU 选择保存在用户配置中，重启程序生效。
- GPU 需要 NVIDIA 显卡与支持 CUDA 12.x 的驱动；不可用时自动回退 CPU。
- 启动失败时会在程序目录生成 `spektrafilm_crash.log`。
- 许可证：GPL-3.0-or-later；profiles/LUT 数据 CC BY-SA 4.0。本项目为非官方分支，与上游作者无隶属或背书关系。

**完整更新日志**：https://github.com/jjingith/spektrafilm/commits/zh-cn-gpu
