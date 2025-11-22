#!/usr/bin/env python
"""
测试阿里云百炼 API 连接
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'LLM_repo_valid'))

import requests
import json


def test_aliyun_api():
    """测试阿里云百炼 API"""
    print("=" * 80)
    print("🧪 测试阿里云百炼 (Qwen) API")
    print("=" * 80)
    
    # 从 config 读取配置
    from LLM_repo_valid.config import ALIYUN_API_KEY, ALIYUN_API_URL, ALIYUN_MODEL
    
    print(f"API URL: {ALIYUN_API_URL}")
    print(f"Model: {ALIYUN_MODEL}")
    print(f"API Key: {ALIYUN_API_KEY[:20]}..." if len(ALIYUN_API_KEY) > 20 else "未配置")
    print()
    
    if ALIYUN_API_KEY == "your_aliyun_api_key_here":
        print("❌ 错误: API Key 未配置!")
        print("\n📖 配置步骤:")
        print("1. 访问阿里云百炼控制台: https://bailian.console.aliyun.com")
        print("2. 在左侧菜单选择 'API-KEY管理'")
        print("3. 创建或复制你的 API Key")
        print("4. 编辑 LLM_repo_valid/config.py，将 API Key 填入:")
        print("   ALIYUN_API_KEY = 'sk-xxx...'")
        print("\n💡 提示: 阿里云百炼提供免费额度，可以直接使用！")
        return False
    
    # 构造请求
    headers = {
        "Authorization": f"Bearer {ALIYUN_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": ALIYUN_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "请用一个词回复：你好"}
        ],
        "temperature": 0.1,
        "max_tokens": 10
    }
    
    try:
        print("📡 发送测试请求...")
        response = requests.post(
            ALIYUN_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ API 连接成功!")
            print(f"\n响应内容:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # 提取回复内容
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                print(f"\n💬 AI 回复: {content}")
            
            return True
            
        elif response.status_code == 401:
            print("\n❌ 认证失败 (401)")
            print("可能原因:")
            print("1. API Key 不正确")
            print("2. API Key 已过期")
            print("3. API Key 权限不足")
            print("\n请检查你的 API Key 并重新配置")
            return False
            
        elif response.status_code == 400:
            print("\n❌ 请求参数错误 (400)")
            print(f"错误信息: {response.text}")
            return False
            
        else:
            print(f"\n❌ 请求失败 ({response.status_code})")
            print(f"响应内容: {response.text[:500]}")
            return False
        
    except requests.exceptions.Timeout:
        print("\n❌ 请求超时")
        print("请检查网络连接")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")
        return False
        
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON 解析失败: {e}")
        print(f"原始响应: {response.text[:500]}")
        return False


def test_llm_client_with_aliyun():
    """测试通过 llm_client 使用阿里云 API"""
    print("\n" + "=" * 80)
    print("🧪 测试 LLM 客户端 (使用阿里云)")
    print("=" * 80)
    
    try:
        from LLM_repo_valid.llm_client import llm_client
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "请简短回答：什么是机器学习？"}
        ]
        
        print("📡 调用 llm_client...")
        response = llm_client.call(messages)
        
        if response:
            print("\n✅ 成功!")
            print(f"💬 AI 回复: {response}")
            return True
        else:
            print("\n❌ 失败: 没有响应")
            return False
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_json_mode():
    """测试 JSON 模式"""
    print("\n" + "=" * 80)
    print("🧪 测试 JSON 模式")
    print("=" * 80)
    
    try:
        from LLM_repo_valid.llm_client import llm_client
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Reply in JSON format."},
            {"role": "user", "content": '请用 JSON 格式回复，包含一个 "greeting" 字段，值为 "你好"'}
        ]
        
        print("📡 调用 JSON 模式...")
        response = llm_client.call_json(messages)
        
        if response:
            print("\n✅ 成功!")
            print(f"📄 JSON 响应:")
            print(json.dumps(response, indent=2, ensure_ascii=False))
            return True
        else:
            print("\n❌ 失败: 没有响应")
            return False
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("🚀 阿里云百炼 API 测试套件")
    print("=" * 80)
    print()
    
    results = []
    
    # 测试 1: 基本 API 连接
    results.append(("基本 API 连接", test_aliyun_api()))
    
    # 如果基本连接成功，继续其他测试
    if results[0][1]:
        results.append(("LLM 客户端", test_llm_client_with_aliyun()))
        results.append(("JSON 模式", test_json_mode()))
    
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
        print("\n🎉 所有测试通过! 阿里云百炼 API 配置成功!")
        print("\n下一步:")
        print("  cd LLM_repo_valid")
        print("  python main.py --limit 5  # 测试处理 5 篇论文")
        return 0
    else:
        print("\n⚠️  部分测试失败，请按照提示配置 API Key")
        return 1


if __name__ == "__main__":
    sys.exit(main())
