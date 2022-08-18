from difflib import get_close_matches
import re
import requests


def regex_group(search, num, default=None):
    try:
        return search.group(num)
    except (AttributeError, IndexError):
        return default

def regex_match(findall, num, default=None):
    try:
        return findall[num]
    except (TypeError, IndexError):
        return default

def default(fallback):
    def decorator_func(func):
        func.default = fallback
        return func
    return decorator_func

def name(string=None):
    def decorator_func(func):
        nonlocal string
        if string == None:
            string = func.__name__
        func.name = string
        return func
    return decorator_func


class Parser:
    """
    Basic parser for Cemu log files.
    This class should ONLY contain info that can be found using only the contents of the log file.
    To extend this parser, inherit it and add your custom functions to self.embed.
    See ExtraParser for an example.
    """
    @name("init.loaded_title")
    @default(False)
    def loaded_title(self, file, info):
        return bool(re.search(r"------- Loaded title -------", file))
    @name("init.game_crashed")
    @default(False)
    def game_crashed(self, file, info):
        if info["init.loaded_title"]:
            return bool(re.search(r"Stack trace", file))
        return False
    @name("init.overwolf_issue")
    @default(False)
    def overwolf_issue(self, file, info):
        if info["init.loaded_title"]:
            return bool(re.search(r"ow-graphics-vulkan\.dll", file))
        return False
    @name("init.piracy_check")
    @default(False)
    def piracy_check(self, file, info):
        if info["init.loaded_title"]:
            return bool(re.search(r"\+0x001d9be4", file))
        return False
    @name("emulator.cemu_version")
    @default("Unknown")
    def cemu_version(self, file, info):
        return regex_group(re.search(r"------- Init Cemu (.*?) -------", file), 1)
    @name("emulator.cemuhook_version")
    @default("N/A")
    def cemuhook_version(self, file, info):
        return regex_group(re.search(r"Cemuhook version: (.*?)$", file, re.M), 1)
    @name("game.title_id")
    @default("Unknown")
    def title_id(self, file, info):
        result = regex_group(re.search(r"TitleId: (.*?)$", file, re.M), 1)
        return result.upper() if result else None
    @name("game.title_version")
    @default("Unknown")
    def title_version(self, file, info):
        return regex_group(re.search(r"TitleVersion: (v[0-9]+)", file), 1)
    @name("game.rpx_hash.updated")
    @default("Unknown")
    def rpx_hash_updated(self, file, info):
        updated = re.search(r"RPX hash \(updated\): (.*?)$", file, re.M)
        if not updated:
            updated = re.search(r"RPX hash: (.*?)$", file, re.M)
        return regex_group(updated, 1)
    @name("game.rpx_hash.base")
    @default("Unknown")
    def rpx_hash_base(self, file, info):
        base = "N/A"
        if info["game.rpx_hash.updated"]:
            base = regex_group(re.search(r"RPX hash \(base\): (.*?)$", file, re.M), 1)
        return base
    @name("game.shadercache_name")
    @default("Unknown")
    def shadercache_name(self, file, info):
        result = regex_group(re.search(r"shaderCache name: (.*?)$", file, re.M), 1)
        if not result:
            result = regex_group(
                re.search(r"Shader cache file: shaderCache[\\/].*?[\\/](.*?)$", file, re.M),
                1
            )
        return result
    @name("specs.cpu")
    @default("Unknown")
    def cpu(self, file, info):
        return regex_group(re.search(r"(?<!CPU[0-9] )CPU: (.*?) *$", file, re.M), 1)
    @name("specs.ram")
    @default("Unknown")
    def ram(self, file, info):
        return regex_group(re.search(r"RAM: ([0-9]+)MB", file), 1)
    @name("specs.gpu")
    @default("Unknown")
    def gpu(self, file, info):
        return regex_group(re.search(r"(?:GL_RENDERER: |Using GPU: )(.*?)$", file, re.M), 1)
    @name("specs.gpu_driver")
    @default("Unknown")
    def gpu_driver(self, file, info):
        result = regex_group(re.search(r"GL_VERSION: (.*?)$", file, re.M), 1)
        if not result:
            result = regex_group(re.search(r"Driver version: (.*?)$", file, re.M), 1)
        return result
    @name("settings.cpu_affinity")
    @default("Unknown")
    def cpu_affinity(self, file, info):
        result = regex_group(re.search(r"Set process CPU affinity to (.*?)$", file, re.M), 1)
        if result:
            return " ".join(
                map(
                    lambda x: f"CPU{ord(x[0]) - 0x30}",
                    result.split("CPU")[1:]
                )
            )
        return "All cores"
    @name("settings.cpu_mode")
    @default("Unknown")
    def cpu_mode(self, file, info):
        return regex_group(re.search(r"CPU-Mode: (.*?)$", file, re.M), 1)
    @name("settings.cpu_extensions")
    @default("Unknown")
    def cpu_extensions(self, file, info):
        result = re.search(r"Recompiler initialized. CPU extensions: (.*?)$", file, re.M)
        if result:
            return list(filter(lambda x: x != "", regex_group(result, 1).split(' ')))
        return []
    @name("settings.disabled_cpu_extensions")
    @default("")
    def disabled_cpu_extensions(self, file, info):
        used_extensions = re.search(r"CPU extensions that will actually be used by recompiler: (.*?)$", file, re.M)
        used_extensions = regex_group(used_extensions, 1, '').split(' ')
        if used_extensions != ['']:
            return ', '.join(
                list(filter(
                    lambda x: x not in used_extensions,
                    info["settings.cpu_extensions"]
                ))
            )
        return None
    @name("settings.backend")
    @default("Unknown")
    def backend(self, file, info):
        return regex_group(re.search(r"------- Init (OpenGL|Vulkan) graphics backend -------", file), 1)
    @name("settings.vulkan_async")
    @default("Unknown")
    def vulkan_async(self, file, info):
        if info["settings.backend"] == "Vulkan":
            result = re.search(r"Async compile: true", file)
            return "Enabled" if result else "Disabled"
        return "N/A"
    @name("settings.gx2drawdone")
    @default("Unknown")
    def gx2drawdone(self, file, info):
        if info["settings.backend"] == "Vulkan":
            return "N/A"
        result = re.search(r"Full sync at GX2DrawDone: true", file)
        return "Enabled" if result else "Disabled"
    @name("settings.console_region")
    @default("Auto")
    def console_region(self, file, info):
        return regex_group(re.search(r"Console region: (.*?)$", file, re.M), 1)
    @name("settings.thread_quantum")
    @default("Default")
    def thread_quantum(self, file, info):
        return regex_group(re.search(r"Thread quantum set to (.*?)$", file, re.M), 1)
    @name("settings.custom_timer_mode")
    @default("Default")
    def custom_timer_mode(self, file, info):
        result = regex_group(re.search(r"Custom timer mode: (.*?)$", file, re.M), 1)
        if result == "none":
            result = "Default"
        return result
    @name("settings.accurate_barriers")
    @default("Disabled")
    def accurate_barriers(self, file, info):
        result = re.search(r"Accurate barriers: Enabled", file)
        if info["settings.backend"] == "OpenGL":
            return "N/A"
        return "Enabled" if result else "Disabled"
    @name("specs.gfx_api_version")
    @default("Unknown")
    def gfx_api_version(self, file, info):
        if info["settings.backend"] == "OpenGL":
            # https://www.khronos.org/registry/OpenGL-Refpages/gl4/html/glGetString.xhtml#description
            # GL_VERSION string always starts with "major.minor " or "major.minor.release "
            return regex_group(re.search(r"GL_VERSION: (.+?\..+?)(?:[. ].*?)?$", file, re.M), 1)
        elif info["settings.backend"] == "Vulkan":
            return regex_group(re.search(r"Vulkan instance version: (.+?)$", file, re.M), 1)
        return None
    def __init__(self):
        self.embed = [
            self.loaded_title, self.game_crashed,
            self.overwolf_issue, self.piracy_check,
            self.cemu_version, self.cemuhook_version,
            self.title_id, self.title_version,
            self.rpx_hash_updated, self.rpx_hash_base, self.shadercache_name,
            self.cpu, self.ram, self.gpu, self.gpu_driver,
            self.cpu_affinity, self.cpu_mode, self.cpu_extensions,
            self.disabled_cpu_extensions, self.backend,
            self.vulkan_async, self.gx2drawdone, self.console_region,
            self.thread_quantum, self.custom_timer_mode, self.accurate_barriers,
            self.gfx_api_version
        ]
    def parse(self, file):
        info = {}
        for func in self.embed:
            result = func(file, info)
            info[func.name] = result if (result != None) else func.default
        return info


