"""
数据可视化模块
"""
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
import os
import config

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 设置样式
sns.set_style("whitegrid")
sns.set_palette("husl")


def ensure_figures_dir():
    """确保 figures 目录存在"""
    if not os.path.exists(config.FIGURES_DIR):
        os.makedirs(config.FIGURES_DIR)


def create_contributions_heatmap(contributions: List[Dict], theme: str = 'light'):
    """
    创建 GitHub 风格的贡献日历热力图
    
    Args:
        contributions: 贡献记录列表
        theme: 主题模式，'light' 或 'dark'
    """
    ensure_figures_dir()
    
    if not contributions:
        print("没有贡献数据，跳过热力图生成")
        return
    
    # 转换为 DataFrame
    df = pd.DataFrame(contributions)
    df['date'] = pd.to_datetime(df['date'], utc=True)
    df['date_only'] = df['date'].dt.tz_localize(None).dt.date
    
    # 按日期统计总贡献数
    daily_counts = df.groupby('date_only').size()
    
    # 生成最近一年的日期范围（不包括未来日期）
    end_date = datetime.now().date()
    # 找到end_date所在周的周日
    end_weekday = datetime.now().weekday()  # 0=Monday, 6=Sunday
    end_of_week = end_date + timedelta(days=(6 - end_weekday) if end_weekday != 6 else 0)  # 本周周六
    start_date = end_of_week - timedelta(days=364)  # 52周 * 7天
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # 创建完整的日期索引，填充缺失日期
    all_counts = pd.Series(0, index=date_range.date)
    for date, count in daily_counts.items():
        if date in all_counts.index:
            all_counts[date] = count
    
    # 转换为周和星期几的矩阵（GitHub 风格）
    # 行：星期几（0=周日, 6=周六）
    # 列：周数
    weeks = {}
    for date, count in all_counts.items():
        date_obj = pd.Timestamp(date)
        # 跳过未来日期
        if date_obj.date() > end_date:
            continue
        
        week = (date_obj - pd.Timestamp(start_date)).days // 7
        weekday = date_obj.dayofweek
        weekday = (weekday + 1) % 7  # 转换为 GitHub 风格（周日=0）
        
        if week not in weeks:
            weeks[week] = {}
        weeks[week][weekday] = count
    
    # 构建矩阵
    num_weeks = max(weeks.keys()) + 1
    matrix = np.zeros((7, num_weeks))
    for week, days in weeks.items():
        for day, count in days.items():
            matrix[day, week] = count
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(16, 3))
    
    # 根据主题选择颜色方案
    if theme == 'dark':
        # GitHub 深色模式配色
        colors = ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353']
        bg_color = '#0d1117'
        text_color = '#c9d1d9'
        border_color = '#30363d'
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
    else:
        # GitHub 浅色模式配色
        colors = ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39']
        bg_color = 'white'
        text_color = 'black'
        border_color = 'white'
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
    
    max_count = matrix.max()
    
    if max_count > 0:
        # 定义颜色分级
        def get_color(count):
            if count == 0:
                return colors[0]
            elif count <= max_count * 0.25:
                return colors[1]
            elif count <= max_count * 0.5:
                return colors[2]
            elif count <= max_count * 0.75:
                return colors[3]
            else:
                return colors[4]
        
        # 绘制格子
        for week in range(num_weeks):
            for day in range(7):
                # 计算该格子对应的日期
                days_offset = week * 7 + day
                current_date = start_date + timedelta(days=days_offset)
                
                # 跳过未来日期
                if current_date > end_date:
                    continue
                
                count = matrix[day, week]
                color = get_color(count)
                rect = plt.Rectangle((week, 6-day), 1, 1, 
                                    facecolor=color, 
                                    edgecolor=border_color, 
                                    linewidth=2)
                ax.add_patch(rect)
    
    # 设置坐标轴
    ax.set_xlim(0, num_weeks)
    ax.set_ylim(0, 7)
    ax.set_aspect('equal')
    
    # Y轴标签（星期）
    day_labels = ['', 'Mon', '', 'Wed', '', 'Fri', '']
    ax.set_yticks(np.arange(0.5, 7.5, 1))
    ax.set_yticklabels(day_labels[::-1], fontsize=9, color=text_color)
    
    # X轴标签（月份）
    month_positions = []
    month_labels = []
    current_month = None
    for week in range(num_weeks):
        date = pd.Timestamp(start_date) + timedelta(weeks=week)
        if date.month != current_month:
            month_positions.append(week)
            month_labels.append(date.strftime('%b'))
            current_month = date.month
    
    ax.set_xticks(month_positions)
    ax.set_xticklabels(month_labels, fontsize=9, color=text_color)
    
    # 移除边框
    ax.grid(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='both', which='both', length=0)
    
    # 标题
    total_contributions = int(all_counts.sum())
    ax.set_title(f'Contributions in Last Year ({total_contributions} total)', 
                fontsize=16, fontweight='bold', pad=20, loc='left', color=text_color)
    
    # 添加图例
    legend_x = num_weeks - 10
    legend_y = -1.5
    ax.text(legend_x - 0.8, legend_y, 'Less', fontsize=8, ha='right', va='center', color=text_color)
    for i, color in enumerate(colors):
        rect = plt.Rectangle((legend_x + i * 1, legend_y - 0.3), 0.8, 0.8,
                            facecolor=color, edgecolor=border_color, linewidth=1)
        rect.set_clip_on(False)
        ax.add_patch(rect)
    ax.text(legend_x + len(colors) * 1 + 0.5, legend_y, 'More', 
           fontsize=8, ha='left', va='center', color=text_color)
    
    # 在 More 旁边显示最大值
    max_count_int = int(max_count)
    legend_color = '#8b949e' if theme == 'dark' else 'gray'
    ax.text(legend_x + len(colors) * 1 + 1.8, legend_y, f'(max: {max_count_int})', 
           fontsize=8, ha='left', va='center', color=legend_color, style='italic')

    output_file = f"contributions_heatmap_{theme}.svg"
    plt.savefig(os.path.join(config.FIGURES_DIR, output_file), format='svg', bbox_inches='tight')
    plt.close()

    print(f"GitHub 风格贡献日历图已保存: {output_file}")


