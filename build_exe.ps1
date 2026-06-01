# 打包 run_check.py 为单文件 exe（满足"调用 exe 程序"要求）。
# 用法： powershell -ExecutionPolicy Bypass -File build_exe.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# 1. 确保 pyinstaller 已安装
python -c "import PyInstaller" 2>$null
if (-not $?) { python -m pip install pyinstaller }

# 2. 打包（--paths checker 让 PyInstaller 找到 plugins 包，并显式带上各检查器模块）
python -m PyInstaller --onefile --name run_check --paths checker `
  --distpath dist --workpath build\work --specpath build `
  --hidden-import plugins `
  --hidden-import plugins.cppcheck_checker `
  --hidden-import plugins.custom_regex_checker `
  checker\run_check.py

# 3. 把配置复制到 exe 同目录，使 exe 可独立运行（config 自动定位顺序见 run_check.py）
Copy-Item checker\config.json, checker\config.misra.json dist\ -Force

Write-Host "完成：dist\run_check.exe"
& .\dist\run_check.exe --list-checkers
