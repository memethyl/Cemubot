from .utility import regex_group
from abc import ABC
import concurrent.futures
import difflib
import enum
import json
import re
import requests
import traceback
from typing import Dict, List, Optional, Union


class GPUAPI(enum.IntFlag):
    OpenGL = 1
    Vulkan = 2
    Both = 3


class APIVersion(ABC):
    def __str__(self):
        pass


class APIResult:
    version: APIVersion
    url: Optional[str] = None

    def __init__(self, version: APIVersion, url: str=None):
        self.version = version
        self.url = url

    def __str__(self):
        return f"APIResult(version={self.version}, url={self.url})"


class GLVersion(APIVersion):
    major: int
    minor: int

    def __init__(self, major: int, minor: int):
        self.major = major
        self.minor = minor

    def __str__(self):
        return f"{self.major}.{self.minor}"


class VKVersion(APIVersion):
    major: int
    minor: int
    patch: int
    
    def __init__(self, major: int, minor: int, patch: int):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __str__(self):
        if self.patch == 0:
            return f"{self.major}.{self.minor}"
        return f"{self.major}.{self.minor}.{self.patch}"


class GPUSearchResult:
    opengl: Optional[APIResult]
    vulkan: Optional[APIResult]

    def __init__(self, opengl: Optional[APIResult]=None, vulkan: Optional[APIResult]=None):
        self.opengl = opengl
        self.vulkan = vulkan


class GPUSearchModule(ABC):
    def search(self, gpu: str, api: GPUAPI = GPUAPI.Both) -> GPUSearchResult:
        pass


