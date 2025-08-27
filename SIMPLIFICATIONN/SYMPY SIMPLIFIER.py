from sympy import symbols,Implies, simplify_logic, pretty, parse_expr, Eq
import re
# Import the formatter functionality
try:

    from .FORMATTER import simplify_logical_expression
except ImportError:
    from FORMATTER import simplify_logical_expression

def convert_to_sympy_syntax(expression):
    """
    Convert user-provided symbolic expression to valid SymPy syntax.
    Handles negations of inequalities by transforming them appropriately.
    
    Args:
        expression (str): The input expression with operators like &&, ||, !, ->, >, <
    
    Returns:
        str: Expression with SymPy-compatible operators
    """
    # Step 1: Normalize spaces
    expr = expression.strip()
    expr = re.sub(r'\s+', ' ', expr)  # Replace multiple spaces with single space
    expr = re.sub(r'\s*([&|!()<>])\s*', r'\1', expr)  # Remove spaces around operators and parentheses
    
    # Step 2: Process negations of inequality expressions before general operator replacement
    # Transform !(X > Y) to (X <= Y) and !(X < Y) to (X >= Y)
    # Use a loop to handle nested cases
    prev_expr = ""
    while prev_expr != expr:
        prev_expr = expr
        expr = re.sub(r'!\(([A-Z])\s*>\s*([A-Z])\)', r'(\1 <= \2)', expr)
        expr = re.sub(r'!\(([A-Z])\s*<\s*([A-Z])\)', r'(\1 >= \2)', expr)
    
    # Step 3: Replace operators
    expr = expr.replace('&&', '&')
    expr = expr.replace('||', '|')
    expr = expr.replace('->', '>>')
    
    # Handle NOT operator (!) carefully
    # First, ensure there's no space between ! and what it negates
    expr = re.sub(r'!\s*', '!', expr)
    # Then replace ! with ~
    expr = expr.replace('!', '~')
    
    return expr

def detect_arithmetic_expressions(expression):
    """
    Detect arithmetic expressions in the form of (X + Y == Z).
    Inequalities (X > Y), (X < Y) are now handled directly instead of being mapped to symbols.
    
    Args:
        expression (str): The input expression
    
    Returns:
        tuple: (modified_expression, symbol_map)
    """
    # Regular expression to match patterns like (H + 2 == D)
    eq_pattern = r'\(([A-Z])\s*\+\s*(\d+)\s*==\s*([A-Z])\)'
    
    # Dictionary to store the mappings
    symbol_map = {}
    counter = 0
    
    def replace_eq_match(match):
        nonlocal counter
        var1, num, var2 = match.groups()
        key = f"({var1} + {num} == {var2})"
        if key not in symbol_map:
            # Create a new symbol for this expression
            new_symbol = f"AE{counter}"  # AE for Arithmetic Expression
            symbol_map[key] = new_symbol
            counter += 1
        return symbol_map[key]
    
    # Replace equality matches in the expression
    modified_expr = re.sub(eq_pattern, replace_eq_match, expression)
    
    # Note: We no longer replace (X > Y) or (X < Y) patterns with symbols
    
    return modified_expr, symbol_map

