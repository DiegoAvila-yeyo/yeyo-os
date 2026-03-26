#!/usr/bin/env python3.11
"""
YeyoOS — Seed de base de conocimiento por namespace
Fase 5: Popula imagen:conocimiento, codigo:conocimiento,
        video:conocimiento, automatizacion:conocimiento

Uso:
  python3.11 scripts/seed_knowledge.py
  python3.11 scripts/seed_knowledge.py --namespace imagen:conocimiento
  python3.11 scripts/seed_knowledge.py --dry-run
"""

import asyncio
import json
import os
import sys
from typing import Optional

import asyncpg
import httpx

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://yeyo:yeyo@localhost:5432/yeyoos")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen2.5-coder:7b")

# ============================================================
# KNOWLEDGE BASE — contenido por namespace
# ============================================================

KNOWLEDGE: dict[str, list[dict]] = {

    "imagen:conocimiento": [
        # Estilos
        {"content": "Estilo fotorrealista: alta definición, lighting natural, detalles finos de textura, profundidad de campo realista. Ideal para portraits y arquitectura.", "category": "estilo"},
        {"content": "Estilo anime/manga: líneas limpias, ojos grandes expresivos, paleta de colores vibrante, shading cel. Popular en personajes y escenas dinámicas.", "category": "estilo"},
        {"content": "Estilo minimalista: fondo limpio, formas geométricas simples, paleta reducida a 2-3 colores, mucho espacio negativo. Efectivo para logos e iconos.", "category": "estilo"},
        {"content": "Estilo oil painting: pinceladas visibles, mezcla rica de colores, texturas impasto, iluminación dramática tipo Rembrandt.", "category": "estilo"},
        {"content": "Estilo cyberpunk: neon lights (morado, cyan, rosa), lluvia en superficies reflectantes, ambiente nocturno urbano, hologramas flotantes.", "category": "estilo"},
        {"content": "Estilo watercolor: bordes difusos, transparencia en capas, granulación del papel visible, colores que se mezclan húmedos.", "category": "estilo"},
        {"content": "Estilo pixel art: resolución baja intencional, bordes pixelados, paleta limitada, dithering para gradientes. 16x16 a 64x64 px típico.", "category": "estilo"},
        {"content": "Estilo flat design: sin sombras ni gradientes, colores sólidos planos, ilustración vectorial limpia, muy usado en UI/UX.", "category": "estilo"},
        # Composición
        {"content": "Regla de tercios: dividir la imagen en 3x3. Colocar sujeto principal en intersecciones de las líneas para composición más dinámica que centrar.", "category": "composicion"},
        {"content": "Leading lines (líneas guía): usar caminos, ríos, arquitectura para dirigir el ojo del espectador hacia el sujeto principal.", "category": "composicion"},
        {"content": "Marco dentro del marco: usar puertas, ventanas o ramas para enmarcar el sujeto, añade profundidad y contexto.", "category": "composicion"},
        {"content": "Simetría y patrones: composición centrada para sujetos con simetría natural. Patrones repetitivos crean sensación de ritmo.", "category": "composicion"},
        {"content": "Espacio negativo: área vacía alrededor del sujeto. Crea respiro visual y puede ser tan importante como el sujeto mismo.", "category": "composicion"},
        # Iluminación
        {"content": "Golden hour lighting: luz dorada suave justo después del amanecer o antes del atardecer. Sombras largas y cálidas, muy fotogénico.", "category": "iluminacion"},
        {"content": "Iluminación Rembrandt: fuente de luz a 45° arriba y al lado, crea triángulo de luz bajo el ojo opuesto. Dramático para retratos.", "category": "iluminacion"},
        {"content": "Rim lighting (backlight): fuente de luz detrás del sujeto crea borde luminoso que lo separa del fondo. Muy cinemático.", "category": "iluminacion"},
        {"content": "Soft box / difuso: luz difuminada sin sombras duras. Ideal para productos, moda y retratos donde se quiere flattering lighting.", "category": "iluminacion"},
        # Colores
        {"content": "Paleta análoga: colores adyacentes en la rueda de color (ej: azul, azul-verde, verde). Armonioso y tranquilizador.", "category": "color"},
        {"content": "Paleta complementaria: colores opuestos en la rueda (ej: naranja y azul, rojo y verde). Alto contraste y vibración visual.", "category": "color"},
        {"content": "Paleta monocromática: un solo color en diferentes saturaciones y brillo. Muy elegante y sofisticado.", "category": "color"},
        {"content": "Color grading cinematográfico: teal en sombras + orange en medios tonos es el look más popular en cine moderno.", "category": "color"},
        # Técnicas de prompt
        {"content": "Prompts efectivos para imagen: empezar con sujeto principal, luego acción/pose, luego entorno, luego estilo artístico, luego técnica de iluminación, finalmente calidad (4K, high detail, masterpiece).", "category": "prompt"},
        {"content": "Negative prompts útiles: 'blurry, low quality, bad anatomy, extra limbs, watermark, text, signature, cropped, worst quality'.", "category": "prompt"},
        {"content": "Aspect ratios comunes: 1:1 para Instagram feed, 16:9 para YouTube/banner, 9:16 para stories/TikTok, 4:3 para fotografía clásica.", "category": "prompt"},
        {"content": "Para retratos: incluir 'sharp focus on eyes, detailed face, professional photography, studio lighting, bokeh background' mejora consistencia.", "category": "prompt"},
    ],

    "codigo:conocimiento": [
        # Clean code
        {"content": "Principio DRY (Don't Repeat Yourself): si copias código más de 2 veces, crea una función o clase reutilizable.", "category": "clean_code"},
        {"content": "Principio SOLID — Single Responsibility: cada clase/función debe tener una sola razón para cambiar.", "category": "clean_code"},
        {"content": "Principio SOLID — Open/Closed: abierto para extensión (herencia/interfaces), cerrado para modificación.", "category": "clean_code"},
        {"content": "Naming conventions: variables en snake_case (Python), camelCase (JS/TS), UPPER_CASE para constantes. Nombres descriptivos > comentarios.", "category": "clean_code"},
        {"content": "Funciones pequeñas: máximo 20 líneas. Si necesita más, extraer subfunciones. Una función = una acción.", "category": "clean_code"},
        {"content": "Early return pattern: validar condiciones al inicio y retornar temprano para evitar nesting profundo (arrow anti-pattern).", "category": "clean_code"},
        # Python
        {"content": "Python best practices: usar type hints en todas las funciones, f-strings para interpolación, dataclasses para DTOs simples, async/await para I/O.", "category": "python"},
        {"content": "Python async patterns: usar asyncio.gather() para paralelizar coroutines independientes. asyncio.create_task() para background tasks sin await.", "category": "python"},
        {"content": "Python error handling: crear excepciones custom heredando de Exception, capturar específico no genérico, siempre loguear con contexto.", "category": "python"},
        {"content": "Python performance: list comprehensions son más rápidas que loops, generators para grandes datasets, lru_cache para memoización.", "category": "python"},
        # TypeScript/JavaScript
        {"content": "TypeScript strict mode: activar 'strict: true' en tsconfig. Evita 'any', usar 'unknown' y type guards. Interfaces para shapes de objetos.", "category": "typescript"},
        {"content": "React patterns modernos: componentes funcionales + hooks. useState para estado local, useReducer para estado complejo, useContext para estado global.", "category": "typescript"},
        {"content": "Async/await sobre Promises: más legible, mejor stack traces, try/catch natural. Evitar callback hell.", "category": "typescript"},
        {"content": "TypeScript utility types: Partial<T>, Required<T>, Pick<T, K>, Omit<T, K>, Record<K, V>. Evitan duplicar definiciones de tipos.", "category": "typescript"},
        # Arquitectura
        {"content": "Arquitectura en capas: Presentation → Business Logic → Data Access. Cada capa solo conoce la capa inferior, nunca salta capas.", "category": "arquitectura"},
        {"content": "Repository pattern: abstraer acceso a datos detrás de una interfaz. El business logic no conoce si usa PostgreSQL, MongoDB o archivos.", "category": "arquitectura"},
        {"content": "Dependency Injection: las dependencias se pasan al constructor, no se crean dentro. Facilita testing y desacoplamiento.", "category": "arquitectura"},
        {"content": "Event-driven architecture: componentes se comunican via eventos en vez de llamadas directas. Desacoplamiento máximo, escalabilidad horizontal.", "category": "arquitectura"},
        # Testing
        {"content": "Testing pyramid: muchos unit tests (rápidos, aislados), menos integration tests, pocos E2E. Ratio recomendado: 70/20/10.", "category": "testing"},
        {"content": "AAA pattern en tests: Arrange (preparar datos), Act (ejecutar función), Assert (verificar resultado). Cada test prueba una sola cosa.", "category": "testing"},
        {"content": "Mocking best practices: mockear dependencias externas (DB, APIs), no mockear lógica de negocio. Los mocks deben parecerse a la realidad.", "category": "testing"},
        # Seguridad
        {"content": "SQL injection prevention: siempre usar parameterized queries / prepared statements. Nunca concatenar strings con input del usuario.", "category": "seguridad"},
        {"content": "Secrets management: variables de entorno para credenciales, nunca hardcodear. Usar .env local + vault en producción.", "category": "seguridad"},
        {"content": "Input validation: validar y sanitizar todo input del usuario en el backend, no solo en frontend. Nunca confiar en el cliente.", "category": "seguridad"},
    ],

    "video:conocimiento": [
        # Composición y cámara
        {"content": "Rule of thirds en video: mismo que fotografía pero el sujeto debe tener 'espacio para mirar' o moverse hacia el espacio vacío.", "category": "composicion"},
        {"content": "Camera movement types: Pan (horizontal), Tilt (vertical), Dolly in/out (acercarse/alejarse), Crane (arriba/abajo), Handheld (orgánico/dinámico).", "category": "camara"},
        {"content": "180° rule: nunca cruzar la línea de acción en una escena. Los personajes deben mantener posición relativa izquierda/derecha entre cortes.", "category": "edicion"},
        {"content": "Shot sizes: Extreme Wide (contexto), Wide (sujeto completo), Medium (torso), Close-Up (cara), Extreme Close-Up (detalle).", "category": "composicion"},
        {"content": "Dutch angle (cámara inclinada): transmite desorientación, tensión o que algo está mal. Muy usado en thriller y horror.", "category": "composicion"},
        # Iluminación para video
        {"content": "Three-point lighting: Key light (principal, fuerte), Fill light (rellena sombras, más suave), Back/Rim light (separa sujeto del fondo).", "category": "iluminacion"},
        {"content": "Interview lighting setup: key light a 45° del sujeto, fill al otro lado más suave, rimlight detrás para separación. Fondo desenfocado con bokeh.", "category": "iluminacion"},
        {"content": "Color temperature en video: 5600K para exterior día, 3200K para interior con tungsteno. Mezclar temperaturas crea look cinematográfico.", "category": "iluminacion"},
        # Edición
        {"content": "Jump cut: corte entre dos tomas del mismo sujeto con pequeña variación. Crea sensación de tiempo que pasa o ritmo acelerado. Popular en YouTube.", "category": "edicion"},
        {"content": "Match cut: cortar en movimiento — el movimiento del shot A continúa naturalmente en el shot B. Crea continuidad fluida.", "category": "edicion"},
        {"content": "J-cut y L-cut: J-cut = el audio del siguiente clip empieza antes del corte visual. L-cut = el audio del clip anterior continúa después del corte.", "category": "edicion"},
        {"content": "Pacing del video: escenas de acción requieren cortes rápidos (1-3 seg), escenas dramáticas aguantan cortes más largos (5-10 seg).", "category": "edicion"},
        {"content": "Música y cortes: cortar en el beat de la música refuerza ritmo. Cortar justo antes del beat crea anticipación.", "category": "edicion"},
        # Color grading
        {"content": "LUTs (Look Up Tables): presets de color grading. Teal & Orange es el más popular en cine moderno. Aplicar al 50-70% de intensidad para no sobrecargar.", "category": "color"},
        {"content": "Log footage: grabar en perfil LOG preserva más detalle en sombras y luces. Requiere color grade en post, pero da más flexibilidad.", "category": "color"},
        {"content": "Skin tones: ajustar curva roja/naranja en HSL para neutralidad. Evitar over-saturation en piel, se ve non-natural.", "category": "color"},
        # Formatos y exportación
        {"content": "Export settings YouTube: H.264 o H.265, bitrate 35-68 Mbps para 1080p, 44.1 kHz audio stereo. Subir siempre 4K si es posible para mejor compresión.", "category": "exportacion"},
        {"content": "Frame rates: 24fps cinematic, 30fps broadcast/YouTube standard, 60fps para gaming/deportes, 120fps+ para slow motion.", "category": "exportacion"},
        {"content": "Aspect ratios: 16:9 para YouTube/PC, 9:16 para Reels/TikTok/Stories, 1:1 cuadrado para feed Instagram, 4:5 para portrait Instagram.", "category": "exportacion"},
    ],

    "automatizacion:conocimiento": [
        # Patrones de workflow
        {"content": "Trigger → Action pattern: toda automatización tiene un disparador (evento, schedule, webhook) y una o más acciones. Mantener cada acción atómica.", "category": "patron"},
        {"content": "Idempotencia: una automatización idempotente produce el mismo resultado si se ejecuta múltiples veces. Crítico para evitar duplicados.", "category": "patron"},
        {"content": "Error handling en automations: always implement retry logic con exponential backoff. Log todos los errores con contexto. Alertas para fallos críticos.", "category": "patron"},
        {"content": "Dead letter queue: cuando un mensaje falla repetidamente, moverlo a cola separada para revisión manual. Evita que un mensaje roto bloquee toda la cola.", "category": "patron"},
        # Herramientas
        {"content": "n8n: herramienta open-source de automatización visual. Self-hosted, 400+ integraciones, soporta código custom en JavaScript/Python.", "category": "herramienta"},
        {"content": "Make (antes Integromat): alternativa a Zapier con modelo visual más potente. Mejor para flujos complejos con branches y transformaciones de datos.", "category": "herramienta"},
        {"content": "GitHub Actions: CI/CD nativo de GitHub. YAML-based, excelente para build/test/deploy. Free para repos públicos.", "category": "herramienta"},
        {"content": "Cron expressions: '0 9 * * MON-FRI' = 9am de lunes a viernes. '*/15 * * * *' = cada 15 minutos. '0 0 1 * *' = primer día del mes.", "category": "herramienta"},
        {"content": "Webhooks: HTTP POST enviado automáticamente cuando ocurre un evento. Más eficiente que polling. Requiere URL pública (usar ngrok en local).", "category": "herramienta"},
        # Integraciones comunes
        {"content": "Slack notifications: webhook de Slack acepta JSON con 'text' o 'blocks' (rich formatting). Ideal para alertas de sistemas y notificaciones de deployment.", "category": "integracion"},
        {"content": "Email automation: SendGrid/Resend para transaccional, Mailchimp para marketing. Rate limits típicos: 100 emails/hora en tier free.", "category": "integracion"},
        {"content": "Database sync: usar Change Data Capture (CDC) con Debezium para capturar cambios en tiempo real sin polling. Mucho más eficiente.", "category": "integracion"},
        # Buenas prácticas
        {"content": "Modularidad: una automatización = una responsabilidad. No crear mega-flujos de 50 pasos. Dividir en flujos pequeños que se llaman entre sí.", "category": "practica"},
        {"content": "Documentar automations: describir qué dispara el flujo, qué hace y qué produce. Los flujos sin documentación se convierten en caja negra.", "category": "practica"},
        {"content": "Testing de automations: crear entornos de prueba separados. Nunca testear en producción. Usar datos mock para triggers.", "category": "practica"},
        {"content": "Monitoreo: configurar alertas cuando una automatización falla o tarda más de lo esperado. Herramientas: PagerDuty, Grafana, o simple email.", "category": "practica"},
        {"content": "Rate limiting awareness: las APIs tienen límites (ej: Twitter 300 requests/15min). Implementar sleep() entre requests y respetar Retry-After headers.", "category": "practica"},
        # API patterns
        {"content": "REST vs GraphQL para automations: REST es más simple para integraciones básicas. GraphQL cuando necesitas muchos campos específicos de una entidad compleja.", "category": "api"},
        {"content": "OAuth 2.0 flow: Authorization Code para usuarios humanos, Client Credentials para server-to-server. Guardar tokens en secrets manager, nunca en código.", "category": "api"},
        {"content": "Pagination en APIs: cursor-based pagination es más estable que offset-based para datos que cambian. Siempre manejar el caso de última página.", "category": "api"},
    ],
}

