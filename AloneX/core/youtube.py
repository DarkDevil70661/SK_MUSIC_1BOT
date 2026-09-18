# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ʏ_ꜱʜᴀᴅᴏᴡ_ᴍᴜꜱɪᴄ
# ᴀᴅᴠᴀɴᴄᴇᴅ ᴍᴜꜱɪᴄ & ᴠɪᴅᴇᴏ ʙᴏᴛ
# • ᴍᴜꜱɪᴄ • ᴠɪᴅᴇᴏ • ʟɪᴠᴇ
# • ꜰᴀꜱᴛ • ꜱᴛᴀʙʟᴇ • ꜱᴇᴄᴜʀᴇ
# ᴅᴇᴠ : ᴇɴᴀꜰᴜʟ
# ᴠᴇʀ : ᴠ3.0.0
# YEAR : 2026
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import os
import re
import asyncio
import random
import yt_dlp

from py_yt import VideosSearch, Playlist
from AloneX import logger, config
from AloneX.helpers import Track, utils


# ============================================================
# DOWNLOAD DIRECTORY
# ============================================================

DOWNLOAD_DIR = "downloads"
COOKIE_DIR = "AloneX/cookies"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(COOKIE_DIR, exist_ok=True)


# ============================================================
# YOUTUBE URL HELPERS
# ============================================================

def normalize_youtube_url(link: str) -> str | None:
    """
    Convert YouTube video ID or URL into a normal YouTube URL.
    """

    if not link:
        return None

    link = str(link).strip()

    # Already a full URL
    if link.startswith("http://") or link.startswith("https://"):
        if "youtube.com" in link or "youtu.be" in link:
            return link

    # Raw video ID
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", link):
        return f"https://www.youtube.com/watch?v={link}"

    return None


def extract_video_id(link: str) -> str | None:
    """
    Extract YouTube video ID from URL or raw ID.
    """

    if not link:
        return None

    link = str(link).strip()

    # Raw ID
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", link):
        return link

    patterns = [
        r"(?:v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, link)

        if match:
            return match.group(1)

    return None


# ============================================================
# COOKIE HANDLING
# ============================================================

def get_cookie_file() -> str | None:
    """
    Find a random cookie file from AloneX/cookies.

    Expected:
        AloneX/cookies/cookies.txt
        AloneX/cookies/cookie_0.txt
        AloneX/cookies/cookie_1.txt
        ...
    """

    if not os.path.isdir(COOKIE_DIR):
        return None

    files = [
        os.path.join(COOKIE_DIR, file)
        for file in os.listdir(COOKIE_DIR)
        if file.lower().endswith(".txt")
    ]

    if not files:
        return None

    # Only use non-empty cookie files
    files = [
        file
        for file in files
        if os.path.isfile(file) and os.path.getsize(file) > 100
    ]

    if not files:
        return None

    return random.choice(files)


# ============================================================
# COMMON YT-DLP OPTIONS
# ============================================================

def get_common_options() -> dict:
    """
    Common yt-dlp configuration.

    IMPORTANT:
    We do NOT hard-code cookies.
    If a valid cookie file exists, it will automatically be used.
    """

    options = {
        "quiet": True,
        "no_warnings": True,

        # Do not stop entire operation because one format fails
        "ignoreerrors": False,

        # Network stability
        "socket_timeout": 30,

        # Retry failed requests
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 2,

        # Avoid unnecessary playlist extraction
        "noplaylist": True,

        # YouTube client configuration
        #
        # Keep this relatively conservative.
        "extractor_args": {
            "youtube": {
                "player_client": ["web_safari", "web_embedded"],
            }
        },

        # HTTP headers
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/139.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    cookie = get_cookie_file()

    if cookie:
        options["cookiefile"] = cookie
        logger.info(f"[YouTube] Using cookies: {cookie}")
    else:
        logger.warning("[YouTube] No cookies.txt found.")

    return options


# ============================================================
# DIRECT AUDIO DOWNLOAD
# ============================================================

def _download_audio_sync(url: str, output_path: str) -> str | None:
    """
    Synchronous yt-dlp audio downloader.
    Runs inside executor so the bot event loop is not blocked.
    """

    options = get_common_options()

    options.update(
        {
            # Best available audio
            "format": "bestaudio/best",

            # Convert to MP3
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],

            # Output path without extension.
            # yt-dlp/FFmpeg will add .mp3.
            "outtmpl": output_path,

            # Continue if already downloaded
            "overwrites": False,
        }
    )

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])

        final_path = f"{output_path}.mp3"

        if os.path.exists(final_path):
            if os.path.getsize(final_path) > 0:
                return final_path

    except Exception as e:
        logger.error(f"[YouTube Audio] Download failed: {e}")

    return None


