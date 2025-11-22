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
    TYPICAL_IMPL_DIRS, MAX_DEPTH, MAX_FILES_TO_ANALYZE, SAMPLE_FILE_LINES
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
    
    response = searcher._make_request(url)
    
    if not response or response.status_code != 200:
        return None
    
    try:
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
    
    response = searcher._make_request(url)
    
    if not response or response.status_code != 200:
        return None
    
    try:
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


def get_file_content(owner: str, repo: str, path: str) -> Optional[str]:
    """
    获取文件内容
    
    Args:
        owner: 仓库所有者
        repo: 仓库名称
        path: 文件路径
        
    Returns:
        文件内容
    """
    searcher = GitHubSearcher()
    url = f"{searcher.base_url}/repos/{owner}/{repo}/contents/{path}"
    
    response = searcher._make_request(url)
    
    if not response or response.status_code != 200:
        return None
    
    try:
        data = response.json()
        
        # 文件内容是 base64 编码的
        import base64
        content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return content
        
    except Exception:
        return None


def deep_analyze_repo_structure(owner: str, repo: str, max_depth: int = MAX_DEPTH) -> Dict:
    """
    深度分析仓库结构
    
    Args:
        owner: 仓库所有者
        repo: 仓库名称
        max_depth: 最大遍历深度
        
    Returns:
        深度分析结果
    """
    all_code_files = []
    all_directories = []
    file_tree = {}
    
    def traverse_dir(path: str, depth: int):
        """递归遍历目录"""
        if depth > max_depth:
            return
        
        files = get_repo_file_tree(owner, repo, path)
        if not files:
            return
        
        for item in files:
            name = item.get("name", "")
            item_type = item.get("type", "")
            full_path = f"{path}/{name}" if path else name
            
            if item_type == "dir":
                all_directories.append(full_path)
                # 递归遍历子目录
                traverse_dir(full_path, depth + 1)
            elif item_type == "file":
                ext = os.path.splitext(name)[1].lower()
                if ext in CODE_EXTENSIONS:
                    all_code_files.append({
                        "path": full_path,
                        "name": name,
                        "extension": ext,
                        "size": item.get("size", 0)
                    })
    
    # 从根目录开始遍历
    traverse_dir("", 0)
    
    # 分析代码文件分布
    extension_counts = {}
    for file in all_code_files:
        ext = file["extension"]
        extension_counts[ext] = extension_counts.get(ext, 0) + 1
    
    # 识别主要语言
    main_language = max(extension_counts.items(), key=lambda x: x[1])[0] if extension_counts else None
    
    # 分析目录结构
    has_models_dir = any("model" in d.lower() for d in all_directories)
    has_data_dir = any("data" in d.lower() or "dataset" in d.lower() for d in all_directories)
    has_train_dir = any("train" in d.lower() for d in all_directories)
    has_test_dir = any("test" in d.lower() for d in all_directories)
    has_config_dir = any("config" in d.lower() for d in all_directories)
    
    # 识别关键代码文件
    key_files = []
    for file in all_code_files:
        name_lower = file["name"].lower()
        if any(keyword in name_lower for keyword in ["train", "model", "network", "main", "run"]):
            key_files.append(file)
    
    return {
        "total_code_files": len(all_code_files),
        "total_directories": len(all_directories),
        "extension_counts": extension_counts,
        "main_language": main_language,
        "has_models_dir": has_models_dir,
        "has_data_dir": has_data_dir,
        "has_train_dir": has_train_dir,
        "has_test_dir": has_test_dir,
        "has_config_dir": has_config_dir,
        "key_files": key_files[:10],  # 只保留前10个关键文件
        "all_code_files": all_code_files[:MAX_FILES_TO_ANALYZE],  # 限制数量
    }


