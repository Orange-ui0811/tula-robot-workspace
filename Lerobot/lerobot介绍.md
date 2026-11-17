# lerobot介绍

任务ID: 136
标签: 资料
负责人: George
状态: 待办
所属项目: Brazo (https://app.notion.com/p/Brazo-2e04cc1989208083a692ee57482d90be?pvs=21)
网址: https://deepwiki.com/huggingface/lerobot

# **1. 引言**

作为Hugging Face贡献的开源机器人学习框架，LeRobot凭借其PyTorch内核、对模仿学习（IL）和强化学习（RL）的专注，以及与现实世界机器人应用的紧密联系，正迅速成为机器人学界和产业界关注的焦点。本文旨在全面、深入地剖析LeRobot框架的设计理念、核心架构、关键组件、工作流程及其应用实践。从**环境安装、系统概览，到四大核心子系统（策略、数据集、环境、控制）的细致解读**，再到训练与评估流程的实战演练，本文将逐步揭开LeRobot的强大功能与灵活扩展性。

## **1.1 LeRobot框架简介**

LeRobot 专注于提供最先进的模仿学习 (Imitation Learning, IL) 和强化学习 (Reinforcement Learning, RL) 算法实现，这些算法经过精心设计，旨在能够高效地从演示数据中学习，并将学得的策略直接迁移和部署到真实的物理机器人上。LeRobot 的设计哲学强调易用性、模块化和可扩展性，致力于降低机器人学习的门槛，加速从研究到应用的转化过程。

该框架不仅仅是一个算法库，更是一个集成了数据集管理、策略训练、仿真环境交互、以及物理机器人控制等多个关键模块的综合性平台。通过提供预训练模型、标准化的数据集接口和多样化的仿真环境支持，LeRobot 极大地简化了机器人学习项目的启动和开发流程。

![9b78a118d20b490c8eb2fc4f76b039f3.png](https://oss.guyuehome.com/upload/2025/06/262145023835/9b78a118d20b490c8eb2fc4f76b039f3.png)

## **1.2 核心特性与优势**

LeRobot 之所以能在众多框架中脱颖而出，得益于其一系列精心设计的核心特性：

![e5afac93c9ba45c7a58a3b9d481532a3.png](https://oss.guyuehome.com/upload/2025/06/262145187497/e5afac93c9ba45c7a58a3b9d481532a3.png)

- **端到端的机器人学习支持**：从数据收集、处理、模型训练、仿真评估到真实机器人部署，LeRobot 提供了全链路的支持。
- **先进的模仿与强化学习算法**：内置多种SOTA（State-of-the-Art）策略，如ACT (Action Chunking Transformer), Diffusion Policy, TDMPC等，并提供统一的调用接口。
- **与Hugging Face生态系统的深度集成**：可以方便地从Hugging Face Hub加载预训练模型和标准数据集，加速研究进程。
- **强大的数据集管理系统**：`LeRobotDataset` 类支持复杂的多模态数据（如视频、图像、状态、动作序列），并提供高效的数据加载和预处理机制。
- **灵活的环境接口**：基于 Gymnasium API，支持多种流行的机器人仿真环境（如Aloha, PushT, XArm），并易于扩展到新的环境。
- **直接的机器人控制能力**：通过 `control_robot.py` 脚本和可扩展的硬件接口，支持对真实机器人进行遥操作、数据录制和策略部署。
- **模块化与可扩展设计**：遵循良好的软件设计原则，各组件低耦合，方便用户进行定制化开发和功能扩展。
- **完善的文档与社区支持**：提供详细的文档和教程，并依托Hugging Face社区，为用户提供交流和支持的平台。

## **1.3 适用场景**

LeRobot框架的强大功能使其适用于广泛的机器人学习研究与应用场景：

- **机器人技能学习**：训练机器人执行复杂的操作任务，如物体抓取、放置、工具使用、双臂协作等。
- **视觉运动控制**：开发基于视觉输入的端到端控制策略。
- **从演示中学习（LfD）**：利用人类演示数据快速教会机器人新技能。
- **策略迁移与泛化**：研究如何将仿真环境中训练的策略有效迁移到真实机器人，并提升策略对不同任务和环境的泛化能力。
- **多模态机器人学习**：融合视觉、力觉、本体感觉等多模态信息进行机器人决策。
- **教育与研究平台**：作为机器人学习领域的教学工具和算法验证平台。

# **2. LeRobot安装与环境配置**

![7c9e41399e2e43a49de9e21646f5847a.png](https://oss.guyuehome.com/upload/2025/06/262145286833/7c9e41399e2e43a49de9e21646f5847a.png)

## **2.1 系统需求**

在开始安装之前，请确保您的系统满足以下基本要求：

- **Python**: 版本需为 3.10 或更高。LeRobot 主要在 Python 3.10 版本下进行测试和开发。
- **CUDA**: 对于希望利用GPU进行加速训练和推理的用户，需要安装NVIDIA CUDA Toolkit。虽然CUDA是可选的，但对于处理复杂的模型和大规模数据集，强烈建议配置GPU环境。
- **ffmpeg**: 这是处理视频数据和数据集管理的关键依赖。LeRobot 需要 ffmpeg 支持 `libsvtav1` 编码器。可以通过 `ffmpeg -encoders | grep svtav1` 命令检查。
- **操作系统**:
    - **Linux**: 推荐的操作系统，具有最佳的兼容性和性能。
    - **macOS**: 支持。
    - **Windows**: 支持，但部分功能可能受限或需要额外配置。

## **2.2 标准安装步骤**

标准的安装流程包括克隆代码库、创建虚拟环境、安装核心依赖以及LeRobot包本身。

### **2.2.1 克隆代码库**

首先，从GitHub克隆LeRobot的官方代码库：

```bash
git clone https://github.com/huggingface/lerobot.git
cd lerobot
```

### **2.2.2 创建Python虚拟环境**

为了避免与其他Python项目的依赖冲突，强烈建议为LeRobot创建一个独立的虚拟环境。这里以conda为例：

```bash
conda create -n lerobot_env python=3.10
conda activate lerobot_env
```

如果您使用venv，可以执行：

```bash
python3 -m venv lerobot_env
source lerobot_env/bin/activate # Linux/macOS
# lerobot_env\Scripts\activate # Windows
```

### **2.2.3 安装ffmpeg**

ffmpeg对于LeRobot的数据集视频处理功能至关重要。

- **Ubuntu/Debian**:
    
    ```bash
    sudo apt update && sudo apt install ffmpeg
    ```
    
- **macOS (使用Homebrew)**:
    
    ```bash
    brew install ffmpeg
    ```
    
- **Windows**: 可以从ffmpeg官网下载预编译版本，并将其可执行文件路径添加到系统环境变量PATH中。

**注意**：如前所述，请确保您的ffmpeg版本支持 `libsvtav1`。如果默认安装不支持，您可能需要从源码编译或查找包含此支持的特定版本。例如，某些平台可以通过 `conda install -c conda-forge ffmpeg` 安装到支持的版本。

### **2.2.4 安装LeRobot核心库**

在激活虚拟环境并进入LeRobot代码库根目录后，使用pip进行安装。推荐使用可编辑模式（`-e .`）安装，这样对源码的修改可以立即生效，无需重新安装：

```bash
pip install -e .
```

此命令会安装LeRobot的核心组件。

## **2.3 安装可选组件**

LeRobot采用模块化设计，许多特定功能（如对特定仿真环境或硬件的支持）的依赖是可选的，可以根据需要安装。这有助于保持核心库的轻量化。

### **2.3.1 模拟环境依赖**

LeRobot支持多种仿真环境。您可以根据需要安装相应的依赖包：

- **Aloha Simulation**:
    
    ```bash
    pip install -e ".[aloha]"
    ```
    
- **PushT Simulation**:
    
    ```bash
    pip install -e ".[pusht]"
    ```
    
- **XArm Simulation**:
    
    ```bash
    pip install -e ".[xarm]"
    ```
    
    也可以一次性安装所有支持的模拟环境：
    

```bash
pip install -e ".[envs]"
# 或者分别安装
# pip install -e ".[aloha,pusht,xarm]"
```

### **2.3.2 机器人硬件支持依赖**

如果计划将LeRobot用于控制物理机器人，可能需要安装特定硬件的SDK：

- **Dynamixel Servos**:
    
    ```bash
    pip install -e ".[dynamixel]"
    ```
    
- **FeeTech Servos**:
    
    ```bash
    pip install -e ".[feetech]"
    ```
    
- **RealSense Cameras**:
    
    ```bash
    pip install -e ".[realsense]"
    ```
    

### **2.3.3 开发工具依赖**

对于希望参与LeRobot框架开发或进行更深度定制的开发者，可以安装开发工具相关的依赖(Development Tool Dependencies)：

```bash
pip install -e ".[dev]"
```

这通常包括代码格式化工具（如black, isort）、静态检查工具（如flake8, mypy）和测试框架（如pytest）。

## **2.4 Docker安装**

为了提供一个隔离且可复现的运行环境，LeRobot官方提供了Docker支持。这对于确保环境一致性、简化部署流程尤其有用。主要有三种Docker镜像配置：

1. **CPU容器 (`lerobot-cpu`)**: 仅包含CPU支持，适用于不需要GPU加速的通用场景或开发调试。
2. **GPU容器 (`lerobot-gpu`)**: 包含NVIDIA GPU支持，适用于模型训练和需要GPU加速的推理任务。
3. **开发容器 (`lerobot-gpu-dev`)**: 在GPU容器的基础上，额外包含了开发工具，方便进行代码开发和调试。

### **2.4.1 Docker镜像类型**

- `docker/lerobot-cpu/Dockerfile`: CPU版本镜像的定义文件。
- `docker/lerobot-gpu/Dockerfile`: GPU版本镜像的定义文件，依赖NVIDIA Container Toolkit。
- `docker/lerobot-gpu-dev/Dockerfile`: GPU开发版镜像的定义文件。

### **2.4.2 构建Docker镜像**

您可以从代码库中的Dockerfile本地构建镜像。例如，构建GPU开发版镜像：

```bash
# 进入LeRobot代码库根目录
# 假设要构建GPU开发版镜像
docker build -t lerobot-gpu-dev -f docker/lerobot-gpu-dev/Dockerfile .
```

类似地，可以构建 `lerobot-cpu` 和 `lerobot-gpu` 镜像。

### **2.4.3 运行Docker容器**

运行容器时 **(Running Docker Containers)**，需要根据镜像类型进行相应配置。

- **运行CPU容器**:
    
    ```bash
    docker run -it --rm \
      -v $(pwd):/workspace \
      -w /workspace \
      lerobot-cpu \
      bash
    ```
    
- **运行GPU容器** (需要安装NVIDIA Container Toolkit):
    
    ```bash
    docker run -it --rm --gpus all \
      -v $(pwd):/workspace \
      -w /workspace \
      lerobot-gpu \
      bash
    ```
    

对于 `lerobot-gpu-dev` 容器，运行命令类似。`-v $(pwd):/workspace` 将当前LeRobot代码库目录挂载到容器的 `/workspace` 路径，方便在容器内访问和修改代码。

![57d3096a82f04e118e53dee64de1f1c2.png](https://oss.guyuehome.com/upload/2025/06/262145457384/57d3096a82f04e118e53dee64de1f1c2.png)

## **2.5 安装验证**

安装完成后，可以通过几种方式验证LeRobot是否正确安装并可以运行：

### **2.5.1. 简单的Python脚本测试**

在Python解释器中尝试导入LeRobot并执行一些基本操作，例如加载一个小型数据集或创建一个策略实例。

```python
import torch
from lerobot.common.datasets import make_dataset
from lerobot.common.policies import make_policy

try:
    # 尝试加载一个示例数据集 (如果网络和Hugging Face Hub配置正常)
    # dataset = make_dataset("lerobot/pusht", split="train[:1%]") # 加载一小部分数据
    # print(f"Successfully loaded dataset with {len(dataset)} samples.")

    # 尝试创建一个策略实例
    policy = make_policy("diffusion", policy_kwargs={"obs_dim": 10, "action_dim": 2}, device="cpu")
    print("Successfully created a policy instance.")
    print("LeRobot installation appears to be working!")
except Exception as e:
    print(f"An error occurred during verification: {e}")
```

### **2.5.2. 运行测试套件**

LeRobot包含一套单元测试和集成测试，用于验证框架各个组件的功能（如果安装了 `[dev]` 或 `[test]` 依赖）。

```bash
pytest tests/
```

所有测试通过则表明安装基本成功。

## **2.6 主要依赖库概览**

LeRobot构建在一系列强大的开源库之上，理解这些核心依赖有助于更好地使用和扩展框架：

| **类别** | **主要依赖库** | **用途** |
| --- | --- | --- |
| **核心深度学习** | `torch`, `torchvision` | 深度学习计算、模型构建、GPU加速 |
| **数据处理与加载** | `datasets` (Hugging Face),  `einops`,  `opencv-python-headless` | 数据集管理、张量操作、图像处理 |
| **视频处理** | `av`,  `imageio[ffmpeg]`,  `torchcodec` | 视频数据的编码、解码、读取和写入 |
| **可视化与实验跟踪** | `rerun-sdk`,  `matplotlib`,  `tensorboard`,   `wandb`  (optional) | 数据可视化、训练过程监控、实验结果记录 |
| **仿真环境** | `gymnasium`,  `gym-aloha`,  `gym-pusht`,  `gym-xarm` | 机器人仿真环境接口和具体环境实现 |
| **机器人硬件接口** | `dynamixel-sdk`, `feetech-servo-sdk`, `pyrealsense2` | 与物理机器人电机、相机等硬件通信的SDK |
| **配置与命令行** | `hydra-core`,  `omegaconf`,  `typer` | 配置文件管理、命令行参数解析 |
| **构建与打包** | `poetry` | 项目依赖管理和打包工具 |

![04a730963dad4892902568b04baf2cbe.png](https://oss.guyuehome.com/upload/2025/06/262146402623/04a730963dad4892902568b04baf2cbe.png)

## **2.7 常见安装问题与排查**

# **3. LeRobot系统架构深度解析**

LeRobot 作为一个综合性的机器人学习框架，其强大的功能背后是一套精心设计的系统架构（ System Architecture）。理解其架构有助于开发者更高效地使用框架、进行二次开发和解决遇到的问题，本章节将深入剖析LeRobot的整体架构及其四大核心子系统。

## **3.1 整体架构概览**

LeRobot 的系统架构围绕着**策略 (Policy)**、**数据集 (Dataset)**、**环境 (Environment)** 和 **机器人控制 (Robot Control)** 四大核心支柱构建。这些子系统通过清晰定义的接口进行交互，共同支撑起从数据处理、模型训练、仿真评估到真实机器人部署的完整工作流程。

![6c3337fea3914b599312eb0b8744fc1e.png](https://oss.guyuehome.com/upload/2025/06/262146513478/6c3337fea3914b599312eb0b8744fc1e.png)

该架构遵循模块化和分层设计原则：

- **底层硬件与仿真接口**：提供与物理机器人硬件（电机、相机等）和多种仿真环境（Gymnasium API兼容）的连接。
- **中层核心组件**：包括数据集管理模块 (`LeRobotDataset`)，负责数据的加载、预处理和增强；策略模块 (`PreTrainedPolicy` 及其实现)，封装了各种机器人学习算法；环境封装模块，统一了不同仿真环境的交互方式。
- **上层应用与脚本**：提供可执行脚本（如 `train.py`, `eval.py`, `control_robot.py`），编排和驱动整个学习与控制流程。用户也可以基于这些核心组件开发自定义应用。
- **工具与配置**：包括配置文件管理（Hydra）、可视化工具（Rerun, Tensorboard）、以及Hugging Face Hub的集成，为开发和实验提供便利。

## **3.2 四大核心子系统**

接下来，我们将详细探讨每个核心子系统(Core Subsystems)的设计与功能。

### **3.2.1 策略系统**

策略系统(Policy System)是LeRobot的"大脑"，负责根据观察到的状态（如图像、机器人关节角度）生成动作，以完成特定任务。LeRobot致力于提供一系列先进的、可以直接应用于机器人控制的策略模型。

![d460577201744bdb9ddc61ed35e3ebf9.png](https://oss.guyuehome.com/upload/2025/06/262147121054/d460577201744bdb9ddc61ed35e3ebf9.png)

#### **3.2.1.1 `make_policy()`工厂函数**

为了方便用户创建和切换不同的策略模型，LeRobot提供了一个统一的工厂函数（Factory Function） `make_policy()`。该函数根据指定的策略类型（如 "diffusion", "act", "tdmpc"）和相关配置参数，实例化并返回相应的策略对象。

```python
from lerobot.common.policies import make_policy

# 示例：创建一个Diffusion Policy实例
diffusion_policy_config = {
    "policy_type": "diffusion",
    # 特定于Diffusion Policy的参数
    "obs_dim": 256, # 假设观察特征维度
    "action_dim": 7, # 动作维度
    "pred_horizon": 16, # 预测视野
    "obs_horizon": 2,   # 观察视野
    "action_horizon": 8, # 动作视野
    # ... 其他Diffusion Policy参数
}
policy_instance = make_policy(
    policy_name_or_path=diffusion_policy_config["policy_type"], # 可以是类型名或HF Hub路径
    # checkpoint_path=None, # 可选，加载预训练权重的路径
    # device="cuda" if torch.cuda.is_available() else "cpu",
    **diffusion_policy_config # 将配置字典解包作为参数
)

print(f"成功创建策略: {type(policy_instance)}")
```

这种工厂模式的设计遵循了**开闭原则**（Open/Closed Principle），即对扩展开放（可以方便地添加新的策略类型），对修改关闭（现有代码不需要因为新增策略而大规模改动）。训练脚本 (`train.py`) 和评估脚本 (`eval.py`) 都通过这个工厂函数与具体的策略实现解耦。

#### **3.2.1.2 `PreTrainedPolicy`接口**

所有由 `make_policy()` 创建的策略都继承自一个共同的基类（或实现一个共同的接口，通常命名为 `PreTrainedPolicy` 或类似的名称）。这个接口定义了策略对象必须具备的核心方法，确保了不同策略在上层应用中的一致性。

关键接口方法通常包括：

- `predict(observation, ...)` 或 `select_action(observation, ...)`: 根据当前观察（可能还包括历史信息、任务目标等）输出动作。这是策略在执行阶段的核心。
- `compute_loss(batch, ...)`: 根据一批训练数据计算损失函数值。这是策略在训练阶段的核心。
- `train_step(batch, optimizer, ...)`: 执行一个完整的训练步骤，包括前向传播、损失计算、反向传播和参数更新。
- `save_pretrained(save_directory, ...)`: 将训练好的策略模型（包括网络权重和配置）保存到指定目录，或上传到Hugging Face Hub。
- `from_pretrained(model_name_or_path, ...)`: 从本地目录或Hugging Face Hub加载预训练的策略模型。

这个统一接口的设计体现了**接口隔离原则**（Interface Segregation Principle）和**依赖倒置原则**（Dependency Inversion Principle），使得上层模块（如训练器、评估器）依赖于抽象接口而非具体实现。

#### **3.2.1.3 支持的策略架构**

LeRobot 实现并支持多种当前主流的机器人学习策略架构(Policy Architectures)，每种架构针对不同的任务特性和数据模态有所侧重：

- **ACT (Action Chunking Transformer 模型动作切分策略)**:
    - **描述**: 一种基于Transformer的策略，特别适用于需要长时序理解和精确动作协调的双臂操作任务。它通过将动作序列分块（chunking）处理，能够有效地学习复杂的操作技能。
    - **核心思想**: 利用Transformer的自注意力机制捕捉状态和动作序列中的时序依赖关系。
    - **适用场景**: 双臂协同装配、物体整理、复杂轨迹跟踪等。
    - `[图：ACT策略架构图，突出Transformer编码器、动作分块和解码器部分]`
- **Diffusion Policy (去噪扩散策略)**:
    - **描述**: 一种基于去噪扩散概率模型的策略，近年来在视觉运动控制领域取得了显著成功。它将动作生成过程建模为一个从噪声逐步去噪到目标动作的迭代过程。
    - **核心思想**: 通过学习反向扩散过程（去噪网络，通常是U-Net结构）来生成高质量、多样性的动作序列。
    - **适用场景**: 基于高维视觉输入的端到端控制，如物体推动、抓取、轨迹模仿等。
    - `[图：Diffusion Policy工作原理图，展示前向加噪过程和反向去噪（生成）过程，以及U-Net网络结构]`
- **TDMPC (Temporal Difference Model Predictive Control)**:
    - **描述**: 一种结合了模型学习和模型预测控制（MPC）思想的策略。它学习一个世界模型来预测环境动态，并基于该模型进行在线规划以选择最优动作。
    - **核心思想**: 通过时间差分学习（TD-learning）训练潜在空间中的动态模型，并利用此模型进行短期规划。
    - **适用场景**: 需要在线适应和规划的任务，对环境动态变化有一定鲁棒性。
    - `[图：TDMPC架构图，展示世界模型、任务行为学习和MPC规划器的交互]`
- **VQBeT (Vector Quantized Behavior Transformer)**:
    - **描述**: 行为Transformer与矢量量化（VQ）相结合的策略。它首先将连续的行为（如动作序列）通过VQ-VAE等技术量化为离散的token，然后使用Transformer学习这些行为token序列的模式。
    - **核心思想**: 将复杂的连续行为空间离散化，简化学习难度，并利用Transformer强大的序列建模能力。
    - **适用场景**: 学习多模态行为、长时序任务、模仿复杂的人类演示。
- **PI0 (Vision-Language-Action Policy)**:
    - **描述**: 类似RT-1, RT-2, Gato, PaLM-E等大规模预训练的视觉-语言-动作模型这类策略通常基于大型Transformer架构，能够理解自然语言指令，并结合视觉输入生成相应的机器人动作。它们展现了强大的泛化能力和零样本/少样本学习潜力。
    - **核心思想**: 利用大规模多模态数据进行预训练，学习通用的世界知识和任务执行能力。
    - **适用场景**: 自然语言指令下的机器人操作、开放域任务执行、零样本泛化。
    - `[图：PI0这类VLA模型的概念架构图，展示图像、文本输入如何被统一编码并生成动作输出]`
- **PI0FAST (Fast Action Tokenization Policy)**:
    - **描述**: PI0策略的一种变体，专注于提升动作token化的效率或动作生成的实时性。具体实现细节需参考其源码或相关论文。
    - **核心思想**: 优化动作表示或生成过程，以满足机器人控制的实时性要求。

![7bb2e06bf4664fd5911a107a2bd1f5aa.png](https://oss.guyuehome.com/upload/2025/06/262147240323/7bb2e06bf4664fd5911a107a2bd1f5aa.png)

#### **3.2.1.4 策略创建与使用示例**

之前的博客中已有一个策略创建的示例，这里我们进一步展示如何加载预训练模型和进行一次简单的预测：

```python
import torch
from lerobot.common.policies import make_policy
from lerobot.common.datasets.utils import PADDING_MASKS # 用于处理变长序列

# 假设我们有一个预训练的Diffusion Policy模型在Hugging Face Hub上
# (例如 "lerobot/diffusion_pusht_image_g8acc")
# 或者本地路径 "outputs/train/diffusion_pusht_image_g8acc/checkpoints/epoch_XXX"
# model_identifier = "lerobot/diffusion_pusht_image_g8acc"
# 为简单起见，我们先创建一个全新的策略
policy = make_policy(
    "diffusion", # 策略类型
    # 提供必要的配置参数，这些参数通常在训练时定义，加载预训练模型时会自动获取
    # 如果是创建新策略用于训练，则必须提供
    policy_config={ # 假设使用 policy_config 传递
        "obs_dim": 256,  # 示例观察维度 (例如 ResNet18 输出 + 机器人状态)
        "action_dim": 2, # 示例动作维度 (例如 x, y delta)
        "pred_horizon": 16,
        "obs_horizon": 2,
        "action_horizon": 8,
        "num_diffusion_iters": 100, # 扩散步数
        # ... 其他特定于Diffusion Policy的参数
    },
    device="cuda" if torch.cuda.is_available() else "cpu"
)
print(f"策略已创建: {policy}")

# 假设我们有一些观察数据
# 对于Diffusion Policy，通常需要一个观察字典，包含图像和机器人状态
# 形状: (batch_size, obs_horizon, *feature_dims)
# 这里用随机数据模拟
batch_size = 1
obs_horizon = policy.obs_horizon # 从策略配置中获取
# 示例图像特征 (例如经过CNN编码的特征)
image_features = torch.randn(batch_size, obs_horizon, 256-2).to(policy.device) # 假设状态维度为2
# 示例机器人状态 (例如末端执行器位置)
robot_state = torch.randn(batch_size, obs_horizon, 2).to(policy.device)

observation_dict = {
    "observation.image_features": image_features,
    "observation.state": robot_state,
    # 根据策略的具体需求，可能还需要其他键，如 "observation.mask"
    PADDING_MASKS.OBSERVATION: torch.ones(batch_size, obs_horizon, dtype=torch.bool).to(policy.device)
}

# 将策略设置为评估模式
policy.eval()

# 进行动作预测
with torch.no_grad():
    # 不同的策略 `predict` 方法签名可能不同，需查阅具体策略文档
    # Diffusion Policy 通常需要 `num_inference_steps`
    # 返回的action_dict通常包含 "action" 键，形状 (batch_size, pred_horizon, action_dim)
    predicted_action_dict = policy.predict(observation_dict, num_inference_steps=10)
    predicted_actions = predicted_action_dict["action"]

print(f"预测动作形状: {predicted_actions.shape}") # 应为 (1, pred_horizon, action_dim)

# 如果要加载预训练权重：
# policy_hf_path = "lerobot/diffusion_pusht_image_g8acc"
# loaded_policy = make_policy(policy_hf_path, device=policy.device)
# print(f"从Hub加载的策略: {loaded_policy}")
# obs_spec = loaded_policy.obs_spec # 预训练模型通常带有观察和动作空间规范
```

这个例子展示了策略生命周期的基本环节：创建（或加载）、准备输入数据、执行预测。在实际应用中，观察数据会来自仿真环境或真实机器人。

### **3.2.2 数据集管理**

高质量的数据是训练高性能机器人策略的基石。LeRobot的数据集管理系统(Dataset Management)高效地处理机器人学习中常见的复杂、多模态、时序性数据。

![ff06922f9a734232bc7e1aa0647b1ca4.png](https://oss.guyuehome.com/upload/2025/06/262147356806/ff06922f9a734232bc7e1aa0647b1ca4.png)

### **3.2.2.1 `LeRobotDataset`核心类**

`LeRobotDataset` 是LeRobot数据集处理的核心。它继承自PyTorch的 `torch.utils.data.Dataset` 类，并在此基础上针对机器人学习数据的特性进行了扩展。

主要特性包括：

- **Hugging Face Hub集成**: 可以直接从Hugging Face Hub下载和加载标准化的机器人数据集（如 `lerobot/pusht`, `lerobot/aloha_sim_cube_human` 等）。
- **本地数据集支持**: 也支持加载本地存储的数据集。
- **多模态数据处理**: 能够处理包含图像序列、机器人状态（关节角度、末端执行器姿态）、动作指令、语言指令、奖励信号等多种类型的数据。
- **时序数据支持**: 机器人数据通常是时间序列。`LeRobotDataset` 能够加载和处理固定长度或可变长度的轨迹片段（episodes/chunks）。
- **灵活的数据转换 (Transforms)**: 允许用户定义和应用一系列预处理和增强操作，如图像缩放、裁剪、归一化、颜色抖动等。这些转换可以在加载数据时动态应用。
- **元数据访问**: 提供访问数据集元数据（如观察空间、动作空间、帧率、数据集描述等）的接口。
- **高效的DataLoader**: 可以方便地与PyTorch的 `DataLoader` 结合使用，实现多进程数据加载和批处理。

#### **3.2.2.2 `make_dataset()`工厂函数**

与策略系统类似，数据集管理系统也提供了一个工厂函数 `make_dataset()`，用于根据配置创建 `LeRobotDataset` 实例。

```python
from lerobot.common.datasets import make_dataset
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset # 导入基类
from torchvision import transforms as T # 导入图像变换

# 示例：从Hugging Face Hub加载PushT数据集，并应用图像变换
dataset_name = "lerobot/pusht"
# dataset_name = "lerobot/aloha_sim_cube_human" # 另一个例子
split = "train[:10%]" # 加载训练集的前10%数据进行演示

# 定义图像变换
image_transforms = T.Compose([
    T.Resize((224, 224)), # 调整图像大小
    T.ToTensor(),          # 转换为PyTorch张量 (C, H, W) 并将像素值缩放到[0,1]
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]) # 标准化
])

# 创建数据集实例
# 对于需要特定帧键的数据集，如'camera_front_image', 'camera_wrist_image'
# 变换需要以字典形式提供，键对应数据集中的图像键
# 例如：
# common_transforms = {
#     "observation.camera_top_image": image_transforms,
#     # "observation.another_camera_image": other_transforms, # 如果有多个相机
# }
# 如果策略期望的图像输入键是"image"，而数据集中是 "observation.camera_top_image"
# 可能需要在数据加载后或策略内部进行键名映射
# 或者，如果数据集只有一个主图像流，且其键名与策略期望的不同，
# LeRobotDataset的某些实现或其包装器可能支持自动或配置化的键名映射。
# 查阅具体数据集和策略的文档是关键。

# 假设PushT数据集的主要图像键是 "observation.image" (或框架能自动处理)
# 并且策略期望的是 "image" 键，或者 `make_dataset` 会处理好这个映射
# 或者我们只对"observation.image"应用变换
dataset_transforms = {
    "observation.image": image_transforms, # 假设pusht数据集图像键是这个
    # 如果有其他需要变换的模态，也可以在此处添加
}

try:
    dataset: LeRobotDataset = make_dataset(
        dataset_name_or_path=dataset_name,
        # data_dir=None, # 如果是本地数据集，指定路径
        split=split,
        # episode_transforms=None, # 针对整个episode的变换
        # frame_transforms=dataset_transforms, # 针对每一帧的变换 (更常用)
        # LeRobotDataset 的新版本可能将 transforms 参数统一
        transforms=dataset_transforms, # 假设 transforms 参数接受字典
        # prefetch_S3=False, # 是否从S3预取数据
        # delta_action=True, # 动作是否为差量 (某些数据集的元信息)
        # framestack=1, # 帧堆叠数量
        # target_key_map=None, # 用于重命名字段键
    )
    print(f"成功加载数据集 '{dataset_name}' (split: {split})")
    print(f"数据集大小: {len(dataset)}")

    # 访问第一个样本
    if len(dataset) > 0:
        sample = dataset[0] # 返回一个字典，包含多模态数据
        print("样本键:", sample.keys())
        if "observation.image" in sample: # 注意键名可能带有 "observation." 前缀
             print(f"  图像形状: {sample['observation.image'].shape}") # (T, C, H, W) 或 (C,H,W)取决于配置
        if "action" in sample:
             print(f"  动作形状: {sample['action'].shape}") # (T, action_dim)
        if "episode_index" in sample:
             print(f"  回合索引: {sample['episode_index']}")

except Exception as e:
    print(f"加载数据集时发生错误: {e}")
    print("请检查数据集名称、网络连接、Hugging Face Hub token配置（如果需要）以及依赖项。")
```

此函数封装了数据集查找、下载（如果来自Hub）、实例化和配置的复杂逻辑。

#### **3.2.2.3 数据集来源**

- **Hugging Face Hub**: LeRobot与HF Hub紧密集成，用户可以方便地浏览、发现和使用社区贡献的众多机器人数据集。只需提供数据集的Hub ID（如 `lerobot/pusht`），`make_dataset` 即可自动处理下载和缓存。

![45dde0c9ad0f43ef95ed1a85f04f12cb.png](https://oss.guyuehome.com/upload/2025/06/262147475107/45dde0c9ad0f43ef95ed1a85f04f12cb.png)

- **本地存储**: 如果数据集存储在本地，可以通过向 `make_dataset` 提供数据集根目录的路径来加载。数据集通常需要遵循特定的文件结构和元数据格式（例如，包含 `metadata.json`, `index.hdf5` 或 `.parquet` 文件等，具体取决于数据集类型）。

#### **3.2.2.4 数据集元数据**

每个 `LeRobotDataset` 实例都附带有详细的元数据，描述了数据集的特性。这些元数据对于理解数据内容、配置策略模型和进行数据探索至关重要。

可以通过 `dataset.get_metadata()` 或直接访问 `dataset.metadata` 属性（具体API可能因版本而异）来获取。

元数据通常包含以下信息：

- `name`: 数据集名称。
- `version`: 数据集版本。
- `description`: 数据集内容的简要描述。
- `observation_space`: 观察空间的定义（通常遵循Gymnasium的Space格式），描述了每个观察特征的类型、形状、范围等。例如：
    
    ```json
    "observation_space": {
        "camera_image": {"shape": [3, 224, 224], "dtype": "float32", "low": 0.0, "high": 1.0},
        "robot_joint_positions": {"shape": [7], "dtype": "float32", "low": -3.14, "high": 3.14}
    }
    ```
    
- `action_space`: 动作空间的定义，描述了动作的类型、形状、范围。
- `fps` 或 `frame_rate`: 数据的帧率。
- `num_episodes`: 数据集中的总回合数。
- `total_frames` 或 `total_steps`: 数据集中的总帧数或总步数。
- `extra_info`: 其他特定于数据集的附加信息。

探索元数据的代码示例：

```python
# (需先成功创建dataset实例)
# metadata = dataset.get_metadata() # 假设有此方法
# print(f"数据集名称: {metadata.get('name', 'N/A')}")
# print(f"观察空间: {metadata.get('observation_space', {})}")
# print(f"动作空间: {metadata.get('action_space', {})}")
# print(f"帧率: {metadata.get('fps', 'N/A')}")
# 也可以直接访问 dataset.info (Hugging Face datasets integration) 或 dataset.spec
if hasattr(dataset, 'spec'): # LeRobotDataset 通常有 spec 属性
    print(f"数据集名称: {dataset.spec.name}")
    print(f"观察空间: {dataset.spec.observation_space}")
    print(f"动作空间: {dataset.spec.action_space}")
    print(f"帧率: {dataset.spec.fps}")
```

#### **3.2.2.5 数据集可视化**

理解和检验数据集的质量对于成功的机器人学习至关重要。LeRobot提供了或支持使用多种工具进行数据集可视化：

- **`visualize_dataset.py`脚本**: LeRobot代码库中通常会包含一个名为 `lerobot/scripts/visualize_dataset.py` (或类似名称) 的脚本。该脚本允许用户加载指定的LeRobot数据集，并交互式地查看其中的图像、视频、动作轨迹等信息。
    
    **命令行用法示例**:
    
    ```bash
    python lerobot/scripts/visualize_dataset.py \
      --dataset_name_or_path=lerobot/pusht \
      --split=train \
      --num_episodes_to_show=5 \
      --shuffle # 可选，随机选择回合
    ```
    
- **可视化工具**:
    
    ![854bafcd0d1d4c43a8f172acd59505a2.png](https://oss.guyuehome.com/upload/2025/06/262148184424/854bafcd0d1d4c43a8f172acd59505a2.png)
    
    - **Rerun (rerun.io)**: 一个强大的、开源的可视化工具，专为机器人、计算机视觉和多模态AI数据设计。LeRobot可以集成Rerun SDK，将数据集中的图像序列、3D姿态、点云、文本等信息发送到Rerun Viewer进行交互式展示和分析。
    - **HTML/Flask**: 对于简单的可视化需求或离线报告，可以将数据（如图像序列、图表）渲染到HTML页面中，可以通过Flask等Web框架在本地启动一个服务进行查看。
    - **Matplotlib/OpenCV**: 对于单个图像、图表绘制或简单的视频播放，可以直接在Python脚本中使用Matplotlib或OpenCV进行可视化。

#### **3.2.2.6 数据集加载与使用示例**

结合 `torch.utils.data.DataLoader` 使用 `LeRobotDataset` 进行批量数据加载是训练过程中的标准做法：

```python
import torch
from torch.utils.data import DataLoader
# (假设dataset实例已按3.2.2.2中的方式创建好)

if 'dataset' in locals() and dataset is not None: # 确保dataset已创建
    # 创建DataLoader
    # LeRobotDataset 可能自身就提供了 get_dataloader 方法
    if hasattr(dataset, 'get_dataloader'):
        dataloader = dataset.get_dataloader(
            batch_size=32,
            shuffle=True, # 在训练时通常打乱数据
            num_workers=4, # 使用多个子进程加载数据，加快速度
            pin_memory=True if torch.cuda.is_available() else False,
            # drop_last=True # 如果最后一个batch不完整，是否丢弃
        )
    else: # 或者标准用法
        dataloader = DataLoader(
            dataset,
            batch_size=32,
            shuffle=True,
            num_workers=4,
            pin_memory=True if torch.cuda.is_available() else False,
            # collate_fn=dataset.collate_fn # 如果LeRobotDataset提供了自定义的collate_fn
        )

    print(f"DataLoader已创建。")

    # 遍历DataLoader获取批量数据
    # for batch_idx, batch_data in enumerate(dataloader):
    #     if batch_idx >= 2: # 仅演示前2个batch
    #         break
    #     print(f"\nBatch {batch_idx + 1}:")
    #     for key, value in batch_data.items():
    #         if isinstance(value, torch.Tensor):
    #             print(f"  {key}: shape={value.shape}, device={value.device}")
    #         elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], torch.Tensor):
    #              print(f"  {key}: list of tensors, first item shape={value[0].shape}")
    #         else:
    #             print(f"  {key}: type={type(value)}")
        # 在这里，batch_data可以直接送入策略模型的 train_step 或 compute_loss 方法
else:
    print("Dataset 未成功创建，跳过DataLoader演示。")
```

`DataLoader` 负责将单个样本聚合成批次 (batch)，并可以并行加载数据，是PyTorch生态中数据处理的重要一环。`LeRobotDataset` 的设计与 `DataLoader` 良好兼容。

### **3.2.3 环境接口 (Environment Interfaces)**

LeRobot 框架的环境接口提供了一个统一的抽象层，使策略模型能够与各种机器人仿真环境进行交互。这种设计遵循了**单一职责原则**，将环境交互逻辑与策略模型分离，提高了代码的可重用性和可维护性。

![decd4e216a7d4a64a4c53bc150af6abd.png](https://oss.guyuehome.com/upload/2025/06/262148346192/decd4e216a7d4a64a4c53bc150af6abd.png)

#### **3.2.3.1 `make_env()`工厂函数**

与策略系统和数据集管理类似，环境接口也采用了工厂模式，通过 `make_env()` 函数统一创建不同类型的环境实例：

```python
from lerobot.common.envs import make_env
import gymnasium as gym

# 示例：创建一个 PushT 环境
env_config = {
    "env_name": "PushT-v0",
    "num_envs": 4,  # 并行环境数量
    "asynchronous": True,  # 是否异步执行
    "env_kwargs": {
        "render_mode": "rgb_array",
        "reward_type": "dense",
        # 其他特定于 PushT 环境的参数
    }
}

env = make_env(**env_config)
print(f"创建的环境: {env}")

# 查看环境的观察空间和动作空间
print(f"观察空间: {env.observation_space}")
print(f"动作空间: {env.action_space}")

# 初始化环境
observation, info = env.reset()
print(f"初始观察的形状: {observation.shape if hasattr(observation, 'shape') else '非张量类型'}")
```

这种工厂模式设计允许框架灵活地支持不同的环境实现，同时保持一致的接口。环境创建逻辑的集中化也使得添加新环境类型变得简单。

#### **3.2.3.2 基于 Gymnasium 的环境标准**

LeRobot 的环境接口基于 Gymnasium API（OpenAI Gym 的继承者），这是强化学习社区广泛采用的标准。

关键接口方法包括：

- **`reset()`**: 重置环境到初始状态，返回初始观察和相关信息。
- **`step(action)`**: 执行一个动作，推进环境一个时间步，返回新的观察、奖励、终止标志、截断标志和额外信息。
- **`render()`**: 渲染环境的当前状态，可用于可视化。
- **`close()`**: 释放环境资源。

这种标准化的接口使得 LeRobot 框架中的不同组件（如策略、评估器）能够与各种环境无缝协作，无需了解具体环境的实现细节。

#### **3.2.3.3 支持的环境类型**

LeRobot 目前支持多种机器人仿真环境，每种环境针对不同类型的机器人任务和机构：

- **Aloha 环境**:
    - **描述**: 专为双臂机器人设计的仿真环境，支持多种双臂操作任务如物体抓取、放置、推动等。
    - **特点**: 精确的物理仿真、逼真的物体交互、可配置的任务目标。
    - **适用场景**: 双臂协作抓取、精细操作、组装任务研究。
- **PushT 环境**:
    - **描述**: 专注于物体推动任务的仿真环境，通常包含一个平面工作区和各种形状的物体。
    - **特点**: 简化的物理模型、高效的仿真速度、丰富的任务变体（如推动到目标、排列物体等）。
    - **适用场景**: 研究无抓取操作策略、物体位置控制、基于视觉的操作规划。
- **XArm 环境**:
    - **描述**: 针对 XArm 机械臂系列的仿真环境，支持多种末端执行器配置和任务场景。
    - **特点**: 高精度的正逆运动学模型、支持力反馈、与真实 XArm 硬件的高度一致性。
    - **适用场景**: 工业抓取应用、末端执行器精确控制、机器人操作技能开发。

![196973cbee714a60b8b32380cc1bc13c.png](https://oss.guyuehome.com/upload/2025/06/262148463269/196973cbee714a60b8b32380cc1bc13c.png)

### **3.2.3.4 环境观察处理**

为了适配不同策略模型的输入需求，LeRobot 提供了一系列环境观察处理工具 (Environment Observation Processing)：

- **`preprocess_observation()`**: 将原始环境观察转换为策略所需的格式。这可能包括图像裁剪、调整大小、归一化等操作。
- **`env_to_policy_features()`**: 将环境特征映射到策略特征空间，处理字段名称映射和数据结构转换等问题。

```python
from lerobot.common.envs.utils import preprocess_observation, env_to_policy_features

# 假设env_obs是从环境step()方法返回的原始观察
# 预处理环境观察
processed_obs = preprocess_observation(
    env_obs,
    image_size=(224, 224),  # 调整图像大小
    normalize=True,  # 是否归一化
    # 其他预处理参数
)

# 将环境特征转换为策略特征
policy_obs = env_to_policy_features(
    processed_obs,
    # 特征映射配置
    feature_map={
        "camera_image": "observation.image",  # 环境特征名到策略特征名的映射
        "robot_state": "observation.state"
    }
)
```

这些工具在训练和评估脚本中起到关键作用，确保环境输出和策略输入之间的兼容性。

#### **3.2.3.5 向量化环境**

为了提高采样效率，LeRobot 支持向量化环境（Vectorized Environments），即同时运行多个环境实例：

```python
# 创建8个并行的环境实例
vectorized_env = make_env(
    env_name="PushT-v0",
    num_envs=8,
    asynchronous=True,  # 异步执行可以进一步提高效率
    # 其他参数
)

# 重置所有环境
observations, infos = vectorized_env.reset()
print(f"向量化环境观察形状: {observations.shape}")  # 应为(8, ...)

# 对所有环境执行相同的动作
actions = [env.action_space.sample() for _ in range(8)]  # 示例：随机动作
next_observations, rewards, terminateds, truncateds, infos = vectorized_env.step(actions)
```

向量化环境不仅加快了数据收集速度，还能提高训练的稳定性，因为策略同时接收多个不同环境状态的反馈。

#### **3.2.3.6 环境接口使用示例**

下面是一个完整的环境使用示例，展示了如何创建环境、与环境交互、使用策略模型进行推理：

```python
import numpy as np
import torch
from lerobot.common.envs import make_env
from lerobot.common.policies import make_policy

# 创建环境
env = make_env(
    env_name="PushT-v0",
    num_envs=1,  # 单个环境实例
    env_kwargs={
        "render_mode": "rgb_array",
        # 其他环境参数
    }
)

# 创建策略（或加载预训练策略）
policy = make_policy(
    "diffusion",  # 或其他策略类型
    policy_config={
        "obs_dim": 256,  # 示例维度
        "action_dim": 2,
        # 其他策略参数
    },
    device="cuda" if torch.cuda.is_available() else "cpu"
)

# 策略评估循环
episode_rewards = []
num_episodes = 5

for episode in range(num_episodes):
    obs, info = env.reset()
    done = False
    episode_reward = 0

    # 存储观察历史（对于需要序列输入的策略）
    obs_history = [obs]

    while not done:
        # 准备策略输入
        if len(obs_history) > policy.obs_horizon:
            recent_obs = obs_history[-policy.obs_horizon:]
        else:
            # 如果历史不够长，可以复制最早的观察来填充
            padding = [obs_history[0]] * (policy.obs_horizon - len(obs_history))
            recent_obs = padding + obs_history

        # 构造策略观察字典
        policy_obs = {
            "observation.image_features": torch.tensor(np.array([o["image_features"] for o in recent_obs]),
                                                      dtype=torch.float32).unsqueeze(0).to(policy.device),
            "observation.state": torch.tensor(np.array([o["state"] for o in recent_obs]),
                                            dtype=torch.float32).unsqueeze(0).to(policy.device),
            # 其他必要字段
        }

        # 获取策略动作
        with torch.no_grad():
            action_dict = policy.predict(policy_obs)
            action = action_dict["action"][0, 0].cpu().numpy()  # 取第一个预测步的动作

        # 执行动作
        next_obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated

        # 更新状态
        obs = next_obs
        obs_history.append(obs)
        episode_reward += reward

    episode_rewards.append(episode_reward)
    print(f"Episode {episode+1}, Reward: {episode_reward:.2f}")

print(f"平均奖励: {np.mean(episode_rewards):.2f} ± {np.std(episode_rewards):.2f}")

# 关闭环境
env.close()
```

### **3.2.4 机器人控制**

机器人控制系统 (Robot Control)是 LeRobot 框架中负责与物理机器人硬件交互的关键组件。它将抽象的策略指令转化为实际的机器人运动控制，并从真实机器人中获取传感器反馈。

![6b71f05a3efb45129bb25af2bf387d13.png](https://oss.guyuehome.com/upload/2025/06/262149011596/6b71f05a3efb45129bb25af2bf387d13.png)

#### **3.2.4.1 `control_robot.py` 核心脚本**

LeRobot 的物理机器人控制主要通过 `control_robot.py` 脚本实现，它提供了丰富的命令行选项，支持多种控制模式：

```bash
python lerobot/scripts/control_robot.py --mode=[teleoperation/record/replay/calibrate] \
  --robot_type=[manipulator/mobile] \
  --policy_path=[path_to_policy_checkpoint] \
  --output_dir=[path_to_save_data] \
  # 其他特定于模式和机器人类型的参数
```

主要控制模式包括：

- **遥操作模式（Teleoperation）**: 允许人类操作者通过键盘、控制器或其他输入设备远程控制机器人。这对于收集示范数据或验证机器人功能尤为有用。
- **记录模式（Record）**: 在操作机器人的同时，记录传感器数据（如图像、关节状态）和控制指令，形成可用于训练的数据集。记录的数据会被整合到 `LeRobotDataset` 格式中。
- **回放模式（Replay）**: 重现先前记录的轨迹或部署学习策略，将策略模型的输出转换为实际的机器人控制指令。
- **校准模式（Calibrate）**: 用于机器人传感器和执行器的校准，确保控制精度。

![2381b1b567e94de888713dd8e045adc2.png](https://oss.guyuehome.com/upload/2025/06/262149172298/2381b1b567e94de888713dd8e045adc2.png)

#### **3.2.4.2 支持的机器人类型**

LeRobot 框架设计为支持多种类型的机器人硬件：

- **操作型机器人（Manipulator）**:
    - **描述**: 固定基座的机械臂，通常具有多个关节和末端执行器。
    - **支持的型号**: 包括但不限于各种工业机械臂、定制研究平台和经济型桌面机械臂。
    - **控制接口**: 通常基于关节角度或末端执行器笛卡尔坐标控制。
- **移动机器人（Mobile）**:
    - **描述**: 能够在环境中移动的平台，可能配备各种传感器和简单的操作装置。
    - **支持的型号**: 包括轮式移动机器人、差速驱动平台等。
    - **控制接口**: 通常基于速度命令（线速度、角速度）或位置目标。

#### **3.2.4.3 硬件接口**

LeRobot 提供了一系列硬件接口，用于连接和控制不同的机器人组件：

- **电机驱动接口**:
    - **Dynamixel SDK**: 用于控制 ROBOTIS Dynamixel 系列伺服电机，这是机器人社区常用的高性能执行器。
    - **FeeTech Servo SDK**: 支持 FeeTech 伺服电机，这是另一种流行的机器人执行器选择。
    - **自定义电机驱动**: 框架允许集成其他电机类型的驱动程序。
- **传感器接口**:
    - **相机接口**:
        - **OpenCV**: 支持通过 OpenCV 访问通用网络摄像头和视频设备。
        - **RealSense SDK**: 为英特尔 RealSense 深度相机提供专门支持，可获取 RGB 图像和深度数据。
    - **力/触觉传感器**: 支持力传感器和触觉反馈设备的数据采集。
    - **姿态传感器**: 用于获取机器人各部件的位置和方向信息。

```python
# 示例：配置电机和相机接口
robot_config = {
    "motor_interface": {
        "type": "dynamixel",
        "port": "/dev/ttyUSB0",
        "baudrate": 1000000,
        "motor_ids": [1, 2, 3, 4, 5, 6],  # 电机ID列表
        "protocol": 2.0  # Dynamixel 协议版本
    },
    "camera_interface": {
        "type": "realsense",
        "device_id": "",  # 空字符串表示使用默认设备
        "resolution": [640, 480],
        "fps": 30,
        "enable_depth": True
    }
}
```

框架采用模块化设计，允许轻松扩展以支持新的硬件类型，只需实现相应的接口类。

#### **3.2.4.4 遥操作与数据录制**

遥操作和数据录制功能对于收集高质量的演示数据至关重要，这些数据是进行模仿学习的基础：

- **遥操作接口**:
    - **键盘控制**: 通过键盘按键映射到机器人动作。
    - **游戏控制器**: 支持使用 Xbox、PlayStation 或其他游戏控制器进行精细操作。
    - **3D空间鼠标**: 提供直观的三维空间控制。
    - **VR控制器**: 支持通过虚拟现实控制器实现沉浸式远程控制。
- **数据录制流程**:
    1. 初始化机器人和传感器。
    2. 启动遥操作界面。
    3. 操作者控制机器人完成任务。
    4. 系统同步记录所有传感器数据和控制指令。
    5. 数据被保存为标准 LeRobot 数据集格式。
    6. 可选的实时质量监控和可视化。

```python
# 使用命令行启动遥操作和录制会话的示例
python lerobot/scripts/control_robot.py \
  --mode=record \
  --robot_type=manipulator \
  --control_device=keyboard \
  --output_dir=datasets/my_demo_dataset \
  --record_video=True \
  --record_frequency=20  # 每秒记录的帧数
```

录制的数据可以直接用于训练模仿学习策略，或者通过 Hugging Face Hub 共享给社区。

#### **3.2.4.5 将策略模型部署到物理机器人**

将训练好的策略应用于实际机器人是 LeRobot 框架的关键功能之一：

- **部署流程**:
    1. 加载训练好的策略模型。
    2. 初始化物理机器人及其传感器。
    3. 建立传感器数据到策略输入的映射。
    4. 建立策略输出到机器人控制指令的映射。
    5. 在控制循环中执行策略推理和机器人控制。
    6. 可选的实时可视化和监控。

```bash
# 使用命令行部署策略模型的示例
python lerobot/scripts/control_robot.py \
  --mode=replay \
  --robot_type=manipulator \
  --policy_path=lerobot/diffusion_pusht_image_g8acc \
  --control_frequency=20 \
  --safety_limits=True
```

#### **3.2.4.6 机器人控制代码示例**

下面是一个简化的代码示例，展示了如何使用 LeRobot 框架控制物理机器人并部署学习策略：

```python
import time
from lerobot.common.policies import make_policy
from lerobot.common.robot_devices import create_robot_interface

# 加载策略模型
policy = make_policy(
    policy_name_or_path="lerobot/diffusion_pusht_real",  # 从Hugging Face Hub加载
    device="cuda"  # 或 "cpu" 用于没有GPU的系统
)

# 创建机器人接口
robot = create_robot_interface(
    robot_type="manipulator",
    motor_config={
        "type": "dynamixel",
        "port": "/dev/ttyUSB0",
        "baudrate": 1000000,
        "motor_ids": [1, 2, 3, 4, 5, 6]
    },
    camera_config={
        "type": "realsense",
        "resolution": [640, 480],
        "fps": 30
    },
    # 其他配置参数
)

# 初始化机器人和相机
robot.initialize()
print("机器人初始化完成")

try:
    # 控制循环
    control_frequency = 20  # Hz
    period = 1.0 / control_frequency

    while True:
        loop_start = time.time()

        # 获取传感器观察
        observations = robot.get_observations()

        # 处理观察，转换为策略输入格式
        policy_obs = process_observations_for_policy(observations, policy)

        # 使用策略生成动作
        with torch.no_grad():
            action_dict = policy.predict(policy_obs)
            action = action_dict["action"][0, 0].cpu().numpy()  # 第一个预测步的动作

        # 执行动作
        robot.execute_action(action)

        # 等待以维持稳定的控制频率
        elapsed = time.time() - loop_start
        if elapsed < period:
            time.sleep(period - elapsed)
        else:
            print(f"警告：控制循环超时 {elapsed*1000:.1f}ms > {period*1000:.1f}ms")

except KeyboardInterrupt:
    print("用户中断，正在安全停止机器人...")
finally:
    # 确保机器人安全停止
    robot.stop()
    robot.shutdown()
    print("机器人已安全关闭")
```

此示例展示了机器人控制的基本流程，包括初始化、传感器数据获取、策略推理和动作执行。在实际应用中，还需要考虑更多的安全检查、错误处理和状态监控。

## **3.3 训练与评估流程**

LeRobot 提供了结构化的训练和评估流程(Training and Evaluation Process)，使研究者能够有效地开发和测试机器人学习策略。这些流程通过 `train.py` 和 `eval.py` 脚本实现，它们整合了前面讨论的四大核心子系统。

![bb2dfa6eaa0440099639ea94f367948d.png](https://oss.guyuehome.com/upload/2025/06/262149337377/bb2dfa6eaa0440099639ea94f367948d.png)

### **3.3.1 训练流程**

训练流程(Training Pipeline)是策略从数据中学习的关键过程，LeRobot 的 `train.py` 脚本提供了一个完整、灵活的训练框架。

#### **3.3.1.1 训练流程概览**

标准训练流程包括以下主要步骤：

1. **解析配置与参数**: 使用 Hydra 框架解析配置文件和命令行参数。
2. **创建数据集**: 使用 `make_dataset()` 加载训练数据。
3. **创建环境** (可选): 使用 `make_env()` 创建用于评估的环境。
4. **创建策略模型**: 使用 `make_policy()` 创建或加载策略模型。
5. **创建优化器与调度器**: 配置用于模型参数更新的优化算法。
6. **训练循环**:
    - 从数据集批量加载数据
    - 计算损失函数
    - 反向传播更新模型参数
    - 定期评估、记录指标和保存检查点
7. **生成最终模型**: 训练结束后保存最终模型和结果摘要。

#### **3.3.1.2 使用命令行接口**

LeRobot 的训练脚本提供了丰富的命令行选项，使用户能够灵活配置训练过程：

```bash
python lerobot/scripts/train.py \
  --config=configs/train/diffusion_pusht.yaml \
  policy=diffusion \
  dataset=pusht \
  training.batch_size=64 \
  training.num_epochs=100 \
  training.learning_rate=1e-4 \
  evaluation.eval_freq=5 \
  # 其他参数...
```

这里使用了 Hydra 的层次化配置系统，允许通过命令行覆盖配置文件中的默认值。

#### **3.3.1.3 配置系统**

LeRobot 使用 Hydra 和 OmegaConf 为训练流程提供强大的配置管理：

- **层次化配置**: 将配置分为多个逻辑组，如策略配置、数据集配置、训练参数等。
- **组合与继承**: 支持从基础配置继承和组合多个配置组。
- **参数验证**: 确保所有必需参数都已提供且类型正确。
- **配置版本控制**: 配置文件可以与代码一起版本控制，确保实验的可复现性。

```python
# 配置文件示例 (configs/train/diffusion_pusht.yaml)
defaults:
  - policy: diffusion
  - dataset: pusht
  - training: default
  - _self_

policy:
  obs_dim: 256
  action_dim: 2
  pred_horizon: 16
  obs_horizon: 2
  action_horizon: 8
  # 更多策略特定参数...

dataset:
  name: lerobot/pusht
  split: train
  # 更多数据集特定参数...

training:
  batch_size: 64
  num_epochs: 100
  learning_rate: 1e-4
  weight_decay: 1e-5
  # 更多训练特定参数...

evaluation:
  enabled: true
  eval_freq: 5  # 每5个epoch评估一次
  env_name: PushT-v0
  num_eval_episodes: 20
  # 更多评估特定参数...

logging:
  log_dir: outputs/train/${now:%Y-%m-%d}/${now:%H-%M-%S}
  use_wandb: false
  project_name: lerobot-training
  # 更多日志特定参数...
```

这种结构化配置使得实验设置清晰、可读且易于修改。

#### **3.3.1.4 优化器与学习率调度**

LeRobot 支持多种优化算法和学习率调度策略 (Optimizers and Learning Rate Scheduling)：

```python
def make_optimizer_and_scheduler(model, config):
    """创建优化器和学习率调度器"""
    # 参数组，可以为不同参数设置不同的学习率
    param_groups = [
        {'params': model.parameters(), 'lr': config.learning_rate}
    ]

    # 创建优化器
    if config.optimizer == 'adam':
        optimizer = torch.optim.Adam(
            param_groups,
            weight_decay=config.weight_decay
        )
    elif config.optimizer == 'adamw':
        optimizer = torch.optim.AdamW(
            param_groups,
            weight_decay=config.weight_decay
        )
    else:
        raise ValueError(f"不支持的优化器类型: {config.optimizer}")

    # 创建学习率调度器
    if config.lr_scheduler == 'cosine':
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=config.num_epochs,
            eta_min=config.min_lr
        )
    elif config.lr_scheduler == 'step':
        scheduler = torch.optim.lr_scheduler.StepLR(
            optimizer,
            step_size=config.lr_step_size,
            gamma=config.lr_gamma
        )
    elif config.lr_scheduler == 'none':
        scheduler = None
    else:
        raise ValueError(f"不支持的学习率调度器: {config.lr_scheduler}")

    return optimizer, scheduler
```

不同的策略模型可能需要不同的优化设置。例如，Diffusion Policy通常使用AdamW优化器配合余弦退火学习率调度，而Transformer类模型(如ACT)可能需要特殊的预热-退火组合调度。LeRobot框架允许通过配置灵活调整这些参数，以达到最优训练效果。

#### **3.3.1.5 训练循环详解**

训练循环 (Training Loop)是整个训练过程的核心，这里我们来看一个简化的训练循环实现：

```python
def train_policy(policy, dataloader, optimizer, scheduler, config):
    """策略训练的主循环"""
    # 设置训练模式
    policy.train()

    # 训练指标跟踪
    metrics = {
        'train_loss': [],
        'train_loss_components': defaultdict(list),
        'learning_rates': []
    }

    # 进度条
    progress_bar = tqdm(total=len(dataloader), desc="训练批次")

    # 批次迭代
    for batch_idx, batch in enumerate(dataloader):
        # 记录当前学习率
        current_lr = optimizer.param_groups[0]['lr']
        metrics['learning_rates'].append(current_lr)

        # 将数据移至策略所在设备
        batch = {k: v.to(policy.device) if isinstance(v, torch.Tensor) else v
                 for k, v in batch.items()}

        # 前向传播和损失计算
        loss_dict = policy.compute_loss(batch)
        total_loss = loss_dict['loss']

        # 反向传播和参数更新
        optimizer.zero_grad()
        total_loss.backward()

        # 梯度裁剪（可选）
        if config.clip_grad_norm > 0:
            torch.nn.utils.clip_grad_norm_(
                policy.parameters(),
                config.clip_grad_norm
            )

        optimizer.step()

        # 记录损失
        metrics['train_loss'].append(total_loss.item())
        for loss_name, loss_value in loss_dict.items():
            if isinstance(loss_value, torch.Tensor):
                metrics['train_loss_components'][loss_name].append(loss_value.item())

        # 更新进度条
        progress_bar.update(1)
        if batch_idx % 10 == 0:  # 每10个批次更新一次进度条描述
            avg_loss = np.mean(metrics['train_loss'][-10:])
            progress_bar.set_description(f"训练批次 (Loss: {avg_loss:.4f})")

        # 日志记录、提前停止、检查点保存等逻辑
        # ...

    progress_bar.close()

    # 学习率调度（按epoch）
    if scheduler is not None:
        scheduler.step()

    return metrics
```

这个循环包含了以下关键步骤：

- 将策略模型设置为训练模式
- 遍历数据加载器中的所有批次
- 将批次数据移至正确的设备(CPU/GPU)
- 计算损失函数
- 执行反向传播
- 可选的梯度裁剪
- 更新模型参数
- 记录训练指标
- 更新学习率

#### **3.3.1.6 日志与可视化**

LeRobot支持多种训练日志和可视化(Logging and Visualization)工具，帮助研究者监控训练进度和分析实验结果：

- **TensorBoard**: 用于记录和可视化标量指标（如损失值、准确率）、图像、模型图结构等。
- **Weights & Biases (wandb)**: 提供更强大的实验跟踪和团队协作功能，支持实验对比、超参数搜索等。
- **Rerun**: 专为机器人和计算机视觉设计的可视化工具，可展示时间序列数据、3D场景等。
- **自定义HTML报告**: 生成包含训练曲线、示例预测、评估结果的HTML报告。

```python
# Tensorboard 日志记录示例
from torch.utils.tensorboard import SummaryWriter

def setup_logging(config):
    """设置训练日志记录"""
    log_dir = config.logging.log_dir
    os.makedirs(log_dir, exist_ok=True)

    # 设置TensorBoard
    tb_writer = SummaryWriter(log_dir=os.path.join(log_dir, 'tensorboard'))

    # 设置Weights & Biases（如果启用）
    if config.logging.use_wandb:
        import wandb
        wandb.init(
            project=config.logging.project_name,
            name=config.logging.run_name,
            config=OmegaConf.to_container(config, resolve=True)
        )

    return {
        'tb_writer': tb_writer,
        'log_dir': log_dir
    }

def log_metrics(metrics, step, logger):
    """记录训练指标"""
    # TensorBoard日志
    for metric_name, metric_value in metrics.items():
        if isinstance(metric_value, (int, float)):
            logger['tb_writer'].add_scalar(f'metrics/{metric_name}', metric_value, step)
        elif isinstance(metric_value, dict):
            for sub_name, sub_value in metric_value.items():
                if isinstance(sub_value, (int, float)):
                    logger['tb_writer'].add_scalar(f'metrics/{metric_name}/{sub_name}', sub_value, step)

    # Weights & Biases日志
    if 'wandb' in sys.modules:
        import wandb
        wandb.log(metrics, step=step)
```

这些工具使研究者能够深入了解训练动态，比较不同实验设置的效果，并分享结果。

### **3.3.2 评估流程**

训练完成后，评估流程 (Evaluation Pipeline)帮助研究者量化策略模型的性能并生成可视化结果，以验证其能否满足预期目标。

### **3.3.2.1 评估流程概览**

LeRobot的 `eval.py` 脚本提供了全面的评估功能，评估流程通常包括以下步骤：

1. **解析配置与参数**: 使用Hydra加载评估配置。
2. **创建环境**: 使用 `make_env()` 创建评估环境。
3. **加载策略模型**: 使用 `make_policy()` 加载训练好的策略。
4. **执行评估**: 在环境中运行策略，收集指标和轨迹。
5. **结果分析与可视化**: 计算成功率、平均奖励等指标，并生成评估视频和报告。

#### **3.3.2.2 使用命令行接口**

评估脚本也提供了灵活的命令行接口：

```bash
python lerobot/scripts/eval.py \
  --config=configs/eval/diffusion_pusht.yaml \
  policy.name_or_path=lerobot/diffusion_pusht_image_g8acc \
  env.name=PushT-v0 \
  eval.num_episodes=50 \
  eval.save_video=True \
  # 其他参数...
```

这种接口允许轻松配置评估设置、策略加载路径和结果保存选项。

#### **3.3.2.3 评估指标**

根据任务性质和研究目标，LeRobot支持多种评估指标(Evaluation Metrics)：

- **任务成功率**: 策略成功完成任务的百分比。
- **平均奖励**: 每个评估回合中获得的平均累积奖励。
- **完成时间**: 成功完成任务所需的平均步数或时间。
- **轨迹平滑度**: 衡量动作序列的平滑性，对于机器人控制尤为重要。
- **物体交互指标**: 如抓取成功率、放置精度等特定于任务的指标。
- **域迁移指标**: 评估从仿真到现实世界的策略泛化能力。

```python
def compute_metrics(episodes_data):
    """计算评估指标"""
    metrics = {}

    # 成功率
    successes = [ep['success'] for ep in episodes_data]
    metrics['success_rate'] = np.mean(successes)

    # 平均奖励
    rewards = [sum(ep['rewards']) for ep in episodes_data]
    metrics['mean_reward'] = np.mean(rewards)
    metrics['std_reward'] = np.std(rewards)

    # 平均回合长度
    lengths = [len(ep['rewards']) for ep in episodes_data]
    metrics['mean_episode_length'] = np.mean(lengths)

    # 若有其他任务特定指标
    if all('distance_to_goal' in ep for ep in episodes_data):
        final_distances = [ep['distance_to_goal'][-1] for ep in episodes_data]
        metrics['mean_final_distance'] = np.mean(final_distances)

    return metrics
```

这些指标帮助研究者全面评估策略的性能并指导进一步改进。

#### **3.3.2.4 环境推出与轨迹收集**

评估过程的核心是在目标环境中执行策略并收集轨迹数据(Environment Rollouts and Trajectory Collection)：

```python
def rollout(env, policy, config):
    """在环境中执行策略并收集轨迹"""
    # 存储评估回合数据
    episodes_data = []

    # 每个评估回合
    for episode_idx in range(config.num_episodes):
        episode_data = {
            'observations': [],
            'actions': [],
            'rewards': [],
            'next_observations': [],
            'terminateds': [],
            'truncateds': [],
            'infos': []
        }

        # 重置环境
        obs, info = env.reset()
        done = False

        # 存储初始观察
        episode_data['observations'].append(obs)

        # 初始化观察历史（用于需要历史上下文的策略）
        obs_history = [obs]

        while not done:
            # 准备策略输入
            policy_obs = prepare_policy_obs(obs_history, policy.obs_horizon)

            # 获取策略动作
            with torch.no_grad():
                action_dict = policy.predict(policy_obs)
                action = extract_action(action_dict)

            # 执行动作
            next_obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated

            # 更新观察历史
            obs_history.append(next_obs)
            if len(obs_history) > policy.obs_horizon * 2:  # 限制历史长度
                obs_history = obs_history[-policy.obs_horizon * 2:]

            # 存储回合数据
            episode_data['actions'].append(action)
            episode_data['rewards'].append(reward)
            episode_data['next_observations'].append(next_obs)
            episode_data['terminateds'].append(terminated)
            episode_data['truncateds'].append(truncated)
            episode_data['infos'].append(info)

            # 更新当前观察
            obs = next_obs
            episode_data['observations'].append(obs)

        # 计算回合成功与否
        if 'success' in info:
            episode_data['success'] = info['success']
        else:
            # 如果环境没有提供success信息，可以根据任务定义
            episode_data['success'] = any(reward > config.success_reward_threshold
                                         for reward in episode_data['rewards'])

        episodes_data.append(episode_data)
        print(f"回合 {episode_idx+1}/{config.num_episodes} "
              f"完成，{'成功' if episode_data['success'] else '失败'}")

    return episodes_data
```

这个函数执行一系列评估回合，收集详细的轨迹数据，包括观察、动作、奖励等，以便后续分析。

### **3.3.2.5 视频生成 (Video Generation)**

评估结果的可视化对于理解策略行为至关重要。LeRobot可以生成评估轨迹的视频演示：

```python
def generate_evaluation_videos(episodes_data, env, config):
    """从评估数据生成视频"""
    video_dir = os.path.join(config.output_dir, 'videos')
    os.makedirs(video_dir, exist_ok=True)

    # 选择要录制的回合
    episodes_to_record = []

    # 确保包含成功和失败的案例
    successful_episodes = [i for i, ep in enumerate(episodes_data) if ep['success']]
    failed_episodes = [i for i, ep in enumerate(episodes_data) if not ep['success']]

    # 如果有成功案例，选择部分成功的回合
    if successful_episodes:
        num_success_to_record = min(config.num_videos // 2, len(successful_episodes))
        episodes_to_record.extend(random.sample(successful_episodes, num_success_to_record))

    # 如果有失败案例，选择部分失败的回合
    if failed_episodes:
        num_fail_to_record = min(config.num_videos - len(episodes_to_record), len(failed_episodes))
        episodes_to_record.extend(random.sample(failed_episodes, num_fail_to_record))

    # 如果还不够，随机选择
    if len(episodes_to_record) < config.num_videos:
        remaining = list(set(range(len(episodes_data))) - set(episodes_to_record))
        episodes_to_record.extend(random.sample(remaining,
                                              min(config.num_videos - len(episodes_to_record),
                                                 len(remaining))))

    # 录制选定的回合
    video_paths = []
    for ep_idx in episodes_to_record:
        episode = episodes_data[ep_idx]
        video_path = os.path.join(video_dir, f"episode_{ep_idx}_{'success' if episode['success'] else 'failure'}.mp4")

        # 使用环境的render方法重新创建并录制回合
        video_frames = []

        # 重置环境到回合初始状态(可能需要设置随机种子或初始状态)
        env.reset(seed=episode.get('seed', None))

        # 重放动作序列并收集渲染帧
        for action in episode['actions']:
            env.step(action)
            frame = env.render()
            video_frames.append(frame)

        # 将帧保存为视频
        save_video(video_frames, video_path, fps=config.video_fps)
        video_paths.append(video_path)

    return video_paths
```

这个函数选择评估回合的代表性子集，重放其中的动作序列并录制视频，这些视频可以直观地展示策略的行为和效果。

#### **3.3.2.6 结果报告生成**

为了方便分享和分析评估结果，LeRobot可以生成综合报告：

```python
def generate_evaluation_report(metrics, video_paths, config):
    """生成评估报告"""
    report_path = os.path.join(config.output_dir, 'evaluation_report.html')

    # 创建HTML报告
    with open(report_path, 'w') as f:
        f.write('<html><head><title>LeRobot评估报告</title>')
        f.write('<style>body{font-family:Arial;max-width:1200px;margin:0 auto;padding:20px;}')
        f.write('table{width:100%;border-collapse:collapse;}')
        f.write('th,td{padding:8px;text-align:left;border-bottom:1px solid #ddd;}</style>')
        f.write('</head><body>')

        # 报告标题
        f.write(f'<h1>LeRobot评估报告: {config.policy_name}</h1>')
        f.write(f'<p>环境: {config.env_name}</p>')
        f.write(f'<p>评估时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>')

        # 指标表格
        f.write('<h2>评估指标</h2>')
        f.write('<table><tr><th>指标</th><th>值</th></tr>')
        for metric_name, metric_value in metrics.items():
            f.write(f'<tr><td>{metric_name}</td><td>{metric_value:.4f}</td></tr>')
        f.write('</table>')

        # 评估视频
        if video_paths:
            f.write('<h2>评估视频</h2>')
            for i, video_path in enumerate(video_paths):
                rel_path = os.path.relpath(video_path, os.path.dirname(report_path))
                f.write(f'<h3>视频 {i+1}</h3>')
                f.write(f'<video width="400" controls><source src="{rel_path}" type="video/mp4">您的浏览器不支持视频标签</video>')

        f.write('</body></html>')

    print(f"评估报告已生成: {report_path}")
    return report_path
```

这些报告提供了结构化的评估结果展示，包括数字指标和视频演示，方便研究者分析策略的优缺点。

## **3.4 综合性的代码库结构**

理解LeRobot的代码库组织对于有效使用和扩展该框架至关重要。本节将详细介绍LeRobot的代码库结构 (Repository Structure)和关键组件。

### **3.4.1 代码库组织**

LeRobot的代码库按功能和模块化原则组织，主要包含以下目录结构：

```bash
lerobot/
├── examples             # 示例和教程，从这里开始学习LeRobot
│   └── advanced         # 包含更高级的示例
├── lerobot
│   ├── configs          # 包含可以在命令行中覆盖的所有选项的配置类
│   ├── common           # 包含核心功能类和工具
│   │   ├── datasets     # 各种人类演示数据集：aloha, pusht, xarm
│   │   ├── envs         # 各种模拟环境：aloha, pusht, xarm
│   │   ├── policies     # 各种策略实现：act, diffusion, tdmpc等
│   │   ├── robot_devices # 硬件接口：dynamixel电机，opencv相机，koch机器人
│   │   └── utils        # 各种工具函数
│   └── scripts          # 包含通过命令行执行的函数
│       ├── eval.py      # 加载策略并在环境中评估
│       ├── train.py     # 通过模仿学习和/或强化学习训练策略
│       ├── control_robot.py # 远程操作真实机器人，记录数据，运行策略
│       ├── push_dataset_to_hub.py # 将数据集转换为LeRobot数据集格式并上传到Hugging Face hub
│       └── visualize_dataset.py # 加载数据集并渲染其演示
├── outputs              # 包含脚本执行结果：日志、视频、模型检查点
└── tests                # 包含用于持续集成的pytest工具
```

这种结构遵循了Python项目的最佳实践，有助于代码的可维护性和可扩展性。

### **3.4.2 核心组件详解**

LeRobot的各个核心组件都有其特定的职责和设计理念：

- **lerobot/common/datasets/**：包含数据集加载、处理和管理的所有代码。核心类是`LeRobotDataset`，它处理多模态机器人数据，支持图像变换、序列处理和高效数据加载。
- **lerobot/common/envs/**：实现了与各种仿真环境的统一接口，基于Gymnasium标准。包含环境封装器、观察处理工具和环境工厂函数。
- **lerobot/common/policies/**：包含所有策略模型的实现，如ACT、Diffusion、TDMPC等。每个策略都实现了共同的`PreTrainedPolicy`接口，确保一致的使用方式。
- **lerobot/common/robot_devices/**：负责与物理机器人硬件通信的接口，包括电机控制、相机管理和传感器数据处理。
- **lerobot/configs/**：使用Hydra框架管理配置，提供层次化的配置系统，支持命令行覆盖和配置组合。
- **lerobot/scripts/**：包含主要的可执行脚本，这些脚本整合了框架的各个部分，提供从训练到部署的完整工作流。

# **4. 入门实践指南**

LeRobot框架设计得直观易用，本节将通过实际案例，展示如何快速开始使用LeRobot进行机器人学习。

## **4.1 安装与环境准备**

首先，让我们从安装框架开始：

```bash
# 克隆代码库
git clone https://github.com/huggingface/lerobot.git
cd lerobot

# 创建虚拟环境
conda create -n lerobot_env python=3.10
conda activate lerobot_env

# 安装ffmpeg(Ubuntu/Debian示例)
sudo apt update && sudo apt install ffmpeg

# 安装LeRobot核心包
pip install -e .

# 安装所需的可选组件(例如PushT环境)
pip install -e ".[pusht]"
```

## **4.2 加载和探索数据集**

数据是机器人学习的基础，让我们加载并探索一个数据集：

```python
from lerobot.common.datasets import make_dataset
import matplotlib.pyplot as plt
import torch
import numpy as np

# 加载PushT数据集的一小部分
dataset = make_dataset("lerobot/pusht", split="train[:1%]")
print(f"加载了 {len(dataset)} 个样本")

# 查看数据集规范
print(f"数据集名称: {dataset.spec.name}")
print(f"观察空间: {dataset.spec.observation_space}")
print(f"动作空间: {dataset.spec.action_space}")

# 访问单个样本
sample = dataset[0]
print("样本键:", list(sample.keys()))

# 可视化图像
if "observation.image" in sample:
    # 将图像从张量转换为NumPy数组
    image = sample["observation.image"]
    if isinstance(image, torch.Tensor):
        # 假设图像格式为 [T, C, H, W] 或 [C, H, W]
        if image.dim() == 4:  # [T, C, H, W]
            image = image[0]  # 取第一帧
        # 将 [C, H, W] 转为 [H, W, C]
        image = image.permute(1, 2, 0).numpy()
        # 如果已归一化，则恢复到0-1范围
        if image.max() <= 1.0:
            image = np.clip(image, 0, 1)
        else:
            image = np.clip(image / 255.0, 0, 1)

    plt.figure(figsize=(8, 8))
    plt.imshow(image)
    plt.title("示例观察图像")
    plt.axis('off')
    plt.show()

# 查看动作数据
if "action" in sample:
    action = sample["action"]
    print(f"动作形状: {action.shape}")
    print(f"动作值: {action.numpy() if isinstance(action, torch.Tensor) else action}")
```

## **4.3 使用预训练模型**

LeRobot提供了多个预训练策略模型，可以直接用于推理：

```python
import torch
from lerobot.common.policies import make_policy
from lerobot.common.envs import make_env

# 加载预训练的Diffusion Policy
policy = make_policy(
    "lerobot/diffusion_pusht_image_g8acc",  # Hugging Face Hub上的模型ID
    device="cuda" if torch.cuda.is_available() else "cpu"
)

# 创建评估环境
env = make_env(
    env_name="PushT-v0",
    env_kwargs={"render_mode": "rgb_array"}
)

# 重置环境
obs, info = env.reset()

# 初始化观察历史
obs_history = [obs]

# 运行一个回合
done = False
frames = []

while not done:
    # 准备策略输入
    # 注：实际应用中需要根据策略的具体要求构造观察字典
    # 这里只是示例框架
    policy_obs = {
        "observation.image_features": torch.tensor(np.array([o["image_features"] for o in obs_history[-policy.obs_horizon:]]),
                                                  dtype=torch.float32).unsqueeze(0).to(policy.device),
        "observation.state": torch.tensor(np.array([o["state"] for o in obs_history[-policy.obs_horizon:]]),
                                         dtype=torch.float32).unsqueeze(0).to(policy.device),
        # 可能需要其他字段，如掩码
    }

    # 获取策略动作
    with torch.no_grad():
        action_dict = policy.predict(policy_obs)
        action = action_dict["action"][0, 0].cpu().numpy()  # 取第一个预测步的动作

    # 执行动作
    next_obs, reward, terminated, truncated, info = env.step(action)
    done = terminated or truncated

    # 更新观察历史
    obs_history.append(next_obs)

    # 收集渲染帧
    frame = env.render()
    frames.append(frame)

    # 更新当前观察
    obs = next_obs

print(f"回合完成，{'成功' if info.get('success', False) else '失败'}")

# 可选：保存回合视频
# 需要先导入视频保存工具
# from lerobot.common.utils.video import save_video
# save_video(frames, "policy_rollout.mp4", fps=30)
```

## **4.4 训练自己的策略**

下面是一个使用LeRobot训练自己的策略的简化示例：

```bash
# 使用命令行接口运行训练
python lerobot/scripts/train.py \
  --config=configs/train/diffusion_pusht.yaml \
  policy=diffusion \
  dataset=pusht \
  training.batch_size=64 \
  training.num_epochs=100 \
  training.learning_rate=1e-4 \
  logging.log_dir=outputs/my_first_policy
```

训练完成后，可以使用评估脚本测试策略性能：

```bash
python lerobot/scripts/eval.py \
  --config=configs/eval/diffusion_pusht.yaml \
  policy.name_or_path=outputs/my_first_policy/checkpoints/latest \
  env.name=PushT-v0 \
  eval.num_episodes=10 \
  eval.save_video=True
```

## **4.5 部署到物理机器人**

如果有合适的硬件设置，可以将训练好的策略部署到实际机器人：

```bash
python lerobot/scripts/control_robot.py \
  --mode=replay \
  --robot_type=manipulator \
  --policy_path=outputs/my_first_policy/checkpoints/latest \
  --control_frequency=20 \
  --safety_limits=True
```

# **5. 结语**

LeRobot框架代表了机器人学习领域的一个重要里程碑，它不仅提供了强大的技术工具，更搭建了一个开放、协作的平台，使研究者和开发者能够共同推动机器人智能的进步。随着框架的不断发展和社区的壮大，我们有理由期待LeRobot在未来机器人应用中发挥更加关键的作用，并助力实现更智能、更灵活、更安全的机器人系统。