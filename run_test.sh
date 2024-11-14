#! /bin/bash -e
file_patterns="*.py, *.sh  , *.cpp,  Dockerfile*"

CURRENT_YEAR=$(date +%Y)
# LICENSE_PATTERN="Copyright \(c\) .*?${CURRENT_YEAR}, NVIDIA CORPORATION."
LICENSE_PATTERN="Copyright \(c\) .*, NVIDIA CORPORATION."

# FILES="docker/Dockerfile.pip python/src/spark_rapids_ml/regression.py docker/Dockerfile python/pyproject.toml python/run_test.sh"
FILES=$(find . -type f)

# echo "$FILES"

IFS="," read -r -a PATTERNS <<< "$(echo "$file_patterns" | tr -d ' ')"
# echo "${PATTERNS[*]}"


# echo "============="

NO_LICENSE_FILES=""
for FILE in $FILES; do
    # for PATTERN in "${PATTERNS[@]}"; do
        # if [[ $(basename $FILE) == $PATTERN ]]; then
            # echo "Checking $FILE"
            if !(grep -Eq "$LICENSE_PATTERN" "$FILE"); then
                NO_LICENSE_FILES+="$FILE "
            fi
            # break
        # fi
    # done
done

if [ ! -z "$NO_LICENSE_FILES" ]; then
    echo "Following files missed copyright/license header: "
    echo $NO_LICENSE_FILES | tr ' ' '\n'
    exit 1
fi
