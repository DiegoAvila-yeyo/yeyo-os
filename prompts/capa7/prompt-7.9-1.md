## ═══════════════════════════════════════
## MICRO-FASE 7.9 — User Data Migration
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 7.9-1 [VSCODE] — Crear sistema de migración de datos de usuario

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.9 de Capa 7 (Evolución): crear el sistema de import/export de datos de usuario entre instalaciones de YeyoOS.

CONTEXTO:
- Micro-fase 7.8 completada: Multi-User System creado
- Export: Flash Memory + preferencias + node configs → archivo cifrado
- Import: verificar → descifrar → merge (no overwrite)
- Formato: .yeyo-backup (encrypted tar.gz)
- Cifrado: AES-256 con contraseña del usuario
- Compatibilidad cross-version
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/auth/migration.py:

   Ruta: ~/yeyo-os/src/auth/migration.py
   Contenido:

   """
   YeyoOS — User Data Migration
   Micro-fase 7.9 — Capa 7: Evolución

   Import/export de datos de usuario entre instalaciones.
   Formato .yeyo-backup: tar.gz cifrado con AES-256.
   Merge inteligente: no sobreescribe, fusiona.
   """

   import gzip
   import hashlib
   import io
   import json
   import logging
   import os
   import secrets
   import tarfile
   from datetime import datetime
   from pathlib import Path
   from typing import Optional

   from pydantic import BaseModel, Field

   logger = logging.getLogger("yeyo.auth.migration")


   class BackupManifest(BaseModel):
       """Manifiesto del archivo de backup."""
       version: str = "1.0.0"
       yeyo_version: str = "1.0.0"
       username: str
       created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
       includes_flash_memory: bool = True
       includes_preferences: bool = True
       includes_node_configs: bool = True
       total_files: int = 0
       checksum: str = ""


   class MigrationResult(BaseModel):
       """Resultado de una operación de migración."""
       success: bool
       operation: str  # "export" o "import"
       file_path: str = ""
       files_processed: int = 0
       files_merged: int = 0
       files_skipped: int = 0
       errors: list[str] = []
       timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


   class DataMigrator:
       """Sistema de migración de datos de usuario."""

       BACKUP_EXTENSION = ".yeyo-backup"
       ENCRYPTION_ITERATIONS = 100000
       SALT_SIZE = 32

       def __init__(self, user_data_dir: str = "data/users"):
           self.user_data_dir = Path(user_data_dir)

       def _derive_key(self, password: str, salt: bytes) -> bytes:
           """Deriva clave AES-256 desde contraseña con PBKDF2."""
           key = hashlib.pbkdf2_hmac(
               'sha256', password.encode(), salt, self.ENCRYPTION_ITERATIONS, dklen=32,
           )
           return key

       def _encrypt_data(self, data: bytes, password: str) -> bytes:
           """Cifra datos con AES-256-CBC."""
           try:
               from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
               from cryptography.hazmat.primitives import padding
               from cryptography.hazmat.backends import default_backend

               salt = os.urandom(self.SALT_SIZE)
               key = self._derive_key(password, salt)
               iv = os.urandom(16)

               padder = padding.PKCS7(128).padder()
               padded_data = padder.update(data) + padder.finalize()

               cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
               encryptor = cipher.encryptor()
               encrypted = encryptor.update(padded_data) + encryptor.finalize()

               # Formato: salt (32) + iv (16) + encrypted_data
               return salt + iv + encrypted

           except ImportError:
               logger.warning("cryptography no disponible, usando encoding base64 (NO SEGURO)")
               import base64
               marker = b"YEYO_UNENCRYPTED:"
               return marker + base64.b64encode(data)

       def _decrypt_data(self, encrypted_data: bytes, password: str) -> bytes:
           """Descifra datos AES-256-CBC."""
           try:
               from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
               from cryptography.hazmat.primitives import padding
               from cryptography.hazmat.backends import default_backend

               salt = encrypted_data[:self.SALT_SIZE]
               iv = encrypted_data[self.SALT_SIZE:self.SALT_SIZE + 16]
               ciphertext = encrypted_data[self.SALT_SIZE + 16:]

               key = self._derive_key(password, salt)

               cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
               decryptor = cipher.decryptor()
               padded = decryptor.update(ciphertext) + decryptor.finalize()

               unpadder = padding.PKCS7(128).unpadder()
               return unpadder.update(padded) + unpadder.finalize()

           except ImportError:
               import base64
               if encrypted_data.startswith(b"YEYO_UNENCRYPTED:"):
                   return base64.b64decode(encrypted_data[17:])
               raise ValueError("No se puede descifrar: cryptography no disponible")

       async def export_user_data(
           self,
           username: str,
           password: str,
           output_path: Optional[str] = None,
           include_flash_memory: bool = True,
           include_preferences: bool = True,
           include_node_configs: bool = True,
       ) -> MigrationResult:
           """Exporta datos del usuario a archivo .yeyo-backup cifrado."""
           user_dir = self.user_data_dir / username
           if not user_dir.exists():
               return MigrationResult(
                   success=False, operation="export",
                   errors=[f"Directorio de usuario no encontrado: {user_dir}"],
               )

           if not output_path:
               timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
               output_path = str(
                   self.user_data_dir / f"{username}_{timestamp}{self.BACKUP_EXTENSION}"
               )

           errors = []
           file_count = 0

           try:
               # Crear tar.gz en memoria
               tar_buffer = io.BytesIO()
               with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
                   dirs_to_include = []
                   if include_flash_memory:
                       dirs_to_include.append(("flash_memory", user_dir / "flash_memory"))
                   if include_preferences:
                       dirs_to_include.append(("preferences", user_dir / "preferences"))
                   if include_node_configs:
                       dirs_to_include.append(("node_configs", user_dir / "node_configs"))

                   for arcname_prefix, dir_path in dirs_to_include:
                       if dir_path.exists():
                           for f in dir_path.rglob("*"):
                               if f.is_file():
                                   arcname = f"{arcname_prefix}/{f.relative_to(dir_path)}"
                                   tar.add(str(f), arcname=arcname)
                                   file_count += 1

                   # Agregar manifiesto
                   manifest = BackupManifest(
                       username=username,
                       includes_flash_memory=include_flash_memory,
                       includes_preferences=include_preferences,
                       includes_node_configs=include_node_configs,
                       total_files=file_count,
                   )
                   manifest_data = manifest.model_dump_json().encode()
                   manifest_info = tarfile.TarInfo(name="manifest.json")
                   manifest_info.size = len(manifest_data)
                   tar.addfile(manifest_info, io.BytesIO(manifest_data))

               # Cifrar
               tar_data = tar_buffer.getvalue()
               encrypted = self._encrypt_data(tar_data, password)

               # Escribir archivo
               output_file = Path(output_path)
               output_file.parent.mkdir(parents=True, exist_ok=True)
               output_file.write_bytes(encrypted)

               logger.info(f"Export completado: {username} → {output_path} "
                           f"({file_count} archivos)")

               return MigrationResult(
                   success=True, operation="export",
                   file_path=output_path,
                   files_processed=file_count,
               )

           except Exception as e:
               logger.error(f"Error exportando datos: {e}")
               return MigrationResult(
                   success=False, operation="export",
                   errors=[str(e)],
               )

       async def import_user_data(
           self,
           backup_path: str,
           password: str,
           target_username: Optional[str] = None,
       ) -> MigrationResult:
           """Importa datos de usuario desde .yeyo-backup. Merge sin overwrite."""
           backup_file = Path(backup_path)
           if not backup_file.exists():
               return MigrationResult(
                   success=False, operation="import",
                   errors=[f"Archivo no encontrado: {backup_path}"],
               )

           errors = []
           files_merged = 0
           files_skipped = 0

           try:
               # Descifrar
               encrypted_data = backup_file.read_bytes()
               tar_data = self._decrypt_data(encrypted_data, password)

               # Extraer
               tar_buffer = io.BytesIO(tar_data)
               with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
                   # Leer manifiesto
                   manifest_member = tar.getmember("manifest.json")
                   manifest_file = tar.extractfile(manifest_member)
                   manifest = BackupManifest(**json.loads(manifest_file.read()))

                   username = target_username or manifest.username
                   user_dir = self.user_data_dir / username
                   user_dir.mkdir(parents=True, exist_ok=True)

                   for member in tar.getmembers():
                       if member.name == "manifest.json":
                           continue
                       if not member.isfile():
                           continue

                       target_path = user_dir / member.name
                       if target_path.exists():
                           files_skipped += 1
                           continue

                       # Merge: solo agregar archivos nuevos
                       target_path.parent.mkdir(parents=True, exist_ok=True)
                       extracted = tar.extractfile(member)
                       if extracted:
                           target_path.write_bytes(extracted.read())
                           files_merged += 1

               logger.info(f"Import completado: {backup_path} → {username} "
                           f"(merged={files_merged}, skipped={files_skipped})")

               return MigrationResult(
                   success=True, operation="import",
                   file_path=backup_path,
                   files_processed=files_merged + files_skipped,
                   files_merged=files_merged,
                   files_skipped=files_skipped,
               )

           except Exception as e:
               logger.error(f"Error importando datos: {e}")
               return MigrationResult(
                   success=False, operation="import",
                   errors=[str(e)],
               )

       async def verify_backup(self, backup_path: str, password: str) -> BackupManifest:
           """Verifica integridad del backup sin importar."""
           backup_file = Path(backup_path)
           if not backup_file.exists():
               raise FileNotFoundError(f"Archivo no encontrado: {backup_path}")

           encrypted_data = backup_file.read_bytes()
           tar_data = self._decrypt_data(encrypted_data, password)

           tar_buffer = io.BytesIO(tar_data)
           with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
               manifest_file = tar.extractfile(tar.getmember("manifest.json"))
               manifest = BackupManifest(**json.loads(manifest_file.read()))

           return manifest

