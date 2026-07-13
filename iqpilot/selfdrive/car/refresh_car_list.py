#!/usr/bin/env python3
"""
Copyright © IQ.Lvbs, apart of Project Teal Lvbs, All Rights Reserved, licensed under https://konn3kt.com/tos

Refreshes the "CarList" param from the shipped car_list.json (the supported-platform
manifest). Standalone maintenance entry point; a no-op when the manifest is missing
or already matches the stored value.
"""
import json
import os

from openpilot.common.basedir import BASEDIR
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog

_CANDIDATE_PARTS = (
  ("opendbc", "iqpilot", "car", "car_list.json"),
  ("opendbc_repo", "opendbc", "iqpilot", "car", "car_list.json"),
  ("iqpilot", "selfdrive", "car", "car_list.json"),
)


def _locate_manifest() -> str | None:
  for parts in _CANDIDATE_PARTS:
    candidate = os.path.join(BASEDIR, *parts)
    if os.path.isfile(candidate):
      return candidate
  return None


def refresh_car_list_param() -> None:
  manifest = _locate_manifest()
  if manifest is None:
    cloudlog.warning("car_list.json not found in known paths; leaving CarList param unchanged")
    return

  with open(manifest) as fh:
    platforms = json.load(fh)

  params = Params()
  if params.get("CarList") == platforms:
    cloudlog.warning("CarList param already current, nothing to write")
    return

  params.put("CarList", platforms)
  cloudlog.warning("CarList param refreshed from car_list.json")


if __name__ == "__main__":
  refresh_car_list_param()
