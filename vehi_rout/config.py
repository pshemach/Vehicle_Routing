"""
Configuration module for the Vehicle Routing Problem.
Contains all the parameters used in the solution.
"""

# Keep TOTAL_DAYS for backward compatibility
TOTAL_DAYS = 1

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
SOLVER_TIME_LIMIT_SECONDS = 60  # Increased from 30 to 60 seconds to find better solutions

# Single penalty weight for all nodes
PENALTY_WEIGHT = 1000
