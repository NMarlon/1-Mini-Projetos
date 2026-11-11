"""Autenticação: extração automática de cookies + entrada manual."""

import re
import json
import os
import ctypes
import ctypes.wintypes
import tempfile
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

import httpx
from backend.config import BASE_URL_TB, USER_AGENT, JSTOKEN_TTL_SECONDS
from backend import database
from backend.process_utils import run_hidden

REQUIRED_COOKIES = ["ndus"]
OPTIONAL_COOKIES = ["csrfToken", "browserid", "lang", "ndut_fmt"]
TERABOX_DOMAINS = (".terabox.com", "www.terabox.com", ".terabox1024.com", "www.terabox1024.com")

ROOKIE_BROWSERS = {
    "chrome": "chrome",
    "edge": "edge",
    "firefox": "firefox",
    "brave": "brave",
    "arc": "arc",
    "opera": "opera",
    "vivaldi": "vivaldi",
}


# ── Helpers de cookie (suporta Cookie objects e dicts) ──

def _cookie_attr(cookie, attr: str, default=None):
    if isinstance(cookie, dict):
        return cookie.get(attr, default)
    return getattr(cookie, attr, default)


def _filter_cookies(cookie_jar) -> Dict[str, str]:
    """Filtra cookies do Terabox. Aceita lista de Cookies ou dicts."""
    cookies = {}
    for cookie in cookie_jar:
        domain = (_cookie_attr(cookie, "domain") or "").lower()
        name = _cookie_attr(cookie, "name")
        if any(d in domain for d in TERABOX_DOMAINS):
            if name in (REQUIRED_COOKIES + OPTIONAL_COOKIES):
                cookies[name] = _cookie_attr(cookie, "value")
    return cookies


# ── Dia browser (MSIX/Windows Store) ──

def _find_dia_user_data_dirs() -> List[Path]:
    """Localiza diretórios User Data do Dia (MSIX e instalação tradicional)."""
    dirs = []
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    # MSIX / Windows Store: %LOCALAPPDATA%\Packages\TheBrowserCompany.Dia_*\LocalCache\Local\Dia\User Data
    packages = local / "Packages"
    if packages.exists():
        try:
            for pkg in packages.iterdir():
                if pkg.name.lower().startswith("thebrowsercompany.dia"):
                    ud = pkg / "LocalCache" / "Local" / "Dia" / "User Data"
                    if ud.exists():
                        dirs.append(ud)
        except OSError:
            pass
    # Instalação tradicional
    for ud in [
        local / "Dia" / "User Data",
        Path(os.environ.get("APPDATA", "")) / "Dia" / "User Data",
    ]:
        if ud.exists():
            dirs.append(ud)
    return dirs


def _find_dia_profiles() -> List[Dict]:
    """Lista perfis do Dia sem abrir/fechar o navegador."""
    profiles = []
    for user_data in _find_dia_user_data_dirs():
        try:
            for prof_dir in user_data.iterdir():
                if not prof_dir.is_dir():
                    continue
                cookie_file = prof_dir / "Network" / "Cookies"
                if not cookie_file.exists():
                    cookie_file = prof_dir / "Cookies"
                if cookie_file.exists():
                    profiles.append({
                        "name": prof_dir.name,
                        "path": str(cookie_file),
                        "is_default": prof_dir.name == "Default",
                    })
        except OSError:
            continue
    # Remover duplicatas
    seen = set()
    unique = []
    for p in profiles:
        if p["path"] not in seen:
            seen.add(p["path"])
            unique.append(p)
    return unique


# ── Cópia de arquivo bloqueado (Windows share flags) ──

GENERIC_READ = 0x80000000
OPEN_EXISTING = 3
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateFileW.argtypes = [
    ctypes.wintypes.LPCWSTR, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD,
    ctypes.c_void_p, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD, ctypes.wintypes.HANDLE,
]
_kernel32.CreateFileW.restype = ctypes.wintypes.HANDLE
_kernel32.ReadFile.argtypes = [
    ctypes.wintypes.HANDLE, ctypes.c_void_p, ctypes.wintypes.DWORD,
    ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.c_void_p,
]
_kernel32.ReadFile.restype = ctypes.wintypes.BOOL
_kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]


def _copy_file_shared(src: str, dst: str):
    """Copia arquivo mesmo que outro processo o tenha aberto (share flags)."""
    handle = _kernel32.CreateFileW(
        src, GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None, OPEN_EXISTING, 0, None,
    )
    if not handle or handle == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(), f"Não foi possível abrir {src}")
    try:
        chunks = []
        buf = ctypes.create_string_buffer(1024 * 1024)
        n = ctypes.wintypes.DWORD(0)
        while True:
            ok = _kernel32.ReadFile(handle, buf, len(buf), ctypes.byref(n), None)
            if not ok:
                raise OSError(ctypes.get_last_error(), f"Falha ao ler {src}")
            if n.value == 0:
                break
            chunks.append(buf.raw[:n.value])
        with open(dst, "wb") as f:
            f.write(b"".join(chunks))
    finally:
        _kernel32.CloseHandle(handle)


