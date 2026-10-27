"""Google sign-in window, run in its own process so Chromium never stays loaded in the player.

Like other desktop clients, the user signs in on Google's own page; the resulting YouTube cookies are
written once to stdout for the provider worker to validate and store in the OS keyring.
"""

import json
import re
import sys

SIGN_IN_URL = "https://accounts.google.com/ServiceLogin?service=youtube&continue=https%3A%2F%2Fmusic.youtube.com%2F"
MUSIC_URL = "https://music.youtube.com/"
DOMAINS = {"youtube.com", "music.youtube.com"}
REQUIRED = {"SAPISID", "__Secure-3PAPISID"}
# 1 is left for Python's own uncaught-exception exit, so a crash never reads as a cancel.
SUCCESS, FAILED, INTERACTIVE, UNAVAILABLE, CANCELLED = 0, 1, 2, 3, 4


def available():
    # Check without importing, so the player process never loads Chromium.
    from importlib.util import find_spec

    try:
        return find_spec("PySide6.QtWebEngineWidgets") is not None
    except (ImportError, ValueError):
        return False


def browser_agent(agent):
    # Google refuses sign-in from embedded engines that announce themselves.
    return re.sub(r"\s*QtWebEngine/\S+", "", agent)


def cookie_row(cookie):
    expiry = cookie.expirationDate()
    return {
        "name": bytes(cookie.name()).decode("utf-8", "replace"),
        "value": bytes(cookie.value()).decode("utf-8", "replace"),
        "domain": cookie.domain(), "path": cookie.path() or "/", "secure": cookie.isSecure(),
        "expires": None if cookie.isSessionCookie() or not expiry.isValid() else int(expiry.toSecsSinceEpoch()),
    }


class Capture:
    """Track the profile's YouTube cookies as Chromium adds, rotates and removes them."""

    def __init__(self):
        self.cookies = {}

    def added(self, cookie):
        row = cookie_row(cookie)
        if row["domain"].lstrip(".") in DOMAINS:
            self.cookies[(row["name"], row["domain"], row["path"])] = row

    def removed(self, cookie):
        row = cookie_row(cookie)
        self.cookies.pop((row["name"], row["domain"], row["path"]), None)

    def signed_in(self):
        return REQUIRED <= {row["name"] for row in self.cookies.values()}

    def rows(self):
        return list(self.cookies.values())


def hide_from_dock():
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyProhibited

        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyProhibited)
    except ImportError:
        pass


def main(args):
    if len(args) != 2 or args[0] not in {"interactive", "silent"}:
        print("usage: --sign-in-worker interactive|silent PROFILE_DIR", file=sys.stderr)
        return FAILED
    silent, storage = args[0] == "silent", args[1]
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication

    try:
        from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
        from PySide6.QtWebEngineWidgets import QWebEngineView
    except ImportError:
        # The binding can exist without the Qt WebEngine libraries on some Linux distributions.
        return UNAVAILABLE

    QGuiApplication.setOrganizationName("YouTubeMusicNative")
    QGuiApplication.setOrganizationDomain("com.carter")
    QGuiApplication.setApplicationName("youtube-music-native")
    QGuiApplication.setApplicationDisplayName("Tubify")
    app = QApplication([sys.argv[0]])
    if silent:
        hide_from_dock()
    try:
        from PySide6.QtWebEngineCore import QWebEngineProfileBuilder
    except ImportError:
        profile = QWebEngineProfile("signin", app)
        profile.setPersistentStoragePath(storage)
        profile.setCachePath(storage + "/cache")
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
    else:
        builder = QWebEngineProfileBuilder()
        builder.setPersistentStoragePath(storage)
        builder.setCachePath(storage + "/cache")
        # Google marks some sign-in cookies session-only; keep them so expiry can renew silently.
        builder.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        profile = builder.createProfile("signin", app)
    agent = browser_agent(profile.httpUserAgent())
    profile.setHttpUserAgent(agent)
    capture = Capture()
    store = profile.cookieStore()
    store.cookieAdded.connect(capture.added)
    store.cookieRemoved.connect(capture.removed)
    store.loadAllCookies()
    result = {"code": INTERACTIVE if silent else CANCELLED}
    settle = QTimer(app)
    settle.setSingleShot(True)
    # Cookie notifications trail page loads, and the page may rotate cookies just after loading.
    settle.setInterval(4000 if silent else 1500)

    def finish(code):
        if code == SUCCESS:
            sys.stdout.write(json.dumps({"cookies": capture.rows(), "user_agent": agent}) + "\n")
            sys.stdout.flush()
        result["code"] = code
        app.quit()

    def evaluate():
        if page.url().host() == "music.youtube.com" and capture.signed_in():
            finish(SUCCESS)
        elif silent:
            finish(INTERACTIVE)

    def loaded(ok):
        if page.url().host() == "music.youtube.com":
            settle.start()

    settle.timeout.connect(evaluate)
    page = QWebEnginePage(profile)
    page.loadFinished.connect(loaded)
    if silent:
        QTimer.singleShot(20000, lambda: finish(INTERACTIVE))
        page.load(QUrl(MUSIC_URL))
    else:
        view = QWebEngineView()
        view.setPage(page)
        view.setWindowTitle("Sign in to YouTube Music")
        view.resize(480, 720)
        app.setQuitOnLastWindowClosed(True)
        view.show()
        view.raise_()
        view.activateWindow()
        page.load(QUrl(SIGN_IN_URL))
    app.exec()
    import shiboken6

    # Pages must go before their profile, and the profile must close for Chromium to flush cookies.
    if not silent:
        shiboken6.delete(view)
    shiboken6.delete(page)
    shiboken6.delete(profile)
    return result["code"]
