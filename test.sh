#!/bin/bash
# 运行测试并将输出同时写入标准输出和日志文件
echo "Starting tests at $(date)"
cd /test
# curl -sSf https://astral.sh/uv/install.sh | sh 
alias uv=/root/.local/bin/uv
uv run test_redis.py 2>&1 | tee -a /logs/py-test-logs.log
tail -n 15 /tmp/full_output.log > /logs/py-test-logs.lo

wrk -t2 -c10 -d10s http://gateServer:8080 2>&1 | tee -a /logs/wrk-test-logs.log
tail -n 15 /tmp/full_wrk_output.log > /logs/wrk-test-logs.log

echo "Tests completed with status $EXIT_CODE at $(date)"
# 将退出状态码写入日志
echo "Exit code: $EXIT_CODE" >> /logs/test_output.log
# 使用实际的测试退出码作为容器的退出码
exit $EXIT_CODE