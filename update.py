import sys
import os
import json
import re
import time
import hashlib
import subprocess
from rich import print
from curl_cffi import requests
from packaging.version import Version


def validate_sha256(filepath: str, expected_sha256: str):
    # validate download checksum
    assert isinstance(filepath, str)
    assert len(filepath.strip()) > 0
    assert isinstance(expected_sha256, str)
    assert len(expected_sha256.strip()) > 0

    shasum = hashlib.sha256()
    with open(filepath, "rb") as f:
        data_chunk = f.read(4096)
        while data_chunk:
            shasum.update(data_chunk)
            data_chunk = f.read(4096)
        checksum = shasum.hexdigest()
        if checksum != expected_sha256:
            return False
        else:
            return True


available_releases_url = "https://updater.factorio.com/get-available-versions"
latest_release_url = "https://factorio.com/api/latest-releases"
sha256_url = "https://www.factorio.com/download/sha256sums/"
image = "goofolph/factorio"
filepath = "factorio-headless_linux.tar.xz"
env = ".env"

session = requests.Session(impersonate="chrome")


def get(url: str):
    assert isinstance(url, str)
    assert len(url.strip()) > 0

    time.sleep(1)
    resp = session.get(url)
    resp.raise_for_status()
    return resp


class FactorioVersion:
    def __init__(self, version: str, filename: str, sha256: str):
        assert isinstance(version, str)
        version = version.strip()
        assert len(version) > 0
        assert isinstance(filename, str)
        filename = filename.strip()
        assert isinstance(sha256, str)
        sha256 = sha256.strip()

        self.version = Version(version)
        self.filename = filename
        self.sha256 = sha256
        self.download_url = (
            f"https://www.factorio.com/get-download/{version}/headless/linux64"
        )

    def __str__(self):
        return f"FactorioVersion(version={self.version}, filename={self.filename})"


def all_releases():
    available = get(available_releases_url).json()
    hashes = [line.split() for line in get(sha256_url).text.split("\n")]

    all_versions = set()
    for pair in available["core-linux_headless64"]:
        if "from" in pair:
            all_versions.add(pair["from"])
        if "to" in pair:
            all_versions.add(pair["to"])
        if "stable" in pair:
            all_versions.add(pair["stable"])
    all_versions = [FactorioVersion(v, "", "") for v in all_versions]

    hashes_versions = []
    for h in hashes:
        match = re.match(r"^.*headless.*(\d+\.\d+\.\d+)\.tar\.xz$", h[1])
        if match:
            hashes_versions.append(FactorioVersion(match[1], h[1], h[0]))

    return all_versions, hashes_versions


def main():
    current_verison = "0"

    # Get current version from .env file
    with open(".env", "r", encoding="utf8") as f:
        for l in f.readlines():
            match = re.match("^FACTORIO_VERSION=([\d\.]+)$", l)
            if match:
                current_verison = match.group(1)
    print(f"Current version: {current_verison}")

    # Get latest stable version number from factorio api
    time.sleep(5)
    resp = session.get(release_url)
    resp.raise_for_status()
    versions = resp.json()
    stable = versions["stable"]["headless"]
    print("Latest stable verison", stable)

    # check if current download is already latest
    if Version(current_verison) < Version(stable):
        print("Current version is less than stable. Starting upgrade...")
    else:
        print("Current version is equal to the stable. Exiting.")
        sys.exit(0)

    # Get matching sha256 checksum
    time.sleep(5)
    resp = session.get(sha256_url)
    resp.raise_for_status()
    sha256s = resp.text
    stable_sha_line = [
        sha
        for sha in sha256s.split("\n")
        if re.match(f".*factorio-headless_linux_{stable}.tar.xz", sha)
    ][0].split()
    stable_sha256 = stable_sha_line[0]
    print("stable sha256", stable_sha256)

    # Download server tar
    download_url = f"https://www.factorio.com/get-download/{stable}/headless/linux64"
    print("Downloading", download_url)
    time.sleep(5)
    resp = session.get(download_url)
    resp.raise_for_status()
    with open(filepath, "wb") as f:
        f.write(resp.content)
    print("File donwloaded successfully.")

    if validate_sha256(filepath, stable_sha256):
        print("Download successfully validated.")
    else:
        print("Download failed to validate")
        sys.exit(1)

    # Replace version number in docker .env file for new image tag
    with open(env, "r", encoding="utf8") as f:
        lines = f.readlines()
    for i in range(0, len(lines)):
        line = lines[i]
        match = re.match("^FACTORIO_VERSION=([\d\.]+)$", line)
        if match:
            lines[i] = f"FACTORIO_VERSION={stable}"
    with open(env, "w", encoding="utf8") as f:
        f.writelines(lines)

    print("Building new container version")
    subprocess.call(["docker", "compose", "build", "--no-cache"])
    if subprocess.check_output(["docker", "images", "-q", f"{image}:{stable}"]):
        subprocess.call(["docker", "tag", f"{image}:{stable}", f"{image}:latest"])
        print("Recreating containers to use new build version")
        subprocess.call(["docker", "compose", "up", "-d"])
    else:
        print("Docker compose build failed. Reverting version string.")
        with open(env, "r", encoding="utf8") as f:
            lines = f.readlines()
        for i in range(0, len(lines)):
            line = lines[i]
            match = re.match("^FACTORIO_VERSION=([\d\.]+)$", line)
            if match:
                lines[i] = f"FACTORIO_VERSION={current_verison}"
        with open(env, "w", encoding="utf8") as f:
            f.writelines(lines)


if __name__ == "__main__":
    main()
