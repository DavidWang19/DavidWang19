"""
GitHub API 数据获取模块（GraphQL + REST API）
"""
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict
import config
from cache_manager import cache_manager


async def get_github_contributions_graphql(days: int = 365) -> List[Dict]:
    """
    使用 GraphQL API 获取 GitHub 贡献数据（更全面）
    """
    headers = {
        'Authorization': f'bearer {config.GITHUB_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # 计算时间范围
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)
    
    # GraphQL 查询：使用 contributionCalendar 获取每日提交数据（适合热力图）
    query = """
    query($from: DateTime!, $to: DateTime!) {
      viewer {
        contributionsCollection(from: $from, to: $to) {
          # 1. 每日提交的汇总数据 (Heatmap所需)
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
          # 2. 额外信息
          totalCommitContributions
        }
      }
    }
    """
    
    variables = {
        'from': from_date.isoformat(),
        'to': to_date.isoformat()
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.github.com/graphql',
                json={'query': query, 'variables': variables},
                headers=headers
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                if 'errors' in data:
                    print(f"GraphQL 查询出错: {data['errors']}")
                    return []
                
                # 解析 GraphQL 响应
                contributions = []
                contributions_data = data['data']['viewer']['contributionsCollection']
                total_contributions = contributions_data.get('totalCommitContributions', 0)
                calendar_data = contributions_data['contributionCalendar']
                
                print(f"\nGraphQL API 统计:")
                print(f"  - 总提交贡献数: {total_contributions}")
                print(f"  - 日历总贡献数: {calendar_data['totalContributions']}")
                
                # 遍历每周的每天
                for week in calendar_data['weeks']:
                    for day in week['contributionDays']:
                        contribution_count = day['contributionCount']
                        date = day['date']
                        
                        # 为每个贡献计数创建一条记录
                        for _ in range(contribution_count):
                            contributions.append({
                                'date': date + 'T12:00:00Z',  # 添加时间部分以符合 ISO 格式
                                'repo': 'GitHub Contributions',  # 不区分具体仓库
                                'message': f'{contribution_count} contributions on {date}',
                                'source': 'github'
                            })
                
                print(f"  - 获取的日期范围: {len(calendar_data['weeks'])} 周")
                print(f"\nGraphQL 总共获取 {len(contributions)} 次贡献")
                return contributions
                
    except Exception as e:
        print(f"GraphQL API 调用失败: {e}")
        print("将回退到 REST API...")
        return []


async def fetch_repo_commits(session: aiohttp.ClientSession, repo_name: str, 
                             headers: Dict, since: str) -> List[Dict]:
    """
    异步获取单个仓库的提交记录
    """
    commits_url = f'{config.GITHUB_API_URL}/repos/{repo_name}/commits'
    # 移除 author 过滤，获取所有提交后在本地过滤
    params = {
        'since': since,
        'per_page': 100
    }
    
    try:
        async with session.get(commits_url, headers=headers, params=params) as response:
            # 409 Conflict 通常表示空仓库
            if response.status == 409:
                return []
            
            response.raise_for_status()
            repo_commits = await response.json()
            
            commits = []
            for commit in repo_commits:
                # 在本地过滤，检查提交者是否是当前用户
                author_login = commit.get('author', {}).get('login') if commit.get('author') else None
                committer_login = commit.get('committer', {}).get('login') if commit.get('committer') else None
                commit_author_name = commit['commit']['author']['name']
                
                # 检查是否是当前用户的提交（通过登录名或提交者名称）
                if (author_login == config.GITHUB_USERNAME or 
                    committer_login == config.GITHUB_USERNAME or
                    commit_author_name == config.GITHUB_USERNAME):
                    commits.append({
                        'date': commit['commit']['author']['date'],
                        'repo': repo_name,
                        'message': commit['commit']['message'],
                        'source': 'github'
                    })
            
            if commits:
                print(f"  ✓ {repo_name}: {len(commits)} 次提交")
            return commits
            
    except aiohttp.ClientResponseError as e:
        if e.status == 409:
            return []
        else:
            print(f"  ✗ {repo_name}: 获取失败 ({e.status})")
        return []
    except Exception as e:
        print(f"  ✗ {repo_name}: {e}")
        return []


async def get_github_contributions_async(days: int = 365) -> List[Dict]:
    """
    异步获取 GitHub 贡献数据
    优先使用 GraphQL API，失败时回退到 REST API
    """
    # 检查缓存
    cache_key = f"github_contributions_{days}"
    cached_data = cache_manager.get(cache_key)
    if cached_data is not None:
        print("✓ 使用缓存的 GitHub 数据")
        return cached_data
    
    # 首先尝试 GraphQL API
    contributions = await get_github_contributions_graphql(days)
    
    if contributions:
        cache_manager.set(cache_key, contributions)
        return contributions
    
    print("\n使用 REST API 作为备选方案...")
    
    # 如果 GraphQL 失败，使用 REST API
    headers = {
        'Authorization': f'token {config.GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    since = (datetime.now() - timedelta(days=days)).isoformat()
    
    try:
        # 获取用户的所有仓库
        async with aiohttp.ClientSession() as session:
            repos_url = f'{config.GITHUB_API_URL}/user/repos'
            # 修改：包含所有类型的仓库，包括协作者、组织成员等
            params = {'affiliation': 'owner,collaborator,organization_member', 'per_page': 100}
            
            async with session.get(repos_url, headers=headers, params=params) as response:
                response.raise_for_status()
                repos = await response.json()
                
                print(f"找到 {len(repos)} 个 GitHub 仓库，开始并发获取提交记录...")
                
                # 并发获取所有仓库的提交记录（不限制 author，获取所有提交后再过滤）
                tasks = [
                    fetch_repo_commits(session, repo['full_name'], headers, since)
                    for repo in repos
                ]
                
                results = await asyncio.gather(*tasks)
                
                # 合并所有结果
                all_commits = []
                repos_with_commits = 0
                for commits in results:
                    if commits:
                        repos_with_commits += 1
                    all_commits.extend(commits)
                
                print(f"\nGitHub 扫描完成:")
                print(f"  - 总仓库数: {len(repos)}")
                print(f"  - 有提交的仓库: {repos_with_commits}")
                print(f"  - 总提交数: {len(all_commits)}")
                return all_commits
        
    except Exception as e:
        print(f"获取 GitHub 数据失败: {e}")
        return []


def get_github_contributions(days: int = 365) -> List[Dict]:
    """
    获取 GitHub 贡献数据（同步包装器）
    """
    return asyncio.run(get_github_contributions_async(days))


async def get_github_stats_async() -> Dict:
    """
    异步获取 GitHub 统计数据
    """
    # 检查缓存
    cache_key = "github_stats"
    cached_data = cache_manager.get(cache_key)
    if cached_data is not None:
        print("✓ 使用缓存的 GitHub 统计数据")
        return cached_data
    
    headers = {
        'Authorization': f'token {config.GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    stats = {
        'total_repos': 0,
        'total_stars': 0,
        'total_forks': 0,
        'languages': {}
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            repos_url = f'{config.GITHUB_API_URL}/user/repos'
            # 使用 affiliation 获取所有相关仓库（包括私有）
            params = {'affiliation': 'owner', 'per_page': 100}
            
            async with session.get(repos_url, headers=headers, params=params) as response:
                response.raise_for_status()
                repos = await response.json()
                
                stats['total_repos'] = len(repos)
                
                for repo in repos:
                    stats['total_stars'] += repo.get('stargazers_count', 0)
                    stats['total_forks'] += repo.get('forks_count', 0)
                    
                    # 获取仓库语言
                    language = repo.get('language')
                    if language:
                        stats['languages'][language] = stats['languages'].get(language, 0) + 1
        
        # 保存到缓存
        cache_manager.set(cache_key, stats)
        
    except Exception as e:
        print(f"获取 GitHub 统计数据失败: {e}")
    
    return stats


def get_github_stats() -> Dict:
    """
    获取 GitHub 统计数据（同步包装器）
    
    Returns:
        统计数据字典
    """
    return asyncio.run(get_github_stats_async())
