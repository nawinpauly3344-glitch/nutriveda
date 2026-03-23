@echo off
title MHB Nutrition - Build RAG Knowledge Base
echo ============================================
echo   MHB Nutrition - RAG Knowledge Base Builder
echo ============================================
echo.
echo This will read all 33 PDF/PPT files from:
echo C:\Users\Deepu\Documents\MHB Files\MHB
echo.
echo It creates a searchable vector index using OpenAI embeddings.
echo Cost: approximately $0.05 (one-time, already done if you see vector_store folder)
echo.
echo IMPORTANT: Make sure your OPENAI_API_KEY is in the .env file!
echo.
pause

cd /d "%~dp0backend"
set PATH=%APPDATA%\Python\Python314\Scripts;%PATH%

python -c "import sys; sys.path.insert(0,'.');  from rag.ingest import run_ingestion; run_ingestion()"

echo.
if errorlevel 1 (
    echo ERROR: Ingestion failed. Check your OPENAI_API_KEY in .env
) else (
    echo SUCCESS: RAG knowledge base is ready!
    echo You can now start the backend with start_backend.bat
)
pause
