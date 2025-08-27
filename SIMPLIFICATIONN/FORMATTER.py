def simplify_logical_expression(expression):
    var_map = {}
    reverse_map = {}  
    current_letter = 'A'
    
    def normalize_variable(var):
        var = var.strip()
        prefixes = ['dw.', 'rtDW.', 'inp.']
        for prefix in prefixes:
            if var.startswith(prefix):
                return var[len(prefix):]
        return var
    
    def extract_variables(expr):
        import re
        # Fix issues with spaces in variable names first
        expr = expr.replace("dw.is_ ModeManager", "dw.is_ModeManager")
        expr = expr.replace("IN_ NO_ACTIVE_CHILD", "IN_NO_ACTIVE_CHILD")
        
        # Find complex expressions in parentheses with operators and comparisons
        complex_pattern = r'\([^()]*(?:\+|-|\*|\/|==|!=|>=|<=|>|<)[^()]*\)'
        complex_matches = re.findall(complex_pattern, expr)
        
        # New pattern to match relational operations (< and >)
        relational_pattern = r'([a-zA-Z][a-zA-Z0-9._]*)\s*([<>])\s*([a-zA-Z0-9._\s\+\-\*\/]+)'
        
        # Process each complex match to extract operands of relational operators
        for complex_match in complex_matches.copy():
            relational_matches = re.findall(relational_pattern, complex_match)
            for left_operand, operator, right_operand in relational_matches:
                # Add both operands to matches separately
                if left_operand.strip() not in complex_matches:
                    complex_matches.append(left_operand.strip())
                if right_operand.strip() not in complex_matches:
                    complex_matches.append(right_operand.strip())
        
        # Process numeric comparisons separately (e.g., "19 > dw.temporalCounter_i1")
        numeric_comparison_pattern = r'\((\d+)\s*(?:[<>]=?|==|!=)\s*([a-zA-Z][a-zA-Z0-9._]*)\)'
        for complex_match in complex_matches.copy():
            numeric_matches = re.findall(numeric_comparison_pattern, complex_match)
            if numeric_matches:
                for num, var in numeric_matches:
                    # Add the variable separately to matches
                    if var not in complex_matches:
                        complex_matches.append(var)
                    # Add the number separately (optional, depends if you want numbers to get mapped)
                    if num not in complex_matches:
                        complex_matches.append(num)
        
        # Find regular comparison expressions and variables
        pattern = r'(?:[a-zA-Z][a-zA-Z0-9._]*\s*==\s*[a-zA-Z][a-zA-Z0-9._]*)|(?<!\w)[a-zA-Z][a-zA-Z0-9._]*(?!\s*==)'
        matches = []
        
        # Add complex expressions first
        matches.extend(complex_matches)
        
        # Store positions of complex expressions to exclude them from regular variable extraction
        excluded_ranges = []
        for complex_match in complex_matches:
            for m in re.finditer(re.escape(complex_match), expr):
                excluded_ranges.append((m.start(), m.end()))
        
        # Process rest of expression for simple variables and comparisons
        for match in re.finditer(pattern, expr):
            # Only add if it's not part of a complex expression
            start, end = match.span()
            if not any(start >= ex_start and end <= ex_end for ex_start, ex_end in excluded_ranges):
                # Only add if it's a complete expression
                if start == 0 or not expr[start-1].isalnum():
                    if end == len(expr) or not expr[end].isalnum():
                        var = match.group(0)
                        # Skip if it's just a prefix or a partial match
                        if not (var.endswith('_') and var.count('.') == 1):
                            # Skip if it's just a part of a comparison
                            if '==' in var or not any('==' in m for m in matches if m.startswith(var) or var.startswith(m)):
                                matches.append(var)
        return sorted(set(matches))
    
    # Replace variables in the expression
    # Fix issues with spaces before using the expression
    expression = expression.replace("dw.is_ ModeManager", "dw.is_ModeManager")
    expression = expression.replace("IN_ NO_ACTIVE_CHILD", "IN_NO_ACTIVE_CHILD")
    
    def replace_variable(match):
        nonlocal current_letter
        var = match.group(0).strip()
        
        # Skip if it's just a prefix
        if var.endswith('_') and var.count('.') == 1:
            return var
            
        # Skip if it's a partial match of a comparison
        if '==' not in var and any('==' in m for m in var_map.keys() if m.startswith(var) or var.startswith(m)):
            return var
        
        # Handle numeric values
        if var.isdigit():
            if var in var_map:
                return var_map[var]
            var_map[var] = current_letter
            reverse_map[current_letter] = var
            current_letter = chr(ord(current_letter) + 1)
            return var_map[var]
        
        # If it's already mapped, return the mapping
        if var in var_map:
            return var_map[var]
        
        # If var is a single letter that might be a previous mapping, skip it
        if len(var) == 1 and 'A' <= var <= 'Z' and var in reverse_map:
            return var
            
        # Create new mapping
        var_map[var] = current_letter
        reverse_map[current_letter] = var
        current_letter = chr(ord(current_letter) + 1)
        return var_map[var]
    
    def process_relational_operators(expr):
        import re
        
        # Identify relational operations, capturing both operands
        rel_pattern = r'([a-zA-Z0-9._]+)\s*([<>])\s*([a-zA-Z0-9._\s\+\-\*\/]+)'
        
        def replace_relational(match):
            left_operand, operator, right_operand = match.groups()
            left_operand = left_operand.strip()
            right_operand = right_operand.strip()
            
            # Map left operand
            if left_operand not in var_map and not (len(left_operand) == 1 and 'A' <= left_operand <= 'Z' and left_operand in reverse_map):
                nonlocal current_letter
                var_map[left_operand] = current_letter
                reverse_map[current_letter] = left_operand
                current_letter = chr(ord(current_letter) + 1)
            
            # Map right operand
            if right_operand not in var_map and not (len(right_operand) == 1 and 'A' <= right_operand <= 'Z' and right_operand in reverse_map):
                var_map[right_operand] = current_letter
                reverse_map[current_letter] = right_operand
                current_letter = chr(ord(current_letter) + 1)
            
            left_map = var_map.get(left_operand, left_operand)
            right_map = var_map.get(right_operand, right_operand)
            
            return f"{left_map} {operator} {right_map}"
        
        return re.sub(rel_pattern, replace_relational, expr)
    
    if '->' in expression:
        parts = expression.split('->')
        left_part = parts[0].strip()
        right_part = parts[1].strip()
    else:
        left_part = expression
        right_part = ""
    
    # Extract all variables first
    all_variables = extract_variables(expression)
    
    # Create mappings for all variables
    for var in all_variables:
        if var not in var_map:
            # Check if var is a single letter that might already be used as a mapping
            if len(var) == 1 and 'A' <= var <= 'Z' and var in reverse_map:
                continue
                
            var_map[var] = current_letter
            reverse_map[current_letter] = var
            current_letter = chr(ord(current_letter) + 1)
    
    # Replace variables in the expression
    import re
    # First replace complex expressions in parentheses
    complex_pattern = r'\([^()]*(?:\+|-|\*|\/|==|!=|>=|<=|>|<)[^()]*\)'
    
    # Process numeric comparisons separately
    numeric_comparison_pattern = r'\((\d+)\s*(?:[<>]=?|==|!=)\s*([a-zA-Z][a-zA-Z0-9._]*)\)'
    
    # Special processing for relational operators
    simplified_left = process_relational_operators(left_part)
    
    # Replace other complex expressions
    for complex_match in re.finditer(complex_pattern, simplified_left):
        complex_expr = complex_match.group(0)
        # Skip if it contains a relational operator as we've already processed those
        if not re.search(r'[<>]', complex_expr):
            numeric_matches = re.findall(numeric_comparison_pattern, complex_expr)
            
            if numeric_matches:
                # Handle numeric comparison by replacing parts individually
                modified_expr = complex_expr
                for num, var in numeric_matches:
                    if num in var_map:
                        modified_expr = modified_expr.replace(num, var_map[num])
                    if var in var_map:
                        modified_expr = modified_expr.replace(var, var_map[var])
                simplified_left = simplified_left.replace(complex_expr, modified_expr)
            elif complex_expr in var_map:
                simplified_left = simplified_left.replace(complex_expr, var_map[complex_expr])
    
    # Then replace simple variables and comparisons
    pattern = r'(?:[a-zA-Z][a-zA-Z0-9._]*\s*==\s*[a-zA-Z][a-zA-Z0-9._]*)|(?<!\w)[a-zA-Z][a-zA-Z0-9._]*(?!\s*==)|(?<!\w)\d+(?!\w)'
    simplified_left = re.sub(pattern, replace_variable, simplified_left)
    
    if right_part:
        # Process relational operators in right part
        simplified_right = process_relational_operators(right_part)
        
        # Replace complex expressions first in right part
        for complex_match in re.finditer(complex_pattern, simplified_right):
            complex_expr = complex_match.group(0)
            # Skip if it contains a relational operator as we've already processed those
            if not re.search(r'[<>]', complex_expr):
                numeric_matches = re.findall(numeric_comparison_pattern, complex_expr)
                
                if numeric_matches:
                    # Handle numeric comparison by replacing parts individually
                    modified_expr = complex_expr
                    for num, var in numeric_matches:
                        if num in var_map:
                            modified_expr = modified_expr.replace(num, var_map[num])
                        if var in var_map:
                            modified_expr = modified_expr.replace(var, var_map[var])
                    simplified_right = simplified_right.replace(complex_expr, modified_expr)
                elif complex_expr in var_map:
                    simplified_right = simplified_right.replace(complex_expr, var_map[complex_expr])
                    
        # Then replace simple variables and comparisons
        simplified_right = re.sub(pattern, replace_variable, simplified_right)
        simplified = f"{simplified_left} -> {simplified_right}"
    else:
        simplified = simplified_left
    
    mapping_explanation = "\nVariable Mappings:\n"
    
    # Directly map all letters to original expressions
    original_mappings = {}
    for letter, value in sorted(reverse_map.items()):
        # If the value is a single letter, find its original value
        original_value = value
        while len(original_value) == 1 and 'A' <= original_value <= 'Z' and original_value in reverse_map:
            original_value = reverse_map[original_value]
        
        original_mappings[letter] = original_value
    
    for letter in sorted(original_mappings.keys()):
        mapping_explanation += f"{letter} -> \"{original_mappings[letter]}\"\n"
    
    return simplified, mapping_explanation

def main():
    print("Logical Expression Simplifier")
    print("-----------------------------")
    print("\nEnter your logical expression:")
    
    try:
        expression = input().strip()
        if not expression:
            print("Error: Empty expression")
            return
            
        simplified, mappings = simplify_logical_expression(expression)
        
        print("\nResults:")
        print("logical statement:", expression)
        print("simplified statement :", simplified)
        print(mappings)
        
        output_file = r"B:\SIMPLIFIERLOCAL\SIMPLIFICATIONN\simplified_expression.txt"
        with open(output_file, "w", encoding='utf-8') as f:
            f.write("logical statement: " + expression + "\n\n")
            f.write("simplified statement : " + simplified + "\n\n")
            f.write(mappings)
            
        print(f"\nOutput has been saved to '{output_file}'")
        
    except Exception as e:
        print(f"Error processing expression: {str(e)}")

if __name__ == "__main__":
    main()
