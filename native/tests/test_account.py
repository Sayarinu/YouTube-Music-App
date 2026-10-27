from PySide6.QtCore import QCoreApplication, QEventLoop, QObject, QTimer, Signal
import sys

from youtube_music_native.account import Account
from youtube_music_native.jobs import Worker


class FakeWorker(QObject):
    succeeded = Signal(int, dict)
    failed = Signal(int, dict)

    def __init__(self):
        super().__init__()
        self.requests = []

    def request(self, operation, payload=None):
        self.requests.append((operation, payload))
        return len(self.requests)


def test_restore_and_failed_reconnect_keep_cached_identity(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    worker = FakeWorker()
    account = Account(tmp_path / "settings.ini", worker=worker)
    changes = []
    account.sessionChanged.connect(lambda: changes.append(True))
    app.processEvents()
    assert worker.requests == [("restore", None)]
    worker.succeeded.emit(1, {"connected": True, "profile": {"name": "Listener"}})
    account.requireReconnect("Session expired")
    assert not account.connected and account.reconnect
    account.importTauri()
    worker.failed.emit(2, {"code": "offline", "message": "Offline"})
    assert account.profile["name"] == "Listener"
    assert account.reconnect and not account.busy
    assert changes == []
    account.importTauri()
    worker.succeeded.emit(3, {"connected": True, "profile": {"name": "Listener"}})
    assert account.connected and not account.reconnect
    assert changes == [True]
    account.signOut()
    worker.succeeded.emit(4, {"connected": False, "profile": {}})
    assert not account.connected and account.profile == {}
    assert changes == [True, True]


def test_provider_requests_are_asynchronous_and_errors_are_sanitized():
    app = QCoreApplication.instance() or QCoreApplication([])
    worker = Worker()
    loop = QEventLoop()
    results = []
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(True))
    timer.start(1)

    def failed(identifier, error):
        results.append((identifier, error))
        if len(results) == 2:
            loop.quit()

    worker.failed.connect(failed)
    worker.request("unknown", {"private": "never echo this"})
    cancelled = worker.request("unknown")
    worker.cancelQueued(cancelled)
    worker.request("unknown")
    QTimer.singleShot(10000, loop.quit)
    loop.exec()
    timer.stop()
    worker.close()
    assert [identifier for identifier, _ in results] == [1, 3]
    assert ticks
    assert "never echo" not in str(results)
    # Headless CI may have no unlocked OS vault; neither error exposes payloads.
    assert all(error["code"] in {"AuthError", "CredentialError"} for _, error in results)


def test_idle_worker_releases_process_and_starts_again_for_next_request():
    app = QCoreApplication.instance() or QCoreApplication([])
    worker = Worker(idle_ms=5)
    loop = QEventLoop()
    results, starts = [], []
    worker.process.started.connect(lambda: starts.append(True))

    def failed(identifier, error):
        results.append(identifier)
        if identifier == 1:
            QTimer.singleShot(100, lambda: worker.request("unknown"))
        else:
            loop.quit()

    worker.failed.connect(failed)
    worker.request("unknown")
    QTimer.singleShot(10000, loop.quit)
    loop.exec()
    worker.close()
    assert results == [1, 2] and len(starts) == 2


def test_cancelling_an_active_job_preserves_later_queued_work():
    app = QCoreApplication.instance() or QCoreApplication([])
    worker = Worker()
    worker.process.setArguments(["-u", "-c", "import json,sys,time\nfor line in sys.stdin:\n r=json.loads(line)\n if r['operation']=='slow': time.sleep(5)\n print(json.dumps({'id':r['id'],'ok':True,'result':{}}),flush=True)"])
    worker.process.setProgram(sys.executable)
    loop = QEventLoop()
    results, failures = [], []
    worker.succeeded.connect(lambda identifier, value: (results.append(identifier), loop.quit() if len(results) == 2 else None))
    worker.failed.connect(lambda identifier, error: failures.append(identifier))
    slow = worker.request("slow")
    second = worker.request("fast")
    def cancel_active():
        if not worker._active:
            QTimer.singleShot(10, cancel_active)
            return
        worker.cancel(slow)
        worker.request("fast")
    QTimer.singleShot(30, cancel_active)
    QTimer.singleShot(2000, loop.quit)
    loop.exec()
    worker.close()
    assert results == [second, 3] and not failures


class FakeSignIn(QObject):
    def __init__(self):
        super().__init__()
        self.launches, self.killed = [], 0

    def __call__(self, owner, mode, profile, done):
        self.launches.append((mode, profile, done))
        return self

    def kill(self):
        self.killed += 1

    def waitForFinished(self, timeout):
        return True


