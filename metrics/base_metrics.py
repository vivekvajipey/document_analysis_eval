# evaluation_system/metrics/base_metric.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Union

class BaseMetric(ABC):
    """Abstract base class for evaluation metrics."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the metric, potentially with configuration.
        :param config: Dictionary containing configuration parameters for the metric.
        """
        self.config = config or {}

    @abstractmethod
    def calculate(self, prediction: Any, ground_truth: Any) -> Union[float, Dict[str, float]]:
        """
        Calculate the metric score.
        :param prediction: The output produced by the pipeline/tool.
        :param ground_truth: The corresponding ground truth data.
        :return: A single float score or a dictionary of scores.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the metric."""
        pass