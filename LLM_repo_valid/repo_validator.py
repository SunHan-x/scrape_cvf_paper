"""
仓库质量验证器 - 评估代码仓库是否有意义且维护良好
"""

import os
import time
from typing import Dict, Optional, List
from datetime import datetime
import requests

from config import (
    MIN_CODE_FILES, MIN_REPO_SIZE_KB, MAX_ABANDONED_YEARS,
    MIN_STARS_FOR_OLD_REPO, CODE_EXTENSIONS, TYPICAL_IMPL_FILES,
    TYPICAL_IMPL_DIRS
)
from utils import extract_repo_owner_name, truncate_text
from llm_client import llm_client
from github_search import GitHubSearcher


def get_repo_file_tree(owner: str, repo: str, path: str = "") -> Optional[List[Dict]]:
    """
    获取仓库文件树
    
    Args:
        owner: 仓库所有者
        repo: 仓库名称
        path: 路径（默认根目录）
        
    Returns:
        文件列表
    """
    searcher = GitHubSearcher()
    url = f"{searcher.base_url}/repos/{owner}/{repo}/contents/{path}"
    
    try:
        response = requests.get(
            url,
            headers=searcher.headers,
            timeout=10
        )
        
        if response.status_code != 200:
            return None
        
        return response.json()
        
    except Exception as e:
        print(f"    ⚠️  获取文件树失败: {e}")
        return None


