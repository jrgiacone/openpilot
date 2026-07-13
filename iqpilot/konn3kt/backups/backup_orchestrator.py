"""
Copyright © IQ.Lvbs, apart of Project Teal Lvbs, All Rights Reserved, licensed under https://konn3kt.com/tos

Offroad daemon that drives cloud backup/restore of the device's params. It watches
two request params, runs the seal→upload / download→unseal→apply flow, and streams
progress + status out over the backupManagerK3 message so the app can follow along.
"""
import json
import time
import asyncio
import traceback
from enum import Enum
from typing import Any
from datetime import datetime

from openpilot.common.params import Params
from openpilot.common.realtime import Ratekeeper
from openpilot.common.swaglog import cloudlog
from openpilot.system.hardware import HARDWARE

from cereal import messaging, custom
from iqpilot.konn3kt.api import Konn3ktApi
from iqpilot.konn3kt.backups.imahelper import ImaHelper, ImaRemoteRecord
from iqpilot.konn3kt.backups.archive_codec import unseal_backup_blob, seal_backup_blob, SnakeKeyEncoder

_DEBUG_LOG = "/data/openpilot/k3_log.txt"
_Status = custom.IQBackupManager.Phase
_CREATE_REQUEST = "BackupManagerK3_CreateBackup"
_RESTORE_REQUEST = "BackupManagerK3_RestoreVersion"


def k3_log(msg: str) -> None:
  try:
    with open(_DEBUG_LOG, "a") as fh:
      stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
      fh.write(f"[{stamp}] {msg}\n")
      fh.flush()
  except Exception as e:
    cloudlog.error(f"[K3] Failed to write to debug log: {e}")


k3_log("=== K3 Backup Manager Module Loaded ===")


class Phase(Enum):
  BACKUP = "backup"
  RESTORE = "restore"


