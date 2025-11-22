# CVPR数据填充说明

## 项目概述
该项目用于检查和填充 `CVPR_xlsx/CVPR_2013_2025.xlsx` 文件中的空单元格。

## 主要功能

### `fix_all_empty_cells.py` 脚本功能:
1. **检查空单元格**: 遍历每个sheet,识别空的Abstract、PDF_URL和PDF_Path字段
2. **从网站获取数据**: 从 https://openaccess.thecvf.com/ 抓取缺失的Abstract和PDF_URL
3. **处理PDF文件**:
   - 首先在 `CVPR_pdf/` 文件夹中查找已存在的PDF
   - 如果没找到,从网站下载PDF到 `CVPR_pdf/` 文件夹
   - 填充PDF_Path字段

## 当前处理状态

### 已完成的年份:
- ✅ CVPR_2013: 无空单元格
- ✅ CVPR_2014: 57个PDF路径已填充
- ✅ CVPR_2015: 1个PDF路径已填充
- ✅ CVPR_2016: 无空单元格
- ✅ CVPR_2017: 1个PDF路径已填充
- ✅ CVPR_2018: 无空单元格
- ✅ CVPR_2019: 无空单元格

### 待处理的年份:
- 🔄 CVPR_2020: 1个Abstract, 1466个PDF_URL, 1466个PDF_Path (正在处理中)
- ⏳ CVPR_2021: 1个Abstract, 1660个PDF_URL, 1660个PDF_Path
- ⏳ CVPR_2022: 3个Abstract, 2074个PDF_URL, 2074个PDF_Path
- ⏳ CVPR_2023: 0个Abstract, 2353个PDF_URL, 2353个PDF_Path
- ⏳ CVPR_2024: 5个Abstract, 2716个PDF_URL, 2716个PDF_Path
- ⏳ CVPR_2025: 0个Abstract, 2871个PDF_URL, 2871个PDF_Path

## 使用方法

### 1. 单独处理某一年:
```bash
python3 fix_all_empty_cells.py --start-year 2020 --end-year 2020
```

### 2. 处理年份范围:
```bash
python3 fix_all_empty_cells.py --start-year 2020 --end-year 2025
```

### 3. Dry Run模式(只检查不修改):
```bash
python3 fix_all_empty_cells.py --dry-run
```

### 4. 不下载PDF(只填充Abstract和PDF_URL):
```bash
python3 fix_all_empty_cells.py --no-download-pdf
```

### 5. 批量处理所有年份(推荐):
```bash
bash process_all_years.sh
```

### 6. 后台运行(处理大量数据时):
```bash
nohup python3 fix_all_empty_cells.py --start-year 2020 --end-year 2025 > fix.log 2>&1 &
```

## 查看后台进程进度

### 查看日志:
```bash
tail -f fix_2020.log
```

### 查看进程状态:
```bash
ps aux | grep fix_all_empty_cells
```

### 检查已处理的条目数:
```bash
grep "✅" fix_2020.log | wc -l
```

### 停止后台进程:
```bash
kill <PID>
```

## 文件说明

### 输入文件:
- `CVPR_xlsx/CVPR_2013_2025.xlsx`: 原始Excel文件

### 输出文件:
- `CVPR_xlsx/CVPR_2013_2025_fixed.xlsx`: 修复后的Excel文件

### PDF文件夹:
- `CVPR_pdf/`: 存储所有下载的PDF文件

### 备份文件:
- `CVPR_xlsx/CVPR_2013_2025_backup.xlsx`: 原始文件的备份(由process_all_years.sh创建)

## 注意事项

1. **处理时间**: 
   - 2020-2025年每年有1400-2800+篇论文
   - 每篇需要访问网页(~1-2秒) + 可能下载PDF(~5-10秒)
   - 预计每年需要2-6小时
   - 总计可能需要12-36小时

2. **网络要求**:
   - 需要稳定的网络连接
   - 建议使用后台进程(`nohup`)避免终端关闭导致中断

3. **磁盘空间**:
   - 每个PDF平均约1-2MB
   - 总共约13140篇论文,预计需要13-26GB空间

4. **继续处理**:
   - 脚本会自动跳过已处理的条目
   - 可以安全地重新运行脚本,它会从中断点继续

## 当前运行状态

当前正在后台处理2020年的数据:
- 进程ID: 34513
- 日志文件: fix_2020.log

查看进度:
```bash
tail -f /home/sunhan/scrape_cvf/fix_2020.log
```

## 后续步骤

处理完2020年后,依次处理:
```bash
# 等2020年完成后
python3 fix_all_empty_cells.py --start-year 2021 --end-year 2021

# 或者直接运行批处理脚本
bash process_all_years.sh
```

## 完成后验证

```bash
python3 << 'EOF'
import pandas as pd

xl = pd.ExcelFile('CVPR_xlsx/CVPR_2013_2025_fixed.xlsx')
print("验证结果:")
for sheet in xl.sheet_names:
    df = pd.read_excel('CVPR_xlsx/CVPR_2013_2025_fixed.xlsx', sheet_name=sheet)
    empty = (df.isna() | (df.astype(str) == '')).sum().sum()
    if empty > 0:
        print(f"  {sheet}: 仍有 {empty} 个空单元格")
    else:
        print(f"  {sheet}: ✅ 完美")
EOF
```
