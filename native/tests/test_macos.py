import os
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QCoreApplication

from youtube_music_native.macos import prepare_runtime
from youtube_music_native.macos_media import COMMANDS, MacBus
from youtube_music_native.signin import Capture, browser_agent


def test_runtime_paths_are_added_once_and_only_on_macos(tmp_path):
    environ = {"PATH": "/usr/bin"}
    prepare_runtime(environ, platform="linux", bundle=tmp_path)
    assert environ == {"PATH": "/usr/bin"}
    prepare_runtime(environ, platform="darwin", bundle=tmp_path)
    prepare_runtime(environ, platform="darwin", bundle=tmp_path)
    paths = environ["PATH"].split(os.pathsep)
    assert paths[0] == str(tmp_path / "helpers") and paths[-1] == "/usr/bin"
    assert paths.count(str(Path("/opt/homebrew/bin"))) == 1
    libraries = environ["DYLD_FALLBACK_LIBRARY_PATH"].split(os.pathsep)
    assert libraries[:2] == [str(tmp_path), str(Path("/opt/homebrew/lib"))]


def test_sign_in_announces_a_plain_browser_and_tracks_rotated_cookies():
    agent = "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 (KHTML, like Gecko) QtWebEngine/6.10.0 Chrome/140.0.0.0 Safari/537.36"
    assert browser_agent(agent) == "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"

    def cookie(name, domain=".youtube.com"):
        expiry = SimpleNamespace(isValid=lambda: False)
        return SimpleNamespace(name=lambda: name.encode(), value=lambda: b"private", domain=lambda: domain, path=lambda: "/",
                               isSecure=lambda: True, isSessionCookie=lambda: True, expirationDate=lambda: expiry)

    capture = Capture()
    capture.added(cookie("SAPISID"))
    capture.added(cookie("SID", ".google.com"))
    assert not capture.signed_in()
    capture.added(cookie("__Secure-3PAPISID"))
    assert capture.signed_in() and {row["name"] for row in capture.rows()} == {"SAPISID", "__Secure-3PAPISID"}
    capture.removed(cookie("SAPISID"))
    assert not capture.signed_in()


class Remote:
    def __init__(self):
        self.enabled, self.handlers, self.removed = None, [], []

    def setEnabled_(self, value):
        self.enabled = value

    def addTargetWithHandler_(self, handler):
        self.handlers.append(handler)
        return len(self.handlers)

    def removeTarget_(self, target):
        self.removed.append(target)


class Center:
    def __init__(self):
        self.info, self.state, self.updates = None, None, 0

    def setNowPlayingInfo_(self, info):
        self.info, self.updates = info, self.updates + 1

    def setPlaybackState_(self, state):
        self.state = state


class Notices:
    def __init__(self):
        self.observers = []

    def addObserver_selector_name_object_(self, observer, selector, name, value):
        self.observers.append((selector, name))

    def removeObserver_(self, observer):
        self.observers.clear()


KEYS = SimpleNamespace(**{name: name for name in (
    "MPMediaItemPropertyTitle", "MPMediaItemPropertyArtist", "MPMediaItemPropertyAlbumTitle", "MPMediaItemPropertyPlaybackDuration",
    "MPNowPlayingInfoPropertyElapsedPlaybackTime", "MPNowPlayingInfoPropertyPlaybackRate", "MPMediaItemPropertyArtwork")})


def snapshot(status="Playing", position=5000000, art=""):
    metadata = {"mpris:trackid": ("o", "/track/1"), "mpris:length": ("x", 120000000), "xesam:title": ("s", "Song"),
                "xesam:artist": ("as", ["First", "Second"]), "xesam:album": ("s", "Album")}
    if art:
        metadata["mpris:artUrl"] = ("s", art)
    return {"PlaybackStatus": status, "Position": position, "Metadata": metadata, "CanPlay": True, "CanPause": True,
            "CanGoNext": True, "CanGoPrevious": False, "CanSeek": True, "CanControl": True}


def test_now_playing_mirrors_the_player_and_forwards_media_keys():
    app = QCoreApplication.instance() or QCoreApplication([])
    remotes = {name: Remote() for name, _, _ in COMMANDS}
    commands = SimpleNamespace(**{name: (lambda remote: lambda: remote)(remote) for name, remote in remotes.items()})
    notices = Notices()
    center = Center()
    bus = MacBus(snapshot(), media=KEYS, center=center, commands=commands, workspace=SimpleNamespace(notificationCenter=lambda: notices))
    received = []
    bus.command.connect(lambda name, args: received.append((name, args)))
    bus._observe_sleep = lambda: None
    bus.start()
    assert center.state == 1
    assert center.info["MPMediaItemPropertyArtist"] == "First, Second"
    assert center.info["MPMediaItemPropertyPlaybackDuration"] == 120
    assert center.info["MPNowPlayingInfoPropertyElapsedPlaybackTime"] == 5
    assert remotes["nextTrackCommand"].enabled and not remotes["previousTrackCommand"].enabled
    updates = center.updates
    bus.publish(snapshot(position=6000000))
    assert center.updates == updates
    bus.seeked(30)
    assert center.info["MPNowPlayingInfoPropertyElapsedPlaybackTime"] == 30
    bus.publish(snapshot("Paused"))
    assert center.state == 2 and center.info["MPNowPlayingInfoPropertyPlaybackRate"] == 0
    remotes["togglePlayPauseCommand"].handlers[0](None)
    assert remotes["changePlaybackPositionCommand"].handlers[0](SimpleNamespace(positionTime=lambda: 42.5)) == 0
    assert received == [("PlayPause", []), ("SetPosition", ["/track/1", 42500000])]
    bus.close()
    assert center.info is None and center.state == 3
    assert all(remote.removed == [1] for remote in remotes.values())


def test_missing_local_artwork_is_skipped(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    remotes = {name: Remote() for name, _, _ in COMMANDS}
    commands = SimpleNamespace(**{name: (lambda remote: lambda: remote)(remote) for name, remote in remotes.items()})
    center = Center()
    bus = MacBus(snapshot(art=str(tmp_path / "missing.jpg")), media=KEYS, center=center, commands=commands)
    bus._observe_sleep = lambda: None
    bus.start()
    assert "MPMediaItemPropertyArtwork" not in center.info
    bus.close()
