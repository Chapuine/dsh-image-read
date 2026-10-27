# dsh-image-read

用于 dsh（DeepSeek Harness）的图片读取 Skill：从图片中提取文字（OCR），或理解并描述图片内容（视觉理解）。直接复用 dsh 当前调用的用户自身 DeepSeek 模型读图，**无需第三方 API**。

## 功能特性

- **OCR 文字提取**：截图、单据、合同、报表、扫描件、证件、聊天记录等文字类图片
- **视觉理解**：照片、产品图、流程图、海报、界面截图等内容类图片
- **混合模式**：按图片类型自动选择，或同时输出文字与内容描述
- **图片预处理脚本**：格式校验、EXIF 摆正、透明通道白底合成、JPEG/PNG 转换、超长图重叠切片、等比降采样，保证大图和长截图也能被模型完整读取

## 目录结构

```
dsh-image-read/
├── SKILL.md                 # Skill 定义：读图工作流与输出规范
└── scripts/
    └── read_image.py        # 图片预处理脚本（Python 3 + Pillow）
```

## 安装

将本仓库克隆或下载后，把 `dsh-image-read` 文件夹放入 dsh 的 skills 目录（常见位置如 `~/.dsh/skills/`，以你的 dsh 配置为准），重启 dsh 即可生效。

## 使用

对 dsh 说类似的话即可触发本 Skill：

- “读取这张图片里的文字” / “帮我 OCR 这张截图”
- “描述这张图片的内容” / “这张照片里是什么”
- “把这张发票/单据转成文字”
- “这张图片和那份报表的数据对一下”

预处理脚本也可单独使用：

```bash
python3 dsh-image-read/scripts/read_image.py <图片路径> --output-dir <输出目录>
# 超长截图/长图：默认按高度 4096px 重叠切片（重叠 200px）
# 保留透明通道：加 --keep-format
# 调整上限：--max-size 2048 / --split-height 4096 / --overlap 200
```

## 依赖

- Python 3
- Pillow（`pip install Pillow`）

## 注意事项

- 需要 dsh 当前模型支持图像输入；模型不支持读图时，Skill 会明确告知而不是编造内容
- 处理含隐私或敏感信息的图片时，仅输出与任务相关的内容