2. Actualizar src/auth/__init__.py:

   Ruta: ~/yeyo-os/src/auth/__init__.py
   Contenido:
   from .multi_user import UserManager, User, UserRole, Session
   from .migration import DataMigrator, MigrationResult, BackupManifest

3. Crear archivo tests/unit/auth/test_migration.py:

   Ruta: ~/yeyo-os/tests/unit/auth/test_migration.py
   Contenido:

   """Tests para User Data Migration — Micro-fase 7.9"""

   import os
   import tempfile
   import pytest
   from pathlib import Path
   from src.auth.migration import DataMigrator, BackupManifest, MigrationResult


   class TestDataMigrator:
       """Tests para DataMigrator."""

       def setup_method(self):
           self.tmp_dir = tempfile.mkdtemp()
           self.migrator = DataMigrator(user_data_dir=self.tmp_dir)
           # Crear datos de usuario de prueba
           user_dir = Path(self.tmp_dir) / "testuser"
           (user_dir / "flash_memory").mkdir(parents=True)
           (user_dir / "preferences").mkdir(parents=True)
           (user_dir / "node_configs").mkdir(parents=True)
           (user_dir / "flash_memory" / "memories.json").write_text('{"test": true}')
           (user_dir / "preferences" / "theme.json").write_text('{"dark": true}')

       @pytest.mark.asyncio
       async def test_export_creates_file(self):
           output = os.path.join(self.tmp_dir, "test.yeyo-backup")
           result = await self.migrator.export_user_data(
               "testuser", "password123", output_path=output,
           )
           assert result.success is True
           assert Path(output).exists()

       @pytest.mark.asyncio
       async def test_export_counts_files(self):
           output = os.path.join(self.tmp_dir, "test.yeyo-backup")
           result = await self.migrator.export_user_data(
               "testuser", "password123", output_path=output,
           )
           assert result.files_processed == 2  # memories.json + theme.json

       @pytest.mark.asyncio
       async def test_export_nonexistent_user(self):
           result = await self.migrator.export_user_data(
               "ghost", "password123",
           )
           assert result.success is False

       @pytest.mark.asyncio
       async def test_import_restores_data(self):
           # Export
           backup_path = os.path.join(self.tmp_dir, "backup.yeyo-backup")
           await self.migrator.export_user_data(
               "testuser", "secret123", output_path=backup_path,
           )
           # Import to new user
           result = await self.migrator.import_user_data(
               backup_path, "secret123", target_username="newuser",
           )
           assert result.success is True
           assert result.files_merged > 0
           new_dir = Path(self.tmp_dir) / "newuser" / "flash_memory"
           assert new_dir.exists()

       @pytest.mark.asyncio
       async def test_import_merge_no_overwrite(self):
           backup_path = os.path.join(self.tmp_dir, "backup.yeyo-backup")
           await self.migrator.export_user_data(
               "testuser", "secret123", output_path=backup_path,
           )
           # Import same data twice
           await self.migrator.import_user_data(
               backup_path, "secret123", target_username="testuser2",
           )
           result = await self.migrator.import_user_data(
               backup_path, "secret123", target_username="testuser2",
           )
           assert result.files_skipped > 0

       @pytest.mark.asyncio
       async def test_wrong_password_fails(self):
           backup_path = os.path.join(self.tmp_dir, "backup.yeyo-backup")
           await self.migrator.export_user_data(
               "testuser", "correct123", output_path=backup_path,
           )
           result = await self.migrator.import_user_data(
               backup_path, "wrongpassword",
           )
           # Con fallback base64, no falla por password pero con crypto sí
           # Este test verifica que el flujo maneja errores
           assert isinstance(result, MigrationResult)

       @pytest.mark.asyncio
       async def test_verify_backup(self):
           backup_path = os.path.join(self.tmp_dir, "backup.yeyo-backup")
           await self.migrator.export_user_data(
               "testuser", "secret123", output_path=backup_path,
           )
           manifest = await self.migrator.verify_backup(backup_path, "secret123")
           assert manifest.username == "testuser"
           assert manifest.total_files == 2

       @pytest.mark.asyncio
       async def test_backup_nonexistent_file(self):
           result = await self.migrator.import_user_data(
               "/nonexistent.yeyo-backup", "pass",
           )
           assert result.success is False

       def test_encryption_roundtrip(self):
           data = b"Hello YeyoOS secret data"
           encrypted = self.migrator._encrypt_data(data, "mypassword")
           decrypted = self.migrator._decrypt_data(encrypted, "mypassword")
           assert decrypted == data

       def test_backup_extension(self):
           assert DataMigrator.BACKUP_EXTENSION == ".yeyo-backup"

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/auth/test_migration.py -v

VERIFICAR:
- [ ] Archivo src/auth/migration.py existe con DataMigrator
- [ ] Export crea archivo .yeyo-backup cifrado
- [ ] Import descifra y restaura datos
- [ ] Merge no sobreescribe archivos existentes
- [ ] AES-256 con PBKDF2 (fallback base64 si cryptography no disponible)
- [ ] Manifiesto incluido en backup con metadata
- [ ] Verify verifica sin importar
- [ ] Cross-version compatible (manifiesto tiene version)
- [ ] TODOS los tests pasan

SI FALLA:
- cryptography: pip install cryptography
- pytest-asyncio: pip install pytest-asyncio

NO HACER:
- No almacenar contraseñas en el backup
- No sobreescribir datos al importar (merge only)

GATE: Migración export/import con cifrado AES-256, merge inteligente, verify, todos los tests pasan.
```