def _dia_running() -> bool:
    try:
        out = run_hidden(
            ["tasklist", "/FI", "IMAGENAME eq Dia.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        return "Dia.exe" in out
    except Exception:
        return False


def _close_dia(timeout: int = 15) -> bool:
    """Fecha o Dia graciosamente (fecha janelas principais)."""
    try:
        run_hidden(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process Dia -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }"],
            capture_output=True, text=True, timeout=20,
        )
    except Exception:
        pass
    start = time.time()
    while time.time() - start < timeout:
        if not _dia_running():
            return True
        time.sleep(0.5)
    # Forçar fechamento se ainda estiver aberto
    try:
        run_hidden(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process Dia -ErrorAction SilentlyContinue | Stop-Process -Force"],
            capture_output=True, text=True, timeout=20,
        )
        time.sleep(1)
    except Exception:
        pass
    return not _dia_running()


def _start_dia() -> bool:
    """Reabre o Dia, já apontando para a UI do app."""
    try:
        from backend.config import HOST, PORT
        app_url = f"http://{HOST}:{PORT}"
        # Executável real do pacote MSIX: TheBrowserCompany.Dia_<versao>_<arch>__<hash>
        apps_dir = Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "WindowsApps"
        if apps_dir.exists():
            matches = list(apps_dir.glob("TheBrowserCompany.Dia_*"))
            # Ordenar por versão (mais recente) e preferir x64
            matches.sort(key=lambda p: p.name, reverse=True)
            for pkg_dir in matches:
                exe = pkg_dir / "Dia.exe"
                if exe.exists():
                    subprocess.Popen([str(exe), app_url], close_fds=True)
                    return True
        # Fallback: atalho do menu iniciar (abre sem URL)
        subprocess.Popen(
            ["explorer.exe", "shell:AppsFolder\\TheBrowserCompany.Dia_ttt1ap7aakyb4!Dia"],
            close_fds=True,
        )
        return True
    except Exception:
        return False


def _read_dia_cookies(cookie_path: str) -> Optional[Dict[str, str]]:
    """Lê cookies de um arquivo do Dia (sem fechar o navegador)."""
    try:
        import rookie_cookies
    except ImportError:
        return None

    cookie_file = Path(cookie_path)
    profile_dir = cookie_file.parent.parent  # .../Network/Cookies -> profile
    user_data_dir = profile_dir.parent
    local_state = user_data_dir / "Local State"

    tmpdir = Path(tempfile.mkdtemp())
    try:
        tmp_cookies = tmpdir / "Cookies"
        _copy_file_shared(str(cookie_file), str(tmp_cookies))
        kwargs = {}
        if local_state.exists():
            tmp_state = tmpdir / "Local State"
            _copy_file_shared(str(local_state), str(tmp_state))
            kwargs["local_state_path"] = str(tmp_state)
        jar = rookie_cookies.from_path(str(tmp_cookies), **kwargs)
        return _filter_cookies(list(jar))
    except Exception:
        return None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _extract_dia_cookies_sync(profile: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Extrai cookies do Dia (fecha e reabre se necessário)."""
    profiles = _find_dia_profiles()
    if profile:
        profiles = [p for p in profiles if p["name"] == profile]
    if not profiles:
        return None

    # Primeiro tentar sem fechar o navegador (funciona se o Dia estiver fechado)
    for dp in profiles:
        cookies = _read_dia_cookies(dp["path"])
        if cookies and "ndus" in cookies:
            return cookies

    # Se falhou, o navegador provavelmente está aberto -> fechar, ler, reabrir
    was_running = _dia_running()
    if not was_running:
        return None

    if not _close_dia():
        return None

    try:
        time.sleep(1)
        for dp in profiles:
            cookies = _read_dia_cookies(dp["path"])
            if cookies and "ndus" in cookies:
                return cookies
        return None
    finally:
        _start_dia()


# ── Perfis de navegadores ──

def list_browser_profiles(browser: str) -> List[Dict]:
    """Lista perfis disponíveis de um navegador."""
    profiles = []
    try:
        import rookie_cookies
    except ImportError:
        return profiles

    if browser in ("chrome", "edge", "firefox", "brave", "arc"):
        rookie_name = ROOKIE_BROWSERS.get(browser, browser)
        try:
            profiles_func = getattr(rookie_cookies, f"{rookie_name}_profiles", None)
            if profiles_func:
                for prof in profiles_func():
                    p = prof.get("profile", {}) if isinstance(prof, dict) else {}
                    profiles.append({
                        "name": p.get("display_name", "Unknown"),
                        "path": (p.get("path", "") or "").replace("\\\\?\\", ""),
                        "is_default": prof.get("is_default", False),
                    })
            else:
                # Fallback: perfil único
                profiles.append({"name": "Default", "path": "", "is_default": True})
        except Exception:
            pass

    elif browser == "dia":
        for dp in _find_dia_profiles():
            profiles.append({
                "name": dp["name"],
                "path": dp["path"],
                "is_default": dp["is_default"],
            })

    return profiles


def check_profile_has_terabox(browser: str, profile_name: str) -> Optional[bool]:
    """Verifica se um perfil tem cookie ndus. None = desconhecido (arquivo bloqueado)."""
    try:
        import rookie_cookies

        if browser == "dia":
            profiles = [p for p in _find_dia_profiles() if p["name"] == profile_name]
            if not profiles:
                return None
            cookies = _read_dia_cookies(profiles[0]["path"])
            if cookies is None:
                return None  # bloqueado (Dia aberto)
            return "ndus" in cookies

        rookie_name = ROOKIE_BROWSERS.get(browser, browser)
        cookie_jar = rookie_cookies.jar(browser=rookie_name, profile=profile_name)
        cookies = _filter_cookies(cookie_jar)
        return "ndus" in cookies
    except Exception:
        return None


# ── Extração genérica ──

async def extract_cookies_from_browser(browser: str = "auto", profile: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Extrai cookies do Terabox de um navegador/perfil."""
    try:
        import rookie_cookies
    except ImportError:
        return None

    # Dia: fluxo especial (fecha/reabre navegador)
    if browser == "dia":
        import asyncio
        return await asyncio.to_thread(_extract_dia_cookies_sync, profile)

    browsers_to_try = list(ROOKIE_BROWSERS.keys()) if browser == "auto" else [browser]

    for b in browsers_to_try:
        rookie_name = ROOKIE_BROWSERS.get(b)
        if not rookie_name:
            continue

        # Perfil específico
        if profile:
            try:
                cookie_jar = rookie_cookies.jar(browser=rookie_name, profile=profile)
                cookies = _filter_cookies(cookie_jar)
                if "ndus" in cookies:
                    return cookies
            except Exception:
                pass

        # Perfil padrão
        try:
            cookie_jar = rookie_cookies.jar(browser=rookie_name)
            cookies = _filter_cookies(cookie_jar)
            if "ndus" in cookies:
                return cookies
        except Exception:
            pass

        # Todos os perfis
        try:
            profiles_func = getattr(rookie_cookies, f"{rookie_name}_profiles", None)
            if profiles_func:
                for prof in profiles_func():
                    try:
                        name = prof.get("profile", {}).get("display_name", "") if isinstance(prof, dict) else str(prof)
                        cookie_jar = rookie_cookies.jar(browser=rookie_name, profile=name)
                        cookies = _filter_cookies(cookie_jar)
                        if "ndus" in cookies:
                            return cookies
                    except Exception:
                        continue
        except Exception:
            pass

    # Se modo auto e nenhum navegador funcionou, tentar Dia
    if browser == "auto":
        import asyncio
        cookies = await asyncio.to_thread(_extract_dia_cookies_sync, None)
        if cookies:
            return cookies

    return None


async def scrape_jstoken(cookies: Dict[str, str]) -> Optional[str]:
    """Raspa jsToken do HTML da página /main do Terabox."""
    try:
        async with httpx.AsyncClient(
            base_url=BASE_URL_TB,
            headers={"User-Agent": USER_AGENT},
            cookies=cookies,
            timeout=15.0,
            follow_redirects=True,
        ) as client:
            resp = await client.get("/main")
            html = resp.text
            from urllib.parse import unquote
            decoded = unquote(html)
            patterns = [
                r'fn\("([^"]+)"\)',
                r"fn\('([^']+)'\)",
                r'window\.jsToken\s*=\s*["\']([^"\']+)["\']',
                r'"jsToken"\s*:\s*"([^"]+)"',
                r"jsToken\s*=\s*['\"]([^'\"]+)['\"]",
            ]
            for pattern in patterns:
                match = re.search(pattern, decoded)
                if match:
                    token = match.group(1)
                    if "function" not in token and len(token) > 5:
                        return token
            return None
    except Exception:
        return None


async def refresh_jstoken(cookies: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Re-raspa e salva um novo jsToken sem exigir reconexão manual.

    Usado por syncs longos: o token dura ~5 minutos e pode expirar no meio
    de uma fila grande de arquivos.
    """
    row = await database.fetch_one("SELECT * FROM auth_cache ORDER BY id DESC LIMIT 1")
    if cookies is None:
        if not row:
            return None
        try:
            cookies = json.loads(row["cookies_json"])
        except Exception:
            return None
    if not cookies or "ndus" not in cookies:
        return None

    token = await scrape_jstoken(cookies)
    if not token:
        return None

    expires = (datetime.now() + timedelta(seconds=JSTOKEN_TTL_SECONDS)).isoformat()
    if row:
        await database.execute(
            "UPDATE auth_cache SET jstoken = ?, jstoken_expires_at = ?, updated_at = ? WHERE id = ?",
            (token, expires, datetime.now().isoformat(), row["id"]),
        )
    else:
        await database.execute(
            "INSERT INTO auth_cache (browser, cookies_json, jstoken, jstoken_expires_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("manual", json.dumps(cookies), token, expires, datetime.now().isoformat()),
        )
    return token


async def connect(browser: str = "auto", profile: Optional[str] = None) -> dict:
    cookies = await extract_cookies_from_browser(browser, profile)
    if not cookies:
        return {"status": "error", "error": f"Não foi possível extrair cookies do navegador '{browser}'" + (f" (perfil: {profile})" if profile else "") + ". Faça login no Terabox nesse navegador/perfil ou use a opção manual."}

    jstoken = await scrape_jstoken(cookies)
    if not jstoken:
        return {"status": "error", "error": "Não foi possível obter jsToken. Verifique se você está logado no Terabox."}

    await database.execute("DELETE FROM auth_cache")
    expires = (datetime.now() + timedelta(seconds=JSTOKEN_TTL_SECONDS)).isoformat()
    await database.execute(
        "INSERT INTO auth_cache (browser, cookies_json, jstoken, jstoken_expires_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (f"{browser}:{profile}" if profile else browser, json.dumps(cookies), jstoken, expires, datetime.now().isoformat()),
    )

    return {
        "status": "ok",
        "browser": browser,
        "profile": profile,
        "cookies_found": len(cookies),
    }


async def connect_manual(cookies_str: str) -> dict:
    cookies = {}
    for part in cookies_str.split(";"):
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            cookies[key.strip()] = value.strip()

    if "ndus" not in cookies:
        return {"status": "error", "error": "Cookie 'ndus' não encontrado. Verifique se copiou todos os cookies."}

    if "lang" not in cookies:
        cookies["lang"] = "en"

    jstoken = await scrape_jstoken(cookies)
    if not jstoken:
        return {"status": "error", "error": "Não foi possível obter jsToken. Verifique se os cookies são válidos."}

    await database.execute("DELETE FROM auth_cache")
    expires = (datetime.now() + timedelta(seconds=JSTOKEN_TTL_SECONDS)).isoformat()
    await database.execute(
        "INSERT INTO auth_cache (browser, cookies_json, jstoken, jstoken_expires_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("manual", json.dumps(cookies), jstoken, expires, datetime.now().isoformat()),
    )

    return {
        "status": "ok",
        "browser": "manual",
        "cookies_found": len(cookies),
    }


async def get_cached_auth() -> Optional[dict]:
    row = await database.fetch_one("SELECT * FROM auth_cache ORDER BY id DESC LIMIT 1")
    if not row:
        return None
    cookies = json.loads(row["cookies_json"])
    jstoken = row["jstoken"]
    expires = row["jstoken_expires_at"]
    if expires:
        try:
            exp_dt = datetime.fromisoformat(expires)
            if datetime.now() > exp_dt:
                new_token = await scrape_jstoken(cookies)
                if new_token:
                    jstoken = new_token
                    new_expires = (datetime.now() + timedelta(seconds=JSTOKEN_TTL_SECONDS)).isoformat()
                    await database.execute(
                        "UPDATE auth_cache SET jstoken = ?, jstoken_expires_at = ?, updated_at = ? WHERE id = ?",
                        (jstoken, new_expires, datetime.now().isoformat(), row["id"]),
                    )
                else:
                    return None
        except Exception:
            return None
    return {"cookies": cookies, "jstoken": jstoken, "browser": row["browser"]}


async def disconnect():
    await database.execute("DELETE FROM auth_cache")


async def get_status() -> dict:
    auth = await get_cached_auth()
    if not auth:
        return {"authenticated": False, "cookies_found": 0}
    cookies = auth["cookies"]
    row = await database.fetch_one("SELECT jstoken_expires_at FROM auth_cache ORDER BY id DESC LIMIT 1")
    expires_in = None
    if row and row["jstoken_expires_at"]:
        try:
            exp_dt = datetime.fromisoformat(row["jstoken_expires_at"])
            expires_in = max(0, int((exp_dt - datetime.now()).total_seconds()))
        except Exception:
            pass
    return {
        "authenticated": True,
        "browser": auth["browser"],
        "cookies_found": len(cookies),
        "jstoken_expires_in": expires_in,
    }