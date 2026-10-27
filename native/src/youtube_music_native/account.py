"""Non-blocking account state exposed to QML; credentials remain in the worker."""

import json
from pathlib import Path
import shutil
import sys
import time

from PySide6.QtCore import QObject, Property, QProcess, QSettings, QStandardPaths, QTimer, QUrl, Signal, Slot

from . import signin
from .jobs import Worker
from .launcher import process_command

RENEW_AFTER = 7 * 24 * 3600
RENEW_COOLDOWN = 10 * 60


def launch_sign_in(owner, mode, profile, done):
    """Run the Google sign-in process; done(exit_code, stdout) fires once."""
    process = QProcess(owner)
    command = process_command("signin")
    process.setProgram(command[0])
    process.setArguments([*command[1:], mode, str(profile)])
    process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
    process.readyReadStandardError.connect(lambda: process.readAllStandardError())
    output = bytearray()
    process.readyReadStandardOutput.connect(lambda: output.extend(bytes(process.readAllStandardOutput())))

    def finished(code, status):
        output.extend(bytes(process.readAllStandardOutput()))
        process.deleteLater()
        done(code if status == QProcess.ExitStatus.NormalExit else signin.FAILED, bytes(output))

    process.finished.connect(finished)
    process.errorOccurred.connect(lambda error: error == QProcess.ProcessError.FailedToStart and finished(signin.FAILED, QProcess.ExitStatus.CrashExit))
    process.start()
    return process


