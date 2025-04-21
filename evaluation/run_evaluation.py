# evaluation_system/evaluation/run_evaluation.py
import argparse
import json
import yaml
from pathlib import Path
from datetime import datetime
import importlib
import pandas as pd # For saving aggregated results

from pipelines.executor import PipelineExecutor
from metrics.base_metrics import BaseMetric # Corrected import

# --- Helper Functions ---

def load_ground_truth(gt_base_path: Path, pdf_filename: str) -> Dict[str, Any]:
    """Loads ground truth for a given PDF from a JSON file."""
    pdf_name_no_ext = Path(pdf_filename).stem
    json_path = gt_base_path / f"{pdf_name_no_ext}.json"
    
    print(f"    Loading ground truth for {pdf_filename} from {json_path}...")
    
    gt_data = {}
    if json_path.exists():
        try:
            with open(json_path, 'r') as f:
                gt_data = json.load(f)
                
            # For text accuracy metrics, also provide concatenated text for simpler comparison
            if "content_units" in gt_data:
                concatenated_text = "\n".join([unit["text"] for unit in gt_data["content_units"]])
                gt_data["text"] = concatenated_text
                
            print(f"    Ground truth loaded successfully with {len(gt_data.get('content_units', []))} content units")
        except Exception as e:
            print(f"    Error loading ground truth: {e}")
    else:
        print(f"    No ground truth file found at {json_path}")
    
    return gt_data

def load_metrics(metric_configs: List[Dict]) -> List[BaseMetric]:
    """Dynamically loads and instantiates specified metric classes."""
    metrics = []
    print("  Loading metrics...")
    for mc in metric_configs:
        try:
            module_path = mc['metric_module']
            class_name = mc['metric_class']
            params = mc.get('params', {})
            module = importlib.import_module(module_path)
            metric_class = getattr(module, class_name)
            if not issubclass(metric_class, BaseMetric):
                raise TypeError(f"{class_name} is not a subclass of BaseMetric")
            instance = metric_class(config=params)
            metrics.append(instance)
            print(f"    Loaded metric: {instance.name}")
        except (ImportError, AttributeError, KeyError, TypeError) as e:
            print(f"    Error loading metric {mc}: {e}")
    return metrics

def calculate_all_metrics(metrics: List[BaseMetric], prediction: Any, ground_truth: Dict[str, Any]) -> Dict[str, Any]:
    """Runs all loaded metrics."""
    metric_results = {}
    print("    Calculating metrics...")
    for metric in metrics:
        try:
            # Determine which part of GT the metric needs
            # This might require conventions or config in the metric itself
            # Example: if metric.name == 'text_edit_distance': gt = ground_truth.get('text')
            # For simplicity here, pass all GT. Metrics must handle missing keys.
            score = metric.calculate(prediction, ground_truth)
            metric_results[metric.name] = score
            print(f"      {metric.name}: {score}")
        except Exception as e:
            print(f"    Error calculating metric {metric.name}: {e}")
            metric_results[metric.name] = None # Or specific error value
    return metric_results

def save_results(output_dir: Path, pipeline_name: str, run_ts: str, pdf_filename: str,
                 pipeline_output: Dict, metrics_output: Dict):
    """Saves raw pipeline output and metrics for a single document."""
    doc_results_dir = output_dir / "raw" / pipeline_name / run_ts / pdf_filename.stem
    doc_results_dir.mkdir(parents=True, exist_ok=True)

    # Save final structured output (used for metrics)
    final_output_path = doc_results_dir / "final_output.json"
    try:
        # Assuming final output is JSON serializable
        with open(final_output_path, 'w') as f:
            json.dump(pipeline_output.get('final_output', None), f, indent=2)
    except TypeError as e:
         print(f"    Warning: Could not serialize final output to JSON: {e}")
         # Fallback: save as string or handle differently
         (doc_results_dir / "final_output.txt").write_text(str(pipeline_output.get('final_output', None)))


    # Save metadata (cost, latency, metrics)
    metadata = {
        "pdf_filename": pdf_filename,
        "pipeline_name": pipeline_name,
        "run_timestamp": run_ts,
        "total_cost": pipeline_output.get('total_cost'),
        "total_latency": pipeline_output.get('total_latency'),
        "success": pipeline_output.get('success'),
        "metrics": metrics_output,
        "stages": [ # Save stage costs/latencies, omit large outputs
            {k: v for k, v in stage.items() if k != 'output'}
            for stage in pipeline_output.get('stages', [])
        ]
    }
    metadata_path = doc_results_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    return metadata # Return metadata for aggregation


# --- Main Execution Logic ---

