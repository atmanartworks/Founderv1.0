# Network Access Setup Guide

To access the application from another device on your local network:

## Your Network IP
**Your local IP address: `192.168.3.3`**

## Step 1: Start Backend (on your machine)

The backend must bind to all network interfaces (0.0.0.0) to be accessible from other devices:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or if you're using a different command:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Important:** Use `--host 0.0.0.0` (not `localhost` or `127.0.0.1`) so it's accessible from other devices.

## Step 2: Start Frontend (on your machine)

The frontend needs to be accessible on the network. Run:

```bash
cd frontend
npm run dev -- -H 0.0.0.0
```

Or if using Next.js directly:
```bash
next dev -H 0.0.0.0
```

**Note:** By default, Next.js only binds to localhost. The `-H 0.0.0.0` flag makes it accessible on your network.

## Step 3: Access from Another Device

On the other device (phone, tablet, another computer), open a browser and go to:

```
http://192.168.3.3:3000
```

## Troubleshooting

### If you can't access the frontend:
1. Make sure both devices are on the same Wi-Fi network
2. Check your firewall settings - you may need to allow port 3000
3. Verify your IP address hasn't changed: run `ifconfig | grep "inet " | grep -v 127.0.0.1`

### If you get CORS errors:
1. The backend CORS is configured to allow `http://192.168.3.3:3000`
2. If your IP is different, update `backend/app/main.py` to add your IP to the `origins` list
3. Or temporarily allow all origins in development (see comment in `main.py`)

### If the API doesn't work:
1. The frontend automatically detects if it's on localhost or network IP
2. If accessing from `192.168.3.3:3000`, it will use `http://192.168.3.3:8000/api/v1` for API calls
3. Make sure the backend is running with `--host 0.0.0.0`

## Quick Reference

**On your machine (backend):**
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**On your machine (frontend):**
```bash
cd frontend
npm run dev -- -H 0.0.0.0
```

**On another device:**
```
http://192.168.3.3:3000
```

## Security Note

⚠️ **This setup is for local network development only!** 
- Don't expose this to the internet
- The CORS configuration allows network access for convenience
- For production, use proper domain names and HTTPS

