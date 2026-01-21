@echo off
REM Sentinel RAG Streamlit Launcher for Windows

echo ================================
echo Sentinel RAG Interface
echo ================================
echo.

REM Change to project root (parent of app folder)
cd ..

REM Check if .env file exists
if not exist ".env" (
    echo Warning: .env file not found!
    echo Creating from .env.example...
    copy .env.example .env
    echo Please update .env with your configuration
    echo.
)

REM Check if uv is installed
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: uv not found. Please install uv first:
    echo https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

echo Using uv package manager...
echo Starting Streamlit Interface...
echo Access at: http://localhost:8501
echo.

uv run streamlit run app\streamlit_app.py

pause
