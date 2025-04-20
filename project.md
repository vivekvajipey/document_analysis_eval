# Ruminate Document Preprocessing Evaluation System

## 1. Introduction & Objectives

**Context:** The Ruminate application currently utilizes the Marker library for PDF processing, enabling users to interact with documents on a block-by-block basis. While functional, user feedback indicates a desire for a more seamless reading experience primarily focused on the interactive right-hand pane (rendered block content + chat). The current system, tied to Marker's layout-based blocks, can sometimes result in fragmented or unnaturally segmented content.

**Primary Goal:** To identify and implement an optimal document preprocessing pipeline for Ruminate that accurately extracts, orders, and structures document content into **natural reading units**. This will enable a fluid, intuitive, and reliable reading and interaction experience entirely within the application's right-hand pane, minimizing reliance on the raw PDF view for content consumption.

**Evaluation Objectives:** This evaluation system aims to:
1.  **Benchmark Performance:** Quantitatively measure the accuracy of different preprocessing pipelines across various dimensions (text extraction, structure identification, reading order, table/formula accuracy, reading unit quality).
2.  **Assess Cost:** Estimate the monetary cost associated with running each pipeline (API usage, compute resources).
3.  **Measure Latency:** Determine the processing time required for each pipeline to understand the impact on user experience.
4.  **Enable Data-Driven Decisions:** Provide objective data to select the most effective and efficient pipeline architecture for Ruminate's specific needs and target document types.
5.  **Facilitate Experimentation:** Create a modular framework to easily test new tools, models, or pipeline configurations as the field evolves.

## 2. Evaluation Scope & Methodology

**Approach:** We will evaluate multiple **modular preprocessing pipelines**. Each pipeline consists of a sequence of tools designed to perform specific sub-tasks (e.g., layout analysis, OCR, table extraction, reading unit construction).

**Core Process:**
1.  **Dataset:** A diverse corpus of PDF documents representing various types (academic papers, scanned documents, financial reports, textbooks, notes, etc.) will be used as input. Corresponding ground truth data (correct text, layout, reading order, table structures, manually defined "natural reading units") will be prepared for comparison.
2.  **Pipeline Execution:** Pre-defined pipeline configurations (sequences of tools) will be run on each document in the test set using the `PipelineExecutor`.
3.  **Data Collection:** During execution, the system will record:
    * Intermediate and final outputs from each pipeline stage.
    * Estimated cost incurred by each tool (especially API calls).
    * Latency (processing time) for each tool and the total pipeline.
4.  **Metric Calculation:** The final structured output of each pipeline will be compared against the ground truth using a suite of defined metrics.
5.  **Analysis:** Results (accuracy metrics, cost, latency) will be aggregated and analyzed to compare the effectiveness and efficiency of different pipelines across various document types and attributes.

## 3. Tools & Pipelines Under Evaluation

The system is designed to be flexible, allowing the evaluation of various tools and their combinations.

**`Tool Categories (Examples based on tools/ wrappers):`**
* **Baseline/Existing:**
    * `MarkerWrapper`: Interfacing with the Marker library/API (potentially testing different configurations like `--use_llm`).
* **Alternative Pipeline Components:**
    * *Layout Analysis:* `SuryaLayoutWrapper` (if separating layout analysis).
    * *OCR:* `PaddleOCRWrapper`, `TesseractWrapper`, potentially others evaluated in OmniDocBench.
    * *Basic Extraction:* `PyMuPDFExtractor` (for baseline text/coordinate extraction).
    * *Table Extraction:* `TableTransformerWrapper` or other specialized table parsers.
    * *Formula Recognition:* Wrappers for tools like Mathpix or specialized models.
* **End-to-End VLMs:**
    * `MistralWrapper`: Interfacing with the Mistral OCR API.
    * `GeminiWrapper`: Interfacing with the Google Gemini API (leveraging its native PDF processing, File API, and potentially structured output capabilities).
    * Wrappers for other relevant VLMs (e.g., Nougat, Qwen2-VL).
* **Hybrid Components:**
    * *VLM-based Refiner:* Using `GeminiWrapper` or `MistralWrapper` with specific prompts to refine order, merge/split blocks, and associate elements based on output from earlier pipeline stages.
    * *Unit Constructor:* A dedicated tool (`UnitConstructor`) using heuristics or a model to assemble the final "natural reading units".

**`Example Pipelines (Defined in pipelines/configs/):`**
* `marker_baseline.yaml`: Evaluates the current approach using Marker.
* `marker_llm.yaml`: Evaluates Marker with the `--use_llm` flag enabled.
* `mistral_ocr_e2e.yaml`: Evaluates using Mistral OCR for end-to-end processing.
* `gemini_e2e.yaml`: Evaluates using Gemini API for end-to-end processing.
* `pipeline_pymupdf_ocr_gemini_refine.yaml`: A hybrid example: PyMuPDF for text -> PaddleOCR -> Gemini for refining order and constructing reading units.
* `pipeline_marker_gemini_refine.yaml`: Marker for initial structure -> Gemini for refining order and constructing reading units.

