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


def extract_url_patterns_with_context(text: str, context_chars: int = 50) -> List[Dict]:
    """
    从文本中提取 URL 模式及其上下文
    
    Args:
        text: 文本内容
        context_chars: 上下文字符数
        
    Returns:
        包含 URL 模式和上下文的字典列表
    """
    # 查找所有可能的 URL 起始位置 (http:// 或 https://)
    url_start_pattern = r'https?://'
    url_patterns = []
    
    for match in re.finditer(url_start_pattern, text, re.IGNORECASE):
        start_pos = match.start()
        url_start = match.group()
        
        # 提取 URL 起始位置之前和之后的内容
        context_start = max(0, start_pos - context_chars)
        # 粗略估计 URL 可能的结束位置（最多200个字符）
        url_end_estimate = min(len(text), start_pos + 200)
        context_end = min(len(text), url_end_estimate + context_chars)
        
        # 提取完整上下文
        full_context = text[context_start:context_end]
        
        # 提取 URL 起始后的内容（用于 LLM 分析）
        url_candidate = text[start_pos:url_end_estimate]
        
        url_patterns.append({
            "url_start": url_start,
            "position": start_pos,
            "before_context": text[context_start:start_pos],
            "url_candidate": url_candidate,
            "after_context": text[url_end_estimate:context_end],
            "full_context": full_context
        })
    
    return url_patterns


def extract_urls_with_llm(url_patterns: List[Dict]) -> List[str]:
    """
    使用 LLM 从 URL 模式和上下文中精确识别真正的 URL
    
    Args:
        url_patterns: URL 模式和上下文列表
        
    Returns:
        精确的 URL 列表
    """
    if not url_patterns:
        return []
    
    print(f"    🤖 使用 LLM 从 {len(url_patterns)} 个候选中精确提取 URL...")
    
    # 构造输入
    patterns_text = []
    for i, pattern in enumerate(url_patterns, 1):
        patterns_text.append(
            f"{i}. 上下文:\n"
            f"   前: ...{pattern['before_context'][-30:]}\n"
            f"   URL候选: {pattern['url_start']}[这里是URL]\n"
            f"   后: {pattern['after_context'][:30]}...\n"
            f"   完整候选: {pattern['url_candidate'][:100]}..."
        )
    
    messages = [
        {
            "role": "system",
            "content": "你是一个 URL 提取专家。从 PDF 文本中精确识别 GitHub/GitLab 等代码仓库的完整 URL。注意处理换行、多余字符等问题。"
        },
        {
            "role": "user",
            "content": f"""从以下 PDF 文本片段中提取完整的代码仓库 URL（GitHub、GitLab等）。

{chr(10).join(patterns_text)}

要求：
1. 提取完整的 URL（包括协议、域名、路径）
2. 处理 PDF 中的换行问题（URL 可能被断成多行）
3. 移除 URL 后面无关的内容（如论文标题、页码等）
4. 标准的仓库 URL 格式：https://github.com/用户名/仓库名
5. 如果不是代码仓库 URL，返回 null

用 JSON 格式回复：
{{
  "urls": [
    {{
      "index": 1,
      "url": "提取的完整URL或null",
      "reason": "提取理由（中文）"
    }}
  ]
}}"""
        }
    ]
    
    response = llm_client.call_json(messages, temperature=0.1)
    
    if not response or "urls" not in response:
        print(f"    ⚠️  LLM 提取失败，使用备用方案")
        # 备用方案：使用正则提取
        return extract_urls_fallback([p["url_candidate"] for p in url_patterns])
    
    extracted_urls = []
    for item in response["urls"]:
        url = item.get("url")
        reason = item.get("reason", "")
        
        if url and url != "null" and url.lower() != "null":
            extracted_urls.append(url)
            print(f"    ✓ 提取: {url}")
            if reason:
                print(f"      理由: {reason}")
    
    return extracted_urls


def extract_urls_fallback(candidates: List[str]) -> List[str]:
    """
    备用方案：使用正则表达式提取 URL
    
    Args:
        candidates: URL 候选列表
        
    Returns:
        URL 列表
    """
    urls = []
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    
    for candidate in candidates:
        # 处理换行
        candidate = re.sub(r'\n\s*', '', candidate)
        
        matches = re.findall(url_pattern, candidate)
        for url in matches:
            # 清理
            url = url.rstrip('.,;:!?)\']»')
            url = re.sub(r'\.(\d+)[A-Z][a-zA-Z]+.*$', r'.\1', url)
            
            if len(url) > 15 and 'github.com' in url.lower() or 'gitlab.com' in url.lower():
                urls.append(url)
    
    return list(set(urls))
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


