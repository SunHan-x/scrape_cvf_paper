#!/usr/bin/env python3
"""
增强版空单元格修复脚本
- 填充空的Abstract、PDF_URL
- 检查CVPR_pdf文件夹中是否已有PDF，如果没有则下载
- 填充PDF_Path字段
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urljoin
import argparse
import os
import re

BASE_URL = "https://openaccess.thecvf.com/"
PDF_DIR = "CVPR_pdf"

def get_paper_details(paper_url):
    """
    从论文详情页获取摘要和PDF URL
    """
    try:
        response = requests.get(paper_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 提取摘要
        abstract_div = soup.find('div', id='abstract')
        abstract = abstract_div.get_text(strip=True) if abstract_div else ""
        
        # 移除前导的 "Abstract" 标签
        if abstract.startswith("Abstract"):
            abstract = abstract[len("Abstract"):].strip()
        
        # 提取PDF URL
        pdf_url = ""
        pdf_link = soup.find('a', href=lambda x: x and x.endswith('.pdf'))
        if pdf_link:
            pdf_url = urljoin(BASE_URL, pdf_link['href'])
        
        return abstract, pdf_url

    except Exception as e:
        print(f"    ❌ 错误: {e}")
        return None, None

def sanitize_filename(filename):
    """
    清理文件名，移除非法字符
    """
    # 移除或替换非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # 限制长度
    if len(filename) > 200:
        filename = filename[:200]
    return filename.strip()

def find_existing_pdf(pdf_dir, title, year):
    """
    在PDF目录中查找已存在的PDF文件
    """
    if not os.path.exists(pdf_dir):
        return None
    
    # 尝试多种可能的文件名格式
    possible_names = [
        f"CVPR_{year}_{title}.pdf",
        f"CVPR_{year}_{sanitize_filename(title)}.pdf",
    ]
    
    for filename in possible_names:
        filepath = os.path.join(pdf_dir, filename)
        if os.path.exists(filepath):
            return filepath
    
    # 如果精确匹配失败，尝试模糊匹配
    sanitized_title = sanitize_filename(title).lower()
    for filename in os.listdir(pdf_dir):
        if filename.startswith(f"CVPR_{year}_") and filename.endswith(".pdf"):
            # 检查标题是否在文件名中
            file_title = filename[len(f"CVPR_{year}_"):-4].lower()
            if sanitized_title in file_title or file_title in sanitized_title:
                return os.path.join(pdf_dir, filename)
    
    return None

def download_pdf(pdf_url, pdf_dir, title, year):
    """
    下载PDF文件
    """
    try:
        os.makedirs(pdf_dir, exist_ok=True)
        
        # 生成文件名
        safe_title = sanitize_filename(title)
        filename = f"CVPR_{year}_{safe_title}.pdf"
        filepath = os.path.join(pdf_dir, filename)
        
        # 如果文件已存在，跳过下载
        if os.path.exists(filepath):
            print(f"    ✓ PDF已存在")
            return filepath
        
        # 下载PDF
        print(f"    ⬇️  下载PDF...")
        response = requests.get(pdf_url, timeout=30, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"    ✅ PDF下载成功")
        return filepath
        
    except Exception as e:
        print(f"    ❌ PDF下载失败: {e}")
        return None

def fix_empty_cells(input_file, output_file, pdf_dir, start_year=2013, end_year=2025, 
                   dry_run=False, download_pdfs=True):
    """
    修复Excel文件中的空单元格
    
    Args:
        input_file: 输入Excel文件路径
        output_file: 输出Excel文件路径
        pdf_dir: PDF文件夹路径
        start_year: 开始年份
        end_year: 结束年份
        dry_run: 如果为True，只检查不修改
        download_pdfs: 是否下载缺失的PDF
    """
    print("=" * 80)
    print(f"增强版空单元格修复脚本 - {start_year}年至{end_year}年")
    print("=" * 80)
    print()
    
    if dry_run:
        print("⚠️  DRY RUN 模式 - 只检查，不修改文件")
        print()
    
    # 读取所有sheet
    df_dict = pd.read_excel(input_file, sheet_name=None)
    
    # 统计信息
    stats = {
        'abstract_fixed': 0,
        'abstract_failed': 0,
        'pdf_url_fixed': 0,
        'pdf_url_failed': 0,
        'pdf_path_found': 0,
        'pdf_path_downloaded': 0,
        'pdf_path_failed': 0,
    }
    
    sheets_modified = {}
    
    for sheet_name, df in df_dict.items():
        year = int(sheet_name.split('_')[1])
        
        # 只处理指定年份范围
        if year < start_year or year > end_year:
            sheets_modified[sheet_name] = df
            continue
        
        print(f"\n{'='*70}")
        print(f"📅 处理 {sheet_name} (共 {len(df)} 篇论文)")
        print(f"{'='*70}")
        
        # 检查各种空值
        empty_abstract_mask = df['Abstract'].isna() | (df['Abstract'].astype(str).str.strip() == '') | (df['Abstract'].astype(str) == 'nan')
        empty_pdf_url_mask = df['PDF_URL'].isna() | (df['PDF_URL'].astype(str).str.strip() == '') | (df['PDF_URL'].astype(str) == 'nan')
        empty_pdf_path_mask = df['PDF_Path'].isna() | (df['PDF_Path'].astype(str).str.strip() == '') | (df['PDF_Path'].astype(str) == 'nan')
        
        empty_abstract_count = empty_abstract_mask.sum()
        empty_pdf_url_count = empty_pdf_url_mask.sum()
        empty_pdf_path_count = empty_pdf_path_mask.sum()
        
        print(f"  空Abstract: {empty_abstract_count}")
        print(f"  空PDF_URL: {empty_pdf_url_count}")
        print(f"  空PDF_Path: {empty_pdf_path_count}")
        
        if empty_abstract_count == 0 and empty_pdf_url_count == 0 and empty_pdf_path_count == 0:
            print(f"  ✅ 无需修复")
            sheets_modified[sheet_name] = df
            continue
        
        # 创建副本以便修改
        df_fixed = df.copy()
        
        # 确保列的数据类型正确,避免pandas警告
        if df_fixed['PDF_URL'].dtype != 'object':
            df_fixed['PDF_URL'] = df_fixed['PDF_URL'].astype('object')
        if df_fixed['PDF_Path'].dtype != 'object':
            df_fixed['PDF_Path'] = df_fixed['PDF_Path'].astype('object')
        
        # 找出需要修复的行
        needs_fix_mask = empty_abstract_mask | empty_pdf_url_mask | empty_pdf_path_mask
        needs_fix_indices = df[needs_fix_mask].index.tolist()
        
        print(f"  需要处理 {len(needs_fix_indices)} 行")
        print()
        
        for idx, row_idx in enumerate(needs_fix_indices, 1):
            row = df.loc[row_idx]
            title = row['Title']
            url = row['URL']
            
            print(f"  [{idx}/{len(needs_fix_indices)}] 处理: {title[:50]}...")
            
            if dry_run:
                print(f"    [DRY RUN] 将访问: {url}")
                continue
            
            # 检查是否需要从网站获取信息
            need_web_data = empty_abstract_mask[row_idx] or empty_pdf_url_mask[row_idx]
            
            abstract = None
            pdf_url = None
            
            if need_web_data:
                # 从网站获取摘要和PDF URL
                abstract, pdf_url = get_paper_details(url)
                
                # 更新Abstract
                if empty_abstract_mask[row_idx]:
                    if abstract:
                        df_fixed.loc[row_idx, 'Abstract'] = abstract
                        stats['abstract_fixed'] += 1
                        print(f"    ✅ Abstract已更新 ({len(abstract)} 字符)")
                    else:
                        stats['abstract_failed'] += 1
                        print(f"    ⚠️  Abstract获取失败")
                
                # 更新PDF_URL
                if empty_pdf_url_mask[row_idx]:
                    if pdf_url:
                        df_fixed.loc[row_idx, 'PDF_URL'] = pdf_url
                        stats['pdf_url_fixed'] += 1
                        print(f"    ✅ PDF_URL已更新")
                    else:
                        stats['pdf_url_failed'] += 1
                        print(f"    ⚠️  PDF_URL获取失败")
                
                time.sleep(0.5)  # 避免请求过快
            else:
                # 如果不需要从网站获取，使用现有的PDF_URL
                pdf_url = row['PDF_URL'] if not empty_pdf_url_mask[row_idx] else None
            
            # 处理PDF_Path
            if empty_pdf_path_mask[row_idx]:
                # 先查找是否已有PDF文件
                existing_pdf = find_existing_pdf(pdf_dir, title, year)
                
                if existing_pdf:
                    df_fixed.loc[row_idx, 'PDF_Path'] = existing_pdf
                    stats['pdf_path_found'] += 1
                    print(f"    ✅ 找到已存在的PDF")
                elif download_pdfs and pdf_url:
                    # 下载PDF
                    downloaded_path = download_pdf(pdf_url, pdf_dir, title, year)
                    if downloaded_path:
                        df_fixed.loc[row_idx, 'PDF_Path'] = downloaded_path
                        stats['pdf_path_downloaded'] += 1
                    else:
                        stats['pdf_path_failed'] += 1
                else:
                    stats['pdf_path_failed'] += 1
                    if not pdf_url:
                        print(f"    ⚠️  无PDF_URL，无法下载")
                    elif not download_pdfs:
                        print(f"    ⚠️  未启用PDF下载")
        
        sheets_modified[sheet_name] = df_fixed
    
    # 保存结果
    if not dry_run:
        print("\n" + "=" * 80)
        print("💾 保存修复后的文件...")
        print("=" * 80)
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for sheet_name, df in sheets_modified.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f"✅ 已保存到: {output_file}")
    
    # 打印统计信息
    print("\n" + "=" * 80)
    print("修复统计")
    print("=" * 80)
    print(f"Abstract - 成功: {stats['abstract_fixed']}, 失败: {stats['abstract_failed']}")
    print(f"PDF_URL - 成功: {stats['pdf_url_fixed']}, 失败: {stats['pdf_url_failed']}")
    print(f"PDF_Path - 找到已存在: {stats['pdf_path_found']}, 新下载: {stats['pdf_path_downloaded']}, 失败: {stats['pdf_path_failed']}")
    print(f"总成功: {stats['abstract_fixed'] + stats['pdf_url_fixed'] + stats['pdf_path_found'] + stats['pdf_path_downloaded']}")
    print(f"总失败: {stats['abstract_failed'] + stats['pdf_url_failed'] + stats['pdf_path_failed']}")
    print()

def parse_arguments():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(
        description='修复CVPR Excel文件中的空单元格，包括下载PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 先运行dry run检查
  python fix_all_empty_cells.py --dry-run
  
  # 修复所有年份（2013-2025）
  python fix_all_empty_cells.py
  
  # 只修复特定年份
  python fix_all_empty_cells.py --start-year 2020 --end-year 2025
  
  # 不下载PDF，只填充其他信息
  python fix_all_empty_cells.py --no-download-pdf
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='CVPR_xlsx/CVPR_2013_2025.xlsx',
        help='输入Excel文件路径 (默认: CVPR_xlsx/CVPR_2013_2025.xlsx)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='CVPR_xlsx/CVPR_2013_2025_fixed.xlsx',
        help='输出Excel文件路径 (默认: CVPR_xlsx/CVPR_2013_2025_fixed.xlsx)'
    )
    
    parser.add_argument(
        '--pdf-dir', '-p',
        type=str,
        default='CVPR_pdf',
        help='PDF文件夹路径 (默认: CVPR_pdf)'
    )
    
    parser.add_argument(
        '--start-year', '-s',
        type=int,
        default=2013,
        help='开始年份 (默认: 2013)'
    )
    
    parser.add_argument(
        '--end-year', '-e',
        type=int,
        default=2025,
        help='结束年份 (默认: 2025)'
    )
    
    parser.add_argument(
        '--no-download-pdf',
        action='store_true',
        help='不下载PDF文件'
    )
    
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='只检查不修改 (dry run模式)'
    )
    
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    print(f"配置:")
    print(f"  输入文件: {args.input}")
    print(f"  输出文件: {args.output}")
    print(f"  PDF目录: {args.pdf_dir}")
    print(f"  年份范围: {args.start_year} - {args.end_year}")
    print(f"  下载PDF: {not args.no_download_pdf}")
    print(f"  Dry Run: {args.dry_run}")
    print()
    
    fix_empty_cells(
        input_file=args.input,
        output_file=args.output,
        pdf_dir=args.pdf_dir,
        start_year=args.start_year,
        end_year=args.end_year,
        dry_run=args.dry_run,
        download_pdfs=not args.no_download_pdf
    )

if __name__ == "__main__":
    main()
