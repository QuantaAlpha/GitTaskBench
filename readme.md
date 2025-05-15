# GitTaskBench


## Install

```console
cd gittaskbench
pip install -e .
```


## Quick Start
```console
gittaskbench grade --taskid <taskid> [--output_dir <output_dir>] [-v]
```
## Options:

*  #### --taskid <taskid>: (Required) The task identifier, e.g., Trafilatura_01.

*  #### --output_dir <output_dir>: (Optional) The directory containing the agent's output files. If not specified, the default value is read from task_info.yaml.
*  #### -v: (Optional) Enable verbose output to display detailed error messages.

## Example:
```console
gittaskbench grade --taskid Trafilatura_01
```
