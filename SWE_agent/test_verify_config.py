#!/usr/bin/env python3
"""
验证run_batch.sh配置是否正确的脚本
"""
import os
import sys
from pathlib import Path

def verify_config():
    """验证配置参数"""
    print("🔍 验证 run_batch.sh 配置...")
    print("=" * 50)
    
    # 从run_batch.sh中读取配置
    config = {}
    try:
        with open('run_batch.sh', 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if line.startswith('MODEL_NAME='):
                value = line.split('=', 1)[1].split('#')[0].strip()
                config['MODEL_NAME'] = value.strip('"').strip("'")
            elif line.startswith('OUTPUT_BASE_DIR='):
                value = line.split('=', 1)[1].split('#')[0].strip()
                config['OUTPUT_BASE_DIR'] = value.strip('"').strip("'")
            elif line.startswith('USER_NAME='):
                value = line.split('=', 1)[1].split('#')[0].strip()
                config['USER_NAME'] = value.strip('"').strip("'")
            elif line.startswith('PROMPT_DIR='):
                value = line.split('=', 1)[1].split('#')[0].strip()
                config['PROMPT_DIR'] = value.strip('"').strip("'")
                
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return False
    
    print("📋 当前配置:")
    for key, value in config.items():
        print(f"   {key}: {value}")
    print()
    
    # 验证关键路径
    checks = []
    
    # 检查轨迹文件目录
    if 'OUTPUT_BASE_DIR' in config:
        traj_dir = config['OUTPUT_BASE_DIR']
        if os.path.exists(traj_dir):
            checks.append(("✅", f"轨迹文件目录存在: {traj_dir}"))
            
            # 检查是否有轨迹文件
            traj_count = 0
            for root, dirs, files in os.walk(traj_dir):
                traj_count += len([f for f in files if f.endswith('.traj')])
            
            if traj_count > 0:
                checks.append(("✅", f"找到 {traj_count} 个轨迹文件"))
            else:
                checks.append(("⚠️", "未找到轨迹文件"))
        else:
            checks.append(("❌", f"轨迹文件目录不存在: {traj_dir}"))
    
    # 检查提示文件目录
    if 'PROMPT_DIR' in config:
        prompt_dir = config['PROMPT_DIR']
        if os.path.exists(prompt_dir):
            checks.append(("✅", f"提示文件目录存在: {prompt_dir}"))
            
            # 检查是否有.md文件
            md_files = [f for f in os.listdir(prompt_dir) if f.endswith('.md')]
            if md_files:
                checks.append(("✅", f"找到 {len(md_files)} 个提示文件"))
            else:
                checks.append(("⚠️", "未找到.md提示文件"))
        else:
            checks.append(("❌", f"提示文件目录不存在: {prompt_dir}"))
    
    # 检查批处理脚本
    if os.path.exists('batch_sweagent_run.py'):
        checks.append(("✅", "批处理脚本存在"))
    else:
        checks.append(("❌", "批处理脚本不存在"))
    
    print("🔍 验证结果:")
    for status, message in checks:
        print(f"   {status} {message}")
    
    # 总结
    error_count = len([c for c in checks if c[0] == "❌"])
    warning_count = len([c for c in checks if c[0] == "⚠️"])
    
    print()
    if error_count == 0:
        if warning_count == 0:
            print("🎉 配置验证通过！可以运行批处理脚本。")
        else:
            print(f"⚠️ 配置基本正确，但有 {warning_count} 个警告。")
        print("💡 建议先运行测试:")
        print("   python3 test_trajectory_parser.py")
        return True
    else:
        print(f"❌ 配置有 {error_count} 个错误，请修复后再运行。")
        return False

if __name__ == "__main__":
    verify_config() 