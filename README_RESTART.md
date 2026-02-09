# Starlink Flight Analysis - Server Management

## 🚨 CRITICAL: Always Use Restart Script

**NEVER manually start servers. ALWAYS use the restart script.**

```bash
./restart.sh
```

## Why Use the Restart Script?

The restart script handles:
1. ✅ Kills all existing processes (Flask, Vite, node)
2. ✅ Clears Redis cache (FLUSHALL)
3. ✅ Clears Python cache (__pycache__)
4. ✅ Starts Flask server on port 5002
5. ✅ Starts Vite dev server on port 5173 (strict port)
6. ✅ Verifies all services started successfully

## Port Assignments

| Service | Port | URL |
|---------|------|-----|
| Frontend (Vite) | 5173 | http://localhost:5173 |
| Backend (Flask) | 5002 | http://localhost:5002 |
| Redis | 6379 | N/A |

## Common Issues

### "Port already in use"
**Solution**: The restart script handles this. If you see this error, run:
```bash
./restart.sh
```

### "Vite started on wrong port (5020, 5021, etc.)"
**Solution**: Kill all node processes and restart:
```bash
pkill -9 node
./restart.sh
```

### "Flask not responding"
**Solution**: Check Flask logs:
```bash
tail -f analysis/flask.log
```

### "Frontend shows old cached data"
**Solution**: The restart script clears Redis cache. If needed, manually clear:
```bash
redis-cli FLUSHALL
./restart.sh
```

## Logs

- **Flask**: `tail -f /Users/dykim/dev/starlink/analysis/flask.log`
- **Vite**: `tail -f /tmp/vite.log`

## DO NOT DO

❌ `cd frontend && npm run dev`
❌ `cd analysis && python3 app.py`
❌ Manually start servers
❌ Use alternative ports (5020, 5021, etc.)

## ALWAYS DO

✅ `./restart.sh`
✅ Check logs if errors occur
✅ Use correct ports (5173, 5002)
