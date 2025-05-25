# GitTaskBench


## Setup
You can install `gittaskbench` with pip:
```console
cd gittaskbench
pip install -e .
```
also you can
```console
pip install -r requirements.txt
```

## Quick Start
```console
gittaskbench [-v] grade --taskid <taskid> [--output_dir <output_dir>] [--result <result>]
```
### Options:

- --taskid <taskid>: (Required) The task identifier, e.g., Trafilatura_01.
- -v: (Optional) Enable verbose output to display detailed error messages.
- --output_dir : (Optional) The directory containing the agent's output files. If not specified, the default value is read from task_info.yaml.
- --result :(Optional) The directory containing the agent's test results files. If not specified, the default value is read from task_info.yaml.
## Example:
```console
gittaskbench grade --taskid Trafilatura_01
```
