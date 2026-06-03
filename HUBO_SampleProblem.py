import json
import random
import math

# ============================================================
# LOAD DATASET
# ============================================================

with open("dataset.json", "r") as f:
    data = json.load(f)

supply_sites   = data["supply_sites"]
demand_sites   = data["demand_sites"]
inventory      = data["inventory"]
demand         = data["demand"]
allowed_routes = data["allowed_routes"]

transport_cost = {
    tuple(eval(k)): v
    for k, v in data["transport_cost"].items()
}

# ============================================================
# VARIABLE CREATION
# ============================================================

variables = {}

for s in supply_sites:
    if inventory[s] == 0:
        continue
    for d in allowed_routes[s]:
        if demand[d] == 0:
            continue
        variables[f"ship_{s}_{d}"] = 0

# Hub and carrier activation variables
variables["hub_NA"]      = 0
variables["carrier_AIR"] = 0

# ============================================================
# HUBO TERM STORAGE
# ============================================================

hubo_terms = []

# ============================================================
# LINEAR TRANSPORT COST TERMS
# ============================================================

for (s, d), cost in transport_cost.items():
    var = f"ship_{s}_{d}"
    if var in variables:
        hubo_terms.append((cost, [var]))

# ============================================================
# INVENTORY CONSTRAINTS  (P1)
# ============================================================

P1 = 100

for s in supply_sites:
    outgoing_vars = [
        f"ship_{s}_{d}"
        for d in allowed_routes[s]
        if f"ship_{s}_{d}" in variables
    ]

    for var in outgoing_vars:
        hubo_terms.append((-2 * P1 * inventory[s], [var]))

    for i in range(len(outgoing_vars)):
        hubo_terms.append((P1, [outgoing_vars[i]]))
        for j in range(i + 1, len(outgoing_vars)):
            hubo_terms.append((2 * P1, [outgoing_vars[i], outgoing_vars[j]]))

# ============================================================
# DEMAND CONSTRAINTS  (P2)
# ============================================================

P2 = 100

for d in demand_sites:
    incoming_vars = [
        f"ship_{s}_{d}"
        for s in supply_sites
        if d in allowed_routes[s] and f"ship_{s}_{d}" in variables
    ]

    for var in incoming_vars:
        hubo_terms.append((-2 * P2 * demand[d], [var]))

    for i in range(len(incoming_vars)):
        hubo_terms.append((P2, [incoming_vars[i]]))
        for j in range(i + 1, len(incoming_vars)):
            hubo_terms.append((2 * P2, [incoming_vars[i], incoming_vars[j]]))

# ============================================================
# CUBIC HUBO INTERACTION
# ============================================================

cubic_vars = ["ship_SUP1_DEM1", "hub_NA", "carrier_AIR"]

if all(v in variables for v in cubic_vars):
    hubo_terms.append((-500, cubic_vars))
else:
    missing = [v for v in cubic_vars if v not in variables]
    print(f"Warning: Skipping cubic term — missing variables: {missing}")

# ============================================================
# ENERGY FUNCTION
# ============================================================

def compute_energy(state, terms):
    energy = 0
    for coeff, vars_in_term in terms:
        product = 1
        for var in vars_in_term:
            product *= state[var]
        energy += coeff * product
    return energy

# ============================================================
# RANDOM INITIALIZATION
# ============================================================

state = {var: random.randint(0, 1) for var in variables}

# ============================================================
# SIMULATED ANNEALING
# ============================================================

temperature  = 10.0
cooling_rate = 0.995
steps        = 100000

best_state  = state.copy()
best_energy = compute_energy(state, hubo_terms)

for step in range(steps):

    candidate          = state.copy()
    flip_var           = random.choice(list(candidate.keys()))
    candidate[flip_var] ^= 1

    current_energy   = compute_energy(state,     hubo_terms)
    candidate_energy = compute_energy(candidate, hubo_terms)
    delta            = candidate_energy - current_energy

    if delta < 0:
        state = candidate
    else:
        if random.random() < math.exp(-delta / temperature):
            state = candidate

    if candidate_energy < best_energy:
        best_energy = candidate_energy
        best_state  = candidate.copy()

    temperature *= cooling_rate

