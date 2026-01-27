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

REM Check if Docker is installed
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Docker not found. Please install Docker first.
    pause
    exit /b 1
)

echo Using uv package manager...

REM Check if Qdrant container is running
echo Checking Qdrant connection...
docker ps --filter "name=qdrant" --filter "status=running" -q > nul 2>&1
for /f %%i in ('docker ps --filter "name=qdrant" --filter "status=running" -q') do set QDRANT_RUNNING=%%i

if not defined QDRANT_RUNNING (
    echo Qdrant is not running. Starting Qdrant container...
    
    REM Check if container exists but is stopped
    for /f %%i in ('docker ps -a --filter "name=qdrant" -q') do set QDRANT_EXISTS=%%i
    
    if defined QDRANT_EXISTS (
        echo Restarting existing Qdrant container...
        docker start qdrant
    ) else (
        echo Creating new Qdrant container...
        docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v "%cd%\qdrant_data:/qdrant/storage" qdrant/qdrant
    )
    
    echo Waiting for Qdrant to start...
    timeout /t 3 /nobreak > nul
    echo Qdrant should now be running on port 6333
) else (
    echo Qdrant is already running
)

echo.
echo Starting Streamlit Interface...
echo Access at: http://localhost:8501
echo Qdrant Dashboard: http://localhost:6333/dashboard
echo.

uv run streamlit run app\streamlit_app.py

pause