def create_wakatime_language_pie(stats: Dict, output_file: str = 'wakatime_languages.svg', theme: str = 'light'):
    """
    创建 WakaTime 编程语言饼图
    
    Args:
        stats: WakaTime 统计数据
        output_file: 输出文件名
        theme: 主题模式 ('light' 或 'dark')
    """
    ensure_figures_dir()
    
    if not stats or not stats.get('languages'):
        print("没有 WakaTime 数据，跳过图表生成")
        return
    
    # 获取语言数据
    languages = stats['languages']
    
    # 根据主题设置颜色 - GitHub 风格
    if theme == 'dark':
        bg_color = '#0d1117'
        text_color = '#c9d1d9'
        legend_bg = '#161b22'
        legend_edge = '#30363d'
        fig, ax = plt.subplots(figsize=(12, 8), facecolor=bg_color)
        ax.set_facecolor(bg_color)
    else:
        bg_color = '#ffffff'
        text_color = '#24292f'
        legend_bg = '#f6f8fa'
        legend_edge = '#d0d7de'
        fig, ax = plt.subplots(figsize=(12, 8), facecolor=bg_color)
        ax.set_facecolor(bg_color)
    
    # 提取数据
    labels = [lang['name'] for lang in languages]
    sizes = [lang['percent'] for lang in languages]
    
    # 为小于1%的类别创建空标签（在饼图上不显示，但图例中保留）
    pie_labels = [name if percent >= 1.0 else '' for name, percent in zip(labels, sizes)]
    
    # GitHub 风格配色方案
    if theme == 'dark':
        # GitHub 深色模式颜色
        github_colors = ['#58a6ff', '#56d364', '#f85149', '#db6d28', '#c297ff', 
                        '#76e3ea', '#ffa657', '#f0883e', '#7ee787', '#79c0ff']
    else:
        # GitHub 浅色模式颜色
        github_colors = ['#0969da', '#1a7f37', '#cf222e', '#bc4c00', '#8250df',
                        '#1b7c83', '#fb8500', '#d15704', '#116329', '#0550ae']
    
    # 根据语言数量循环使用颜色
    colors = [github_colors[i % len(github_colors)] for i in range(len(labels))]
    
    # 创建饼图，使用自定义的标签显示函数
    def autopct_format(pct):
        return f'{pct:.1f}%' if pct >= 1.0 else ''
    
    wedges, texts, autotexts = ax.pie(
        sizes, 
        labels=pie_labels, 
        autopct=autopct_format,
        startangle=90,
        colors=colors,
        textprops={'fontsize': 10, 'weight': 'bold', 'color': text_color}
    )
    
    # 设置百分比文字样式
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(9)
        autotext.set_weight('bold')
    
    # 添加图例（显示百分比）- GitHub 风格
    legend_labels = [
        f"{lang['name']} ({lang['percent']:.1f}%)" 
        for lang in languages
    ]
    legend = ax.legend(
        legend_labels,
        loc='center left',
        bbox_to_anchor=(1.05, 0, 0.5, 1),
        fontsize=9,
        facecolor=legend_bg,
        edgecolor=legend_edge,
        labelcolor=text_color,
        framealpha=1.0
    )
    
    plt.savefig(
        os.path.join(config.FIGURES_DIR, output_file),
        format='svg',
        bbox_inches='tight',
        facecolor=bg_color
    )
    plt.close()
    
    print(f"✓ WakaTime 语言饼图已保存: {output_file}")


