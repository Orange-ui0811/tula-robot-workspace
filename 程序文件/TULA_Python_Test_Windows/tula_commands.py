from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class TULACommandSpec:
    code: str
    category: str    
    params: int
    description: str
    parameter_range: Optional[str] = None
    example: Optional[str] = None


# Command metadata distilled from TULA_command_list.xlsx.
# The current hardware controller is TD-201, but the software-facing driver name is TULA.
COMMAND_SPECS: Dict[str, TULACommandSpec] = {
    # Motion commands, point-to-point.
    "ma": TULACommandSpec(
        code="ma",
        category="motion_ptp",
        params=1,
        description="Move to absolute target position in controller counts.",
        parameter_range="-2147000000..2147000000",
        example=">01ma 1000",
    ),
    "mr": TULACommandSpec(
        code="mr",
        category="motion_ptp",
        params=1,
        description="Move by a relative count offset.",
        parameter_range="-2147000000..2147000000",
        example=">01mr 100",
    ),
    "hm": TULACommandSpec("hm", "motion_ptp", 0, "Move to home sensor.", None, ">01hm"),
    "auto": TULACommandSpec("auto", "motion_ptp", 0, "Run automatic stage tuning.", None, ">01auto"),
    "st": TULACommandSpec("st", "motion_ptp", 0, "Abort motion immediately.", None, ">01st"),
    # Open-loop commands.
    "on": TULACommandSpec("on", "open_loop", 1, "Define moving on-time or pulse.", "1..6000000", ">01on 1000"),
    "off": TULACommandSpec("off", "open_loop", 1, "Define time between starts of each step.", "1..600000", ">01off 1000"),
    "cy": TULACommandSpec("cy", "open_loop", 1, "Define optional run count.", "1..2147000000", ">01cy 10"),
    "re": TULACommandSpec("re", "open_loop", 0, "Run motor in reverse.", None, ">01re"),
    "fo": TULACommandSpec("fo", "open_loop", 0, "Run motor forward.", None, ">01fo"),
    "bi": TULACommandSpec("bi", "open_loop", 0, "Move in both directions.", None, ">01bi"),
    # Status commands.
    "cp": TULACommandSpec("cp", "status", 0, "Report current encoder position.", None, ">01cp"),
    "al": TULACommandSpec("al", "status", 0, "Get alarm/status word.", None, ">01al"),
    "info": TULACommandSpec("info", "status", 0, "Report controller settings.", None, ">01info"),
    "ver": TULACommandSpec("ver", "status", 0, "Get firmware version.", None, ">01ver"),
    # Configuration commands.
    "freq": TULACommandSpec("freq", "configuration", 1, "Set driving frequency.", "20..100", ">01freq 68"),
    "duty": TULACommandSpec("duty", "configuration", 1, "Set open-loop duty.", "1..48", ">01duty 25"),
    "volt": TULACommandSpec("volt", "configuration", 1, "Set voltage. Axis 1 only on TD-201.", "16..35", ">01volt 30"),
    "enc": TULACommandSpec("enc", "configuration", 1, "Set encoder type. 1=A/B, 2=A/B/Z.", "1..2", ">01enc 2"),
    "res": TULACommandSpec("res", "configuration", 1, "Set encoder resolution in nm.", "10,100,1000,5000", ">01res 1000"),
    "swap": TULACommandSpec("swap", "configuration", 1, "Swap encoder A/B inputs.", "0..1", ">01swap 1"),
    "mid": TULACommandSpec("mid", "configuration", 1, "Set motor current direction.", "0..1", ">01mid 1"),
    "vel": TULACommandSpec("vel", "configuration", 1, "Set velocity.", "1..100", ">01vel 100"),
    "reset": TULACommandSpec("reset", "configuration", 0, "Warm-start controller.", None, ">01reset"),
    "offset": TULACommandSpec("offset", "configuration", 1, "Set home offset.", "-2147000000..2147000000", ">01offset 100"),
    "save": TULACommandSpec("save", "configuration", 0, "Save current configuration to flash.", None, ">01save"),
    "message": TULACommandSpec("message", "configuration", 1, "Set RS-485 receive data on/off.", "0..1", ">01message 0"),
    "inp": TULACommandSpec("inp", "configuration", 1, "Set in-position tolerance in counts.", "0..1000", ">01inp 10"),
    "baudrate": TULACommandSpec("baudrate", "configuration", 1, "Set serial baud rate.", "2400..921600", ">01baudrate 19200"),
    # Control filter commands.
    "kp": TULACommandSpec("kp", "control_filter", 1, "Position loop proportional gain.", "0..32767", ">01kp 100"),
    "ki": TULACommandSpec("ki", "control_filter", 1, "Velocity loop integral gain.", "0..32767", ">01ki 90"),
    "kd": TULACommandSpec("kd", "control_filter", 1, "Velocity loop derivative gain.", "0..32767", ">01kd 10"),
    "kf": TULACommandSpec("kf", "control_filter", 1, "Position controller IIR filter parameter.", "0..32767", ">01kf 1000"),
}


STATUS_BITS: Dict[int, str] = {
    0x8000: "MOTOR_RUNNING",
    0x2000: "AUTO_TUNING",
    0x1000: "HOME_MISSING",
    0x0400: "PULSE_DIR_OPEN",
    0x0200: "PULSE_DIR",
    0x0100: "ILLEGAL_CMD",
    0x0080: "PARAMETER_ERR",
    0x0010: "ENCODER_ERR",
    0x0008: "POSITION_ERR",
    0x0004: "ENCODER_Z_ERR",
    0x0001: "OVER_TEMP",
}


ERROR_STATUS_BITS: Tuple[int, ...] = (
    0x2000,
    0x0100,
    0x0080,
    0x0010,
    0x0008,
    0x0004,
    0x0001,
)


def get_command_spec(code: str) -> TULACommandSpec:
    try:
        return COMMAND_SPECS[code.lower()]
    except KeyError as exc:
        raise KeyError(f"Unknown TULA command: {code}") from exc
