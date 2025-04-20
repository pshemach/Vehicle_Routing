# Vehicle Routing Solution - Flask API and Web UI

This is a Flask-based web application for the Vehicle Routing Solution. It provides a user-friendly interface for uploading purchase order (PO) files, running the routing algorithm, and visualizing the results.

## Features

- **File Upload**: Upload PO files in CSV format
- **Routing Configuration**: Configure routing parameters (multi-day planning, maximum nodes, etc.)
- **Interactive Maps**: Visualize routes on interactive maps
- **Summary Reports**: View and download summary reports and detailed route information
- **Job Management**: Track and manage routing jobs

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Vehicle_Routing
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Run the Flask application:
```bash
python app.py
```

4. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

### 1. Upload PO File

1. On the home page, click "Choose File" to select a PO file (CSV format)
2. Configure the routing parameters:
   - Distance Matrix Path: Path to the distance matrix file
   - GPS Data Path: Path to the GPS coordinates file
   - Use Time Matrix: Toggle to use time instead of distance
   - Multi-Day Planning: Toggle for multi-day planning
   - Number of Days: Number of days to plan (for multi-day planning)
   - Maximum Nodes: Maximum number of nodes to visit per day
3. Click "Upload and Solve" to start the routing process

### 2. View Results

After the routing process completes, you'll be redirected to the results page, which shows:

- **Job Information**: Details about the routing job
- **Summary Files**: Links to summary text files
- **CSV Files**: Links to detailed route information in CSV format
- **Route Maps**: Interactive maps showing routes for each vehicle and day

### 3. Manage Jobs

Navigate to the Jobs page to view all routing jobs. From here, you can:

- View completed jobs
- Run initialized jobs
- Retry failed jobs

## API Endpoints

The application provides the following API endpoints:

- `GET /`: Home page with upload form
- `GET /jobs`: Jobs management page
- `POST /upload`: Upload PO file and initialize routing job
- `GET /solve/<job_id>`: Run the routing algorithm for a specific job
- `GET /results/<job_id>`: View results for a specific job
- `GET /file/<job_id>/<file_type>/<filename>`: Get a specific file from the output folder
- `GET /api/jobs`: List all jobs (JSON)
- `GET /api/job/<job_id>`: Get information about a specific job (JSON)

## Directory Structure

```
Vehicle_Routing/
├── app.py                  # Flask application
├── requirements.txt        # Python dependencies
├── static/                 # Static files
│   ├── css/                # CSS files
│   └── js/                 # JavaScript files
├── templates/              # HTML templates
│   ├── base.html           # Base template
│   ├── index.html          # Home page
│   ├── jobs.html           # Jobs page
│   └── results.html        # Results page
├── uploads/                # Uploaded files
└── output/                 # Output files
    ├── csv/                # CSV files
    ├── maps/               # Map HTML files
    └── summaries/          # Summary text files
```

## Customization

You can customize the application by modifying the following files:

- `templates/base.html`: Base template with common elements
- `templates/index.html`: Home page with upload form
- `templates/results.html`: Results page with maps and summaries
- `static/css/custom.css`: Custom CSS styles
- `static/js/app.js`: Custom JavaScript functions

## Dependencies

- Flask: Web framework
- Pandas: Data manipulation
- NumPy: Numerical computing
- OR-Tools: Optimization library
- Folium: Map visualization
- Bootstrap: UI framework
- jQuery: JavaScript library
