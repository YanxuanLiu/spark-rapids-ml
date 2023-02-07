#
# Copyright (c) 2022, NVIDIA CORPORATION.
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
#
from typing import Any, Dict, Tuple

import numpy as np
import pytest

from spark_rapids_ml.regression import LinearRegression, LinearRegressionModel

from .sparksession import CleanSparkSession
from .utils import (
    array_equal,
    assert_params,
    create_pyspark_dataframe,
    cuml_supported_data_types,
    feature_types,
    idfn,
    make_regression_dataset,
    pyspark_supported_feature_types,
)


# @lru_cache(4) TODO fixme: TypeError: Unhashable Type” Numpy.Ndarray
def train_with_cuml_linear_regression(
    X: np.ndarray,
    y: np.ndarray,
    alpha: float,
    l1_ratio: float,
    other_params: Dict[str, Any] = {},
) -> Any:
    if alpha == 0:
        from cuml import LinearRegression as cuLinearRegression

        lr = cuLinearRegression(output_type="numpy")
    else:
        if l1_ratio == 0.0:
            from cuml import Ridge

            lr = Ridge(output_type="numpy", alpha=alpha)
        elif l1_ratio == 1.0:
            from cuml import Lasso

            lr = Lasso(output_type="numpy", alpha=alpha)
        else:
            from cuml import ElasticNet

            lr = ElasticNet(
                output_type="numpy", alpha=alpha, l1_ratio=l1_ratio, **other_params
            )

    lr.fit(X, y)
    return lr


@pytest.mark.parametrize("reg", [0.0, 0.7])
def test_linear_regression_params(tmp_path: str, reg: float) -> None:
    # Default params
    default_spark_params = {
        "elasticNetParam": 0.0,
        "fitIntercept": True,
        "loss": "squaredError",
        "maxIter": 100,
        "regParam": 0.0,
        "solver": "auto",
        "standardization": True,
        "tol": 1e-06,
    }
    default_cuml_params = {
        "algorithm": "eig",
        "alpha": 0.0,
        "fit_intercept": True,
        "l1_ratio": 0.0,
        "max_iter": 100,
        "normalize": True,
        "solver": "eig",
    }
    default_lr = LinearRegression()
    assert_params(default_lr, default_spark_params, default_cuml_params)

    # Spark ML Params
    spark_params = {
        "fitIntercept": False,
        "standardization": False,
        "regParam": reg,
        "solver": "normal",
    }
    spark_lr = LinearRegression(**spark_params)
    expected_spark_params = default_spark_params.copy()
    expected_spark_params.update(spark_params)
    expected_cuml_params = default_cuml_params.copy()
    expected_cuml_params.update(
        {
            "alpha": reg,
            "fit_intercept": False,
            "normalize": False,
            "solver": "eig",
        }
    )
    assert_params(spark_lr, expected_spark_params, expected_cuml_params)

    # Estimator persistence
    path = tmp_path + "/linear_regression_tests"
    estimator_path = f"{path}/linear_regression"
    spark_lr.write().overwrite().save(estimator_path)
    loaded_lr = LinearRegression.load(estimator_path)
    assert_params(loaded_lr, expected_spark_params, expected_cuml_params)

    # Unsupported value
    spark_params = {"solver": "l-bfgs"}
    with pytest.raises(
        ValueError, match="Value 'l-bfgs' for 'solver' param is unsupported"
    ):
        unsupported_lr = LinearRegression(**spark_params)


@pytest.mark.parametrize("data_type", ["byte", "short", "int", "long"])
def test_linear_regression_numeric_type(gpu_number: int, data_type: str) -> None:
    data = [
        [1, 4, 4, 4, 0],
        [2, 2, 2, 2, 1],
        [3, 3, 3, 2, 2],
        [3, 3, 3, 2, 3],
        [5, 2, 1, 3, 4],
    ]

    with CleanSparkSession() as spark:
        feature_cols = ["c1", "c2", "c3", "c4"]
        schema = (
            ", ".join([f"{c} {data_type}" for c in feature_cols])
            + f", label {data_type}"
        )
        df = spark.createDataFrame(data, schema=schema)
        lr = LinearRegression(num_workers=gpu_number)
        lr.setFeaturesCol(feature_cols)
        lr.fit(df)


