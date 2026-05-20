#!/bin/bash
# 手动触发标气到期检查
# 用法: ./test_check.sh

echo "=== 手动触发标气到期检查 ==="
echo "时间: $(date)"
echo ""

# 调用检查接口
echo "正在调用检查接口..."
resp=$(curl -s http://127.0.0.1:5000/check)
echo "响应状态码: $?"

# 显示响应内容（前500字符）
echo ""
echo "响应内容:"
echo "$resp" | head -c 500
echo ""
echo ""
echo "=== 检查完成 ==="
