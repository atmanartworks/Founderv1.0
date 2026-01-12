# How to Start FounderGPT Servers

## Quick Start

### Backend (FastAPI)
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Next.js)
```bash
cd frontend
npm run dev
```

## Access URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/v1/docs
- **Health Check**: http://localhost:8000/health

## Background Process (Optional)

### Backend
```bash
cd backend
source venv/bin/activate
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
```

### Frontend
```bash
cd frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
```

## Check Status

```bash
# Check if servers are running
curl http://localhost:8000/health  # Backend
curl http://localhost:3000         # Frontend

# View logs
tail -f /tmp/backend.log
tail -f /tmp/frontend.log
```

## Stop Servers

```bash
# Stop backend
pkill -f "uvicorn app.main:app"

# Stop frontend
pkill -f "next dev"
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
lsof -ti:8000 | xargs kill -9

# Find process using port 3000
lsof -ti:3000 | xargs kill -9
```

### Backend Not Starting
1. Check `.env` file exists and has required keys
2. Verify virtual environment is activated
3. Check logs: `tail -f /tmp/backend.log`

### Frontend Not Starting
1. Check `node_modules` installed: `npm install`
2. Check `.env.local` exists (if needed)
3. Check logs: `tail -f /tmp/frontend.log`

---

**Status**: ✅ Servers Running
**Last Updated**: 2024-12-XX

