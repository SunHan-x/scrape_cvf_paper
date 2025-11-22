import requests
from bs4 import BeautifulSoup
import pandas as pd
import random
import time
from urllib.parse import urljoin

BASE_URL = "https://openaccess.thecvf.com/"

def get_paper_count_from_website(year):
    """
    从网站获取指定年份的论文总数
    """
    # 先尝试使用 day=all
    url_all = f"{BASE_URL}CVPR{year}?day=all"
    try:
        response = requests.get(url_all, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有论文标题
        dt_elements = soup.find_all('dt', class_='ptitle')
        
        if len(dt_elements) > 0:
            # day=all 成功
            return len(dt_elements)
        
        # day=all 返回0,尝试获取各个day的论文数
        print(f"    day=all 无效,尝试逐天获取...")
        return get_paper_count_by_days(year)
        
    except Exception as e:
        print(f"  ❌ 获取 {year} 年论文数失败: {e}")
        return None

def get_paper_count_by_days(year):
    """
    通过逐天获取来统计论文总数(当day=all不可用时)
    """
    main_url = f"{BASE_URL}CVPR{year}"
    
    try:
        response = requests.get(main_url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有day链接
        day_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '?day=' in href and href not in day_links:
                day_links.append(href)
        
        if not day_links:
            print(f"    ⚠️  未找到day链接")
            return None
        
        total_papers = 0
        for link in day_links:
            full_url = urljoin(BASE_URL, link)
            try:
                response = requests.get(full_url, timeout=20)
                response.raise_for_status()
                day_soup = BeautifulSoup(response.text, 'html.parser')
                dt_elements = day_soup.find_all('dt', class_='ptitle')
                count = len(dt_elements)
                total_papers += count
                
                # 提取day名称
                day_name = link.split('day=')[1].split('&')[0] if '&' in link.split('day=')[1] else link.split('day=')[1]
                print(f"      {day_name}: {count} 篇")
                
                time.sleep(0.3)  # 避免请求过快
            except Exception as e:
                print(f"    ⚠️  获取 {link} 失败: {e}")
        
        return total_papers
        
    except Exception as e:
        print(f"    ❌ 获取主页面失败: {e}")
        return None

def verify_paper_details(paper_url, expected_title, expected_abstract):
    """
    验证单篇论文的详细信息
    """
    try:
        response = requests.get(paper_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 提取标题
        title_elem = soup.find('div', id='papertitle')
        actual_title = title_elem.get_text(strip=True) if title_elem else ""
        
        # 提取摘要
        abstract_div = soup.find('div', id='abstract')
        actual_abstract = abstract_div.get_text(strip=True) if abstract_div else ""
        
        # 移除 "Abstract" 标签
        if actual_abstract.startswith("Abstract"):
            actual_abstract = actual_abstract[len("Abstract"):].strip()
        
        # 验证标题
        title_match = actual_title.strip() == expected_title.strip()
        
        # 验证摘要（允许一定的格式差异）
        abstract_match = actual_abstract.strip() == expected_abstract.strip()
        
        return {
            'title_match': title_match,
            'abstract_match': abstract_match,
            'actual_title': actual_title,
            'actual_abstract': actual_abstract[:100] + '...' if len(actual_abstract) > 100 else actual_abstract
        }
    except Exception as e:
        return {
            'title_match': False,
            'abstract_match': False,
            'error': str(e)
        }

def main():
    print("=" * 80)
    print("CVPR 数据验证报告")
    print("=" * 80)
    print()
    
    # 读取 Excel 文件
    excel_path = 'CVPR_xlsx/CVPR_2013_2025.xlsx'
    print(f"📂 读取文件: {excel_path}")
    
    try:
        df_dict = pd.read_excel(excel_path, sheet_name=None)
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return
    
    print(f"✅ 成功读取 {len(df_dict)} 个sheet")
    print()
    
    # 第一部分：验证论文数量
    print("=" * 80)
    print("第一部分：验证各年份论文数量")
    print("=" * 80)
    print()
    
    count_results = []
    
    for sheet_name, df in df_dict.items():
        year = sheet_name.split('_')[1]
        excel_count = len(df)
        
        print(f"📅 验证 {year} 年...")
        print(f"  Excel中的论文数: {excel_count}")
        
        website_count = get_paper_count_from_website(year)
        
        if website_count is not None:
            print(f"  网站上的论文数: {website_count}")
            match = excel_count == website_count
            diff = excel_count - website_count
            
            if match:
                print(f"  ✅ 数量一致")
            else:
                print(f"  ⚠️  数量不一致 (差异: {diff:+d})")
            
            count_results.append({
                '年份': year,
                'Excel数量': excel_count,
                '网站数量': website_count,
                '差异': diff,
                '是否一致': '✅' if match else '❌'
            })
        else:
            count_results.append({
                '年份': year,
                'Excel数量': excel_count,
                '网站数量': 'N/A',
                '差异': 'N/A',
                '是否一致': '❌'
            })
        
        print()
        time.sleep(1)  # 避免请求过快
    
    # 第二部分：抽样验证论文信息
    print("=" * 80)
    print("第二部分：抽样验证论文详细信息 (每年20篇)")
    print("=" * 80)
    print()
    
    sample_results = []
    
    for sheet_name, df in df_dict.items():
        year = sheet_name.split('_')[1]
        print(f"📅 验证 {year} 年的论文详情...")
        
        # 随机抽取20篇（如果论文数不足20篇，则全部抽取）
        sample_size = min(20, len(df))
        sample_indices = random.sample(range(len(df)), sample_size)
        
        year_correct = 0
        year_total = 0
        
        for idx in sample_indices:
            paper = df.iloc[idx]
            year_total += 1
            
            print(f"  [{year_total}/{sample_size}] 验证: {paper['Title'][:50]}...")
            
            result = verify_paper_details(
                paper['URL'],
                paper['Title'],
                paper['Abstract']
            )
            
            if 'error' in result:
                print(f"    ❌ 验证失败: {result['error']}")
                sample_results.append({
                    '年份': year,
                    '论文标题': paper['Title'][:50] + '...',
                    '标题匹配': '❌',
                    '摘要匹配': '❌',
                    '错误': result['error']
                })
            else:
                title_status = '✅' if result['title_match'] else '❌'
                abstract_status = '✅' if result['abstract_match'] else '❌'
                
                print(f"    标题: {title_status}")
                print(f"    摘要: {abstract_status}")
                
                if result['title_match'] and result['abstract_match']:
                    year_correct += 1
                    print(f"    ✅ 信息正确")
                else:
                    print(f"    ⚠️  信息不匹配")
                    if not result['title_match']:
                        print(f"      期望标题: {paper['Title'][:50]}")
                        print(f"      实际标题: {result['actual_title'][:50]}")
                
                sample_results.append({
                    '年份': year,
                    '论文标题': paper['Title'][:50] + '...',
                    '标题匹配': title_status,
                    '摘要匹配': abstract_status,
                    '错误': ''
                })
            
            time.sleep(0.5)  # 避免请求过快
        
        accuracy = (year_correct / year_total * 100) if year_total > 0 else 0
        print(f"  📊 {year} 年准确率: {year_correct}/{year_total} ({accuracy:.1f}%)")
        print()
    
    # 生成汇总报告
    print("=" * 80)
    print("验证汇总报告")
    print("=" * 80)
    print()
    
    print("📊 论文数量对比:")
    count_df = pd.DataFrame(count_results)
    print(count_df.to_string(index=False))
    print()
    
    # 统计数量一致性
    match_count = sum(1 for r in count_results if r['是否一致'] == '✅')
    total_years = len(count_results)
    print(f"数量一致的年份: {match_count}/{total_years} ({match_count/total_years*100:.1f}%)")
    print()
    
    print("📋 抽样验证统计:")
    sample_df = pd.DataFrame(sample_results)
    
    # 统计每年的准确率
    for year in sorted(set(r['年份'] for r in sample_results)):
        year_samples = [r for r in sample_results if r['年份'] == year]
        correct = sum(1 for r in year_samples if r['标题匹配'] == '✅' and r['摘要匹配'] == '✅')
        total = len(year_samples)
        print(f"  {year}: {correct}/{total} 正确 ({correct/total*100:.1f}%)")
    
    # 保存详细报告到Excel
    report_path = 'CVPR_xlsx/verification_report.xlsx'
    with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
        count_df.to_excel(writer, sheet_name='论文数量对比', index=False)
        sample_df.to_excel(writer, sheet_name='抽样验证详情', index=False)
    
    print()
    print(f"✅ 详细报告已保存至: {report_path}")

if __name__ == "__main__":
    main()
