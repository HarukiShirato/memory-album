# 网站图片放置说明

## 1) 图片放哪里

把你要展示的图片放到这个目录：

`assets/photos/`

例如：

- `assets/photos/life_001.jpg`
- `assets/photos/trip_2025_10.png`

## 2) 网站如何读取图片

网站会读取 `assets/gallery.json`，你只要在这个文件里添加照片条目即可。

格式示例：

```json
{
  "photos": [
    {
      "src": "./assets/photos/life_001.jpg",
      "title": "校园午后",
      "date": "2026-03-12"
    },
    {
      "src": "./assets/photos/trip_2025_10.png",
      "title": "海边日落",
      "date": "2025-10-06"
    }
  ]
}
```

## 3) 注意事项

- `src` 路径建议用 `./assets/photos/文件名`
- 文件名尽量用英文、数字、下划线
- 图片太大时，建议先压缩再上传（单张 300KB-1MB 更合适）
- 改完 `gallery.json` 后提交到 GitHub，Pages 会自动更新