def create_sympy_expression(expression):
    """
    Create a SymPy expression from the converted string, handling arithmetic operations.
    Now directly handles inequalities (X > Y) and their negations.
    
    Args:
        expression (str): The converted expression in SymPy syntax
    
    Returns:
        sympy expression: The parsed SymPy expression
    """
    try:
        # First, detect and replace arithmetic expressions
        modified_expr, arith_symbols = detect_arithmetic_expressions(expression)
        
        # Define all basic symbols (A through Z)
        A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z = symbols('A B C D E F G H I J K L M N O P Q R S T U V W X Y Z')
        
        # Create a dictionary of symbol mappings
        symbol_map = {
            'A': A, 'B': B, 'C': C, 'D': D, 'E': E, 'F': F, 'G': G, 'H': H,
            'I': I, 'J': J, 'K': K, 'L': L, 'M': M, 'N': N, 'O': O, 'P': P,
            'Q': Q, 'R': R, 'S': S, 'T': T, 'U': U, 'V': V, 'W': W, 'X': X,
            'Y': Y, 'Z': Z
        }
        
        # Pre-process negations of inequalities
        # For example, convert ~(X > Y) to (X <= Y)
        # Identify patterns like ~(A > B) and replace with (A <= B)
        modified_expr = re.sub(r'~\(([A-Z])\s*>\s*([A-Z])\)', r'(\1 <= \2)', modified_expr)
        # Identify patterns like ~(A < B) and replace with (A >= B)
        modified_expr = re.sub(r'~\(([A-Z])\s*<\s*([A-Z])\)', r'(\1 >= \2)', modified_expr)
        
        # Check if expression contains ">>" (implication)
        if ">>" in modified_expr:
            # Split at the implication operator
            parts = modified_expr.split(">>")
            if len(parts) == 2:
                # Parse each part separately
                antecedent = parse_expr(parts[0], local_dict=symbol_map)
                consequent = parse_expr(parts[1], local_dict=symbol_map)
                
                # Create an Implies expression
                return Implies(antecedent, consequent)
        
        # Process special arithmetic symbols (equations)
        for expr_key, symbol_name in arith_symbols.items():
            if expr_key.startswith("(") and " == " in expr_key:
                # Handle equality expressions like (X + 2 == Y)
                match = re.match(r'\(([A-Z])\s*\+\s*(\d+)\s*==\s*([A-Z])\)', expr_key)
                if match:
                    var1, num, var2 = match.groups()
                    # Create Eq expression and associate it with the symbol
                    eq_expr = Eq(symbol_map[var1] + int(num), symbol_map[var2])
                    symbol_map[symbol_name] = eq_expr
            else:
                # For other expressions, create a regular symbol
                symbol_map[symbol_name] = symbols(symbol_name)
        
        # Parse the expression normally
        return parse_expr(modified_expr, local_dict=symbol_map)
    
    except Exception as e:
        import traceback
        print(f"Error creating SymPy expression: {e}")
        print(traceback.format_exc())
        raise

def simplify_antecedent(expression):
    """
    Simplify only the antecedent of an implication while preserving the structure.
    
    Args:
        expression: The SymPy expression containing an implication
    
    Returns:
        sympy expression: The expression with simplified antecedent
    """
    if not isinstance(expression, Implies):
        raise ValueError("Expression must be an implication")
    
    # Get antecedent and consequent
    antecedent = expression.args[0]
    consequent = expression.args[1]
    
    # Simplify only the antecedent
    simplified_antecedent = simplify_logic(antecedent)
    
    # Rebuild the implication with simplified antecedent
    return Implies(simplified_antecedent, consequent)

def simplify_converted_expression(converted_expr):
    """
    Parse and simplify a converted expression.
    Now handles inequalities directly without special symbol mapping.
    
    Args:
        converted_expr (str): The expression in SymPy syntax
    
    Returns:
        tuple: (parsed_expression, simplified_expression)
    """
    try:
        # Log the input for debugging
        print("\nInput expression for simplification:", converted_expr)
        
        # Parse the string expression into a SymPy expression
        parsed_expr = create_sympy_expression(converted_expr)
        
        # Print the parsed expression for debugging
        print("\nSuccessfully parsed expression:")
        print(parsed_expr)
        
        # Check if we have an implication
        if isinstance(parsed_expr, Implies):
            # Simplify only the antecedent
            simplified = simplify_antecedent(parsed_expr)
            return parsed_expr, simplified
        else:
            # If not an implication, just simplify the whole expression
            simplified = simplify_logic(parsed_expr)
            print("\nExpression is not an implication. Simplified whole expression.")
            return parsed_expr, simplified
            
    except Exception as e:
        import traceback
        print(f"Error parsing/simplifying expression: {e}")
        print(traceback.format_exc())
        return None, None


def convert_from_sympy_syntax(expression):
    """
    Convert SymPy expression back to original format with &&, ||, !, and -> operators.
    
    Args:
        expression (str): The SymPy expression
    
    Returns:
        str: Expression with original operators
    """
    # Replace SymPy operators with original format
    expr = str(expression)
    expr = expr.replace('&', '&&')
    expr = expr.replace('|', '||')
    expr = expr.replace('~', '!')
    expr = expr.replace('>>', '->')
    
    return expr

