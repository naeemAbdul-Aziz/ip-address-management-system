# start-dev.ps1

Write-Host "Starting IPAM System (Local Dev)..." -ForegroundColor Cyan

# 1. Start Backend (New Window)
Write-Host "Launching Backend (FastAPI)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

# 2. Frontend Instructions
Write-Host "--------------------------------------------------------" -ForegroundColor Yellow
Write-Host "BACKEND LAUNCHED." -ForegroundColor Green
Write-Host "FOR FRONTEND via 'npm':" -ForegroundColor Yellow
Write-Host "1. Open a new terminal."
Write-Host "2. cd frontend"
Write-Host "3. npm run dev"
Write-Host "--------------------------------------------------------" -ForegroundColor Yellow
