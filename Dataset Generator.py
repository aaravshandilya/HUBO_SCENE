import random
import json

# ============================================================
# CONFIGURATION
# ============================================================

NUM_SUPPLY = 10
NUM_DEMAND = 10

# ============================================================
# SITE CREATION
# ============================================================

supply_sites = [
    f"SUP{i}"
    for i in range(1, NUM_SUPPLY + 1)
]

demand_sites = [
    f"DEM{i}"
    for i in range(1, NUM_DEMAND + 1)
]

# ============================================================
# INVENTORY
# ============================================================

inventory = {}

for s in supply_sites:
    inventory[s] = random.randint(5, 20)

# ============================================================
# DEMAND
# ============================================================

demand = {}

for d in demand_sites:
    demand[d] = random.randint(3, 12)

# ============================================================
# ENSURE FEASIBILITY
# ============================================================

while sum(inventory.values()) < sum(demand.values()):
    random_site = random.choice(supply_sites)
    inventory[random_site] += 5

# ============================================================
# SPARSE ROUTING GRAPH
# ============================================================

allowed_routes = {}

for s in supply_sites:
    allowed_routes[s] = random.sample(
        demand_sites,
        random.randint(2, 4)
    )

# GUARANTEE SUP1 -> DEM1 route exists for cubic HUBO term
if "DEM1" not in allowed_routes["SUP1"]:
    allowed_routes["SUP1"].append("DEM1")

# ============================================================
# TRANSPORTATION COSTS
# ============================================================

transport_cost = {}

for s in supply_sites:
    for d in allowed_routes[s]:
        transport_cost[str((s, d))] = random.randint(1, 15)

# ============================================================
# FINAL DATASET
# ============================================================

dataset = {
    "supply_sites": supply_sites,
    "demand_sites": demand_sites,
    "inventory": inventory,
    "demand": demand,
    "allowed_routes": allowed_routes,
    "transport_cost": transport_cost
}

# ============================================================
# SAVE DATASET
# ============================================================

with open("dataset.json", "w") as f:
    json.dump(
        dataset,
        f,
        indent=4
    )

print("Dataset generated successfully.")