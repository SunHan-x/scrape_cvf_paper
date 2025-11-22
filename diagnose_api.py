#!/usr/bin/env python
"""
API 诊断工具 - 详细检查 API 配置和连接问题
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'LLM_repo_valid'))

import requests
import json


def check_api_endpoints():
    """检查不同的 API 端点"""
    print("=" * 80)
    print("🔍 检查 API 端点")
    print("=" * 80)
    
    from LLM_repo_valid.config import GEMINI_API_KEY
    
    # 可能的 API 端点
    endpoints = [
        "https://zenmux.ai/v1/chat/completions",
        "https://api.zenmux.ai/v1/chat/completions",
        "https://zenmux.ai/api/v1/chat/completions",
    ]
    
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    simple_payload = {
        "model": "gemini-3-pro-preview-free",
        "messages": [
            {"role": "user", "content": "Hi"}
        ],
        "max_tokens": 5
    }
    
    for endpoint in endpoints:
        print(f"\n测试端点: {endpoint}")
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=simple_payload,
                timeout=10
            )
            
            print(f"  状态码: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✅ 成功!")
                try:
                    data = response.json()
                    print(f"  响应: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
                    return endpoint
                except:
                    print(f"  响应文本: {response.text[:200]}...")
            elif response.status_code == 404:
                print(f"  ❌ 端点不存在")
            elif response.status_code == 401:
                print(f"  ❌ 认证失败 (检查 API Key)")
            elif response.status_code == 500:
                print(f"  ❌ 服务器错误")
                print(f"  响应: {response.text[:300]}...")
            else:
                print(f"  ⚠️  其他错误")
                print(f"  响应: {response.text[:300]}...")
                
        except requests.exceptions.Timeout:
            print(f"  ❌ 超时")
        except Exception as e:
            print(f"  ❌ 错误: {e}")
    
    return None


def test_minimal_request():
    """测试最小化请求"""
    print("\n" + "=" * 80)
    print("🧪 测试最小化请求")
    print("=" * 80)
    
    from LLM_repo_valid.config import GEMINI_API_KEY
    
    url = "https://zenmux.ai/v1/chat/completions"
    
    # 尝试不同的模型名称
    models = [
        "gemini-3-pro-preview-free",
        "gemini-pro",
        "gemini-1.5-pro",
    ]
    
    for model in models:
        print(f"\n测试模型: {model}")
        
        headers = {
            "Authorization": f"Bearer {GEMINI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hi"}]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"  状态码: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✅ 成功!")
                return model
            else:
                print(f"  ❌ 失败: {response.text[:200]}")
                
        except Exception as e:
            print(f"  ❌ 错误: {e}")
    
    return None


def check_api_key():
    """检查 API Key 格式"""
    print("\n" + "=" * 80)
    print("🔑 检查 API Key")
    print("=" * 80)
    
    from LLM_repo_valid.config import GEMINI_API_KEY
    
    print(f"API Key 长度: {len(GEMINI_API_KEY)}")
    print(f"前缀: {GEMINI_API_KEY[:10]}...")
    print(f"后缀: ...{GEMINI_API_KEY[-10:]}")
    
    if GEMINI_API_KEY == "your_gemini_api_key_here":
        print("❌ API Key 未配置!")
        return False
    
    if not GEMINI_API_KEY.startswith("sk-"):
        print("⚠️  警告: API Key 不以 'sk-' 开头，可能不是正确格式")
    
    return True


def test_alternative_api():
    """测试备用 API（如果有）"""
    print("\n" + "=" * 80)
    print("🔄 测试备用方案")
    print("=" * 80)
    print("建议:")
    print("1. 检查 https://zenmux.ai 网站是否可访问")
    print("2. 查看 API 文档: https://zenmux.ai/docs")
    print("3. 确认 API Key 是否有效")
    print("4. 尝试使用其他 LLM API (如 OpenAI、Claude 等)")


def main():
    print("\n" + "=" * 80)
    print("🩺 LLM API 诊断工具")
    print("=" * 80)
    
    # 1. 检查 API Key
    if not check_api_key():
        print("\n❌ 请先配置 API Key!")
        return 1
    
    # 2. 检查端点
    working_endpoint = check_api_endpoints()
    
    # 3. 测试模型
    if not working_endpoint:
        working_model = test_minimal_request()
    
    # 4. 备用方案
    test_alternative_api()
    
    print("\n" + "=" * 80)
    print("💡 建议")
    print("=" * 80)
    
    if working_endpoint:
        print(f"✅ 找到可用端点: {working_endpoint}")
        print(f"   请在 config.py 中更新 GEMINI_API_URL")
    else:
        print("❌ 没有找到可用的 API 端点")
        print("\n可能的原因:")
        print("1. API 服务暂时不可用 (500 错误通常是服务器问题)")
        print("2. API Key 无效或已过期")
        print("3. 网络连接问题")
        print("4. API URL 不正确")
        print("\n解决方案:")
        print("1. 访问 https://zenmux.ai 检查服务状态")
        print("2. 重新生成 API Key")
        print("3. 查看 API 文档确认正确的端点和模型名称")
        print("4. 考虑使用其他 LLM 服务 (OpenAI, Anthropic, etc.)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