class ExtraParser(Parser):
    """
    Same as Parser, with a few extra bits of info that must be fetched from
    external sources (GPU support and game compatibility).
    """
    @name("specs.gpu_specs.url")
    @default("")
    def gpu_specs_url(self, file, info):
        query = info["specs.gpu"]
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
                x for x in get_close_matches(query, results.keys())
                if not (bool(re.search(r"mobile|max-q", query, re.I)) ^ bool(re.search(r"mobile|max-q", x, re.I)))
            ]
            if results[matches[0]]:
                return f"https://www.techpowerup.com{results[matches[0]]}"
            return None
        except (KeyError, IndexError):
            return None
    @name("specs.gpu_specs.html")
    @default("")
    def gpu_specs_html(self, file, info):
        if info["specs.gpu_specs.url"]:
            req = requests.get(info["specs.gpu_specs.url"])
            if req.status_code == 200:
                text = req.text
                text = text.replace('\n','')
                text = text.replace('\t','')
                return text
        return None
    @name("specs.opengl")
    @default("Unknown")
    def opengl(self, file, info):
        return regex_group(re.search(r"<dt>OpenGL</dt><dd>(.*?)</dd>", info["specs.gpu_specs.html"]), 1)
    @name("specs.vulkan")
    @default("Unknown")
    def vulkan(self, file, info):
        return regex_group(re.search(r"<dt>Vulkan</dt><dd>(.*?)</dd>", info["specs.gpu_specs.html"]), 1)
    @name("game.wiki_page.url")
    @default("")
    def wiki_page_url(self, file, info):
        try:
            if self.title_ids[info["game.title_id"]]["wiki_has_game_id_redirect"]:
                return f"http://wiki.cemu.info/wiki/{self.title_ids[info['game.title_id']]['game_id']}"
            else:
                # todo: use a cache of the cemu wiki instead of making a request on each parse
                title = self.title_ids[info["game.title_id"]]["game_title"]
                title = re.sub(r"[^\x00-\x7f]", r"", title)
                title = title.replace(" ", "_")
                return f"http://wiki.cemu.info/wiki/{title}"
        except KeyError:
            # this usually triggers when the title ID isn't in the database (mostly system titles)
            return None
    @name("game.wiki_page.html")
    @default("")
    def wiki_page_html(self, file, info):
        if info["game.wiki_page.url"]:
            req = requests.get(info["game.wiki_page.url"])
            if req.status_code == 200:
                return req.text
        return None
    @name("game.compat.rating")
    @default("Unknown")
    def compat_rating(self, file, info):
        compat = regex_match(
            re.findall(r"<tr style=\"vertical-align:middle;\">.*?</tr>", info["game.wiki_page.html"], re.M|re.S),
            -1, ""
        )
        return regex_group(
            re.search(r"<a href=\"/wiki/Category:.*?_\(Rating\)\" title=\"Category:.*? \(Rating\)\">(.*?)</a>", compat),
            1
        )
    @name("game.compat.version")
    @default("Unknown")
    def compat_version(self, file, info):
        compat = regex_match(
            re.findall(r"<tr style=\"vertical-align:middle;\">.*?</tr>", info["game.wiki_page.html"], re.M|re.S),
            -1, ""
        )
        return regex_group(
            re.search(r"<a href=\"(?:/wiki/|/index\.php\?title=)Release.*? title=\".*?\">(.*?)</a>", compat),
            1
        )
    def __init__(self, title_ids):
        super().__init__()
        self.title_ids = title_ids
        self.embed += [
            self.gpu_specs_url, self.gpu_specs_html, self.opengl, self.vulkan,
            self.wiki_page_url, self.wiki_page_html,
            self.compat_rating, self.compat_version
        ]