def clean_urls_with_llm(urls: List[str], paper_title: str) -> List[str]:
    """
    使用 LLM 清理和验证提取的 URL，移除错误拼接的部分
    
    Args:
        urls: 原始 URL 列表
        paper_title: 论文标题（用于上下文）
        
    Returns:
        清理后的 URL 列表
    """
    if not urls:
        return []
    
    # 如果URL看起来都正常（没有异常长的路径），直接返回
    suspicious = False
    for url in urls:
        # 检查是否有异常特征
        path = url.split('github.com/')[-1] if 'github.com' in url else ''
        if len(path) > 50 or any(char.isupper() and i > 0 and path[i-1].islower() for i, char in enumerate(path)):
            suspicious = True
            break
    
    if not suspicious:
        return urls
    
    print(f"    🤖 使用 LLM 清理可疑 URL...")
    
    urls_text = "\n".join([f"{i+1}. {url}" for i, url in enumerate(urls)])
    
    messages = [
        {
            "role": "system",
            "content": "你是一个URL清理专家。帮助识别和修正从PDF中提取的GitHub URL，移除错误拼接的内容（如论文标题等）。"
        },
        {
            "role": "user",
            "content": f"""论文标题: {paper_title}

从PDF中提取到以下URL，但可能包含错误拼接的内容（如把下一篇论文标题也拼接进去了）：
{urls_text}

请分析每个URL，移除不属于URL的部分，返回清理后的正确URL。

要求：
1. GitHub URL 格式通常是: https://github.com/用户名/仓库名
2. 移除URL后面错误拼接的论文标题、页码等内容
3. 如果URL无法修正，返回null

用JSON格式回复：
{{
  "cleaned_urls": [
    {{
      "original": "原始URL",
      "cleaned": "清理后的URL或null",
      "reason": "清理原因（中文）"
    }}
  ]
}}"""
        }
    ]
    
    response = llm_client.call_json(messages, temperature=0.1)
    
    if not response or "cleaned_urls" not in response:
        print(f"    ⚠️  LLM 清理失败，使用原始URL")
        return urls
    
    cleaned = []
    for item in response["cleaned_urls"]:
        cleaned_url = item.get("cleaned")
        reason = item.get("reason", "")
        
        if cleaned_url and cleaned_url != "null":
            cleaned.append(cleaned_url)
            if cleaned_url != item.get("original"):
                print(f"    ✂️  修正: {item.get('original')} -> {cleaned_url}")
                print(f"       原因: {reason}")
    
    return cleaned if cleaned else urls


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
    
    # 2. 提取 URL 模式和上下文
    url_patterns = extract_url_patterns_with_context(text, context_chars=50)
    print(f"    找到 {len(url_patterns)} 个 URL 模式")
    
    if not url_patterns:
        return {
            "success": False,
            "official_repo_url": None,
            "candidates": [],
            "source": "pdf"
        }
    
    # 3. 使用 LLM 精确提取 URL
    if use_llm:
        all_urls = extract_urls_with_llm(url_patterns)
    else:
        all_urls = extract_urls_fallback([p["url_candidate"] for p in url_patterns])
    
    print(f"    提取出 {len(all_urls)} 个 URL")
    
    # 4. 过滤出代码仓库 URL
    code_urls = filter_code_urls(all_urls)
    print(f"    其中 {len(code_urls)} 个是代码仓库 URL")
    
    if not code_urls:
        return {
            "success": False,
            "official_repo_url": None,
            "candidates": [],
            "source": "pdf"
        }
    
    # 5. 根据上下文过滤
    urls_with_context = find_urls_with_context(text, code_urls)
    likely_code_urls = [
        url for url, context in urls_with_context
        if is_likely_code_url(context)
    ]
    
    # 如果有明确的代码相关 URL，优先使用
    candidates = likely_code_urls if likely_code_urls else code_urls
    print(f"    经上下文分析，{len(candidates)} 个候选链接")
    
    # 6. 选择官方仓库
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