# ============================================================
# SIMULATED ANNEALING RESULTS
# ============================================================

print("\n" + "=" * 52)
print("  SIMULATED ANNEALING RESULTS")
print("=" * 52)
print(f"  Best HUBO Energy : {best_energy}")
print("\n  Active Shipments :")
for var, value in best_state.items():
    if value == 1:
        print(f"    {var}")

# ============================================================
# COEFFICIENTS & SUPPLEMENTARY DATA
# ============================================================
# Adjust these values to match your problem parameters.
# Stub values of 0 are used for procurement, unmet demand,
# tariff routes, and remaining inventory until real data
# is available.
# ============================================================

coefficients = {

    # --- Penalty / cost coefficients ---
    "UD"      : 50,       # Unmet demand linear penalty
    "FC1"     : 10,       # Fixed cost per active source site
    "FC2"     : 10,       # Fixed cost per active destination site
    "P1"      : 100,      # Inventory conservation penalty
    "P2"      : 100,      # Demand satisfaction penalty
    "P3"      : 100,      # Source activation consistency penalty
    "P4"      : 100,      # Destination activation consistency penalty
    "M"       : 20,       # Big-M activation bound

    # --- Interaction reward / penalty coefficients ---
    "lambda1" : 500,      # Hub / carrier synergy reward
    "lambda2" : 200,      # Tariff route penalty
    "lambda3" : 100,      # Shipment consolidation reward
    "lambda4" : 50,       # Supply-chain resilience penalty

    # --- Suppliers and procurement ---
    # Replace "SUP_EXT1" and costs with real supplier data
    "suppliers" : ["SUP_EXT1"],
    "B"         : {"SUP_EXT1": {d: 20 for d in demand_sites}},  # Procurement cost B[m][j]
    "T"         : {"SUP_EXT1": {d: 0  for d in demand_sites}},  # Procurement qty  T[m][j]

    # --- Unmet demand per destination ---
    # Set U[j] > 0 if a destination cannot be fully satisfied
    "U" : {d: 0 for d in demand_sites},

    # --- Remaining / slack inventory per source ---
    # S[i] = inventory not shipped (residual slack)
    "S" : {s: 0 for s in supply_sites},

    # --- Hubs, carriers, tariff routes ---
    "hubs"     : ["NA"],
    "carriers" : ["AIR"],
    "routes"   : ["ROUTE1"],
    "G"        : {"ROUTE1": 0},   # 1 if tariff route is activated, else 0
}

# ============================================================
# OBJECTIVE FUNCTION
# ============================================================

