from __future__ import annotations

import argparse

from tula_motor_bus import TULAMotor, TULAMotorsBus


def main() -> None:
    parser = argparse.ArgumentParser(description="TULA LeRobot-shaped motor bus example")
    parser.add_argument("--port", default="COM4", help="Serial port, for example COM4 or COM5")
    parser.add_argument("--move", action="store_true", help="Send a small raw-count test move")
    parser.add_argument("--target-1", type=int, default=500, help="Axis 1 target in raw counts")
    parser.add_argument("--target-2", type=int, default=800, help="Axis 2 target in raw counts")
    args = parser.parse_args()

    bus = TULAMotorsBus(
        port=args.port,
        motors={
            "joint_1": TULAMotor(id=1),
            "joint_2": TULAMotor(id=2),
        },
    )

    try:
        bus.connect(handshake=True)
        print("Positions counts:", bus.sync_read("Present_Position", normalize=False))
        print("Positions degrees:", bus.sync_read("Present_Position", normalize=True))
        print("Status:", bus.sync_read("Status_Names"))

        if args.move:
            bus.sync_write(
                "Goal_Position",
                {"joint_1": args.target_1, "joint_2": args.target_2},
                normalize=False,
            )
            print("Positions after move counts:", bus.sync_read("Present_Position", normalize=False))
    finally:
        bus.disconnect()


if __name__ == "__main__":
    main()
