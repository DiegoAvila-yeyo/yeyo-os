## ═══════════════════════════════════════
## MICRO-FASE 7.12 — Documentation Generator
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 7.12-1 [VSCODE] — Crear generador de documentación automática

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.12 de Capa 7 (Evolución): crear el generador automático de documentación para usuarios y developers.

CONTEXTO:
- Capas 0-6 completadas + micro-fases 7.0-7.11
- Genera documentación desde: docstrings, API specs (OpenAPI), estructura de código
- Tipos: user guide, developer guide, API reference
- Output: HTML estático
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios:
   mkdir -p src/docs
   mkdir -p tests/unit/docs

2. Crear archivo src/docs/__init__.py:

   Ruta: ~/yeyo-os/src/docs/__init__.py
   Contenido:
   from .generator import DocsGenerator, DocSection

3. Crear archivo src/docs/generator.py:

   Ruta: ~/yeyo-os/src/docs/generator.py
   Contenido:

   """
   YeyoOS — Documentation Generator
   Micro-fase 7.12 — Capa 7: Evolución

   Genera documentación HTML automática desde:
   - Docstrings de Python
   - OpenAPI spec de FastAPI
   - Estructura del código fuente
   """

   import ast
   import json
   import logging
   from datetime import datetime
   from pathlib import Path
   from typing import Optional

   from pydantic import BaseModel, Field

   logger = logging.getLogger("yeyo.docs.generator")


   class DocSection(BaseModel):
       """Sección de documentación."""
       title: str
       content: str
       level: int = Field(default=1, ge=1, le=6)
       subsections: list["DocSection"] = []


   class DocModule(BaseModel):
       """Módulo documentado."""
       name: str
       path: str
       docstring: str = ""
       classes: list[dict] = []
       functions: list[dict] = []


   class DocsConfig(BaseModel):
       """Configuración del generador de docs."""
       project_name: str = "YeyoOS"
       version: str = "1.0.0"
       source_dirs: list[str] = Field(default_factory=lambda: ["src"])
       output_dir: str = "docs/build"
       include_api_reference: bool = True
       include_user_guide: bool = True
       include_developer_guide: bool = True
       api_url: str = "http://localhost:8000"


   class DocsGenerator:
       """Genera documentación HTML estática de YeyoOS."""

       def __init__(self, config: Optional[DocsConfig] = None):
           self.config = config or DocsConfig()
           self.output_dir = Path(self.config.output_dir)
           self.output_dir.mkdir(parents=True, exist_ok=True)
           self._modules: list[DocModule] = []

       def extract_docstrings(self, source_dir: str) -> list[DocModule]:
           """Extrae docstrings de todos los archivos Python."""
           modules = []
           src_path = Path(source_dir)

           if not src_path.exists():
               logger.warning(f"Directorio no encontrado: {source_dir}")
               return modules

           for py_file in src_path.rglob("*.py"):
               if py_file.name.startswith("__"):
                   continue
               try:
                   source = py_file.read_text(encoding='utf-8')
                   tree = ast.parse(source)
                   module_doc = ast.get_docstring(tree) or ""

                   classes = []
                   functions = []

                   for node in ast.walk(tree):
                       if isinstance(node, ast.ClassDef):
                           class_doc = ast.get_docstring(node) or ""
                           methods = []
                           for item in node.body:
                               if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                   method_doc = ast.get_docstring(item) or ""
                                   methods.append({
                                       "name": item.name,
                                       "docstring": method_doc,
                                       "is_async": isinstance(item, ast.AsyncFunctionDef),
                                   })
                           classes.append({
                               "name": node.name,
                               "docstring": class_doc,
                               "methods": methods,
                           })
                       elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                           if not isinstance(getattr(node, '_parent', None), ast.ClassDef):
                               func_doc = ast.get_docstring(node) or ""
                               functions.append({
                                   "name": node.name,
                                   "docstring": func_doc,
                                   "is_async": isinstance(node, ast.AsyncFunctionDef),
                               })

                   modules.append(DocModule(
                       name=py_file.stem,
                       path=str(py_file),
                       docstring=module_doc,
                       classes=classes,
                       functions=functions,
                   ))

               except SyntaxError:
                   logger.warning(f"Error parsing {py_file}")

           self._modules = modules
           logger.info(f"Extraídos {len(modules)} módulos de {source_dir}")
           return modules

       async def fetch_openapi_spec(self) -> Optional[dict]:
           """Obtiene OpenAPI spec de FastAPI."""
           try:
               import httpx
               async with httpx.AsyncClient(timeout=10.0) as client:
                   resp = await client.get(f"{self.config.api_url}/openapi.json")
                   if resp.status_code == 200:
                       return resp.json()
           except Exception as e:
               logger.warning(f"No se pudo obtener OpenAPI spec: {e}")
           return None

       def generate_api_reference(self, openapi_spec: dict) -> str:
           """Genera HTML de API reference desde OpenAPI spec."""
           html = "<h1>API Reference</h1>\n"
           paths = openapi_spec.get("paths", {})

           for path, methods in sorted(paths.items()):
               for method, details in methods.items():
                   summary = details.get("summary", "")
                   description = details.get("description", "")
                   html += f'<div class="endpoint">\n'
                   html += f'  <h3><span class="method">{method.upper()}</span> {path}</h3>\n'
                   if summary:
                       html += f'  <p class="summary">{summary}</p>\n'
                   if description:
                       html += f'  <p class="description">{description}</p>\n'

                   # Parameters
                   params = details.get("parameters", [])
                   if params:
                       html += '  <h4>Parameters</h4>\n  <ul>\n'
                       for p in params:
                           html += f'    <li><code>{p.get("name")}</code> ({p.get("in")}): {p.get("description", "")}</li>\n'
                       html += '  </ul>\n'

                   html += '</div>\n'

           return html

       def generate_module_docs(self, modules: list[DocModule]) -> str:
           """Genera HTML de documentación de módulos."""
           html = "<h1>Developer Guide — Módulos</h1>\n"

           for module in sorted(modules, key=lambda m: m.name):
               html += f'<div class="module">\n'
               html += f'  <h2>{module.name}</h2>\n'
               html += f'  <p class="path"><code>{module.path}</code></p>\n'
               if module.docstring:
                   html += f'  <p>{module.docstring}</p>\n'

               for cls in module.classes:
                   html += f'  <div class="class">\n'
                   html += f'    <h3>class {cls["name"]}</h3>\n'
                   if cls.get("docstring"):
                       html += f'    <p>{cls["docstring"]}</p>\n'
                   for method in cls.get("methods", []):
                       prefix = "async " if method.get("is_async") else ""
                       html += f'    <div class="method">\n'
                       html += f'      <h4>{prefix}{method["name"]}()</h4>\n'
                       if method.get("docstring"):
                           html += f'      <p>{method["docstring"]}</p>\n'
                       html += f'    </div>\n'
                   html += f'  </div>\n'

               html += '</div>\n'

           return html

       def generate_user_guide(self) -> str:
           """Genera HTML del user guide."""
           return """<h1>YeyoOS — Guía de Usuario</h1>
   <h2>Introducción</h2>
   <p>YeyoOS es un sistema operativo AI-nativo que aprende de ti y se adapta a tus necesidades.</p>

   <h2>Primeros Pasos</h2>
   <ol>
     <li>Instala YeyoOS desde la ISO</li>
     <li>Completa el wizard de instalación (idioma, usuario, red)</li>
     <li>El sistema descargará el modelo de IA automáticamente</li>
     <li>¡Comienza a interactuar con tu OS inteligente!</li>
   </ol>

   <h2>Neural Hub</h2>
   <p>El Neural Hub es tu interfaz principal. Aquí puedes:</p>
   <ul>
     <li>Chatear con la IA integrada</li>
     <li>Gestionar nodos y conexiones</li>
     <li>Instalar paquetes desde el YEYO Store</li>
     <li>Ver el estado del sistema en tiempo real</li>
   </ul>

   <h2>YEYO Store</h2>
   <p>El marketplace de paquetes para ampliar las capacidades de YeyoOS.</p>

   <h2>Seguridad</h2>
   <p>Guardian protege tu sistema 24/7. Kill Switch (Ctrl+Alt+K) pausa toda la IA si es necesario.</p>

   <h2>Backup y Migración</h2>
   <p>Exporta tus datos cifrados para migrar a otra instalación de YeyoOS.</p>
   """

       def _wrap_html(self, title: str, body: str) -> str:
           """Envuelve contenido en HTML completo."""
           return f"""<!DOCTYPE html>
   <html lang="es">
   <head>
     <meta charset="UTF-8">
     <meta name="viewport" content="width=device-width, initial-scale=1.0">
     <title>{title} — {self.config.project_name}</title>
     <style>
       body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
              max-width: 900px; margin: 0 auto; padding: 2rem; color: #333; }}
       h1 {{ color: #1a1a2e; border-bottom: 2px solid #e94560; padding-bottom: 0.5rem; }}
       h2 {{ color: #16213e; }}
       h3 {{ color: #0f3460; }}
       code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }}
       .endpoint {{ border-left: 3px solid #e94560; padding-left: 1rem; margin: 1rem 0; }}
       .method {{ background: #e94560; color: white; padding: 2px 8px; border-radius: 3px;
                  font-weight: bold; font-size: 0.85em; }}
       .module {{ border: 1px solid #eee; padding: 1rem; margin: 1rem 0; border-radius: 8px; }}
       .class {{ margin-left: 1rem; border-left: 2px solid #ddd; padding-left: 1rem; }}
       .path {{ color: #666; font-size: 0.9em; }}
       nav a {{ margin-right: 1rem; }}
     </style>
   </head>
   <body>
     <nav>
       <a href="index.html">Inicio</a>
       <a href="user-guide.html">Guía de Usuario</a>
       <a href="developer-guide.html">Developer Guide</a>
       <a href="api-reference.html">API Reference</a>
     </nav>
     {body}
     <footer>
       <p>Generado automáticamente por YeyoOS Docs Generator — {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
     </footer>
   </body>
   </html>"""

       async def generate_all(self) -> dict:
           """Genera toda la documentación."""
           generated_files = {}

           # 1. User Guide
           if self.config.include_user_guide:
               user_guide = self.generate_user_guide()
               path = self.output_dir / "user-guide.html"
               path.write_text(self._wrap_html("Guía de Usuario", user_guide))
               generated_files["user_guide"] = str(path)

           # 2. Developer Guide
           if self.config.include_developer_guide:
               all_modules = []
               for src_dir in self.config.source_dirs:
                   modules = self.extract_docstrings(src_dir)
                   all_modules.extend(modules)
               dev_guide = self.generate_module_docs(all_modules)
               path = self.output_dir / "developer-guide.html"
               path.write_text(self._wrap_html("Developer Guide", dev_guide))
               generated_files["developer_guide"] = str(path)

           # 3. API Reference
           if self.config.include_api_reference:
               spec = await self.fetch_openapi_spec()
               if spec:
                   api_ref = self.generate_api_reference(spec)
               else:
                   api_ref = "<h1>API Reference</h1><p>OpenAPI spec no disponible. Inicie el servidor para generar.</p>"
               path = self.output_dir / "api-reference.html"
               path.write_text(self._wrap_html("API Reference", api_ref))
               generated_files["api_reference"] = str(path)

           # 4. Index
           index = f"""<h1>📚 {self.config.project_name} Documentation</h1>
   <p>Versión: {self.config.version}</p>
   <ul>
     <li><a href="user-guide.html">Guía de Usuario</a></li>
     <li><a href="developer-guide.html">Developer Guide</a></li>
     <li><a href="api-reference.html">API Reference</a></li>
   </ul>"""
           path = self.output_dir / "index.html"
           path.write_text(self._wrap_html("Documentación", index))
           generated_files["index"] = str(path)

           logger.info(f"Documentación generada: {len(generated_files)} archivos en {self.output_dir}")
           return generated_files

