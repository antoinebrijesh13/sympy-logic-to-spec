#!/usr/bin/env python3

import os
import sys
import subprocess
import time

def run_script(script_name, description):
    """Run a Python script and handle any errors"""
    print(f"\n{'='*60}")
    print(f"Running {description}...")
    print(f"{'='*60}")
    
    try:
        # Get the absolute path to the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, script_name)
        
        # Check if the script exists
        if not os.path.exists(script_path):
            print(f"Error: Script {script_name} not found at {script_path}")
            return False
        
        # Run the script from the script directory
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=False, 
                              text=True, 
                              cwd=script_dir)
        
        if result.returncode == 0:
            print(f"\n✓ {description} completed successfully!")
        else:
            print(f"\n✗ {description} failed with return code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"\n✗ Error running {description}: {str(e)}")
        return False
    
    return True

def main():
    print("Logical Expression Processing Pipeline")
    print("=====================================")
    print()
    
    # Get the script directory for reference
    script_dir = os.path.dirname(os.path.abspath(__file__))
  
    print()
    
    # Step 1: Run the simplifier
    if not run_script("SYMPY SIMPLIFIER.py", "Logical Expression Simplifier"):
        print("\nPipeline stopped due to simplifier failure.")
        return
    
    # Step 2: Run the verifier
    if not run_script("VERIFIER.py", "Expression Equivalence Verifier"):
        print("\nPipeline stopped due to verifier failure.")
        return
    
    # Step 3: Run the natural language generator
    if not run_script("generate_nl_files.py", "Natural Language Generator"):
        print("\nPipeline stopped due to natural language generator failure.")
        return
    
    print(f"\n{'='*60}")
    print(" Pipeline completed successfully!")
    print(f"{'='*60}")
    print("\nResults:")
    print(f"- Simplified expressions: {os.path.join(script_dir, 'expressions.csv')}")
    print(f"- Verification results: {os.path.join(script_dir, 'verification_results.txt')}")
    print(f"- Natural language files: {os.path.join(script_dir, 'nl_outputs/')} directory")

if __name__ == "__main__":
    main() 