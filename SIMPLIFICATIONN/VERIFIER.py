from z3 import *
from z3 import unsat
import re
import os
import pandas as pd

def create_variable(var_name):
    """Create appropriate Z3 variable based on the variable name"""
    if var_name.startswith('IN_') or var_name in ['PLAY', 'REW', 'FF', 'EMPTY', 'DISCINSERT', 'EJECT']:
        # These look like constants/enum values
        return Int(var_name)
    elif any(var_name.startswith(prefix) for prefix in ['inp.', 'rtY.', 'rtDW.', 'dw.']):
        # Parts/properties of a struct - determine type based on usage
        if any(x in var_name for x in ['_sens', 'Eject']) or var_name.endswith('DiscInsert') or var_name.endswith('DiscEject'):
            # Sensor variables and specific input variables that are boolean
            return Bool(var_name)
        elif 'is_' in var_name:
            # State variables that hold enum values - these should be Int, not Bool
            return Int(var_name)
        elif var_name == 'inp.anomaly':
            # inp.anomaly is a boolean flag
            return Bool(var_name)
        elif var_name.startswith('inp.') and any(x in var_name for x in ['EnergyLow', 'Lmin', 'Lmax', 'ThetaZero', 'ThetaDotZero']):
            # These input variables are boolean flags based on their usage in logical expressions
            return Bool(var_name)
        elif any(x in var_name for x in ['Time', 'Counter', 'Tick', 'Duration', 'Wait', 'u1', 'u2']):
            # Time-related variables and input variables should be Int
            return Int(var_name)
        else:
            return Int(var_name)
    elif var_name in ['TWAIT', 'TIME', 'COUNTER', 'DURATION', 'u1', 'u2']:
        # Common time-related variables and input variables
        return Int(var_name)
    else:
        # Default to Int for variables that might be used in arithmetic
        return Int(var_name)

