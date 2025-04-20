import numpy as np
import trimesh
from scipy.optimize import minimize
import os
import time
import random

class ToyOptimizer:
    def __init__(self, model_path):
        self.model = trimesh.load(model_path)
        self.original_model = self.model.copy()
        self.components = self.model.split()
        self.selected_component_index = 0
        self.thickness = 5.0
        self.curvature = 0.0
        self.flexibility = 0.5
        self.damping = 0.1
        self.surface_texture = 'Smooth'
        self.color_theme = 'Default'
        self.scene_mode = 'Default'
        self.optimization_history = []
        
        # Enhanced user profiles with more parameters
        self.user_profiles = {
            'Child': {
                'thickness': 4.0, 
                'curvature': 0.5, 
                'flexibility': 0.8, 
                'damping': 0.05,
                'max_force_required': 2.0,
                'texture_preference': 'Soft',
                'size_factor': 0.8,
                'target_stress_relief': 'Playful'
            },
            'Teen': {
                'thickness': 5.0,
                'curvature': 0.3,
                'flexibility': 0.6,
                'damping': 0.08,
                'max_force_required': 3.5,
                'texture_preference': 'Smooth',
                'size_factor': 0.9,
                'target_stress_relief': 'Energetic'
            },
            'Adult': {
                'thickness': 6.0, 
                'curvature': 0.2, 
                'flexibility': 0.5, 
                'damping': 0.1,
                'max_force_required': 5.0,
                'texture_preference': 'Textured',
                'size_factor': 1.0,
                'target_stress_relief': 'Focused'
            },
            'Elderly': {
                'thickness': 5.0, 
                'curvature': 0.0, 
                'flexibility': 0.3, 
                'damping': 0.2,
                'max_force_required': 3.0,
                'texture_preference': 'Grippy',
                'size_factor': 1.1,
                'target_stress_relief': 'Gentle'
            },
            'Therapy': {
                'thickness': 5.5,
                'curvature': 0.4,
                'flexibility': 0.7,
                'damping': 0.15,
                'max_force_required': 4.0,
                'texture_preference': 'Variable',
                'size_factor': 1.0,
                'target_stress_relief': 'Therapeutic'
            }
        }
        self.current_user = 'Adult'

    def set_user_profile(self, profile_name):
        if profile_name in self.user_profiles:
            profile = self.user_profiles[profile_name]
            self.refresh_parameters(profile['thickness'], profile['curvature'], 
                                   profile['flexibility'], profile['damping'])
            self.current_user = profile_name
            self.surface_texture = profile['texture_preference']
            print(f'Switched to profile: {profile_name}')

    def refresh_parameters(self, thickness, curvature, flexibility, damping):
        self.thickness = thickness
        self.curvature = curvature
        self.flexibility = flexibility
        self.damping = damping
        print(f'Parameters updated: Thickness={self.thickness:.1f}, Curvature={self.curvature:.1f}, '
              f'Flexibility={self.flexibility:.2f}, Damping={self.damping:.2f}')
        
        # Save to history if significantly different from previous parameters
        if not self.optimization_history or self._parameters_differ_significantly(
            self.optimization_history[-1] if self.optimization_history else None):
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            self.optimization_history.append({
                'timestamp': timestamp,
                'user_profile': self.current_user,
                'thickness': thickness,
                'curvature': curvature,
                'flexibility': flexibility,
                'damping': damping
            })
            if len(self.optimization_history) > 10:  # Keep last 10 optimizations
                self.optimization_history.pop(0)
    
    def _parameters_differ_significantly(self, previous_params):
        if previous_params is None:
            return True
        
        # Check if any parameter has changed by more than a threshold
        thickness_diff = abs(self.thickness - previous_params['thickness'])
        curvature_diff = abs(self.curvature - previous_params['curvature'])
        flexibility_diff = abs(self.flexibility - previous_params['flexibility'])
        damping_diff = abs(self.damping - previous_params['damping'])
        
        return (thickness_diff > 0.2 or curvature_diff > 0.1 or 
                flexibility_diff > 0.05 or damping_diff > 0.05)
    
    def apply_geometry_update(self):
        # Reset model to original state before applying modifications
        for i, component in enumerate(self.components):
            original_component = self.original_model.split()[i]
            component.vertices = np.array(original_component.vertices)
        
        scaling_factor = self.thickness / 5.0
        curvature_offset = self.curvature / 10.0
        
        for component in self.components:
            vertices = np.array(component.vertices)
            
            # Apply scaling based on thickness
            vertices *= scaling_factor
            
            # Apply curvature with flexibility factor
            # More complex pattern that varies based on flexibility
            x_influence = np.sin(vertices[:, 0] * 0.1) * self.flexibility
            y_influence = np.cos(vertices[:, 1] * 0.1) * self.flexibility
            z_offset = curvature_offset * x_influence * y_influence
            
            # Add some variation based on surface texture
            if self.surface_texture == 'Textured':
                texture_noise = np.sin(vertices[:, 0] * 2.0) * np.sin(vertices[:, 1] * 2.0) * 0.05
                z_offset += texture_noise
            elif self.surface_texture == 'Grippy':
                grip_pattern = (np.sin(vertices[:, 0] * 5.0) * np.sin(vertices[:, 1] * 5.0)) * 0.08
                vertices[:, 2] += grip_pattern
            
            # Apply z offset
            vertices[:, 2] += z_offset
            
            # Apply damping effect (subtle compression)
            damping_effect = 1.0 - (self.damping * 0.2)  # Scale damping effect
            vertices *= damping_effect
            
            component.vertices = vertices
        
        print('Geometry updated with current parameters')
        
        # Call UI update if callback is registered
        if hasattr(self, 'ui_update_callback'):
            self.ui_update_callback()

    def objective(self, x, user_profile):
        thickness, curvature, flexibility, damping = x
        
        # Get target values from user profile
        target_thickness = user_profile['thickness']
        target_curvature = user_profile['curvature']
        target_flexibility = user_profile['flexibility']
        target_damping = user_profile['damping']
        
        # Different weights for parameters based on stress relief target
        if user_profile['target_stress_relief'] == 'Playful':
            # Children enjoy more flexible, bouncy toys
            weight_thickness = 0.5
            weight_curvature = 1.0
            weight_flexibility = 2.0  # Highest priority
            weight_damping = 1.5
        elif user_profile['target_stress_relief'] == 'Focused':
            # Adults may prefer more resistance for focus
            weight_thickness = 1.0
            weight_curvature = 0.8
            weight_flexibility = 1.0
            weight_damping = 2.0  # Highest priority
        elif user_profile['target_stress_relief'] == 'Gentle':
            # Elderly users need gentle resistance
            weight_thickness = 1.5
            weight_curvature = 0.5
            weight_flexibility = 0.8
            weight_damping = 2.0  # Highest priority
        elif user_profile['target_stress_relief'] == 'Therapeutic':
            # Therapeutic uses benefit from specific resistance patterns
            weight_thickness = 1.2
            weight_curvature = 1.5
            weight_flexibility = 1.8
            weight_damping = 1.5
        elif user_profile['target_stress_relief'] == 'Energetic':
            # Teens prefer more dynamic response
            weight_thickness = 0.8
            weight_curvature = 1.2
            weight_flexibility = 1.5
            weight_damping = 1.0
        else:  # Default
            weight_thickness = 1.0
            weight_curvature = 1.0
            weight_flexibility = 1.0
            weight_damping = 1.0
        
        # Calculate weighted sum of squared errors
        cost = (
            weight_thickness * (thickness - target_thickness)**2 +
            weight_curvature * (curvature - target_curvature)**2 +
            weight_flexibility * (flexibility - target_flexibility)**2 +
            weight_damping * (damping - target_damping)**2
        )
        
        # Add constraint penalties (soft constraints)
        # Enforce max force requirement
        estimated_force = thickness * (1 - flexibility) * (1 + damping)
        if estimated_force > user_profile['max_force_required']:
            cost += 5.0 * (estimated_force - user_profile['max_force_required'])**2
        
        # Size constraint based on user preference
        size_deviation = abs(thickness - target_thickness * user_profile['size_factor'])
        cost += 2.0 * size_deviation
        
        return cost

    def optimize_model(self):
        # Get current user profile
        current_profile = self.user_profiles[self.current_user]
        
        initial_guess = [self.thickness, self.curvature, self.flexibility, self.damping]
        
        # Define bounds based on user group
        if self.current_user == 'Child':
            bounds = [(3.0, 5.0), (0.3, 0.7), (0.7, 0.9), (0.03, 0.1)]
        elif self.current_user == 'Elderly':
            bounds = [(4.0, 6.0), (-0.1, 0.2), (0.2, 0.4), (0.15, 0.3)]
        elif self.current_user == 'Teen':
            bounds = [(4.0, 6.0), (0.2, 0.5), (0.5, 0.7), (0.05, 0.15)]
        elif self.current_user == 'Therapy':
            bounds = [(4.5, 6.5), (0.3, 0.6), (0.6, 0.8), (0.1, 0.2)]
        else:  # Adult or default
            bounds = [(5.0, 7.0), (0.0, 0.4), (0.4, 0.6), (0.08, 0.15)]
        
        # Create an objective function that captures the profile
        def obj_func(x):
            return self.objective(x, current_profile)
        
        result = minimize(obj_func, initial_guess, method='L-BFGS-B', bounds=bounds)
        
        # Apply small random variations to prevent identical results
        random_factor = 0.02  # 2% random variation
        self.thickness = result.x[0] * (1 + (random.random() - 0.5) * 2 * random_factor)
        self.curvature = result.x[1] * (1 + (random.random() - 0.5) * 2 * random_factor)
        self.flexibility = result.x[2] * (1 + (random.random() - 0.5) * 2 * random_factor)
        self.damping = result.x[3] * (1 + (random.random() - 0.5) * 2 * random_factor)
        
        # Keep within bounds
        self.thickness = max(bounds[0][0], min(bounds[0][1], self.thickness))
        self.curvature = max(bounds[1][0], min(bounds[1][1], self.curvature))
        self.flexibility = max(bounds[2][0], min(bounds[2][1], self.flexibility))
        self.damping = max(bounds[3][0], min(bounds[3][1], self.damping))
        
        self.refresh_parameters(self.thickness, self.curvature, self.flexibility, self.damping)
        self.apply_geometry_update()

    def simulate_stress_response(self):
        """Simulate how the toy responds to stress based on current parameters"""
        applied_force = 10.0  # Standard test force
        
        # Calculate deformation based on parameters
        stiffness = (1 - self.flexibility) * self.thickness
        deformation = applied_force / (stiffness + 0.01)  # Avoid division by zero
        
        # Calculate energy absorption (damping)
        energy_absorbed = applied_force * deformation * self.damping
        
        # Calculate recovery time
        recovery_time = deformation * (1 - self.damping) * 2.0
        
        # Calculate stress relief score based on user profile
        user_profile = self.user_profiles[self.current_user]
        
        if user_profile['target_stress_relief'] == 'Playful':
            # Children enjoy quick response and less resistance
            stress_relief_score = (energy_absorbed * 0.5 + (1/recovery_time) * 5.0) * 10
        elif user_profile['target_stress_relief'] == 'Focused':
            # Adults may prefer more resistance for focus
            stress_relief_score = (energy_absorbed * 2.0 + deformation * 0.5) * 10
        elif user_profile['target_stress_relief'] == 'Gentle':
            # Elderly users need gentle resistance
            stress_relief_score = (deformation * 2.0 + recovery_time * 0.5) * 10
        elif user_profile['target_stress_relief'] == 'Therapeutic':
            # Therapeutic uses benefit from specific patterns
            stress_relief_score = (energy_absorbed * 1.5 + recovery_time * 1.5) * 10
        elif user_profile['target_stress_relief'] == 'Energetic':
            # Teens prefer dynamic feedback
            stress_relief_score = (deformation * 1.5 + energy_absorbed * 1.0 + (1/recovery_time) * 2.0) * 8
        else:  # Default
            stress_relief_score = (energy_absorbed + deformation + recovery_time) * 3.3
        
        return {
            'deformation': deformation,
            'energy_absorbed': energy_absorbed,
            'recovery_time': recovery_time,
            'stress_relief_score': min(100, max(0, stress_relief_score)),  # Scale to 0-100
            'estimated_force': self.thickness * (1 - self.flexibility) * (1 + self.damping)
        }
    
    def export_model(self, filename):
        """Export the current model to STL file"""
        combined_mesh = trimesh.util.concatenate(self.components)
        combined_mesh.export(filename)
        return os.path.abspath(filename)