def sample_code_files(owner: str, repo: str, files: List[Dict], max_samples: int = 5) -> List[Dict]:
    """
    采样关键代码文件内容
    
    Args:
        owner: 仓库所有者
        repo: 仓库名称
        files: 文件列表
        max_samples: 最大采样数
        
    Returns:
        采样的文件内容
    """
    samples = []
    
    # 优先选择关键文件
    priority_keywords = ["train", "model", "network", "main"]
    
    # 先选择优先级高的文件
    priority_files = [f for f in files if any(kw in f["name"].lower() for kw in priority_keywords)]
    other_files = [f for f in files if f not in priority_files]
    
    selected_files = (priority_files + other_files)[:max_samples]
    
    for file in selected_files:
        content = get_file_content(owner, repo, file["path"])
        if content:
            # 只取前N行
            lines = content.split("\n")[:SAMPLE_FILE_LINES]
            samples.append({
                "path": file["path"],
                "name": file["name"],
                "lines": len(content.split("\n")),
                "sample": "\n".join(lines)
            })
    
    return samples


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
    readme: Optional[str] = None,
    deep_structure: Optional[Dict] = None,
    code_samples: Optional[List[Dict]] = None
) -> Dict:
    """
    使用 LLM 深度评估仓库质量
    
    Args:
        repo_info: 仓库信息
        paper_data: 论文数据
        structure: 文件结构分析
        readme: README 内容
        deep_structure: 深度结构分析
        code_samples: 代码采样
        
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
    tree_text = "根目录:\n"
    tree_text += f"  代码文件 ({structure['code_file_count']}): {', '.join(structure['code_files'][:10])}\n"
    tree_text += f"  目录 ({structure['directory_count']}): {', '.join(structure['directories'][:10])}\n"
    
    # 添加深度结构信息
    if deep_structure:
        tree_text += f"\n深度分析 (遍历了 {MAX_DEPTH} 层目录):\n"
        tree_text += f"  总代码文件数: {deep_structure['total_code_files']}\n"
        tree_text += f"  文件类型分布: {deep_structure['extension_counts']}\n"
        tree_text += f"  主要语言: {deep_structure['main_language']}\n"
        tree_text += f"  目录结构:\n"
        tree_text += f"    - 模型目录: {'有' if deep_structure['has_models_dir'] else '无'}\n"
        tree_text += f"    - 数据目录: {'有' if deep_structure['has_data_dir'] else '无'}\n"
        tree_text += f"    - 训练目录: {'有' if deep_structure['has_train_dir'] else '无'}\n"
        tree_text += f"    - 测试目录: {'有' if deep_structure['has_test_dir'] else '无'}\n"
        tree_text += f"    - 配置目录: {'有' if deep_structure['has_config_dir'] else '无'}\n"
        
        if deep_structure['key_files']:
            tree_text += f"  关键文件:\n"
            for file in deep_structure['key_files'][:5]:
                tree_text += f"    - {file['path']}\n"
    
    # 添加代码采样
    code_samples_text = ""
    if code_samples:
        code_samples_text = "\n代码示例:\n"
        for sample in code_samples[:3]:  # 最多3个示例
            code_samples_text += f"\n文件: {sample['path']} (共 {sample['lines']} 行)\n"
            code_samples_text += f"```\n{sample['sample']}\n```\n"
    
    # 截断 README
    readme_text = truncate_text(readme, 1000) if readme else "无 README"
    
    messages = [
        {
            "role": "system",
            "content": "你是一位资深机器学习工程师。请评估 GitHub 仓库是否是一个有意义、维护良好的实现。请用 JSON 格式回复，并使用中文。"
        },
        {
            "role": "user",
            "content": f"""论文标题: "{paper_data.get('title', '')}"
年份: {paper_data.get('year', '')}
摘要: "{truncate_text(paper_data.get('abstract', ''), 300)}"

仓库: {repo_info['html_url']}

基本统计:
- Stars: {repo_info['stars']}
- Forks: {repo_info['forks']}
- 最后提交: {repo_info['pushed_at']}
- 主要语言: {repo_info['language']}
- 大小: {repo_info['size']}KB
- 是否已归档: {repo_info.get('archived', False)}
- 代码文件数: {structure['code_file_count']}
- 是否有典型结构: {structure['has_typical_files'] or structure['has_typical_dirs']}

{tree_text}

README (截断):
{readme_text}

{code_samples_text}

请仔细分析仓库的代码架构、实现质量和维护状态，并用 JSON 格式回复：
{{
  "is_meaningful": true/false,
  "is_implementation_of_paper": true/false,
  "has_complete_architecture": true/false,
  "code_organization_score": 0.0-1.0,
  "maintenance_score": 0.0-1.0,
  "code_quality_score": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "architecture_analysis": "代码架构分析（中文）",
  "reasons": ["原因1（中文）", "原因2（中文）", ...]
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
        "has_complete_architecture": response.get("has_complete_architecture", False),
        "code_organization_score": response.get("code_organization_score", 0.0),
        "maintenance_score": response.get("maintenance_score", 0.0),
        "code_quality_score": response.get("code_quality_score", 0.0),
        "score": response.get("overall_score", 0.0),
        "architecture_analysis": response.get("architecture_analysis", ""),
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
        print(f"    开始深度分析仓库结构...")
        
        # 深度分析仓库结构
        deep_structure = deep_analyze_repo_structure(owner, repo)
        print(f"    发现 {deep_structure['total_code_files']} 个代码文件")
        
        # 采样代码文件
        code_samples = None
        if deep_structure['all_code_files']:
            print(f"    采样关键代码文件...")
            code_samples = sample_code_files(owner, repo, deep_structure['all_code_files'], max_samples=5)
            print(f"    成功采样 {len(code_samples)} 个文件")
        
        # LLM 评估
        llm_result = llm_evaluate_repo(
            repo_info,
            paper_data,
            rule_result.get("structure", {}),
            None,
            deep_structure,
            code_samples
        )
        
        print(f"    LLM 评估分数: {llm_result.get('score', 'N/A')}")
        if llm_result.get('architecture_analysis'):
            print(f"    架构分析: {llm_result['architecture_analysis'][:100]}...")
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
