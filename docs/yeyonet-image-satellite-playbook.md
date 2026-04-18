# YeyoNet — playbook para prueba real de imagen entre dos PCs

Este documento separa exactamente lo que debe hacer la **PC Satélite** y lo que debe hacer la **PC Central** para validar que `image_generate` corre de verdad en la otra máquina.

## Objetivo

Probar este flujo completo:

1. La PC Satélite corre el backend actualizado.
2. La PC Satélite conecta YeyoNet hacia la Central.
3. La PC Satélite confirma que su backend local de imagen funciona con su GPU.
4. La PC Central crea un job `image_generate`.
5. El job queda `assigned_to` la Satélite.
6. El resultado vuelve con `result.image_b64`.
7. La PC Central guarda la imagen resultante y la abre.

---

## Reparto de responsabilidades

### PC Central

- Mantener el backend principal en `:8000`
- Ver el estado de YeyoNet (`/identity`, `/satellites`, `/jobs/{id}`)
- Lanzar el job distribuido
- Guardar la imagen resultante

### PC Satélite

- Hacer `git pull`
- Reiniciar su backend para tomar el nuevo código
- Confirmar que el backend local de imagen funciona
- Dejar YeyoNet conectado a la Central
- Mantener internet en la primera generación para descargar el modelo si todavía no está cacheado

---

## Lo que debe hacer la PC Satélite

### 1. Traer el cambio nuevo

```bash
git pull origin main
```

### 2. Reiniciar el backend de la Satélite

Usa **el mismo comando con el que ya dejas la Satélite funcionando hoy**.  
Lo importante es que el backend vuelva a levantar con el código nuevo.

Si lo corres manualmente con el patrón del repo:

```bash
/Users/eltitoyeyo/YEYO/yeyo-os.worktrees/copilot-worktree-2026-04-05T05-46-52/.venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Si en esa máquina ya usabas variables de entorno para arrancar, **usa exactamente las mismas de siempre**.

### 3. Confirmar que el backend de imagen local responde

Abrir:

```text
http://localhost:8000/api/v1/media/image/status
```

Debe responder algo como:

```json
{
  "loaded": false,
  "device": "cuda",
  "model": "runwayml/stable-diffusion-v1-5"
}
```

#### Señal buena

- `device: "cuda"` en una PC con NVIDIA
- `device: "mps"` en Apple Silicon
- `loaded` puede ser `false` antes de la primera generación

#### Señal mala

- `device: "cpu"` cuando esperabas GPU
- error `500`
- endpoint no responde

Si sale `cpu`, la generación puede seguir siendo real, pero **ya no prueba que la GPU de la Satélite esté trabajando**.

### 4. Hacer una prueba local de imagen en la Satélite

Esto aísla el backend de imagen antes de meter a YeyoNet en medio.

```bash
curl -s -X POST http://localhost:8000/api/v1/media/image/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "a small industrial robot standing on a white table, studio lighting, detailed",
    "negative_prompt": "blurry, low quality, text, watermark",
    "steps": 10,
    "guidance_scale": 7.5,
    "width": 512,
    "height": 512,
    "seed": 42
  }' > /tmp/yeyonet-local-image.json
```

#### Qué debe pasar

- la primera vez puede tardar bastante porque descarga el modelo
- debe terminar con JSON que incluya:
  - `"success": true`
  - `"image_b64": "data:image/png;base64,..."`
  - `"device": "cuda"` o `"mps"`

#### Qué significa si falla

- si falla aquí, **todavía no es problema de YeyoNet**
- es problema del backend local de imagen, modelo, torch o GPU

### 5. Confirmar que YeyoNet sigue conectado

En la Satélite, revisa el UI o el endpoint local de conexión que ya usas.

En la Central, debe verse el satélite en:

```text
http://localhost:8000/api/v1/yeyonet/satellites
```

Con:

- `status: "online"`
- `ram_free_gb > 0`
- `gpu_name` real

Si no se reconecta solo después del reinicio, entra a la UI de YeyoNet en la Satélite y vuelve a presionar **Conectar**.

---

## Lo que debe hacer la PC Central

### 1. Confirmar que esta máquina sigue siendo la Central

Abrir:

```text
http://localhost:8000/api/v1/yeyonet/identity
```

Debe verse:

- `role: "central"`
- `status: "online"`

### 2. Confirmar que la Satélite aparece con recursos reales

Abrir:

```text
http://localhost:8000/api/v1/yeyonet/satellites
```

Debe verse el satélite con:

- `status: "online"`
- `ram_free_gb > 0`
- `gpu_name != null`

### 3. Lanzar el job distribuido de imagen

```bash
curl -s -X POST http://localhost:8000/api/v1/yeyonet/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "image_generate",
    "payload": {
      "prompt": "a retro futuristic robot walking through a neon alley, cinematic, highly detailed",
      "negative_prompt": "blurry, low quality, text, watermark, deformed",
      "steps": 10,
      "guidance_scale": 7.5,
      "width": 512,
      "height": 512,
      "seed": 42
    }
  }'
```

Guarda el `job_id` de la respuesta.

### 4. Monitorear el job

Abrir:

```text
http://localhost:8000/api/v1/yeyonet/jobs/<JOB_ID>
```

#### Señal buena

- `status` pasa por `queued -> assigned -> completed`
- `assigned_to` es el `id` del satélite
- `result.status == "generated"`
- `result.image_b64` existe

#### Señal mala

- se queda en `queued`
- `assigned_to` sigue en `null`
- `status == failed`
- `result.status == placeholder_generated`
- `result.image_b64` no existe

### 5. Guardar la imagen resultante en la Central

Reemplaza `JOB_ID` por el real:

```bash
python3 - <<'PY'
import base64
import json
import urllib.request
from pathlib import Path

job_id = "JOB_ID"
url = f"http://localhost:8000/api/v1/yeyonet/jobs/{job_id}"
data = json.load(urllib.request.urlopen(url))
img = data["result"]["image_b64"].split(",", 1)[1]
output = Path("tests/qa-results/yeyonet/distributed-image-smoke.png")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(base64.b64decode(img))
print(output)
PY
```

Si ese archivo se guarda y se abre bien, la prueba quedó cerrada.

---

## Qué demuestra esta prueba

Si pasa todo lo anterior, queda demostrado esto:

1. la Satélite **sí recibió** el trabajo
2. la Satélite **sí ejecutó** generación real de imagen
3. la GPU/runtime local de la Satélite **sí participó**
4. la Central **sí recibió** el resultado real
5. YeyoNet ya no está haciendo solo handshake, sino **trabajo útil distribuido**

---

## Qué no demuestra

Esta prueba no demuestra todavía:

- batching de múltiples imágenes
- colas largas
- tolerancia a OOM
- reintentos automáticos en generación pesada
- persistencia en storage externo

Eso va después del primer smoke test real.

---

## Checklist corto

### Satélite

- [ ] `git pull origin main`
- [ ] backend reiniciado
- [ ] `/api/v1/media/image/status` responde
- [ ] prueba local `/api/v1/media/image/generate` exitosa
- [ ] YeyoNet conectado

### Central

- [ ] `/api/v1/yeyonet/identity` dice `central`
- [ ] `/api/v1/yeyonet/satellites` muestra GPU/RAM del satélite
- [ ] job `image_generate` creado
- [ ] `assigned_to` apunta al satélite
- [ ] `result.image_b64` vuelve
- [ ] imagen guardada en `tests/qa-results/yeyonet/distributed-image-smoke.png`
