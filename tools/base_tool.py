# evaluation_system/tools/base_tool.py
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

class BaseTool(ABC):
    """Abstract base class for all processing tools in the pipeline."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the tool with its specific configuration.
        :param config: Dictionary containing configuration parameters for the tool.
        """
        self.config = config
        self._cost = 0.0
        self._latency = 0.0

    @abstractmethod
    def process(self, input_data: Any, context: Dict[str, Any]) -> Any:
        """
        Process the input data using the tool.
        :param input_data: Data from the previous pipeline stage or initial input.
        :param context: Dictionary holding context info (e.g., pdf_path, run_id).
        :return: Processed output data.
        """
        pass

    def run(self, input_data: Any, context: Dict[str, Any]) -> Tuple[Any, float, float]:
        """
        Runs the process method and tracks latency and cost.
        Subclasses should generally not override this, but override _process.
        They can update self._cost within _process if needed (e.g., token usage).

        :param input_data: Data from the previous pipeline stage or initial input.
        :param context: Dictionary holding context info.
        :return: Tuple containing (processed_output, cost, latency).
        """
        self._cost = 0.0  # Reset cost for this run
        start_time = time.monotonic()
        
        try:
            output_data = self.process(input_data, context)
            self._latency = time.monotonic() - start_time
            # Cost might be updated within process() based on API usage etc.
            # Add basic cost calculation logic here if applicable by default
            # e.g., self._cost = self._calculate_cost(output_data)
        except Exception as e:
            print(f"Error processing with {self.__class__.__name__}: {e}")
            self._latency = time.monotonic() - start_time
            # Decide how to handle errors - raise, return None, return error object?
            # For now, let's re-raise or return a specific error indicator
            raise # Or return None / specific error structure

        return output_data, self.get_cost(), self.get_latency()

    def get_cost(self) -> float:
        """Returns the estimated cost incurred by the last process() call."""
        # This might involve API call costs, token counts, etc.
        # Tools should update self._cost in their process method if applicable.
        return self._cost

    def get_latency(self) -> float:
        """Returns the latency (in seconds) of the last process() call."""
        return self._latency

    # Optional: Helper for cost calculation if needed by subclasses
    # def _calculate_cost(self, output_data: Any) -> float:
    #     """Estimate cost based on output or internal metrics."""
    #     return 0.0