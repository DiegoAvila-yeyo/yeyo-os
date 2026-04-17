# NODO 3 Laboratorio — Fixes Log

## Notes

1. **Lab clip generate endpoint uses integer index, not UUID**
   - Endpoint: POST /api/v1/lab/projects/{id}/clips/{frame_idx}/generate
   - `frame_idx` is an int (0-5), not the clip UUID
   - Worked correctly once using integer index

2. **Pause/Resume behavior**
   - When project is already completed, pause returns "No active generation to pause" (correct)
   - When project is paused but we call resume too quickly, returns 409 Conflict (expected)
   - Pause during active generation returns `{"status": "pausing"}` correctly

## Result: ALL PASS (8/8)