4. Crear archivo tests/unit/docs/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/docs/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/docs/test_generator.py:

   Ruta: ~/yeyo-os/tests/unit/docs/test_generator.py
   Contenido:

   """Tests para Documentation Generator — Micro-fase 7.12"""

   import tempfile
   import pytest
   from pathlib import Path
   from src.docs.generator import DocsGenerator, DocsConfig, DocModule, DocSection


   class TestDocsGenerator:
       """Tests para DocsGenerator."""

       def setup_method(self):
           self.tmp_dir = tempfile.mkdtemp()
           self.config = DocsConfig(
               output_dir=self.tmp_dir,
               source_dirs=[self.tmp_dir],
           )
           self.generator = DocsGenerator(config=self.config)

       def test_creates_output_dir(self):
           assert Path(self.tmp_dir).exists()

       def test_extract_docstrings_from_file(self):
           src_dir = Path(self.tmp_dir) / "src_test"
           src_dir.mkdir()
           (src_dir / "example.py").write_text('''
   """Module docstring."""

   class MyClass:
       """Class docstring."""
       def my_method(self):
           """Method docstring."""
           pass

   def my_function():
       """Function docstring."""
       pass
   ''')
           modules = self.generator.extract_docstrings(str(src_dir))
           assert len(modules) == 1
           assert modules[0].docstring == "Module docstring."
           assert len(modules[0].classes) >= 1

       def test_extract_docstrings_empty_dir(self):
           empty_dir = Path(self.tmp_dir) / "empty"
           empty_dir.mkdir()
           modules = self.generator.extract_docstrings(str(empty_dir))
           assert len(modules) == 0

       def test_extract_docstrings_nonexistent_dir(self):
           modules = self.generator.extract_docstrings("/nonexistent")
           assert len(modules) == 0

       def test_generate_user_guide(self):
           html = self.generator.generate_user_guide()
           assert "YeyoOS" in html
           assert "Neural Hub" in html
           assert "YEYO Store" in html

       def test_generate_api_reference(self):
           spec = {
               "paths": {
                   "/api/chat": {
                       "post": {
                           "summary": "Enviar mensaje",
                           "description": "Envía un mensaje al chatbot",
                       },
                   },
               },
           }
           html = self.generator.generate_api_reference(spec)
           assert "/api/chat" in html
           assert "POST" in html

       def test_generate_module_docs(self):
           modules = [
               DocModule(
                   name="test_module",
                   path="src/test_module.py",
                   docstring="Test module doc",
                   classes=[{
                       "name": "TestClass",
                       "docstring": "Test class",
                       "methods": [{"name": "test_method", "docstring": "A method", "is_async": False}],
                   }],
               ),
           ]
           html = self.generator.generate_module_docs(modules)
           assert "test_module" in html
           assert "TestClass" in html

       def test_wrap_html_complete(self):
           html = self.generator._wrap_html("Test Title", "<p>Content</p>")
           assert "<!DOCTYPE html>" in html
           assert "Test Title" in html
           assert "<p>Content</p>" in html
           assert "YeyoOS" in html

       @pytest.mark.asyncio
       async def test_generate_all_creates_files(self):
           self.config.include_api_reference = False
           self.generator = DocsGenerator(config=self.config)
           files = await self.generator.generate_all()
           assert "index" in files
           assert "user_guide" in files
           assert Path(files["index"]).exists()

       def test_doc_section_model(self):
           section = DocSection(title="Test", content="Content", level=2)
           assert section.title == "Test"
           assert section.level == 2

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/docs/test_generator.py -v

VERIFICAR:
- [ ] Archivo src/docs/generator.py existe con DocsGenerator
- [ ] Extrae docstrings de Python con AST
- [ ] Genera API reference desde OpenAPI spec
- [ ] Genera user guide HTML
- [ ] Genera developer guide HTML
- [ ] Index con navegación
- [ ] HTML con estilo CSS inline
- [ ] generate_all crea todos los archivos
- [ ] TODOS los tests pasan

SI FALLA:
- httpx: pip install httpx

NO HACER:
- No generar docs de dependencias externas
- No requerir servidor running para user guide

GATE: Docs generator extrae docstrings, genera HTML estático para user guide, developer guide, API reference, todos los tests pasan.
```
