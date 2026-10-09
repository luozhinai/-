@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set WEBUI_AUTO_BUILD=false
if not exist ".venv\Scripts\python.exe" (
  echo 尚未安装本仓库的 Python 环境。请先安装依赖，然后再启动网页版。
  pause
  exit /b 1
)
echo 网页地址：http://127.0.0.1:8000
echo 请保持此窗口打开，关闭窗口会停止网页服务。
".venv\Scripts\python.exe" main.py --webui-only --host 127.0.0.1 --port 8000
pause
