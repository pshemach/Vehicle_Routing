import os
import json
import uuid
import shutil
from glob import glob
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from flask_cors import CORS
import pandas as pd
import logging

from vehi_rout.controller import VRPController
from datetime import datetime

def parse_order_time_window(raw_list):
    """
    Converts raw JSON input with timeWindow as "HH:MM-HH:MM"
    into a dict with minute ranges, e.g., "50021": (480, 600)
    """
    result = {}
    for item in raw_list:
        code = str(item["shopCode"])
        start_str, end_str = item["timeWindow"].split("-")
        start_min = int(datetime.strptime(start_str.strip(), "%H:%M").hour * 60)
        end_min = int(datetime.strptime(end_str.strip(), "%H:%M").hour * 60)
        result[code] = (start_min, end_min)
    return result

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Global variables
controller = None
current_job_id = None
current_results = {}

def create_output_directories(output_folder):
    """Create output directories for the job."""
    os.makedirs(os.path.join(output_folder, 'summaries'), exist_ok=True)
    os.makedirs(os.path.join(output_folder, 'csv'), exist_ok=True)
    os.makedirs(os.path.join(output_folder, 'maps'), exist_ok=True)

def copy_output_files(output_folder):
    """Copy output files to the job output folder."""
    try:
        for subdir in ['summaries', 'csv', 'maps']:
            src_dir = os.path.join('output', subdir)
            dst_dir = os.path.join(output_folder, subdir)
            if os.path.exists(src_dir):
                for file in glob(os.path.join(src_dir, '*')):
                    shutil.copy2(file, dst_dir)
                    logger.debug(f"Copied {file} to {dst_dir}")
    except Exception as e:
        logger.error(f"Error copying output files: {str(e)}")

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/jobs')
def jobs():
    return render_template('jobs.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global controller, current_job_id
    if 'po_file' not in request.files:
        return jsonify({'error': 'No PO file provided'}), 400

    po_file = request.files['po_file']
    if po_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(po_file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    current_job_id = str(uuid.uuid4())
    job_folder = os.path.join(app.config['UPLOAD_FOLDER'], current_job_id)
    os.makedirs(job_folder, exist_ok=True)

    po_filename = secure_filename(po_file.filename)
    po_path = os.path.join(job_folder, po_filename)
    po_file.save(po_path)
    
    if 'gps_file' in request.files:
        gps_file = request.files['gps_file']
        if gps_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if not allowed_file(gps_file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        gps_filename = secure_filename(gps_file.filename)
        gps_path = os.path.join(job_folder, gps_filename)
        gps_file.save(gps_path)
    print(request.files)
    print(request.form)

    use_time = request.form.get('use_time') == 'true'
    multi_day = request.form.get('multi_day') == 'true'
    days = int(request.form.get('days', 1))
    max_nodes = int(request.form.get('max_nodes', 300))
    num_vehicles = int(request.form.get('num_vehicles', 8))
    max_visits = [int(request.form.get(f'max_visits[{i}]', 15)) for i in range(num_vehicles)]
    max_distance = [int(request.form.get(f'max_distance[{i}]', 100)) for i in range(num_vehicles)]

    matrix_path = request.form.get('matrix_path', 'data/master/osrm_distance_matrix.csv')
    gps_path = request.form.get('gps_path', 'data/master/master_gps.csv')
    
    geo_constraints = request.form.get('geo_constraints')
    order_time_window = request.form.get('order_time_window')   
    order_groups = request.form.get('order_groups')
    priority_orders = request.form.get('priority_orders')
    vehicle_constraints = request.form.get('vehicle_constraints')
    predefined_routes = request.form.get('predefined_routes')
    vehicle_routes = request.form.get('vehicle_routes')
    
    print(f"use_time: {use_time}")
    print(f"order_time_window_type: {type(order_time_window)}")
    print(f"order_time_window: {order_time_window}")
    
    # if len(order_time_window) > 2:
    #     use_time = True
    #     print(len(order_time_window))
    #     print(f"use_time: {use_time}")
    #     matrix_path = 'data/master/osrm_duration_matrix.csv'
    controller = VRPController(use_distance=not use_time)
    
    # print(f"use_time: {use_time}")
    
    job_info = {
        'job_id': current_job_id,
        'matrix_path': matrix_path,
        'gps_path': gps_path,
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
    
    job_info['geo_constraints'] = json.loads(geo_constraints) if geo_constraints else []
    job_info['order_time_window'] = json.loads(order_time_window) if order_time_window else []
    job_info['order_groups'] = json.loads(order_groups) if order_groups else []
    job_info['priority_orders'] = json.loads(priority_orders) if priority_orders else []
    job_info['vehicle_constraints'] = json.loads(vehicle_constraints) if vehicle_constraints else []
    job_info['predefined_routes'] = json.loads(predefined_routes) if predefined_routes else []
    job_info['vehicle_routes'] = json.loads(vehicle_routes) if vehicle_routes else {}
        
    try:
        controller.update_vehicle_config(
            num_vehicles=num_vehicles,
            max_visits=max_visits,
            max_distance=max_distance
        )
        print(f"matrix_path: {matrix_path}")
        print(f"gps_path: {gps_path}")
        print(f"po_path: {po_path}")
        controller.load_data(
            demand_path=po_path,
            matrix_path=matrix_path,
            gps_path=gps_path
        )
        
        controller.vehicle_routes = job_info.get('vehicle_routes', {})
        controller.predefined_routes = job_info.get('predefined_routes', [])

    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return jsonify({'error': f'Error loading data: {str(e)}'}), 500

    with open(os.path.join(job_folder, 'job_info.json'), 'w') as f:
        json.dump(job_info, f)
    return jsonify({'job_id': current_job_id})

@app.route('/solve/<job_id>', methods=['GET'])
def solve(job_id):
    global controller, current_results
    logger.info(f"Starting /solve for job_id: {job_id}")

    job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    if not os.path.exists(job_folder):
        logger.error(f"Job folder not found: {job_folder}")
        return jsonify({'error': 'Job not found'}), 404

    with open(os.path.join(job_folder, 'job_info.json'), 'r') as f:
        job_info = json.load(f)
    logger.debug(f"Loaded job_info: {job_info}")

    job_info['status'] = 'running'
    with open(os.path.join(job_folder, 'job_info.json'), 'w') as f:
        json.dump(job_info, f)
    logger.debug(f"Updated job status to 'running' for job_id: {job_id}")

    output_folder = os.path.join(app.config['OUTPUT_FOLDER'], job_id)
    create_output_directories(output_folder)
    logger.debug(f"Created output folder: {output_folder}")
    
    parsed_windows = parse_order_time_window(job_info.get('order_time_window', []))
    print(f"parsed_windows: {parsed_windows}")

    try:
        visited_nodes, route_dict = controller.solve_single_day(
            day=0,
            save_visualization=True,
            geo_constraints=job_info.get('geo_constraints', []),
            order_time_window=parsed_windows,
            order_groups=job_info.get('order_groups', []),
            priority_orders=job_info.get('priority_orders', []),
            vehicle_constraints=job_info.get('vehicle_constraints', [])
        )
        logger.debug(f"Solver returned: {len(visited_nodes)} nodes, route_dict keys: {list(route_dict.keys())}")
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

        copy_output_files(output_folder)
        logger.debug(f"Copied output files to: {output_folder}")

        job_info['status'] = 'completed'
        with open(os.path.join(job_folder, 'job_info.json'), 'w') as f:
            json.dump(job_info, f)
        logger.debug(f"Updated job status to 'completed' for job_id: {job_id}")

        return redirect(url_for('results', job_id=job_id))

    except Exception as e:
        logger.error(f"Error in /solve for job_id {job_id}: {str(e)}")
        job_info['status'] = 'failed'
        job_info['error'] = str(e)
        with open(os.path.join(job_folder, 'job_info.json'), 'w') as f:
            json.dump(job_info, f)
        # Attempt to copy any generated files
        copy_output_files(output_folder)
        return jsonify({'error': f'Error solving routing problem: {str(e)}'}), 500

@app.route('/results/<job_id>', methods=['GET'])
def results(job_id):
    job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    if not os.path.exists(job_folder):
        return jsonify({'error': 'Job not found'}), 404

    with open(os.path.join(job_folder, 'job_info.json'), 'r') as f:
        job_info = json.load(f)

    if job_info['status'] != 'completed':
        return jsonify({'error': 'Job is not completed yet'}), 400

    output_folder = os.path.join(app.config['OUTPUT_FOLDER'], job_id)
    summary_files = [f for f in os.listdir(os.path.join(output_folder, 'summaries')) if f.endswith('.txt')] if os.path.exists(os.path.join(output_folder, 'summaries')) else []
    csv_files = [f for f in os.listdir(os.path.join(output_folder, 'csv')) if f.endswith('.csv')] if os.path.exists(os.path.join(output_folder, 'csv')) else []
    map_files = [f for f in os.listdir(os.path.join(output_folder, 'maps')) if f.endswith('.html')] if os.path.exists(os.path.join(output_folder, 'maps')) else []

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
    output_folder = os.path.join(app.config['OUTPUT_FOLDER'], job_id, file_type)
    return send_from_directory(output_folder, filename)

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
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
    job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    if not os.path.exists(job_folder) or not os.path.exists(os.path.join(job_folder, 'job_info.json')):
        return jsonify({'error': 'Job not found'}), 404

    with open(os.path.join(job_folder, 'job_info.json'), 'r') as f:
        job_info = json.load(f)
    return jsonify(job_info)

@app.route('/api/route-orders', methods=['GET'])
def get_route_orders():
    day = int(request.args.get('day'))
    vehicle = int(request.args.get('vehicle'))
    job_id = request.args.get('job_id') or current_job_id

    job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    job_info_path = os.path.join(job_folder, 'job_info.json')
    with open(job_info_path, 'r') as f:
        job_info = json.load(f)

    # Load orders.csv for shop details
    po_file = job_info['po_file']
    orders_path = os.path.join(job_folder, po_file)
    orders_df = pd.read_csv(orders_path)

    # Load the route_dict JSON file
    route_dict_path = os.path.join('output', job_id, 'csv', f'route_dict_day_{day}.json')
    with open(route_dict_path, 'r') as f:
        route_dict = json.load(f)

    # Get all shop codes in all routes for the day
    all_route_codes = set()
    for vinfo in route_dict.values():
        all_route_codes.update([str(code) for code in vinfo.get('route_nodes', []) if str(code) != '0'])

    # Get shop codes in current vehicle's route
    vehicle_key = str(vehicle)
    route_info = route_dict.get(vehicle_key, {})
    route_nodes = route_info.get('route_nodes', [])
    shop_list = []
    for code in route_nodes:
        if str(code) == '0':
            continue
        row = orders_df[orders_df['CODE'].astype(str) == str(code)]
        if not row.empty:
            shop_list.append({
                'CODE': str(code),
                'LOCATION': row.iloc[0]['LOCATION']
            })

    # Available orders: shops not in any route
    available_orders = []
    for _, row in orders_df.iterrows():
        code = str(row['CODE'])
        if code not in all_route_codes:
            available_orders.append({
                'CODE': code,
                'LOCATION': row['LOCATION']
            })

    return jsonify({
        'shopList': shop_list,
        'availableOrders': available_orders
    })

@app.route('/api/add-order', methods=['POST'])
def add_order():
    """Add an order to a specific route by updating the route_dict JSON file."""
    data = request.json
    if not data or 'orderId' not in data or 'day' not in data or 'vehicle' not in data or 'job_id' not in data:
        return jsonify({'error': 'Order ID, day, vehicle, and job_id are required'}), 400
    try:
        job_id = data['job_id']
        day = int(data['day'])
        vehicle = str(data['vehicle'])
        order_id = str(data['orderId'])
        # Load route_dict JSON
        route_dict_path = os.path.join('output', job_id, 'csv', f'route_dict_day_{day}.json')
        with open(route_dict_path, 'r') as f:
            route_dict = json.load(f)
        # Add order to the end of the route_nodes for the vehicle
        if vehicle not in route_dict:
            route_dict[vehicle] = {'route_nodes': []}
        if order_id not in route_dict[vehicle]['route_nodes']:
            # Insert before the last node if last node is depot (0)
            nodes = route_dict[vehicle]['route_nodes']
            if nodes and nodes[-1] == '0':
                nodes.insert(-1, order_id)
            else:
                nodes.append(order_id)
            route_dict[vehicle]['route_nodes'] = nodes
        # Save updated route_dict
        with open(route_dict_path, 'w') as f:
            json.dump(route_dict, f)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/remove-order', methods=['POST'])
def remove_order():
    """Remove an order from a specific route by updating the route_dict JSON file."""
    data = request.json
    if not data or 'orderId' not in data or 'day' not in data or 'vehicle' not in data or 'job_id' not in data:
        return jsonify({'error': 'Order ID, day, vehicle, and job_id are required'}), 400
    try:
        job_id = data['job_id']
        day = int(data['day'])
        vehicle = str(data['vehicle'])
        order_id = str(data['orderId'])
        # Load route_dict JSON
        route_dict_path = os.path.join('output', job_id, 'csv', f'route_dict_day_{day}.json')
        with open(route_dict_path, 'r') as f:
            route_dict = json.load(f)
        # Remove order from route_nodes for the vehicle
        if vehicle in route_dict and 'route_nodes' in route_dict[vehicle]:
            nodes = route_dict[vehicle]['route_nodes']
            route_dict[vehicle]['route_nodes'] = [c for c in nodes if str(c) != order_id]
        # Save updated route_dict
        with open(route_dict_path, 'w') as f:
            json.dump(route_dict, f)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-route-orders', methods=['POST'])
def save_route_orders():
    """Save the updated route orders and regenerate the route."""
    data = request.json
    
    if not data or 'orders' not in data or 'day' not in data or 'vehicle' not in data:
        return jsonify({'error': 'Orders list, day, and vehicle are required'}), 400
        
    try:
        # Update route orders using the controller
        controller.update_route_orders(
            order_ids=data['orders'],
            day=int(data['day']),
            vehicle=int(data['vehicle'])
        )
        
        # Regenerate route visualization
        controller.regenerate_route_visualization(
            day=int(data['day']),
            vehicle=int(data['vehicle'])
        )
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5099)