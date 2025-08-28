---

This project is a pipeline for simplifying complex logical expressions, verifying the correctness of the simplifications, and generating natural language descriptions from the simplified logic.

---

## About The Project

The core of this project is a Python-based pipeline that takes logical expressions from a specification file, simplifies them using the powerful SymPy library, and then verifies that the simplified expressions are logically equivalent to the original ones by Z3 SMT solver. Finally, it generates natural language descriptions of the simplified logic using a local llm model running on ollama,the translation  make it easier for engineers and stakeholders to understand the system's behavior.

##  Core Components (Python Files)

This project is composed of several Python scripts that work together to form the processing pipeline.

### `run_pipeline.py`

This is the main entry point for the entire pipeline. It orchestrates the execution of the other scripts in the correct order:

1.  **Simplifier** (`SYMPY SIMPLIFIER.py`)
2.  **Verifier** (`VERIFIER.py`)
3.  **Natural Language Generator** (`generate_nl_files.py`)

It ensures that each step completes successfully before proceeding to the next, providing a seamless workflow from raw logical expressions to verified, human-readable specifications.

### `SYMPY SIMPLIFIER.py`

This script is the core of the simplification logic. It reads expressions from the `SPECS/spec.txt` file and performs the following actions:

* **Formatting**: It uses the `FORMATTER.py` module to convert the logical expressions into a SymPy-compatible format.
* **Simplification**: It leverages the `simplify_logic` function from the SymPy library to reduce the complexity of the expressions.
* **Output**: The original and simplified expressions are saved to `expressions.csv` for the verification step.

### `FORMATTER.py`

This module serves as a pre-processor for the `SYMPY SIMPLIFIER.py` script. Its main responsibility is to take raw logical expressions and normalize them by:

* **Variable Mapping**: Replacing complex variable names with single-letter placeholders (A, B, C, etc.) to make them easier for SymPy to handle.
* **Syntax Conversion**: Translating common logical operators (like `&&`, `||`, `!`) into a format that SymPy can parse.

### `VERIFIER.py`

To ensure the integrity of the simplification process, this script uses the Z3 theorem prover to verify that the simplified expressions are logically equivalent to the original ones. It reads the pairs of expressions from `expressions.csv` and:

* **Z3 Expression Conversion**: Converts the string expressions into Z3's format.
* **Equivalence Checking**: For each pair, it creates a proof goal to check if `original != simplified` is unsatisfiable. If it is, the expressions are equivalent.
* **Reporting**: The results of the verification are saved in `verification_results.txt`, which includes a summary of equivalent, non-equivalent, and erroneous pairs.

### `generate_nl_files.py`

The final step in the pipeline is to make the simplified expressions more accessible. This script reads the simplified logic from `expressions.csv` and:

* **Ollama Integration**: Sends the logical statements to a large language model(mistral:instruct) via ollama local API.
* **Natural Language Generation**: The model translates the logical expressions into clear, human-readable text.
* **Output**: The generated descriptions are saved as individual text files in the `nl_outputs/` directory.
---

## 🗂️ Key Files and Directories

* **`SPECS/spec.txt`**: This is the input file for the pipeline. It contains the raw, complex logical expressions that need to be processed, with one expression per line.

* **`expressions.csv`**: This CSV file is an intermediate output from the simplification step. It stores the original expression and its corresponding simplified version in two columns, making it easy for the verifier to process them in pairs.

* **`verification_results.txt`**: This file contains the summary of the verification process, detailing the number of expression pairs that were successfully verified as equivalent.

* **`simplified_expression.txt`**: A output file that shows a single logical statement, its simplified form, and the mappings between the original variables and the simplified placeholders used as cache for.
---
### Prerequisites

This project requires Python 3.13 You will also need to install the necessary Python libraries and set up Ollama for the natural language generation step.

**1. Install Python Libraries**

You can install all the required libraries using the `requirements.txt` file:pip install -r requirements.txt

**2. Set Up Ollama**

# Ollama Setup for Natural Language Generation

The `generate_nl_files.py` script in this project uses **Ollama** to run a large language model locally on your machine.  
This allows you to generate natural language descriptions of the logical expressions without needing an internet connection or API keys.

## Follow these steps to get Ollama set up:

### 1. Download and Install Ollama
- Visit the official Ollama website: [https://ollama.com/]
- Download the installer for your operating system (Windows, macOS, or Linux) and follow the installation instructions.

### 2. Pull the Required Model
Once Ollama is installed, you need to download the specific model used by this project.  
Open your terminal (or Command Prompt on Windows) and run the following command:

```bash
ollama pull mistral:instruct

```
### 3. Ensure Ollama is Running

Before you run the main run_pipeline.py script, you must ensure that the Ollama application is running in the background.
The script needs to communicate with the Ollama server to generate the natural language text

### 4. Run the Main Script
Now, you can run the main run_pipeline.py script.
