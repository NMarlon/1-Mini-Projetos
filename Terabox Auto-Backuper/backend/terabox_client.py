"""Cliente para interagir com a API do Terabox.

Regras importantes aprendidas com o bug das pastas duplicadas:

- Pastas: ``rtype=0`` (não renomear em conflito).
- Arquivo novo: ``rtype=0``.
- Substituição intencional: ``rtype=3`` (sobrescrever).
- Nunca usar ``rtype=1`` (renomeia e cria duplicatas).
- Todos os caminhos enviados à API são POSIX (barra ``/``).
"""

import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from typing import List, Optional, Set, Tuple
from urllib.parse import quote_plus

import httpx

from backend.config import (
    BASE_URL_TB,
    USER_AGENT,
    APP_ID,
    CHANNEL,
    CLIENT_TYPE,
    PROJECT_DIR,
)
from backend.paths import join_remote, normalize_local, normalize_remote, remote_parent
from backend.process_utils import run_hidden
from backend.sync_plan import LocalEntry, RemoteEntry, RemoteSnapshot

# Erros de autenticação/jsToken conhecidos
AUTH_ERRNOS = {-6, 4000023, 400141, 450016}

# Alguns códigos usados pelo Terabox para "já existe"
EXISTS_ERRNOS = {-8, 31061, 31062}

# Diretório/arquivo inexistente (a API varia entre -7 e -9)
MISSING_ERRNOS = {-7, -9}

API_PAGE_SIZE = 1000
API_PACE_SECONDS = 0.12
MAX_LIST_PAGES = 1000

SKIP_FILE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
SKIP_FILE_SUFFIXES = (".tmp", ".part", ".crdownload", "~")


class TeraboxError(Exception):
    """Erro genérico da API do Terabox."""

    def __init__(self, message: str, errno: Optional[int] = None, transient: bool = False):
        super().__init__(message)
        self.errno = errno
        self.transient = transient


class TeraboxAuthError(TeraboxError):
    """Cookies/jsToken inválidos ou expirados."""


class TeraboxTransientError(TeraboxError):
    """Erro temporário (rede, 5xx, rate limit). Pode ser repetido."""


