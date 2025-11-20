# CVF论文爬虫工具

一个用于从CVF (Computer Vision Foundation) 网站批量抓取计算机视觉会议论文的Python工具。支持抓取论文元数据（标题、摘要、链接）和PDF文件。

## 支持的会议

- **CVPR** - IEEE/CVF Conference on Computer Vision and Pattern Recognition
- **ICCV** - IEEE/CVF International Conference on Computer Vision
- **WACV** - IEEE/CVF Winter Conference on Applications of Computer Vision
- **ECCV** - European Conference on Computer Vision
- **ACCV** - Asian Conference on Computer Vision

## 功能特性

- ✅ 支持多个会议同时抓取
- ✅ 自定义年份范围
- ✅ 自动适应不同的URL结构（智能检测并切换抓取策略）
- ✅ 可选PDF文件下载
- ✅ 数据导出为Excel格式（.xlsx）
- ✅ 按会议和年份分sheet存储
- ✅ 自定义输出目录
- ✅ 断点续传（中途中断可继续）
- ✅ 自动跳过已下载的PDF

## 安装依赖

```bash
pip install -r requirements.txt
```

依赖包：
- `requests` - HTTP请求
- `beautifulsoup4` - HTML解析
- `pandas` - 数据处理
- `openpyxl` - Excel文件读写

## 使用方法

### 基本用法

```bash
# 抓取CVPR 2020-2022年的论文元数据
python scrape_cvpr.py --conference CVPR --start-year 2020 --end-year 2022
```

### 抓取多个会议

```bash
# 同时抓取CVPR和ICCV 2021-2023年的论文
python scrape_cvpr.py --conference CVPR ICCV --start-year 2021 --end-year 2023
```

### 下载PDF文件

```bash
# 抓取元数据并下载PDF
python scrape_cvpr.py --conference CVPR --start-year 2020 --end-year 2022 --download-pdf
```

### 自定义输出目录

```bash
# 指定Excel和PDF的保存目录
python scrape_cvpr.py --conference CVPR --start-year 2020 --end-year 2022 \
  --output-dir data --pdf-dir papers --download-pdf
```

### 完整示例

```bash
# 抓取多个会议，下载PDF，自定义目录
python scrape_cvpr.py \
  --conference CVPR ICCV ECCV \
  --start-year 2020 \
  --end-year 2023 \
  --download-pdf \
  --output-dir ./my_data \
  --pdf-dir ./my_pdfs
```

## 命令行参数

| 参数 | 简写 | 说明 | 默认值 | 必需 |
|------|------|------|--------|------|
| `--conference` | `-c` | 要抓取的会议名称，可指定多个 | - | 是 |
| `--start-year` | `-s` | 起始年份（包含） | - | 是 |
| `--end-year` | `-e` | 结束年份（包含） | - | 是 |
| `--output-dir` | `-od` | Excel文件保存目录 | `xlsx` | 否 |
| `--download-pdf` | `-dp` | 是否下载PDF文件 | `False` | 否 |
| `--pdf-dir` | `-pd` | PDF文件保存目录（需配合`--download-pdf`使用） | `pdf` | 否 |

## 输出格式

### Excel文件结构

- **文件名格式**：`{会议名}_{起始年}_{结束年}.xlsx`
  - 例如：`CVPR_2020_2022.xlsx` 或 `CVPR_ICCV_2021_2023.xlsx`

- **Sheet命名**：`{会议名}_{年份}`
  - 例如：`CVPR_2020`, `CVPR_2021`, `ICCV_2022`

- **列信息**：
  - `Conference` - 会议名称
  - `Year` - 年份
  - `Title` - 论文标题
  - `Abstract` - 摘要
  - `URL` - 论文详情页链接
  - `PDF_URL` - PDF下载链接
  - `PDF_Path` - 本地PDF保存路径（如已下载）

### PDF文件命名

- **格式**：`{会议名}_{年份}_{论文标题}.pdf`
- **示例**：`CVPR_2022_Deep Learning for Computer Vision.pdf`
- 文件名自动清理特殊字符，限制长度为200字符

## 目录结构

```
scrape_cvf/
├── scrape_cvpr.py          # 主程序
├── requirements.txt        # 依赖列表
├── README.MD              # 说明文档
├── xlsx/                  # Excel输出目录（默认）
│   └── CVPR_2020_2022.xlsx
└── pdf/                   # PDF下载目录（默认）
    ├── CVPR_2020_Paper1.pdf
    ├── CVPR_2020_Paper2.pdf
    └── ...
```

## 注意事项

1. **网络连接**：需要稳定的网络连接访问 `openaccess.thecvf.com`
2. **抓取速度**：每篇论文需要请求详情页，速度取决于网络和服务器响应
3. **存储空间**：下载PDF会占用大量磁盘空间（每篇论文约5-20MB）
4. **断点续传**：程序会在每完成一个会议年份后保存进度
5. **PDF去重**：已存在的PDF文件会自动跳过，不会重复下载
6. **礼貌抓取**：代码中预留了`time.sleep()`选项，如需更礼貌地访问可取消注释

## 常见问题

**Q: 为什么有些年份抓取失败？**  
A: 程序会自动检测URL结构并切换策略。如果某个会议年份的页面结构不同，可能需要手动检查CVF网站。

**Q: 可以中途停止后继续吗？**  
A: 可以。程序每完成一个会议年份后会保存进度到Excel文件。重新运行时会继续抓取剩余的会议年份，已下载的PDF会自动跳过。

**Q: Excel文件太大怎么办？**  
A: 可以缩小年份范围或分批次抓取不同会议。

**Q: 如何只更新PDF而不重新抓取元数据？**  
A: 目前不支持。建议保留已有的Excel文件，使用相同参数运行并加上`--download-pdf`，程序会跳过已存在的PDF。

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 更新日志

- **v1.0** (2025-11-20)
  - 初始版本发布
  - 支持5个CVF会议
  - 支持元数据抓取和PDF下载
  - 智能URL结构检测
  - Excel多sheet输出