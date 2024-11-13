#! /bin/bash -e
file_patterns="*.md,  *.py,*.sh"

CURRENT_YEAR=$(date +%Y)
LICENSE_PATTERN="Copyright \(c\) .*?${CURRENT_YEAR}, NVIDIA CORPORATION."

FILES=$(ls ci)
echo "$FILES"
IFS="," read -r -a FILE_PATTERN_ARRAY <<< $file_patterns
echo "${FILE_PATTERN_ARRAY[*]}"

PATTERNS=""
for PATTERN in "${FILE_PATTERN_ARRAY[@]}"; do
    PATTERNS+="$(echo "$PATTERN" | xargs -I{} echo "{}")|"
done
PATTERNS=${PATTERNS%|}
echo "$PATTERNS"

FILES=$(echo "$FILES" | grep -E "$PATTERNS")
echo "++++++++"
echo "$FILES"

NO_LICENSE_FILES=()
for FILE in $FILES; do
    echo "Checking $FILE"
    if !(grep -E "$LICENSE_PATTERN" "ci/$FILE"); then
        NO_LICENSE_FILES+=($FILE)
    fi
done

if [ ! -z "${NO_LICENSE_FILES[@]}" ]; then
    echo "Following files missed copyright/license header: ${NO_LICENSE_FILES[*]}"
    exit 1
fi
