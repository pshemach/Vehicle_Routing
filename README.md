# Vehicle Routing Solution

This project implements a vehicle routing solution for a distribution center with 8 vehicles. It supports both single-day and multi-day planning, with the ability to distribute products either on the same day or on another day.

## Features

- **Distance-based routing**: Uses distance matrix for routing decisions
- **Multi-day planning**: Supports planning for multiple days with different priorities
- **Flexible constraints**: Configurable vehicle capacities, maximum distances, and visit limits
- **Visualization**: Interactive maps showing routes for each vehicle
- **Detailed reporting**: Summaries and detailed route information in various formats

## Directory Structure

```
Vehicle_Routing/
├── data/
│   ├── master/           # Master data (GPS coordinates, distance matrix)
│   └── orders/           # Daily order data
├── output/               # Generated output files
│   ├── csv/              # CSV files with route details
│   ├── maps/             # HTML map visualizations
│   └── summaries/        # Text summaries of routes
├── vehi_rout/            # Main package
│   ├── config.py         # Configuration parameters
│   ├── controller.py     # Main controller
│   ├── data_model/       # Data model for the solver
│   ├── solver/           # VRP solver implementation
│   └── utils/            # Utility functions
├── example.py            # Example script
├── main.py               # Command-line interface
└── README.md             # This file
```

## How to Use

### Running the Example Script

The easiest way to get started is to run the example script:

```bash
python example.py
```

This will:

1. Solve a single-day routing problem
2. Solve a multi-day routing problem (3 days)
3. Generate various output files

### Using the Command-Line Interface

For more control, you can use the command-line interface:

```bash
# Single-day routing
python main.py --max-nodes 300 --save-viz

# Multi-day routing
python main.py --multi-day --days 3 --max-nodes 300 --save-viz

# Use time matrix instead of distance matrix
python main.py --use-time --multi-day --days 3 --max-nodes 300 --save-viz
```

### Output Files

The solution generates the following output files:

- **Route Summaries**: `output/summaries/day_X_summary.txt`
- **Multi-Day Summary**: `output/summaries/multi_day_summary.txt`
- **Daily Route Details**: `output/csv/day_X_routes.csv`
- **Combined Route Details**: `output/csv/all_days_routes.csv`
- **Route Visualizations**: `output/maps/day_X_vehicle_Y_route.html`

## Configuration

You can modify the configuration parameters in `vehi_rout/config.py`:

- `TOTAL_DAYS`: Number of days to plan ahead
- `MAX_VISITS_PER_VEHICLE`: Maximum number of visits per vehicle
- `MAX_DISTANCE_PER_VEHICLE`: Maximum distance per vehicle
- `DISTANCE_BASE_PENALTY`: Base penalty for not visiting a node
- `PENALTY_WEIGHTS`: Penalty weights for different days remaining

## Extending the Solution

To extend the solution:

1. Modify the configuration parameters in `vehi_rout/config.py`
2. Add new constraints in `vehi_rout/solver/vrp_solver.py`
3. Add new visualization options in `vehi_rout/utils/visualization.py`
4. Create custom controllers by extending `VRPController` in `vehi_rout/controller.py`
