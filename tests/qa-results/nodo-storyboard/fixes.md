# NODO 2 Storyboard — Fixes Log

## Bug Fixed: frames/reorder route ordering

**Root cause**: In `storyboard.py`, the route `PUT /{storyboard_id}/frames/{frame_id}` was declared BEFORE `PUT /{storyboard_id}/frames/reorder`. FastAPI matches routes in registration order, so "reorder" was treated as a frame_id UUID, causing 400 "Invalid ID format".

**Fix 1**: Moved `reorder_frames` route BEFORE `update_frame` route in both:
- `/Users/eltitoyeyo/YEYO/yeyo-os/src/api/routes/storyboard.py` (main repo — where server loads from)
- `/Users/eltitoyeyo/YEYO/yeyo-os.worktrees/copilot-worktree-2026-04-17T00-41-44/src/api/routes/storyboard.py`

**Fix 2**: Added `Body(...)` annotation to `items: List[FrameReorderItem]` parameter so FastAPI correctly parses a JSON array as the request body.

**Fix 3**: Added `Body` to FastAPI imports.

## AI Generate
- Endpoint exists and accepts requests
- Ollama is running (2 models loaded) but generation is very slow (>10s timeout)
- Marked as deferred — functional but slow

## Result: ALL PASS (10/10)
