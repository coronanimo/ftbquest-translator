import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, NamedTuple, Dict, Optional
from dataclasses import dataclass
from config import getConfig
from database import Database
import json
import os
import datetime
from pathlib import Path

@dataclass
class BatchItem:
    modid: str
    key: str
    text: str
    index: int  # 原始列表中的索引

class TranslationResult(NamedTuple):
    modid: str
    key: str
    original: str
    translation: str

class LLMClient:
    # 翻译助手的系统提示词
    SYSTEM_PROMPT = (
        "你是一个专业的Minecraft模组词条翻译助手。"
        "发送出去的格式是一个JSON对象，格式为：{\"items\":[{\"m\":\"模组ID\",\"texts\":[\"待翻译文本1\",\"待翻译文本2\"]}]}。\n"
        "其中m是modid（模组ID），texts是该模组需要翻译的文本数组。\n"
        "返回的格式与发出去的格式一致，顺序、数量也要一致。不要增加额外信息，以免json无法解析\n"
        "翻译规则：\n"
        "1. 对于类似于CF、FE、RF、CF/t、FE/t、RF/t这样的单位以及类似字段，保持原样\n"
        "2. 对于包含%s、%d、%1$s等控制字符的文本，保持这些控制字符的原样\n"
        "3. 对于包含<...>、[...]等标签的文本，保持标签的原样，里面的内容可以考虑翻译\n"
        "4. 如果遇到类似 +10 Damage 这样的数值描述，保持数值的原样，Damage这个单词可以翻译\n"
        "5. 使用Minecraft中文社区常用的翻译方式\n"
    )

    def __init__(self, db: Database):
        self.api_base = getConfig('LLM', 'api_base')
        self.api_key = getConfig('LLM', 'api_key')
        self.model = getConfig('LLM', 'model')
        self.max_tokens = int(getConfig('LLM', 'max_tokens'))
        self.parallel_requests = int(getConfig('LLM', 'parallel_requests'))
        self.db = db
        
        # 添加日志目录初始化
        self.log_dir = Path('logs')
        self.log_dir.mkdir(exist_ok=True)

    def translate_batch(self, items: List[Tuple[str, str, str]], use_cache: bool = True) -> List[TranslationResult]:
        """批量翻译文本条目"""
        total_items = len(items)
        print(f"\n开始处理 {total_items} 个待翻译条目...")
        
        # 1. 先检查缓存
        need_translate = []
        results = [None] * total_items
        
        if use_cache:
            cached_count = 0
            for i, (modid, key, text) in enumerate(items):
                cached_translation = self.db.get_cached_translation(modid, text)
                if cached_translation:
                    cached_count += 1
                    results[i] = TranslationResult(
                        modid=modid,
                        key=key,
                        original=text,
                        translation=cached_translation
                    )
                else:
                    need_translate.append(BatchItem(modid, key, text, i))
            
            if cached_count > 0:
                print(f"✓ 从缓存中获取 {cached_count} 个翻译")
        else:
            need_translate = [BatchItem(modid, key, text, i) 
                             for i, (modid, key, text) in enumerate(items)]

        # 2. 处理未缓存的条目
        if need_translate:
            print(f"→ 需要翻译 {len(need_translate)} 个条目...")
            batches = self._create_batches(need_translate)
            print(f"→ 已分成 {len(batches)} 个批次")
            
            asyncio.run(self._process_all_batches(batches, results, use_cache))

        return [r for r in results if r is not None]

    def _create_batches(self, items: List[BatchItem]) -> List[List[BatchItem]]:
        """根据token限制将条目分成多个批次"""
        prompt_tokens = self._calculate_tokens(self.SYSTEM_PROMPT)
        max_batch_tokens = self.max_tokens * 0.5
        
        batches = []
        current_batch = []
        current_tokens = prompt_tokens
        
        # 预估JSON结构的基础token开销
        json_overhead = self._calculate_tokens('{"items":["modid":"","texts":[]..]}')
        current_tokens += json_overhead
        
        for item in items:
            # 计算该项的token开销（包括modid和text的JSON结构）
            item_tokens = (                
                self._calculate_tokens(item.text) + 
                self._calculate_tokens('{"t":""},')
            )
            
            if current_tokens + item_tokens > max_batch_tokens:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_tokens = prompt_tokens + json_overhead
            
            current_batch.append(item)
            current_tokens += item_tokens
        
        if current_batch:
            batches.append(current_batch)
        
        return batches

    async def _process_all_batches(self, batches: List[List[BatchItem]], 
                                 results: List[Optional[TranslationResult]], 
                                 use_cache: bool):
        """并行处理所有批次"""
        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(self.parallel_requests)
            
            # 创建所有任务
            tasks = [
                self._process_batch(session, semaphore, batch, results, use_cache)
                for batch in batches
            ]
            
            # 等待所有任务完成，即使有任务失败也不会影响其他任务
            completed = 0
            for task in asyncio.as_completed(tasks):
                try:
                    await task
                    completed += 1
                    print(f"完成批次 {completed}/{len(batches)}")
                except Exception as e:
                    print(f"批次处理失败: {str(e)}")
                    # 继续处理其他批次，不会因为一个批次失败就全部终止

            print(f"所有批次处理完成 ({completed}/{len(batches)})")

    async def _process_batch(self, session: aiohttp.ClientSession,
                           semaphore: asyncio.Semaphore,
                           batch: List[BatchItem],
                           results: List[Optional[TranslationResult]],
                           use_cache: bool):
        """处理单个批次"""
        async with semaphore:
            print(f"开始处理批次（{len(batch)}个条目）...")
            try:
                translations = await self._translate_batch_async(session, batch)
                
                # 只检查是否为字符串类型，空字符串也是有效结果
                if translations and all(isinstance(t, str) for t in translations):
                    # 更新缓存和结果
                    for item, translation in zip(batch, translations):
                        if use_cache:
                            self.db.cache_translation(
                                modid=item.modid,
                                key=item.key,
                                original=item.text,
                                translation=translation
                            )
                        
                        results[item.index] = TranslationResult(
                            modid=item.modid,
                            key=item.key,
                            original=item.text,
                            translation=translation
                        )
                    
                    if use_cache:
                        cache_count, earliest_cache = self.db.get_cache_stats()
                        print(f"✓ 已更新缓存，当前共有 {cache_count} 条翻译记录 (最早记录: {earliest_cache})")
                else:                    
                    print(f"批次处理失败：存在无效的翻译结果")
                
            except Exception as e:
                print(f"处理批次时出错: {str(e)}")

    async def _translate_batch_async(self, session: aiohttp.ClientSession, 
                                   batch: List[BatchItem]) -> List[str]:
        """异步调用API翻译一批文本"""
        # 生成日志文件名，使用时间戳
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        log_file = self.log_dir / f'llm_request_{timestamp}.log'
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # 按modid分组构建JSON，同时保存每个文本的位置信息
        grouped_items = {}
        position_map = {}  # 记录每个(modid, text_index)对应batch中的位置
        current_pos = 0
        
        for item in batch:
            if item.modid not in grouped_items:
                grouped_items[item.modid] = []
            text_index = len(grouped_items[item.modid])
            grouped_items[item.modid].append(item.text)
            position_map[(item.modid, text_index)] = current_pos
            current_pos += 1
        
        # 构建JSON格式的翻译请求
        translation_request = {
            "items": [
                {"m": modid, "texts": texts}
                for modid, texts in grouped_items.items()
            ]
        }
        
        messages = [{
            'role': 'system',
            'content': self.SYSTEM_PROMPT
        }, {
            'role': 'user',
            'content': json.dumps(translation_request, ensure_ascii=False)
        }]

        data = {
            'model': self.model,
            'messages': messages,
            'max_tokens': self.max_tokens
        }

        # 写入请求日志
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("=== LLM Request ===\n")
            f.write(json.dumps(data, ensure_ascii=False, indent=2))
            f.write("\n\n")

        try:
            async with session.post(f'{self.api_base}/v1/chat/completions',
                                  headers=headers,
                                  json=data) as response:
                response.raise_for_status()
                result = await response.json()
                
                # 写入响应日志
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write("=== LLM Response ===\n")
                    f.write(json.dumps(result, ensure_ascii=False, indent=2))
                    f.write("\n\n")

                response_text = result['choices'][0]['message']['content'].strip()
                
                # 处理响应文本...
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

                try:
                    response_json = json.loads(response_text)
                    
                    # 添加详细的调试日志
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write("\n=== Debug Information ===\n")
                        # 记录原始请求中每个modid的条目数量
                        f.write("Original Request Items Count:\n")
                        for modid, texts in grouped_items.items():
                            f.write(f"ModID: {modid}, Items: {len(texts)}\n")
                            f.write("Texts:\n")
                            for i, text in enumerate(texts):
                                f.write(f"  {i}: {text}\n")
                        
                        # 记录响应中每个modid的条目数量
                        f.write("\nResponse Items Count:\n")
                        for group in response_json["items"]:
                            modid = group["m"]
                            texts = group["texts"]
                            f.write(f"ModID: {modid}, Items: {len(texts)}\n")
                            f.write("Translations:\n")
                            for i, text in enumerate(texts):
                                f.write(f"  {i}: {text}\n")
                        
                        # 检查并记录任何不匹配
                        f.write("\nMismatch Check:\n")
                        for group in response_json["items"]:
                            modid = group["m"]
                            original_count = len(grouped_items.get(modid, []))
                            response_count = len(group["texts"])
                            if original_count != response_count:
                                f.write(f"WARNING: Count mismatch for {modid}!\n")
                                f.write(f"  Original: {original_count}, Response: {response_count}\n")
                    
                    # 写入解析后的翻译结果
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write("=== Parsed Translations ===\n")
                        f.write(json.dumps(response_json, ensure_ascii=False, indent=2))
                        f.write("\n")
                    
                    # 还原顺序的代码保持不变...
                    translations = [None] * len(batch)
                    for group in response_json["items"]:
                        modid = group["m"]
                        for i, translation in enumerate(group["texts"]):
                            original_pos = position_map[(modid, i)]
                            translations[original_pos] = translation
                    
                    return translations
                    
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    error_msg = f"解析翻译响应失败: {str(e)}{response_text}"
                    print(error_msg)
                    # 写入错误信息
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write("=== Error ===\n")
                        f.write(error_msg)
                        f.write("\n")
                    return [None] * len(batch)
                
        except Exception as e:
            error_msg = f'批量翻译失败: {str(e)}'
            print(error_msg)
            # 写入错误信息
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write("=== Error ===\n")
                f.write(error_msg)
                f.write("\n")
            return [None] * len(batch)

    def _calculate_tokens(self, text: str) -> int:
        """计算文本的token数量"""
        token_count = 0
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # 中文字符
                token_count += 0.66
            else:  # 其他字符（主要是英文）
                token_count += 0.5
        return int(token_count)
