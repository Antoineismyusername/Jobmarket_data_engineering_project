import os
from pathlib import Path

from prefect import flow, task


@task(name="Clean directories data/raw and data/processed", cache_policy=None, retries=0)
def clean_data_dirs():
    from clean_data_dirs import main

    main()

@task(name="Extract France Travail", cache_policy=None, retries=0)
def extract_france_travail():
    from scripts.offers.extract.extraction_france_travail import main

    main()


@task(name="Extract Adzuna", cache_policy=None, retries=1)
def extract_adzuna():
    from scripts.offers.extract.extraction_adzuna import main

    main()


@task(name="Normalize France Travail", cache_policy=None, retries=1)
def normalize_france_travail():
    from scripts.offers.normalize.normalize_france_travail import main

    main()


@task(name="Normalize Adzuna", cache_policy=None, retries=0)
def normalize_adzuna():
    from scripts.offers.normalize.normalize_adzuna import main

    main()


@task(name="Charge MongoDB", cache_policy=None, retries=0)
def charge_mongodb():
    from scripts.offers.load.load_mongodb import main

    main()

@flow(name="JobMarket - pipeline ETL", log_prints=True, retries=0)
def pipeline_etl():
    #clean_data_dirs()
    
    extraction_ft = extract_france_travail.submit()
    extraction_adzuna = extract_adzuna.submit()

    normalization_ft = normalize_france_travail.submit(wait_for=[extraction_ft])
    normalization_adzuna = normalize_adzuna.submit(wait_for=[extraction_adzuna])

    loading = charge_mongodb.submit(wait_for=[normalization_ft, normalization_adzuna])
    loading.result()


if __name__ == "__main__":
    pipeline_etl()