# ============================================================

def generate_embedding(text: str, model: str = OLLAMA_MODEL) -> Optional[list[float]]:
    """Genera embedding via Ollama API."""
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{OLLAMA_HOST}/api/embed",
                json={"model": model, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [[]])
            if embeddings and embeddings[0]:
                return embeddings[0]
    except Exception as e:
        print(f"  ⚠️  Embedding falló: {e}")
    return None


async def seed_namespace(conn: asyncpg.Connection, namespace: str, entries: list[dict], dry_run: bool = False):
    """Inserta entradas en un namespace. Skippea duplicados por checksum."""
    print(f"\n📁 {namespace} ({len(entries)} entradas)")

    inserted = 0
    skipped = 0

    for entry in entries:
        content = entry["content"]
        category = entry.get("category", "general")

        # Check if already exists by content similarity (simple exact match via checksum)
        existing = await conn.fetchval(
            "SELECT id FROM flash_memories WHERE content = $1 AND namespace = $2 LIMIT 1",
            content,
            namespace,
        )
        if existing:
            print(f"  ⏭  [skip] {content[:60]}...")
            skipped += 1
            continue

        if dry_run:
            print(f"  🔍 [dry] {content[:70]}...")
            inserted += 1
            continue

        # Generate embedding
        print(f"  🔢 embed + store: {content[:60]}...", end="", flush=True)
        embedding = generate_embedding(content)

        metadata = {"category": category, "source": "seed"}

        if embedding:
            vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
            await conn.execute(
                """
                INSERT INTO flash_memories (content, type, metadata, embedding, source, namespace)
                VALUES ($1, 'fact', $2, $3::vector, 'seed', $4)
                """,
                content,
                json.dumps(metadata),
                vector_str,
                namespace,
            )
        else:
            # Store without embedding (will use keyword search as fallback)
            await conn.execute(
                """
                INSERT INTO flash_memories (content, type, metadata, source, namespace)
                VALUES ($1, 'fact', $2, 'seed', $3)
                """,
                content,
                json.dumps(metadata),
                namespace,
            )

        print(" ✅")
        inserted += 1

    print(f"  → Insertadas: {inserted}, Saltadas: {skipped}")
    return inserted, skipped


async def main():
    dry_run = "--dry-run" in sys.argv
    target_ns = None
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            target_ns = arg
            break

    print("🌱 YeyoOS — Seed de knowledge base")
    if dry_run:
        print("🔍 DRY RUN (no se escribirá nada)\n")

    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"❌ Conexión a PostgreSQL falló: {e}")
        sys.exit(1)

    try:
        total_inserted = 0
        total_skipped = 0

        namespaces_to_seed = {target_ns: KNOWLEDGE[target_ns]} if target_ns else KNOWLEDGE

        for namespace, entries in namespaces_to_seed.items():
            inserted, skipped = await seed_namespace(conn, namespace, entries, dry_run)
            total_inserted += inserted
            total_skipped += skipped

        print(f"\n{'─'*50}")
        print(f"✅ Seed completado: {total_inserted} insertadas, {total_skipped} saltadas")

        # Verify
        if not dry_run:
            print("\n📊 Estado actual:")
            rows = await conn.fetch(
                """
                SELECT namespace, COUNT(*) as total
                FROM flash_memories
                WHERE namespace LIKE '%:conocimiento'
                GROUP BY namespace
                ORDER BY namespace
                """
            )
            for row in rows:
                print(f"  {row['namespace']}: {row['total']} entradas")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
