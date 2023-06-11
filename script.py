import json

def calculate_total_tax_prior_brackets(brackets):
    total_tax = 0
    for i in range(len(brackets)):
        income_min = brackets[i]['income_min']
        income_max = brackets[i]['income_max']
        rate = brackets[i]['rate']

        if income_max is None:
            break
        
        taxable_amount = min(income_max, taxable_income) - income_min
        tax_in_bracket = taxable_amount * rate / 100
        total_tax += tax_in_bracket
    
    return round(total_tax, 2)

# Load tax brackets from JSON file
with open('tax_brackets.json', 'r') as file:
    data = json.load(file)

    tax_brackets = data['tax_brackets']
    standard_deduction_single = data['standard_deduction']['single']

    income = 50000  # Example income amount
    taxable_income = income - standard_deduction_single

    for bracket in tax_brackets:
        bracket['total_tax_prior_brackets'] = calculate_total_tax_prior_brackets(tax_brackets)

# Print updated tax brackets JSON with total tax for prior brackets
    print(json.dumps(data, indent=2))
