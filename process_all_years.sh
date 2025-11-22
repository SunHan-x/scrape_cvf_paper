#!/bin/bash

# 分批处理所有年份的脚本
# 每处理完一个年份，就更新输入文件

cd /home/sunhan/scrape_cvf

echo "开始批量处理所有年份..."
echo "========================================"

# 首先备份原始文件
if [ ! -f "CVPR_xlsx/CVPR_2013_2025_backup.xlsx" ]; then
    cp "CVPR_xlsx/CVPR_2013_2025.xlsx" "CVPR_xlsx/CVPR_2013_2025_backup.xlsx"
    echo "✅ 已备份原始文件"
fi

# 定义要处理的年份
years=(2015 2017 2020 2021 2022 2023 2024 2025)

for year in "${years[@]}"; do
    echo ""
    echo "========================================"
    echo "处理 $year 年..."
    echo "========================================"
    
    # 定义日志文件
    log_file="fix_${year}.log"
    
    # 运行修复脚本，输出到日志文件和终端
    python3 fix_all_empty_cells.py --start-year $year --end-year $year 2>&1 | tee "$log_file"
    
    if [ $? -eq 0 ]; then
        echo "✅ $year 年处理完成"
        echo "📝 日志已保存到: $log_file"
        # 更新输入文件
        cp "CVPR_xlsx/CVPR_2013_2025_fixed.xlsx" "CVPR_xlsx/CVPR_2013_2025.xlsx"
        echo "✅ 已更新输入文件"
    else
        echo "❌ $year 年处理失败,退出"
        echo "📝 错误日志已保存到: $log_file"
        exit 1
    fi
done

echo ""
echo "========================================"
echo "所有年份处理完成！"
echo "========================================"
echo "最终文件: CVPR_xlsx/CVPR_2013_2025_fixed.xlsx"
echo "备份文件: CVPR_xlsx/CVPR_2013_2025_backup.xlsx"
