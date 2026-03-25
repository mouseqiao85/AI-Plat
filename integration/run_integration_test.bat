@echo off
setlocal

REM 设置API密钥环境变量
set WENXIN_API_KEY=bce-v3/ALTAK-nIMprNDvrn57vPHwiHTJP/333cd1e75646ed043529e4245c89d5d776182aa4

REM 运行集成测试
echo Running integration test...
python integration_test.py

pause