async def download_song(link: str) -> str | None:
    """
    Download YouTube audio directly using yt-dlp.
    """

    video_id = extract_video_id(link)

    if not video_id:
        logger.error(f"[YouTube Audio] Invalid URL/ID: {link}")
        return None

    url = f"https://www.youtube.com/watch?v={video_id}"

    output_base = os.path.join(
        DOWNLOAD_DIR,
        video_id,
    )

    output_file = f"{output_base}.mp3"

    # Cache
    if os.path.exists(output_file):
        if os.path.getsize(output_file) > 0:
            return output_file

    loop = asyncio.get_running_loop()

    try:
        result = await loop.run_in_executor(
            None,
            _download_audio_sync,
            url,
            output_base,
        )

        return result

    except Exception as e:
        logger.error(
            f"[YouTube Audio] Executor error for {video_id}: {e}"
        )

        return None


# ============================================================
# DIRECT VIDEO DOWNLOAD
# ============================================================

def _download_video_sync(url: str, output_path: str) -> str | None:
    """
    Synchronous yt-dlp video downloader.
    """

    options = get_common_options()

    options.update(
        {
            # Best video + best audio
            # Falls back automatically if unavailable.
            "format": (
                "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                "best[ext=mp4]/"
                "best"
            ),

            # Merge video/audio into MP4
            "merge_output_format": "mp4",

            # Output
            "outtmpl": output_path,

            "overwrites": False,
        }
    )

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])

        # Normally mp4 after merge
        mp4_file = f"{output_path}.mp4"

        if os.path.exists(mp4_file):
            if os.path.getsize(mp4_file) > 0:
                return mp4_file

        # Some formats may output another extension
        for extension in ("mkv", "webm", "mp4"):

            file_path = f"{output_path}.{extension}"

            if os.path.exists(file_path):
                if os.path.getsize(file_path) > 0:
                    return file_path

    except Exception as e:
        logger.error(f"[YouTube Video] Download failed: {e}")

    return None


async def download_video(link: str) -> str | None:
    """
    Download YouTube video directly using yt-dlp.
    """

    video_id = extract_video_id(link)

    if not video_id:
        logger.error(f"[YouTube Video] Invalid URL/ID: {link}")
        return None

    url = f"https://www.youtube.com/watch?v={video_id}"

    output_base = os.path.join(
        DOWNLOAD_DIR,
        video_id,
    )

    output_file = f"{output_base}.mp4"

    # Cache
    if os.path.exists(output_file):
        if os.path.getsize(output_file) > 0:
            return output_file

    loop = asyncio.get_running_loop()

    try:
        result = await loop.run_in_executor(
            None,
            _download_video_sync,
            url,
            output_base,
        )

        return result

    except Exception as e:
        logger.error(
            f"[YouTube Video] Executor error for {video_id}: {e}"
        )

        return None


# ============================================================
# YOUTUBE CLASS
# ============================================================