class TeraboxClient:
    """Cliente assíncrono para a API do Terabox."""

    def __init__(self, cookies: dict, jstoken: str, token_issued_at: Optional[float] = None):
        self.cookies = dict(cookies or {})
        self.jstoken = jstoken
        self.cookies_str = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        self._token_issued_at = float(token_issued_at or time.time())
        self._last_api_call = 0.0
        self._client = httpx.AsyncClient(
            base_url=BASE_URL_TB,
            headers={"User-Agent": USER_AGENT},
            cookies=self.cookies,
            timeout=httpx.Timeout(60.0, connect=20.0),
            follow_redirects=True,
        )

    async def close(self):
        await self._client.aclose()

    # ── Helpers internos ──

    def _params(self, extra: dict = None) -> dict:
        p = {
            "app_id": APP_ID,
            "web": "1",
            "channel": CHANNEL,
            "clienttype": CLIENT_TYPE,
            "jsToken": self.jstoken,
        }
        if extra:
            p.update(extra)
        return p

    async def _pace(self):
        now = time.monotonic()
        elapsed = now - self._last_api_call
        if elapsed < API_PACE_SECONDS:
            await asyncio.sleep(API_PACE_SECONDS - elapsed)
        self._last_api_call = time.monotonic()

    @staticmethod
    def _errmsg(data: dict) -> str:
        return str(
            data.get("errmsg")
            or data.get("error_msg")
            or data.get("message")
            or data.get("error")
            or ""
        )

    def _check_auth(self, data: dict):
        errno = data.get("errno")
        msg = self._errmsg(data).lower()
        if errno in AUTH_ERRNOS:
            raise TeraboxAuthError(
                f"Autenticação/jsToken inválido (errno={errno}): {msg}",
                errno=errno,
            )
        if "not login" in msg or "token" in msg and "invalid" in msg:
            raise TeraboxAuthError(f"Autenticação inválida: {msg}", errno=errno)

    async def _request_json(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> Tuple[dict, str]:
        await self._pace()
        try:
            resp = await self._client.request(
                method, path, params=params, data=data, headers=headers
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
            raise TeraboxTransientError(f"Falha de rede: {exc}", transient=True) from exc
        except httpx.HTTPError as exc:
            raise TeraboxTransientError(f"Erro HTTP: {exc}", transient=True) from exc

        if resp.status_code in (401, 403):
            raise TeraboxAuthError(f"HTTP {resp.status_code} na API do Terabox")
        if resp.status_code == 429 or resp.status_code >= 500:
            raise TeraboxTransientError(f"HTTP {resp.status_code} na API do Terabox", transient=True)

        try:
            payload = resp.json()
        except Exception as exc:
            raise TeraboxTransientError(
                f"Resposta inválida da API (HTTP {resp.status_code})", transient=True
            ) from exc

        self._check_auth(payload)
        return payload, resp.text

    async def ensure_token(self, max_age_seconds: int = 240):
        """Renova o jsToken antes de ele expirar (TTL real ~300s)."""
        if time.time() - self._token_issued_at < max_age_seconds:
            return
        await self.refresh_token()

    async def refresh_token(self):
        """Re-raspa o jsToken usando os cookies atuais."""
        from backend import auth

        token = await auth.refresh_jstoken(self.cookies)
        if not token:
            raise TeraboxAuthError(
                "Não foi possível renovar o jsToken. Reconecte ao Terabox."
            )
        self.jstoken = token
        self._token_issued_at = time.time()

    # ── Quota / VIP ──

    async def get_quota(self) -> dict:
        data, _ = await self._request_json(
            "GET", "/api/quota", params={"checkfree": "1"}
        )
        return data

    async def is_vip(self) -> bool:
        try:
            data, _ = await self._request_json(
                "GET",
                "/rest/2.0/membership/proxy/user",
                params={"method": "query"},
            )
            return data.get("data", {}).get("member_info", {}).get("is_vip", 0) == 1
        except Exception:
            return False

    # ── Listagem remota ──

    async def list_directory_page(self, remote_dir: str, page: int = 1, num: int = API_PAGE_SIZE) -> Tuple[List[dict], int]:
        """Lista uma página de um diretório. Retorna (itens, errno)."""
        remote_dir = normalize_remote(remote_dir)
        data, _ = await self._request_json(
            "GET",
            "/api/list",
            params=self._params(
                {
                    "dir": remote_dir,
                    "num": str(num),
                    "page": str(page),
                    "order": "time",
                    "desc": "1",
                    "showempty": "0",
                }
            ),
        )
        errno = data.get("errno", 0)
        if errno in MISSING_ERRNOS:
            return [], -7
        if errno not in (0, None):
            raise TeraboxError(
                f"Falha ao listar {remote_dir}: errno={errno} {self._errmsg(data)}",
                errno=errno,
            )
        return data.get("list") or [], 0

    async def fetch_remote_snapshot(self, root: str) -> RemoteSnapshot:
        """Lista recursivamente todo o conteúdo de uma pasta remota.

        Pagina cada diretório até o fim (o limite antigo de 1000 itens fazia
        o sync "esquecer" arquivos em pastas grandes).
        """
        root = normalize_remote(root)
        snapshot = RemoteSnapshot()
        queue: List[str] = [root]
        visited: Set[str] = set()

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            page = 1
            while page <= MAX_LIST_PAGES:
                items, errno = await self.list_directory_page(current, page=page)
                if errno == -7:
                    break
                for entry in items:
                    name = str(entry.get("server_filename") or "")
                    raw_path = entry.get("path")
                    path = normalize_remote(raw_path) if raw_path else join_remote(current, name)
                    is_dir = int(entry.get("isdir") or 0) == 1
                    if is_dir:
                        snapshot.dirs.add(path)
                        if path not in visited:
                            queue.append(path)
                    else:
                        md5 = entry.get("md5") or entry.get("md5sum")
                        try:
                            size = int(entry.get("size") or 0)
                        except (TypeError, ValueError):
                            size = 0
                        snapshot.files[path] = RemoteEntry(
                            path=path,
                            name=name,
                            size=size,
                            md5=str(md5).lower() if md5 else None,
                            is_dir=False,
                            mtime=entry.get("server_mtime"),
                        )
                if len(items) < API_PAGE_SIZE:
                    break
                page += 1

        return snapshot

    async def find_remote_file(self, remote_path: str) -> Optional[RemoteEntry]:
        """Busca um arquivo exato pelo caminho, paginando o diretório pai."""
        remote_path = normalize_remote(remote_path)
        parent = remote_parent(remote_path)
        page = 1
        while page <= MAX_LIST_PAGES:
            items, errno = await self.list_directory_page(parent, page=page)
            if errno == -7:
                return None
            for entry in items:
                name = str(entry.get("server_filename") or "")
                raw_path = entry.get("path")
                path = normalize_remote(raw_path) if raw_path else join_remote(parent, name)
                if path != remote_path:
                    continue
                if int(entry.get("isdir") or 0) == 1:
                    return RemoteEntry(path=path, name=name, is_dir=True, size=0)
                md5 = entry.get("md5") or entry.get("md5sum")
                try:
                    size = int(entry.get("size") or 0)
                except (TypeError, ValueError):
                    size = 0
                return RemoteEntry(
                    path=path,
                    name=name,
                    size=size,
                    md5=str(md5).lower() if md5 else None,
                    is_dir=False,
                    mtime=entry.get("server_mtime"),
                )
            if len(items) < API_PAGE_SIZE:
                return None
            page += 1
        return None

    # ── Criação de pastas/arquivos ──

    async def create_directory(self, remote_path: str) -> bool:
        """Cria uma pasta sem renomear em conflito (``rtype=0``)."""
        remote_path = normalize_remote(remote_path)
        data, _ = await self._request_json(
            "POST",
            "/api/create",
            params=self._params({"isdir": "1", "rtype": "0"}),
            data={"path": remote_path, "size": "0", "isdir": "1"},
        )
        errno = data.get("errno", 0)
        if errno in (0, None):
            return True
        msg = self._errmsg(data)
        if "exist" in msg.lower() or "已存在" in msg or errno in EXISTS_ERRNOS:
            return True
        raise TeraboxError(
            f"Falha ao criar pasta {remote_path}: errno={errno} {msg}",
            errno=errno,
        )

    async def precreate_file(self, cloud_path: str, md5_json: str) -> dict:
        """Pré-cria um upload.

        Retorna ``{"ok": True, "uploadid": ...}`` ou
        ``{"ok": False, "errno": ..., "error": ...}``.
        """
        cloud_path = normalize_remote(cloud_path)
        target = remote_parent(cloud_path)
        target_path = "/" if target == "/" else target + "/"
        data, text = await self._request_json(
            "POST",
            "/api/precreate",
            headers={
                "Origin": BASE_URL_TB,
                "Referer": BASE_URL_TB + "/main?category=all",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "app_id": APP_ID,
                "web": "1",
                "channel": CHANNEL,
                "clienttype": "0",
                "jsToken": self.jstoken,
                "path": cloud_path,
                "autoinit": "1",
                "target_path": target_path,
                "block_list": md5_json,
            },
        )
        uploadid = data.get("uploadid")
        if uploadid:
            return {"ok": True, "uploadid": str(uploadid), "errno": 0}

        errno = data.get("errno")
        msg = self._errmsg(data)
        lower = (text or "").lower()
        if "need verify" in lower or "need verify" in msg.lower():
            return {
                "ok": False,
                "errno": errno,
                "error": "O Terabox pediu verificação extra (need verify). Tente novamente mais tarde.",
            }
        if errno in (0, None):
            return {
                "ok": False,
                "errno": 0,
                "error": "precreate não retornou uploadid (arquivo já existente?)",
                "already_exists": True,
            }
        return {
            "ok": False,
            "errno": errno,
            "error": f"precreate falhou: errno={errno} {msg}",
        }

    async def create_file(
        self,
        cloud_path: str,
        uploadid: str,
        size: int,
        md5_json: str,
        overwrite: bool = False,
    ) -> dict:
        """Finaliza a criação do arquivo no cloud.

        ``overwrite=True`` usa ``rtype=3`` para substituir o arquivo no mesmo
        caminho. ``overwrite=False`` usa ``rtype=0``.
        """
        cloud_path = normalize_remote(cloud_path)
        target = remote_parent(cloud_path)
        target_path = "/" if target == "/" else target + "/"
        data, _ = await self._request_json(
            "POST",
            "/api/create",
            params=self._params(
                {"isdir": "0", "rtype": "3" if overwrite else "0"}
            ),
            data={
                "path": cloud_path,
                "uploadid": uploadid,
                "target_path": target_path,
                "size": str(int(size)),
                "block_list": md5_json,
            },
        )
        errno = data.get("errno", 0)
        if errno not in (0, None):
            raise TeraboxError(
                f"Falha ao criar arquivo {cloud_path}: errno={errno} {self._errmsg(data)}",
                errno=errno,
            )
        return data

    # ── Upload via curl ──

    async def upload_file(
        self,
        local_path: str,
        cloud_filename: str,
        uploadid: str,
        md5hash: str,
        partseq: int = 0,
    ) -> str:
        """Upload de arquivo/chunk via curl. Retorna md5 ou 'failed'/'mismatch'."""
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, self._curl_upload, local_path, cloud_filename, uploadid, partseq
            )
            if result is None:
                return "failed"
            uresp = json.loads(result)
            if "error_code" in uresp:
                return "failed"
            if str(uresp.get("md5", "")).lower() == str(md5hash).lower():
                return str(uresp["md5"])
            return "mismatch"
        except Exception:
            return "failed"

    def _curl_upload(
        self, local_path: str, cloud_filename: str, uploadid: str, partseq: int
    ) -> Optional[str]:
        """Executa curl para upload (bloqueante, roda em executor)."""
        curl_exe = "curl"
        local_curl = PROJECT_DIR / "curl" / "bin" / "curl.exe"
        if local_curl.exists():
            curl_exe = str(local_curl)
        elif (PROJECT_DIR / "curl.exe").exists():
            curl_exe = str(PROJECT_DIR / "curl.exe")

        cloud_path = cloud_filename
        cmd = [
            curl_exe,
            "-sS",
            "-X",
            "POST",
            "-H",
            f"User-Agent:{USER_AGENT}",
            "-H",
            f"Origin:{BASE_URL_TB}",
            "-H",
            f"Referer:{BASE_URL_TB}/main?category=all",
            "-H",
            "Content-Type:multipart/form-data",
            "-b",
            self.cookies_str,
            "-F",
            f'file=@"{local_path}"',
            "--connect-timeout",
            "30",
            "--max-time",
            "1800",
            f"{BASE_URL_TB.replace('www', 'c-jp')}:443/rest/2.0/pcs/superfile2?"
            f"method=upload&type=tmpfile&app_id={APP_ID}&path={quote_plus(cloud_path)}&"
            f"uploadid={uploadid}&partseq={partseq}",
        ]
        try:
            out = run_hidden(cmd, capture_output=True, check=True, timeout=1800)
            return out.stdout.decode("utf-8", errors="replace")
        except Exception:
            return None

    # ── Download (para processo reverso) ──

    async def get_download_link(self, remote_path: str) -> Optional[str]:
        """Obtém link de download de um arquivo remoto.

        O endpoint mais confiável para conta própria é ``/api/filemetas`` com
        ``target=[path]`` e ``dlink=1``. O ``/api/download`` antigo exige
        ``fidlist`` + assinatura e retornava errno=2.
        """
        path = normalize_remote(remote_path)
        try:
            await self.ensure_token()
            data, _ = await self._request_json(
                "GET",
                "/api/filemetas",
                params=self._params({"target": json.dumps([path]), "dlink": "1"}),
            )
            for item in data.get("info") or []:
                link = item.get("dlink")
                if isinstance(link, str) and link:
                    if link.startswith("//"):
                        link = "https:" + link
                    return link
        except Exception:
            pass

        # Fallback: /rest/2.0/pcs/file responde 302 com Location
        try:
            await self._pace()
            resp = await self._client.get(
                "/rest/2.0/pcs/file",
                params={
                    "method": "download",
                    "app_id": APP_ID,
                    "path": path,
                    "jsToken": self.jstoken,
                },
                follow_redirects=False,
            )
            if resp.status_code in (301, 302, 303, 307, 308):
                link = resp.headers.get("location")
                if link:
                    return link
        except Exception:
            pass
        return None

    async def download_file(self, remote_path: str, local_path: str) -> bool:
        """Baixa um arquivo remoto para o caminho local (sem deixar parcial)."""
        link = await self.get_download_link(remote_path)
        if not link:
            return False
        tmp_path = local_path + ".part"
        try:
            async with self._client.stream("GET", link) as resp:
                if resp.status_code != 200:
                    return False
                Path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
                with open(tmp_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
            os.replace(tmp_path, local_path)
            return True
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            return False

    # ── Delete remoto ──

    async def delete_remote(self, remote_path: str) -> bool:
        """Deleta um arquivo ou pasta remota."""
        try:
            data, _ = await self._request_json(
                "POST",
                "/api/filemanager",
                params=self._params({"opera": "delete", "async": "0"}),
                data={"filelist": json.dumps([normalize_remote(remote_path)])},
            )
            return data.get("errno") == 0
        except Exception:
            return False

    # ── Helpers de arquivo ──

    @staticmethod
    def compute_md5(file_path: str) -> str:
        h = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _should_skip_file(name: str) -> bool:
        if name in SKIP_FILE_NAMES:
            return True
        if name.startswith(".chunk_") or name.startswith("~$"):
            return True
        if name.endswith(SKIP_FILE_SUFFIXES):
            return True
        return False

    @staticmethod
    def collect_local_entries(
        local_path: str, include_subfolders: bool = True
    ) -> Tuple[List[LocalEntry], List[str], List[dict]]:
        """Varre uma pasta (ou arquivo) local.

        Retorna ``(arquivos, diretorios_relativos, erros)``. Erros de
        permissão não são mais engolidos silenciosamente.
        """
        local_path = normalize_local(local_path)
        files: List[LocalEntry] = []
        dirs: List[str] = []
        errors: List[dict] = []

        if os.path.isfile(local_path):
            try:
                st = os.stat(local_path)
                files.append(
                    LocalEntry(
                        rel_path=os.path.basename(local_path),
                        full_path=local_path,
                        size=st.st_size,
                        mtime_ns=st.st_mtime_ns,
                    )
                )
            except OSError as exc:
                errors.append({"file": local_path, "error": str(exc)})
            return files, dirs, errors

        if not os.path.isdir(local_path):
            errors.append({"file": local_path, "error": "origem não existe ou não é pasta/arquivo"})
            return files, dirs, errors

        if not include_subfolders:
            try:
                for item in os.scandir(local_path):
                    if not item.is_file(follow_symlinks=False):
                        continue
                    if TeraboxClient._should_skip_file(item.name):
                        continue
                    try:
                        st = item.stat(follow_symlinks=False)
                    except OSError as exc:
                        errors.append({"file": item.path, "error": str(exc)})
                        continue
                    files.append(
                        LocalEntry(
                            rel_path=item.name,
                            full_path=item.path,
                            size=st.st_size,
                            mtime_ns=st.st_mtime_ns,
                        )
                    )
            except OSError as exc:
                errors.append({"file": local_path, "error": str(exc)})
            return files, dirs, errors

        def _onerror(exc):
            errors.append({"file": getattr(exc, "filename", local_path), "error": str(exc)})

        for root, dirnames, filenames in os.walk(
            local_path, topdown=True, followlinks=False, onerror=_onerror
        ):
            # Evitar loops com links simbólicos/junções
            dirnames[:] = [
                d for d in dirnames if not os.path.islink(os.path.join(root, d))
            ]

            rel_root = os.path.relpath(root, local_path)
            if rel_root != ".":
                dirs.append(rel_root.replace("\\", "/"))

            for name in filenames:
                if TeraboxClient._should_skip_file(name):
                    continue
                full_path = os.path.join(root, name)
                if os.path.islink(full_path):
                    continue
                try:
                    st = os.stat(full_path)
                except OSError as exc:
                    errors.append({"file": full_path, "error": str(exc)})
                    continue
                rel_path = os.path.relpath(full_path, local_path).replace("\\", "/")
                files.append(
                    LocalEntry(
                        rel_path=rel_path,
                        full_path=full_path,
                        size=st.st_size,
                        mtime_ns=st.st_mtime_ns,
                    )
                )

        return files, dirs, errors
