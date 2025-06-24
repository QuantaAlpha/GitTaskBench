#!/bin/bash
###### 
# 用于批量生成prompt，基于queries里面各个仓库的input、query.json配置信息

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
EVAL_AUTOMATION_DIR="$(dirname "$SCRIPT_DIR")"
WORKSPACE_DIR="$(dirname "$EVAL_AUTOMATION_DIR")"

# Default paths relative to the script's location (assuming standard project structure)
# Adjust these defaults if your structure differs
### 更改
GIT_ROOT_DIR="$WORKSPACE_DIR"  
DEFAULT_QUERIES_DIR="$EVAL_AUTOMATION_DIR/queries"  
DEFAULT_WORKING_DIR="$EVAL_AUTOMATION_DIR/prompt"
# 然后可以把选中的任务prompt、继续调整的prompt移到final_prompt文件夹中来


# Initialize variables with default values
QUERIES_DIR="${DEFAULT_QUERIES_DIR}"
WORKING_DIR="${DEFAULT_WORKING_DIR}"



# Parse command-line arguments (optional)
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --queries-dir)
            QUERIES_DIR="$2"
            shift # past argument
            shift # past value
            ;;
        --working-dir)
            WORKING_DIR="$2"
            shift # past argument
            shift # past value
            ;;
        -*|--*)
            echo "Unknown option $1" >&2
            exit 1
            ;;
        *)
            # Ignore positional arguments or handle them if needed
            shift # past argument
            ;;
    esac
done

# Construct the path to the Python script
PYTHON_SCRIPT="${SCRIPT_DIR}/new_run_setup.py"

# Check if the Python script exists
if [ ! -f "${PYTHON_SCRIPT}" ]; then
    echo "Error: Python script not found at ${PYTHON_SCRIPT}" >&2
    exit 1
fi

# Execute the Python script with the determined arguments
echo "Running new_run_setup.py..."
echo "  Queries Dir: ${QUERIES_DIR}"
echo "  Working Dir: ${WORKING_DIR}"

python3 "${PYTHON_SCRIPT}" \
    --queries-dir "${QUERIES_DIR}" \
    --working-dir "${WORKING_DIR}" \
    --git-root-dir "${GIT_ROOT_DIR}"

# Check the exit status of the Python script
if [ $? -eq 0 ]; then
    echo "Script executed successfully."
else
    echo "Script execution failed." >&2
    exit 1
fi

exit 0
