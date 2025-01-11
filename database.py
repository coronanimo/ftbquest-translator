import sqlite3
from config import getDefaultConfig
from typing import List, Tuple
import hashlib

class Database:
    def __init__(self):
        self.db_path = getDefaultConfig('database_path')
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()

    def _create_tables(self):
        """创建数据库表"""
        cursor = self.conn.cursor()
        
        # 创建翻译词条表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS translations (
                modid TEXT NOT NULL,
                key TEXT NOT NULL,
                enus TEXT NOT NULL,
                zhcn1 TEXT,
                zhcn2 TEXT,
                zhcn3 TEXT,
                PRIMARY KEY (modid, key)
            )
        ''')
        
        # 创建翻译缓存表 - 修改表结构，增加modid和key
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS translation_cache (
                text_hash TEXT NOT NULL,
                modid TEXT NOT NULL,
                key TEXT NOT NULL,
                original TEXT NOT NULL,
                translation TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (text_hash, modid)
            )
        ''')
        
        self.conn.commit()

    def insert_translation(self, modid: str, key: str, enus: str):
        """插入新的翻译词条"""
        cursor = self.conn.cursor()        
        cursor.execute('''
            INSERT INTO translations (modid, key, enus)
            VALUES (?, ?, ?)
            ON CONFLICT(modid, key) DO UPDATE SET
            enus = excluded.enus
        ''', (modid, key, enus))
        self.conn.commit()

    def update_zhcn1(self, modid: str, key: str, zhcn1: str):
        """更新zhcn1字段"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE translations
            SET zhcn1 = ?
            WHERE modid = ? AND key = ?
        ''', (zhcn1, modid, key))
        self.conn.commit()

    def update_zhcn2(self, modid: str, key: str, zhcn2: str):
        """更新zhcn2字段"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE translations
            SET zhcn2 = ?
            WHERE modid = ? AND key = ?
        ''', (zhcn2, modid, key))
        self.conn.commit()

    def update_zhcn3(self, modid: str, key: str, zhcn3: str):
        """更新zhcn3字段"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE translations
            SET zhcn3 = ?
            WHERE modid = ? AND key = ?
        ''', (zhcn3, modid, key))
        self.conn.commit()

    def get_untranslated(self) -> List[Tuple[str, str, str]]:
        """获取需要翻译的词条"""
        cursor = self.conn.cursor()
        
        # 先获取所有 zhcn1 不为空的记录
        cursor.execute('''
            SELECT modid, key, enus, zhcn1
            FROM translations
            WHERE zhcn1 IS NOT NULL
        ''')
        
        # 检查并更新纯英文的 zhcn1
        for row in cursor.fetchall():
            zhcn1 = row[3]
            # 检查是否为纯英文文本(不含中文字符)
            if len(zhcn1) > 6 and not any('\u4e00' <= c <= '\u9fff' for c in zhcn1):
                cursor.execute('''
                    UPDATE translations
                    SET zhcn1 = NULL
                    WHERE modid = ? AND key = ?
                ''', (row[0], row[1]))
        self.conn.commit()
        
        # 然后获取所有需要翻译的记录
        cursor.execute('''
            SELECT modid, key, enus
            FROM translations
            WHERE zhcn1 IS NULL AND zhcn2 IS NULL AND zhcn3 IS NULL
            ORDER BY RANDOM()
        ''')
        return cursor.fetchall()

    def get_low_confidence(self) -> List[Tuple[str, str, str]]:
        """获取低信心值的条目（有zhcn2但没有zhcn1的条目）"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT modid, key, enus 
            FROM translations
            WHERE zhcn2 IS NOT NULL AND zhcn1 IS NULL AND zhcn3 IS NULL
            ORDER BY RANDOM()
        ''')
        return cursor.fetchall()

    def cache_purge(self):
        """清除缓存"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM translation_cache')
        self.conn.commit()

    def cache_translation(self, modid: str, key: str, original: str, translation: str) -> None:
        """缓存翻译结果"""
        cursor = self.conn.cursor()
        text_hash = hashlib.md5(original.encode('utf-8')).hexdigest()
        
        cursor.execute('''
            INSERT OR REPLACE INTO translation_cache 
            (text_hash, modid, key, original, translation)
            VALUES (?, ?, ?, ?, ?)
        ''', (text_hash, modid, key, original, translation))
        
        self.conn.commit()

    def get_cached_translation(self, modid: str, text: str) -> str | None:
        """获取缓存的翻译结果，考虑mod上下文"""
        cursor = self.conn.cursor()
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        
        cursor.execute('''
            SELECT translation FROM translation_cache
            WHERE text_hash = ? AND modid = ?
        ''', (text_hash, modid))
        
        result = cursor.fetchone()
        return result[0] if result else None

    def get_cache_stats(self) -> tuple[int, str]:
        """获取缓存统计信息"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*), MIN(created_at) FROM translation_cache')
        count, earliest = cursor.fetchone()
        return count, earliest or "N/A"

    def close(self):
        """关闭数据库连接"""
        self.conn.close()