def get_readme_content(owner: str, repo: str) -> Optional[str]:
    """
    获取 README 文件内容
    
    Args:
        owner: 仓库所有者
        repo: 仓库名称
        
    Returns:
        README 内容
    """
    searcher = GitHubSearcher()
    url = f"{searcher.base_url}/repos/{owner}/{repo}/readme"
    
    try:
        response = requests.get(
            url,
            headers=searcher.headers,
            timeout=10
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        # README 内容是 base64 编码的
        import base64
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content
        
    except Exception as e:
        print(f"    ⚠️  获取 README 失败: {e}")
        return None


def analyze_file_structure(files: List[Dict]) -> Dict:
    """
    分析文件结构
    
    Args:
        files: 文件列表
        
    Returns:
        分析结果
    """
    code_files = []
    non_code_files = []
    directories = []
    
    for item in files:
        name = item.get("name", "")
        item_type = item.get("type", "")
        
        if item_type == "dir":
            directories.append(name)
        elif item_type == "file":
            ext = os.path.splitext(name)[1].lower()
            if ext in CODE_EXTENSIONS:
                code_files.append(name)
            else:
                non_code_files.append(name)
    
    # 检查是否有典型实现文件
    has_typical_files = any(
        f in code_files for f in TYPICAL_IMPL_FILES
    )
    
    # 检查是否有典型实现目录
    has_typical_dirs = any(
        d in directories for d in TYPICAL_IMPL_DIRS
    )
    
    return {
        "code_file_count": len(code_files),
        "code_files": code_files,
        "non_code_file_count": len(non_code_files),
        "directory_count": len(directories),
        "directories": directories,
        "has_typical_files": has_typical_files,
        "has_typical_dirs": has_typical_dirs,
    }


def rule_based_filter(repo_info: Dict, paper_year: int) -> Dict:
    """
    基于规则的快速过滤
    
    Args:
        repo_info: 仓库信息
        paper_year: 论文发表年份
        
    Returns:
        过滤结果
    """
    # 获取文件树
    owner_repo = extract_repo_owner_name(repo_info["html_url"])
    if not owner_repo:
        return {
            "is_meaningful": False,
            "confident": True,
            "reason": "Invalid repository URL",
            "score": 0.0
        }
    
    owner, repo = owner_repo
    
    # 获取根目录文件
    files = get_repo_file_tree(owner, repo)
    if files is None:
        return {
            "is_meaningful": None,
            "confident": False,
            "reason": "Cannot fetch repository contents",
            "score": None
        }
    
    # 分析文件结构
    structure = analyze_file_structure(files)
    
    # 规则 1: 没有代码文件
    if structure["code_file_count"] == 0:
        return {
            "is_meaningful": False,
            "confident": True,
            "reason": "No code files found",
            "score": 0.0,
            "structure": structure
        }
    
    # 规则 2: 仓库太小且代码文件很少
    if repo_info["size"] < MIN_REPO_SIZE_KB and structure["code_file_count"] <= 1:
        return {
            "is_meaningful": False,
            "confident": True,
            "reason": f"Very tiny repo (size: {repo_info['size']}KB) with almost no code",
            "score": 0.1,
            "structure": structure
        }
    
    # 规则 3: 已归档
    if repo_info.get("archived", False):
        return {
            "is_meaningful": False,
            "confident": True,
            "reason": "Repository is archived",
            "score": 0.2,
            "structure": structure
        }
    
    # 规则 4: 长时间未更新且没有关注
    try:
        last_push = datetime.strptime(repo_info["pushed_at"], "%Y-%m-%dT%H:%M:%SZ")
        current_year = datetime.now().year
        years_since_push = current_year - last_push.year
        
        if years_since_push > MAX_ABANDONED_YEARS and repo_info["stars"] < MIN_STARS_FOR_OLD_REPO:
            return {
                "is_meaningful": False,
                "confident": True,
                "reason": f"Abandoned repo (last push: {years_since_push} years ago, stars: {repo_info['stars']})",
                "score": 0.2,
                "structure": structure
            }
    except Exception:
        pass
    
    # 规则通过，但不完全确定（需要 LLM 深度评估）
    return {
        "is_meaningful": True,
        "confident": False,
        "reason": "Has code files and basic structure",
        "score": None,
        "structure": structure
    }


def llm_evaluate_repo(
    repo_info: Dict,
    paper_data: Dict,
    structure: Dict,
    readme: Optional[str] = None
) -> Dict:
    """
    使用 LLM 深度评估仓库质量
    
    Args:
        repo_info: 仓库信息
        paper_data: 论文数据
        structure: 文件结构分析
        readme: README 内容
        
    Returns:
        评估结果
    """
    print(f"  🤖 LLM 深度评估仓库质量...")
    
    # 如果没有 README，尝试获取
    if readme is None:
        owner_repo = extract_repo_owner_name(repo_info["html_url"])
        if owner_repo:
            owner, repo = owner_repo
            readme = get_readme_content(owner, repo)
    
    # 构造文件树文本
    tree_text = "Root directory:\n"
    tree_text += f"  Code files ({structure['code_file_count']}): {', '.join(structure['code_files'][:10])}\n"
    tree_text += f"  Directories ({structure['directory_count']}): {', '.join(structure['directories'][:10])}\n"
    
    # 截断 README
    readme_text = truncate_text(readme, 1000) if readme else "No README found"
    
    messages = [
        {
            "role": "system",
            "content": "You are a senior ML engineer. Evaluate if a GitHub repository is a meaningful, well-maintained implementation. Reply in JSON format."
        },
        {
            "role": "user",
            "content": f"""Paper title: "{paper_data.get('title', '')}"
Year: {paper_data.get('year', '')}
Abstract: "{truncate_text(paper_data.get('abstract', ''), 300)}"

Repository: {repo_info['html_url']}

Basic stats:
- Stars: {repo_info['stars']}
- Forks: {repo_info['forks']}
- Last commit: {repo_info['pushed_at']}
- Main language: {repo_info['language']}
- Size: {repo_info['size']}KB
- Is archived: {repo_info.get('archived', False)}
- Code files: {structure['code_file_count']}
- Has typical structure: {structure['has_typical_files'] or structure['has_typical_dirs']}

{tree_text}

README (truncated):
{readme_text}

Evaluate this repository and reply in JSON format:
{{
  "is_meaningful": true/false,
  "is_implementation_of_paper": true/false,
  "maintenance_score": 0.0-1.0,
  "code_quality_score": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "reasons": ["reason 1", "reason 2", ...]
}}"""
        }
    ]
    
    response = llm_client.call_json(messages, temperature=0.1)
    
    if not response:
        return {
            "is_meaningful": None,
            "score": None,
            "reason": "LLM evaluation failed"
        }
    
    return {
        "is_meaningful": response.get("is_meaningful", False),
        "is_implementation": response.get("is_implementation_of_paper", False),
        "maintenance_score": response.get("maintenance_score", 0.0),
        "code_quality_score": response.get("code_quality_score", 0.0),
        "score": response.get("overall_score", 0.0),
        "reasons": response.get("reasons", [])
    }


def validate_repository(
    repo_url: str,
    paper_data: Dict,
    use_llm: bool = True
) -> Dict:
    """
    验证仓库是否有意义
    
    Args:
        repo_url: 仓库 URL
        paper_data: 论文数据
        use_llm: 是否使用 LLM 深度评估
        
    Returns:
        验证结果
    """
    print(f"  ✅ 验证仓库: {repo_url}")
    
    # 获取仓库信息
    owner_repo = extract_repo_owner_name(repo_url)
    if not owner_repo:
        return {
            "is_meaningful": False,
            "score": 0.0,
            "reason": "Invalid repository URL"
        }
    
    owner, repo = owner_repo
    searcher = GitHubSearcher()
    repo_info = searcher.get_repo_info(owner, repo)
    
    if not repo_info:
        return {
            "is_meaningful": False,
            "score": 0.0,
            "reason": "Repository not found or inaccessible"
        }
    
    # 规则过滤
    rule_result = rule_based_filter(repo_info, paper_data.get("year", 2020))
    
    print(f"    规则评估: {rule_result['reason']}")
    
    # 如果规则已经很确定，直接返回
    if rule_result["confident"]:
        return rule_result
    
    # 需要 LLM 深度评估
    if use_llm:
        llm_result = llm_evaluate_repo(
            repo_info,
            paper_data,
            rule_result.get("structure", {}),
            None
        )
        
        print(f"    LLM 评估分数: {llm_result.get('score', 'N/A')}")
        print(f"    原因: {', '.join(llm_result.get('reasons', []))}")
        
        return {
            **rule_result,
            **llm_result,
            "confident": True
        }
    
    # 不使用 LLM，返回规则结果
    return rule_result


if __name__ == "__main__":
    # 测试
    test_repo_url = "https://github.com/some/repo"
    test_paper_data = {
        "title": "Test Paper",
        "year": 2024,
        "abstract": "This is a test abstract."
    }
    
    result = validate_repository(test_repo_url, test_paper_data, use_llm=True)
    print(f"\n结果: {result}")
