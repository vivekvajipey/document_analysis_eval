# evaluation_system/pipelines/executor.py
import yaml
import importlib
from pathlib import Path
from typing import List, Dict, Any, Tuple

from tools.base_tool import BaseTool # Assuming tools are importable

class PipelineExecutor:
    def __init__(self, pipeline_config_path: Path):
        """
        Initialize the executor with the path to a pipeline configuration file.
        :param pipeline_config_path: Path to the YAML pipeline configuration file.
        """
        if not pipeline_config_path.exists():
            raise FileNotFoundError(f"Pipeline config not found: {pipeline_config_path}")

        with open(pipeline_config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        if not self.config or 'pipeline_name' not in self.config or 'stages' not in self.config:
            raise ValueError(f"Invalid pipeline config format in {pipeline_config_path}")

        self.pipeline_name = self.config['pipeline_name']
        self.stages = self.config['stages']
        self._tools_cache = {} # Cache instantiated tools if needed

    def _get_tool_instance(self, tool_module_path: str, tool_class_name: str, tool_config: Dict) -> BaseTool:
        """Dynamically imports and instantiates a tool."""
        try:
            # Example: tool_module_path = "tools.marker_wrapper"
            #          tool_class_name = "MarkerWrapper"
            module = importlib.import_module(tool_module_path)
            tool_class = getattr(module, tool_class_name)
            if not issubclass(tool_class, BaseTool):
                 raise TypeError(f"{tool_class_name} is not a subclass of BaseTool")
            # You might want to cache instances if tools are stateless and config is the same
            # key = (tool_module_path, tool_class_name, str(tool_config))
            # if key not in self._tools_cache:
            #    self._tools_cache[key] = tool_class(config=tool_config)
            # return self._tools_cache[key]
            return tool_class(config=tool_config) # Instantiate anew each time for simplicity here
        except (ImportError, AttributeError, TypeError) as e:
            print(f"Error loading tool {tool_class_name} from {tool_module_path}: {e}")
            raise

    def run(self, initial_input: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the defined pipeline sequentially.
        :param initial_input: The initial data for the first stage (e.g., PDF file path).
        :param context: Dictionary holding context info (e.g., pdf_path, run_id).
        :return: Dictionary containing results:
                 {'pipeline_name': str,
                  'final_output': Any,
                  'stages': [{'name': str, 'output': Any, 'cost': float, 'latency': float}],
                  'total_cost': float,
                  'total_latency': float}
        """
        current_data = initial_input
        stage_results = []
        total_cost = 0.0
        total_latency = 0.0

        print(f"--- Running Pipeline: {self.pipeline_name} ---")
        for i, stage_config in enumerate(self.stages):
            stage_name = stage_config.get('name', f'stage_{i+1}')
            tool_module = stage_config.get('tool_module')
            tool_class = stage_config.get('tool_class')
            tool_params = stage_config.get('params', {})

            if not tool_module or not tool_class:
                print(f"Skipping stage {stage_name}: Missing 'tool_module' or 'tool_class'.")
                continue

            print(f"  Executing Stage: {stage_name} ({tool_class})")
            try:
                tool_instance = self._get_tool_instance(tool_module, tool_class, tool_params)
                output_data, cost, latency = tool_instance.run(current_data, context)

                print(f"  Stage {stage_name} completed: Latency={latency:.4f}s, Cost={cost:.6f}")
                stage_results.append({
                    'name': stage_name,
                    'output': output_data, # Caution: storing large intermediate outputs
                    'cost': cost,
                    'latency': latency
                })
                total_cost += cost
                total_latency += latency
                current_data = output_data # Pass output to the next stage

            except Exception as e:
                print(f"  Stage {stage_name} FAILED: {e}")
                # Decide on failure strategy: stop pipeline, record failure, continue?
                # For now, let's stop and report partial results
                break # Stop pipeline execution on stage failure

        print(f"--- Pipeline {self.pipeline_name} Finished ---")
        print(f"Total Latency: {total_latency:.4f}s")
        print(f"Total Est. Cost: {total_cost:.6f}")

        return {
            'pipeline_name': self.pipeline_name,
            'final_output': current_data, # Last successful output or initial input if first stage failed
            'stages': stage_results,
            'total_cost': total_cost,
            'total_latency': total_latency,
            'success': len(stage_results) == len(self.stages) # Indicate if all stages completed
        }