class YouTube:

    def __init__(self):

        self.base = (
            "https://www.youtube.com/watch?v="
        )

        self.regex = re.compile(
            r"(https?://)?"
            r"(www\.|m\.|music\.)?"
            r"(youtube\.com/"
            r"(watch\?v=|shorts/|playlist\?list=)"
            r"|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)"
            r"([&?][^\s]*)?"
        )

        self.cookie_dir = COOKIE_DIR

    # ========================================================
    # COOKIE
    # ========================================================

    def get_cookies(self):

        return get_cookie_file()

    async def save_cookies(self, urls: list[str]) -> None:

        """
        Save cookies from Batbin URLs.

        Example:
            /addcookie <batbin-url>
        """

        import aiohttp

        logger.info(
            "[YouTube] Saving cookies..."
        )

        os.makedirs(
            self.cookie_dir,
            exist_ok=True,
        )

        async with aiohttp.ClientSession() as session:

            for i, url in enumerate(urls):

                path = os.path.join(
                    self.cookie_dir,
                    f"cookie_{i}.txt",
                )

                try:

                    link = (
                        "https://batbin.me/api/v2/paste/"
                        + url.split("/")[-1]
                    )

                    async with session.get(
                        link,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:

                        resp.raise_for_status()

                        data = await resp.read()

                        with open(
                            path,
                            "wb",
                        ) as fw:
                            fw.write(data)

                        logger.info(
                            f"[YouTube] Cookie saved: {path}"
                        )

                except Exception as e:

                    logger.error(
                        f"[YouTube] Cookie save failed: {e}"
                    )

        logger.info(
            f"[YouTube] Cookies saved in {self.cookie_dir}"
        )

    # ========================================================
    # URL VALIDATION
    # ========================================================

    def valid(self, url: str) -> bool:

        return bool(
            re.match(
                self.regex,
                url,
            )
        )

    # ========================================================
    # SEARCH
    # ========================================================

    async def search(
        self,
        query: str,
        m_id: int,
        video: bool = False,
    ) -> Track | None:

        try:

            _search = VideosSearch(
                query,
                limit=1,
            )

            results = await _search.next()

            if results and results.get("result"):

                data = results["result"][0]

                thumbnails = (
                    data.get("thumbnails")
                    or []
                )

                thumbnail = None

                if thumbnails:

                    thumbnail = (
                        thumbnails[-1]
                        .get("url")
                        or ""
                    ).split("?")[0]

                return Track(
                    id=data.get("id"),

                    channel_name=(
                        data.get("channel", {})
                        .get("name")
                    ),

                    duration=data.get(
                        "duration"
                    ),

                    duration_sec=(
                        utils.to_seconds(
                            data.get("duration")
                        )
                        if data.get("duration")
                        else 0
                    ),

                    message_id=m_id,

                    title=(
                        data.get("title")
                        or "Unknown"
                    )[:25],

                    thumbnail=thumbnail,

                    url=data.get("link"),

                    view_count=(
                        data.get("viewCount", {})
                        .get("short")
                    ),

                    video=video,
                )

        except Exception as e:

            logger.error(
                f"[YouTube Search] Error: {e}"
            )

        return None

    # ========================================================
    # PLAYLIST
    # ========================================================

    async def playlist(
        self,
        limit: int,
        user: str,
        url: str,
        video: bool,
    ) -> list[Track]:

        tracks = []

        try:

            plist = await Playlist.get(url)

            for data in (
                plist.get("videos", [])
            )[:limit]:

                thumbnails = (
                    data.get("thumbnails")
                    or []
                )

                thumbnail = None

                if thumbnails:

                    thumbnail = (
                        thumbnails[-1]
                        .get("url")
                        or ""
                    ).split("?")[0]

                link = data.get("link") or ""

                if "&list=" in link:

                    link = link.split(
                        "&list="
                    )[0]

                tracks.append(
                    Track(
                        id=data.get("id"),

                        channel_name=(
                            data.get("channel", {})
                            .get("name", "")
                        ),

                        duration=data.get(
                            "duration"
                        ),

                        duration_sec=(
                            utils.to_seconds(
                                data.get("duration")
                            )
                            if data.get("duration")
                            else 0
                        ),

                        title=(
                            data.get("title")
                            or "Unknown"
                        )[:25],

                        thumbnail=thumbnail,

                        url=link,

                        user=user,

                        view_count="",

                        video=video,
                    )
                )

        except Exception as e:

            logger.error(
                f"[YouTube Playlist] Error: {e}"
            )

        return tracks

    # ========================================================
    # DOWNLOAD
    # ========================================================

    async def download(
        self,
        video_id: str,
        video: bool = False,
    ) -> str | None:

        if not video_id:

            return None

        if video:

            return await download_video(
                video_id
            )

        return await download_song(
            video_id
        )

    # ========================================================
    # FORMAT DURATION
    # ========================================================

    def _format_duration(
        self,
        seconds: int,
    ) -> str:

        seconds = max(
            int(seconds or 0),
            0,
        )

        h, rem = divmod(
            seconds,
            3600,
        )

        m, s = divmod(
            rem,
            60,
        )

        if h:

            return (
                f"{h}:"
                f"{m:02d}:"
                f"{s:02d}"
            )

        return (
            f"{m}:"
            f"{s:02d}"
        )

    # ========================================================
    # FORMAT VIEWS
    # ========================================================

    def _format_views(
        self,
        count,
    ) -> str:

        if not count:

            return ""

        try:

            count = int(count)

        except Exception:

            return str(count)

        if count >= 1_000_000:

            return (
                f"{count / 1_000_000:.1f}"
                "M views"
            )

        if count >= 1_000:

            return (
                f"{count / 1_000:.1f}"
                "K views"
            )

        return (
            f"{count} views"
        )

    # ========================================================
    # RELATED / AUTOPLAY
    # ========================================================

    def _extract_related(
        self,
        video_id: str,
    ) -> dict | None:

        options = get_common_options()

        options.update(
            {
                "extract_flat": "in_playlist",
                "skip_download": True,

                "geo_bypass": True,

                "socket_timeout": 20,

                "retries": 2,

                "extractor_retries": 2,

                "noplaylist": False,

                "quiet": True,

                "no_warnings": True,
            }
        )

        url = (
            f"https://www.youtube.com/watch?v="
            f"{video_id}"
            f"&list=RD{video_id}"
        )

        try:

            with yt_dlp.YoutubeDL(
                options
            ) as ydl:

                return ydl.extract_info(
                    url,
                    download=False,
                )

        except Exception as e:

            logger.error(
                f"[Autoplay] yt-dlp related "
                f"error: {e}"
            )

            return None

    # ========================================================
    # RELATED FROM MIX
    # ========================================================

    async def _related_from_mix(
        self,
        video_id: str,
        played: set[str],
    ) -> Track | None:

        loop = asyncio.get_running_loop()

        try:

            info = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._extract_related,
                    video_id,
                ),
                timeout=30,
            )

        except asyncio.TimeoutError:

            logger.warning(
                f"[Autoplay] Mix timeout "
                f"for {video_id}"
            )

            return None

        except Exception as e:

            logger.error(
                f"[Autoplay] Mix failed "
                f"for {video_id}: {e}"
            )

            return None

        entries = (
            (info or {}).get("entries")
            or []
        )

        for entry in entries:

            if not entry:

                continue

            eid = entry.get("id")

            if not eid:

                continue

            if eid in played:

                continue

            title = (
                entry.get("title")
                or "Unknown"
            )

            if title.lower() in (
                "[deleted video]",
                "[private video]",
            ):

                continue

            duration = int(
                entry.get("duration")
                or 0
            )

            if duration <= 0:

                continue

            if duration > config.DURATION_LIMIT:

                continue

            thumbnails = (
                entry.get("thumbnails")
                or []
            )

            thumbnail = None

            if thumbnails:

                thumbnail = (
                    thumbnails[-1]
                    .get("url")
                    or ""
                ).split("?")[0]

            return Track(
                id=eid,

                channel_name=(
                    entry.get("channel")
                    or entry.get("uploader")
                    or "YouTube"
                ),

                duration=self._format_duration(
                    duration
                ),

                duration_sec=duration,

                title=title[:25],

                thumbnail=thumbnail,

                url=(
                    f"https://www.youtube.com/watch?v="
                    f"{eid}"
                ),

                view_count=self._format_views(
                    entry.get("view_count")
                ),

                video=False,
            )

        return None

    # ========================================================
    # RELATED FROM SEARCH
    # ========================================================

    async def _related_from_search(
        self,
        current: Track,
        played: set[str],
    ) -> Track | None:

        queries = []

        if current.channel_name:

            queries.append(
                current.channel_name
            )

        if current.title:

            queries.append(
                current.title
            )

        for query in queries:

            try:

                _search = VideosSearch(
                    query,
                    limit=8,
                )

                results = await _search.next()

            except Exception as e:

                logger.error(
                    f"[Autoplay] Search "
                    f"failed for {query!r}: {e}"
                )

                continue

            for data in (
                results or {}
            ).get("result", []):

                eid = data.get("id")

                if not eid:

                    continue

                if eid in played:

                    continue

                duration_str = data.get(
                    "duration"
                )

                duration_sec = (
                    utils.to_seconds(
                        duration_str
                    )
                    if duration_str
                    else 0
                )

                if not duration_sec:

                    continue

                if (
                    duration_sec
                    > config.DURATION_LIMIT
                ):

                    continue

                thumbnails = (
                    data.get("thumbnails")
                    or []
                )

                thumbnail = None

                if thumbnails:

                    thumbnail = (
                        thumbnails[-1]
                        .get("url")
                        or ""
                    ).split("?")[0]

                return Track(
                    id=eid,

                    channel_name=(
                        data.get(
                            "channel",
                            {},
                        ).get("name")
                        or "YouTube"
                    ),

                    duration=duration_str,

                    duration_sec=duration_sec,

                    title=(
                        data.get("title")
                        or "Unknown"
                    )[:25],

                    thumbnail=thumbnail,

                    url=data.get("link"),

                    view_count=(
                        data.get(
                            "viewCount",
                            {},
                        ).get("short")
                    ),

                    video=False,
                )

        return None

    # ========================================================
    # GET RELATED
    # ========================================================

    async def get_related(
        self,
        current: Track,
        played: list[str] | None = None,
    ) -> Track | None:

        if not current:

            return None

        if not current.id:

            return None

        played_set = set(
            played or []
        )

        played_set.add(
            current.id
        )

        # First try YouTube Mix
        related = await self._related_from_mix(
            current.id,
            played_set,
        )

        if related:

            return related

        logger.info(
            f"[Autoplay] Mix unavailable "
            f"for {current.id}; "
            f"using search fallback."
        )

        # Search fallback
        related = await self._related_from_search(
            current,
            played_set,
        )

        if related:

            return related

        logger.warning(
            f"[Autoplay] No related track "
            f"found for {current.id}"
        )

        return None
