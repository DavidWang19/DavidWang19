"""
缓存管理模块
"""
import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str = None, cache_duration_hours: int = 24):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录路径，默认为项目根目录下的 cache 文件夹
            cache_duration_hours: 缓存有效期（小时），默认 24 小时
        """
        if cache_dir is None:
            # 使用项目根目录下的 cache 文件夹
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(project_root, 'cache')
        
        self.cache_dir = cache_dir
        self.cache_duration = timedelta(hours=cache_duration_hours)
        
        # 确保缓存目录存在
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _get_cache_key(self, key: str) -> str:
        """
        生成缓存文件名
        
        Args:
            key: 缓存键
            
        Returns:
            缓存文件的完整路径
        """
        # 使用 MD5 哈希避免文件名过长或包含非法字符
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_key}.json")
    
    def get(self, key: str) -> Optional[Any]:
        """
        从缓存中获取数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的数据，如果不存在或已过期返回 None
        """
        cache_file = self._get_cache_key(key)
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查缓存是否过期
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cached_time > self.cache_duration:
                # 缓存已过期，删除文件
                os.remove(cache_file)
                return None
            
            return cache_data['data']
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # 缓存文件损坏，删除它
            print(f"⚠️  缓存文件损坏，已删除: {e}")
            if os.path.exists(cache_file):
                os.remove(cache_file)
            return None
    
    def set(self, key: str, data: Any) -> None:
        """
        将数据保存到缓存
        
        Args:
            key: 缓存键
            data: 要缓存的数据
        """
        cache_file = self._get_cache_key(key)
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'key': key,
            'data': data
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  缓存保存失败: {e}")
    
    def clear(self, key: Optional[str] = None) -> None:
        """
        清除缓存
        
        Args:
            key: 要清除的缓存键，如果为 None 则清除所有缓存
        """
        if key is None:
            # 清除所有缓存
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
            print("✓ 已清除所有缓存")
        else:
            # 清除指定缓存
            cache_file = self._get_cache_key(key)
            if os.path.exists(cache_file):
                os.remove(cache_file)
                print(f"✓ 已清除缓存: {key}")
    
    def get_cache_info(self) -> dict:
        """
        获取缓存信息
        
        Returns:
            缓存统计信息
        """
        cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
        
        info = {
            'total_files': len(cache_files),
            'cache_dir': self.cache_dir,
            'cache_duration_hours': self.cache_duration.total_seconds() / 3600,
            'files': []
        }
        
        for filename in cache_files:
            cache_file = os.path.join(self.cache_dir, filename)
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                file_info = {
                    'key': cache_data.get('key', 'unknown'),
                    'timestamp': cache_data.get('timestamp', 'unknown'),
                    'size': os.path.getsize(cache_file)
                }
                info['files'].append(file_info)
            except:
                continue
        
        return info


# 创建全局缓存管理器实例
cache_manager = CacheManager()
