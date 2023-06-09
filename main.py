from datetime import datetime

import pandas as pd
from hydra import compose
from prefect import flow, get_run_logger, task

import workflows.common as common
from workflows.common import Configuration, Table
from workflows.data_lake_flows import (
    create_bucket,
    extract_events,
    extract_mentions,
    subflow_extract_load_cameo_tables,
    subflow_to_load_csv_to_datalake,
    transform_events,
    transform_mentions,
)
from workflows.datawarehouse_flows import subflow_datawarehouse
from workflows.dbt_flow import trigger_dbt_flow


@task(log_prints=False, tags=["load"], retries=3)
def retrive_file_urls_from_csv(list_file_url) -> pd.DataFrame:
    df = pd.read_csv(
        list_file_url,
        delimiter=" ",
        dtype={"FileUrl": "string"},
        names=["Size", "Id", "FileUrl"],
    )
    df["DateTimeTemporary"] = df["FileUrl"].str.extract(r"(\d{14})")
    df["DateTime"] = pd.to_datetime(df["DateTimeTemporary"], format="%Y%m%d%H%M%S")
    df["Date"] = df["DateTime"].dt.date
    df["Size"] = pd.to_numeric(df["Size"], errors="coerce").fillna(0)
    df = df.drop("DateTimeTemporary", axis=1)
    return df


def log_master_list_info(
    master_list_export, master_list_mentions, master_list_gkg, logger
):
    megabytes_base = 1024 * 1024

    master_list_export_sum = master_list_export.Size.sum()
    master_list_mentions_sum = master_list_mentions.Size.sum()
    master_list_gkg_sum = master_list_gkg.Size.sum()

    export_size_mb = master_list_export_sum / megabytes_base
    mentions_size_mb = master_list_mentions_sum / megabytes_base
    gkg_size_mb = master_list_gkg_sum / megabytes_base

    logger.info(f"Total size of export data in MB: {export_size_mb}")
    logger.info(f"Total size of mentions data in MB: {mentions_size_mb}")
    logger.info(f"Total size of GKG data in MB: {gkg_size_mb}")

    print(
        f"Export Number of Rows {str(master_list_export.shape[0])}, Size of all data in rows {str(export_size_mb)}"
    )
    print(
        f"Mentions - Number of Rows {str(master_list_mentions.shape[0])}, Size of all data in rows {str(mentions_size_mb)}"
    )
    print(
        f"GKG - Number of Rows {str(master_list_gkg.shape[0])}, Size of all data in rows {str(gkg_size_mb)}"
    )


@flow(name="GDELT ELT Main Pipeline", log_prints=True)
def main_flow(
    master_csv_list_url,
    min_date: str,
    config_file="config.server.yaml",
    clean_start=False,
    max_datetime=None,
):
    global config
    cfg = compose(config_name=config_file)
    config = Configuration(**cfg.config)
    common.config = config
    print(dict(config.dask))
    min_datetime = datetime.strptime(min_date, "%d/%m/%Y")
    master_list = retrive_file_urls_from_csv(master_csv_list_url)
    master_list = master_list[master_list["DateTime"].dt.date >= min_datetime.date()]
    if max_datetime is not None:
        master_list = master_list[master_list["DateTime"].dt.date < max_datetime.date()]

    master_list_events = master_list[master_list["FileUrl"].str.contains("export")]
    master_list_mentions = master_list[master_list["FileUrl"].str.contains("mentions")]
    master_list_gkg = master_list[master_list["FileUrl"].str.contains("gkg")]

    logger = get_run_logger()
    log_master_list_info(
        master_list_events, master_list_mentions, master_list_gkg, logger
    )
    create_bucket(config)

    subflow_extract_load_cameo_tables(config)
    subflow_to_load_csv_to_datalake(
        config, master_list_events, extract_events, transform_events, Table.events
    )
    subflow_to_load_csv_to_datalake(
        config,
        master_list_mentions,
        extract_mentions,
        transform_mentions,
        Table.mentions,
    )
    subflow_datawarehouse(config, clean_start)
    trigger_dbt_flow(config)


if __name__ == "__main__":
    master_csv_list_url = "http://data.gdeltproject.org/gdeltv2/masterfilelist.txt"
    last_15mins_csv_list_url = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

    # Change this value based upon your bandwidth and time.
    # Prefer first run of year 2023 which should take around 15mins to 30mins based upon you bandwidth
    min_date = "1/3/2023"
    config_file = "config.local.yaml"

    main_flow(
        master_csv_list_url=master_csv_list_url,
        min_date=min_date,
        max_datetime=datetime(2023, 7, 1),
        config_file=config_file,
        clean_start=True,
    )