@pytest.mark.parametrize("feature_type", pyspark_supported_feature_types)
@pytest.mark.parametrize("data_type", cuml_supported_data_types)
@pytest.mark.parametrize("data_shape", [(10, 2)], ids=idfn)
@pytest.mark.parametrize("reg", [0.0, 0.7])
def test_linear_regression_basic(
    tmp_path: str,
    feature_type: str,
    data_type: np.dtype,
    data_shape: Tuple[int, int],
    reg: float,
) -> None:
    # Train a toy model
    X, _, y, _ = make_regression_dataset(data_type, data_shape[0], data_shape[1])
    with CleanSparkSession() as spark:
        df, features_col, label_col = create_pyspark_dataframe(
            spark, feature_type, data_type, X, y
        )

        lr = LinearRegression()
        lr.setRegParam(reg)

        lr.setFeaturesCol(features_col)
        assert lr.getFeaturesCol() == features_col

        assert label_col is not None
        lr.setLabelCol(label_col)
        assert lr.getLabelCol() == label_col

        def assert_model(
            lhs: LinearRegressionModel, rhs: LinearRegressionModel
        ) -> None:
            assert lhs.coef_ == rhs.coef_
            assert lhs.intercept_ == lhs.intercept_

            # Vector type will be cast to array(double)
            if feature_type == "vector":
                assert lhs.dtype == np.dtype(np.float64).name
            else:
                assert lhs.dtype == np.dtype(data_type).name

            assert lhs.dtype == rhs.dtype
            assert lhs.n_cols == rhs.n_cols
            assert lhs.n_cols == data_shape[1]

        # train a model
        lr_model = lr.fit(df)

        # model persistence
        path = tmp_path + "/linear_regression_tests"
        model_path = f"{path}/linear_regression_model"
        lr_model.write().overwrite().save(model_path)

        lr_model_loaded = LinearRegressionModel.load(model_path)
        assert_model(lr_model, lr_model_loaded)


@pytest.mark.parametrize("feature_type", pyspark_supported_feature_types)
@pytest.mark.parametrize("data_shape", [(1000, 20)], ids=idfn)
@pytest.mark.parametrize("data_type", cuml_supported_data_types)
@pytest.mark.parametrize("max_record_batch", [100, 10000])
@pytest.mark.parametrize("alpha", [0.0, 0.7])  # equal to reg parameter
@pytest.mark.parametrize(
    "l1_ratio_and_other_params",
    [
        (0.0, {}),  # LinearRegression
        (0.5, {"tol": 1e-5}),  # ElasticNet
        (1.0, {"tol": 1e-5}),  # Lasso
    ],
)
@pytest.mark.slow
def test_linear_regression(
    gpu_number: int,
    feature_type: str,
    data_shape: Tuple[int, int],
    data_type: np.dtype,
    max_record_batch: int,
    alpha: float,
    l1_ratio_and_other_params: Tuple[float, Dict[str, Any]],
) -> None:
    X_train, X_test, y_train, _ = make_regression_dataset(
        data_type, data_shape[0], data_shape[1]
    )

    l1_ratio, other_params = l1_ratio_and_other_params
    cu_lr = train_with_cuml_linear_regression(
        X_train, y_train, alpha, l1_ratio, other_params
    )
    cu_expected = cu_lr.predict(X_test)

    conf = {"spark.sql.execution.arrow.maxRecordsPerBatch": str(max_record_batch)}
    with CleanSparkSession(conf) as spark:
        train_df, features_col, label_col = create_pyspark_dataframe(
            spark, feature_type, data_type, X_train, y_train
        )
        assert label_col is not None

        slr = LinearRegression(num_workers=gpu_number, verbose=7, **other_params)
        slr.setRegParam(alpha)
        slr.setStandardization(
            False
        )  # Spark default is True, but Cuml default is False
        slr.setElasticNetParam(l1_ratio)
        slr.setFeaturesCol(features_col)
        slr.setLabelCol(label_col)
        slr_model = slr.fit(train_df)

        assert array_equal(cu_lr.coef_, slr_model.coef_, 1e-3)

        test_df, _, _ = create_pyspark_dataframe(spark, feature_type, data_type, X_test)

        result = slr_model.transform(test_df).collect()
        pred_result = [row.prediction for row in result]
        assert array_equal(cu_expected, pred_result, 1e-3)