def tokenize_statement(statement):
    """Convert a statement string into tokens while preserving arithmetic operations"""
    # First, handle spaces around minus signs in numbers
    statement = re.sub(r'(\w+(?:\.\w+)*)\s*<\s*-\s*(\d+)', r'\1 < -\2', statement)
    statement = re.sub(r'(\w+(?:\.\w+)*)\s*>\s*-\s*(\d+)', r'\1 > -\2', statement)
    statement = re.sub(r'(\w+(?:\.\w+)*)\s*==\s*-\s*(\d+)', r'\1 == -\2', statement)
    statement = re.sub(r'(\w+(?:\.\w+)*)\s*!=\s*-\s*(\d+)', r'\1 != -\2', statement)
    statement = re.sub(r'(\w+(?:\.\w+)*)\s*>=\s*-\s*(\d+)', r'\1 >= -\2', statement)
    statement = re.sub(r'(\w+(?:\.\w+)*)\s*<=\s*-\s*(\d+)', r'\1 <= -\2', statement)
    
    # Handle negative numbers in comparisons
    statement = re.sub(r'-\s*(\d+)', r'-\1', statement)  # Remove spaces after minus sign
    
    # Mark arithmetic expressions to preserve them
    statement = re.sub(r'(\w+(?:\.\w+)*)\s*\+\s*(\d+)', r'ARITH_ADD_\1_\2', statement)
    statement = re.sub(r'(\w+(?:\.\w+)*)\s*-\s*(\d+)', r'ARITH_SUB_\1_\2', statement)
    
    # Handle variable-to-variable arithmetic
    statement = re.sub(r'(\w+(?:\.\w+)*)\s*\+\s*(\w+(?:\.\w+)*)', r'ARITH_ADD_VAR_\1_\2', statement)
    statement = re.sub(r'(\w+(?:\.\w+)*)\s*-\s*(\w+(?:\.\w+)*)', r'ARITH_SUB_VAR_\1_\2', statement)
    
    # Replace multi-character operators with unique placeholders
    replacements = {
        '&&': ' AND ',
        '||': ' OR ',
        '->': ' IMPLIES ',
        '==': ' EQUALS ',
        '!=': ' NOTEQUALS ',
        '>=': ' GEQ ',
        '<=': ' LEQ ',
        '!': ' NOT '
    }
    
    for op, placeholder in replacements.items():
        statement = statement.replace(op, placeholder)
    
    # Add spaces around remaining operators and parentheses
    statement = statement.replace('(', ' ( ').replace(')', ' ) ')
    
    # Handle > and < operators carefully to avoid splitting >= and <=
    # First replace >= and <= with placeholders
    statement = statement.replace('>=', ' GEQ ').replace('<=', ' LEQ ')
    # Then handle remaining > and <
    statement = statement.replace('>', ' > ').replace('<', ' < ')
    
    # Split into tokens and replace placeholders back
    tokens = statement.split()
    for i, token in enumerate(tokens):
        if token == 'AND': tokens[i] = '&&'
        elif token == 'OR': tokens[i] = '||'
        elif token == 'IMPLIES': tokens[i] = '->'
        elif token == 'EQUALS': tokens[i] = '=='
        elif token == 'NOTEQUALS': tokens[i] = '!='
        elif token == 'GEQ': tokens[i] = '>='
        elif token == 'LEQ': tokens[i] = '<='
        elif token == 'NOT': tokens[i] = '!'
        # Restore arithmetic expressions
        elif token.startswith('ARITH_ADD_'):
            parts = token.split('_', 2)
            if len(parts) >= 3:
                var_name = parts[2].rsplit('_', 1)[0]
                num = parts[2].rsplit('_', 1)[1]
                tokens[i] = f"{var_name}+{num}"
        elif token.startswith('ARITH_SUB_'):
            parts = token.split('_', 2)
            if len(parts) >= 3:
                var_name = parts[2].rsplit('_', 1)[0]
                num = parts[2].rsplit('_', 1)[1]
                tokens[i] = f"{var_name}-{num}"
        elif token.startswith('ARITH_ADD_VAR_'):
            parts = token.split('_', 3)
            if len(parts) >= 4:
                var1 = parts[3].split('_', 1)[0]
                var2 = parts[3].split('_', 1)[1]
                tokens[i] = f"{var1}+{var2}"
        elif token.startswith('ARITH_SUB_VAR_'):
            parts = token.split('_', 3)
            if len(parts) >= 4:
                var1 = parts[3].split('_', 1)[0]
                var2 = parts[3].split('_', 1)[1]
                tokens[i] = f"{var1}-{var2}"
    
    return tokens

def get_arith_expr(expr_str, variables, var_types=None):
    """Parse and create Z3 arithmetic expression"""
    # First handle negative numbers and variables
    if expr_str.startswith('-'):
        # Handle negative numbers
        if expr_str[1:].isdigit():
            return -int(expr_str[1:])
        # Handle negative variables
        var_name = expr_str[1:]
        if var_name not in variables:
            variables[var_name] = create_variable(var_name)
        return -variables[var_name]
    
    if '+' in expr_str:
        parts = expr_str.split('+')
        if len(parts) == 2:
            # Handle variable + constant
            if parts[1].strip().isdigit():
                var_name = parts[0].strip()
                if var_name not in variables:
                    variables[var_name] = create_variable(var_name)
                return variables[var_name] + int(parts[1])
            # Handle variable + variable
            else:
                var1 = parts[0].strip()
                var2 = parts[1].strip()
                if var1 not in variables:
                    variables[var1] = create_variable(var1)
                if var2 not in variables:
                    variables[var2] = create_variable(var2)
                return variables[var1] + variables[var2]
    elif '-' in expr_str:
        parts = expr_str.split('-')
        if len(parts) == 2:
            # Handle variable - constant
            if parts[1].strip().isdigit():
                var_name = parts[0].strip()
                if var_name not in variables:
                    variables[var_name] = create_variable(var_name)
                return variables[var_name] - int(parts[1])
            # Handle variable - variable
            else:
                var1 = parts[0].strip()
                var2 = parts[1].strip()
                if var1 not in variables:
                    variables[var1] = create_variable(var1)
                if var2 not in variables:
                    variables[var2] = create_variable(var2)
                return variables[var1] - variables[var2]
    elif expr_str.isdigit():
        return int(expr_str)
    else:
        # Handle single variable
        if expr_str not in variables:
            variables[expr_str] = create_variable(expr_str)
        return variables[expr_str]

