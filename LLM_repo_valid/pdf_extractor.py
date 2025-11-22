"""
PDF 代码链接提取器 - 从论文 PDF 中提取代码仓库链接
"""

import os
import re
from typing import List, Dict, Optional, Tuple
import pymupdf  # PyMuPDF
import requests
from bs4 import BeautifulSoup

from config import CODE_HOST_DOMAINS, CODE_KEYWORDS
from utils import is_valid_repo_url, normalize_url
from llm_client import llm_client


def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """
    从 PDF 中提取全文本
    
    Args:
        pdf_path: PDF 文件路径
        
    Returns:
        提取的文本，失败返回 None
    """
    if not os.path.exists(pdf_path):
        print(f"    ⚠️  PDF 文件不存在: {pdf_path}")
        return None
    
    try:
        doc = pymupdf.open(pdf_path)
        text = ""
        
        # 只提取前几页（通常代码链接在前面）
        max_pages = min(5, len(doc))
        
        for page_num in range(max_pages):
            page = doc[page_num]
            text += page.get_text()
        
        doc.close()
        return text
        
    except Exception as e:
        print(f"    ❌ PDF 提取失败: {e}")
        return None


def extract_urls_from_text(text: str) -> List[str]:
    """
    从文本中提取所有 URL，处理换行断开的 URL
    
    Args:
        text: 文本内容
        
    Returns:
        URL 列表
    """
    # 预处理：处理换行导致的 URL 断开
    # 先处理 https:// 或 http:// 后面紧跟换行的情况
    text = re.sub(r'(https?://[^\s<>"{}|\\^`\[\]]+?)\n\s*([a-zA-Z0-9\-_/\.]+)', r'\1\2', text)
    
    # URL 正则表达式 - 匹配 http:// 或 https:// 开头的 URL
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    
    urls = re.findall(url_pattern, text, re.IGNORECASE)
    
    # 清理 URL
    cleaned_urls = []
    for url in urls:
        # 移除尾部标点和常见的干扰字符
        url = url.rstrip('.,;:!?)\']»')
        # 移除可能的换行符
        url = url.replace('\n', '').replace('\r', '')
        
        # 检查 URL 是否基本有效
        if len(url) > 10 and '/' in url:
            # 简单验证：至少有协议和域名部分
            try:
                # 检查域名部分是否合理
                domain_part = url.split('//')[1].split('/')[0] if '//' in url else ''
                if '.' in domain_part and len(domain_part) > 3:
                    cleaned_urls.append(url)
            except:
                # 如果解析失败，仍然保留（可能是特殊格式）
                cleaned_urls.append(url)
    
    return list(set(cleaned_urls))  # 去重


def extract_github_from_project_page(url: str) -> Optional[str]:
    """
    从项目主页中提取 GitHub 链接
    
    Args:
        url: 项目主页 URL
        
    Returns:
        GitHub 链接，如果没找到返回 None
    """
    try:
        print(f"      🔗 访问项目页面: {url}")
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有链接
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # 检查是否是 GitHub 链接
            if 'github.com' in href.lower():
                # 标准化 URL
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    continue
                
                # 验证是否是有效的仓库链接
                if is_valid_repo_url(href, ['github.com']):
                    print(f"      ✅ 找到 GitHub 链接: {href}")
                    return normalize_url(href)
        
        return None
        
    except Exception as e:
        print(f"      ⚠️  访问项目页面失败: {e}")
        return None


def filter_code_urls(urls: List[str]) -> List[str]:
    """
    过滤出代码仓库 URL，并从项目主页提取 GitHub 链接
    
    Args:
        urls: URL 列表
        
    Returns:
        代码仓库 URL 列表
    """
    code_urls = []
    project_pages = []  # 可能是项目主页的 URL
    
    for url in urls:
        # 直接是代码仓库
        if is_valid_repo_url(url, CODE_HOST_DOMAINS):
            normalized = normalize_url(url)
            if normalized not in code_urls:
                code_urls.append(normalized)
        
        # 可能是项目主页（常见模式）
        elif any(pattern in url.lower() for pattern in [
            '.github.io',
            'github.io',
            'project',
            'page',
            'demo',
            'site'
        ]):
            # 避免明显不是项目页的链接
            if not any(skip in url.lower() for skip in ['arxiv.org', 'doi.org', 'youtube.com']):
                project_pages.append(url)
    
    # 如果没有直接找到代码链接，尝试从项目页提取
    if not code_urls and project_pages:
        print(f"    🔍 未找到直接代码链接，尝试从 {len(project_pages)} 个项目页面提取...")
        
        for page_url in project_pages[:3]:  # 最多尝试3个
            github_url = extract_github_from_project_page(page_url)
            if github_url and github_url not in code_urls:
                code_urls.append(github_url)
    
    return code_urls


def find_urls_with_context(text: str, urls: List[str]) -> List[Tuple[str, str]]:
    """
    找到 URL 及其上下文（用于判断是否是代码链接）
    
    Args:
        text: 文本内容
        urls: URL 列表
        
    Returns:
        (url, context) 元组列表
    """
    results = []
    
    for url in urls:
        # 找到 URL 在文本中的位置
        idx = text.find(url)
        if idx == -1:
            continue
        
        # 提取上下文（前后各100个字符）
        start = max(0, idx - 100)
        end = min(len(text), idx + len(url) + 100)
        context = text[start:end]
        
        results.append((url, context))
    
    return results


