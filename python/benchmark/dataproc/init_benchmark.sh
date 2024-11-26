#!/bin/bash
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


set -euxo pipefail

function get_metadata_attribute() {
  local -r attribute_name=$1
  local -r default_value=$2
  /usr/share/google/get_metadata_value "attributes/${attribute_name}" || echo -n "${default_value}"
}

RAPIDS_VERSION=$(get_metadata_attribute rapids-version 24.10.0)

# patch existing packages
mamba install "llvmlite<0.40,>=0.39.0dev0" "numba>=0.56.2"

# install cudf and cuml
# using ~= pulls in lates micro version patches
pip install --upgrade pip

# dataproc 2.1 pyarrow and arrow conda installation is not compatible with cudf
mamba uninstall -y pyarrow arrow

pip install cudf-cu11~=${RAPIDS_VERSION} cuml-cu11~=${RAPIDS_VERSION} cuvs-cu11~=${RAPIDS_VERSION} \
    pylibraft-cu11~=${RAPIDS_VERSION} \
    rmm-cu11~=${RAPIDS_VERSION} \
    --extra-index-url=https://pypi.nvidia.com

# install benchmark files
BENCHMARK_HOME=$(get_metadata_attribute benchmark-home UNSET)
if [[ ${BENCHMARK_HOME} == "UNSET" ]]; then
    echo "Please set --metadata benchmark-home"
    exit 1
fi

gsutil cp gs://${BENCHMARK_HOME}/benchmark_runner.py .
gsutil cp gs://${BENCHMARK_HOME}/spark_rapids_ml.zip .
gsutil cp gs://${BENCHMARK_HOME}/benchmark.zip .

python_ver=`python --version | grep -oP '3\.[0-9]+'`
unzip spark_rapids_ml.zip -d /opt/conda/miniconda3/lib/python${python_ver}/site-packages
unzip benchmark.zip -d /opt/conda/miniconda3/lib/python${python_ver}/site-packages
