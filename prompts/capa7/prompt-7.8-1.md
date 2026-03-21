## ═══════════════════════════════════════
## MICRO-FASE 7.8 — Multi-User System
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.8-1 [VSCODE] — Crear sistema multi-usuario

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.8 de Capa 7 (Evolución): crear el sistema de soporte multi-usuario con roles, sesiones aisladas y Flash Memory por usuario.

CONTEXTO:
- Capas 0-6 completadas + micro-fases 7.0-7.7
- Cada usuario tiene: su propia Flash Memory, preferencias, configuración de nodos
- Recursos compartidos: GPU (via scheduler), configuración del sistema
- Roles: admin (gestiona todo), user (uso normal), guest (acceso limitado)
- Login: contraseña local cifrada con argon2
- Sesiones con aislamiento de datos
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios:
   mkdir -p src/auth
   mkdir -p tests/unit/auth

2. Crear archivo src/auth/__init__.py:

   Ruta: ~/yeyo-os/src/auth/__init__.py
   Contenido:
   from .multi_user import UserManager, User, UserRole, Session

3. Crear archivo src/auth/multi_user.py:

   Ruta: ~/yeyo-os/src/auth/multi_user.py
   Contenido:

   """
   YeyoOS — Multi-User System
   Micro-fase 7.8 — Capa 7: Evolución

   Sistema multi-usuario con roles, sesiones aisladas,
   y Flash Memory independiente por usuario.
   """

   import hashlib
   import json
   import logging
   import secrets
   import uuid
   from datetime import datetime, timedelta
   from enum import Enum
   from pathlib import Path
   from typing import Optional

   from pydantic import BaseModel, Field

   logger = logging.getLogger("yeyo.auth")


   class UserRole(str, Enum):
       """Roles de usuario."""
       ADMIN = "admin"      # Gestiona usuarios, sistema, GPU allocation
       USER = "user"        # Uso normal, Flash Memory propia
       GUEST = "guest"      # Acceso limitado, sin persistencia


   class User(BaseModel):
       """Modelo de usuario de YeyoOS."""
       user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
       username: str = Field(min_length=2, max_length=32)
       display_name: str = ""
       role: UserRole = UserRole.USER
       password_hash: str = ""
       flash_memory_path: str = ""
       preferences: dict = Field(default_factory=dict)
       created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
       last_login: Optional[str] = None
       is_active: bool = True
       gpu_quota_pct: int = Field(default=50, ge=0, le=100)


   class Session(BaseModel):
       """Sesión de usuario activa."""
       session_id: str = Field(default_factory=lambda: secrets.token_hex(32))
       user_id: str
       username: str
       role: UserRole
       created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
       expires_at: str = ""
       is_active: bool = True


   class UserManager:
       """Gestor de usuarios y sesiones de YeyoOS."""

       SESSION_DURATION_HOURS = 24
       GUEST_SESSION_HOURS = 4

       def __init__(self, data_dir: str = "data/users"):
           self.data_dir = Path(data_dir)
           self.data_dir.mkdir(parents=True, exist_ok=True)
           self._users: dict[str, User] = {}
           self._sessions: dict[str, Session] = {}
           self._username_index: dict[str, str] = {}  # username → user_id

       def _hash_password(self, password: str) -> str:
           """Hash de contraseña con argon2 (fallback sha256+salt)."""
           try:
               from argon2 import PasswordHasher
               ph = PasswordHasher()
               return ph.hash(password)
           except ImportError:
               salt = secrets.token_hex(16)
               hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
               return f"sha256:{salt}:{hashed}"

       def _verify_password(self, password: str, password_hash: str) -> bool:
           """Verifica contraseña contra hash."""
           try:
               from argon2 import PasswordHasher
               from argon2.exceptions import VerifyMismatchError
               ph = PasswordHasher()
               try:
                   return ph.verify(password_hash, password)
               except VerifyMismatchError:
                   return False
           except ImportError:
               if password_hash.startswith("sha256:"):
                   parts = password_hash.split(":")
                   if len(parts) == 3:
                       salt, stored_hash = parts[1], parts[2]
                       computed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
                       return computed == stored_hash
               return False

       def create_user(
           self,
           username: str,
           password: str,
           role: UserRole = UserRole.USER,
           display_name: str = "",
       ) -> User:
           """Crea un nuevo usuario."""
           if username in self._username_index:
               raise ValueError(f"Usuario '{username}' ya existe")

           if role == UserRole.GUEST:
               raise ValueError("No se puede crear un usuario guest permanente")

           password_hash = self._hash_password(password)
           flash_memory_path = str(self.data_dir / username / "flash_memory")

           user = User(
               username=username,
               display_name=display_name or username,
               role=role,
               password_hash=password_hash,
               flash_memory_path=flash_memory_path,
           )

           # Crear directorio de datos del usuario
           user_dir = self.data_dir / username
           user_dir.mkdir(parents=True, exist_ok=True)
           (user_dir / "flash_memory").mkdir(exist_ok=True)
           (user_dir / "preferences").mkdir(exist_ok=True)
           (user_dir / "node_configs").mkdir(exist_ok=True)

           self._users[user.user_id] = user
           self._username_index[username] = user.user_id
           self._save_user(user)

           logger.info(f"Usuario creado: {username} (role={role})")
           return user

       def login(self, username: str, password: str) -> Session:
           """Autentica usuario y crea sesión."""
           user_id = self._username_index.get(username)
           if not user_id:
               raise ValueError("Usuario no encontrado")

           user = self._users.get(user_id)
           if not user or not user.is_active:
               raise ValueError("Usuario no activo")

           if not self._verify_password(password, user.password_hash):
               raise ValueError("Contraseña incorrecta")

           # Crear sesión
           duration = timedelta(hours=self.SESSION_DURATION_HOURS)
           expires = datetime.now() + duration

           session = Session(
               user_id=user.user_id,
               username=user.username,
               role=user.role,
               expires_at=expires.isoformat(),
           )

           self._sessions[session.session_id] = session
           user.last_login = datetime.now().isoformat()

           logger.info(f"Login exitoso: {username}")
           return session

       def create_guest_session(self) -> Session:
           """Crea sesión de invitado (limitada, sin persistencia)."""
           duration = timedelta(hours=self.GUEST_SESSION_HOURS)
           expires = datetime.now() + duration

           session = Session(
               user_id="guest",
               username="guest",
               role=UserRole.GUEST,
               expires_at=expires.isoformat(),
           )

           self._sessions[session.session_id] = session
           logger.info("Sesión guest creada")
           return session

       def validate_session(self, session_id: str) -> Optional[Session]:
           """Valida una sesión activa."""
           session = self._sessions.get(session_id)
           if not session or not session.is_active:
               return None

           expires = datetime.fromisoformat(session.expires_at)
           if datetime.now() > expires:
               session.is_active = False
               return None

           return session

       def logout(self, session_id: str) -> bool:
           """Cierra una sesión."""
           session = self._sessions.get(session_id)
           if session:
               session.is_active = False
               logger.info(f"Logout: {session.username}")
               return True
           return False

       def get_user(self, user_id: str) -> Optional[User]:
           return self._users.get(user_id)

       def get_user_by_username(self, username: str) -> Optional[User]:
           user_id = self._username_index.get(username)
           if user_id:
               return self._users.get(user_id)
           return None

       def list_users(self) -> list[User]:
           return list(self._users.values())

       def delete_user(self, admin_session_id: str, target_user_id: str) -> bool:
           """Solo admin puede eliminar usuarios."""
           session = self.validate_session(admin_session_id)
           if not session or session.role != UserRole.ADMIN:
               raise PermissionError("Solo admin puede eliminar usuarios")

           user = self._users.get(target_user_id)
           if not user:
               raise ValueError("Usuario no encontrado")

           if user.role == UserRole.ADMIN:
               admin_count = sum(1 for u in self._users.values() if u.role == UserRole.ADMIN)
               if admin_count <= 1:
                   raise ValueError("No se puede eliminar el último admin")

           user.is_active = False
           del self._username_index[user.username]
           logger.info(f"Usuario eliminado: {user.username}")
           return True

       def update_gpu_quota(
           self, admin_session_id: str, target_user_id: str, quota_pct: int
       ) -> User:
           """Admin configura GPU quota de un usuario."""
           session = self.validate_session(admin_session_id)
           if not session or session.role != UserRole.ADMIN:
               raise PermissionError("Solo admin puede modificar GPU quota")

           user = self._users.get(target_user_id)
           if not user:
               raise ValueError("Usuario no encontrado")

           user.gpu_quota_pct = max(0, min(100, quota_pct))
           logger.info(f"GPU quota actualizado: {user.username} → {quota_pct}%")
           return user

       def _save_user(self, user: User):
           """Persiste datos del usuario."""
           user_file = self.data_dir / user.username / "profile.json"
           safe_data = user.model_dump()
           safe_data.pop("password_hash", None)
           try:
               with open(user_file, 'w') as f:
                   json.dump(safe_data, f, indent=2)
           except Exception as e:
               logger.warning(f"No se pudo guardar usuario: {e}")

