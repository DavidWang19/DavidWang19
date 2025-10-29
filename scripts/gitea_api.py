"""
Gitea API 数据获取模块（Heatmap API）
"""
import os
import asyncio
import aiohttp
import ssl
from datetime import datetime, timedelta
from typing import List, Dict
import config
from cache_manager import cache_manager


def get_ssl_context():
    """
    获取 SSL 上下文配置
    """
    if config.GITEA_CERT:
        cert_path = config.GITEA_CERT
        # 如果是相对路径，转换为绝对路径（相对于项目根目录）
        if not os.path.isabs(cert_path):
            cert_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), cert_path)
        
        if os.path.exists(cert_path):
            print(f"使用 SSL 证书: {cert_path}")
            ssl_context = ssl.create_default_context(cafile=cert_path)
            # 允许旧版本的证书和缺少扩展的证书
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context
        else:
            print(f"⚠️  证书文件不存在: {cert_path}，将跳过 SSL 验证")
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context
    else:
        print("⚠️  未配置 GITEA_CERT，将跳过 SSL 验证")
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context


async def get_gitea_contributions_async(days: int = 365) -> List[Dict]:
    """
    使用 Gitea Heatmap API 获取贡献数据
    """
    if not config.GITEA_URL or not config.GITEA_USERNAME:
        print("Gitea 配置未设置，跳过")
        return []
    
    # 检查缓存
    cache_key = f"gitea_contributions_{days}"
    cached_data = cache_manager.get(cache_key)
    if cached_data is not None:
        print("✓ 使用缓存的 Gitea 数据")
        return cached_data
    
    ssl_context = get_ssl_context()
    
    try:
        # 使用 Gitea 的 heatmap API
        heatmap_url = f'{config.GITEA_URL}/api/v1/users/{config.GITEA_USERNAME}/heatmap?token={config.GITEA_TOKEN}'
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(heatmap_url) as response:
                response.raise_for_status()
                heatmap_data = await response.json()
                
                print(f"\nGitea Heatmap API 获取到 {len(heatmap_data)} 天的数据")
                
                # 计算时间范围
                cutoff_date = datetime.now() - timedelta(days=days)
                
                # 转换 heatmap 数据为贡献列表
                contributions_list = []
                total_contributions = 0
                filtered_days = 0
                
                for entry in heatmap_data:
                    timestamp = entry['timestamp']
                    contribution_count = entry['contributions']
                    
                    # 转换时间戳为日期（Gitea 使用秒级 Unix 时间戳）
                    contribution_date = datetime.fromtimestamp(timestamp)
                    
                    # 只保留指定时间范围内的数据
                    if contribution_date >= cutoff_date:
                        filtered_days += 1
                        total_contributions += contribution_count
                        
                        # 为每个贡献创建一条记录
                        for _ in range(contribution_count):
                            contributions_list.append({
                                'date': contribution_date.isoformat() + 'Z',
                                'repo': 'Gitea Contributions',
                                'message': f'{contribution_count} contributions on {contribution_date.date()}',
                                'source': 'gitea'
                            })
                
                print(f"  - 时间范围: 最近 {days} 天")
                print(f"  - 符合范围的天数: {filtered_days}")
                print(f"  - 总贡献数: {total_contributions}")
                print(f"\nGitea 总共获取 {len(contributions_list)} 次贡献")
                
                # 保存到缓存
                cache_manager.set(cache_key, contributions_list)
                
                return contributions_list
        
    except Exception as e:
        print(f"获取 Gitea Heatmap 数据失败: {e}")
        raise e


def get_gitea_contributions(days: int = 365) -> List[Dict]:
    """
    获取 Gitea 贡献数据（同步包装器）
    """
    return asyncio.run(get_gitea_contributions_async(days))


async def get_gitea_stats_async() -> Dict:
    """
    异步获取 Gitea 统计数据
    """
    if not config.GITEA_URL or not config.GITEA_TOKEN:
        return {}
    
    # 检查缓存
    cache_key = "gitea_stats"
    cached_data = cache_manager.get(cache_key)
    if cached_data is not None:
        print("✓ 使用缓存的 Gitea 统计数据")
        return cached_data
    
    headers = {
        'Authorization': f'token {config.GITEA_TOKEN}',
        'Accept': 'application/json'
    }
    
    ssl_context = get_ssl_context()
    
    stats = {
        'total_repos': 0,
        'total_stars': 0,
    }
    
    try:
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            repos_url = f'{config.GITEA_URL}/api/v1/user/repos'
            params = {'limit': 100}
            
            async with session.get(repos_url, headers=headers, params=params) as response:
                response.raise_for_status()
                repos = await response.json()
                
                stats['total_repos'] = len(repos)
                
                for repo in repos:
                    stats['total_stars'] += repo.get('stars_count', 0)
        
        # 保存到缓存
        cache_manager.set(cache_key, stats)
        
    except Exception as e:
        print(f"获取 Gitea 统计数据失败: {e}")
        raise e
    
    return stats


def get_gitea_stats() -> Dict:
    """
    获取 Gitea 统计数据（同步包装器）
    
    Returns:
        统计数据字典
    """
    return asyncio.run(get_gitea_stats_async())