def parse_expression(tokens, idx, variables, var_types=None):
    """Recursive descent parser for expressions"""
    if idx >= len(tokens):
        raise ValueError("Unexpected end of expression")
    
    # Parse a single term or subexpression
    if tokens[idx] == '(':  # If we see a parenthesis, parse the subexpression
        idx1, left_expr = parse_subexpression(tokens, idx + 1, variables, var_types)
        # If after the subexpression we have a comparison operator, parse as comparison
        if idx1 < len(tokens) and tokens[idx1] in ['==', '!=', '>', '<', '>=', '<=']:
            op = tokens[idx1]
            idx2 = idx1 + 1
            # Right side can also be a parenthesized subexpression
            if idx2 < len(tokens) and tokens[idx2] == '(':  # right side is parenthesized
                idx3, right_expr = parse_subexpression(tokens, idx2 + 1, variables, var_types)
            else:
                idx3, right_expr = parse_expression(tokens, idx2, variables, var_types)
            if op == '==':
                expr = left_expr == right_expr
            elif op == '!=':
                expr = left_expr != right_expr
            elif op == '>':
                expr = left_expr > right_expr
            elif op == '<':
                expr = left_expr < right_expr
            elif op == '>=':
                expr = left_expr >= right_expr
            elif op == '<=':
                expr = left_expr <= right_expr
            return idx3, expr
        else:
            return idx1, left_expr
    elif tokens[idx] == '!':
        # Parse a negation
        idx, term = parse_expression(tokens, idx + 1, variables, var_types)
        return idx, Not(term)
    else:
        # Parse a variable, constant, or comparison
        if idx + 2 < len(tokens) and tokens[idx + 1] in ['==', '!=', '>', '<', '>=', '<=']:
            # This is a comparison
            left_str = tokens[idx]
            op = tokens[idx + 1]
            right_str = tokens[idx + 2]
            
            # Handle arithmetic in comparisons
            if left_str.isdigit() or (left_str.startswith('-') and left_str[1:].isdigit()):
                left_val = int(left_str)
            else:
                left_val = get_arith_expr(left_str, variables, var_types)
                
            if right_str.isdigit() or (right_str.startswith('-') and right_str[1:].isdigit()):
                right_val = int(right_str)
            else:
                right_val = get_arith_expr(right_str, variables, var_types)
            
            if op == '==':
                expr = left_val == right_val
            elif op == '!=':
                expr = left_val != right_val
            elif op == '>':
                expr = left_val > right_val
            elif op == '<':
                expr = left_val < right_val
            elif op == '>=':
                expr = left_val >= right_val
            elif op == '<=':
                expr = left_val <= right_val
            
            return idx + 3, expr
        else:
            # This is a single variable or constant
            term = tokens[idx]
            if term.lower() == 'true':
                return idx + 1, True
            elif term.lower() == 'false':
                return idx + 1, False
            elif term.isdigit() or (term.startswith('-') and term[1:].isdigit()):
                return idx + 1, int(term)
            else:
                # Handle potential arithmetic
                if '+' in term or '-' in term:
                    return idx + 1, get_arith_expr(term, variables, var_types)
                else:
                    if term not in variables:
                        var_type = var_types.get(term, 'Bool') if var_types else 'Bool'
                        variables[term] = create_variable_with_type(term, var_type)
                    return idx + 1, variables[term]