class BackupOrchestrator:
  def __init__(self):
    k3_log("BackupManagerK3 initializing...")
    self.params = Params()
    self.device_id = self.params.get("DongleId")
    k3_log(f"Device ID: {self.device_id}")
    self.api = Konn3ktApi(self.device_id)
    self.imahelper = ImaHelper(self.params)
    self.pm = messaging.PubMaster(["backupManagerK3"])

    self.backup_status = _Status.idle
    self.restore_status = _Status.idle
    self.progress = 0.0
    self.operation: Phase | None = None
    self.last_error = ""
    k3_log("BackupManagerK3 initialized successfully")

  # -- status stream ------------------------------------------------------------
  def _report_status(self) -> None:
    msg = messaging.new_message('backupManagerK3', valid=True)
    state = msg.backupManagerK3
    state.savePhase = self.backup_status
    state.loadPhase = self.restore_status
    state.saveProgress = self.progress
    state.loadProgress = self.progress
    state.faultText = self.last_error
    self.pm.send('backupManagerK3', msg)

  def _advance(self, progress: float, phase: Phase) -> None:
    self.progress = progress
    self.operation = phase
    self._report_status()

  def _fail(self, phase: Phase, err: str) -> None:
    if phase is Phase.BACKUP:
      self.backup_status = _Status.failed
    else:
      self.restore_status = _Status.failed
    self.last_error = err
    self._report_status()

  @staticmethod
  def _snake_payload(backup_info: custom.IQBackupManager.Snapshot) -> dict[str, Any]:
    return json.loads(json.dumps(backup_info.to_dict(), cls=SnakeKeyEncoder))

  # -- backup -------------------------------------------------------------------
  async def create_backup(self) -> bool:
    k3_log("create_backup() called")
    try:
      self.backup_status = _Status.inProgress
      self._advance(0.0, Phase.BACKUP)

      snapshot = self.imahelper.capture_entries()
      k3_log(f"Collected {len(snapshot.entries)} backup entries")
      self._advance(25.0, Phase.BACKUP)

      sealed = seal_backup_blob(json.dumps(snapshot.entries), use_aes_256=True)
      k3_log(f"Encrypted config length: {len(sealed)}")
      self._advance(50.0, Phase.BACKUP)

      payload = self._snake_payload(self.imahelper.build_backup_info(self.device_id, sealed))
      self._advance(75.0, Phase.BACKUP)

      k3_log(f"Uploading backup to api/v2/backup/{self.device_id}")
      cloudlog.debug(f"[K3] Uploading backup with payload: {json.dumps(payload)}")
      result = self.api.api_get(f"api/v2/backup/{self.device_id}", method='PUT',
                                access_token=self.api.get_token(), json=payload)
      k3_log(f"API result: {result}")

      if not result:
        k3_log(f"Backup upload failed: {result}")
        self._fail(Phase.BACKUP, "Failed to upload backup")
        cloudlog.error(f"[K3] {result}")
        return False

      k3_log("Backup upload successful!")
      self.backup_status = _Status.completed
      self._advance(100.0, Phase.BACKUP)
      cloudlog.info("[K3] Backup successfully created and uploaded")
      return True

    except Exception as e:
      k3_log(f"Exception in create_backup: {type(e).__name__}: {str(e)}")
      k3_log(f"Traceback: {traceback.format_exc()}")
      cloudlog.exception(f"[K3] Error creating backup: {str(e)}")
      self._fail(Phase.BACKUP, str(e))
      return False

  # -- restore ------------------------------------------------------------------
  def _fetch_remote_record(self, version: int | None) -> ImaRemoteRecord:
    endpoint = f"api/v2/backup/{self.device_id}" + (f"/{version}" if version else "")
    k3_log(f"Fetching backup from endpoint: {endpoint}")
    response = self.api.api_get(endpoint, access_token=self.api.get_token())
    k3_log(f"API response: {response}")
    if not response:
      raise Exception(f"No backup found for device {self.device_id}")
    data = response.json()
    k3_log(f"Parsed JSON data, keys: {data.keys() if data else None}")
    return self.imahelper.read_remote_record(data)

  async def restore_backup(self, version: int | None = None) -> bool:
    k3_log(f"restore_backup() called with version={version}")
    try:
      self.restore_status = _Status.inProgress
      self._advance(0.0, Phase.RESTORE)

      record = self._fetch_remote_record(version)
      self._advance(25.0, Phase.RESTORE)
      k3_log(f"Encrypted config length: {len(record.encrypted_config)}")
      self._advance(50.0, Phase.RESTORE)

      aes_256 = record.metadata.get("AES", "128") == "256"
      k3_log(f"Using AES-256: {aes_256}")
      config_json = unseal_backup_blob(record.encrypted_config, aes_256)
      k3_log(f"Decrypted config length: {len(config_json) if config_json else 0}")
      if not config_json:
        raise Exception("Failed to decrypt backup configuration")

      config_data = json.loads(config_json)
      k3_log(f"Parsed config data, {len(config_data)} params")
      self._advance(75.0, Phase.RESTORE)

      k3_log("Applying configuration...")
      report = self.imahelper.absorb_entries(config_data)
      cloudlog.info(f"[K3] Restore complete: {report.restored_count} restored, "
                    f"{report.skipped_count} skipped, calibration={report.restored_calibration}, "
                    f"model={report.restored_model}")

      k3_log("Restore completed successfully!")
      self.restore_status = _Status.completed
      self._advance(100.0, Phase.RESTORE)
      cloudlog.info("[K3] Backup successfully restored")
      self._reboot_after_restore()
      return True

    except Exception as e:
      k3_log(f"Exception in restore_backup: {type(e).__name__}: {str(e)}")
      k3_log(f"Traceback: {traceback.format_exc()}")
      cloudlog.exception(f"[K3] Error restoring backup: {str(e)}")
      self._fail(Phase.RESTORE, str(e))
      return False

  def _reboot_after_restore(self) -> None:
    # Reboot so calibrationd/paramsd/torqued seed from the restored values at init instead of
    # overwriting them mid-session, and so SecOC / model / every param applies from a clean start.
    try:
      time.sleep(3)  # let the app read the 'completed' status before the device goes down
      k3_log("Rebooting device to finish restore")
      cloudlog.info("[K3] Rebooting to finish restore")
      HARDWARE.reboot()
    except Exception as e:
      cloudlog.error(f"[K3] Reboot after restore failed: {e}")

  # -- request handlers ---------------------------------------------------------
  async def _handle_create_request(self) -> bool:
    k3_log("Detected BackupManagerK3_CreateBackup")
    try:
      ok = await self.create_backup()
      k3_log(f"create_backup() returned {ok}")
      return ok
    finally:
      k3_log("Removing BackupManagerK3_CreateBackup param")
      self.params.remove(_CREATE_REQUEST)

  async def _handle_restore_request(self, raw_version) -> None:
    k3_log(f"Detected BackupManagerK3_RestoreVersion = {raw_version} ({type(raw_version)})")
    try:
      text = raw_version.decode('utf-8') if isinstance(raw_version, bytes) else raw_version
      version = int(text) if text.isdigit() else None
      k3_log(f"Parsed version number: {version}")
      result = await self.restore_backup(version)
      k3_log(f"restore_backup() returned: {result}")
    except Exception as e:
      k3_log(f"Exception during restore: {type(e).__name__}: {str(e)}")
      k3_log(f"Traceback: {traceback.format_exc()}")
    finally:
      k3_log("Removing BackupManagerK3_RestoreVersion param")
      self.params.remove(_RESTORE_REQUEST)

  def _reset_idle(self) -> None:
    self.progress = 100.0
    self.operation = None
    self.restore_status = _Status.idle
    self.backup_status = _Status.idle

  async def main_thread(self) -> None:
    k3_log("main_thread() starting")
    # a prior restore may have queued a model download to re-trigger post-reboot
    self.imahelper.revive_pending_model_download()
    rk = Ratekeeper(1, print_delay_threshold=None)
    settle = False

    k3_log("Entering main loop")
    while True:
      try:
        if settle:
          self._reset_idle()

        if self.params.get_bool(_CREATE_REQUEST):
          if await self._handle_create_request():
            settle = True

        raw_version = self.params.get(_RESTORE_REQUEST)
        if raw_version:
          await self._handle_restore_request(raw_version)
          settle = True

        self._report_status()
        rk.keep_time()

      except Exception as e:
        k3_log(f"Exception in main_thread: {type(e).__name__}: {str(e)}")
        k3_log(f"Traceback: {traceback.format_exc()}")
        cloudlog.exception(f"[K3] Error in backup manager main thread: {str(e)}")
        self.last_error = str(e)
        self._report_status()
        rk.keep_time()


def main():
  k3_log("main() function called, starting BackupManagerK3")
  asyncio.run(BackupOrchestrator().main_thread())


if __name__ == "__main__":
  main()
