import time
import numpy as np
from tula_robot import TulaRobot

def run_stress_test(port="COM5", target_hz=50, test_duration=10):
    """
    高频通信压力测试
    :param target_hz: 目标频率 (默认 50Hz，即每 20ms 一次读写)
    :param test_duration: 测试持续时间 (秒)
    """
    print("="*50)
    print(f"  TulaRobot 高频并发压测 (目标: {target_hz}Hz, 时长: {test_duration}s)")
    print("="*50)

    # 1. 初始化机器人
    robot = TulaRobot(port=port, active_axes=[1, 2])
    
    # 临时禁用回零，防止压测前耗时过长（假设你已经手动对好位置）
    robot.skip_home = False  # 如果你的机器人默认会回零，可以设置为 False 来跳过回零步骤，直接进入读写循环 
    
    try:
        robot.connect()
        
        # 2. 获取初始安全位置
        print("\n[压测准备] 正在读取当前绝对位置作为安全锚点...")
        initial_obs = robot.read()
        safe_action = initial_obs["observation.state"].copy()
        print(f"[压测准备] 锚点位置: {safe_action}°。压测期间将循环下发此位置。")
        
        # 3. 压测参数初始化
        loop_interval = 1.0 / target_hz  # 理想单次循环时间 (50Hz = 0.02s)
        total_loops = target_hz * test_duration
        
        latencies = []
        missed_deadlines = 0
        
        print(f"\n🚀 开始高频压测 (预计执行 {total_loops} 次读写循环)...\n")
        
        start_time = time.time()
        
        # 4. 核心高频主循环
        for i in range(total_loops):
            loop_start = time.perf_counter() # 使用高精度计时器
            
            # --- [核心通信负载] ---
            try:
                _ = robot.read()          # 测压：高频读
                robot.write(safe_action)  # 测压：高频写
            except IOError as e:
                # 底层 C 驱动抛出的超时/通信异常，记录掉帧并继续
                missed_deadlines += 1
                time.sleep(0.005)  # 主动让渡 5ms 总线控制权，冲刷脏数据
                continue
            # ----------------------
            
            loop_end = time.perf_counter()
            latency = loop_end - loop_start
            latencies.append(latency)
            
            # 计算需要休眠补偿的时间，以维持目标 Hz
            sleep_time = loop_interval - latency
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                missed_deadlines += 1  # 如果单次读写耗时超过了 20ms，记为一次掉帧
                
            # 每 100 次打印一次存活心跳，证明程序没卡死
            if (i + 1) % 100 == 0:
                print(f"   -> 已完成 {i + 1}/{total_loops} 次循环，当前最新延迟: {latency*1000:.2f} ms")

        # 5. 统计分析
        actual_duration = time.time() - start_time
        avg_latency = np.mean(latencies) * 1000
        max_latency = np.max(latencies) * 1000
        min_latency = np.min(latencies) * 1000
        
        print("\n" + "="*50)
        print("  📊 压测报告 (Stress Test Report)")
        print("="*50)
        print(f"预期频率: {target_hz} Hz")
        print(f"实际平均频率: {total_loops / actual_duration:.2f} Hz")
        print(f"单次读写延迟 (Latency): 平均 {avg_latency:.2f} ms | 最大 {max_latency:.2f} ms | 最小 {min_latency:.2f} ms")
        print(f"掉帧次数 (超过 {loop_interval*1000:.1f}ms): {missed_deadlines} 次")
        
        if missed_deadlines == 0 and max_latency < (loop_interval * 1000):
            print("\n✅ 结论: 完美！你的底层 C 驱动与串口通讯拥有极高的实时性，完全胜任具身智能算法的高频控制需求！")
        else:
            print("\n⚠️ 结论: 存在掉帧或延迟尖峰。可能由于串口波特率瓶颈、C语言内部 Timeout 设置过长，或 Windows/OS 线程调度导致。")
            
    except IOError as e:
            missed_deadlines += 1
            # 删掉 time.sleep(0.005) 和 continue！
            # 什么都不用做，让它自然走到下面的帧率控制代码
            pass
    finally:
        robot.disconnect()

if __name__ == "__main__":
    # 你可以在这里修改 COM5 和轴号
    run_stress_test(port="COM5", target_hz=50, test_duration=10)

