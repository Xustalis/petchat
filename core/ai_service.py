"""AI service integration for emotion recognition, memory extraction, and decision support"""
import os
import json
import re
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class AIService:
    """Handles all AI-related operations"""
    
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None):
        """
        Initialize AI service
        
        Args:
            api_key: OpenAI API key (if None, tries to read from env)
            api_base: API base URL (if None, uses default OpenAI or env)
        """
        # Try provided values first, then env, then raise error
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        api_base = api_base or os.getenv("OPENAI_API_BASE")
        
        if not api_key:
            raise ValueError("OpenAI API key is required. Please configure it in the application settings.")
        
        client_kwargs = {"api_key": api_key}
        if api_base:
            client_kwargs["base_url"] = api_base
        
        self.client = OpenAI(**client_kwargs)
        self.model = "gpt-4o-mini"  # Use cheaper model for MVP
    
    def analyze_emotion(self, recent_messages: List[Dict]) -> Dict[str, float]:
        """
        Analyze emotion from recent messages
        
        Returns:
            Dict with emotion types as keys and confidence scores as values
        """
        if len(recent_messages) == 0:
            return {"neutral": 1.0}
        
        # Prepare conversation context
        context = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in recent_messages])
        
        prompt = f"""分析以下对话的整体情绪氛围。注意：分析的是整个对话环境，而不是某个人的情绪。

对话内容：
{context}

请识别对话的整体情绪趋势，并给出概率分布。可能的情绪类型包括：
- neutral: 平和/轻松
- happy: 愉快/兴奋
- tense: 紧张/焦躁
- negative: 消极/冲突

返回JSON格式，包含每个情绪类型的置信度（0-1之间，总和为1）：
{{"neutral": 0.5, "happy": 0.3, "tense": 0.1, "negative": 0.1}}

只返回JSON，不要其他说明。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个情绪分析助手，专注于分析对话的整体氛围。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            # Try to extract JSON from response
            emotion_data = self._extract_json(content)
            if emotion_data and isinstance(emotion_data, dict):
                # Ensure all emotion types have valid scores
                default_emotions = {"neutral": 0.0, "happy": 0.0, "tense": 0.0, "negative": 0.0}
                default_emotions.update({k: float(v) for k, v in emotion_data.items() if k in default_emotions})
                # Normalize to sum to 1.0
                total = sum(default_emotions.values())
                if total > 0:
                    default_emotions = {k: v / total for k, v in default_emotions.items()}
                else:
                    default_emotions = {"neutral": 1.0}
                return default_emotions
            else:
                return {"neutral": 1.0}
        except Exception as e:
            print(f"Error analyzing emotion: {e}")
            return {"neutral": 1.0}
    
    def extract_memories(self, recent_messages: List[Dict]) -> List[Dict]:
        """
        Extract key information (memories) from conversation
        
        Returns:
            List of memory dicts with 'content' and 'category' fields
        """
        if len(recent_messages) < 2:
            return []
        
        context = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in recent_messages])
        
        prompt = f"""从以下对话中提取关键信息。关注：
1. 共同提到的重要事件（出游、考试、截止日期等）
2. 已达成的明确约定
3. 需要记住的长期话题

对话内容：
{context}

返回JSON数组格式，每个元素包含：
- content: 记忆内容（摘要性描述）
- category: 类别（event/agreement/topic等）

如果没有关键信息，返回空数组 []。

只返回JSON数组，不要其他说明。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个信息提取助手，专注于从对话中提取关键信息。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            memories = self._extract_json_array(content)
            return memories if isinstance(memories, list) else []
        except Exception as e:
            print(f"Error extracting memories: {e}")
            return []
    
    def generate_suggestion(self, recent_messages: List[Dict]) -> Optional[Dict]:
        """
        Generate decision/planning suggestion if triggered
        
        Returns:
            Dict with 'title', 'content', and 'type' fields, or None if no suggestion
        """
        # Check if there are planning-related keywords
        context = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in recent_messages[-5:]])
        
        keywords = ['明天', '下周', '周末', '计划', '安排', '出去玩', '聚餐', '学习']
        if not any(keyword in context for keyword in keywords):
            return None
        
        prompt = f"""分析以下对话，如果涉及计划、安排或决策，请生成一个实用的建议。

对话内容：
{context}

如果对话中提到了时间（明天、下周、周末等）和行动（出去玩、安排、计划等），请生成一个建议，包括：
- title: 建议标题
- content: 具体建议内容（可以是行程建议、时间安排、可执行清单等）
- type: 类型（plan/schedule/checklist等）

如果不需要建议，返回null。

只返回JSON对象或null，不要其他说明。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个决策辅助助手，帮助用户整理计划和安排。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            if content.lower() in ['null', 'none', '']:
                return None
            
            suggestion = self._extract_json(content)
            return suggestion if isinstance(suggestion, dict) else None
        except Exception as e:
            print(f"Error generating suggestion: {e}")
            return None
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON object from text"""
        # Try to find JSON object (handles nested structures)
        # Look for { ... } pattern
        brace_count = 0
        start_idx = -1
        
        for i, char in enumerate(text):
            if char == '{':
                if start_idx == -1:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    try:
                        json_str = text[start_idx:i+1]
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
                    start_idx = -1
        
        # Fallback: try parsing entire text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    
    def _extract_json_array(self, text: str) -> List:
        """Extract JSON array from text"""
        # Try to find JSON array [ ... ]
        bracket_count = 0
        start_idx = -1
        
        for i, char in enumerate(text):
            if char == '[':
                if start_idx == -1:
                    start_idx = i
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0 and start_idx != -1:
                    try:
                        json_str = text[start_idx:i+1]
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
                    start_idx = -1
        
        # Fallback: try parsing entire text
        try:
            data = json.loads(text)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

