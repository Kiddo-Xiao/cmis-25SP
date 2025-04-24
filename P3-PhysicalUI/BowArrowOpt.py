import numpy as np
import trimesh
from scipy.optimize import minimize
import os
import time
import random
import math
import Constants as co

class BowArrowOptimizer:
    def __init__(self, model_path):
        self.model = trimesh.load(model_path)
        self.components = self.model.split()
        
        if len(self.components) != 2:
            raise ValueError("STL must contain exactly 2 components (Bow and Arrow)")
        
        self.original_model = self.model.copy()
        
        # Default parameters of Bow
        self.bow_thickness = co.DEFAULT_BOW_THICKNESS       # mm
        self.bow_curvature = co.DEFAULT_BOW_CURVATURE       # ratio
        self.limb_stiffness = co.DEFAULT_LIMB_STIFFNESS      # ratio
        self.grip_width = co.DEFAULT_GRIP_WIDTH         # mm

        # Default parameters of Arrow
        self.arrow_length = co.DEFAULT_ARROW_LENGTH       # mm
        self.arrow_weight = co.DEFAULT_ARROW_WEIGHT        # g
        self.tip_diameter = co.DEFAULT_ARROW_TIP_DIAMETER        # mm
        self.tip_length = co.DEFAULT_ARROW_TIP_LENGTH          # mm        
        
        # User profiles with tailored parameters
        self.user_profiles = {
            'Child': {
                'bow_thickness': 10.0,
                'bow_curvature': 0.25,
                'limb_stiffness': 0.4,
                'grip_width': 25.0,
                'arrow_length': 50.0,
                'arrow_weight': 1.5,
                'tip_diameter': 10.0,
                'tip_length': 7.0,
                'max_draw_force': 4.0,      # N
                'max_launch_speed': 2.5,    # m/s
                'safety_factor': 1.5,
                'speed_factor': 0.8,
                'grip_size_factor': 1.2
            },
            'Adult': {
                'bow_thickness': 8.0,
                'bow_curvature': 0.3,
                'limb_stiffness': 0.6,
                'grip_width': 34.0,
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
                'bow_thickness': 6.0,
                'bow_curvature': 0.35,
                'limb_stiffness': 0.75,
                'grip_width': 25.0,
                'arrow_length': 70.0,
                'arrow_weight': 2.5,
                'tip_diameter': 6.0,
                'tip_length': 4.0,
                'max_draw_force': 8.0,      # N
                'max_launch_speed': 5.0,    # m/s
                'safety_factor': 1.0,
                'speed_factor': 1.2,
                'grip_size_factor': 0.9
            }
        }
        self.current_user = 'Adult' # Child, Adult, Professional
        self.palm_size = co.DEFAULT_PALM_SIZE # mm (default adult palm size)
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
        base_palm_size = co.DEFAULT_PALM_SIZE  # Standard adult palm size in mm
        
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
        palm_factor = self.palm_size / (co.DEFAULT_PALM_SIZE if self.current_user != 'Child' else 70.0)
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
        # arrow_length = self.calculate_optimal_arrow_length(bow_thickness, bow_curvature, grip_width)
        # Keep arrow length fixed to the existing self.arrow_len
        # 
        # gth (from STL)
        arrow_length = self.arrow_length  # mm
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
        thickness_factor = self.bow_thickness / co.DEFAULT_BOW_THICKNESS
        curvature_factor = self.bow_curvature / co.DEFAULT_BOW_CURVATURE
        grip_scale = self.grip_width / co.DEFAULT_GRIP_WIDTH
        
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
                    arrow_scale = self.arrow_length / co.DEFAULT_ARROW_LENGTH
                    # Find arrow axis (assume primarily along x-axis)
                    x_min, x_max = np.min(vertices[:, 0]), np.max(vertices[:, 0])
                    arrow_center_x = (x_min + x_max) / 2
                    
                    print(f"[Geometry Update] Arrow scaled to {self.arrow_length:.2f} mm (scale factor: {arrow_scale:.2f})")
                    
                    # Scale from center point
                    for v_idx, vertex in enumerate(vertices):
                        rel_x = vertex[0] - arrow_center_x
                        vertices[v_idx, 0] = arrow_center_x + rel_x * arrow_scale
                        
                    # Adjust tip diameter if this is arrow tip component
                    # (simplified approach - just apply uniform scaling to tip)
                    tip_scale = self.tip_diameter / co.DEFAULT_ARROW_TIP_DIAMETER
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
        grip_width_factor = (self.palm_size / co.DEFAULT_PALM_SIZE) * user_profile['grip_size_factor']
        ideal_grip_width = target_grip_width * grip_width_factor
        grip_deviation = abs(grip_width - ideal_grip_width)
        cost += 2.0 * grip_deviation
        
        return cost

    def estimate_launch_speed(self, bow_thickness, bow_curvature, limb_stiffness, grip_width):
        """Estimate arrow launch speed based on bow parameters.
        
        Energy is transferred to the arrow in the form of work (force * distance) over a distance of 1 mm. 
        Then, by the work-energy theorem, the launch speed of the arrow (in m/s) is given by sqrt(v^2 + 2W/M), where:
        v: velocity before work is applied (m/s)
        W: work (Joules)
        M: mass of arrow (kg)

        Since the arrow is at rest before work is applied, v = 0 and the equation simplifies to sqrt(2W/M).

        Curious to see the resultant estimated distance? See https://www.omnicalculator.com/physics/projectile-motion

        Equation source: https://study.com/skill/learn/how-to-use-the-work-energy-theorem-to-calculate-the-final-velocity-of-an-object-explanation.html
        """
        distance_arrow_is_pushed = co.DEFAULT_DISTANCE_ARROW_PUSHED / 1000  # in m
        force = self.estimate_draw_force(bow_thickness, bow_curvature, limb_stiffness, grip_width)  # in N
        work = force * distance_arrow_is_pushed  # in J
        mass_of_arrow = co.DEFAULT_ARROW_WEIGHT / 1000  # in kg
        estimated_speed = math.sqrt(2 * work / mass_of_arrow)  # in m/s
        
        return estimated_speed

    def estimate_draw_force(self, bow_thickness, bow_curvature, limb_stiffness, grip_width):
        """Estimate force required to fully draw the bow.
        
        The force required to deflect a single cantilever beam (in the direction of the force) is given by 3DEI/(L^3), where:
        D: deflection/distance moved (mm)
        E: Young's modulus (dependent on material properties) (N/mm^2)
        I: area moment of inertia, which for a rectangular beam with a cross section of dimensions b * h, is given by b(h^3)/12 (mm^4)
        L: length of the beam (mm)

        For 2 * 10 = 20 beams, the total force is given by 60DEI/(L^3).
        """
        deflection = co.DEFAULT_DEFLECTION
        youngs_modulus = co.DEFAULT_YOUNGS_MODULUS  # E for PLA at infill density of 100% and layer height of 0.20 mm
        beam_thickness = co.DEFAULT_BEAM_THICKNESS
        moment_of_inertia = bow_thickness * (beam_thickness ** 3) / 12

        height_difference_between_beam_ends = co.DEFAULT_HEIGHT_DIFFERENCE_BETWEEN_BEAM_ENDS  # in mm
        beam_length = math.sqrt((grip_width ** 2) + (height_difference_between_beam_ends ** 2))

        estimated_force = 60 * deflection * youngs_modulus * moment_of_inertia / (beam_length ** 3)

        empirical_corrective_factor = co.DEFAULT_EMPIRICAL_CORRECTIVE_FACTOR  # we are doing more deformation than the original equation expects

        estimated_force = estimated_force * empirical_corrective_factor
        
        return estimated_force

    # UPDATE: Added a method to optimize for launch speed and draw force
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
                # UPDATE: Higher penalty for deviating from locked speed target to garentee user demands
                speed_error = 100.0 * (launch_speed - target_speed)**2
            else:
                # Softer penalty when speed isn't locked
                speed_error = (launch_speed - target_speed)**2
                 
            if lock_force:
                # UPDATE: Higher penalty for deviating from locked force target to garentee user demands
                force_error = 100.0 * (draw_force - target_force)**2
            else:
                # Softer penalty when force isn't locked
                force_error = (draw_force - target_force)**2
            
            # Add penalties for unrealistic or unsafe values
            safety_penalty = 0
            
            # Calculate comfort based on physical parameters
            # Higher penalty for uncomfortable configurations
            palm_factor = self.palm_size / co.DEFAULT_PALM_SIZE
            grip_width_ideal = co.DEFAULT_GRIP_WIDTH * palm_factor
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
            (co.MIN_BOW_THICKNESS, co.MAX_BOW_THICKNESS),     # bow_thickness
            (co.MIN_BOW_CURVATURE, co.MAX_BOW_CURVATURE),     # bow_curvature
            (co.MIN_LIMB_STIFFNESS, co.MAX_LIMB_STIFFNESS),     # limb_stiffness
            (co.MIN_GRIP_WIDTH, co.MAX_GRIP_WIDTH)    # grip_width
        ]
        
        # Run optimization
        result = minimize(objective_performance, initial_guess, method='L-BFGS-B', bounds=bounds)
        
        # Apply optimized parameters
        bow_thickness, bow_curvature, limb_stiffness, grip_width = result.x
        
        # Calculate derived parameters (arrows, etc.)
        # arrow_length = self.calculate_optimal_arrow_length(bow_thickness, bow_curvature, grip_width)
        arrow_length = co.DEFAULT_ARROW_LENGTH  # Keep arrow length fixed to the existing self.arrow_len
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
        
    def estimate_top_clamp_space(self):
        """
        Estimate the physical top-clamping space from the bow geometry.
        (Assumes clamp spans 40–90mm depending on profile and stiffness)
        """
        if self.current_user == 'Child':
            return 50.0 + (self.bow_thickness - 5.0) * 2  # more safety
        elif self.current_user == 'Professional':
            return 85.0 + (self.bow_curvature - 0.3) * 50
        else:
            return 70.0 + (self.limb_stiffness - 0.6) * 30

    # # Check the bounding and make sure that the arrow length stays within the bow's limits
    # def calculate_optimal_arrow_length(self, bow_thickness, bow_curvature, grip_width):
    #     """Adaptively calculate arrow length based on bow parameters and user needs"""
    #     base_length = 60.0  # mm

    #     # More stiffness and curvature = faster release, so shorter arrow improves stability
    #     stiffness_factor = 1.0 - (self.limb_stiffness - 0.6) * 0.3  # slightly shorter for stiffer bows
    #     curvature_factor = 1.0 - (bow_curvature - 0.3) * 0.4        # shorten with high curvature
    #     thickness_factor = 1.0 + (bow_thickness - 5.0) * 0.05       # thicker bow = slightly longer arrow
        
    #     # Add grip width influence - wider grip needs slightly longer arrow for stability
    #     grip_factor = 1.0 + (grip_width - 25.0) * 0.01

    #     # User profile adjustment
    #     profile_factor = {
    #         'Child': 0.9,
    #         'Adult': 1.0,
    #         'Professional': 1.1
    #     }.get(self.current_user, 1.0)

    #     length = base_length * stiffness_factor * curvature_factor * thickness_factor * profile_factor * grip_factor
    #     return max(co.MIN_ARROW_LENGTH, min(length, co.MAX_ARROW_LENGTH))  # clamp between 45mm and 80mm
    
    def calculate_optimal_arrow_weight(self, limb_stiffness, grip_width):
        """Simplified arrow weight based on bow stiffness and thickness"""
        base_weight = 2.0  # g
        stiffness_factor = 1.0 + (limb_stiffness - 0.6) * 0.6
        thickness_factor = 1.0 + (self.bow_thickness - 5.0) * 0.1
        profile_factor = {
            'Child': 0.8,
            'Adult': 1.0,
            'Professional': 1.25
        }.get(self.current_user, 1.0)
        return round(base_weight * stiffness_factor * thickness_factor * profile_factor, 2)
    
    def calculate_optimal_tip_diameter(self, limb_stiffness, grip_width):
        """Tip diameter based on bow stiffness and thickness"""
        base_diameter = co.DEFAULT_ARROW_TIP_DIAMETER
        stiffness_factor = 1.0 - (limb_stiffness - 0.6) * 0.4
        thickness_factor = 1.0 - (self.bow_thickness - 5.0) * 0.04
        profile_factor = {
            'Child': 1.3,
            'Adult': 1.0,
            'Professional': 0.85
        }.get(self.current_user, 1.0)
        diameter = base_diameter * stiffness_factor * thickness_factor * profile_factor
        return round(min(max(diameter, 4.0), 12.0), 2)

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
            tip_size_factor = self.tip_diameter / co.DEFAULT_ARROW_TIP_DIAMETER  # Relative to standard 8mm
                
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