class Account(QObject):
    changed = Signal()
    connectedChanged = Signal()
    sessionChanged = Signal()

    def __init__(self, settings_path, fixture=False, worker=None, parent=None, signin_profile=None, launcher=launch_sign_in, clock=time.time):
        super().__init__(parent)
        self._signin_profile = Path(signin_profile) if signin_profile else Path(settings_path).parent / "signin-profile"
        self._launcher, self._clock = launcher, clock
        self._signin = None
        self._signin_mode = ""
        self._renew_message = ""
        self._last_renewal = None
        self._pending = None
        self._operation_mode = ""
        self.settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
        self._fixture = fixture
        self.worker = None if fixture else (worker if worker is not None else Worker(self))
        self._request = None
        self._operation = ""
        self._busy = False
        self._connected = False
        self._reconnect = False
        self._message = ""
        try:
            self._profile = json.loads(self.settings.value("accountProfile", "{}"))
            if not isinstance(self._profile, dict):
                self._profile = {}
        except (ValueError, TypeError):
            self._profile = {}
        if fixture:
            self._profile = {"name": "Your music", "handle": "", "avatar": ""}
        else:
            self.worker.succeeded.connect(self._succeeded)
            self.worker.failed.connect(self._failed)
            QTimer.singleShot(0, self.restore)

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(bool, notify=connectedChanged)
    def connected(self):
        return self._connected and not self._reconnect

    @Property(bool, notify=changed)
    def reconnect(self):
        return self._reconnect

    @Property(str, notify=changed)
    def message(self):
        return self._message

    @Property("QVariantMap", notify=changed)
    def profile(self):
        return self._profile

    @Property(bool, constant=True)
    def fixtureMode(self):
        return self._fixture

    @Property(bool, constant=True)
    def signInAvailable(self):
        return not self._fixture and signin.available()

    @Property(bool, notify=changed)
    def signingIn(self):
        return self._signin_mode == "interactive"

    @Property(bool, constant=True)
    def tauriAvailable(self):
        return sys.platform == "linux" and self._tauri_path().is_file()

    def _tauri_path(self):
        return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)) / "com.carter.youtube-music" / "cookies"

    def _send(self, operation, payload=None):
        if self.worker is None:
            return
        if self._busy:
            if operation == "import_cookies":
                self._pending = (operation, payload)
            return
        self._operation = operation
        self._busy = True
        self._message = ""
        self._request = self.worker.request(operation, payload)
        self.changed.emit()

    @Slot()
    def restore(self):
        self._send("restore")

    @Slot()
    def importTauri(self):
        self._send("import_session", {"path": str(self._tauri_path()), "tauri": True})

    @Slot(QUrl)
    def importFile(self, url):
        if url.isLocalFile():
            self._send("import_session", {"path": url.toLocalFile()})

    @Slot()
    def signIn(self):
        if self.signInAvailable and self._signin_mode != "interactive":
            self._stop_sign_in()
            self._start_sign_in("interactive")

    def renew(self, message=""):
        """Reuse the sign-in profile's Google session without showing a window; False if not attempted."""
        now = self._clock()
        if (self._signin is not None or not self.signInAvailable or not self._signin_profile.is_dir()
                or self._last_renewal is not None and now - self._last_renewal < RENEW_COOLDOWN):
            return False
        self._last_renewal = now
        self._renew_message = message
        self._start_sign_in("silent")
        return True

    def _start_sign_in(self, mode):
        self._signin_profile.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._signin_mode = mode
        self._message = "Finish signing in with Google in the sign-in window." if mode == "interactive" else self._message
        self._signin = self._launcher(self, mode, self._signin_profile, lambda code, output: self._signed_in(mode, code, output))
        self.changed.emit()

    def _stop_sign_in(self):
        process, self._signin, self._signin_mode = self._signin, None, ""
        if process is not None:
            process.blockSignals(True)
            process.kill()
            process.waitForFinished(2000)

    def _signed_in(self, mode, code, output):
        if self._signin_mode != mode:
            return
        self._signin, self._signin_mode = None, ""
        payload = None
        if code == signin.SUCCESS:
            try:
                payload = json.loads(output.decode("utf-8").strip().splitlines()[-1])
            except (UnicodeDecodeError, ValueError, IndexError):
                payload = None
        if isinstance(payload, dict):
            self._operation_mode = mode
            self._send("import_cookies", payload)
        elif mode == "silent":
            self._renewal_failed()
        else:
            self._message = {signin.CANCELLED: "", signin.UNAVAILABLE: "Google sign-in needs Qt WebEngine on this system. Choose a browser session file instead."}.get(code, "Google sign-in didn’t finish. Try again.")
            self.changed.emit()

    def _renewal_failed(self):
        message, self._renew_message = self._renew_message, ""
        if message:
            # Only a renewal triggered by an expired session raises the banner.
            self._set_reconnect(message)
        else:
            self.changed.emit()

    @Slot()
    def signOut(self):
        self._stop_sign_in()
        # Forget Google's sign-in too, so silent renewal cannot reconnect a signed-out account.
        shutil.rmtree(self._signin_profile, ignore_errors=True)
        self._send("sign_out")

    @Slot(str)
    def requireReconnect(self, message):
        if self._signin_mode == "silent":
            return
        if not self.renew(message):
            self._set_reconnect(message)

    def _set_reconnect(self, message):
        self._reconnect = True
        self._message = message
        self.changed.emit()
        self.connectedChanged.emit()

    def _succeeded(self, identifier, result):
        if identifier != self._request:
            return
        self._request = None
        self._busy = False
        self._connected = bool(result.get("connected"))
        self._reconnect = False
        self._profile = result.get("profile") or {}
        self._message = "Connected to YouTube Music." if self._connected else ""
        self.settings.setValue("accountProfile", json.dumps(self._profile))
        self.settings.sync()
        self.changed.emit()
        self.connectedChanged.emit()
        if self._operation in {"import_session", "import_cookies", "sign_out"}:
            self.sessionChanged.emit()
        if self._operation == "import_cookies":
            self._renew_message = ""
        captured = result.get("captured") or 0
        if self._operation == "restore" and self._connected and captured and self._clock() - captured > RENEW_AFTER:
            # Refresh rotating Google cookies before they lapse; failure leaves the current session alone.
            self.renew()
        self._dispatch_pending()

    def _failed(self, identifier, error):
        if identifier != self._request:
            return
        self._request = None
        self._busy = False
        self._message = error.get("message", "Reconnect YouTube Music.")
        if self._operation == "restore":
            self._reconnect = True
        if self._operation == "import_cookies" and self._operation_mode == "silent":
            self._message = ""
            self._renewal_failed()
        self.changed.emit()
        self.connectedChanged.emit()
        self._dispatch_pending()

    def _dispatch_pending(self):
        if self._pending and not self._busy:
            operation, payload = self._pending
            self._pending = None
            self._send(operation, payload)

    def close(self):
        self._stop_sign_in()
        if self.worker:
            self.worker.close()