def is_likely_code_url(context: str) -> bool:
    """
    根据上下文判断 URL 是否可能是代码链接
    
    Args:
        context: URL 的上下文
        
    Returns:
        是否可能是代码链接
    """
    context_lower = context.lower()
    
    # 检查是否包含代码相关关键词
    for keyword in CODE_KEYWORDS:
        if keyword in context_lower:
            return True
    
    return False


def select_official_repo_with_llm(
    paper_data: Dict,
    candidate_urls: List[str]
) -> Optional[str]:
    """
    使用 LLM 从候选 URL 中选择最可能的官方实现
    
    Args:
        paper_data: 论文元数据
        candidate_urls: 候选 URL 列表
        
    Returns:
        选中的 URL，如果都不是返回 None
    """
    if not candidate_urls:
        return None
    
    if len(candidate_urls) == 1:
        return candidate_urls[0]
    
    # 构造 prompt
    urls_text = "\n".join([f"{i+1}. {url}" for i, url in enumerate(candidate_urls)])
    
    messages = [
        {
            "role": "system",
            "content": "You are a tool that picks the most likely official code repository for a computer vision paper. Reply in JSON format."
        },
        {
            "role": "user",
            "content": f"""Paper title: "{paper_data.get('title', '')}"
Venue: {paper_data.get('conference', '')} {paper_data.get('year', '')}
Abstract: "{paper_data.get('abstract', '')[:500]}..."

Found URLs in PDF:
{urls_text}

From these URLs, which one is MOST likely the official implementation of the paper?
Reply in JSON format:
{{
  "selected_url": "<url or null>",
  "reason": "brief explanation"
}}"""
        }
    ]
    
    response = llm_client.call_json(messages)
    
    if response and "selected_url" in response:
        selected_url = response["selected_url"]
        if selected_url and selected_url.lower() != "null":
            print(f"    🤖 LLM 选择: {selected_url}")
            print(f"       理由: {response.get('reason', 'N/A')}")
            return normalize_url(selected_url)
    
    return None


def extract_code_urls_from_pdf(
    pdf_path: str,
    paper_data: Dict,
    use_llm: bool = True
) -> Dict[str, any]:
    """
    从 PDF 中提取代码仓库 URL
    
    Args:
        pdf_path: PDF 文件路径
        paper_data: 论文元数据
        use_llm: 是否使用 LLM 来选择候选链接
        
    Returns:
        提取结果字典
    """
    print(f"  📄 从 PDF 提取代码链接...")
    
    # 1. 提取文本
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return {
            "success": False,
            "official_repo_url": None,
            "candidates": [],
            "source": "pdf"
        }
    
    # 2. 提取所有 URL
    all_urls = extract_urls_from_text(text)
    print(f"    找到 {len(all_urls)} 个 URL")
    
    # 3. 过滤出代码仓库 URL
    code_urls = filter_code_urls(all_urls)
    print(f"    其中 {len(code_urls)} 个是代码仓库 URL")
    
    if not code_urls:
        return {
            "success": False,
            "official_repo_url": None,
            "candidates": [],
            "source": "pdf"
        }
    
    # 4. 根据上下文过滤
    urls_with_context = find_urls_with_context(text, code_urls)
    likely_code_urls = [
        url for url, context in urls_with_context
        if is_likely_code_url(context)
    ]
    
    # 如果有明确的代码相关 URL，优先使用
    candidates = likely_code_urls if likely_code_urls else code_urls
    print(f"    经上下文分析，{len(candidates)} 个候选链接")
    
    # 5. 选择官方仓库
    official_url = None
    
    if len(candidates) == 1:
        official_url = candidates[0]
        print(f"    ✅ 找到唯一候选: {official_url}")
    elif len(candidates) > 1 and use_llm:
        official_url = select_official_repo_with_llm(paper_data, candidates)
    elif len(candidates) > 1:
        # 不使用 LLM，选第一个
        official_url = candidates[0]
        print(f"    ⚠️  有多个候选，选择第一个: {official_url}")
    
    return {
        "success": bool(official_url),
        "official_repo_url": official_url,
        "candidates": candidates,
        "source": "pdf"
    }


def process_paper_pdf(paper_dir: str, paper_data: Dict, use_llm: bool = True) -> Dict:
    """
    处理单篇论文的 PDF 提取
    
    Args:
        paper_dir: 论文目录
        paper_data: 论文元数据
        use_llm: 是否使用 LLM
        
    Returns:
        提取结果
    """
    pdf_path = os.path.join(paper_dir, "paper.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"    ⚠️  PDF 文件不存在")
        return {
            "success": False,
            "official_repo_url": None,
            "candidates": [],
            "source": "pdf"
        }
    
    return extract_code_urls_from_pdf(pdf_path, paper_data, use_llm)


if __name__ == "__main__":
    # 测试
    from config import PAPERS_ROOT_DIR
    from utils import get_all_paper_dirs, load_paper_data
    
    print("测试 PDF 提取器...")
    paper_dirs = get_all_paper_dirs(PAPERS_ROOT_DIR)
    
    if paper_dirs:
        test_dir = paper_dirs[0]
        print(f"\n测试论文: {os.path.basename(test_dir)}")
        
        paper_data = load_paper_data(test_dir)
        if paper_data:
            result = process_paper_pdf(test_dir, paper_data, use_llm=True)
            print(f"\n结果: {result}")