def objective_function(best_state, data, transport_cost, c):
    """
    Evaluates and prints the full HUBO objective function H
    broken down into its individual named terms.

    Parameters
    ----------
    best_state     : dict  — variable name -> 0/1 from simulated annealing
    data           : dict  — dataset (supply_sites, demand_sites, inventory,
                             demand, allowed_routes)
    transport_cost : dict  — (s, d) -> cost
    c              : dict  — coefficients and supplementary data (see above)
    """

    supply_sites   = data["supply_sites"]
    demand_sites   = data["demand_sites"]
    inventory      = data["inventory"]
    demand         = data["demand"]
    allowed_routes = data["allowed_routes"]

    # Helper: binary shipment value from best_state
    def x(s, d):
        return best_state.get(f"ship_{s}_{d}", 0)

    # ----------------------------------------------------------
    # TERM 1 — Transport cost   sum C_ij * X_ij
    # ----------------------------------------------------------
    transport_cost_total = sum(
        cost * x(s, d)
        for (s, d), cost in transport_cost.items()
    )

    # ----------------------------------------------------------
    # TERM 2 — Procurement cost   sum B_mj * T_mj
    # ----------------------------------------------------------
    procurement_cost_total = sum(
        c["B"][m][j] * c["T"][m][j]
        for m in c["suppliers"]
        for j in demand_sites
    )

    # ----------------------------------------------------------
    # TERM 3 — Unmet demand penalty   UD * sum U_j   (LINEAR)
    # ----------------------------------------------------------
    unmet_demand_total = sum(
        c["UD"] * c["U"][j]
        for j in demand_sites
    )

    # ----------------------------------------------------------
    # TERM 4 — Fixed source activation cost   FC1 * sum Y_i
    # ----------------------------------------------------------
    source_activation_total = 0
    for s in supply_sites:
        Y_i = 1 if any(x(s, d) == 1 for d in allowed_routes[s]) else 0
        source_activation_total += c["FC1"] * Y_i

    # ----------------------------------------------------------
    # TERM 5 — Fixed destination activation cost   FC2 * sum Z_j
    # ----------------------------------------------------------
    dest_activation_total = 0
    for d in demand_sites:
        Z_j = 1 if any(
            x(s, d) == 1
            for s in supply_sites
            if d in allowed_routes[s]
        ) else 0
        dest_activation_total += c["FC2"] * Z_j

    # ----------------------------------------------------------
    # TERM 6 — Inventory conservation penalty
    # P1 * sum_i ( E_i - sum_j X_ij - S_i )^2
    # ----------------------------------------------------------
    inventory_penalty_total = 0
    for s in supply_sites:
        outgoing = sum(x(s, d) for d in allowed_routes[s])
        residual = inventory[s] - outgoing - c["S"].get(s, 0)
        inventory_penalty_total += c["P1"] * (residual ** 2)

    # ----------------------------------------------------------
    # TERM 7 — Demand satisfaction penalty
    # P2 * sum_j ( N_j - sum_i X_ij - sum_m T_mj - U_j )^2
    # ----------------------------------------------------------
    demand_penalty_total = 0
    for d in demand_sites:
        incoming_ship = sum(
            x(s, d)
            for s in supply_sites
            if d in allowed_routes[s]
        )
        incoming_proc = sum(c["T"][m][d] for m in c["suppliers"])
        gap = demand[d] - incoming_ship - incoming_proc - c["U"][d]
        demand_penalty_total += c["P2"] * (gap ** 2)

    # ----------------------------------------------------------
    # TERM 8 — Source activation consistency penalty
    # P3 * sum_i ( sum_j X_ij - M * Y_i )^2
    # ----------------------------------------------------------
    source_consistency_total = 0
    for s in supply_sites:
        outgoing = sum(x(s, d) for d in allowed_routes[s])
        Y_i     = 1 if outgoing > 0 else 0
        source_consistency_total += c["P3"] * ((outgoing - c["M"] * Y_i) ** 2)

    # ----------------------------------------------------------
    # TERM 9 — Destination activation consistency penalty
    # P4 * sum_j ( sum_i X_ij + sum_m T_mj - M * Z_j )^2
    # ----------------------------------------------------------
    dest_consistency_total = 0
    for d in demand_sites:
        incoming_ship = sum(
            x(s, d)
            for s in supply_sites
            if d in allowed_routes[s]
        )
        incoming_proc = sum(c["T"][m][d] for m in c["suppliers"])
        total_in      = incoming_ship + incoming_proc
        Z_j           = 1 if total_in > 0 else 0
        dest_consistency_total += c["P4"] * ((total_in - c["M"] * Z_j) ** 2)

    # ----------------------------------------------------------
    # TERM 10 — Hub / carrier synergy reward
    # -lambda1 * sum_{i,h,carrier} Y_i * H_h * F_c
    # ----------------------------------------------------------
    hub_synergy_total = 0
    for s in supply_sites:
        Y_i = 1 if any(x(s, d) == 1 for d in allowed_routes[s]) else 0
        for h in c["hubs"]:
            H_h = best_state.get(f"hub_{h}", 0)
            for carrier in c["carriers"]:
                F_c = best_state.get(f"carrier_{carrier}", 0)
                hub_synergy_total += Y_i * H_h * F_c
    hub_synergy_total *= -c["lambda1"]

    # ----------------------------------------------------------
    # TERM 11 — Tariff route penalty
    # +lambda2 * sum_{r,carrier,j} G_r * F_c * Z_j
    # ----------------------------------------------------------
    tariff_penalty_total = 0
    for r in c["routes"]:
        G_r = c["G"].get(r, 0)
        for carrier in c["carriers"]:
            F_c = best_state.get(f"carrier_{carrier}", 0)
            for d in demand_sites:
                Z_j = 1 if any(
                    x(s, d) == 1
                    for s in supply_sites
                    if d in allowed_routes[s]
                ) else 0
                tariff_penalty_total += G_r * F_c * Z_j
    tariff_penalty_total *= c["lambda2"]

    # ----------------------------------------------------------
    # TERM 12 — Shipment consolidation reward
    # -lambda3 * sum_{i,j} X_ij^3
    # (binary variables: X^3 = X, so this counts active routes)
    # ----------------------------------------------------------
    consolidation_reward_total = 0
    for s in supply_sites:
        for d in allowed_routes[s]:
            val = x(s, d)
            consolidation_reward_total += val * val * val
    consolidation_reward_total *= -c["lambda3"]

    # ----------------------------------------------------------
    # TERM 13 — Resilience / risk penalty
    # +lambda4 * sum_{a<b<c} Y_a * Y_b * Y_c
    # (counts all unique triples of active source sites)
    # ----------------------------------------------------------
    active_sources = [
        s for s in supply_sites
        if any(x(s, d) == 1 for d in allowed_routes[s])
    ]
    n = len(active_sources)
    triple_count = 0
    for a in range(n):
        for b in range(a + 1, n):
            for cc in range(b + 1, n):
                triple_count += 1
    resilience_penalty_total = c["lambda4"] * triple_count

    # ----------------------------------------------------------
    # TOTAL H
    # ----------------------------------------------------------
    total_H = (
        transport_cost_total
        + procurement_cost_total
        + unmet_demand_total
        + source_activation_total
        + dest_activation_total
        + inventory_penalty_total
        + demand_penalty_total
        + source_consistency_total
        + dest_consistency_total
        + hub_synergy_total
        + tariff_penalty_total
        + consolidation_reward_total
        + resilience_penalty_total
    )

    # ----------------------------------------------------------
    # PRINT BREAKDOWN
    # ----------------------------------------------------------
    print("\n" + "=" * 56)
    print("  OBJECTIVE FUNCTION BREAKDOWN")
    print("=" * 56)
    print(f"  {'Transport Cost':<35} (C_ij * X_ij) : {transport_cost_total:>10.2f}")
    print(f"  {'Procurement Cost':<35} (B_mj * T_mj) : {procurement_cost_total:>10.2f}")
    print(f"  {'Unmet Demand Penalty':<35}  (UD * U_j) : {unmet_demand_total:>10.2f}")
    print(f"  {'Source Activation Cost':<35} (FC1 * Y_i) : {source_activation_total:>10.2f}")
    print(f"  {'Dest Activation Cost':<35} (FC2 * Z_j) : {dest_activation_total:>10.2f}")
    print(f"  {'Inventory Conservation Penalty':<35}      (P1) : {inventory_penalty_total:>10.2f}")
    print(f"  {'Demand Satisfaction Penalty':<35}      (P2) : {demand_penalty_total:>10.2f}")
    print(f"  {'Source Consistency Penalty':<35}      (P3) : {source_consistency_total:>10.2f}")
    print(f"  {'Dest Consistency Penalty':<35}      (P4) : {dest_consistency_total:>10.2f}")
    print(f"  {'Hub/Carrier Synergy Reward':<35}     (-λ1) : {hub_synergy_total:>10.2f}")
    print(f"  {'Tariff Route Penalty':<35}     (+λ2) : {tariff_penalty_total:>10.2f}")
    print(f"  {'Shipment Consolidation Reward':<35}     (-λ3) : {consolidation_reward_total:>10.2f}")
    print(f"  {'Resilience/Risk Penalty':<35}     (+λ4) : {resilience_penalty_total:>10.2f}")
    print("-" * 56)
    print(f"  {'TOTAL H':<48} : {total_H:>10.2f}")
    print("=" * 56)

    return total_H

# ============================================================
# EVALUATE AND PRINT OBJECTIVE FUNCTION
# ============================================================

objective_function(best_state, data, transport_cost, coefficients)