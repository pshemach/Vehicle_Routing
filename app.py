"""
Flask application for the Vehicle Routing Solution.
Provides a web interface for uploading PO files and visualizing routes.
"""

import os
import json
import uuid
import shutil
from glob import glob
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename

from vehi_rout.controller import VRPController

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Ensure upload and output directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Global variables
controller = None
current_job_id = None
current_results = {}

def create_output_directories(output_folder):
    """Create output directories for the job.

    Args:
        output_folder: Path to the job output folder
    """
    os.makedirs(os.path.join(output_folder, 'summaries'), exist_ok=True)
    os.makedirs(os.path.join(output_folder, 'csv'), exist_ok=True)
    os.makedirs(os.path.join(output_folder, 'maps'), exist_ok=True)

def copy_output_files(output_folder):
    """Copy output files to the job output folder using platform-independent code.

    Args:
        output_folder: Path to the job output folder
    """
    # Copy summaries
    for file in glob('output/summaries/*'):
        shutil.copy2(file, os.path.join(output_folder, 'summaries', os.path.basename(file)))

    # Copy CSV files
    for file in glob('output/csv/*'):
        shutil.copy2(file, os.path.join(output_folder, 'csv', os.path.basename(file)))

    # Copy map files
    for file in glob('output/maps/*'):
        shutil.copy2(file, os.path.join(output_folder, 'maps', os.path.basename(file)))

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/jobs')
def jobs():
    """Render the jobs page."""
    return render_template('jobs.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and initialize the routing process."""
    global controller, current_job_id

    # Check if files are provided
    if 'po_file' not in request.files:
        return jsonify({'error': 'No PO file provided'}), 400

    po_file = request.files['po_file']

    # Check if file is valid
    if po_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(po_file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # Generate a unique job ID
    current_job_id = str(uuid.uuid4())
    job_folder = os.path.join(app.config['UPLOAD_FOLDER'], current_job_id)
    os.makedirs(job_folder, exist_ok=True)

    # Save the uploaded file
    po_filename = secure_filename(po_file.filename)
    po_path = os.path.join(job_folder, po_filename)
    po_file.save(po_path)

    # Get form parameters
    use_time = request.form.get('use_time') == 'true'
    multi_day = request.form.get('multi_day') == 'true'
    days = int(request.form.get('days', 1))
    max_nodes = int(request.form.get('max_nodes', 300))

    # Get vehicle configuration
    num_vehicles = int(request.form.get('num_vehicles', 8))

    # Get max visits per vehicle
    max_visits = []
    for i in range(num_vehicles):
        visit_key = f'max_visits[{i}]'
        if visit_key in request.form:
            max_visits.append(int(request.form[visit_key]))
        else:
            max_visits.append(15)  # Default value

    # Get max distance per vehicle
    max_distance = []
    for i in range(num_vehicles):
        distance_key = f'max_distance[{i}]'
        if distance_key in request.form:
            max_distance.append(int(request.form[distance_key]))
        else:
            max_distance.append(100)  # Default value

    # Initialize controller
    controller = VRPController(use_distance=not use_time)

    # Load data
    matrix_path = request.form.get('matrix_path', 'data/master/osrm_distance_matrix.csv')
    gps_path = request.form.get('gps_path', 'data/master/master_gps.csv')

    try:
        controller.load_data(
            demand_path=po_path,
            matrix_path=matrix_path,
            gps_path=gps_path
        )
    except Exception as e:
        return jsonify({'error': f'Error loading data: {str(e)}'}), 500

    # Create job info
    job_info = {
        'job_id': current_job_id,
        'po_file': po_filename,
        'use_time': use_time,
        'multi_day': multi_day,
        'days': days,
        'max_nodes': max_nodes,
        'num_vehicles': num_vehicles,
        'max_visits': max_visits,
        'max_distance': max_distance,
        'status': 'initialized',
        'timestamp': datetime.now().isoformat()
    }

    # Save job info
    with open(os.path.join(job_folder, 'job_info.json'), 'w') as f:
        json.dump(job_info, f)

    # Redirect directly to the solve page instead of returning JSON
    return redirect(url_for('solve', job_id=current_job_id))

@app.route('/solve/<job_id>', methods=['GET'])
def solve(job_id):
    """Run the routing algorithm and generate results."""
    global controller, current_results

    # Check if job exists
    job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    if not os.path.exists(job_folder):
        return jsonify({'error': 'Job not found'}), 404

    # Load job info
    with open(os.path.join(job_folder, 'job_info.json'), 'r') as f:
        job_info = json.load(f)

    # Update job status
    job_info['status'] = 'running'
    with open(os.path.join(job_folder, 'job_info.json'), 'w') as f:
        json.dump(job_info, f)

    # Create output folder for this job
    output_folder = os.path.join(app.config['OUTPUT_FOLDER'], job_id)
    os.makedirs(output_folder, exist_ok=True)

    try:
        # Update controller configuration with vehicle parameters
        controller.update_vehicle_config(
            num_vehicles=job_info['num_vehicles'],
            max_visits=job_info['max_visits'],
            max_distance=job_info['max_distance']
        )
        # Run the solver
        if job_info['multi_day']:
            all_visited_nodes, all_route_dicts = controller.solve_multi_day(
                total_days=job_info['days'],
                max_nodes=job_info['max_nodes'],
                save_visualization=True
            )

            # Store results
            current_results = {
                'job_id': job_id,
                'multi_day': True,
                'days': job_info['days'],
                'num_vehicles': job_info['num_vehicles'],
                'max_visits': job_info['max_visits'],
                'max_distance': job_info['max_distance'],
                'all_visited_nodes': [list(nodes) for nodes in all_visited_nodes],
                'all_route_dicts': all_route_dicts,
                'timestamp': datetime.now().isoformat()
            }

        else:
            visited_nodes, route_dict = controller.solve_single_day(
                day=0,
                max_nodes=job_info['max_nodes'],
                save_visualization=True
            )

            # Store results
            current_results = {
                'job_id': job_id,
                'multi_day': False,
                'num_vehicles': job_info['num_vehicles'],
                'max_visits': job_info['max_visits'],
                'max_distance': job_info['max_distance'],
                'visited_nodes': list(visited_nodes),
                'route_dict': route_dict,
                'timestamp': datetime.now().isoformat()
            }

        # Create subdirectories in the job output folder
        create_output_directories(output_folder)

        # Copy output files to job output folder
        copy_output_files(output_folder)

        # Update job status
        job_info['status'] = 'completed'
        with open(os.path.join(job_folder, 'job_info.json'), 'w') as f:
            json.dump(job_info, f)

        return redirect(url_for('results', job_id=job_id))

    except Exception as e:
        # Update job status
        job_info['status'] = 'failed'
        job_info['error'] = str(e)
        with open(os.path.join(job_folder, 'job_info.json'), 'w') as f:
            json.dump(job_info, f)

        return jsonify({'error': f'Error solving routing problem: {str(e)}'}), 500

@app.route('/results/<job_id>', methods=['GET'])
def results(job_id):
    """Display the results of a routing job."""
    # Check if job exists
    job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    if not os.path.exists(job_folder):
        return jsonify({'error': 'Job not found'}), 404

    # Load job info
    with open(os.path.join(job_folder, 'job_info.json'), 'r') as f:
        job_info = json.load(f)

    # Check if job is completed
    if job_info['status'] != 'completed':
        return jsonify({'error': 'Job is not completed yet'}), 400

    # Get output files
    output_folder = os.path.join(app.config['OUTPUT_FOLDER'], job_id)

    # Get summary files
    summary_files = []
    if os.path.exists(os.path.join(output_folder, 'summaries')):
        summary_files = [f for f in os.listdir(os.path.join(output_folder, 'summaries')) if f.endswith('.txt')]

    # Get CSV files
    csv_files = []
    if os.path.exists(os.path.join(output_folder, 'csv')):
        csv_files = [f for f in os.listdir(os.path.join(output_folder, 'csv')) if f.endswith('.csv')]

    # Get map files
    map_files = []
    if os.path.exists(os.path.join(output_folder, 'maps')):
        map_files = [f for f in os.listdir(os.path.join(output_folder, 'maps')) if f.endswith('.html')]

    # Render results page
    return render_template(
        'results.html',
        job_id=job_id,
        job_info=job_info,
        summary_files=summary_files,
        csv_files=csv_files,
        map_files=map_files
    )

@app.route('/file/<job_id>/<file_type>/<filename>')
def get_file(job_id, file_type, filename):
    """Serve a file from the output folder."""
    output_folder = os.path.join(app.config['OUTPUT_FOLDER'], job_id, file_type)
    return send_from_directory(output_folder, filename)

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs."""
    jobs = []
    for job_id in os.listdir(app.config['UPLOAD_FOLDER']):
        job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
        if os.path.isdir(job_folder) and os.path.exists(os.path.join(job_folder, 'job_info.json')):
            with open(os.path.join(job_folder, 'job_info.json'), 'r') as f:
                job_info = json.load(f)
                jobs.append(job_info)

    return jsonify(jobs)

@app.route('/api/job/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get job information."""
    job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    if not os.path.exists(job_folder) or not os.path.exists(os.path.join(job_folder, 'job_info.json')):
        return jsonify({'error': 'Job not found'}), 404

    with open(os.path.join(job_folder, 'job_info.json'), 'r') as f:
        job_info = json.load(f)

    return jsonify(job_info)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5096)