def format_logical_expression(expression):
    """
    Convert SymPy logical expression to a more readable format.
    Specifically handles Implies() expressions to use arrow notation.
    
    Args:
        expression (str): The SymPy expression string
    
    Returns:
        str: Formatted expression with proper notation
    """
    expr = str(expression)
    
    # Handle Implies() function format
    if expr.startswith('Implies(') and expr.endswith(')'):
        # Extract the content inside Implies()
        inner_content = expr[8:-1]  # Remove 'Implies(' and the last ')'
        
        # Find the position of the comma that separates antecedent and consequent
        # This is tricky because we need to account for nested parentheses
        paren_count = 0
        comma_pos = -1
        
        for i, char in enumerate(inner_content):
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                comma_pos = i
                break
        
        if comma_pos != -1:
            antecedent = inner_content[:comma_pos].strip()
            consequent = inner_content[comma_pos+1:].strip()
            
            # Convert operators in both parts
            antecedent = convert_from_sympy_syntax(antecedent)
            consequent = convert_from_sympy_syntax(consequent)
            
            # Format to arrow notation
            return f"({antecedent}) -> {consequent}"
    
    # If not an Implies() expression, just use standard conversion
    return convert_from_sympy_syntax(expr)

def get_variable_mappings(file_path='simplified_expression.txt'):
    """
    Read variable mappings from the specified file.
    
    Args:
        file_path (str): Path to the file containing variable mappings
    
    Returns:
        dict: Dictionary of variable mappings {variable: original_expression}
    """
    mappings = {}
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find the variable mappings section
        if 'Variable Mappings:' in content:
            mapping_section = content.split('Variable Mappings:')[1].strip()
            
            # Parse each mapping line
            for line in mapping_section.split('\n'):
                if '->' in line:
                    var, expression = line.split('->', 1)
                    var = var.strip()
                    expression = expression.strip().strip('"')
                    mappings[var] = expression
        
        return mappings
    except Exception as e:
        print(f"Error reading variable mappings: {e}")
        return {}

def replace_variables_with_originals(simplified_expr, mappings):
    """
    Replace simplified variables with their original expressions.
    Also handles transformation of negated inequalities and recursive replacement.
    
    Args:
        simplified_expr (str): The simplified expression with variables
        mappings (dict): Dictionary of variable mappings
    
    Returns:
        str: Expression with variables replaced by original expressions
    """
    result = simplified_expr
    
    # Process inequality negations in the simplified expression before variable replacement
    # Transform patterns like !(X > Y) to (X <= Y) or (X < Y)
    result = re.sub(r'!\s*\(\s*([^<>]+)\s*>\s*([^<>]+)\s*\)', r'(\1 <= \2)', result)
    result = re.sub(r'!\s*\(\s*([^<>]+)\s*<\s*([^<>]+)\s*\)', r'(\1 >= \2)', result)
    
    # Also handle the double negation case: !(!(X > Y)) should go back to (X > Y)
    result = re.sub(r'!\s*\(\s*!\s*\(\s*([^<>]+)\s*>\s*([^<>]+)\s*\)\s*\)', r'(\1 > \2)', result)
    result = re.sub(r'!\s*\(\s*!\s*\(\s*([^<>]+)\s*<\s*([^<>]+)\s*\)\s*\)', r'(\1 < \2)', result)
    
    # Create a function to recursively expand mappings
    def expand_mapping(value, visited=None):
        """Recursively expand a mapping value by replacing any variables it contains."""
        if visited is None:
            visited = set()
        
        # Avoid infinite recursion
        if value in visited:
            return value
        visited.add(value)
        
        expanded = value
        # Sort keys by length in descending order to handle longer variables first
        sorted_vars = sorted(mappings.keys(), key=len, reverse=True)
        
        for var in sorted_vars:
            if var != value:  # Don't replace the variable with itself
                pattern = r'\b' + re.escape(var) + r'\b'
                if re.search(pattern, expanded):
                    # Recursively expand the mapping for this variable
                    expanded_mapping = expand_mapping(mappings[var], visited.copy())
                    expanded = re.sub(pattern, expanded_mapping, expanded)
        
        return expanded
    
    # Create expanded mappings
    expanded_mappings = {}
    for var, value in mappings.items():
        expanded_mappings[var] = expand_mapping(value)
    
    # Sort keys by length in descending order to handle longer variables first
    # This prevents partial replacements of variables
    sorted_vars = sorted(expanded_mappings.keys(), key=len, reverse=True)
    
    # First pass: identify relational expressions to protect them from excessive parentheses
    relational_matches = []
    relational_patterns = [
        r'([A-Za-z0-9_.]+)\s*([<>=!]+)\s*([A-Za-z0-9_.]+)',  # Simple relations: A < B
        r'([A-Za-z0-9_.]+)\s*([<>=!]+)\s*([A-Za-z0-9_.]+\s*[-+*/]\s*[A-Za-z0-9_.]+)'  # Relations with operations: A < B - C
    ]
    
    for pattern in relational_patterns:
        for match in re.finditer(pattern, result):
            relational_matches.append((match.start(), match.end(), match.group()))
    
    # Sort matches by start position in reverse to replace from end to start
    relational_matches.sort(reverse=True)
    
    # Replace variables within the relational expressions first
    for start, end, match_text in relational_matches:
        # Find and replace variables in the match, but without adding parentheses
        modified_match = match_text
        for var in sorted_vars:
            pattern = r'\b' + re.escape(var) + r'\b'
            modified_match = re.sub(pattern, expanded_mappings[var], modified_match)
        
        # Update the result with the modified relational expression
        result = result[:start] + modified_match + result[end:]
    
    # Second pass: replace remaining variables with parentheses as before
    for var in sorted_vars:
        pattern = r'\b' + re.escape(var) + r'\b'
        # Only add parentheses if the expanded mapping contains operators or spaces
        expanded_value = expanded_mappings[var]
        if any(op in expanded_value for op in ['&&', '||', '==', '!=', '>=', '<=', '>', '<', '+', '-', '*', '/', ' ']):
            result = re.sub(pattern, f"({expanded_value})", result)
        else:
            result = re.sub(pattern, expanded_value, result)
    
    return result

