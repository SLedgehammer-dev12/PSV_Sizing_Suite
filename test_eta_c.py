import math
from scipy.optimize import minimize_scalar

w = 0.641265476511077

def G_func(eta):
    # Mass flux term to maximize
    num = w * math.log(1.0 / eta) + (w - 1.0) * (1.0 - eta)
    den = (w / eta + 1.0 - w) ** 2
    if den == 0 or num < 0:
        return 1e9 # return large positive to avoid selection in minimize
    return - (num / den) # negative for minimization

res = minimize_scalar(G_func, bounds=(0.1, 0.99), method='bounded')
eta_c = res.x
print(f"Numerical eta_c: {eta_c:.8f}")

# Compare with Excel E values
# Excel used an implicit equation for E. E = hc^2 + ...
# Let's check: E = hc^2 + (omega - 2)*hc + 1 - omega ?
E_excel = 0.55**2 + (w - 1) - 2*w*0.55 # etc
