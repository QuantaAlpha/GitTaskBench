
## 任务描述
根据仓库内容，实现在给定输入的PNG图像中嵌入盲水印<invisible>?

## 可用仓库
仓库名称: InvisibleWatermark
仓库路径 (绝对): /data/data/agent_test_codebase/GitTaskBench/code_base/InvisibleWatermark
理解指南: ['阅读README.md了解项目基本功能和使用方法']

## 文件路径
输入：
文件路径 (绝对): /data/data/agent_test_codebase/GitTaskBench/queries/InvisibleWatermark_01/input/InvisibleWatermark_01_input.png
文件描述: 要嵌入盲水印的输入png图像

输出：
输出文件目录:/data/data/agent_test_codebase/GitTaskBench/eval_automation/output/InvisibleWatermark_01, 如果只有一个文件，就以 `output` 命名; 如果存在多个以 `output_01`开始命名，格式根据需求指定。

## 补充说明
**核心目标**: 快速理解和分析代码仓库，生成并执行必要的代码或调用工具，以高效、准确地完成用户指定的任务。

## 工作流程与规范

1.  **理解任务**: 仔细分析用户提供的任务描述 (`<task>`)、工作目录 (`<work_dir>`)、仓库信息 (`<repo>`) 和代码重要性提示 (`<code_importance>`)。
2.  **规划方案**: 
    *   如果没有现成计划，先制定清晰的执行步骤。请先阅读代码库的README.md文件，了解代码库的结构和使用方法。
    *   如果没有README.md文件或者README.md文件中没有提供足够信息，请先阅读代码库的代码，了解代码库的结构和使用方法。
    *   明确哪些步骤需要编写代码，哪些步骤依赖语言理解和工具调用。
    *   代码生成和执行过程中，涉及到路径的请使用绝对路径，不要使用相对路径，以免出现路径错误。
3.  **代码库分析**: 
    *   **探索结构**: 快速了解仓库的整体文件和目录结构, 请使用绝对路径。
    *   **识别关键文件**: 优先关注 `README.md`, 配置文件, 主入口脚本等。
    *   **依赖管理**: 
        *   检查 `requirements.txt` 或类似文件，确定所需依赖。
        *   **如果需要安装依赖**：在代码块中包含安装命令 (e.g., `pip install -r requirements.txt` 或 `pip install specific_package`)。检查包是否存在避免重复安装。
        *   **不要使用conda install，请使用pip install**。
        *   **环境配置**: Python/Conda环境已预设，无需额外配置。但需确保代码库路径在`PYTHONPATH`中，**必要时生成** `export PYTHONPATH=\"$PYTHONPATH:{remote_repo_path}\"` 命令。
4. 代码实现和执行
    * 提供详细的代码及实现步骤，包含完整的函数/类定义、参数和返回值,提供必要的注释和文档字符串
    * 如果需要依赖一些checkpoint模型文件，请先检查是否存在，如果存在，则直接使用，否则先下载checkpoint文件，再使用(需要自动下载)
        * 比如需要下载checkpoint文件，请使用`wget`命令下载，如果需要下载多个文件，请使用`wget -O`命令下载。

5.  **错误处理与迭代**: 
    *   检查代码执行结果。
    *   如果出现错误，分析原因，**修复代码**并重新生成**完整**脚本进行尝试。
    *   如果多次尝试后仍无法解决或任务无法完成，分析原因并考虑替代方案。
6.  **工具优先**: 
    *   **如果需要依赖一些checkpoint模型文件，请先检查是否存在，如果存在，则直接使用，否则先下载checkpoint文件，再使用(需要自动下载)
7.  **任务完成**: 
    *   当任务成功完成，或确认无法完成时，提供清晰的总结。

## !! 关键约束与强制要求 !!

*   **绝对路径**: 在代码中处理文件（特别是数据加载）时，**必须**使用**绝对路径**。
*   **提供的仓库 > 代码**: 现有仓库代码能完成的任务，**严禁**自行重新编写代码实现。
*   **请先阅读代码库的README.md文件，了解代码库的结构和使用方法**。如果没有README.md文件或者README.md文件中没有提供足够信息，请先阅读代码库的代码，了解代码库的结构和使用方法。
