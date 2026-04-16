# 自动整理电子相册（本地版）

这个脚本系统会做 5 件事：

1. 扫描 `data/photos_raw/` 下的照片
2. 读取 EXIF 拍摄时间（没有就用文件修改时间）
3. 复制并重命名到 `output/organized/年/月/`
4. 导出 `metadata.csv` 和 `metadata.json`
5. 生成 `output/pdf/album.pdf`

## 1) 安装依赖

```powershell
python -m pip install reportlab pillow
```

## 2) 放入照片

- 把原始照片放入：`data/photos_raw/`
- 可以有子文件夹，脚本会递归扫描

## 3) 运行

```powershell
python scripts/build_album.py --input data/photos_raw --output output --title "我的生活相册" --per-page 4
```

参数说明：

- `--input` 原始照片目录
- `--output` 输出目录
- `--title` PDF 封面标题
- `--per-page` 每页图片数，可选：`1` `2` `4` `6`

## 4) 输出结果

- `output/organized/` 规范化后的照片目录
- `output/metadata/metadata.csv`
- `output/metadata/metadata.json`
- `output/pdf/album.pdf`

## 命名与分类规则

- 分类目录：`年/月`，例如：`2025/08/`
- 文件名：`YYYYMMDD_HHMMSS_序号.扩展名`
- 同秒多张照片会自动追加序号避免重名

## 备注

- 原始照片不会被修改，脚本是复制后整理。
- 如果你后续要做网站展示，可以直接读取 `metadata.json` + `output/organized/`。
