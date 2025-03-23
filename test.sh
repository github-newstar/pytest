#!/bin/bash
# 运行测试并将输出同时写入标准输出和日志文件
echo "Starting tests at $(date)"
cd /test
touch /logs/py-test-logs.log /logs/wrk-test-logs{1,2,3}.log
# curl -sSf https://astral.sh/uv/install.sh | sh 
/root/.local/bin/uv run net_test.py regular 2>&1 | tee -a /logs/py-test-logs.log
tail -n 15 /logs/py-test-logs.log > /logs/py-test-logs.log


wrk -t2 -c10 -d60s http://gateServer:8080 2>&1 | tee -a /logs/wrk-test-logs2.log
tail -n 15 /logs/wrk-test-logs2.log > /logs/wrk-test-logs2.log


wrk -t4 -c20 -d60s http://gateServer:8080 2>&1 | tee -a /logs/wrk-test-logs3.log
tail -n 15 /logs/wrk-test-logs3.log > /logs/wrk-test-logs3.log


wrk -t4 -c40 -d60s http://gateServer:8080 2>&1 | tee -a /logs/wrk-test-logs1.log
tail -n 15 /logs/wrk-test-logs1.log > /logs/wrk-test-logs1.log

echo "Tests completed with status $EXIT_CODE at $(date)"
# 将退出状态码写入日志
echo "Exit code: $EXIT_CODE" >> /logs/test_output.log
# 使用实际的测试退出码作为容器的退出码
exit $EXIT_CODE