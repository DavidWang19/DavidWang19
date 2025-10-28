"""
主程序：获取数据并生成图表
"""
import sys
from datetime import datetime
from github_api import get_github_contributions, get_github_stats
from gitea_api import get_gitea_contributions, get_gitea_stats
from wakatime_api import get_wakatime_all_time_stats
from visualize import (
    create_contributions_heatmap,
    create_wakatime_language_pie,
    create_summary_stats
)


def main():
    """主函数"""
    print("=" * 60)
    print("GitHub Profile Stats Generator")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 获取 GitHub 贡献数据
    print("📊 正在获取 GitHub 数据...")
    github_contributions = get_github_contributions(days=372)  # 52周+1周，确保按周对齐
    github_stats = get_github_stats()
    print()
    
    # 2. 获取 Gitea 贡献数据
    print("📊 正在获取 Gitea 数据...")
    gitea_contributions = get_gitea_contributions(days=372)  # 52周+1周，确保按周对齐
    gitea_stats = get_gitea_stats()
    print()
    
    # 3. 合并贡献数据
    all_contributions = github_contributions + gitea_contributions
    print(f"✅ 总共获取 {len(all_contributions)} 次贡献记录")
    print(f"   - GitHub: {len(github_contributions)} 次")
    print(f"   - Gitea: {len(gitea_contributions)} 次")
    print()
    
    # 4. 获取 WakaTime 数据
    print("📊 正在获取 WakaTime 全时间段数据...")
    wakatime_stats = get_wakatime_all_time_stats()
    print()
    
    # 5. 生成图表
    print("🎨 正在生成图表...")
    
    try:
        # 贡献热力图
        print("  - 生成贡献热力图...")
        create_contributions_heatmap(all_contributions)
        create_contributions_heatmap(all_contributions, theme='dark')
        
        # WakaTime 语言饼图
        if wakatime_stats:
            print("  - 生成 WakaTime 语言饼图...")
            create_wakatime_language_pie(wakatime_stats, 'wakatime_languages_light.svg', 'light')
            create_wakatime_language_pie(wakatime_stats, 'wakatime_languages_dark.svg', 'dark')
        
        # 综合统计图
        print("  - 生成综合统计图...")
        create_summary_stats(github_stats, gitea_stats, all_contributions, 'summary_stats_light.svg', 'light')
        create_summary_stats(github_stats, gitea_stats, all_contributions, 'summary_stats_dark.svg', 'dark')
        
        print()
        print("✅ 所有图表生成完成！")
        
    except Exception as e:
        print(f"❌ 生成图表时出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    print("=" * 60)
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
