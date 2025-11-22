"""
GitHub 搜索器 - 使用 GitHub API 搜索论文相关实现
"""

import time
from typing import List, Dict, Optional
import requests

from config import GITHUB_API_TOKEN
from utils import normalize_url, extract_repo_owner_name
from llm_client import llm_client


class GitHubSearcher:
    """GitHub API 搜索封装"""
    
    def __init__(self, token: Optional[str] = GITHUB_API_TOKEN):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token and token != "your_github_token_here":
            self.headers["Authorization"] = f"token {token}"
    
    def check_rate_limit(self) -> Dict:
        """检查 API 速率限制状态"""
        try:
            response = requests.get(
                f"{self.base_url}/rate_limit",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("rate", {})
        except Exception:
            pass
        return {}
    
    def wait_for_rate_limit(self, retry_after: Optional[int] = None):
        """等待速率限制恢复"""
        if retry_after:
            wait_time = retry_after + 5  # 额外等待 5 秒
        else:
            rate_limit = self.check_rate_limit()
            remaining = rate_limit.get("remaining", 0)
            reset_time = rate_limit.get("reset", 0)
            
            if remaining == 0 and reset_time:
                wait_time = max(reset_time - time.time() + 5, 60)
            else:
                wait_time = 60
        
        print(f"    ⏳ 等待 {wait_time:.0f} 秒后重试...")
        time.sleep(wait_time)
    
    def _make_request(self, url: str, params: Optional[Dict] = None, max_retries: int = 3) -> Optional[requests.Response]:
        """发起 HTTP 请求，带有重试和速率限制处理"""
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=10
                )
                
                # 处理速率限制
                if response.status_code == 403:
                    retry_after = response.headers.get("Retry-After")
                    if "rate limit" in response.text.lower():
                        print(f"    ⚠️  GitHub API 速率限制 (尝试 {attempt + 1}/{max_retries})")
                        if attempt < max_retries - 1:
                            self.wait_for_rate_limit(int(retry_after) if retry_after else None)
                            continue
                        else:
                            return None
                    else:
                        return response
                
                return response
                
            except requests.exceptions.Timeout:
                print(f"    ⚠️  请求超时 (尝试 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            except requests.exceptions.RequestException as e:
                print(f"    ⚠️  请求失败: {e} (尝试 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
        
        return None
    
    def search_repositories(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict]:
        """
        搜索 GitHub 仓库
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            仓库信息列表
        """
        url = f"{self.base_url}/search/repositories"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": min(max_results, 100)
        }
        
        response = self._make_request(url, params)
        
        if not response or response.status_code != 200:
            print(f"    ❌ GitHub 搜索失败")
            return []
        
        try:
            data = response.json()
            
            repos = []
            for item in data.get("items", [])[:max_results]:
                repos.append({
                    "name": item["name"],
                    "full_name": item["full_name"],
                    "html_url": item["html_url"],
                    "description": item.get("description", ""),
                    "stars": item["stargazers_count"],
                    "forks": item["forks_count"],
                    "language": item.get("language", ""),
                    "updated_at": item["updated_at"],
                    "topics": item.get("topics", []),
                })
            
            return repos
            
        except Exception as e:
            print(f"    ❌ 解析响应失败: {e}")
            return []
    
    def get_repo_info(self, owner: str, repo: str) -> Optional[Dict]:
        """
        获取仓库详细信息
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            
        Returns:
            仓库信息字典
        """
        url = f"{self.base_url}/repos/{owner}/{repo}"
        
        response = self._make_request(url)
        
        if not response:
            return None
        
        if response.status_code == 404:
            return None
        
        if response.status_code != 200:
            print(f"    ❌ 获取仓库信息失败: HTTP {response.status_code}")
            return None
        
        try:
            data = response.json()
            
            return {
                "name": data["name"],
                "full_name": data["full_name"],
                "html_url": data["html_url"],
                "description": data.get("description", ""),
                "stars": data["stargazers_count"],
                "forks": data["forks_count"],
                "language": data.get("language", ""),
                "size": data["size"],
                "created_at": data["created_at"],
                "updated_at": data["updated_at"],
                "pushed_at": data["pushed_at"],
                "topics": data.get("topics", []),
                "archived": data.get("archived", False),
                "license": data.get("license", {}).get("name", None) if data.get("license") else None,
                "open_issues": data.get("open_issues_count", 0),
            }
            
        except Exception as e:
            print(f"    ❌ 解析仓库信息失败: {e}")
            return None


def construct_search_query(paper_data: Dict) -> str:
    """
    根据论文数据构造 GitHub 搜索查询
    
    Args:
        paper_data: 论文元数据
        
    Returns:
        搜索查询字符串
    """
    title = paper_data.get("title", "")
    
    # 提取主要关键词（去掉冠词、介词等）
    stop_words = {"a", "an", "the", "of", "for", "with", "on", "in", "to", "and", "or"}
    keywords = [
        word for word in title.split()
        if word.lower() not in stop_words and len(word) > 2
    ][:5]  # 取前5个关键词
    
    # 构造查询
    query_parts = [f'"{title}"']
    
    # 添加 in:name,description,readme 来提高相关性
    query = f'{" ".join(query_parts)} in:name,description,readme'
    
    return query


def filter_implementations_with_llm(
    paper_data: Dict,
    candidates: List[Dict]
) -> List[Dict]:
    """
    使用 LLM 过滤出真正实现了论文的仓库
    
    Args:
        paper_data: 论文元数据
        candidates: 候选仓库列表
        
    Returns:
        过滤后的仓库列表，按相关性排序
    """
    if not candidates:
        return []
    
    # 构造候选列表文本
    candidates_text = []
    for i, repo in enumerate(candidates):
        text = f"{i+1}. {repo['full_name']} - {repo['html_url']}\n"
        text += f"   Description: {repo['description']}\n"
        text += f"   Stars: {repo['stars']}, Language: {repo['language']}"
        candidates_text.append(text)
    
    messages = [
        {
            "role": "system",
            "content": "你是一个分类器，用于识别 GitHub 仓库是否是某篇研究论文的实现代码。请用 JSON 格式回复，并使用中文。"
        },
        {
            "role": "user",
            "content": f"""论文标题: "{paper_data.get('title', '')}"
年份: {paper_data.get('year', '')}
会议: {paper_data.get('conference', '')}
摘要: "{paper_data.get('abstract', '')[:500]}..."

以下是 GitHub 搜索结果中的仓库：
{chr(10).join(candidates_text)}

对于每个仓库，判断它是否是这篇论文的实现代码（或非常接近的重新实现）。
请用 JSON 格式回复，包含一个对象数组：
{{
  "repositories": [
    {{
      "full_name": "<仓库全名>",
      "url": "<仓库 URL>",
      "is_implementation": true/false,
      "relevance": 0.0-1.0,
      "reason": "简要说明原因（中文）"
    }},
    ...
  ]
}}"""
        }
    ]
    
    response = llm_client.call_json(messages, temperature=0.1)
    
    if not response or "repositories" not in response:
        print(f"    ⚠️  LLM 响应格式错误")
        return []
    
    # 过滤并排序
    filtered = []
    for item in response["repositories"]:
        if item.get("is_implementation", False) and item.get("relevance", 0) > 0.3:
            # 找到对应的原始仓库数据
            for candidate in candidates:
                if candidate["full_name"] == item["full_name"]:
                    filtered.append({
                        **candidate,
                        "relevance": item["relevance"],
                        "reason": item.get("reason", "")
                    })
                    break
    
    # 按相关性排序
    filtered.sort(key=lambda x: x["relevance"], reverse=True)
    
    return filtered


def search_github_implementations(
    paper_data: Dict,
    max_results: int = 10,
    use_llm: bool = True
) -> Dict:
    """
    在 GitHub 上搜索论文的实现
    
    Args:
        paper_data: 论文元数据
        max_results: 最大搜索结果数
        use_llm: 是否使用 LLM 过滤
        
    Returns:
        搜索结果字典
    """
    print(f"  🔍 在 GitHub 搜索实现...")
    
    searcher = GitHubSearcher()
    
    # 构造查询
    query = construct_search_query(paper_data)
    print(f"    查询: {query}")
    
    # 搜索
    candidates = searcher.search_repositories(query, max_results)
    print(f"    找到 {len(candidates)} 个候选仓库")
    
    if not candidates:
        return {
            "success": False,
            "unofficial_repos": [],
            "source": "github_search"
        }
    
    # LLM 过滤
    if use_llm:
        filtered = filter_implementations_with_llm(paper_data, candidates)
        print(f"    LLM 过滤后保留 {len(filtered)} 个实现")
        
        if filtered:
            for i, repo in enumerate(filtered[:3], 1):
                print(f"      {i}. {repo['full_name']} (相关性: {repo['relevance']:.2f})")
                print(f"         {repo.get('reason', 'N/A')}")
    else:
        filtered = candidates
    
    return {
        "success": bool(filtered),
        "unofficial_repos": [repo["html_url"] for repo in filtered],
        "repo_details": filtered,
        "source": "github_search"
    }


if __name__ == "__main__":
    # 测试
    from config import PAPERS_ROOT_DIR
    from utils import get_all_paper_dirs, load_paper_data
    
    print("测试 GitHub 搜索器...")
    paper_dirs = get_all_paper_dirs(PAPERS_ROOT_DIR)
    
    if paper_dirs:
        test_dir = paper_dirs[0]
        print(f"\n测试论文: {os.path.basename(test_dir)}")
        
        paper_data = load_paper_data(test_dir)
        if paper_data:
            result = search_github_implementations(paper_data, max_results=5, use_llm=True)
            print(f"\n结果: {result}")
