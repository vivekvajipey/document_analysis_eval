# evaluation_ruminate/metrics/text_accuracy.py
from typing import Any, Dict, Union
import Levenshtein # Requires pip install python-Levenshtein

from .base_metrics import BaseMetric

class TextEditDistance(BaseMetric):
    """Calculates Levenshtein distance between predicted and ground truth text."""

    @property
    def name(self) -> str:
        return "text_edit_distance"

    def calculate(self, prediction: Any, ground_truth: Any) -> Union[float, Dict[str, float]]:
        """
        Calculates Levenshtein distance.
        :param prediction: The predicted text string.
        :param ground_truth: Dictionary potentially containing GT text under the 'text' key.
        :return: Levenshtein distance as float, or -1.0 if input is invalid.
        """
        pred_text = str(prediction) if prediction is not None else ""

        if not isinstance(ground_truth, dict) or 'text' not in ground_truth:
             print(f"Warning: Ground truth for {self.name} missing 'text' key.")
             gt_text = "" # Or handle as error / return None
        else:
             gt_text = str(ground_truth['text']) if ground_truth['text'] is not None else ""

        if not gt_text and not pred_text:
            return 0.0 # Both empty
        if not gt_text or not pred_text:
            # Handle case where one is empty and the other isn't if needed,
            # Levenshtein distance might be length of the non-empty string.
            # Let's return a large value or specific indicator if desired.
            # For now, Levenshtein handles this fine.
            pass


        try:
            distance = Levenshtein.distance(pred_text, gt_text)
            # You might want to normalize this (e.g., by length of GT)
            # normalized_distance = distance / len(gt_text) if len(gt_text) > 0 else float('inf') if distance > 0 else 0.0
            # return normalized_distance
            return float(distance)
        except Exception as e:
            print(f"Error calculating Levenshtein distance: {e}")
            return -1.0 # Indicate error