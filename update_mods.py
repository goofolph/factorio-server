import hashlib
import json
import os
import re
import string
from time import sleep
from typing import List, Optional
from curl_cffi import requests
from rich import print
from packaging.version import Version


class FactoriMods:
    def __init__(self, username: str, token: str):
        assert isinstance(username, str)
        assert len(username.strip()) > 0
        assert isinstance(token, str)
        assert len(token.strip()) > 0

        self.url_base = "https://mods.factorio.com"
        self.session = requests.Session(impersonate="chrome", timeout=300)
        self.username = username
        self.token = token

    def __get__(
        self,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        retJson: bool = True,
        retContent: bool = False,
        retText: bool = False,
    ):
        assert isinstance(url, str)
        assert len(url.strip()) > 0
        assert headers is None or isinstance(headers, dict)
        assert params is None or isinstance(params, dict)
        assert data is None or isinstance(data, dict)
        assert sum([retJson, retContent, retText]) == 1

        allowed_chars = string.digits + string.ascii_letters + "-_[]{}() "
        url_slug = (
            f"{url}_"
            f"{json.dumps(headers)}_"
            f"{json.dumps(params)}_"
            f"{json.dumps(data)}"
        )
        url_slug = "".join(c for c in url_slug if c in allowed_chars).rstrip()
        if retJson:
            ext = "json"
        elif retContent:
            ext = "bin"
        elif retText:
            ext = "txt"
        else:
            ext = "unknown"
        sha1 = hashlib.sha1()
        sha1.update(url_slug.encode("utf8"))
        url_slug_hash = sha1.hexdigest()
        cache_name = f"/tmp/{url_slug_hash}.{ext}"
        print("GET:", url)
        print("Cache name:", cache_name)
        if os.path.exists(cache_name):
            print("Reading from cache")
            if retContent:
                with open(cache_name, "rb") as f:
                    ret = f.read()
            elif retJson:
                with open(cache_name, "r", encoding="utf8") as f:
                    ret = json.loads(f.read())
            elif retText:
                with open(cache_name, "r", encoding="utf8") as f:
                    ret = f.read()
            return ret
        else:
            sleep(2)
            resp = self.session.get(
                url,
                headers=headers,
                params=params,
                data=data,
            )
            resp.raise_for_status()
            print("Writing to cache", cache_name)
            if retContent:
                with open(cache_name, "wb") as f:
                    f.write(resp.content)
                return resp.content
            elif retJson:
                with open(cache_name, "w", encoding="utf8") as f:
                    f.write(json.dumps(resp.json()))
                return resp.json()
            elif retText:
                with open(cache_name, "w", encoding="utf8") as f:
                    f.write(resp.text)
                return resp.text

    def mod_info(self, modnames: List[str]):
        assert isinstance(modnames, list)
        assert all(isinstance(elem, str) for elem in modnames)
        assert len(modnames) > 0

        return self.__get__(
            f"{self.url_base}/api/mods",
            params={"namelist": modnames, "pagesize": "max"},
        )

    def mod_version_info(self, modname: str, version: str):
        assert isinstance(modname, str)
        assert len(modname.strip()) > 0
        assert isinstance(version, str)
        assert len(version.strip()) > 0

        info = self.mod_info([modname])
        for release in info["results"][0]["releases"]:
            if release["version"] == version:
                return release
        return None

    def get_mod_latest(
        self,
        modnames: List[str],
        min_factorio_version: str,
    ):
        assert isinstance(modnames, list)
        assert all(isinstance(elem, str) for elem in modnames)
        assert len(modnames) > 0
        assert isinstance(min_factorio_version, str)
        assert len(min_factorio_version.strip()) > 0

        info = self.mod_info(modnames=modnames)
        latest_versions = {}
        for mod in info["results"]:
            compat_versions = []
            for release in mod["releases"]:
                ver = release["info_json"]["factorio_version"]
                if Version(ver) >= Version(min_factorio_version):
                    compat_versions.append(release)
            compat_versions.sort(key=lambda x: Version(x["version"]))
            latest_versions[mod["name"]] = compat_versions[-1]
        return latest_versions

    def download_mod(self, modname: str, version: str, directory: str = "."):
        assert isinstance(modname, str)
        assert len(modname.strip()) > 0
        assert isinstance(version, str)
        assert len(version.strip()) > 0
        assert isinstance(directory, str)
        assert len(directory.strip()) > 0

        release = self.mod_version_info(modname, version)
        url = f"{self.url_base}{release['download_url']}"
        params = {"username": self.username, "token": self.token}
        filepath = os.path.join(directory, release["file_name"])
        if not os.path.exists(filepath):
            with open(filepath, "wb") as f:
                f.write(
                    self.__get__(
                        url,
                        params=params,
                        retJson=False,
                        retContent=True,
                    )
                )

        sha1 = hashlib.sha1()
        with open(filepath, "rb") as f:
            sha1.update(f.read())
        h = sha1.hexdigest()
        assert h == release["sha1"]

    def download_mod_latest(
        self, modname: str, min_factorio_version: str, directory: str = "."
    ):
        assert isinstance(modname, str)
        assert len(modname.strip()) > 0
        assert isinstance(min_factorio_version, str)
        assert len(min_factorio_version.strip()) > 0
        assert isinstance(directory, str)
        assert len(directory.strip()) > 0

        latest = self.get_mod_latest([modname], min_factorio_version)
        print("Latest:", latest)
        self.download_mod(
            modname,
            latest[modname]["version"],
            directory=directory,
        )


if __name__ == "__main__":

    config_file = "./.env"
    min_factorio_version = "2.0"
    modsdir = "./mods"

    config = {}
    with open(config_file, "r", encoding="utf8") as f:
        for line in f.readlines():
            line = line.strip()
            key, value = line.partition("=")[::2]
            config[key.strip()] = value.strip()
    print(config)

    fmods = FactoriMods(
        username=config["FACTORIO_USERNAME"], token=config["FACTORIO_TOKEN"]
    )
    mods = []
    if not os.path.exists(modsdir):
        os.mkdir(modsdir)
    for mod in os.listdir(modsdir):
        match = re.match(r"^(.+)_[\d\.]+\.zip$", mod)
        if match:
            mods.append(match.group(1))
    print(mods)

    for mod in mods:
        fmods.download_mod_latest(mod, min_factorio_version, modsdir)
        # TODO Add cleanup of old versions
