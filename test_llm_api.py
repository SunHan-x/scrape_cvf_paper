#!/usr/bin/env python
"""
测试 LLM API 连接和功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'LLM_repo_valid'))

import requests
import json
from LLM_repo_valid.config import GEMINI_API_KEY, GEMINI_API_URL, GEMINI_MODEL


def test_api_basic():
    """测试基本的 API 连接"""
    print("=" * 80)
    print("测试 1: 基本 API 连接")
    print("=" * 80)
    print(f"API URL: {GEMINI_API_URL}")
    print(f"Model: {GEMINI_MODEL}")
    print(f"API Key: {GEMINI_API_KEY[:20]}..." if len(GEMINI_API_KEY) > 20 else "未配置")
    print()
    
    if GEMINI_API_KEY == "your_gemini_api_key_here":
        print("❌ 错误: API Key 未配置!")
        print("请编辑 LLM_repo_valid/config.py 并设置 GEMINI_API_KEY")
        return False
    
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": GEMINI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, World!' in one word."}
        ],
        "temperature": 0.1,
        "max_tokens": 10
    }
    
    try:
        print("发送请求...")
        response = requests.post(
            GEMINI_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print()
        
        if response.status_code != 200:
            print(f"❌ 错误: HTTP {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            return False
        
        result = response.json()
        print("✅ API 连接成功!")
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return True
        
    except requests.exceptions.Timeout:
        print("❌ 错误: 请求超时")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 错误: 请求失败 - {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ 错误: JSON 解析失败 - {e}")
        print(f"原始响应: {response.text[:500]}")
        return False


def test_llm_client():
    """测试封装的 LLM 客户端"""
    print("\n" + "=" * 80)
    print("测试 2: LLM 客户端封装")
    print("=" * 80)
    
    try:
        from LLM_repo_valid.llm_client import llm_client
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Please say 'Hello' in one word."}
        ]
        
        print("调用 llm_client.call()...")
        response = llm_client.call(messages)
        
        if response:
            print(f"✅ 成功!")
            print(f"响应: {response}")
            return True
        else:
            print("❌ 失败: 没有响应")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_json_mode():
    """测试 JSON 模式"""
    print("\n" + "=" * 80)
    print("测试 3: JSON 模式")
    print("=" * 80)
    
    try:
        from LLM_repo_valid.llm_client import llm_client
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Reply in JSON format."},
            {"role": "user", "content": 'Say "Hello" in JSON format with a key "message".'}
        ]
        
        print("调用 llm_client.call_json()...")
        response = llm_client.call_json(messages)
        
        if response:
            print(f"✅ 成功!")
            print(f"响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
            
            if isinstance(response, dict) and "message" in response:
                print("✅ JSON 格式正确!")
                return True
            else:
                print("⚠️  警告: JSON 格式可能不符合预期")
                return True
        else:
            print("❌ 失败: 没有响应")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_paper_selection():
    """测试论文场景：从多个候选中选择"""
    print("\n" + "=" * 80)
    print("测试 4: 实际应用场景 - 选择代码仓库")
    print("=" * 80)
    
    try:
        from LLM_repo_valid.llm_client import llm_client
        
        messages = [
            {
                "role": "system",
                "content": "You are a tool that picks the most likely official code repository for a paper. Reply in JSON format."
            },
            {
                "role": "user",
                "content": """Paper title: "3D Gaussian Splatting for Real-Time Radiance Field Rendering"
Venue: CVPR 2024

Found URLs in PDF:
1. https://github.com/graphdeco-inria/gaussian-splatting
2. https://github.com/some-other-user/3d-gaussian
3. https://arxiv.org/abs/2308.04079

From these URLs, which one is MOST likely the official implementation of the paper?
Reply in JSON format:
{
  "selected_url": "<url or null>",
  "reason": "brief explanation"
}"""
            }
        ]
        
        print("调用 LLM 选择官方仓库...")
        response = llm_client.call_json(messages)
        
        if response:
            print(f"✅ 成功!")
            print(f"响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
            
            if "selected_url" in response and "reason" in response:
                print("✅ 响应格式正确!")
                print(f"选择的 URL: {response['selected_url']}")
                print(f"理由: {response['reason']}")
                return True
            else:
                print("⚠️  警告: 响应格式可能不符合预期")
                return False
        else:
            print("❌ 失败: 没有响应")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("🧪 LLM API 功能测试")
    print("=" * 80)
    print()
    
    results = []
    
    # 测试 1: 基本连接
    results.append(("基本 API 连接", test_api_basic()))
    
    # 测试 2: 客户端封装
    if results[0][1]:  # 如果基本连接成功
        results.append(("LLM 客户端封装", test_llm_client()))
        results.append(("JSON 模式", test_json_mode()))
        results.append(("实际应用场景", test_paper_selection()))
    
    # 输出总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    print()
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过! LLM API 功能正常")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查配置或网络连接")
        return 1


if __name__ == "__main__":
    sys.exit(main())