class GPUInfoSearch(GPUSearchModule):
    """GPUSearchModule implementation using gpuinfo.org as the database."""
    opengl_cache: Optional[Dict[str, APIResult]] = None
    vulkan_cache: Optional[Dict[str, APIResult]] = None

    def __init__(self, init_cache: bool=True):
        if init_cache:
            self.init_cache()

    def init_cache(self):
        """Initialize the internal OpenGL and Vulkan database caches."""
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(GPUInfoSearch.cache_opengl),
                            executor.submit(GPUInfoSearch.cache_vulkan)]
                self.opengl_cache = futures[0].result()
                self.vulkan_cache = futures[1].result()
        except Exception as e:
            print(f"Database cache could not be initialized")
            traceback.print_exc()

    @staticmethod
    def jsonToQueryString(json: Dict) -> str:
        def recurse(obj: Union[Dict, List], parent: str="") -> List:
            result = []
            for key,value in (obj.items() if type(obj) == dict else enumerate(obj)):
                temp = parent + (key if parent == "" else f"[{key}]")
                if type(value) == dict or type(value) == list:
                    result.extend(recurse(value, f"{temp}"))
                else:
                    result.append(f"{temp}={value}")
            return result
        return '?' + '&'.join(recurse(json))

    @staticmethod
    def cache_opengl() -> Optional[Dict[str, APIResult]]:
        """Returns a cache of the OpenGL version database for offline usage."""
        try:
            req = requests.get("https://opengl.gpuinfo.org/versionsupport.php")
        except requests.exceptions.RequestException:
            return None
        if req.status_code != 200:
            return None
        # (url, name, gl_version)
        devices = re.findall(
            r"<tr>.*?<td class='firstrow'><a href='(displayreport\.php\?id=.+?)'>(.+?)</a></td>.*?<td class='valuezeroleftblack'>(.+?)</td>.*?</tr>",
            req.text, re.S)
        result: Dict[str, APIResult] = {}
        for device in devices:
            version = device[2].split(".")
            result[device[1]] = APIResult(
                GLVersion(int(version[0]), int(version[1])),
                f"https://opengl.gpuinfo.org/{device[0]}")
        return result

    @staticmethod
    def cache_vulkan() -> Optional[Dict[str, APIResult]]:
        """Returns a cache of the Vulkan version database for offline usage."""
        query = {
            "platform": "all",
            "columns": {
                "0": {
                    "data": "device"
                },
                "1": {
                    "data": "api"
                }
            },
            "order": [
                {
                    "column": "device",
                    "dir": "asc"
                }
            ]
        }
        query_str = GPUInfoSearch.jsonToQueryString(query)
        try:
            req = requests.get(f"https://vulkan.gpuinfo.org/api/internal/devices.php{query_str}")
        except requests.exceptions.RequestException:
            return None
        if req.status_code != 200:
            return None
        devices = json.loads(req.text)["data"]
        result: Dict[str, APIResult] = {}
        for device in devices:
            temp = re.search(r"<a href=\"(listreports\.php\?devicename=.*?)\">(.*?)</a>", device["device"])
            version = device["api"].split(".")
            result[temp.group(2)] = APIResult(
                VKVersion(int(version[0]), int(version[1]), int(version[2])),
                f"https://vulkan.gpuinfo.org/{temp.group(1)}"
            )
        return result

    @staticmethod
    def search_opengl_nocache(gpu: str) -> Optional[APIResult]:
        try:
            req = requests.get("https://opengl.gpuinfo.org/versionsupport.php")
        except requests.exceptions.RequestException:
            return None
        if req.status_code != 200:
            return None
        # (url, name, gl_version)
        results = re.findall(
            r"<tr>.*?<td class='firstrow'><a href='(displayreport\.php\?id=.+?)'>(.+?)</a></td>.*?<td class='valuezeroleftblack'>(.+?)</td>.*?</tr>",
            req.text, re.S)
        if results:
            result = sorted(results,
                key=lambda x: difflib.SequenceMatcher(None, x[1], gpu).ratio(),
                reverse=True)
            result = result[0]
            ver = result[2].split(".")
            return APIResult(GLVersion(int(ver[0]), int(ver[1])), f"https://opengl.gpuinfo.org/{result[0]}")
        return None

    @staticmethod
    def search_vulkan_nocache(gpu: str) -> Optional[APIResult]:
        gpu_stripped = re.sub(
            r"/?(?:PCIe|)/?SSE2",
            "", gpu
        )
        query = {
            "platform": "all",
            "columns": {
                "0": {
                    "data": "device",
                    "searchable": "true",
                    "search": {
                        "value": gpu_stripped,
                        "regex": "false"
                    }
                },
                "1": {
                    "data": "api"
                }
            },
            "order": [
                {
                    "column": "device",
                    "dir": "asc"
                }
            ],
            "start": "0",
            "length": "25"
        }
        query_str = GPUInfoSearch.jsonToQueryString(query)
        url = f"https://vulkan.gpuinfo.org/api/internal/devices.php{query_str}"
        try:
            req = requests.get(url)
        except requests.exceptions.RequestException:
            return None
        if req.status_code != 200:
            return None
        result = json.loads(req.text)
        if result["data"]:
            result = result["data"]
            for item in result:
                temp = re.search(r"<a href=\"(.*?)\">(.+?)</a>", item["device"]).groups()
                item["device"] = {"url": temp[0], "name": temp[1]}
            sort_func = lambda x: difflib.SequenceMatcher(
                None,
                x["device"]["name"],
                gpu_stripped
            ).ratio()
            matches = sorted(result, key=sort_func, reverse=True)
            ver = matches[0]["api"]
            ver = ver.split(".")
            return APIResult(
                VKVersion(int(ver[0]), int(ver[1]), int(ver[2])),
                f"https://vulkan.gpuinfo.org/{matches[0]['device']['url']}")
        return None

    def _search_cache(self, gpu: str, api: GPUAPI = GPUAPI.Both) -> GPUSearchResult:
        result: GPUSearchResult = GPUSearchResult()
        if api & GPUAPI.OpenGL:
            if (temp := self.opengl_cache.get(gpu)):
                result.opengl = temp
            else:
                matches = difflib.get_close_matches(gpu, self.opengl_cache.keys())
                result.opengl = self.opengl_cache.get(matches[0]) if matches else None
        if api & GPUAPI.Vulkan:
            if (temp := self.vulkan_cache.get(gpu)):
                result.vulkan = temp
            else:
                gpu_stripped = re.sub(r"/?(?:PCIe|)/?SSE2", "", gpu)
                matches = difflib.get_close_matches(gpu_stripped, self.vulkan_cache.keys())
                result.vulkan = self.vulkan_cache.get(matches[0]) if matches else None
        return result

    def search(self, gpu: str, api: GPUAPI = GPUAPI.Both) -> GPUSearchResult:
        result: GPUSearchResult = GPUSearchResult()
        if self.opengl_cache and self.vulkan_cache:
            result = self._search_cache(gpu, api)
        elif self.opengl_cache and not self.vulkan_cache:
            if api & GPUAPI.OpenGL:
                result.opengl = self._search_cache(gpu, GPUAPI.OpenGL).opengl
            if api & GPUAPI.Vulkan:
                result.vulkan = GPUInfoSearch.search_vulkan_nocache(gpu)
        elif self.vulkan_cache and not self.opengl_cache:
            if api & GPUAPI.Vulkan:
                result.vulkan = self._search_cache(gpu, GPUAPI.Vulkan).vulkan
            if api & GPUAPI.OpenGL:
                result.opengl = GPUInfoSearch.search_opengl_nocache(gpu)
        else:
            futures = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(GPUInfoSearch.search_opengl_nocache, gpu),
                           executor.submit(GPUInfoSearch.search_vulkan_nocache, gpu)]
            if api & GPUAPI.OpenGL:
                result.opengl = futures[0].result()
            if api & GPUAPI.Vulkan:
                result.vulkan = futures[1].result()
        return result


