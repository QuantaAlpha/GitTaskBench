<p align="center">
  <a href="https://swe-agent.com/latest/">
    <img src="assets/swe-agent-banner.png" alt="swe-agent.com" style="height: 12em" />
  </a>
</p>

<p align="center">
  <a href="https://swe-agent.com/latest/"><strong>Documentation</strong></a>&nbsp; | &nbsp;
  <a href="https://discord.gg/AVEFbBn2rH"><strong>Discord</strong></a>&nbsp; | &nbsp;
  <a href="https://arxiv.org/abs/2405.15793"><strong>Paper</strong></a>
</p>

<div align="center">

[![Pytest](https://github.com/SWE-agent/SWE-agent/actions/workflows/pytest.yaml/badge.svg)](https://github.com/SWE-agent/SWE-agent/actions/workflows/pytest.yaml)
[![build-docs](https://github.com/SWE-agent/SWE-agent/actions/workflows/build-docs.yaml/badge.svg)](https://github.com/SWE-agent/SWE-agent/actions/workflows/build-docs.yaml)
[![codecov](https://codecov.io/gh/SWE-agent/SWE-agent/graph/badge.svg?token=18XAVDK365)](https://codecov.io/gh/SWE-agent/SWE-agent)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/SWE-agent/SWE-agent/main.svg)](https://results.pre-commit.ci/latest/github/SWE-agent/SWE-agent/main)
[![Markdown links](https://github.com/SWE-agent/SWE-agent/actions/workflows/check-links.yaml/badge.svg)](https://github.com/SWE-agent/SWE-agent/actions/workflows/check-links.yaml)

</div>

## 🎉 Batch Runner Ready for SWE-Agent

👉 The version of this ReadMe is for the version **SWE-agent v1.0.1-61-gaa4e8ea1**.

✅ We added a new feature in this version, please refer to the [Batch SWE-agent Runner For GitTaskBench](#Batch-SWE-agent-Runner-For-GitTaskBench) for more details.


SWE-agent lets your language model of choice (e.g. GPT-4o or Claude Sonnet 3.7) autonomously use tools to:

* [fix issues in real GitHub repositories](https://swe-agent.com/latest/usage/hello_world),
* perform tasks on the web,
* [find cybersecurity vulnerabilities](https://enigma-agent.com/) (by solving Capture The Flag challenges), or
* [any custom task](https://swe-agent.com/latest/usage/coding_challenges).

It does so by using configurable [agent-computer interfaces](https://arxiv.org/abs/2405.15793) (ACIs) to interact with isolated computer environments.

SWE-agent is built and maintained by researchers from Princeton University and Stanford University.

## 📣 News

* Feb 28: [SWE-agent 1.0 + Claude 3.7 is SoTA on SWE-Bench full](https://x.com/KLieret/status/1895487966409298067)
* Feb 25: [SWE-agent 1.0 + Claude 3.7 is SoTA on SWE-bench verified](https://x.com/KLieret/status/1894408819670733158)
* Feb 13: [Releasing SWE-agent 1.0: SoTA on SWE-bench light & tons of new features](https://x.com/KLieret/status/1890048205448220849)
* Dec 7: [An interview with the SWE-agent & SWE-bench team](https://www.youtube.com/watch?v=fcr8WzeEXyk)

## 🚀 Get started!

👉 Try SWE-agent in your browser: [![Open in GitHub Codespaces](https://img.shields.io/badge/Open_in_GitHub_Codespaces-gray?logo=github)](https://codespaces.new/SWE-agent/SWE-agent) ([more information](https://swe-agent.com/latest/installation/codespaces/))

Read our [documentation][docs] to learn more:

* [Installation](https://swe-agent.com/latest/installation/source/)
* [Hello world from the command line](https://swe-agent.com/latest/usage/hello_world/)
* [Benchmarking on SWE-bench](https://swe-agent.com/latest/usage/batch_mode/)
* [Frequently Asked Questions](https://swe-agent.com/latest/faq/)

[docs]: https://swe-agent.com

## SWE-agent for offensive cybersecurity (EnIGMA) <a name="enigma"></a>

<img src="https://github.com/user-attachments/assets/84599168-11a7-4776-8a49-33dbf0758bb2" height="80px"></img>

[SWE-agent: EnIGMA][enigma] is a mode for solving offensive cybersecurity (capture the flag) challenges.
EnIGMA achieves state-of-the-art results on multiple cybersecurity benchmarks (see [leaderboard](https://enigma-agent.com/#results)).
The EnIGMA project introduced multiple features that are available in all modes of SWE-agent, such as the [debugger and server connection tools](https://swe-agent.com/0.7/background/iat/) and a [summarizer](https://swe-agent.com/0.7/config/summarizers/) to handle long outputs. Please use [SWE-agent 0.7](https://github.com/SWE-agent/SWE-agent/tree/v0.7) while we update EnIGMA for 1.0.

[enigma]: https://enigma-agent.com
[SWE-bench]: https://github.com/SWE-bench/SWE-bench
[nyu-ctf]: https://arxiv.org/abs/2406.05590

## About
SWE-agent is an academic project started at Princeton University by John Yang*, Carlos E. Jimenez*, Alexander Wettig, Kilian Lieret, Shunyu Yao, Karthik Narasimhan, and Ofir Press.
Contact person: [John Yang](https://john-b-yang.github.io/), [Carlos E. Jimenez](http://www.carlosejimenez.com/), and [Kilian Lieret](https://www.lieret.net/) (Email: johnby@stanford.edu, carlosej@princeton.edu, kl5675@princeton.edu).

## Contributions <a name="contributions"></a>

- If you'd like to ask questions, learn about upcoming features, and participate in future development, join our [Discord community](https://discord.gg/AVEFbBn2rH)!
- If you'd like to contribute to the codebase, we welcome [issues](https://github.com/SWE-agent/SWE-agent/issues) and [pull requests](https://github.com/SWE-agent/SWE-agent/pulls)!

## Citation <a name="citation"></a>

If you found this work helpful, please consider citing it using the following:
```bibtex
@inproceedings{yang2024sweagent,
  title={{SWE}-agent: Agent-Computer Interfaces Enable Automated Software Engineering},
  author={John Yang and Carlos E Jimenez and Alexander Wettig and Kilian Lieret and Shunyu Yao and Karthik R Narasimhan and Ofir Press},
  booktitle={The Thirty-eighth Annual Conference on Neural Information Processing Systems},
  year={2024},
  url={https://arxiv.org/abs/2405.15793}
}
```

If you used the summarizer, interactive commands or the offensive cybersecurity capabilities in SWE-agent, please also consider citing:
```bibtex
@misc{abramovich2024enigmaenhancedinteractivegenerative,
      title={EnIGMA: Enhanced Interactive Generative Model Agent for CTF Challenges},
      author={Talor Abramovich and Meet Udeshi and Minghao Shao and Kilian Lieret and Haoran Xi and Kimberly Milner and Sofija Jancheska and John Yang and Carlos E. Jimenez and Farshad Khorrami and Prashanth Krishnamurthy and Brendan Dolan-Gavitt and Muhammad Shafique and Karthik Narasimhan and Ramesh Karri and Ofir Press},
      year={2024},
      eprint={2409.16165},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2409.16165},
}
```





<p align="center">
  <a href="https://swe-agent.com/latest/">
    <img src="assets/swe-agent-banner.png" alt="swe-agent.com" style="height: 12em" />
  </a>
</p>

# Batch SWE-agent Runner For GitTaskBench
<a name="Batch-SWE-agent-Runner-For-GitTaskBench"></a>

## 概述

该工具包含两个脚本 (`run_batch.sh` 和 `batch_sweagent_run.py`)，用于批量运行 SWE-agent 任务。它会按顺序处理指定目录下的所有 `.md` 问题描述文件。

主要功能包括：

1.  **批量执行**: 自动查找并运行指定目录下的所有 `.md` 文件对应的 SWE-agent 任务。
2.  **输出检查与跳过**: 在运行任务前，检查预期的 SWE-agent 输出目录 (`trajectories/<用户名>/<模型名>-<任务名>/`) 是否已存在。如果存在，则跳过该任务，避免重复运行。
3.  **任务后处理**:
    *   **Docker 清理**: 每个任务执行完毕后，停止并移除所有 Docker 容器（可通过 `SKIP_DOCKER_PRUNE` 禁用）。
    *   **等待**: 清理后等待指定秒数 (`SLEEP_DURATION`)。
    *   **Git 提交**: 将指定仓库 (`HOST_REPO_PATH`) 中的所有更改 `git add .` 并 `git commit`（可通过 `SKIP_GIT_COMMIT` 禁用）。提交信息包含任务名称，并使用 `--allow-empty --no-verify` 选项。
4.  **顺序执行**: 推荐使用单 worker (`NUM_WORKERS=1`) 以确保 Docker 清理和 Git 提交操作在每个任务后按预期、安全地执行。

## 环境要求

*   已安装并配置好 `sweagent`。
*   已安装并运行 Docker 服务。
*   Python 3.x。
*   目标 Git 仓库已克隆到本地。

## 配置

在运行之前，你需要仔细配置 `run_batch.sh` 和 `config/default.yaml` 文件。

### 1. 配置 `run_batch.sh`

打开 `code/agent_new/SWE-agent/run_batch.sh` 文件并修改以下变量：

*   `HOST_REPO_PATH`: **(极其重要)** 设置为你 **宿主机** 上目标 Git 仓库的 **绝对路径**。Git 操作将在此路径下执行。
    *   示例: `HOST_REPO_PATH="/path/to/your/local/repository"`
*   `PROMPT_DIR`: 包含 `.md` 问题描述文件的目录路径。
*   `PYTHON_SCRIPT`: 指向 `batch_sweagent_run.py` 的路径（通常保持默认即可）。
*   `MODEL_NAME`: 要使用的 SWE-agent 模型名称（例如，`claude-3-5-sonnet-20241022`）。
*   `DOCKER_IMAGE`: SWE-agent 使用的 Docker 镜像 ID 或标签（例如，`sweagent/swe-agent:latest` 或 `3eb72bc4a848`）。可以通过 `docker images | grep sweagent` 查看。
*   `REPO_PATH_IN_CONTAINER`: 目标仓库在 **Docker 容器内部** 的映射路径。**这必须与 `default.yaml` 中的卷映射目标路径一致**。
*   `CONFIG_FILE`: 指向 `sweagent` 配置文件的路径（例如，`config/default.yaml`）。
*   `OUTPUT_BASE_DIR`: `sweagent` 保存输出的基础目录，默认为 `trajectories`。用于检查是否跳过任务。
*   `USER_NAME`: `sweagent` 输出路径中使用的用户名，默认为 `batch_user`。用于检查是否跳过任务。
*   `NUM_WORKERS`: 并发运行的任务数。**强烈建议设置为 `1`** 以保证任务后处理（Docker清理、Git提交）的顺序性和安全性。
*   `SLEEP_DURATION`: 每个任务清理后等待的秒数。
*   `SKIP_DOCKER_PRUNE`: (可选) 设置为 `"true"` (小写) 可以跳过 Docker 容器的停止和移除步骤。
*   `SKIP_GIT_COMMIT`: (可选) 设置为 `"true"` (小写) 可以跳过 Git add 和 commit 步骤。
*   `LOG_LEVEL`: Python 脚本的日志级别 (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)。

### 2. 配置 `config/default.yaml`

打开 `code/agent_new/SWE-agent/config/default.yaml` 文件（或其他你指定的配置文件）。

**!!! 这是最关键的配置之一 !!!**

找到 `env.deployment.docker_args` 部分，这里定义了 Docker 容器的卷映射。你需要确保 **宿主机路径** 正确指向你的本地仓库。

```yaml
env:
  deployment:
    type: docker
    docker_args:
      - "-v"
      # !!! 修改这里的第一个路径 !!!
      # 将 "/data/data/agent_test_codebase/GitTaskBench" 替换为
      # 你本地机器上 Git 仓库的 **绝对路径**。
      # 第二个路径是容器内的路径，应与 run_batch.sh 中的 REPO_PATH_IN_CONTAINER 匹配。
      - "/path/to/your/local/repository:/path/inside/container"
      # 例如:
      # - "/home/user/my_project:/workspace"
      # - "/data/data/agent_test_codebase/GitTaskBench:/data/data/agent_test_codebase/GitTaskBench"
  # ... 其他配置 ...
```

**请务必将示例中的 `/path/to/your/local/repository` (或 `/data/data/agent_test_codebase/GitTaskBench`) 修改为你实际的宿主机仓库路径。** 容器内的路径 (`/path/inside/container` 或 `/data/data/agent_test_codebase/GitTaskBench`) 必须与 `run_batch.sh` 中设置的 `REPO_PATH_IN_CONTAINER` 变量值完全一致。

## 使用方法

1.  确保所有配置（`run_batch.sh` 和 `default.yaml`）已正确修改。
2.  给 `run_batch.sh` 添加执行权限（如果需要）：
    ```bash
    chmod +x code/agent_new/SWE-agent/run_batch.sh
    ```
3.  运行脚本：
    ```bash
    bash code/agent_new/SWE-agent/run_batch.sh
    ```

脚本将开始执行，你会看到类似以下的输出：

*   显示配置信息。
*   列出找到的 `.md` 文件总数。
*   如果某些任务的输出目录已存在，会提示跳过。
*   开始运行每个任务，显示 SWE-agent 的日志。
*   每个任务完成后，执行 Docker 清理、等待和 Git 提交（除非被禁用）。
*   最后输出批处理运行的摘要信息（成功/失败数量）。

## 注意事项

*   **Worker 数量**: 再次强调，将 `NUM_WORKERS` 设置为 `1` 是最安全的方式，可以避免并发执行 Docker 和 Git 操作带来的问题。
*   **Git 提交**: 提交会自动进行 (`git add .` 然后 `git commit`)。如果你不想自动提交，请在 `run_batch.sh` 中设置 `SKIP_GIT_COMMIT="true"`。提交使用了 `--allow-empty`（即使没有更改也会创建提交）和 `--no-verify`（跳过 pre-commit 钩子）。
*   **输出路径**: 跳过机制依赖于 SWE-agent 默认的输出路径结构 (`<OUTPUT_BASE_DIR>/<USER_NAME>/<MODEL_NAME>-<任务名>/`)。如果你的 `sweagent` 配置修改了这个结构，跳过机制可能无法正常工作。


## 🪪 License <a name="license"></a>
MIT. Check `LICENSE`.