def signed_in_account(tmp_path, monkeypatch, clock):
    from youtube_music_native import signin

    monkeypatch.setattr(signin, "available", lambda: True)
    app = QCoreApplication.instance() or QCoreApplication([])
    worker, launcher = FakeWorker(), FakeSignIn()
    account = Account(tmp_path / "settings.ini", worker=worker, signin_profile=tmp_path / "signin", launcher=launcher, clock=lambda: clock[0])
    app.processEvents()
    return account, worker, launcher


def test_google_sign_in_hands_cookies_to_the_worker_and_cancel_is_quiet(tmp_path, monkeypatch):
    clock = [1000.]
    account, worker, launcher = signed_in_account(tmp_path, monkeypatch, clock)
    worker.succeeded.emit(1, {"connected": False, "profile": {}})
    account.signIn()
    assert account.signingIn and launcher.launches[-1][0] == "interactive"
    launcher.launches[-1][2](4, b"")
    assert not account.signingIn and account.message == "" and len(worker.requests) == 1
    account.signIn()
    launcher.launches[-1][2](1, b"")
    assert "didn’t finish" in account.message
    account.signIn()
    launcher.launches[-1][2](3, b"")
    assert "browser session file" in account.message
    account.signIn()
    launcher.launches[-1][2](0, b'{"cookies": [], "user_agent": "Chrome"}\n')
    assert worker.requests[-1] == ("import_cookies", {"cookies": [], "user_agent": "Chrome"})
    changes = []
    account.sessionChanged.connect(lambda: changes.append(True))
    worker.succeeded.emit(2, {"connected": True, "profile": {"name": "Listener"}, "captured": clock[0]})
    assert account.connected and changes == [True]


def test_expired_session_renews_silently_before_asking_and_only_once_per_cooldown(tmp_path, monkeypatch):
    clock = [1000.]
    account, worker, launcher = signed_in_account(tmp_path, monkeypatch, clock)
    (tmp_path / "signin").mkdir()
    worker.succeeded.emit(1, {"connected": True, "profile": {"name": "Listener"}, "captured": clock[0]})
    assert launcher.launches == []
    account.requireReconnect("Session expired")
    assert launcher.launches[-1][0] == "silent" and account.connected and not account.reconnect
    account.requireReconnect("Session expired")
    assert len(launcher.launches) == 1
    launcher.launches[-1][2](0, b'{"cookies": [], "user_agent": "Chrome"}\n')
    worker.succeeded.emit(2, {"connected": True, "profile": {"name": "Listener"}, "captured": clock[0]})
    assert account.connected and not account.reconnect
    account.requireReconnect("Session expired")
    assert len(launcher.launches) == 1 and account.reconnect and account.message == "Session expired"
    clock[0] += 3600
    account.signIn()
    launcher.launches[-1][2](0, b'{"cookies": []}')
    worker.failed.emit(3, {"code": "reconnect", "message": "Reconnect YouTube Music."})
    assert account.reconnect and account.message == "Reconnect YouTube Music."


def test_failed_silent_renewal_raises_the_banner_and_stale_restore_refreshes_quietly(tmp_path, monkeypatch):
    clock = [10 * 24 * 3600.]
    account, worker, launcher = signed_in_account(tmp_path, monkeypatch, clock)
    (tmp_path / "signin").mkdir()
    worker.succeeded.emit(1, {"connected": True, "profile": {"name": "Listener"}, "captured": 1.})
    assert launcher.launches[-1][0] == "silent"
    launcher.launches[-1][2](2, b"")
    assert account.connected and not account.reconnect
    clock[0] += 3600
    account.requireReconnect("Session expired")
    launcher.launches[-1][2](0, b'{"cookies": []}')
    worker.failed.emit(2, {"code": "reconnect", "message": "private provider detail"})
    assert account.reconnect and account.message == "Session expired"


def test_sign_out_stops_sign_in_and_forgets_the_google_profile(tmp_path, monkeypatch):
    account, worker, launcher = signed_in_account(tmp_path, monkeypatch, [1000.])
    worker.succeeded.emit(1, {"connected": True, "profile": {"name": "Listener"}})
    (tmp_path / "signin").mkdir()
    (tmp_path / "signin" / "Cookies").write_text("private")
    account.signIn()
    account.signOut()
    assert launcher.killed == 1 and not account.signingIn
    assert not (tmp_path / "signin").exists()
    assert worker.requests[-1] == ("sign_out", None)
    launcher.launches[-1][2](0, b'{"cookies": []}')
    assert worker.requests[-1] == ("sign_out", None)