4. Crear archivo tests/unit/auth/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/auth/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/auth/test_multi_user.py:

   Ruta: ~/yeyo-os/tests/unit/auth/test_multi_user.py
   Contenido:

   """Tests para Multi-User System — Micro-fase 7.8"""

   import tempfile
   import pytest
   from src.auth.multi_user import (
       UserManager, User, UserRole, Session,
   )


   class TestUserManager:
       """Tests para UserManager."""

       def setup_method(self):
           self.tmp_dir = tempfile.mkdtemp()
           self.manager = UserManager(data_dir=self.tmp_dir)

       def test_create_user(self):
           user = self.manager.create_user("yeyo", "securepass123")
           assert user.username == "yeyo"
           assert user.role == UserRole.USER
           assert user.is_active is True

       def test_create_admin(self):
           user = self.manager.create_user("admin", "adminpass123", role=UserRole.ADMIN)
           assert user.role == UserRole.ADMIN

       def test_create_duplicate_rejected(self):
           self.manager.create_user("yeyo", "pass12345678")
           with pytest.raises(ValueError, match="ya existe"):
               self.manager.create_user("yeyo", "pass12345678")

       def test_create_guest_rejected(self):
           with pytest.raises(ValueError, match="guest"):
               self.manager.create_user("g", "pass12345678", role=UserRole.GUEST)

       def test_login_success(self):
           self.manager.create_user("yeyo", "securepass123")
           session = self.manager.login("yeyo", "securepass123")
           assert session.username == "yeyo"
           assert session.is_active is True

       def test_login_wrong_password(self):
           self.manager.create_user("yeyo", "securepass123")
           with pytest.raises(ValueError, match="Contraseña"):
               self.manager.login("yeyo", "wrongpassword")

       def test_login_unknown_user(self):
           with pytest.raises(ValueError, match="no encontrado"):
               self.manager.login("ghost", "pass12345678")

       def test_session_validation(self):
           self.manager.create_user("yeyo", "securepass123")
           session = self.manager.login("yeyo", "securepass123")
           valid = self.manager.validate_session(session.session_id)
           assert valid is not None
           assert valid.username == "yeyo"

       def test_session_invalid_id(self):
           result = self.manager.validate_session("nonexistent")
           assert result is None

       def test_logout(self):
           self.manager.create_user("yeyo", "securepass123")
           session = self.manager.login("yeyo", "securepass123")
           assert self.manager.logout(session.session_id) is True
           assert self.manager.validate_session(session.session_id) is None

       def test_guest_session(self):
           session = self.manager.create_guest_session()
           assert session.role == UserRole.GUEST
           assert session.username == "guest"

       def test_flash_memory_per_user(self):
           user1 = self.manager.create_user("user1", "pass12345678")
           user2 = self.manager.create_user("user2", "pass12345678")
           assert user1.flash_memory_path != user2.flash_memory_path
           assert "user1" in user1.flash_memory_path
           assert "user2" in user2.flash_memory_path

       def test_admin_delete_user(self):
           admin = self.manager.create_user("admin", "adminpass1234", role=UserRole.ADMIN)
           session = self.manager.login("admin", "adminpass1234")
           user = self.manager.create_user("victim", "pass12345678")
           result = self.manager.delete_user(session.session_id, user.user_id)
           assert result is True

       def test_non_admin_cannot_delete(self):
           self.manager.create_user("user1", "pass12345678")
           session = self.manager.login("user1", "pass12345678")
           self.manager.create_user("user2", "pass12345678")
           user2 = self.manager.get_user_by_username("user2")
           with pytest.raises(PermissionError):
               self.manager.delete_user(session.session_id, user2.user_id)

       def test_cannot_delete_last_admin(self):
           admin = self.manager.create_user("admin", "adminpass1234", role=UserRole.ADMIN)
           session = self.manager.login("admin", "adminpass1234")
           with pytest.raises(ValueError, match="último admin"):
               self.manager.delete_user(session.session_id, admin.user_id)

       def test_admin_update_gpu_quota(self):
           admin = self.manager.create_user("admin", "adminpass1234", role=UserRole.ADMIN)
           session = self.manager.login("admin", "adminpass1234")
           user = self.manager.create_user("user1", "pass12345678")
           updated = self.manager.update_gpu_quota(session.session_id, user.user_id, 25)
           assert updated.gpu_quota_pct == 25

       def test_list_users(self):
           self.manager.create_user("a", "pass12345678")
           self.manager.create_user("b", "pass12345678")
           users = self.manager.list_users()
           assert len(users) == 2

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/auth/test_multi_user.py -v

VERIFICAR:
- [ ] Archivo src/auth/multi_user.py existe con UserManager, User, UserRole, Session
- [ ] Roles: ADMIN, USER, GUEST
- [ ] Flash Memory path aislado por usuario
- [ ] Login con contraseña verificada (argon2 o sha256)
- [ ] Sesiones con expiración
- [ ] Guest session limitada (4h)
- [ ] Admin puede: eliminar usuarios, cambiar GPU quota
- [ ] No admin NO puede eliminar usuarios
- [ ] No se puede eliminar último admin
- [ ] Datos de usuario persistidos en disco
- [ ] TODOS los tests pasan

SI FALLA:
- argon2: pip install argon2-cffi
- pytest-asyncio: pip install pytest-asyncio

NO HACER:
- No almacenar contraseñas en texto plano
- No permitir guest crear datos persistentes
- No permitir escalar privilegios sin admin

GATE: Multi-user con roles, sesiones, Flash Memory aislada, admin management, todos los tests pasan.
```