def create_summary_stats(github_stats: Dict, gitea_stats: Dict, 
                        contributions: List[Dict], output_file: str = 'summary_stats.svg', theme: str = 'light'):
    """
    创建综合统计卡片
    
    Args:
        github_stats: GitHub 统计数据
        gitea_stats: Gitea 统计数据
        contributions: 贡献记录列表
        output_file: 输出文件名
        theme: 主题模式，'light' 或 'dark'
    """
    ensure_figures_dir()
    
    # 创建横版卡片
    fig = plt.figure(figsize=(8.5, 2))
    
    # GitHub 风格配色方案
    if theme == 'dark':
        bg_color = '#0d1117'
        card_bg_color = '#161b22'
        card_border_color = '#30363d'
        mini_card_bg = '#161b22'
        mini_card_border = '#30363d'
        text_color = '#8b949e'
        title_color = '#c9d1d9'
    else:
        bg_color = '#ffffff'
        card_bg_color = '#f6f8fa'
        card_border_color = '#d0d7de'
        mini_card_bg = '#ffffff'
        mini_card_border = '#d0d7de'
        text_color = '#57606a'
        title_color = '#24292f'
    
    fig.patch.set_facecolor(bg_color)
    
    # 创建主容器
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 8.5)
    ax.set_ylim(0, 2)
    ax.axis('off')
    ax.set_facecolor(bg_color)
    
    # 添加圆角矩形背景
    from matplotlib.patches import FancyBboxPatch
    card_bg = FancyBboxPatch((0.1, 0.1), 8.3, 1.8,
                             boxstyle="round,pad=0.05",
                             edgecolor=card_border_color,
                             facecolor=card_bg_color,
                             linewidth=2)
    ax.add_patch(card_bg)
    
    # 标题
    ax.text(0.3, 1.7, "Coding Statistics Overview",
           fontsize=13, fontweight='bold', color=title_color,
           ha='left', va='top')
    
    # 计算统计数据
    total_repos = github_stats.get('total_repos', 0) + gitea_stats.get('total_repos', 0)
    total_contributions = len(contributions)
    total_stars = github_stats.get('total_stars', 0) + gitea_stats.get('total_stars', 0)
    github_contributions = len([c for c in contributions if c['source'] == 'github'])
    gitea_contributions = len([c for c in contributions if c['source'] == 'gitea'])
    
    # 横向排列5个统计卡片
    stats_data = [
        ('Total\nRepositories', total_repos, '#58a6ff'),
        ('Total Contributions\n(in Last Year)', total_contributions, '#56d364'),
        ('GitHub Contributions\n(in Last Year)', github_contributions, '#c297ff'),
        ('Gitea Contributions\n(in Last Year)', gitea_contributions, '#76e3ea'),
        ('Total Stars', total_stars, '#f0883e'),
    ]
    
    # 计算每个卡片的位置
    card_width = 1.45
    card_spacing = 0.12
    start_x = 0.35
    y_center = 0.8
    
    for i, (label, value, color) in enumerate(stats_data):
        x_pos = start_x + i * (card_width + card_spacing)
        
        # 小卡片背景
        mini_card = FancyBboxPatch((x_pos, 0.25), card_width, 1,
                                   boxstyle="round,pad=0.03",
                                   edgecolor=mini_card_border,
                                   facecolor=mini_card_bg,
                                   linewidth=1.5)
        ax.add_patch(mini_card)
        
        # 数值
        ax.text(x_pos + card_width/2, y_center + 0.15, str(value),
               fontsize=24, fontweight='bold', color=color,
               ha='center', va='center')
        
        # 标签（支持换行）
        ax.text(x_pos + card_width/2, y_center - 0.35, label,
               fontsize=7.5, color=text_color,
               ha='center', va='center', linespacing=1.3)
    
    plt.savefig(os.path.join(config.FIGURES_DIR, output_file), format='svg', 
               bbox_inches='tight', facecolor=bg_color, edgecolor='none', pad_inches=0.1)
    plt.close()
    
    print(f"综合统计图已保存: {output_file}")
