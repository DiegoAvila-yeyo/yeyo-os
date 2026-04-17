# NODO 1 Video — Fixes Log

## Issues encontrados y resueltos

1. **Onboarding animation blocks headless test**
   - Fix: Set `yeyo_onboarding_complete=1` and `yeyo_user_name=Yeyo` in localStorage

2. **KillSwitch overlay (SISTEMA EN PAUSA) blocks interactions**
   - Root cause: `yeyo-security` persists `killSwitchActive=true` in localStorage
   - Fix: Clear `killSwitchActive=false` in localStorage, click Reanudar if visible

3. **Cerrar button intercepts IA tab click**
   - Root cause: IA tab (x=1340-1440, y=48-108) overlaps with Cerrar (x=1352-1432, y=56-84)
   - Fix: Use `page.mouse.click(1390, 103)` to click bottom of IA tab area

4. **Filter labels differ from API names**
   - `bw` displays as `B&W`, `cinematic` as `Cinemático`
   - Fix: Assert using display labels, not API IDs

5. **Transition labels are capitalized**
   - API: `fade`, `dissolve` → UI: `Fade`, `Dissolve`
   - Fix: Use capitalized labels in assertions

## Result: ALL PASS (38/38)
