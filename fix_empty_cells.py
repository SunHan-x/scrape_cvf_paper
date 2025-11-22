import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urljoin
import argparse

BASE_URL = "https://openaccess.thecvf.com/"

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

def fix_empty_cells(input_file, output_file, start_year=2013, end_year=2019, dry_run=False):
    """
    修复Excel文件中的空单元格
    
    Args:
        input_file: 输入Excel文件路径
        output_file: 输出Excel文件路径
        start_year: 开始年份
        end_year: 结束年份
        dry_run: 如果为True，只检查不修改
    """
    print("=" * 80)
    print(f"修复空单元格脚本 - {start_year}年至{end_year}年")
    print("=" * 80)
    print()
    
    if dry_run:
        print("⚠️  DRY RUN 模式 - 只检查，不修改文件")
        print()
    
    # 读取所有sheet
    df_dict = pd.read_excel(input_file, sheet_name=None)
    
    total_fixed = 0
    total_failed = 0
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
        
        # 检查空摘要
        empty_abstract_mask = df['Abstract'].isna() | (df['Abstract'].astype(str).str.strip() == '') | (df['Abstract'].astype(str) == 'nan')
        empty_abstract_count = empty_abstract_mask.sum()
        
        # 检查空PDF_URL
        empty_pdf_mask = df['PDF_URL'].isna() | (df['PDF_URL'].astype(str).str.strip() == '') | (df['PDF_URL'].astype(str) == 'nan')
        empty_pdf_count = empty_pdf_mask.sum()
        
        print(f"  发现 {empty_abstract_count} 个空摘要")
        print(f"  发现 {empty_pdf_count} 个空PDF_URL")
        
        if empty_abstract_count == 0 and empty_pdf_count == 0:
            print(f"  ✅ 无需修复")
            sheets_modified[sheet_name] = df
            continue
        
        # 找出需要修复的行（摘要或PDF_URL为空）
        needs_fix_mask = empty_abstract_mask | empty_pdf_mask
        needs_fix_indices = df[needs_fix_mask].index.tolist()
        
        print(f"  需要修复 {len(needs_fix_indices)} 行")
        print()
        
        # 创建副本以便修改
        df_fixed = df.copy()
        
        for idx, row_idx in enumerate(needs_fix_indices, 1):
            row = df.loc[row_idx]
            title = row['Title']
            url = row['URL']
            
            print(f"  [{idx}/{len(needs_fix_indices)}] 修复: {title[:60]}...")
            
            if dry_run:
                print(f"    [DRY RUN] 将访问: {url}")
                continue
            
            # 获取详情
            abstract, pdf_url = get_paper_details(url)
            
            if abstract is not None or pdf_url is not None:
                # 更新空摘要
                if empty_abstract_mask[row_idx] and abstract:
                    df_fixed.at[row_idx, 'Abstract'] = abstract
                    print(f"    ✅ 摘要已更新 ({len(abstract)} 字符)")
                elif empty_abstract_mask[row_idx]:
                    print(f"    ⚠️  摘要仍为空")
                    total_failed += 1
                
                # 更新空PDF_URL
                if empty_pdf_mask[row_idx] and pdf_url:
                    df_fixed.at[row_idx, 'PDF_URL'] = pdf_url
                    print(f"    ✅ PDF_URL已更新")
                elif empty_pdf_mask[row_idx]:
                    print(f"    ⚠️  PDF_URL仍为空")
                    total_failed += 1
                
                if abstract or pdf_url:
                    total_fixed += 1
            else:
                print(f"    ❌ 获取失败")
                total_failed += 1
            
            # 避免请求过快
            time.sleep(0.5)
        
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
    print(f"成功修复: {total_fixed} 处")
    print(f"修复失败: {total_failed} 处")
    print()

def parse_arguments():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(
        description='修复CVPR Excel文件中的空摘要和PDF链接',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 先运行dry run检查
  python fix_empty_cells.py --input CVPR_xlsx/CVPR_2013_2025.xlsx --dry-run
  
  # 修复2013-2019年的空单元格
  python fix_empty_cells.py --input CVPR_xlsx/CVPR_2013_2025.xlsx --output CVPR_xlsx/CVPR_2013_2025_fixed.xlsx
  
  # 只修复特定年份
  python fix_empty_cells.py --input CVPR_xlsx/CVPR_2013_2025.xlsx --output CVPR_xlsx/CVPR_2013_2025_fixed.xlsx --start-year 2014 --end-year 2015
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
        '--start-year', '-s',
        type=int,
        default=2013,
        help='开始年份 (默认: 2013)'
    )
    
    parser.add_argument(
        '--end-year', '-e',
        type=int,
        default=2019,
        help='结束年份 (默认: 2019)'
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
    print(f"  年份范围: {args.start_year} - {args.end_year}")
    print(f"  Dry Run: {args.dry_run}")
    print()
    
    fix_empty_cells(
        input_file=args.input,
        output_file=args.output,
        start_year=args.start_year,
        end_year=args.end_year,
        dry_run=args.dry_run
    )

if __name__ == "__main__":
    main()
