"""
通用工具函数
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse


def load_paper_data(paper_dir: str) -> Optional[Dict[str, Any]]:
    """
    加载论文元数据
    
    Args:
        paper_dir: 论文目录路径
        
    Returns:
        论文元数据字典，失败返回 None
    """
    json_path = os.path.join(paper_dir, "paper_data.json")
    
    if not os.path.exists(json_path):
        return None
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载论文数据失败 {json_path}: {e}")
        return None


def save_code_data(paper_dir: str, code_data: Dict[str, Any]) -> bool:
    """
    保存代码仓库数据到 github_links.json
    
    Args:
        paper_dir: 论文目录路径
        code_data: 代码仓库数据
        
    Returns:
        是否保存成功
    """
    json_path = os.path.join(paper_dir, "github_links.json")
    
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(code_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ 保存代码数据失败 {json_path}: {e}")
        return False


def load_code_data(paper_dir: str) -> Dict[str, Any]:
    """
    加载已有的代码仓库数据
    
    Args:
        paper_dir: 论文目录路径
        
    Returns:
        代码仓库数据字典，如果不存在返回空字典
    """
    json_path = os.path.join(paper_dir, "github_links.json")
    
    if not os.path.exists(json_path):
        return {}
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"⚠️  加载已有代码数据失败 {json_path}: {e}")
        return {}


def is_valid_repo_url(url: str, allowed_domains: List[str]) -> bool:
    """
    检查 URL 是否是有效的代码仓库链接
    
    Args:
        url: 待检查的 URL
        allowed_domains: 允许的域名列表
        
    Returns:
        是否是有效的仓库链接
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # 移除 www. 前缀
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # 检查是否在允许的域名列表中
        if not any(domain == d or domain.endswith('.' + d) for d in allowed_domains):
            return False
        
        # 检查路径格式（应该是 /owner/repo 格式）
        path_parts = [p for p in parsed.path.split('/') if p]
        if len(path_parts) < 2:
            return False
        
        return True
        
    except Exception:
        return False


def extract_repo_owner_name(url: str) -> Optional[tuple]:
    """
    从仓库 URL 中提取 owner 和 repo name
    
    Args:
        url: 仓库 URL
        
    Returns:
        (owner, repo_name) 元组，失败返回 None
    """
    try:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        if len(path_parts) >= 2:
            owner = path_parts[0]
            repo_name = path_parts[1]
            
            # 移除 .git 后缀
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            
            return (owner, repo_name)
        
        return None
        
    except Exception:
        return None


def get_all_paper_dirs(root_dir: str) -> List[str]:
    """
    获取所有论文目录
    
    Args:
        root_dir: 根目录路径
        
    Returns:
        论文目录列表
    """
    paper_dirs = []
    
    for conference in os.listdir(root_dir):
        conference_dir = os.path.join(root_dir, conference)
        
        if not os.path.isdir(conference_dir):
            continue
        
        for year in os.listdir(conference_dir):
            year_dir = os.path.join(conference_dir, year)
            
            if not os.path.isdir(year_dir):
                continue
            
            for paper in os.listdir(year_dir):
                paper_dir = os.path.join(year_dir, paper)
                
                if not os.path.isdir(paper_dir):
                    continue
                
                # 检查是否有 paper_data.json
                if os.path.exists(os.path.join(paper_dir, "paper_data.json")):
                    paper_dirs.append(paper_dir)
    
    return paper_dirs


def truncate_text(text: str, max_length: int = 500) -> str:
    """
    截断文本到指定长度
    
    Args:
        text: 原文本
        max_length: 最大长度
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def normalize_url(url: str) -> str:
    """
    标准化 URL（移除尾部斜杠、统一小写等）
    
    Args:
        url: 原 URL
        
    Returns:
        标准化后的 URL
    """
    url = url.strip().rstrip('/')
    
    # 移除 .git 后缀
    if url.endswith('.git'):
        url = url[:-4]
    
    return url


def create_code_data_structure() -> Dict[str, Any]:
    """
    创建代码数据的标准结构
    
    Returns:
        标准的代码数据字典
    """
    return {
        "official_repo_url": None,
        "unofficial_repo_urls": [],
        "selected_repo_url": None,
        "repo_type": None,  # "official" | "unofficial" | "none_found"
        "quality": {
            "score": None,
            "is_meaningful": None,
            "reason": None
        },
        "extraction_source": None,  # "pdf" | "web_search" | "github_search"
        "processed_at": None
    }


if __name__ == "__main__":
    # 测试工具函数
    from config import PAPERS_ROOT_DIR
    
    print("测试获取论文目录...")
    paper_dirs = get_all_paper_dirs(PAPERS_ROOT_DIR)
    print(f"找到 {len(paper_dirs)} 篇论文")
    
    if paper_dirs:
        print(f"\n第一篇论文: {paper_dirs[0]}")
        paper_data = load_paper_data(paper_dirs[0])
        if paper_data:
            print(f"标题: {paper_data.get('title')}")
            print(f"年份: {paper_data.get('year')}")