def save_to_csv(original_expr, simplified_expr, csv_file="B:\SIMPLIFIERLOCAL\SIMPLIFICATIONN\expressions.csv"):
    """
    Save original and simplified expressions to a CSV file.
    
    Args:
        original_expr (str): The original expression
        simplified_expr (str): The simplified expression
        csv_file (str): Path to the CSV file
    """
    import csv
    import os
    
    file_exists = os.path.isfile(csv_file)
    
    with open(csv_file, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['original', 'simplified']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write headers if file doesn't exist
        if not file_exists:
            writer.writeheader()
        
        # Write the data
        writer.writerow({
            'original': original_expr,
            'simplified': simplified_expr
        })
    
    return csv_file

def simplification():
    # Example expression from the user
    test_expr = input("Enter the expression: ")
    print("Original:", test_expr)
    
    try:
        # First, use the formatter to map complex variables to simple ones
        simplified_expr, mappings = simplify_logical_expression(test_expr)
        print("\nExpression with simplified variables:")
        print(simplified_expr)
        print(mappings)
        
        # Save mappings to file
        output_file = "SIMPLIFICATIONN/simplified_expression.txt"
        with open(output_file, "w", encoding='utf-8') as f:
            f.write("logical statement: " + test_expr + "\n\n")
            f.write("simplified statement : " + simplified_expr + "\n\n")
            f.write(mappings)
        
        # Now use SymPy to simplify the logical structure
        # Check if we have an implication
        if "->" in simplified_expr:
            print("\nProcessing implication...")
        else:
            print("\nProcessing regular logical expression...")
        
        # Convert to SymPy syntax
        converted = convert_to_sympy_syntax(simplified_expr)
        print("Converted to SymPy syntax:", converted)
        
        # Parse and simplify using our function
        parsed, simplified = simplify_converted_expression(converted)
        if parsed is not None:
            print("\nParsed expression:")
            print(pretty(parsed))
            print("\nSimplified expression:")
            print(pretty(simplified))
            
            # Use the new format_logical_expression function
            formatted_expr = format_logical_expression(simplified)
            print("\nFormatted logical expression:")
            print(formatted_expr)
            
            # Get variable mappings and replace variables with originals
            if mappings:
                # Extract mappings from the string
                mapping_dict = {}
                for line in mappings.split('\n'):
                    if '->' in line:
                        var, expression = line.split('->', 1)
                        var = var.strip()
                        expression = expression.strip().strip('"')
                        mapping_dict[var] = expression
                
                final_expression = replace_variables_with_originals(formatted_expr, mapping_dict)
                print("\nExpression with original variables:")
                print(final_expression)
                
                # Update the file with the final result
                with open(output_file, "a", encoding='utf-8') as f:
                    f.write("\nFinal simplified expression:\n" + final_expression)
                
                # Save to CSV file using the helper function
                csv_file = save_to_csv(test_expr, final_expression)
                print(f"\nResults saved to CSV file: {csv_file}")
    
    except Exception as e:
        import traceback
        print(f"\nError in simplification function: {e}")
        print(traceback.format_exc())

def batch_simplification(input_file):
    """
    Process multiple logical expressions from an input file.
    Each line in the file should contain one expression.
    
    Args:
        input_file (str): Path to the input file containing expressions
    """
    print(f"Processing expressions from {input_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            expressions = f.readlines()
        
        # Filter out empty lines and comments
        expressions = [expr.strip() for expr in expressions if expr.strip() and not expr.strip().startswith('#')]
        
        if not expressions:
            print("No expressions found in the input file.")
            return
        
        print(f"Found {len(expressions)} expressions to process.")
        
        for i, expr in enumerate(expressions, 1):
            print(f"\n[{i}/{len(expressions)}] Processing: {expr}")
            try:
                # First, use the formatter to map complex variables to simple ones
                simplified_expr, mappings = simplify_logical_expression(expr)
                
                # Convert to SymPy syntax
                converted = convert_to_sympy_syntax(simplified_expr)
                
                # Parse and simplify using our function
                parsed, simplified = simplify_converted_expression(converted)
                
                if parsed is not None:
                    # Format the simplified expression
                    formatted_expr = format_logical_expression(simplified)
                    
                    # Extract mappings from the string
                    mapping_dict = {}
                    for line in mappings.split('\n'):
                        if '->' in line:
                            var, expression = line.split('->', 1)
                            var = var.strip()
                            expression = expression.strip().strip('"')
                            mapping_dict[var] = expression
                    
                    # Replace variables with originals
                    final_expression = replace_variables_with_originals(formatted_expr, mapping_dict)
                    
                    # Save to CSV file
                    save_to_csv(expr, final_expression)
                    print(f"Simplified: {final_expression}")
                else:
                    print(f"Failed to parse expression: {expr}")
            
            except Exception as e:
                print(f"Error processing expression {i}: {e}")
        
        print("\nBatch processing completed. Results saved to CSV file.")
    
    except Exception as e:
        import traceback
        print(f"Error in batch processing: {e}")
        print(traceback.format_exc())

def test_inequality_handling():
    """
    Test function to verify the enhanced inequality handling.
    """
    print("Testing inequality handling functionality...\n")
    
    test_cases = [
        "(X > Y) && (A < B)",
        "!(X > Y) && (A < B)", 
        "(A && B) || !(X > Y)",
        "!(!(X > Y))",
        "(X > Y) -> (A < B)",
        "!(X > Y) -> !(A < B)"
    ]
    
    for test_expr in test_cases:
        print(f"\n\nTesting: {test_expr}")
        
        # Convert to SymPy syntax with inequality handling
        converted = convert_to_sympy_syntax(test_expr)
        print("Converted to SymPy syntax:", converted)
        
        # Parse and simplify
        parsed, simplified = simplify_converted_expression(converted)
        if parsed is not None:
            print("\nParsed expression:")
            print(pretty(parsed))
            print("\nSimplified expression:")
            print(pretty(simplified))
            
            # Format the result
            formatted_expr = format_logical_expression(simplified)
            print("\nFormatted logical expression:")
            print(formatted_expr)

if __name__ == "__main__":
    import sys
    
    # Automatically run batch simplification with the specified file
    spec_file = "B:\SIMPLIFIERLOCAL\SIMPLIFICATIONN\SPECS\spec.txt"
    batch_simplification(spec_file)
