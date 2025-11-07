"""
WakaTime API 数据获取模块
获取全时间段编程语言使用统计并进行智能处理
"""
import asyncio
import aiohttp
from typing import Dict, List
import config
from cache_manager import cache_manager


# 无意义的语言/内容列表（需要过滤）
MEANINGLESS_LANGUAGES = {
    'other', 'others', 'binary', 'textmate', 'text', 'plaintext',
    'json', 'yaml', 'yml', 'xml', 'toml', 'ini', 'conf', 'config',
    'markdown', 'md', 'txt', 'log', 'csv', 'tsv',
    'git commit message', 'git config', 'git rebase',
    'tex', 'latex', 'bibtex', 'xaml', 'gitignore', 'gitignore file', 'batchfile', 'batch', 'class',
    'git', 'pickle', 'self', 'sourcemap', 'ssh config', 'ssh_config',
    'diff', 'prolog', 'spi', 'postscript', 'asciidoc'
}

# CMake 归入 C++
CMAKE_LANGUAGES = {'cmake', 'cmakelist', 'cmakelists', 'makefile', 'make', 'ninja', 'microsoft visual studio solution', 'msvs'}

# Jupyter 归入 Python
JUPYTER_LANGUAGES = {'jupyter', 'jupyter notebook', 'ipynb', 'pythonstub', 'python stub'}

# Java Properties 归入 Java
JAVA_RELATED = {'java properties', 'properties', 'mixin_json_configuration', 'mixin json configuration', 'idea_module', 'idea module', 'access transformers'}

# Gradle 相关语言（用于计算真实比例）
GRADLE_TARGET_LANGUAGES = {'java', 'kotlin', 'groovy'}

# 前端开发语言合并为 "Frontend Langs"
FRONTEND_LANGUAGES = {'javascript', 'typescript', 'html', 'css', 'scss', 'sass', 'less', 'jsx', 'tsx', 'vue', 'vue.js', 'svelte', 'tsconfig', 'tsconfig.json'}

# Shell 脚本语言合并为 "Shell"
SHELL_LANGUAGES = {'bash', 'shell', 'shellscript', 'shell script', 'sh', 'zsh', 'nix', 'actionscript', 'powershell', 'pwsh', 'docker', 'dockerfile'}

# Shader 语言合并为 "Shader"
SHADER_LANGUAGES = {'glsl', 'hlsl', 'shaderlab', 'f#'}


