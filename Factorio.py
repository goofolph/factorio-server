import http.client as http_client
import logging
import os
import re
from enum import Enum
from time import sleep

import bs4
import httpx

# from curl_cffi import requests
import requests
from rich import print

username = ""
password = ""

home_url = "https://www.factorio.com/"
available_releases_url = "https://updater.factorio.com/get-available-versions"
latest_release_url = "https://factorio.com/api/latest-releases"
sha256_url = "https://www.factorio.com/download/sha256sums/"
login_url = "https://www.factorio.com/login"
archive_url = "https://www.factorio.com/download/archive/"

http_client.HTTPConnection.debuglevel = 1


class Build(str, Enum):
    alpha = "alpha"
    expansion = "expansion"
    demo = "demo"
    headless = "headless"


class Distro(str, Enum):
    win64 = "win64"
    win64_manual = "win64-manual"
    win32 = "win32"
    win32_manual = "win32-manual"
    osx = "osx"
    linux64 = "linux64"
    linux32 = "linux32"


def get_download_url(
    version: str = "latest",
    build: Build = Build.headless,
    distro: Distro = Distro.linux64,
):
    return f"https://www.factorio.com/get-download/{version}/{build}/{distro}"


logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

session = requests.Session(impersonate="chrome")

# resp = session.get(login_url)
# resp.raise_for_status()
# soup = bs4.BeautifulSoup(resp.text, "html.parser")
# csrf_token = soup.select_one("input[name='csrf_token']")["value"]
# resp = session.post(
#     login_url,
#     json={
#         "csrf_token": csrf_token,
#         "username_or_email": username,
#         "password": password,
#     },
#     allow_redirects=False,
# )
# resp = session.get(home_url)


resp = session.get(
    available_releases_url,
    json={
        # "csrf_token": csrf_token,
        # "username_or_email": username,
        # "password": password,
    },
)
resp.raise_for_status()
available_releases = resp.json()
print(available_releases.keys())
all_versions = set()
for build, versions in available_releases.items():
    # print(build, versions)
    for ver in versions:
        if "from" in ver:
            all_versions.add(ver["from"])
        if "to" in ver:
            all_versions.add(ver["to"])
        if "stable" in ver:
            all_versions.add(ver["stable"])

resp = session.get(sha256_url)
hashes = [line.strip().split() for line in resp.text.split("\n")]

# for version in all_versions:
#     for build in Build:
#         for distro in Distro:
#             print(get_download_url(version=version, build=build, distro=distro))


# def get_sha256(hashes, version, build, distro):
#     hs = set()
#     for sha56, filepath in hashes.items():


for version in all_versions:
    build = Build.headless
    distro = Distro.linux64
    url = get_download_url(version=version, build=build, distro=distro)
    matches = [
        (h, p)
        for h, p in hashes
        if re.search("headless", p)
        and re.search(f"{version}", p)
        and re.search(".tar.xz", p)
    ]
    print("Found", len(matches), "matches for headless", version)
