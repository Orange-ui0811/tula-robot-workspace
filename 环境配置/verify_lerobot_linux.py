"""Offline installation checks. No robot connections or Hub uploads."""
from importlib.metadata import version
from pathlib import Path
import json
import os
import subprocess
import traceback

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
workspace = Path.home() / 'lerobot_workspace'
output = workspace / 'validation'
output.mkdir(exist_ok=True)
report = {'checks': {}}

def check(name, function):
    try:
        report['checks'][name] = {'passed': True, 'details': function()}
    except Exception:
        report['checks'][name] = {'passed': False, 'error': traceback.format_exc()}
    print(name, report['checks'][name]['passed'], flush=True)

def gpu_and_act():
    import torch
    import torchvision
    from lerobot.configs.types import FeatureType, PolicyFeature
    from lerobot.policies.act.configuration_act import ACTConfig
    from lerobot.policies.act.modeling_act import ACTPolicy
    assert torch.cuda.is_available(), 'CUDA is not available'
    config = ACTConfig(
        device='cuda', chunk_size=4, n_action_steps=4,
        dim_model=64, n_heads=4, dim_feedforward=128,
        n_encoder_layers=1, n_decoder_layers=1, use_vae=False,
        pretrained_backbone_weights=None,
        input_features={
            'observation.state': PolicyFeature(FeatureType.STATE, (2,)),
            'observation.environment_state': PolicyFeature(FeatureType.ENV, (4,)),
        },
        output_features={'action': PolicyFeature(FeatureType.ACTION, (2,))},
    )
    policy = ACTPolicy(config).cuda()
    observations = {
        'observation.state': torch.rand(2, 2, device='cuda'),
        'observation.environment_state': torch.rand(2, 4, device='cuda'),
    }
    batch = {**observations, 'action': torch.rand(2, 4, 2, device='cuda'),
             'action_is_pad': torch.zeros(2, 4, device='cuda', dtype=torch.bool)}
    policy.train()
    optimizer = torch.optim.AdamW(policy.parameters(), lr=1e-4)
    loss, _ = policy(batch)
    assert torch.isfinite(loss)
    loss.backward()
    optimizer.step()
    policy.eval()
    policy.reset()
    with torch.no_grad():
        action = policy.select_action(observations)
    torch.cuda.synchronize()
    assert tuple(action.shape) == (2, 2)
    assert torch.isfinite(action).all()
    return {'torch': torch.__version__, 'torchvision': torchvision.__version__,
            'cuda_runtime': torch.version.cuda, 'gpu': torch.cuda.get_device_name(0),
            'gpu_architectures': torch.cuda.get_arch_list(),
            'act_training_loss': float(loss.detach()), 'action_shape': list(action.shape),
            'note': 'Tiny randomly initialized ACT; installation check, not a trained policy.'}

def video():
    from torchcodec.decoders import VideoDecoder
    video_path = output / 'video-check.mp4'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                    '-f', 'lavfi', '-i', 'testsrc=size=64x64:rate=5', '-t', '1',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(video_path)],
                   check=True, timeout=30)
    decoder = VideoDecoder(str(video_path), device='cpu')
    frames = decoder.get_frames_at(indices=[0, 1]).data
    assert tuple(frames.shape) == (2, 3, 64, 64)
    return {'torchcodec': version('torchcodec'), 'decoded_shape': list(frames.shape)}

def dataset():
    import numpy as np
    from tempfile import TemporaryDirectory
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    with TemporaryDirectory(prefix='lerobot-install-check-') as tmp:
        root = Path(tmp) / 'dataset'
        features = {name: {'dtype': 'float32', 'shape': (2,), 'names': ['joint_1', 'joint_2']}
                    for name in ('observation.state', 'action')}
        data = LeRobotDataset.create('local/installation-check', fps=5, features=features,
                                     root=root, robot_type='installation_mock', use_videos=False)
        for i in range(5):
            data.add_frame({'observation.state': np.array([i, i + 1], dtype=np.float32),
                            'action': np.array([i + 1, i + 2], dtype=np.float32),
                            'task': 'offline installation check'})
        data.save_episode()
        data.finalize()
        loaded = LeRobotDataset('local/installation-check', root=root)
        assert len(loaded) == 5
        assert list(loaded[0]['action'].shape) == [2]
        return {'frames': len(loaded), 'action_shape': list(loaded[0]['action'].shape),
                'hub_upload': False}

def simulation():
    import gymnasium as gym
    import gym_pusht
    from PIL import Image
    env = gym.make('gym_pusht/PushT-v0', render_mode='rgb_array')
    try:
        obs, _ = env.reset(seed=42)
        env.step(env.action_space.sample())
        image = env.render()
        assert image.ndim == 3
        Image.fromarray(image).save(output / 'pusht-check.png')
        return {'environment': 'gym_pusht/PushT-v0', 'image_shape': list(image.shape)}
    finally:
        env.close()

def commands():
    result = {}
    for command in ('lerobot-info', 'lerobot-train', 'lerobot-record', 'lerobot-eval'):
        args = [command] if command == 'lerobot-info' else [command, '--help']
        p = subprocess.run(args, capture_output=True, text=True, timeout=90)
        (output / f'{command}.log').write_text(p.stdout + p.stderr)
        result[command] = p.returncode
        assert p.returncode == 0, f'{command}: {p.stderr[-3000:]}'
    return result

report['lerobot_version'] = version('lerobot')
check('gpu_act_training_and_inference', gpu_and_act)
check('ffmpeg_torchcodec', video)
check('local_dataset_roundtrip', dataset)
check('pusht_simulation', simulation)
check('cli_entry_points', commands)
report['passed'] = all(c['passed'] for c in report['checks'].values())
(output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
print(json.dumps(report, indent=2, ensure_ascii=False))
raise SystemExit(0 if report['passed'] else 1)