async def get_wakatime_all_time_stats_async() -> Dict:
    """
    异步获取 WakaTime 全时间段统计数据
    
    Returns:
        处理后的语言统计数据
    """
    if not config.WAKATIME_API_KEY:
        print("WakaTime API Key 未设置，跳过")
        return {}
    
    # 检查缓存（缓存原始数据）
    cache_key = "wakatime_raw_all_time_data"
    cached_raw_data = cache_manager.get(cache_key)
    
    if cached_raw_data is not None:
        print("✓ 使用缓存的 WakaTime 原始数据")
        raw_languages = cached_raw_data['languages']
        total_seconds = cached_raw_data['total_seconds']
    else:
        try:
            # 获取全时间段统计数据
            url = f'{config.WAKATIME_API_URL}/users/current/all_time_since_today?api_key={config.WAKATIME_API_KEY}'
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
            
            # 获取语言详细统计（使用 all_time 范围）
            stats_url = f'{config.WAKATIME_API_URL}/users/current/stats/all_time?api_key={config.WAKATIME_API_KEY}'
            
            async with aiohttp.ClientSession() as session:
                async with session.get(stats_url) as response:
                    response.raise_for_status()
                    stats_data = await response.json()
            
            if 'data' not in stats_data:
                print("WakaTime 数据格式错误")
                return {}
            
            # 提取原始语言数据
            raw_languages = stats_data['data'].get('languages', [])
            total_seconds = stats_data['data'].get('total_seconds', 0)
            
            # 保存原始数据到缓存
            cache_manager.set(cache_key, {
                'languages': raw_languages,
                'total_seconds': total_seconds
            })
            
            print(f"\n📊 WakaTime 全时间段数据获取成功")
            
        except Exception as e:
            print(f"获取 WakaTime 数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    # 处理语言数据（每次都重新处理，确保逻辑变更生效）
    print(f"  原始语言数量: {len(raw_languages)}")
    processed_languages = process_language_data(raw_languages)
    
    result = {
        'languages': processed_languages,
        'total_seconds': total_seconds
    }
    
    print(f"  处理后语言数量: {len(processed_languages)}")
    print(f"  总编程时长: {total_seconds / 3600:.1f} 小时")
    
    return result


def process_language_data(raw_languages: List[Dict]) -> List[Dict]:
    """
    处理语言数据：过滤、归类、重新归一化
    
    Args:
        raw_languages: 原始语言数据列表
    
    Returns:
        处理后的语言数据列表
    """
    # 步骤 1: 创建语言字典（使用小写键名便于匹配）
    language_dict = {}
    cmake_seconds = 0
    gradle_seconds = 0
    
    # 第一遍：收集所有数据，计算 Gradle 目标语言的真实比例
    gradle_target_seconds = {}  # 记录 Java/Kotlin/Groovy 的时长
    
    for lang in raw_languages:
        name = lang['name']
        name_lower = name.lower()
        seconds = lang['total_seconds']
        
        # 记录 Gradle 目标语言的时长（用于计算比例）
        if name_lower in GRADLE_TARGET_LANGUAGES:
            gradle_target_seconds[name_lower] = seconds
    
    # 计算 Gradle 分配比例
    total_gradle_target = sum(gradle_target_seconds.values())
    gradle_distribution = {}
    
    if total_gradle_target > 0:
        for lang, seconds in gradle_target_seconds.items():
            gradle_distribution[lang] = seconds / total_gradle_target
            print(f"  Gradle 分配比例: {lang.capitalize()} = {gradle_distribution[lang]*100:.1f}%")
    else:
        # 如果没有 Java/Kotlin/Groovy 数据，使用默认比例
        print("  未检测到 Java/Kotlin/Groovy，使用默认 Gradle 分配比例")
        gradle_distribution = {'java': 1.0}  # 全部归入 Java
    
    # 第二遍：正式处理数据
    frontend_seconds = 0  # 收集 Frontend 开发相关语言的时长
    jupyter_seconds = 0  # 收集 Jupyter 相关的时长
    java_related_seconds = 0  # 收集 Java 相关文件的时长
    shell_seconds = 0  # 收集 Shell 脚本相关的时长
    shader_seconds = 0  # 收集 Shader 语言的时长
    
    for lang in raw_languages:
        name = lang['name']
        name_lower = name.lower()
        seconds = lang['total_seconds']
        
        # 过滤无意义内容
        if name_lower in MEANINGLESS_LANGUAGES:
            print(f"  过滤: {name} ({seconds / 3600:.2f}h)")
            continue
        
        # 步骤 2: CMake 归入 C++
        if name_lower in CMAKE_LANGUAGES:
            cmake_seconds += seconds
            print(f"  归类: {name} → C++ ({seconds / 3600:.2f}h)")
            continue
        
        # Jupyter 归入 Python
        if name_lower in JUPYTER_LANGUAGES:
            jupyter_seconds += seconds
            print(f"  归类: {name} → Python ({seconds / 3600:.2f}h)")
            continue
        
        # Java Properties 归入 Java
        if name_lower in JAVA_RELATED:
            java_related_seconds += seconds
            print(f"  归类: {name} → Java ({seconds / 3600:.2f}h)")
            continue
        
        # 识别 Gradle
        if name_lower in {'gradle', 'groovy gradle'}:
            gradle_seconds += seconds
            print(f"  分配: {name} → Java/Kotlin/Groovy ({seconds / 3600:.2f}h)")
            continue

        # 合并 Frontend 开发语言
        if name_lower in FRONTEND_LANGUAGES:
            frontend_seconds += seconds
            print(f"  合并: {name} → Frontend Development ({seconds / 3600:.2f}h)")
            continue
        
        # 合并 Shell 脚本语言
        if name_lower in SHELL_LANGUAGES:
            shell_seconds += seconds
            print(f"  合并: {name} → Shell ({seconds / 3600:.2f}h)")
            continue
        
        # 合并 Shader 语言
        if name_lower in SHADER_LANGUAGES:
            shader_seconds += seconds
            print(f"  合并: {name} → Shader ({seconds / 3600:.2f}h)")
            continue
        
        # 合并 Objective-C 的不同命名
        if name_lower in {'objective-c', 'objectivec', 'objective c', 'objc'}:
            if 'objective-c' not in language_dict:
                language_dict['objective-c'] = {'name': 'Objective-C', 'total_seconds': 0}
            language_dict['objective-c']['total_seconds'] += seconds
            print(f"  合并: {name} → Objective-C ({seconds / 3600:.2f}h)")
            continue
        
        # 合并 C/C++ 的不同命名
        if name_lower in {'c/c++', 'c/c', 'c++/c'}:
            if 'c' not in language_dict:
                language_dict['c'] = {'name': 'C', 'total_seconds': 0}
            language_dict['c']['total_seconds'] += seconds
            print(f"  合并: {name} → C ({seconds / 3600:.2f}h)")
            continue
        
        # 添加到字典
        if name_lower not in language_dict:
            language_dict[name_lower] = {
                'name': name,  # 保留原始大小写
                'total_seconds': 0
            }
        language_dict[name_lower]['total_seconds'] += seconds
    
    # 将 CMake 时长归入 C++
    if cmake_seconds > 0:
        cpp_key = 'c++'
        if cpp_key not in language_dict:
            language_dict[cpp_key] = {'name': 'C++', 'total_seconds': 0}
        language_dict[cpp_key]['total_seconds'] += cmake_seconds
        print(f"  ✓ CMake 总计归入 C++: {cmake_seconds / 3600:.2f}h")
    
    # 将 Jupyter 时长归入 Python
    if jupyter_seconds > 0:
        python_key = 'python'
        if python_key not in language_dict:
            language_dict[python_key] = {'name': 'Python', 'total_seconds': 0}
        language_dict[python_key]['total_seconds'] += jupyter_seconds
        print(f"  ✓ Jupyter 总计归入 Python: {jupyter_seconds / 3600:.2f}h")
    
    # 将 Java Properties 时长归入 Java
    if java_related_seconds > 0:
        java_key = 'java'
        if java_key not in language_dict:
            language_dict[java_key] = {'name': 'Java', 'total_seconds': 0}
        language_dict[java_key]['total_seconds'] += java_related_seconds
        print(f"  ✓ Java Properties 总计归入 Java: {java_related_seconds / 3600:.2f}h")

    # 添加 Frontend 汇总
    if frontend_seconds > 0:
        frontend_key = 'frontend'
        language_dict[frontend_key] = {'name': 'Frontend Langs', 'total_seconds': frontend_seconds}
        print(f"  ✓ Frontend 开发总计: {frontend_seconds / 3600:.2f}h")

    # 添加 Shell 汇总
    if shell_seconds > 0:
        shell_key = 'shell'
        language_dict[shell_key] = {'name': 'Shell Langs', 'total_seconds': shell_seconds}
        print(f"  ✓ Shell 脚本总计: {shell_seconds / 3600:.2f}h")
    
    # 添加 Shader 汇总
    if shader_seconds > 0:
        shader_key = 'shader'
        language_dict[shader_key] = {'name': 'Shader Langs', 'total_seconds': shader_seconds}
        print(f"  ✓ Shader 语言总计: {shader_seconds / 3600:.2f}h")
    
    # 步骤 3: 将 Gradle 按真实比例分配
    if gradle_seconds > 0:
        for lang_key, ratio in gradle_distribution.items():
            if lang_key not in language_dict:
                # 如果目标语言不存在，创建它
                display_name = lang_key.capitalize()
                language_dict[lang_key] = {'name': display_name, 'total_seconds': 0}
            
            distributed_seconds = gradle_seconds * ratio
            language_dict[lang_key]['total_seconds'] += distributed_seconds
            print(f"  ✓ Gradle → {language_dict[lang_key]['name']}: {distributed_seconds / 3600:.2f}h ({ratio*100:.1f}%)")
    
    # 步骤 4: 重新计算总时长和百分比
    total_seconds = sum(lang['total_seconds'] for lang in language_dict.values())
    
    # 转换为列表并计算百分比
    processed_languages = []
    for lang_data in language_dict.values():
        percent = (lang_data['total_seconds'] / total_seconds * 100) if total_seconds > 0 else 0
        processed_languages.append({
            'name': lang_data['name'],
            'total_seconds': lang_data['total_seconds'],
            'percent': percent
        })
    
    # 按时长排序
    processed_languages.sort(key=lambda x: x['total_seconds'], reverse=True)
    
    return processed_languages


def get_wakatime_all_time_stats() -> Dict:
    """
    获取 WakaTime 全时间段统计数据（同步包装器）
    """
    return asyncio.run(get_wakatime_all_time_stats_async())
