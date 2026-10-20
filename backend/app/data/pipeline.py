"""Complete Data Pipeline Orchestrator for Crop Yield Prediction.

Executes data acquisition, normalization, weather aggregation, soil profiling,
multimodal alignment, data validation, and report generation.

CLI Usage:
    python -m app.data.pipeline --help
    python -m app.data.pipeline --stage all
"""

import sys
import argparse
import logging
from app.data.config import data_config
from app.data.districts import MAHARASHTRA_DISTRICTS
from app.data.yield_ingestion import YieldIngestionService
from app.data.weather_ingestion import WeatherIngestionService
from app.data.soil_ingestion import SoilIngestionService
from app.data.alignment import DatasetAlignmentService
from app.data.validation import DataValidationService
from app.data.quality_report import QualityReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("DataPipeline")


def run_pipeline(
    crop: str = "Soybean",
    season: str = "Kharif",
    start_year: int = 1990,
    end_year: int = 2017,
    force_download: bool = False,
    stage: str = "all",
) -> int:
    """Execute the configured data acquisition and preprocessing stages."""
    logger.info(f"=== Starting Agricultural Data Pipeline for {crop} ({season}) ===")
    logger.info(f"Target Year Range: {start_year} – {end_year}")

    yield_svc = YieldIngestionService(data_config)
    weather_svc = WeatherIngestionService(data_config)
    soil_svc = SoilIngestionService(data_config)
    alignment_svc = DatasetAlignmentService(data_config)
    validation_svc = DataValidationService()
    report_gen = QualityReportGenerator(data_config)

    # 1. Historical Crop Yield Ingestion
    logger.info("Step 1: Ingesting and normalizing historical crop statistics...")
    raw_crop_file = yield_svc.fetch_raw_data(force_download=force_download)
    df_yield, yield_meta = yield_svc.process_records(
        raw_file_path=raw_crop_file,
        crop=crop,
        season=season,
        min_year=start_year,
        max_year=end_year,
    )
    logger.info(
        f"Yield Ingestion Complete: {len(df_yield)} valid records across {df_yield['district'].nunique()} districts."
    )

    if stage == "yield":
        logger.info("Stage 'yield' completed successfully.")
        return 0

    districts_to_process = sorted(df_yield["district"].unique().tolist())
    logger.info(f"Districts with active crop records ({len(districts_to_process)}): {districts_to_process}")

    # 2. NASA POWER Weather Ingestion
    logger.info("Step 2: Ingesting and aggregating NASA POWER daily agroclimatology...")
    df_weather, weather_meta = weather_svc.process_all_districts(
        districts=districts_to_process,
        start_year=start_year,
        end_year=end_year,
        force_download=force_download,
    )
    logger.info(
        f"Weather Ingestion Complete: {len(df_weather)} seasonal records across {weather_meta['successful_districts']} districts."
    )

    if stage == "weather":
        logger.info("Stage 'weather' completed successfully.")
        return 0

    # 3. ISRIC SoilGrids Ingestion
    logger.info("Step 3: Ingesting and building ISRIC SoilGrids 2.0 topsoil profiles...")
    df_soil, soil_meta = soil_svc.process_all_districts(
        districts=districts_to_process,
        force_download=force_download,
    )
    logger.info(
        f"Soil Profiling Complete: {len(df_soil)} profiles across {soil_meta['successful_profiles']} districts."
    )

    if stage == "soil":
        logger.info("Stage 'soil' completed successfully.")
        return 0

    # 4. Multimodal Dataset Alignment
    logger.info("Step 4: Aligning yield, weather, and soil datasets...")
    df_final, alignment_meta = alignment_svc.align_datasets(
        df_yield=df_yield,
        df_weather=df_weather,
        df_soil=df_soil,
    )
    logger.info(
        f"Alignment Complete: {len(df_final)} aligned records written to {alignment_meta['output_path']}."
    )

    # 5. Validation and Audit
    logger.info("Step 5: Executing data validation and schema integrity checks...")
    validation_results = validation_svc.validate_dataset(df_final)
    if validation_results["is_valid"]:
        logger.info("Data Validation Passed: 0 fatal issues found.")
    else:
        logger.warning(f"Data Validation Issues: {validation_results['issues']}")

    # 6. Quality Report Generation
    logger.info("Step 6: Generating data quality and governance reports...")
    report_info = report_gen.generate_report(
        yield_meta=yield_meta,
        weather_meta=weather_meta,
        soil_meta=soil_meta,
        alignment_meta=alignment_meta,
        validation_results=validation_results,
    )
    logger.info(f"Report Generated: Markdown at {report_info['markdown_report_path']}")
    logger.info(f"Report Generated: JSON at {report_info['json_report_path']}")

    logger.info("=== Agricultural Data Pipeline Completed Successfully! ===")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Maharashtra Agricultural Crop Yield Data Pipeline"
    )
    parser.add_argument(
        "--crop",
        type=str,
        default="Soybean",
        help="Target crop name (default: Soybean)",
    )
    parser.add_argument(
        "--season",
        type=str,
        default="Kharif",
        help="Growing season (default: Kharif)",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=data_config.START_YEAR,
        help="Start year (default: 1990)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=data_config.END_YEAR,
        help="End year (default: 2017)",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Force redownload from remote APIs instead of using local cache",
    )
    parser.add_argument(
        "--stage",
        type=str,
        default="all",
        choices=["all", "yield", "weather", "soil", "align"],
        help="Pipeline stage to execute (default: all)",
    )

    args = parser.parse_args()
    exit_code = run_pipeline(
        crop=args.crop,
        season=args.season,
        start_year=args.start_year,
        end_year=args.end_year,
        force_download=args.force_download,
        stage=args.stage,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
