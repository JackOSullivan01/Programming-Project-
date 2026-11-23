def investment_growth(monthly_returns, starting_amount=1000, monthly_contribution=100):
    balances = [starting_amount]

    for monthly_return in monthly_returns:
        new_balance = balances[-1] * (1 + monthly_return) + monthly_contribution
        balances.append(new_balance)

    return balances


print(investment_growth([0.05, -0.02]))
# [1000, 1150.0, 1227.0]