"""Guardar archivos en un repositorio de GitHub.

- Archivos pequeños (< LIMITE_REPO_MB) se suben como archivos normales del repo
  usando la API Git Data (blob -> tree -> commit), que acepta hasta 100 MB.
- Archivos grandes se suben como "asset" de un Release cuyo tag es el nombre
  del proyecto.
"""

import base64
import json
import logging
import os
import re
import time
import urllib.parse

import requests

log = logging.getLogger(__name__)

API = "https://api.github.com"
UPLOADS = "https://uploads.github.com"
LIMITE_REPO_MB = 90
ARCHIVO_ESTADO = "_estado_bot.json"


class GitHubError(Exception):
    pass


class GitHubStore:
    def __init__(self, token: str, repo: str, branch: str | None = None):
        self.repo = repo.strip().strip("/")
        self._rama_pedida = (branch or "").strip() or None
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {token.strip()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "descargas-bot",
        })
        self._branch = None

    # ------------------------------------------------------------ utilidades
    def _req(self, method, url, ok=(200, 201), **kw):
        if not url.startswith("http"):
            url = f"{API}/repos/{self.repo}{url}"
        kw.setdefault("timeout", 120)
        # Reintenta cortes de conexión y errores temporales de GitHub (5xx, 429)
        for intento in range(4):
            if intento:
                time.sleep(3 * intento)
                if hasattr(kw.get("data"), "seek"):
                    kw["data"].seek(0)
            try:
                r = self.s.request(method, url, **kw)
            except requests.RequestException as e:
                log.warning("GitHub %s %s: %s (intento %d)", method, url, e, intento + 1)
                error = GitHubError(f"No pude conectar con GitHub: {e}")
                continue
            if r.status_code in ok or not (r.status_code >= 500 or r.status_code == 429):
                break
            log.warning("GitHub %s %s -> %s (intento %d)", method, url, r.status_code, intento + 1)
            error = GitHubError(f"GitHub {r.status_code}: {r.text[:200]}")
        else:
            raise error
        if r.status_code not in ok:
            msg = r.text[:300]
            if r.status_code == 401:
                msg = "GITHUB_TOKEN inválido o vencido."
            elif r.status_code == 404 and "/repos/" in url:
                msg = (f"No encuentro el repositorio '{self.repo}' o el token "
                       "no tiene acceso a él.")
            elif r.status_code == 403:
                msg = ("El token no tiene permiso de escritura (necesita "
                       f"'Contents: Read and write'). Detalle: {r.text[:200]}")
            raise GitHubError(f"GitHub {r.status_code}: {msg}")
        return r

    @property
    def branch(self):
        if self._branch is None:
            if self._rama_pedida:
                self._asegurar_rama(self._rama_pedida)
                self._branch = self._rama_pedida
            else:
                self._branch = self._req("GET", "").json().get("default_branch") or "main"
        return self._branch

    def _asegurar_rama(self, rama):
        """Si la rama no existe, la crea vacía (sin el código de la rama principal)."""
        r = self._req("GET", f"/git/ref/heads/{rama}", ok=(200, 404, 409))
        if r.status_code == 200:
            return
        log.info("Creando la rama '%s' en %s", rama, self.repo)
        texto = (f"# Material\n\nArchivos descargados por el bot de Telegram.\n"
                 f"Cada carpeta es un proyecto. Los archivos de más de {LIMITE_REPO_MB} MB "
                 "están en la pestaña Releases.\n")
        blob = self._req("POST", "/git/blobs", json={"content": texto,
                                                      "encoding": "utf-8"}).json()["sha"]
        tree = self._req("POST", "/git/trees", json={"tree": [
            {"path": "README.md", "mode": "100644", "type": "blob", "sha": blob}]}).json()["sha"]
        commit = self._req("POST", "/git/commits", json={
            "message": "Crear rama de material", "tree": tree, "parents": []}).json()["sha"]
        self._req("POST", "/git/refs", json={"ref": f"refs/heads/{rama}", "sha": commit},
                  ok=(201, 422))

    def check(self):
        """Comprueba que el repo existe y que el token puede escribir."""
        info = self._req("GET", "").json()
        perms = info.get("permissions") or {}
        if perms and not perms.get("push", False):
            raise GitHubError("El token puede ver el repositorio pero no escribir en él.")
        return info

    # ------------------------------------------------------------ estado
    def leer_estado(self) -> dict:
        r = self._req("GET", f"/contents/{ARCHIVO_ESTADO}",
                      params={"ref": self.branch}, ok=(200, 404))
        if r.status_code == 404:
            return {}
        try:
            return json.loads(base64.b64decode(r.json()["content"]))
        except Exception:
            return {}

    def guardar_estado(self, estado: dict):
        data = json.dumps(estado, ensure_ascii=False, indent=2).encode()
        self.subir_bytes(ARCHIVO_ESTADO, data, f"Bot: estado {estado}")

    # ------------------------------------------------------------ listados
    def listar_carpeta(self, carpeta: str) -> list[dict]:
        r = self._req("GET", f"/contents/{urllib.parse.quote(carpeta)}",
                      params={"ref": self.branch}, ok=(200, 404))
        if r.status_code == 404:
            return []
        data = r.json()
        if not isinstance(data, list):
            return []
        return [{"name": f["name"], "size": f.get("size", 0), "where": "repo"}
                for f in data if f.get("type") == "file"]

    def _release(self, tag: str, crear: bool):
        r = self._req("GET", f"/releases/tags/{urllib.parse.quote(tag)}", ok=(200, 404))
        if r.status_code == 200:
            return r.json()
        if not crear:
            return None
        return self._req("POST", "/releases", json={
            "tag_name": tag,
            "target_commitish": self.branch,
            "name": tag,
            "body": f"Archivos grandes del proyecto {tag}",
        }).json()

    def listar_release(self, tag: str) -> list[dict]:
        rel = self._release(tag, crear=False)
        if not rel:
            return []
        assets = self._req("GET", f"/releases/{rel['id']}/assets",
                           params={"per_page": 100}).json()
        return [{"name": a["name"], "size": a.get("size", 0), "where": "release"}
                for a in assets]

    def listar_proyecto(self, proyecto: str) -> list[dict]:
        archivos = self.listar_carpeta(proyecto) + self.listar_release(tag_de(proyecto))
        archivos.sort(key=lambda f: f["name"])
        return archivos

    def siguiente_numero(self, proyecto: str) -> int:
        mayor = 0
        for f in self.listar_proyecto(proyecto):
            m = re.match(r"^(\d+)_", f["name"])
            if m:
                mayor = max(mayor, int(m.group(1)))
        return mayor + 1

    # ------------------------------------------------------------ subidas
    def subir_bytes(self, ruta: str, data: bytes, mensaje: str):
        """Crea o reemplaza un archivo en el repo con un commit."""
        for intento in range(6):
            try:
                return self._commit_git_data(ruta, data, mensaje)
            except _RepoVacio:
                return self._commit_contents(ruta, data, mensaje)
            except _Conflicto:
                time.sleep(2 * (intento + 1))
        raise GitHubError("No pude hacer el commit (conflicto repetido).")

    def _commit_git_data(self, ruta, data, mensaje):
        ref = self._req("GET", f"/git/ref/heads/{self.branch}", ok=(200, 404, 409))
        if ref.status_code != 200:
            raise _RepoVacio()
        head = ref.json()["object"]["sha"]
        base_tree = self._req("GET", f"/git/commits/{head}").json()["tree"]["sha"]
        blob = self._req("POST", "/git/blobs", timeout=600, json={
            "content": base64.b64encode(data).decode(), "encoding": "base64",
        }).json()["sha"]
        tree = self._req("POST", "/git/trees", json={
            "base_tree": base_tree,
            "tree": [{"path": ruta, "mode": "100644", "type": "blob", "sha": blob}],
        }).json()["sha"]
        commit = self._req("POST", "/git/commits", json={
            "message": mensaje, "tree": tree, "parents": [head],
        }).json()["sha"]
        r = self._req("PATCH", f"/git/refs/heads/{self.branch}",
                      json={"sha": commit}, ok=(200, 409, 422))
        if r.status_code != 200:
            raise _Conflicto()
        return commit

    def _commit_contents(self, ruta, data, mensaje):
        """Para repos vacíos (sin ningún commit) la API Git Data no funciona."""
        url = f"/contents/{urllib.parse.quote(ruta)}"
        body = {"message": mensaje, "content": base64.b64encode(data).decode()}
        if self._rama_pedida:
            body["branch"] = self._rama_pedida
        prev = self._req("GET", url, params={"ref": body.get("branch")}, ok=(200, 404))
        if prev.status_code == 200 and isinstance(prev.json(), dict):
            body["sha"] = prev.json()["sha"]
        self._req("PUT", url, json=body, timeout=600)

    def subir_archivo(self, proyecto: str, ruta_local: str, nombre: str) -> str:
        """Sube un archivo local. Devuelve 'repo' o 'release'."""
        tam = os.path.getsize(ruta_local)
        if tam < LIMITE_REPO_MB * 1024 * 1024:
            with open(ruta_local, "rb") as fh:
                data = fh.read()
            self.subir_bytes(f"{proyecto}/{nombre}", data, f"{proyecto}: {nombre}")
            return "repo"
        self.subir_a_release(proyecto, ruta_local, nombre)
        return "release"

    def subir_a_release(self, proyecto, ruta_local, nombre):
        rel = self._release(tag_de(proyecto), crear=True)
        url = f"{UPLOADS}/repos/{self.repo}/releases/{rel['id']}/assets"
        with open(ruta_local, "rb") as fh:
            self._req("POST", url, params={"name": nombre}, data=fh, timeout=3600,
                      headers={"Content-Type": "application/octet-stream",
                               "Content-Length": str(os.path.getsize(ruta_local))})


class _RepoVacio(Exception):
    pass


class _Conflicto(Exception):
    pass


def tag_de(proyecto: str) -> str:
    """Nombre de tag válido para el release del proyecto."""
    t = re.sub(r"[^A-Za-z0-9._-]+", "-", proyecto).strip("-.") or "proyecto"
    return t
