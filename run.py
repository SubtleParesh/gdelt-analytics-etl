from prefect.deployments import Deployment, run_deployment


if __name__ == "__main__":
    run_deployment(
        name="GDELT ELT Main Pipeline/master_flow_gdelt",
        parameters= {
            "master_csv_list_url":"http://data.gdeltproject.org/gdeltv2/masterfilelist.txt",
            "min_date": "25/04/2023",
            "clean_start": True
        }
    )