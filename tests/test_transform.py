from orders_summary.transform import summarize_orders_by_region


def test_summarize_orders_by_region(local_spark_session):
    orders_df = local_spark_session.createDataFrame(
        [("us-east", 100.0), ("us-east", 50.0), ("eu-west", 200.0)],
        ["region", "amount"],
    )

    result = summarize_orders_by_region(orders_df).orderBy("region")

    rows = {row["region"]: row["total_amount"] for row in result.collect()}
    assert rows == {"us-east": 150.0, "eu-west": 200.0}
