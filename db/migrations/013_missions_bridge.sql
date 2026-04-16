-- Phase 6: Observatory ↔ Workshop Bridge
-- Extends workshop_missions with observatory context columns

ALTER TABLE workshop_missions ADD COLUMN IF NOT EXISTS finding TEXT DEFAULT '';
ALTER TABLE workshop_missions ADD COLUMN IF NOT EXISTS analysis TEXT DEFAULT '';
ALTER TABLE workshop_missions ADD COLUMN IF NOT EXISTS strategy TEXT DEFAULT '';
ALTER TABLE workshop_missions ADD COLUMN IF NOT EXISTS observatory_task_id UUID;
ALTER TABLE workshop_missions ADD COLUMN IF NOT EXISTS created_by VARCHAR(50) DEFAULT 'user';

CREATE INDEX IF NOT EXISTS idx_missions_origin ON workshop_missions(origin);
CREATE INDEX IF NOT EXISTS idx_missions_observatory ON workshop_missions(observatory_task_id);
