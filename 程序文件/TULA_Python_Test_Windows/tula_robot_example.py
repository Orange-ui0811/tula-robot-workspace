from __future__ import annotations

import argparse
import json

from tula_robot import TULARobot, TULARobotConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="TULA LeRobot-shaped robot example")
    parser.add_argument("--port", default="COM4", help="Serial port, for example COM4 or COM5")
    parser.add_argument("--move", action="store_true", help="Send one robot action in degrees")
    parser.add_argument("--joint-1-deg", type=float, default=2.5, help="Target for joint_1.pos in degrees")
    parser.add_argument("--joint-2-deg", type=float, default=4.0, help="Target for joint_2.pos in degrees")
    parser.add_argument(
        "--action-json",
        default=None,
        help='Optional JSON action dict, for example: \'{"joint_1.pos": 2.5, "joint_2.pos": 4.0}\'',
    )
    parser.add_argument("--return-zero", action="store_true", help="Return both joints to 0 degrees after --move")
    parser.add_argument(
        "--max-relative-target",
        type=float,
        default=None,
        help="Optional LeRobot-style safety clip in degrees",
    )
    args = parser.parse_args()

    robot = TULARobot(
        TULARobotConfig(
            port=args.port,
            max_relative_target=args.max_relative_target,
        )
    )

    try:
        robot.connect(calibrate=True)
        print("Observation features:", robot.observation_features)
        print("Action features:", robot.action_features)
        print("Observation:", robot.get_observation())

        if args.move or args.action_json:
            if args.action_json:
                action = {key: float(value) for key, value in json.loads(args.action_json).items()}
            else:
                action = {
                    "joint_1.pos": args.joint_1_deg,
                    "joint_2.pos": args.joint_2_deg,
                }
            sent = robot.send_action(action)
            print("Action sent:", sent)
            print("Observation after action:", robot.get_observation())

            if args.return_zero:
                sent = robot.send_action({"joint_1.pos": 0.0, "joint_2.pos": 0.0})
                print("Return action sent:", sent)
                print("Observation after return:", robot.get_observation())
    finally:
        robot.disconnect()


if __name__ == "__main__":
    main()
