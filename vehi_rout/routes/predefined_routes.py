"""
Module for managing pre-defined routes.
Provides functionality to create, load, and save pre-defined routes.
"""

import os
import json
import pandas as pd

class PredefinedRouteManager:
    """
    Class for managing pre-defined routes.
    """
    def __init__(self, routes_dir="data/routes"):
        """
        Initialize the PredefinedRouteManager.

        Args:
            routes_dir: Directory to store route files
        """
        self.routes_dir = routes_dir
        self.routes = {}

        # Create routes directory if it doesn't exist
        os.makedirs(self.routes_dir, exist_ok=True)

        # Load existing routes
        self.load_routes()

    def load_routes(self):
        """
        Load all pre-defined routes from the routes directory.
        """
        self.routes = {}

        # Check if routes directory exists
        if not os.path.exists(self.routes_dir):
            return

        # Load each route file
        for filename in os.listdir(self.routes_dir):
            if filename.endswith('.json'):
                route_path = os.path.join(self.routes_dir, filename)
                try:
                    with open(route_path, 'r') as f:
                        route_data = json.load(f)
                        route_id = filename.replace('.json', '')
                        self.routes[route_id] = route_data
                except Exception as e:
                    print(f"Error loading route {filename}: {str(e)}")

    def save_route(self, route_id, route_data):
        """
        Save a pre-defined route.

        Args:
            route_id: Unique identifier for the route
            route_data: Dictionary containing route information
        """
        # Create routes directory if it doesn't exist
        os.makedirs(self.routes_dir, exist_ok=True)

        # Save route to file
        route_path = os.path.join(self.routes_dir, f"{route_id}.json")
        with open(route_path, 'w') as f:
            json.dump(route_data, f, indent=2)

        # Update routes dictionary
        self.routes[route_id] = route_data

    def delete_route(self, route_id):
        """
        Delete a pre-defined route.

        Args:
            route_id: Unique identifier for the route
        """
        # Check if route exists
        if route_id not in self.routes:
            return False

        # Delete route file
        route_path = os.path.join(self.routes_dir, f"{route_id}.json")
        if os.path.exists(route_path):
            os.remove(route_path)

        # Remove from routes dictionary
        del self.routes[route_id]
        return True

    def get_route(self, route_id):
        """
        Get a pre-defined route.

        Args:
            route_id: Unique identifier for the route

        Returns:
            route_data: Dictionary containing route information
        """
        return self.routes.get(route_id)

    def get_all_routes(self):
        """
        Get all pre-defined routes.

        Returns:
            routes: Dictionary of all routes
        """
        return self.routes

    def create_route_from_codes(self, route_name, shop_codes, description=""):
        """
        Create a new route from a list of shop codes.

        Args:
            route_name: Name of the route
            shop_codes: List of shop codes in order or a string with codes separated by commas or newlines
            description: Description of the route

        Returns:
            route_id: Unique identifier for the route
        """
        # Generate a unique ID for the route
        route_id = route_name.lower().replace(' ', '_')

        # Process shop codes - handle different input formats
        processed_codes = []

        # If shop_codes is a string, split it by commas and/or newlines
        if isinstance(shop_codes, str):
            # Replace commas with newlines, then split by newlines
            codes_str = shop_codes.replace(',', '\n')
            # Split by newlines and strip whitespace
            codes = [code.strip() for code in codes_str.split('\n') if code.strip()]
            processed_codes.extend(codes)
        elif isinstance(shop_codes, list):
            # If it's already a list, process each item
            for item in shop_codes:
                if isinstance(item, str):
                    # If the item contains newlines, split it
                    if '\n' in item or '\r\n' in item:
                        # Replace commas with newlines, then split by newlines
                        item_str = item.replace(',', '\n')
                        # Split by newlines and strip whitespace
                        codes = [code.strip() for code in item_str.split('\n') if code.strip()]
                        processed_codes.extend(codes)
                    else:
                        processed_codes.append(item.strip())
                else:
                    # If it's not a string, convert to string
                    processed_codes.append(str(item).strip())

        # Create route data
        route_data = {
            "name": route_name,
            "description": description,
            "shop_codes": processed_codes,
            "created_at": pd.Timestamp.now().isoformat()
        }

        # Save route
        self.save_route(route_id, route_data)

        return route_id