def parse_subexpression(tokens, idx, variables, var_types=None):
    """Parse a subexpression within parentheses"""
    if idx >= len(tokens):
        raise ValueError("Unexpected end of expression")
    
    # Base case: empty parentheses
    if tokens[idx] == ')':
        return idx + 1, True
    
    # Parse the first term
    idx, left_expr = parse_expression(tokens, idx, variables, var_types)
    
    # If we've reached the end of the subexpression
    if idx >= len(tokens) or tokens[idx] == ')':
        return idx + 1, left_expr
    
    # Parse operator and right term
    while idx < len(tokens) and tokens[idx] != ')':
        op = tokens[idx]
        
        if op == '&&':
            idx, right_expr = parse_expression(tokens, idx + 1, variables, var_types)
            left_expr = And(left_expr, right_expr)
        elif op == '||':
            idx, right_expr = parse_expression(tokens, idx + 1, variables, var_types)
            left_expr = Or(left_expr, right_expr)
        elif op == '->':
            idx, right_expr = parse_expression(tokens, idx + 1, variables, var_types)
            left_expr = Implies(left_expr, right_expr)
        else:
            raise ValueError(f"Unexpected token: {op}")
    
    # Skip the closing parenthesis
    if idx < len(tokens) and tokens[idx] == ')':
        idx += 1
    
    return idx, left_expr

def parse_statement(statement):
    """Parse a logical statement and convert it to Z3 expression"""
    # Analyze variable types based on usage context
    var_types = analyze_variable_types(statement)
    
    # Add outer parentheses if not present
    if not statement.strip().startswith('('):
        statement = f"({statement})"
    
    # Ensure implications are properly parenthesized
    # Look for -> not inside parentheses and add parentheses
    balanced = 0
    for i, char in enumerate(statement):
        if char == '(':
            balanced += 1
        elif char == ')':
            balanced -= 1
        elif i < len(statement) - 1 and statement[i:i+2] == '->' and balanced == 0:
            # Found implication at top level, add parentheses
            statement = f"({statement[:i]}) -> ({statement[i+2:]})"
            break
    
    # Tokenize the statement
    tokens = tokenize_statement(statement)
    
    # Dictionary to store variables
    variables = {}
    
    # Parse the expression
    _, expr = parse_subexpression(tokens, 0, variables, var_types)
    
    return expr, variables

def verify_pair(original, simplified):
    """Verify if two logical statements are equivalent"""
    try:
        # Analyze variable types from both statements combined for better inference
        combined_statement = original + " " + simplified
        var_types = analyze_variable_types(combined_statement)
        
        # Parse both statements with the combined type information
        expr1, vars1 = parse_statement_with_types(original, var_types)
        expr2, vars2 = parse_statement_with_types(simplified, var_types)
        
        # Combine variables from both statements
        all_vars = {**vars1, **vars2}
        
        # Create Z3 solver
        s = Solver()
        
        # Check equivalence by testing if (expr1 <-> expr2) is always True
        # This is equivalent to checking if (expr1 != expr2) is unsatisfiable
        s.add(expr1 != expr2)
        
        result = s.check()
        
        if result == unsat:
            return True, None
        else:
            m = s.model()
            counterexample = {}
            for var in sorted(all_vars.keys()):
                if var in m:
                    counterexample[var] = m[all_vars[var]]
            return False, counterexample
            
    except Exception as e:
        return False, str(e)

def parse_statement_with_types(statement, var_types):
    """Parse a logical statement with pre-determined variable types"""
    # Add outer parentheses if not present
    if not statement.strip().startswith('('):
        statement = f"({statement})"
    
    # Ensure implications are properly parenthesized
    # Look for -> not inside parentheses and add parentheses
    balanced = 0
    for i, char in enumerate(statement):
        if char == '(':
            balanced += 1
        elif char == ')':
            balanced -= 1
        elif i < len(statement) - 1 and statement[i:i+2] == '->' and balanced == 0:
            # Found implication at top level, add parentheses
            statement = f"({statement[:i]}) -> ({statement[i+2:]})"
            break
    
    # Tokenize the statement
    tokens = tokenize_statement(statement)
    
    # Dictionary to store variables
    variables = {}
    
    # Parse the expression
    _, expr = parse_subexpression(tokens, 0, variables, var_types)
    
    return expr, variables