class RulesetParser:
    """
    A class that takes log info parsed by {Parser} and a dictionary of rulesets,
    and runs those rulesets on the data to determine potential problems.
    To use this class, create an instance of it and run RulesetParser.parse().
    """
    def __init__(self, rulesets):
        self.rulesets = rulesets
    # determines if ver1 <=> ver2
    def version_check(self, ver1, ver2, operation):
        ver1 = re.findall(r"(\d)\.(\d+)\.(\d+)([a-z])?.*?", ver1, re.I)[0]
        ver2 = re.findall(r"(\d)\.(\d+)\.(\d+)([a-z])?.*?", ver2, re.I)[0]
        ver1 = (int(ver1[0]), int(ver1[1]), int(ver1[2]), ver1[3])
        ver2 = (int(ver2[0]), int(ver2[1]), int(ver2[2]), ver2[3])
        # hotfixes should be ignored if ver2 doesn't specify a hotfix letter
        if ver2[3] == '':
            ver1 = ver1[:-1]
            ver2 = ver2[:-1]
        if operation == "lt":
            for (n1, n2) in zip(ver1, ver2):
                if n1 == n2:
                    continue
                else:
                    return n1 < n2
        elif operation == "eq":
            return ver1 == ver2
        elif operation == "ne":
            return ver1 != ver2
        elif operation == "gt":
            for (n1, n2) in zip(ver1, ver2):
                if n1 == n2:
                    continue
                else:
                    return n1 > n2
        else:
            raise ValueError("Invalid operation; must be lt, eq, ne, or gt")
    def parse(self, log_file: str, info: dict) -> list:
        relevant_info = []
        relevant_info.extend(self.parse_ruleset(log_file, info, self.rulesets["any"]))
        try:
            ruleset = self.rulesets[info["game.title_id"]]
            # to avoid duplicate rulesets,
            # one title ID (usually USA) holds the game's ruleset,
            # and the other regions simply redirect to it
            if type(ruleset) == str:
                ruleset = self.rulesets[ruleset]
            relevant_info.extend(self.parse_ruleset(log_file, info, ruleset))
        except KeyError:
            pass
        return relevant_info
    def parse_ruleset(self, log_file: str, info: dict, ruleset: list) -> list:
        messages = []
        for rule in ruleset:
            match_type = rule["match"]
            message = rule["message"]
            test_result = None
            for test in rule["rules"]:
                test_result = True
                if test["property"] == "log":
                    prop = log_file
                else:
                    prop = info[test["property"]]
                rule_type = test["type"]
                value = test["value"]
                test_result = (\
                    (rule_type == "str_eq" and prop == value) or \
                    (rule_type == "str_ne" and prop != value) or \
                    (rule_type == "str_contains" and value in prop) or \
                    (rule_type == "str_not_contains" and value not in prop) or \
                    (rule_type == "int_lt" and float(prop) < value) or \
                    (rule_type == "int_eq" and float(prop) == value) or \
                    (rule_type == "int_gt" and float(prop) > value) or \
                    (rule_type == "rgx_matches" and re.search(value, prop, re.M)) or \
                    (rule_type == "ver_lt" and self.version_check(prop, value, "lt")) or \
                    (rule_type == "ver_eq" and self.version_check(prop, value, "eq")) or \
                    (rule_type == "ver_ne" and self.version_check(prop, value, "ne")) or \
                    (rule_type == "ver_gt" and self.version_check(prop, value, "gt"))
                )
                if ((not test_result) and (match_type == "all")) \
                or ((    test_result) and (match_type == "any")):
                    break
            if test_result:
                messages.append(message.format(info))
        return messages
