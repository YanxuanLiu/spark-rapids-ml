#! /bin/bash -e

# Copyright (c) 2024, NVIDIA CORPORATION.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

file_patterns="*.cpp, \
            *.java, \
            *.scala, \
            *.py, \
            *.sh, \
            */Dockerfile*, \
            */Jenkinsfile*, \
            *.yml, \
            *.cu, \
            *.hpp, \
            *.cmake"

exclude_patterns="*/src/*, */target/*"

CURRENT_YEAR=$(date +%Y)
LICENSE_PATTERN="Copyright \(c\) .*?${CURRENT_YEAR}, NVIDIA CORPORATION."
# LICENSE_PATTERN="Copyright \(c\) .*, NVIDIA CORPORATION."

FILES=(docker/Dockerfile.pip python/src/spark_rapids_ml/regression.py docker/Dockerfile python/pyproject.toml python/run_test.sh python/src/spark_rapids_ml/clustering.py)
# FILES=($(find . -type f | sed 's|^\./||'))
# FILES=$(git diff --name-only --diff-filter=AM 5a24d77f836e592cfa539efa3a065919659b1805 858c6334c43134c685dffb4fba112ad4d1c948f0)
# RENAME_FILES=$(git diff --name-status 5a24d77f836e592cfa539efa3a065919659b1805 858c6334c43134c685dffb4fba112ad4d1c948f0 | grep "^R" | grep -v "R100" | awk '{print $3}')
# FILES=($FILES $RENAME_FILES)
echo "${FILES[@]}"

IFS="," read -r -a INCLUDE_PATTERNS <<< "$(echo "$file_patterns" | tr -d ' ' | tr -d '\n' )"
echo "${INCLUDE_PATTERNS[*]}"
IFS="," read -r -a EXCLUDE_PATTERNS <<< "$(echo "$exclude_patterns" | tr -d ' ' | tr -d '\n' )"
echo "${EXCLUDE_PATTERNS[*]}"

# Check license header
NO_LICENSE_FILES=""
for FILE in "${FILES[@]}"; do
    INCLUDE=false
    for INCLUDE_PATTERN in "${INCLUDE_PATTERNS[@]}"; do
        if [[ $FILE == $INCLUDE_PATTERN ]]; then
            INCLUDE=true
            break
        fi
    done
    EXCLUDE=false
    for EXCLUDE_PATTERN in "${EXCLUDE_PATTERNS[@]}"; do
        if [[ $FILE == $EXCLUDE_PATTERN ]]; then
            EXCLUDE=true
            break
        fi
    done

    if [[ $INCLUDE == true && $EXCLUDE == false ]]; then
        echo "Checking $FILE"
        if !(grep -Eq "$LICENSE_PATTERN" "$FILE"); then
            NO_LICENSE_FILES+="$FILE "
        fi
    fi
done

# Output result
echo "--------- RESULT ---------"
if [ ! -z "$NO_LICENSE_FILES" ]; then
    echo "Following files missed copyright/license header or expired: "
    echo $NO_LICENSE_FILES | tr ' ' '\n'
    exit 1
else
    echo "All files passed the check"
    exit 0
fi
