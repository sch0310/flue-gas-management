#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时检查标气到期提醒
每天上午9:00自动运行
"""

import time
import requests
import json
from datetime import datetime

# 系统访问地址（本地）
BASE_URL = "http://127.0.0.1:5000"

def check_reminders():
    """调用系统的检查接口"""
    try:
        url = f"{BASE_URL}/check"
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始检查提醒...", flush=True)
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检查完成，状态码: {resp.status_code}", flush=True)
            # 尝试解析JSON响应
            try:
                result = resp.json()
                print(f"  检查结果: {json.dumps(result, ensure_ascii=False)}")
            except:
                # 如果不是JSON（可能是HTML页面），打印前200字符
                print(f"  响应内容: {resp.text[:200]}")
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检查失败，状态码: {resp.status_code}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检查出错: {e}")

def main():
    """主循环：每天9:00检查"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 定时检查服务启动")
    print(f"  将在每天上午 9:00 自动检查标气到期提醒")
    
    # 启动时先检查一次
    check_reminders()
    
    while True:
        now = datetime.now()
        # 检查是否到了9点
        if now.hour == 9 and now.minute == 0:
            check_reminders()
            # 等待61秒，避免同一分钟内重复执行
            time.sleep(61)
        else:
            # 每分钟检查一次时间
            time.sleep(60)

if __name__ == '__main__':
    main()
