from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def summarize_orders_by_region(orders_df: DataFrame) -> DataFrame:
    """Aggregates total order amount per region.

    Args:
        orders_df: DataFrame with columns `region` (string) and `amount` (double).

    Returns:
        DataFrame with columns `region` and `total_amount`.
    """
    return orders_df.groupBy("region").agg(F.sum("amount").alias("total_amount"))
