from prefect.schedules import Cron
from orchestration.pipeline_etl import pipeline_etl

if __name__ == "__main__":
    pipeline_etl.serve(
        name="deployment-from-vm",
        schedule=Cron(
            "0 8 * * 1",
            timezone="Europe/Paris",
        ),
        limit=1,
        global_limit=1,
    )