class TechPowerUpSearch(GPUSearchModule):
    """
    GPUSearchModule implementation using techpowerup.com as the database.
    WARNING: After using this for two years, I got IP banned. Consider using GPUInfoSearch instead.
    """
    @staticmethod
    def get_url(query: str) -> Optional[str]:
        revised_query = re.sub(
            r"(?:[0-9]GB|)/?(?:PCIe|)/?SSE2|\(TM\)|\(R\)| Graphics$|GB$| Series$|(?<=Mobile )Graphics$",
            "", query
        )
        try:
            req = requests.get(f"https://www.techpowerup.com/gpu-specs/?ajaxsrch={revised_query}")
        except requests.exceptions.RequestException:
            return None
        req = req.text
        if "Nothing found." in req:
            return None
        req = req.replace("\n","")
        req = req.replace("\t","")
        results = re.findall(r"<tr><td.+?><a href=\"(/gpu-specs/.*?)\">(.*?)</a>", req)
        results = [list(reversed(x)) for x in results]
        results = dict(results)
        try:
            matches = [
                x for x in difflib.get_close_matches(query, results.keys())
                if not (bool(re.search(r"mobile|max-q", query, re.I)) ^ bool(re.search(r"mobile|max-q", x, re.I)))
            ]
            if results[matches[0]]:
                return f"https://www.techpowerup.com{results[matches[0]]}"
            return None
        except (KeyError, IndexError):
            return None

    @staticmethod
    def get_html(url: str) -> Optional[str]:
        if url:
            try:
                req = requests.get(url)
            except requests.exceptions.RequestException:
                return None
            if req.status_code == 200:
                text = req.text
                text = text.replace('\n','')
                text = text.replace('\t','')
                return text
        return None

    def search(self, gpu: str, api: GPUAPI = GPUAPI.Both) -> GPUSearchResult:
        result: GPUSearchResult = GPUSearchResult()
        url = TechPowerUpSearch.get_url(gpu)
        if not url:
            return result
        html = TechPowerUpSearch.get_html(url)
        if not html:
            return result
        if api & GPUAPI.OpenGL:
            if (gl := regex_group(re.search(r"<dt>OpenGL</dt><dd>(.*?)</dd>", html), 1)):
                gl = gl.split(".")
                result.opengl = APIResult(GLVersion(int(gl[0]), int(gl[1])), url)
        if api & GPUAPI.Vulkan:
            if (vk := regex_group(re.search(r"<dt>Vulkan</dt><dd>(.*?)</dd>", html), 1)):
                vk = vk.split(".")
                result.vulkan = APIResult(VKVersion(int(vk[0]), int(vk[1]), 0), url)
        return result
