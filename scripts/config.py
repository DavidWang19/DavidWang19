"""
配置文件管理模块
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# GitHub 配置
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_USERNAME = 'DavidWang19'
GITHUB_API_URL = 'https://api.github.com'

# Gitea 配置
GITEA_URL = os.getenv('GITEA_URL')
GITEA_TOKEN = os.getenv('GITEA_TOKEN')
GITEA_USERNAME = os.getenv('GITEA_USERNAME')
GITEA_CERT = os.getenv('GITEA_CERT')  # SSL 证书路径

# WakaTime 配置
WAKATIME_API_KEY = os.getenv('WAKATIME_API_KEY')
WAKATIME_API_URL = 'https://wakatime.com/api/v1'

# 图表输出配置
# 获取项目根目录（scripts 的父目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGURES_DIR = os.path.join(PROJECT_ROOT, 'figures')
DPI = 300
FIGSIZE = (12, 6)
