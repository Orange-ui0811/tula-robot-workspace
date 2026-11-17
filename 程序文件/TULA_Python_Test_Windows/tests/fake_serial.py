from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List


class FakeSerial:
    """Small TD-201/TULA serial emulator for offline unit tests."""

    def __init__(self) -> None:
        self.is_open = True
        self.writes: List[str] = []
        self.rx = bytearray()
        self.positions: Dict[str, int] = defaultdict(int)
        self.statuses: Dict[str, int] = defaultdict(int)
        self.scripted: Dict[str, List[str]] = {}

    @property
    def in_waiting(self) -> int:
        return len(self.rx)

    def reset_input_buffer(self) -> None:
        self.rx.clear()

    def reset_output_buffer(self) -> None:
        return None

    def write(self, data: bytes) -> int:
        cmd = data.decode("ascii").strip()
        self.writes.append(cmd)
        response = self._response_for(cmd)
        self.rx.extend(response.encode("ascii"))
        return len(data)

    def flush(self) -> None:
        return None

    def read(self, size: int) -> bytes:
        chunk = self.rx[:size]
        del self.rx[:size]
        return bytes(chunk)

    def close(self) -> None:
        self.is_open = False

    def script_once(self, cmd: str, response: str) -> None:
        self.scripted.setdefault(cmd, []).append(response)

    def _response_for(self, cmd: str) -> str:
        scripted_responses = self.scripted.get(cmd)
        if scripted_responses:
            return scripted_responses.pop(0)

        match = re.fullmatch(r">(\d{2})([A-Za-z]+)(?:\s+(-?\d+))?", cmd)
        if not match:
            return ""

        axis, code, value_text = match.groups()
        value = int(value_text) if value_text is not None else None

        if code == "ver":
            return f"<{axis}ver 221228 132"
        if code == "info":
            return (
                f"<{axis}freq 68"
                f"<{axis}volt 25"
                f"<{axis}enc 2"
                f"<{axis}res 72000"
                f"<{axis}vel 20"
                f"<{axis}lm -1000000000"
                f"<{axis}lp 1000000000"
            )
        if code == "al":
            status = self.statuses[axis]
            return f"<{axis}status {status} ({status:x})"
        if code == "cp":
            return f"<{axis}cp {self.positions[axis]}"
        if code == "hm":
            self.positions[axis] = 0
            self.statuses[axis] = 0
            return f"<{axis}hm<{axis}status 0 (0)"
        if code == "ma" and value is not None:
            self.positions[axis] = value
            self.statuses[axis] = 0
            return f"<{axis}ma {value}<{axis}status 0 (0)"
        if code == "mr" and value is not None:
            self.positions[axis] += value
            self.statuses[axis] = 0
            return f"<{axis}mr {self.positions[axis]}<{axis}status 0 (0)"
        if code == "st":
            self.statuses[axis] = 0
            return f"<{axis}st"
        if code in {"on", "off", "cy"} and value is not None:
            return f"<{axis}{code} {value}"
        if code in {"fo", "re", "bi"}:
            return f"<{axis}{code}"

        return f"<{axis}{code}"
