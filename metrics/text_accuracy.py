# evaluation_ruminate/metrics/text_accuracy.py
from typing import Any, Dict, Union, List
import Levenshtein # Requires pip install python-Levenshtein

from .base_metrics import BaseMetric

class TextEditDistance(BaseMetric):
    """Calculates Levenshtein distance between predicted and ground truth text."""

    @property
    def name(self) -> str:
        return "text_edit_distance"

    def calculate(self, prediction: Any, ground_truth: Any) -> Union[float, Dict[str, float]]:
        """
        Calculates Levenshtein distance for both raw text and content units.
        :param prediction: The predicted text or dictionary containing text or content_units.
        :param ground_truth: Dictionary containing GT text or content_units.
        :return: Dictionary with raw_text_distance, normalized_distance, and optionally unit_distances.
        """
        results = {}
        
        # Extract raw text from prediction (either direct text string or inside dict)
        pred_text = ""
        if isinstance(prediction, str):
            pred_text = prediction
        elif isinstance(prediction, dict) and "text" in prediction:
            pred_text = prediction["text"]
        
        # Extract ground truth text
        if not isinstance(ground_truth, dict) or "text" not in ground_truth:
            print(f"Warning: Ground truth for {self.name} missing 'text' key.")
            gt_text = ""
        else:
            gt_text = ground_truth["text"]
        
        # Calculate raw text distance
        if not gt_text and not pred_text:
            results["raw_text_distance"] = 0.0
            results["normalized_distance"] = 0.0
        else:
            try:
                distance = Levenshtein.distance(pred_text, gt_text)
                results["raw_text_distance"] = float(distance)
                # Normalize by the length of ground truth text
                max_len = max(len(gt_text), 1)  # Avoid division by zero
                results["normalized_distance"] = distance / max_len
            except Exception as e:
                print(f"Error calculating Levenshtein distance: {e}")
                results["raw_text_distance"] = -1.0
                results["normalized_distance"] = -1.0
        
        # If both prediction and ground truth have content_units, compare those too
        if (isinstance(prediction, dict) and "content_units" in prediction and 
            isinstance(ground_truth, dict) and "content_units" in ground_truth):
            
            pred_units = prediction["content_units"]
            gt_units = ground_truth["content_units"]
            
            # Calculate content unit distances - simplified approach for now
            # For a more sophisticated approach, you might want to align units first
            unit_distances = []
            
            # Calculate distance between concatenated unit texts
            pred_concat = "\n".join([u.get("text", "") for u in pred_units if isinstance(u, dict)])
            gt_concat = "\n".join([u.get("text", "") for u in gt_units if isinstance(u, dict)])
            
            unit_distance = Levenshtein.distance(pred_concat, gt_concat)
            max_unit_len = max(len(gt_concat), 1)
            unit_normalized = unit_distance / max_unit_len
            
            results["unit_text_distance"] = float(unit_distance)
            results["unit_normalized_distance"] = unit_normalized
            
        return results