## 4. Key Evaluation Criteria & Metrics

Pipelines will be evaluated across three primary dimensions:

**A. Performance (Accuracy):** How accurately does the pipeline extract and structure the content?
* **OCR Accuracy:** Assesses the correctness of extracted text, especially crucial for scanned documents.
    * *Metrics:* Normalized Edit Distance (NED), Character Error Rate (CER), Word Error Rate (WER). (Implemented in `metrics/text_accuracy.py`)
* **Layout/Structure Accuracy:** Assesses the correct identification and classification of document elements (paragraphs, headings, lists, figures, etc.).
    * *Metrics:* mAP/IoU for bounding box detection/classification (if evaluating layout detection tools), potentially custom metrics for correct classification against GT block types. (Implemented in `metrics/layout_detection.py`)
* **Table Accuracy:** Assesses the correctness of extracted table structure and cell content.
    * *Metrics:* TEDS (Tree-Edit-Distance-based Similarity), Normalized Edit Distance (on cell content). (Implemented in `metrics/table_accuracy.py`)
* **Formula Accuracy:** Assesses the correctness of extracted mathematical formulas.
    * *Metrics:* Normalized Edit Distance (on LaTeX), BLEU, potentially CDM. (Implemented in `metrics/formula_accuracy.py`)
* **Reading Order Accuracy:** Assesses if the content is ordered correctly for linear reading.
    * *Metrics:* Normalized Edit Distance (on the sequence of ground truth block IDs corresponding to the predicted sequence). (Implemented in `metrics/reading_order.py`)
* **"Natural Reading Unit" Quality:** Assesses how well the final output aligns with a human reader's expectation of coherent text units.
    * *Metrics:* Custom metrics comparing pipeline output units to manually defined ground truth units (e.g., measuring unnecessary splits (fragmentation), incorrect merges, correct grouping of figures/captions). Qualitative review by humans. (Implemented in `metrics/reading_unit_quality.py`)

**B. Cost:** What is the estimated monetary cost to process a document?
* *Metrics:* Cost per document (or per page). Calculated based on API pricing (e.g., tokens used, pages processed) and estimated compute costs for local models. (Tracked via `BaseTool` and aggregated in `evaluation/run_evaluation.py`)

**C. Latency:** How long does it take to process a document?
* *Metrics:* Time per document (or per page) in seconds. Measured for each stage and the total pipeline. (Tracked via `BaseTool` and aggregated in `evaluation/run_evaluation.py`)

## 5. System Architecture Overview

The evaluation system is designed with modularity using the following structure:
* `config/`: Holds global settings like API keys.
* `data/`: Contains test PDFs and corresponding ground truth annotations.
* `pipelines/`: Defines specific processing workflows (`configs/`) and the logic to execute them (`executor.py`).
* `tools/`: Contains wrappers (`*_wrapper.py`) for each external tool or model, implementing a common `BaseTool` interface that includes `process`, `get_cost`, and `get_latency` methods.
* `metrics/`: Contains implementations for various accuracy and quality metrics, inheriting from a `BaseMetric` interface.
* `evaluation/`: Scripts to orchestrate evaluation runs (`run_evaluation.py`), analyze results (`analyze_results.py`), and visualize comparisons (`plot_results.py`).
* `results/`: Stores detailed raw outputs and aggregated summary statistics from evaluation runs.

This structure allows for easy addition and testing of new components (tools, pipelines, metrics) and systematic comparison.

## 6. Vision & Expected Outcomes

**Vision:** This evaluation system will provide Ruminate with a robust, data-driven framework to continuously assess and improve its document understanding capabilities. It moves beyond relying on a single tool's limitations and embraces a flexible approach to find the optimal balance between state-of-the-art accuracy, operational cost, and user-perceived performance (latency).

**Expected Outcomes:**
* **Identify Optimal Pipeline:** Determine the specific combination of tools (Marker, VLMs, specialized extractors, custom logic) that yields the best results for Ruminate based on accuracy, cost, and latency trade-offs across relevant document types.
* **Quantify Improvements:** Measure the concrete benefits of new pipeline configurations compared to the baseline Marker-block approach.
* **Pinpoint Bottlenecks:** Identify which stages or tools in a pipeline contribute most to errors, cost, or latency.
* **Foundation for Future Improvement:** Establish a repeatable process for evaluating and integrating new document parsing technologies as they emerge.
* **Enhanced User Experience:** Ultimately, the insights gained will lead to a Ruminate application that provides users with highly accurate, seamlessly flowing document content in the interactive pane, enabling deeper understanding and more effective interaction.
