import numpy as np
import trimesh
from scipy.optimize import minimize
import os
import time
import random

class BowArrowOptimizer:
    def __init__(self, model_path):
        self.model = trimesh.load(model_path)
        self.original_model = self.model.copy()
        self.components = self.model.split()
        
        # Default parameters of Bow
        self.bow_thickness = 5.0       # mm
        self.bow_curvature = 0.3       # ratio
        self.limb_stiffness = 0.6      # ratio
        self.grip_width = 25.0         # mm

        # Default parameters of Arrow
        self.arrow_length = 60.0       # mm
        self.arrow_weight = 2.0        # g
        self.tip_diameter = 8.0        # mm
        self.tip_length = 5.0          # mm        
        
        # User profiles with tailored parameters
        self.user_profiles = {
            'Child': {
                'bow_thickness': 6.0,
                'bow_curvature': 0.25,
                'limb_stiffness': 0.4,
                'grip_width': 30.0,
                'arrow_length': 50.0,
                'arrow_weight': 1.5,
                'tip_diameter': 10.0,
                'tip_length': 7.0,
                'max_draw_force': 3.0,      # N
                'max_launch_speed': 2.0,    # m/s
                'safety_factor': 1.5,
                'speed_factor': 0.8,
                'grip_size_factor': 1.2
            },
            'Adult': {
                'bow_thickness': 5.0,
                'bow_curvature': 0.3,
                'limb_stiffness': 0.6,
                'grip_width': 25.0,
                'arrow_length': 60.0,
                'arrow_weight': 2.0,
                'tip_diameter': 8.0,
                'tip_length': 5.0,
                'max_draw_force': 5.0,      # N
                'max_launch_speed': 3.5,    # m/s
                'safety_factor': 1.2,
                'speed_factor': 1.0,
                'grip_size_factor': 1.0
            },
            'Professional': {
                'bow_thickness': 4.5,
                'bow_curvature': 0.35,
                'limb_stiffness': 0.75,
                'grip_width': 22.0,
                'arrow_length': 70.0,
                'arrow_weight': 2.5,
                'tip_diameter': 6.0,
                'tip_length': 4.0,
                'max_draw_force': 7.0,      # N
                'max_launch_speed': 5.0,    # m/s
                'safety_factor': 1.0,
                'speed_factor': 1.2,
                'grip_size_factor': 0.9
            }
        }
        self.current_user = 'Adult' # Child, Adult, Professional
        self.palm_size = 90.0 # mm (default adult palm size)
        self.preferred_speed = 'Medium' # Low, Medium, High

    def set_user_profile(self, profile_name, palm_size=None, preferred_speed=None):
        """Set user profile and adjust parameters accordingly"""
        if profile_name in self.user_profiles:
            self.current_user = profile_name # moved to top as logs are not updated correctly
            profile = self.user_profiles[profile_name]
            self.refresh_parameters(
                profile['bow_thickness'], 
                profile['bow_curvature'],
                profile['limb_stiffness'],
                profile['grip_width'],
                profile['arrow_length'],
                profile['arrow_weight'],
                profile['tip_diameter']
            )
            self.tip_length = profile['tip_length']
            
            if palm_size:
                self.palm_size = palm_size
                # Adjust grip width based on palm size
                self.adjust_for_palm_size()
                
            if preferred_speed:
                self.preferred_speed = preferred_speed
                # Adjust parameters for preferred shooting speed
                self.adjust_for_speed()
                
            print(f'Switched to profile: {profile_name}')
            return True
        return False

    def adjust_for_palm_size(self):
        """Adjust parameters based on user's palm size"""
        profile = self.user_profiles[self.current_user]
        base_palm_size = 90.0  # Standard adult palm size in mm
        
        # Scale factor based on palm size
        scale_factor = self.palm_size / base_palm_size
        
        # Adjust grip width while keeping it proportional to palm size
        self.grip_width = profile['grip_width'] * scale_factor * profile['grip_size_factor']
        
        # Adjust other parameters as needed for comfort
        if scale_factor > 1.2:  # For larger hands
            self.bow_thickness *= 1.1
        elif scale_factor < 0.8:  # For smaller hands
            self.bow_thickness *= 0.9
            
        print(f"Adjusted for palm size {self.palm_size:.1f}mm: Grip width = {self.grip_width:.1f}mm")
        
    # To calculate comfort score
    def compute_comfort_score(self):
        """Compute comfort score based on ergonomic heuristics and log debug data"""
        os.makedirs("logs", exist_ok=True)
        log_path = "logs/comfort_score_debug.txt"

        # Heuristic weights
        grip_score = 1.0
        thickness_score = 1.0
        stiffness_score = 1.0
        curvature_score = 1.0

        # 1. Grip Heuristics (based on palm size)
        palm_factor = self.palm_size / (90.0 if self.current_user != 'Child' else 70.0)
        grip_ratio = self.grip_width / (self.palm_size * 0.27)
        if grip_ratio > 1.2:
            grip_score = 0.7 if self.current_user == 'Child' else 0.9
        elif grip_ratio < 0.8:
            grip_score = 0.6
        else:
            grip_score = 1.0

        # 2. Thickness Heuristics (penalize excess thickness for children or small palms)
        if self.bow_thickness > 6.0 and self.palm_size < 75.0:
            thickness_score = 0.6
        elif self.bow_thickness < 4.5 and self.palm_size > 100.0:
            thickness_score = 0.8
        else:
            thickness_score = 1.0

        # 3. Stiffness Heuristics (softer is easier, good for small users)
        if self.limb_stiffness > 0.7 and self.current_user == 'Child':
            stiffness_score = 0.5
        elif self.limb_stiffness < 0.5 and self.current_user == 'Professional':
            stiffness_score = 0.7
        else:
            stiffness_score = 1.0

        # 4. Curvature Heuristics (too high or low can be uncomfortable)
        if 0.25 <= self.bow_curvature <= 0.35:
            curvature_score = 1.0
        else:
            curvature_score = 0.8

        # Final comfort score (weighted)
        comfort_score = (
            grip_score * 0.4 +
            thickness_score * 0.3 +
            stiffness_score * 0.2 +
            curvature_score * 0.1
        ) * 100

        comfort_score = round(min(max(comfort_score, 0), 100), 1)

        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write("=== Comfort Score Log ===\n")
            log_file.write(f"User Type: {self.current_user}\n")
            log_file.write(f"Palm Size: {self.palm_size} mm\n")
            log_file.write(f"Grip Width: {self.grip_width:.2f} mm → Grip Score: {grip_score:.2f}\n")
            log_file.write(f"Bow Thickness: {self.bow_thickness:.2f} mm → Thickness Score: {thickness_score:.2f}\n")
            log_file.write(f"Limb Stiffness: {self.limb_stiffness:.2f} → Stiffness Score: {stiffness_score:.2f}\n")
            log_file.write(f"Bow Curvature: {self.bow_curvature:.2f} → Curvature Score: {curvature_score:.2f}\n")
            log_file.write(f"Final Comfort Score: {comfort_score:.1f}/100\n")

        return comfort_score

    def adjust_for_speed(self):
        """Adjust parameters based on preferred shooting speed"""
        profile = self.user_profiles[self.current_user]
        
        if self.preferred_speed == 'Low':
            speed_factor = profile.get('speed_factor') - 0.2
            safety_factor = profile.get('safety_factor') + 0.2
        elif self.preferred_speed == 'High':
            speed_factor = profile.get('speed_factor') + 0.2
            safety_factor = profile.get('safety_factor') - 0.2
        else:  # Medium (default)
            speed_factor = profile.get('speed_factor')
            safety_factor = profile.get('safety_factor')

        # TODO: Adjust parameters based on speed preference 
        self.limb_stiffness = profile['limb_stiffness'] * speed_factor
        self.arrow_weight = profile['arrow_weight'] * (1 / speed_factor)
        self.tip_diameter = profile['tip_diameter'] * safety_factor
        
        print(f"Adjusted for {self.preferred_speed} speed preference")

    def refresh_parameters(self, bow_thickness, bow_curvature, limb_stiffness, 
                          grip_width, arrow_length, arrow_weight, tip_diameter):
        """Update all parameters"""
        # Bow's parameters can be manually set 
        self.bow_thickness = bow_thickness
        self.bow_curvature = bow_curvature
        self.limb_stiffness = limb_stiffness
        self.grip_width = grip_width

        # Arrow's parameters must be calculated by bow's params to make them suitable!
        arrow_length = self.calculate_optimal_arrow_length(bow_thickness, bow_curvature, grip_width)
        arrow_weight = self.calculate_optimal_arrow_weight(limb_stiffness, grip_width)
        tip_diameter = self.calculate_optimal_tip_diameter(limb_stiffness, grip_width)
        self.arrow_length = arrow_length
        self.arrow_weight = arrow_weight
        self.tip_diameter = tip_diameter
        
        print(f'Parameters updated: Thickness={self.bow_thickness:.1f}, Curvature={self.bow_curvature:.2f}, '
              f'Stiffness={self.limb_stiffness:.2f}, Grip Width={self.grip_width:.1f},'
              f'Arrow Length={self.arrow_length:.1f}, Arrow Weight={self.arrow_weight:.1f}, Tip Diameter={self.tip_diameter:.1f}')

    def apply_geometry_update(self):
        """Apply parameter changes to the 3D model geometry"""
        # Reset model to original state before applying modifications
        for i, component in enumerate(self.components):
            if i < len(self.original_model.split()):
                original_component = self.original_model.split()[i]
                component.vertices = np.array(original_component.vertices)
        
        # Calculate scaling and adjustment factors
        thickness_factor = self.bow_thickness / 5.0
        curvature_factor = self.bow_curvature
        grip_scale = self.grip_width / 25.0
        
        # Identify bow components (first component is bow body and second is arrow)
        bow_body_index = 0
        
        # Process each component
        for i, component in enumerate(self.components):
            vertices = np.array(component.vertices)
            
            if i == bow_body_index:
                # Bow body modifications
                # 1. Calculate bow position - assume x-center is bow midpoint
                x_min, x_max = np.min(vertices[:, 0]), np.max(vertices[:, 0])
                bow_center_x = (x_min + x_max) / 2
                
                # 2. Apply curvature to bow limbs (assume limbs are on +/- x ends)
                # Stronger curvature at limb ends, using a quadratic function
                for v_idx, vertex in enumerate(vertices):
                    rel_x = (vertex[0] - bow_center_x) / ((x_max - x_min) / 2)
                    
                    # Apply curvature only to limb portions (not grip)
                    if abs(rel_x) > 0.3:  # Outside grip region
                        # Quadratic curvature function
                        curvature_z = curvature_factor * rel_x**2
                        vertices[v_idx, 2] += curvature_z
                
                # 3. Apply grip width adjustment (scale central portion in y-direction)
                y_center = np.mean(vertices[:, 1])
                for v_idx, vertex in enumerate(vertices):
                    rel_x = (vertex[0] - bow_center_x) / ((x_max - x_min) / 2)
                    
                    # Only adjust grip width in central region
                    if abs(rel_x) < 0.3:  # Grip region
                        y_offset = (vertex[1] - y_center)
                        vertices[v_idx, 1] = y_center + y_offset * grip_scale
                
                # 4. Apply thickness scaling (only for grip region and in z-direction)
                for v_idx, vertex in enumerate(vertices):
                    rel_x = (vertex[0] - bow_center_x) / ((x_max - x_min) / 2)
                    
                    # Only adjust thickness in the grip's power region
                    if rel_x < 0.2 and rel_x > -0.5:  # Grip's power region
                        if vertices[v_idx, 2] >= 0:  # Modify thickness only one side for more convinience 3D print
                            vertices[v_idx, 2] *= thickness_factor   # Adjust only the z-direction
                
            else:
                # Arrow component modifications if present
                # Assuming second component is the arrow
                if i == 1:
                    # Scale arrow length
                    arrow_scale = self.arrow_length / 60.0  # Assuming default arrow is 60mm
                    # Find arrow axis (assume primarily along x-axis)
                    x_min, x_max = np.min(vertices[:, 0]), np.max(vertices[:, 0])
                    arrow_center_x = (x_min + x_max) / 2
                    
                    # Scale from center point
                    for v_idx, vertex in enumerate(vertices):
                        rel_x = vertex[0] - arrow_center_x
                        vertices[v_idx, 0] = arrow_center_x + rel_x * arrow_scale
                        
                    # Adjust tip diameter if this is arrow tip component
                    # (simplified approach - just apply uniform scaling to tip)
                    tip_scale = self.tip_diameter / 8.0  # Assuming default tip is 8mm
                    for v_idx, vertex in enumerate(vertices):
                        # Only scale y and z dimensions for tip
                        vertices[v_idx, 1] = (vertex[1] - y_center) * tip_scale + y_center
                        vertices[v_idx, 2] *= tip_scale
            
            # Update component with modified vertices
            component.vertices = vertices
        
        print('Geometry updated with current parameters')
        
        # Call UI update if callback is registered
        if hasattr(self, 'ui_update_callback'):
            self.ui_update_callback()

    def objective(self, x, user_profile):
        """Objective function for optimization"""
        bow_thickness, bow_curvature, limb_stiffness, grip_width = x
        
        # Get target values from user profile
        target_bow_thickness = user_profile['bow_thickness']
        target_bow_curvature = user_profile['bow_curvature']
        target_limb_stiffness = user_profile['limb_stiffness']
        target_grip_width = user_profile['grip_width']
        
        # Different weights for parameters based on user profile
        if self.current_user == 'Child':
            # Children need safety, comfort and easy drawing
            weight_thickness = 1.0
            weight_curvature = 0.8
            weight_stiffness = 0.6
            weight_grip = 1.5  # Higher priority on grip comfort for children
            safety_weight = 3.0  # High priority on safety
        elif self.current_user == 'Professional':
            # Professionals want precision and control
            weight_thickness = 0.8
            weight_curvature = 1.5
            weight_stiffness = 2.0  # Prioritize consistent behavior
            weight_grip = 1.0
            safety_weight = 1.0
        else:  # Adult or default
            # Balance between performance and safety
            weight_thickness = 1.0
            weight_curvature = 1.0
            weight_stiffness = 1.0
            weight_grip = 1.2
            safety_weight = 1.5
        
        # Calculate weighted sum of squared errors
        cost = (
            weight_thickness * (bow_thickness - target_bow_thickness)**2 +
            weight_curvature * (bow_curvature - target_bow_curvature)**2 +
            weight_stiffness * (limb_stiffness - target_limb_stiffness)**2 +
            weight_grip * (grip_width - target_grip_width)**2
        )
        
        # Add constraint penalties
        # 1. Safety constraints
        estimated_launch_speed = self.estimate_launch_speed(bow_thickness, bow_curvature, limb_stiffness, grip_width)
        max_safe_speed = user_profile['max_launch_speed']
        
        if estimated_launch_speed > max_safe_speed:
            cost += safety_weight * 5.0 * (estimated_launch_speed - max_safe_speed)**2
        
        # 2. Draw force constraint
        estimated_draw_force = self.estimate_draw_force(bow_thickness, bow_curvature, limb_stiffness, grip_width)
        max_draw_force = user_profile['max_draw_force']
        
        if estimated_draw_force > max_draw_force:
            cost += safety_weight * 3.0 * (estimated_draw_force - max_draw_force)**2
        
        # 3. Size constraints based on palm size
        grip_width_factor = (self.palm_size / 90.0) * user_profile['grip_size_factor']
        ideal_grip_width = target_grip_width * grip_width_factor
        grip_deviation = abs(grip_width - ideal_grip_width)
        cost += 2.0 * grip_deviation
        
        return cost

    # TODO: Need more precise calculation for speed
    def estimate_launch_speed(self, bow_thickness, bow_curvature, limb_stiffness, grip_width):
        """Estimate arrow launch speed based on bow parameters"""
        # Simple physics model: launch speed is proportional to:
        # - limb stiffness (higher stiffness -> more energy stored)
        # - bow thickness (thicker bow -> more force)
        # - bow curvature (more curve -> more energy stored)
        # - inversely related to grip width (narrower grip -> more focused energy transfer)
        
        base_speed = 3.0  # m/s (baseline speed)
        
        grip_factor = 25.0 / grip_width  # Narrower grip increases speed (normalized to default 25mm)
        
        estimated_speed = (
            base_speed * 
            (bow_thickness / 5.0) * 
            (1 + bow_curvature) * 
            limb_stiffness *
            (grip_factor ** 0.3)  # Apply grip factor with dampened effect
        )
        
        return estimated_speed
    
    # TODO: Need more precise calculation for force
    def estimate_draw_force(self, bow_thickness, bow_curvature, limb_stiffness, grip_width):
        """Estimate force required to fully draw the bow"""
        # Simple model for draw force:
        # - Proportional to thickness, stiffness
        # - Inversely proportional to flexibility
        # - Wider grip increases required force
        
        base_force = 4.0  # N (baseline force)
        
        grip_factor = grip_width / 25.0  # Wider grip increases required force
        
        estimated_force = (
            base_force * 
            (bow_thickness / 5.0) * 
            (1 + 0.5 * bow_curvature) * 
            limb_stiffness *
            (grip_factor ** 0.5)  # Apply grip factor with square root to dampen effect
            )
        
        return estimated_force

    # UPDATE: Replace optimize_model with optimize_for_performance
    # def optimize_model(self):
    #     """Run optimization to find the best parameters for current user profile"""
    #     # Get current user profile
    #     current_profile = self.user_profiles[self.current_user]
        
    #     initial_guess = [
    #         self.bow_thickness, 
    #         self.bow_curvature, 
    #         self.limb_stiffness,
    #         self.grip_width
    #     ]
        
    #     # Define bounds based on user profile
    #     if self.current_user == 'Child':
    #         bounds = [
    #             (5.0, 7.0),     # bow_thickness
    #             (0.2, 0.3),     # bow_curvature
    #             (0.3, 0.5),     # limb_stiffness
    #             (28.0, 32.0)    # grip_width - wider for children's hands
    #         ]
    #     elif self.current_user == 'Professional':
    #         bounds = [
    #             (4.0, 5.0),     # bow_thickness
    #             (0.3, 0.4),     # bow_curvature
    #             (0.7, 0.9),     # limb_stiffness
    #             (20.0, 25.0)    # grip_width - narrower for precision
    #         ]
    #     else:  # Adult or default
    #         bounds = [
    #             (4.5, 5.5),     # bow_thickness
    #             (0.25, 0.35),   # bow_curvature
    #             (0.5, 0.7),     # limb_stiffness
    #             (23.0, 28.0)    # grip_width - medium range
    #         ]
        
    #     # Create an objective function that captures the profile
    #     def obj_func(x):
    #         return self.objective(x, current_profile)
        
    #     # Run optimization
    #     result = minimize(obj_func, initial_guess, method='L-BFGS-B', bounds=bounds)
        
    #     # Apply small random variations to prevent identical results
    #     random_factor = 0.03  # 3% random variation
    #     bow_thickness = result.x[0] * (1 + (random.random() - 0.5) * 2 * random_factor)
    #     bow_curvature = result.x[1] * (1 + (random.random() - 0.5) * 2 * random_factor)
    #     limb_stiffness = result.x[2] * (1 + (random.random() - 0.5) * 2 * random_factor)
    #     grip_width = result.x[3] * (1 + (random.random() - 0.5) * 2 * random_factor)
        
    #     # Keep within bounds
    #     bow_thickness = max(bounds[0][0], min(bounds[0][1], bow_thickness))
    #     bow_curvature = max(bounds[1][0], min(bounds[1][1], bow_curvature))
    #     limb_stiffness = max(bounds[2][0], min(bounds[2][1], limb_stiffness))
    #     grip_width = max(bounds[3][0], min(bounds[3][1], grip_width))
        
    #     # Calculate optimal arrow parameters based on bow parameters
    #     arrow_length = self.calculate_optimal_arrow_length(bow_thickness, bow_curvature, grip_width)
    #     arrow_weight = self.calculate_optimal_arrow_weight(limb_stiffness, grip_width)
    #     tip_diameter = self.calculate_optimal_tip_diameter(limb_stiffness, grip_width)
        
    #     # Update all parameters
    #     self.refresh_parameters(
    #         bow_thickness, bow_curvature, limb_stiffness,
    #         grip_width, arrow_length, arrow_weight, tip_diameter
    #     )
        
    #     self.apply_geometry_update()

    # UPDATE: Add a method to optimize for launch speed and draw force
    def optimize_for_performance(self, target_speed, target_force, lock_speed=False, lock_force=False):
        """Optimize parameters to achieve target performance metrics"""
        print(f"Optimizing for - Speed: {target_speed} m/s (locked: {lock_speed}), Force: {target_force} N (locked: {lock_force})")
        
        # Define optimization objective function for performance targets
        def objective_performance(x):
            bow_thickness, bow_curvature, limb_stiffness, grip_width = x
            
            # Calculate expected performance with these parameters
            launch_speed = self.estimate_launch_speed(bow_thickness, bow_curvature, limb_stiffness, grip_width)
            draw_force = self.estimate_draw_force(bow_thickness, bow_curvature, limb_stiffness, grip_width)
            
            # Calculate error from targets
            speed_error = 0
            force_error = 0
            
            if lock_speed:
                # UPDATE: Higher penalty for deviating from locked speed target to garentee user deminds
                speed_error = 100.0 * (launch_speed - target_speed)**2
            else:
                # Softer penalty when speed isn't locked
                speed_error = (launch_speed - target_speed)**2
                 
            if lock_force:
                # UPDATE: Higher penalty for deviating from locked force target to garentee user deminds
                force_error = 100.0 * (draw_force - target_force)**2
            else:
                # Softer penalty when force isn't locked
                force_error = (draw_force - target_force)**2
            
            # Add penalties for unrealistic or unsafe values
            safety_penalty = 0
            
            # Calculate comfort based on physical parameters
            # Higher penalty for uncomfortable configurations
            palm_factor = self.palm_size / 90.0
            grip_width_ideal = 25.0 * palm_factor
            grip_comfort_penalty = 2.0 * ((grip_width - grip_width_ideal) / grip_width_ideal)**2
            
            # Total cost
            total_cost = speed_error + force_error + safety_penalty + grip_comfort_penalty
            
            return total_cost
        
        # Initial guess - start from current values
        initial_guess = [
            self.bow_thickness,
            self.bow_curvature,
            self.limb_stiffness,
            self.grip_width
        ]
        
        # Define parameter bounds
        bounds = [
            (4.0, 7.0),     # bow_thickness
            (0.2, 0.4),     # bow_curvature
            (0.3, 0.9),     # limb_stiffness
            (20.0, 35.0)    # grip_width - full range
        ]
        
        # Run optimization
        result = minimize(objective_performance, initial_guess, method='L-BFGS-B', bounds=bounds)
        
        # Apply optimized parameters
        bow_thickness, bow_curvature, limb_stiffness, grip_width = result.x
        
        # Calculate derived parameters (arrows, etc.)
        arrow_length = self.calculate_optimal_arrow_length(bow_thickness, bow_curvature, grip_width)
        arrow_weight = self.calculate_optimal_arrow_weight(limb_stiffness, grip_width)
        tip_diameter = self.calculate_optimal_tip_diameter(limb_stiffness, grip_width)
        
        # Update all parameters
        self.refresh_parameters(
            bow_thickness, bow_curvature, limb_stiffness,
            grip_width, arrow_length, arrow_weight, tip_diameter
        )
        
        # Apply geometry updates
        self.apply_geometry_update()
        
        # Log results
        optimized_speed = self.estimate_launch_speed(bow_thickness, bow_curvature, limb_stiffness, grip_width)
        optimized_force = self.estimate_draw_force(bow_thickness, bow_curvature, limb_stiffness, grip_width)
        
        os.makedirs("logs", exist_ok=True)
        with open("logs/performance_optimization.txt", "w") as log_file:
            log_file.write("=== Performance Optimization Results ===\n")
            log_file.write(f"Target Launch Speed: {target_speed:.2f} m/s (locked: {lock_speed})\n")
            log_file.write(f"Target Draw Force: {target_force:.2f} N (locked: {lock_force})\n")
            log_file.write(f"Achieved Launch Speed: {optimized_speed:.2f} m/s\n")
            log_file.write(f"Achieved Draw Force: {optimized_force:.2f} N\n")
            log_file.write(f"Parameters - Thickness: {bow_thickness:.2f} mm, Curvature: {bow_curvature:.2f}, Stiffness: {limb_stiffness:.2f}, Grip Width: {grip_width:.2f} mm\n")
        
        print(f"Optimization complete - Speed: {optimized_speed:.2f} m/s, Force: {optimized_force:.2f} N")
        
    # TODO: User can not directly change arrow so this need to rewrite to fit the size of the bow!
    def calculate_optimal_arrow_length(self, bow_thickness, bow_curvature, grip_width):
        """Adaptively calculate arrow length based on bow parameters and user needs"""
        base_length = 60.0  # mm

        # More stiffness and curvature = faster release, so shorter arrow improves stability
        stiffness_factor = 1.0 - (self.limb_stiffness - 0.6) * 0.3  # slightly shorter for stiffer bows
        curvature_factor = 1.0 - (bow_curvature - 0.3) * 0.4        # shorten with high curvature
        thickness_factor = 1.0 + (bow_thickness - 5.0) * 0.05       # thicker bow = slightly longer arrow
        
        # Add grip width influence - wider grip needs slightly longer arrow for stability
        grip_factor = 1.0 + (grip_width - 25.0) * 0.01

        # User profile adjustment
        profile_factor = {
            'Child': 0.9,
            'Adult': 1.0,
            'Professional': 1.1
        }.get(self.current_user, 1.0)

        length = base_length * stiffness_factor * curvature_factor * thickness_factor * profile_factor * grip_factor
        return max(45.0, min(length, 80.0))  # clamp between 45mm and 80mm
    def calculate_optimal_arrow_weight(self, limb_stiffness, grip_width):
        """Compute arrow weight based on bow's stiffness, grip width, and user profile"""
        base_weight = 2.0  # g

        stiffness_factor = 1.0 + (limb_stiffness - 0.6) * 0.6  # stiffer bow = heavier arrow
        length_factor = self.arrow_length / 60.0               # scale weight with arrow length
        
        # Add grip width influence - wider grip generally works better with slightly heavier arrows
        grip_factor = 1.0 + (grip_width - 25.0) * 0.008

        profile_factor = {
            'Child': 0.85,
            'Adult': 1.0,
            'Professional': 1.2
        }.get(self.current_user, 1.0)

        weight = base_weight * stiffness_factor * length_factor * profile_factor * grip_factor
        return round(weight, 2)
    def calculate_optimal_tip_diameter(self, limb_stiffness, grip_width):
        """Determine tip diameter based on stiffness, grip width, and safety"""
        base_diameter = 8.0  # mm

        # Heavier or faster bows = smaller, sharper tips (unless user is child)
        stiffness_factor = 1.0 - (limb_stiffness - 0.6) * 0.4
        curvature_penalty = 1.0 if self.bow_curvature < 0.33 else 0.95
        
        # Add grip width influence - wider grip needs larger tip for stability
        grip_factor = 1.0 + (grip_width - 25.0) * 0.01

        profile_factor = {
            'Child': 1.3,
            'Adult': 1.0,
            'Professional': 0.8
        }.get(self.current_user, 1.0)

        diameter = base_diameter * stiffness_factor * curvature_penalty * profile_factor * grip_factor
        return round(min(max(diameter, 4.0), 12.0), 2)  # clamp to safe bounds

    # TODO: Need more reasonable calculation of performance scores
    def simulate_performance(self):
        """Simulate bow and arrow performance with current parameters"""
        # Calculate key performance metrics
        launch_speed = self.estimate_launch_speed(
            self.bow_thickness, self.bow_curvature, self.limb_stiffness, self.grip_width
        )
        
        draw_force = self.estimate_draw_force(
            self.bow_thickness, self.bow_curvature, self.limb_stiffness, self.grip_width
        )
        
        # Basic physics for shoot distance
        # Simplified model: distance ~ (launch_speed^2 * sin(2*angle)) / gravity
        # Assuming optimal 45° angle
        gravity = 9.81  # m/s²
        optimal_angle_factor = 1.0  # sin(2*45°)
        base_distance = (launch_speed**2 * optimal_angle_factor) / gravity
        
        # Adjust for arrow weight, grip width, and air resistance
        weight_factor = 2.0 / self.arrow_weight  # Lighter arrows fly farther
        tip_factor = 8.0 / self.tip_diameter     # Smaller tips have less drag
        
        # Add grip influence on stability
        grip_ratio = self.grip_width / (self.palm_size * 0.27)
        stability_factor = 1.0
        if grip_ratio < 0.8 or grip_ratio > 1.2:  # Sub-optimal grip affects stability
            stability_factor = 0.9
        
        # Estimated flight distance
        flight_distance = base_distance * weight_factor * tip_factor * stability_factor
        
        # Accuracy score (based on balance of parameters)
        # Higher stiffness improves accuracy, and grip width affects stability
        grip_accuracy_factor = 1.0 - abs(grip_ratio - 1.0) * 0.2  # Optimal grip ratio is 1.0
        accuracy_score = (70 + (self.limb_stiffness * 20)) * grip_accuracy_factor
        
        # Calculate comfort score from ergonomics
        comfort_score = self.compute_comfort_score()
        
        # 3D Print Settings
        self.get_print_settings()  # Log the dynamic 3D print settings

        # Safety score
        if self.current_user == 'Child':
            safety_threshold = 2.5  # m/s
            tip_size_factor = self.tip_diameter / 10.0  # Relative to child-safe 10mm
        else:
            safety_threshold = 4.0  # m/s
            tip_size_factor = self.tip_diameter / 8.0  # Relative to standard 8mm
                
        safety_score = 100 - max(0, (launch_speed - safety_threshold) * 20)
        safety_score = safety_score * tip_size_factor
        
        # Overall performance score weighted by user type
        if self.current_user == 'Child':
            # Children prioritize safety and comfort
            performance_score = (
                accuracy_score * 0.2 +
                comfort_score * 0.3 +
                safety_score * 0.5
            )
        elif self.current_user == 'Professional':
            # Professionals prioritize accuracy and distance
            performance_score = (
                accuracy_score * 0.5 +
                comfort_score * 0.2 +
                safety_score * 0.1 +
                min(100, flight_distance * 10) * 0.2
            )
        else:
            # Adults want balance
            performance_score = (
                accuracy_score * 0.3 +
                comfort_score * 0.3 +
                safety_score * 0.2 +
                min(100, flight_distance * 12) * 0.2
            )
        
        # Ensure scores are in 0-100 range
        accuracy_score = min(100, max(0, accuracy_score))
        comfort_score = min(100, max(0, comfort_score))
        safety_score = min(100, max(0, safety_score))
        performance_score = min(100, max(0, performance_score))
        
        return {
            'launch_speed': launch_speed,
            'draw_force': draw_force,
            'flight_distance': flight_distance,
            'accuracy_score': accuracy_score,
            'comfort_score': comfort_score,
            'safety_score': safety_score,
            'performance_score': performance_score
        }

    def export_model(self, filename):
        """Export the current model to STL file"""
        # Combine all components into one mesh
        combined_mesh = trimesh.util.concatenate(self.components)
        combined_mesh.export(filename)
        print(f"Model exported to {filename}")
        return os.path.abspath(filename)

    # TODO: Optimization for 3D printing parameters   
    def get_print_settings(self):
        """Dynamically recommend 3D print settings based on bow and arrow parameters and log them"""

        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        log_path = "logs/print_settings_debug.txt"

        # Material choice based on stiffness and thickness
        if self.limb_stiffness > 0.7:
            material = "Nylon or PETG"
        elif self.bow_thickness < 5.0:
            material = "PETG"
        else:
            material = "PLA or TPU" if self.current_user == "Child" else "PLA"

        # Layer height
        if self.bow_curvature > 0.33 or self.limb_stiffness > 0.7:
            layer_height = "0.12mm"
        elif self.bow_thickness > 5.5:
            layer_height = "0.16mm"
        else:
            layer_height = "0.2mm"

        # Infill
        if self.limb_stiffness > 0.7 or self.arrow_weight > 2.2:
            infill = "30%"
        elif self.bow_thickness > 5.5:
            infill = "25%"
        else:
            infill = "20%"

        # Supports
        supports = "Yes" if self.bow_curvature > 0.36 else "No"

        # Instructions
        if "TPU" in material:
            instructions = "Print bow limbs with TPU for extra flexibility and safety"
        elif self.limb_stiffness > 0.7:
            instructions = "Print bow at 45° angle for better layer adhesion and strength"
        else:
            instructions = "Standard printing orientation is recommended"

        # Write to log file
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("=== 3D Print Settings Log ===\n")
            f.write(f"User Type: {self.current_user}\n")
            f.write(f"Limb Stiffness: {self.limb_stiffness:.2f}\n")
            f.write(f"Bow Thickness: {self.bow_thickness:.2f} mm\n")
            f.write(f"Bow Curvature: {self.bow_curvature:.2f}\n")
            f.write(f"Arrow Weight: {self.arrow_weight:.2f} g\n")
            f.write(f"Material: {material}\n")
            f.write(f"Layer Height: {layer_height}\n")
            f.write(f"Infill: {infill}\n")
            f.write(f"Supports: {supports}\n")
            f.write(f"Instructions: {instructions}\n")

        return {
            "material": material,
            "layer_height": layer_height,
            "infill": infill,
            "supports": supports,
            "special_instructions": instructions
        }
