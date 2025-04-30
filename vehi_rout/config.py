"""
Configuration module for the Vehicle Routing Problem.
Contains all the parameters used in the solution.
"""

# Number of days to plan ahead
TOTAL_DAYS = 6

# Maximum number of visits per vehicle
# 8 vehicles with different capacities
MAX_VISITS_PER_VEHICLE = [15, 15, 15, 15, 15, 15, 15, 15]

# Maximum time (in minutes) per vehicle
MAX_TIME_PER_VEHICLE = [1200, 1200, 600, 600, 600, 600, 600, 600]

# Maximum distance (in km) per vehicle
MAX_DISTANCE_PER_VEHICLE = [500, 500, 500, 500, 500, 500, 500, 500]

# Base penalty for not visiting a node (used in time-based routing)
TIME_BASE_PENALTY = 100000

# Base penalty for not visiting a node (used in distance-based routing)
DISTANCE_BASE_PENALTY = 100000

# Depot node ID
DEPOT = 0

# Solver parameters
SOLVER_TIME_LIMIT_SECONDS = 30

# Penalty weights for different days remaining
# The closer to the deadline, the higher the penalty
PENALTY_WEIGHTS = {
    1: 400,   # 1 day remaining
    2: 500,   # 2 days remaining
    3: 1000,  # 3 days remaining
    4: 1000,  # 4 days remaining
    5: 1000,  # 5 days remaining
    6: 1000, # 6 days remaining
    7: 1000   # 7 days remaining
}
