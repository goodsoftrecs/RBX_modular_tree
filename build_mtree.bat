@echo off
setlocal
cd /d "%~dp0"

REM Use the existing uv-managed CPython that this project was configured with.
REM Do not invoke `py -3.11`: the Windows launcher does not discover uv runtimes.
set "PY311_ROOT=%APPDATA%\uv\python\cpython-3.11-windows-x86_64-none"
set "PY311=%PY311_ROOT%\python.exe"

if not exist "%PY311%" (
    echo ERROR: Existing uv-managed Python 3.11 was not found:
    echo        %PY311%
    echo This offline build will not download or install another Python runtime.
    exit /b 1
)

"%PY311%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)"
if errorlevel 1 (
    echo ERROR: %PY311% is not Python 3.11.
    exit /b 1
)

REM Fail closed if vendored/cached native dependencies are unavailable.
if not exist "m_tree\dependencies\pybind11\CMakeLists.txt" (
    echo ERROR: Vendored pybind11 is missing. Refusing to download dependencies.
    exit /b 1
)
if not exist "m_tree\dependencies\vcpkg\installed\x64-windows\share\eigen3\Eigen3Config.cmake" (
    echo ERROR: Cached Eigen3 is missing. Refusing to download dependencies.
    exit /b 1
)
where cmake >nul 2>nul
if errorlevel 1 (
    echo ERROR: CMake is not available on PATH.
    exit /b 1
)

REM Configure and build using only the existing local toolchain and dependencies.
cmake -S m_tree -B m_tree\build "-DPython_EXECUTABLE=%PY311%" "-DPython_ROOT_DIR=%PY311_ROOT%" "-DVCPKG_TARGET_TRIPLET=x64-windows"
if errorlevel 1 exit /b %errorlevel%

cmake --build m_tree\build --config Release
if errorlevel 1 exit /b %errorlevel%

REM Copy .pyd for direct import (development convenience)
copy /y ".\m_tree\binaries\Release\m_tree.cp311-win_amd64.pyd" ".\m_tree.cp311-win_amd64.pyd" >nul
if errorlevel 1 exit /b %errorlevel%

REM Build the wheel using only Python's standard library. No pip or package index.
"%PY311%" .github\scripts\package_native_wheel.py
if errorlevel 1 exit /b %errorlevel%

REM Package addon for Blender
"%PY311%" .github\scripts\setup_addon.py
if errorlevel 1 exit /b %errorlevel%

echo Addon ready: tmp\rbx_modular_tree_*.zip
PAUSE