def main(args):
    # Load evaluation config
    with open(args.eval_config, 'r') as f:
        eval_config = yaml.safe_load(f)

    data_base_path = Path(eval_config['data_base_path'])
    gt_base_path = Path(eval_config['ground_truth_base_path'])
    results_base_path = Path(eval_config['results_base_path'])
    pipeline_configs_dir = Path(eval_config['pipeline_configs_dir'])
    dataset_categories = eval_config.get('dataset_categories', ['*']) # Default to all
    pdf_limit = eval_config.get('pdf_limit_per_category', None)
    metrics_to_run = eval_config.get('metrics', [])

    # Load metrics
    metrics = load_metrics(metrics_to_run)
    if not metrics:
        print("No metrics loaded. Exiting.")
        return

    # Identify pipelines to run
    pipelines_to_run = []
    if args.pipeline:
        # Run specific pipeline(s) passed via args
        for p_name in args.pipeline:
             p_path = pipeline_configs_dir / f"{p_name}.yaml"
             if p_path.exists():
                 pipelines_to_run.append(p_path)
             else:
                 print(f"Warning: Pipeline config not found: {p_path}")
    else:
        # Run all pipelines defined in the config dir
        pipelines_to_run = list(pipeline_configs_dir.glob("*.yaml"))

    if not pipelines_to_run:
        print("No pipeline configurations found to run. Exiting.")
        return

    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_aggregated_results = []

    print(f"\n=== Starting Evaluation Run: {run_timestamp} ===")

    for pipeline_config_path in pipelines_to_run:
        try:
            executor = PipelineExecutor(pipeline_config_path)
            pipeline_name = executor.pipeline_name
            print(f"\n--- Evaluating Pipeline: {pipeline_name} ---")

            # Find PDFs to process
            pdfs_processed_count = 0
            for category in dataset_categories:
                category_path = data_base_path / category
                print(f"  Processing category: {category}...")
                category_pdfs = sorted(list(category_path.glob("*.pdf")))
                limit = pdf_limit

                if not category_pdfs:
                    print(f"    No PDFs found in {category_path}")
                    continue

                for pdf_path in category_pdfs:
                    if limit is not None and limit <= 0:
                        break # Reached limit for this category

                    print(f"\n  Processing PDF: {pdf_path.name}")
                    context = {
                        "pdf_path": str(pdf_path),
                        "run_id": run_timestamp,
                        "pipeline_name": pipeline_name
                    }

                    # Load Ground Truth
                    ground_truth = load_ground_truth(gt_base_path, pdf_path.name)
                    if not ground_truth:
                        print(f"    Warning: No ground truth found for {pdf_path.name}. Skipping metrics.")
                        # Optionally run pipeline anyway if needed for just cost/latency
                        # pipeline_result = executor.run(initial_input=str(pdf_path), context=context)
                        continue # Skip if GT is required for metrics

                    # Run Pipeline
                    pipeline_result = executor.run(initial_input=str(pdf_path), context=context)

                    # Calculate Metrics
                    prediction_output = pipeline_result.get('final_output') # Or specific structured output
                    metrics_result = calculate_all_metrics(metrics, prediction_output, ground_truth)

                    # Save Individual Results
                    doc_metadata = save_results(results_base_path, pipeline_name, run_timestamp, pdf_path.name,
                                                pipeline_result, metrics_result)
                    all_aggregated_results.append(doc_metadata)

                    if limit is not None:
                        limit -= 1
                    pdfs_processed_count += 1

        except (FileNotFoundError, ValueError, ImportError) as e:
            print(f"Error setting up pipeline {pipeline_config_path.stem}: {e}")
            continue # Move to next pipeline

    # Save aggregated results
    if all_aggregated_results:
        agg_df = pd.DataFrame(all_aggregated_results)
        # Optionally flatten metrics dictionary
        # agg_df = pd.concat([agg_df.drop(['metrics'], axis=1), agg_df['metrics'].apply(pd.Series)], axis=1)
        agg_filename = results_base_path / "aggregated" / f"summary_{run_timestamp}.csv"
        agg_filename.parent.mkdir(parents=True, exist_ok=True)
        agg_df.to_csv(agg_filename, index=False)
        print(f"\nAggregated results saved to: {agg_filename}")

    print(f"\n=== Evaluation Run {run_timestamp} Complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Document Preprocessing Pipeline Evaluations")
    parser.add_argument("--eval_config", type=Path, required=True, help="Path to the main evaluation YAML config file.")
    parser.add_argument("--pipeline", type=str, nargs='+', help="Optional: Run only specific pipeline(s) by name (e.g., marker_baseline gemini_e2e). Runs all if not specified.")
    # Add other arguments if needed (e.g., dataset filter, specific output dir)

    args = parser.parse_args()
    main(args)