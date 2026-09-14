from databricks_local_ci.subprocess_runner import run_entrypoint


def test_orders_summary_real_run_writes_expected_summary(local_spark_session, tmp_path):
    input_path = str(tmp_path / "orders")
    output_path = str(tmp_path / "summary")

    orders_df = local_spark_session.createDataFrame(
        [("us-east", 100.0), ("us-east", 50.0), ("eu-west", 200.0)],
        ["region", "amount"],
    )
    orders_df.write.format("delta").mode("overwrite").save(input_path)

    result = run_entrypoint(
        "orders_summary.main",
        args=["--input-path", input_path, "--output-path", output_path],
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert "Wrote summary to" in result.stdout, result.stdout

    summary_df = local_spark_session.read.format("delta").load(output_path)
    rows = {row["region"]: row["total_amount"] for row in summary_df.collect()}
    assert rows == {"us-east": 150.0, "eu-west": 200.0}
