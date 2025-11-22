"""
LLM 客户端 - 封装对 Gemini API 的调用
"""

import requests
import json
import time
from typing import Dict, Any, Optional, List
from config import (
    GEMINI_API_KEY, GEMINI_API_URL, GEMINI_MODEL,
    LLM_TIMEOUT, LLM_MAX_RETRIES, LLM_TEMPERATURE
)


class LLMClient:
    """封装 LLM API 调用的客户端"""
    
    def __init__(
        self,
        api_key: str = GEMINI_API_KEY,
        api_url: str = GEMINI_API_URL,
        model: str = GEMINI_MODEL,
        temperature: float = LLM_TEMPERATURE,
        timeout: int = LLM_TIMEOUT,
        max_retries: int = LLM_MAX_RETRIES
    ):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
    
    def call(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> Optional[str]:
        """
        调用 LLM API
        
        Args:
            messages: 消息列表，格式为 [{"role": "system"|"user"|"assistant", "content": "..."}]
            temperature: 生成温度，不指定则使用默认值
            max_tokens: 最大生成token数
            json_mode: 是否要求返回JSON格式
            
        Returns:
            LLM 的响应文本，失败返回 None
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return content
                
            except requests.exceptions.Timeout:
                print(f"    ⚠️  LLM API 超时 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                    
            except requests.exceptions.RequestException as e:
                print(f"    ⚠️  LLM API 请求失败: {e} (尝试 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    
            except (KeyError, json.JSONDecodeError) as e:
                print(f"    ⚠️  LLM API 响应解析失败: {e}")
                return None
        
        print(f"    ❌ LLM API 调用失败，已达最大重试次数")
        return None
    
    def call_json(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        调用 LLM API 并解析 JSON 响应
        
        Returns:
            解析后的 JSON 字典，失败返回 None
        """
        response = self.call(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True
        )
        
        if not response:
            return None
        
        try:
            # 提取 JSON（处理 LLM 可能返回 ```json ... ``` 的情况）
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"    ⚠️  JSON 解析失败: {e}")
            print(f"    原始响应: {response[:200]}...")
            return None


# 创建全局客户端实例
llm_client = LLMClient()


def test_llm_client():
    """测试 LLM 客户端是否工作正常"""
    print("测试 LLM 客户端...")
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Hello, World!' in JSON format with a key 'message'."}
    ]
    
    result = llm_client.call_json(messages)
    
    if result:
        print(f"✅ LLM 客户端测试成功: {result}")
    else:
        print("❌ LLM 客户端测试失败")


if __name__ == "__main__":
    test_llm_client()
