#!/usr/bin/env python3
"""
Script to verify if run_batch.sh configuration is correct
"""
import os
import sys
from pathlib import Path

def verify_config():
    """Verify configuration parameters"""
    print("🔍 Verifying run_batch.sh configuration...")
    print("=" * 50)

    # Read configuration from run_batch.sh
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
        print(f"❌ Failed to read config file: {e}")
        return False

    print("📋 Current configuration:")
    for key, value in config.items():
        print(f"   {key}: {value}")
    print()

    # Verify critical paths
    checks = []

    # Check trajectory file directory
    if 'OUTPUT_BASE_DIR' in config:
        traj_dir = config['OUTPUT_BASE_DIR']
        if os.path.exists(traj_dir):
            checks.append(("✅", f"Trajectory directory exists: {traj_dir}"))

            # Check for trajectory files
            traj_count = 0
            for root, dirs, files in os.walk(traj_dir):
                traj_count += len([f for f in files if f.endswith('.traj')])

            if traj_count > 0:
                checks.append(("✅", f"Found {traj_count} trajectory files"))
            else:
                checks.append(("⚠️", "No trajectory files found"))
        else:
            checks.append(("❌", f"Trajectory directory does not exist: {traj_dir}"))

    # Check prompt file directory
    if 'PROMPT_DIR' in config:
        prompt_dir = config['PROMPT_DIR']
        if os.path.exists(prompt_dir):
            checks.append(("✅", f"Prompt directory exists: {prompt_dir}"))

            # Check for .md files
            md_files = [f for f in os.listdir(prompt_dir) if f.endswith('.md')]
            if md_files:
                checks.append(("✅", f"Found {len(md_files)} prompt files"))
            else:
                checks.append(("⚠️", "No .md prompt files found"))
        else:
            checks.append(("❌", f"Prompt directory does not exist: {prompt_dir}"))

    # Check batch script
    if os.path.exists('batch_sweagent_run.py'):
        checks.append(("✅", "Batch script exists"))
    else:
        checks.append(("❌", "Batch script does not exist"))

    print("🔍 Verification results:")
    for status, message in checks:
        print(f"   {status} {message}")

    # Summary
    error_count = len([c for c in checks if c[0] == "❌"])
    warning_count = len([c for c in checks if c[0] == "⚠️"])

    print()
    if error_count == 0:
        if warning_count == 0:
            print("🎉 Configuration verified successfully! Ready to run batch script.")
        else:
            print(f"⚠️ Configuration is mostly correct, but has {warning_count} warnings.")
        print("💡 Recommended to run test first:")
        print("   python3 test_trajectory_parser.py")
        return True
    else:
        print(f"❌ Configuration has {error_count} errors, please fix before running.")
        return False

if __name__ == "__main__":
    verify_config()