import os
import pandas as pd
import requests
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral:instruct"  

PROMPT_TEMPLATE = '''Let's break down this logical statement according to the provided guidelines.

**1. Logical Statement:**
{logical_statement}

**2. Step 1: Logical Decomposition**

*   **Expert A (Simplified Language):**
    *   **Role:** Provide an initial breakdown in simplified terms, focusing on clarity and understanding.
    *   **Focus:** Break down the logical statement into manageable conditions while retaining the core meaning.
    *   **Simplified Translation:** Identify the core conditions (such as modes, states, inputs) and break them into key criteria for the transition.

*   **Expert B (Technical Precision):**
    *   **Role:** Translate the statement using technical terminology and ensure accuracy in logical expressions.
    *   **Focus:** Use precise language to explain the conditions without oversimplifying.
    *   **Precise Translation:** Define the conditions and logical relationships (AND, OR, NOT) explicitly with accurate terminology and variable names.

*   **Expert C (Contextual Example):**
    *   **Role:** Use real-world analogies or contextual explanations to clarify the system's behavior for technical users.
    *   **Focus:** Provide relevant analogies that align with technical scenarios, but without oversimplifying.
    *   **Contextual Example:** Provide relatable comparisons to real-world systems (e.g., decision-making processes, system transitions) to clarify the conditions, without reducing the complexity of the logic.

**3. Step 2: Refining the Explanation**

*   **Expert A (Simplified Language):**
    *   **Role:** Organize the conditions into clear steps, using simple language.
    *   **Focus:** Break the logic down into digestible parts while preserving key technical details.
    *   **Simplified Explanation:** Clearly list out the conditions that must be met for the transition, using straightforward language and bullet points for ease of understanding.

*   **Expert B (Technical Precision):**
    *   **Role:** Ensure the translation is technically precise, using consistent terms and logical operators.
    *   **Focus:** Ensure all logical operators and conditions are clearly explained using proper technical terminology.
    *   **Refined Technical Explanation:** Present the explanation with a focus on accuracy, where each condition is listed clearly, ensuring all technical variables and their relationships are intact.

*   **Expert C (Contextual Example):**
    *   **Role:** Refine the example or analogy to ensure it remains relevant, accurate, and helpful.
    *   **Focus:** Provide an example that aligns with the technical scenario, ensuring the analogy helps clarify the logic.
    *   **Contextual Example:** Provide a more concise, yet accurate example that mirrors the technical scenario and simplifies the understanding of the system's transitions.

**4. Step 3: Final Combined Result**

*   **Combined Result:**
    *   **Role:** Combine all insights from the previous steps into a final refined translation.
    *   **Focus:** The final translation should be clear, precise, and concise, ensuring the explanation is suitable for a technical audience.
    *   **Final Combined Translation:**
        Provide a final cohesive explanation, ensuring that all key technical details, conditions, and relationships are presented clearly. List conditions as needed and provide an overview of how they interrelate.

Strictly follow the structure of the guidelines and the example provided. In the output just display the final translation and nothing else. Do not add the verbose of the previous steps.'''

def logical_to_natural_language(logical_expr, model=MODEL):
    prompt = PROMPT_TEMPLATE.format(logical_statement=logical_expr)
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False
        }
    )
    print("----------------------------")
    return response.json()["response"].strip()

def main():
    csv_path = os.path.join(os.path.dirname(__file__), 'expressions.csv')
    output_dir = os.path.join(os.path.dirname(__file__), 'nl_outputs')
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(csv_path)
    for idx, row in df.iterrows():
        simplified = row["simplified"]
        nl = logical_to_natural_language(simplified)
        out_path = os.path.join(output_dir, f"nl_{idx}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"Logical Statement:\n{simplified}\n\nFinal Combined Translation:\n{nl}\n")
        print(f"Saved: {out_path}")

if __name__ == "__main__":
    main() 
