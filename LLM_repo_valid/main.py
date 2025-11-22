"""
主流程 - 为论文查找和验证代码仓库
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, Optional
import argparse

from config import PAPERS_ROOT_DIR
from utils import (
    get_all_paper_dirs,
    load_paper_data,
    load_code_data,
    save_code_data,
    create_code_data_structure
)
from pdf_extractor import process_paper_pdf
from github_search import search_github_implementations
from repo_validator import validate_repository


def process_single_paper(
    paper_dir: str,
    use_llm: bool = True,
    skip_pdf: bool = False,
    skip_validation: bool = False,
    skip_if_processed: bool = True
) -> Dict:
    """
    处理单篇论文的完整流程
    
    Args:
        paper_dir: 论文目录
        use_llm: 是否使用 LLM
        skip_pdf: 是否跳过 PDF 提取
        skip_validation: 是否跳过仓库验证
        skip_if_processed: 是否跳过已处理的论文
        
    Returns:
        处理结果
    """
    paper_name = os.path.basename(paper_dir)
    start_time = time.time()
    
    print(f"\n{'='*80}")
    print(f"📝 处理论文: {paper_name}")
    print(f"{'='*80}")
    
    # 加载论文数据
    paper_data = load_paper_data(paper_dir)
    if not paper_data:
        print("❌ 无法加载论文数据")
        return {"success": False, "reason": "Cannot load paper data"}
    
    print(f"标题: {paper_data.get('title', 'N/A')}")
    print(f"年份: {paper_data.get('year', 'N/A')}")
    
    # 加载已有的代码数据
    existing_code_data = load_code_data(paper_dir)
    
    # 检查是否已经处理过
    if skip_if_processed and existing_code_data.get("selected_repo_url"):
        print(f"✅ 已有代码仓库: {existing_code_data['selected_repo_url']}")
        if not skip_validation and existing_code_data.get("quality", {}).get("score") is None:
            print("  重新验证仓库质量...")
        else:
            elapsed = time.time() - start_time
            print(f"⏭️  跳过已处理的论文 (耗时: {elapsed:.2f}秒)")
            return {"success": True, "reason": "Already processed", "data": existing_code_data, "elapsed_time": elapsed}
    
    # 创建代码数据结构
    code_data = create_code_data_structure()
    
    # ============ 阶段 A1: 从 PDF 提取代码链接 ============
    if not skip_pdf:
        pdf_result = process_paper_pdf(paper_dir, paper_data, use_llm)
        
        if pdf_result["success"]:
            code_data["official_repo_url"] = pdf_result["official_repo_url"]
            code_data["selected_repo_url"] = pdf_result["official_repo_url"]
            code_data["repo_type"] = "official"
            code_data["extraction_source"] = "pdf"
            
            print(f"✅ 从 PDF 找到官方仓库: {code_data['official_repo_url']}")
        else:
            print(f"⚠️  PDF 中未找到代码链接")
    
    # ============ 阶段 A2 & A3: GitHub 搜索 ============
    if not code_data["selected_repo_url"]:
        print(f"\n{'─'*80}")
        github_result = search_github_implementations(
            paper_data,
            max_results=10,
            use_llm=use_llm
        )
        
        if github_result["success"] and github_result["unofficial_repos"]:
            code_data["unofficial_repo_urls"] = github_result["unofficial_repos"]
            code_data["selected_repo_url"] = github_result["unofficial_repos"][0]
            code_data["repo_type"] = "unofficial"
            code_data["extraction_source"] = "github_search"
            
            print(f"✅ 找到非官方实现: {code_data['selected_repo_url']}")
        else:
            code_data["repo_type"] = "none_found"
            print(f"❌ 未找到任何代码实现")
    
    # ============ 阶段 B: 验证仓库质量 ============
    if code_data["selected_repo_url"] and not skip_validation:
        print(f"\n{'─'*80}")
        validation_result = validate_repository(
            code_data["selected_repo_url"],
            paper_data,
            use_llm=use_llm
        )
        
        code_data["quality"] = {
            "score": validation_result.get("score"),
            "is_meaningful": validation_result.get("is_meaningful"),
            "reason": validation_result.get("reason", ""),
            "reasons": validation_result.get("reasons", [])
        }
        
        if validation_result.get("is_meaningful"):
            print(f"✅ 仓库有意义 (分数: {validation_result.get('score', 'N/A')})")
        else:
            print(f"❌ 仓库无意义: {validation_result.get('reason')}")
            # 清除无意义的仓库
            code_data["selected_repo_url"] = None
            code_data["repo_type"] = "none_meaningful"
    
    # 保存结果
    code_data["processed_at"] = datetime.now().isoformat()
    save_code_data(paper_dir, code_data)
    
    elapsed = time.time() - start_time
    print(f"\n💾 结果已保存到 {os.path.join(paper_dir, 'github_links.json')}")
    print(f"⏱️  总耗时: {elapsed:.2f}秒 ({elapsed/60:.2f}分钟)")
    
    return {
        "success": True,
        "data": code_data,
        "elapsed_time": elapsed
    }


def process_all_papers(
    root_dir: str = PAPERS_ROOT_DIR,
    use_llm: bool = True,
    skip_pdf: bool = False,
    skip_validation: bool = False,
    limit: Optional[int] = None,
    resume: bool = True
):
    """
    处理所有论文
    
    Args:
        root_dir: 论文根目录
        use_llm: 是否使用 LLM
        skip_pdf: 是否跳过 PDF 提取
        skip_validation: 是否跳过仓库验证
        limit: 限制处理数量（用于测试）
        resume: 是否跳过已处理的论文
    """
    print(f"\n{'='*80}")
    print(f"🚀 开始批量处理论文")
    print(f"{'='*80}")
    print(f"根目录: {root_dir}")
    print(f"使用 LLM: {use_llm}")
    print(f"跳过 PDF: {skip_pdf}")
    print(f"跳过验证: {skip_validation}")
    print(f"限制数量: {limit if limit else '无限制'}")
    print(f"恢复模式: {resume}")
    
    # 获取所有论文目录
    paper_dirs = get_all_paper_dirs(root_dir)
    total = len(paper_dirs)
    
    if limit:
        paper_dirs = paper_dirs[:limit]
        total = len(paper_dirs)
    
    print(f"\n找到 {total} 篇论文待处理\n")
    
    # 统计
    stats = {
        "total": total,
        "processed": 0,
        "skipped": 0,
        "found_official": 0,
        "found_unofficial": 0,
        "not_found": 0,
        "meaningful": 0,
        "not_meaningful": 0,
        "errors": 0
    }
    
    start_time = time.time()
    
    for i, paper_dir in enumerate(paper_dirs, 1):
        paper_name = os.path.basename(paper_dir)
        paper_start_time = time.time()
        print(f"\n[{i}/{total}] {paper_name}")
        
        # 检查是否已处理
        if resume:
            existing = load_code_data(paper_dir)
            if existing.get("processed_at"):
                paper_elapsed = time.time() - paper_start_time
                print(f"⏭️  已处理，跳过 (耗时: {paper_elapsed:.2f}秒)")
                stats["skipped"] += 1
                continue
        
        try:
            result = process_single_paper(
                paper_dir,
                use_llm=use_llm,
                skip_pdf=skip_pdf,
                skip_validation=skip_validation,
                skip_if_processed=resume
            )
            
            if result["success"]:
                paper_elapsed = result.get("elapsed_time", time.time() - paper_start_time)
                print(f"\n⏱️  本篇耗时: {paper_elapsed:.2f}秒 ({paper_elapsed/60:.2f}分钟)")
                stats["processed"] += 1
                
                data = result.get("data", {})
                repo_type = data.get("repo_type")
                
                if repo_type == "official":
                    stats["found_official"] += 1
                elif repo_type == "unofficial":
                    stats["found_unofficial"] += 1
                elif repo_type in ["none_found", "none_meaningful"]:
                    stats["not_found"] += 1
                
                if data.get("quality", {}).get("is_meaningful"):
                    stats["meaningful"] += 1
                elif data.get("quality", {}).get("is_meaningful") is False:
                    stats["not_meaningful"] += 1
            
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断")
            break
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            stats["errors"] += 1
            import traceback
            traceback.print_exc()
        
        # 打印进度
        elapsed = time.time() - start_time
        processed_count = i - stats["skipped"]
        avg_time = elapsed / processed_count if processed_count > 0 else 0
        remaining = (total - i) * avg_time
        
        print(f"\n📊 进度: {i}/{total} | "
              f"已处理: {stats['processed']} | "
              f"跳过: {stats['skipped']} | "
              f"错误: {stats['errors']}")
        print(f"⏱️  平均耗时: {avg_time:.2f}秒/篇 | 已用时间: {elapsed/60:.1f}分钟 | 预计剩余: {remaining/60:.1f}分钟")
    
    # 最终统计
    total_elapsed = time.time() - start_time
    print(f"\n{'='*80}")
    print(f"✅ 处理完成")
    print(f"{'='*80}")
    print(f"总数: {stats['total']}")
    print(f"已处理: {stats['processed']}")
    print(f"跳过: {stats['skipped']}")
    print(f"错误: {stats['errors']}")
    print(f"\n代码查找结果:")
    print(f"  找到官方仓库: {stats['found_official']}")
    print(f"  找到非官方仓库: {stats['found_unofficial']}")
    print(f"  未找到: {stats['not_found']}")
    print(f"\n仓库质量:")
    print(f"  有意义: {stats['meaningful']}")
    print(f"  无意义: {stats['not_meaningful']}")
    print(f"\n⏱️  总耗时: {total_elapsed:.2f}秒 ({total_elapsed/60:.1f}分钟)")
    if stats['processed'] > 0:
        print(f"⏱️  平均耗时: {total_elapsed/stats['processed']:.2f}秒/篇")


def main():
    parser = argparse.ArgumentParser(
        description="为 CVF 论文查找和验证代码仓库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理所有论文（使用 LLM）
  python main.py
  
  # 只处理前 10 篇（测试）
  python main.py --limit 10
  
  # 不使用 LLM（仅规则过滤）
  python main.py --no-llm
  
  # 跳过 PDF 提取（只做 GitHub 搜索）
  python main.py --skip-pdf
  
  # 只查找代码，不验证质量
  python main.py --skip-validation
  
  # 处理单篇论文
  python main.py --single "CVPR/2024/Paper Title"
        """
    )
    
    parser.add_argument(
        "--root-dir",
        default=PAPERS_ROOT_DIR,
        help=f"论文根目录 (默认: {PAPERS_ROOT_DIR})"
    )
    
    parser.add_argument(
        "--single",
        type=str,
        help="只处理单篇论文（相对路径，如 'CVPR/2024/Paper Title'）"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="限制处理数量（用于测试）"
    )
    
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="不使用 LLM（仅规则过滤）"
    )
    
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="跳过 PDF 提取"
    )
    
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="跳过仓库验证"
    )
    
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="不跳过已处理的论文"
    )
    
    args = parser.parse_args()
    
    # 单篇论文模式
    if args.single:
        paper_dir = os.path.join(args.root_dir, args.single)
        if not os.path.exists(paper_dir):
            print(f"❌ 论文目录不存在: {paper_dir}")
            sys.exit(1)
        
        process_single_paper(
            paper_dir,
            use_llm=not args.no_llm,
            skip_pdf=args.skip_pdf,
            skip_validation=args.skip_validation,
            skip_if_processed=not args.no_resume
        )
    else:
        # 批量处理模式
        process_all_papers(
            root_dir=args.root_dir,
            use_llm=not args.no_llm,
            skip_pdf=args.skip_pdf,
            skip_validation=args.skip_validation,
            limit=args.limit,
            resume=not args.no_resume
        )


if __name__ == "__main__":
    main()
