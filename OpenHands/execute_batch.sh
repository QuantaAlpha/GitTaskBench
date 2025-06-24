#!/bin/bash

# Shell script to execute the run_batch.py script for OpenHands

# Navigate to the script's directory (which should be the OpenHands project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR" || exit 1

echo "Current directory: $(pwd)"
echo "Executing OpenHands batch script..."

# Execute the Python script using poetry, passing all arguments passed to this shell script
poetry run python run_batch.py "$@"

# Check the exit code of the python script
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "Batch script completed successfully."
else
    echo "Batch script finished with errors (Exit Code: $EXIT_CODE). Check logs in the output directory."
fi

exit $EXIT_CODE 