@echo off
setlocal EnableExtensions
rem Ensure Ed25519 identity dependency for the same python used to run app_v2.py
python -c "import nacl" >nul 2>&1
if not errorlevel 1 exit /b 0
echo [CNexus] PyNaCl not found for: 
python -c "import sys; print(sys.executable)"
echo [CNexus] Installing PyNaCl ...
python -m pip install "pynacl>=1.5.0"
if errorlevel 1 (
    echo [ERROR] pip install pynacl failed. Try: python -m pip install pynacl
    exit /b 1
)
python -c "import nacl" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyNaCl still not importable after install.
    exit /b 1
)
exit /b 0