def analyze_variable_types(statement):
    """Analyze how variables are used in the statement to infer their types"""
    var_types = {}
    
    # Find all variables in the statement
    variables = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_.]*\b', statement)
    
    for var in set(variables):
        if var in ['true', 'false', 'True', 'False']:
            continue
        if var.startswith('IN_') or var in ['PLAY', 'REW', 'FF', 'EMPTY', 'DISCINSERT', 'EJECT']:
            var_types[var] = 'Int'  # Constants/enum values
            continue
            
        # Analyze usage context
        var_types[var] = 'Bool'  # Default to Bool
        
        # Check for arithmetic usage (suggests Int)
        if re.search(rf'\b{re.escape(var)}\s*[+\-]\s*\d+', statement) or \
           re.search(rf'\d+\s*[+\-]\s*{re.escape(var)}', statement) or \
           re.search(rf'\b{re.escape(var)}\s*[+\-]\s*\b[a-zA-Z_][a-zA-Z0-9_.]*\b', statement):
            var_types[var] = 'Int'
            
        # Check for comparison with numbers (could be Int)
        if re.search(rf'\b{re.escape(var)}\s*[><=!]+\s*-?\d+', statement) or \
           re.search(rf'-?\d+\s*[><=!]+\s*{re.escape(var)}', statement):
            var_types[var] = 'Int'
            
        # Check for comparison with enum-like values (suggests Int)
        if re.search(rf'\b{re.escape(var)}\s*[=!]+\s*IN_\w+', statement) or \
           re.search(rf'IN_\w+\s*[=!]+\s*{re.escape(var)}', statement):
            var_types[var] = 'Int'
    
    return var_types

def create_variable_with_type(var_name, var_type):
    """Create Z3 variable with specified type"""
    if var_type == 'Int':
        return Int(var_name)
    else:
        return Bool(var_name)



def main():
    print("\nLogical Statement Equivalence Verifier using Z3")
    print("===============================================")
    
    try:
        # Read the CSV file
        df = pd.read_csv(r'B:\SIMPLIFIERLOCAL\SIMPLIFICATIONN\expressions.csv')
        
        # Initialize counters
        total = len(df)
        equivalent = 0
        non_equivalent = 0
        errors = 0
        
        # Process each pair
        for idx, row in df.iterrows():
            # Show progress
            progress = (idx + 1) / total * 100
            print(f"\rVerifying pair {idx + 1}/{total} ({progress:.1f}%)", end="")
            
            is_equivalent, result = verify_pair(row['original'], row['simplified'])
            
            if is_equivalent:
                equivalent += 1
            else:
                if isinstance(result, dict):
                    print(f"\n\nNon-equivalent pair found at index {idx + 1}")
                    print("Original:", row['original'])
                    print("Simplified:", row['simplified'])
                    print("Counterexample:")
                    for var, val in result.items():
                        print(f"  {var} = {val}")
                    non_equivalent += 1
                else:
                    print(f"\n\nError at index {idx + 1}")
                    print("Original:", row['original'])
                    print("Simplified:", row['simplified'])
                    print(f"Error: {result}")
                    errors += 1
        
        # Print summary
        print("\n\nVerification Summary:")
        print("====================")
        print(f"Total pairs processed: {total}")
        print(f"Equivalent pairs: {equivalent}")
        print(f"Non-equivalent pairs: {non_equivalent}")
        print(f"Errors: {errors}")
        
        # Save results to a file
        with open('verification_results.txt', 'w') as f:
            f.write("Verification Summary:\n")
            f.write("====================\n")
            f.write(f"Total pairs processed: {total}\n")
            f.write(f"Equivalent pairs: {equivalent}\n")
            f.write(f"Non-equivalent pairs: {non_equivalent}\n")
            f.write(f"Errors: {errors}\n")
            
            # Add detailed error information
            if errors > 0 or non_equivalent > 0:
                f.write("\nDetailed Results:\n")
                f.write("================\n")
                for idx, row in df.iterrows():
                    is_equivalent, result = verify_pair(row['original'], row['simplified'])
                    if not is_equivalent:
                        f.write(f"\nPair {idx + 1}:\n")
                        f.write(f"Original: {row['original']}\n")
                        f.write(f"Simplified: {row['simplified']}\n")
                        if isinstance(result, dict):
                            f.write("Counterexample:\n")
                            for var, val in result.items():
                                f.write(f"  {var} = {val}\n")
                        else:
                            f.write(f"Error: {result}\n")
        
        print("\nResults have been saved to verification_results.txt")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("Please check your input files and try again.")

if __name__ == "__main__":
    main() 