@echo off
title MHB Nutrition - Rebuild RAG (Force)
echo ============================================
echo   Rebuilding RAG Knowledge Base (Force)
echo ============================================
echo This will DELETE the existing vector store and rebuild from scratch.
echo Cost: ~$0.05 in OpenAI API charges.
pause

cd /d "%~dp0backend"
set PATH=%APPDATA%\Python\Python314\Scripts;%PATH%
python -c "import sys; sys.path.insert(0,'.'); from rag.ingest import run_ingestion; run_ingestion(force_rebuild=True)"
pause
