# GitTaskBench


## Install

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
gittaskbench [-v] grade --taskid <taskid> [--output_dir <output_dir>] 
```
## Options:

*  #### --taskid <taskid>: (Required) The task identifier, e.g., Trafilatura_01.

*  #### --output_dir <output_dir>: (Optional) The directory containing the agent's output files. If not specified, the default value is read from task_info.yaml.
*  #### -v: (Optional) Enable verbose output to display detailed error messages.

## Example:
```console
gittaskbench grade --taskid Trafilatura_01
```
