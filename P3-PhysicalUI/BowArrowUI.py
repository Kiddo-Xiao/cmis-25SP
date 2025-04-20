import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QComboBox, QSlider, QPushButton, 
                           QSpinBox, QDoubleSpinBox, QGroupBox, QTabWidget,
                           QFormLayout, QFileDialog, QMessageBox, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QPixmap, QImage
import pyqtgraph.opengl as gl
import numpy as np
from BowArrowOpt import BowArrowOptimizer

class BowArrowUI(QMainWindow):
    def __init__(self, model_path):
        super().__init__()
        self.setWindowTitle("Bow Toy Optimizer")
        self.setGeometry(100, 100, 1000, 700)
        
        try:
            self.optimizer = BowArrowOptimizer(model_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load model: {str(e)}")
            sys.exit(1)
        
        # Setup UI components
        self.setup_ui()

        # Set performance range based on physical constraints
        self.update_performance_range()

        # Initialize viewer with model
        self.update_model_view()
        
    # UPDATE: the allowed range of performance metrics based on physical constraints
    def update_performance_range(self):
        ''' ATTENTION: Calculate estimated min/max values for launch speed and draw force Sliders, but these depends 
        on the physical calculations in the optimizer, for example: when we change our mathematical 
        methods to calculate the launch speed(or draw force), the min/max values might not be gotten
        if here we just naively use the min/max values of the bow's physical parameters '''
        min_speed = self.optimizer.estimate_launch_speed(4.0, 0.2, 0.3, 35)  # Minimum parameters
        max_speed = self.optimizer.estimate_launch_speed(7.0, 0.4, 0.9, 20)  # Maximum parameters
        
        min_force = self.optimizer.estimate_draw_force(4.0, 0.2, 0.3, 20)    # Minimum parameters
        max_force = self.optimizer.estimate_draw_force(7.0, 0.4, 0.9, 35)    # Maximum parameters
        
        # Add 10% margin on each side
        min_speed = min_speed * 0.9
        max_speed = max_speed * 1.1
        
        min_force = min_force * 0.9
        max_force = max_force * 1.1
        
        # Update slider ranges
        self.launch_speed_slider.setRange(int(min_speed * 10), int(max_speed * 10))
        self.draw_force_slider.setRange(int(min_force * 10), int(max_force * 10))
        
        # Log the available ranges
        print(f"Performance ranges: Speed {min_speed:.1f}-{max_speed:.1f} m/s, Force {min_force:.1f}-{max_force:.1f} N")

    def update_launch_speed_label(self):
        """Update the label showing target launch speed value"""
        value = self.launch_speed_slider.value() / 10.0  # Convert from scaled int
        self.launch_speed_target_label.setText(f"{value:.1f} m/s")
        
    def update_draw_force_label(self):
        """Update the label showing target draw force value"""
        value = self.draw_force_slider.value() / 10.0  # Convert from scaled int
        self.draw_force_target_label.setText(f"{value:.1f} N")
        
    def optimize_performance(self):
        """Optimize physical parameters to achieve specified performance targets"""
        try:
            # Get targets from sliders
            target_speed = self.launch_speed_slider.value() / 10.0
            target_force = self.draw_force_slider.value() / 10.0
            
            # Get lock states
            lock_speed = self.lock_speed_checkbox.isChecked()
            lock_force = self.lock_force_checkbox.isChecked()
            
            # Call optimizer with performance targets
            self.optimizer.optimize_for_performance(
                target_speed, target_force, 
                lock_speed, lock_force
            )
            
            # Update UI to show new parameters
            self.update_parameter_displays()
            self.update_model_view()
            self.simulate_performance()
            
            QMessageBox.information(self, "Performance Optimization Complete", 
                            "Model has been optimized for your performance targets.")
        except Exception as e:
            QMessageBox.critical(self, "Optimization Error", 
                        f"Failed to optimize for performance: {str(e)}")
    
    def setup_ui(self):
        """Set up the user interface"""
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        
        # Create left panel for controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(400)
        
        # Create right panel for visualization
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        # Create tab widget for different settings
        tab_widget = QTabWidget()
        left_layout.addWidget(tab_widget)
        
        # Create tabs
        config_tab = QWidget()
        results_tab = QWidget()
        tab_widget.addTab(config_tab, "Configure")
        tab_widget.addTab(results_tab, "Results")
        
        # First tab: Setup configure tab
        config_layout = QVBoxLayout(config_tab)
        
        # User profile selection
        profile_group = QGroupBox("User Profile")
        profile_form = QFormLayout(profile_group)
        
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["Child", "Adult", "Professional"])
        self.profile_combo.setCurrentText("Adult")  # Default
        profile_form.addRow("Profile:", self.profile_combo)
        
        # Palm size
        self.palm_size_spin = QDoubleSpinBox()
        self.palm_size_spin.setRange(50, 150)
        self.palm_size_spin.setValue(90)
        self.palm_size_spin.setSuffix(" mm")
        profile_form.addRow("Palm Size:", self.palm_size_spin)
        
        # Speed preference
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["Low", "Medium", "High"])
        self.speed_combo.setCurrentText("Medium")  # Default
        profile_form.addRow("Speed Preference:", self.speed_combo)
        
        config_layout.addWidget(profile_group)
        
        # Apply profile button
        apply_profile_btn = QPushButton("Apply Profile")
        apply_profile_btn.clicked.connect(self.apply_profile)
        config_layout.addWidget(apply_profile_btn)
        
        # Bow params set
        params_group = QGroupBox("Bow Parameters")
        params_form = QFormLayout(params_group)
        
        # Bow thickness
        self.thickness_spin = QDoubleSpinBox()
        self.thickness_spin.setRange(4.0, 9.0)
        self.thickness_spin.setValue(5.0)
        self.thickness_spin.setSingleStep(0.5)
        self.thickness_spin.setSuffix(" mm")
        params_form.addRow("Bow Thickness:", self.thickness_spin)
        
        # UPDATE: hide Bow curvature
        self.curvature_spin = QDoubleSpinBox()
        self.curvature_spin.setRange(0.2, 0.4)
        self.curvature_spin.setValue(0.3)
        self.curvature_spin.setSingleStep(0.01)
        params_form.addRow("Bow Curvature:", self.curvature_spin)
      
        # Limb stiffness
        self.stiffness_spin = QDoubleSpinBox()
        self.stiffness_spin.setRange(0.3, 0.9)
        self.stiffness_spin.setValue(0.6)
        self.stiffness_spin.setSingleStep(0.05)
        params_form.addRow("Limb Stiffness:", self.stiffness_spin)
        
        # Grip width
        self.grip_width_spin = QDoubleSpinBox()
        self.grip_width_spin.setRange(20.0, 35.0)
        self.grip_width_spin.setValue(25.0)
        self.grip_width_spin.setSingleStep(0.5)
        self.grip_width_spin.setSuffix(" mm")
        params_form.addRow("Grip Width:", self.grip_width_spin)
        
        config_layout.addWidget(params_group)
        
        # Apply parameters button
        apply_params_btn = QPushButton("Apply Parameters")
        apply_params_btn.clicked.connect(self.apply_parameters)
        config_layout.addWidget(apply_params_btn)
        
        # UPDATE: more reasonable UI layout
        # Add simulate button
        simulate_btn = QPushButton("Simulate Performance")
        simulate_btn.clicked.connect(self.simulate_performance)
        config_layout.addWidget(simulate_btn)
        # # Optimize button
        # optimize_btn = QPushButton("Optimize Design")
        # optimize_btn.clicked.connect(self.optimize_design)
        # config_layout.addWidget(optimize_btn)

       # Second tab: Setup results tab
        results_layout = QVBoxLayout(results_tab)
        
        performance_group = QGroupBox("Performance Metrics")
        perf_form = QFormLayout(performance_group)
        
        # Performance metrics displays
        self.launch_speed_label = QLabel("0.0 m/s")
        perf_form.addRow("Launch Speed:", self.launch_speed_label)
        
        self.draw_force_label = QLabel("0.0 N")
        perf_form.addRow("Draw Force:", self.draw_force_label)
        
        self.accuracy_label = QLabel("0")
        perf_form.addRow("Accuracy Score:", self.accuracy_label)
        
        self.comfort_label = QLabel("0")
        perf_form.addRow("Comfort Score:", self.comfort_label)
        
        self.safety_label = QLabel("0")
        perf_form.addRow("Safety Score:", self.safety_label)
        
        self.overall_label = QLabel("0")
        perf_form.addRow("Overall Score:", self.overall_label)
        
        results_layout.addWidget(performance_group)
        
        # UPDATE: Performance targets including launch speed and draw force
        performance_targets_group = QGroupBox("Performance Targets")
        targets_form = QFormLayout(performance_targets_group)

        # Launch speed slider and display
        self.launch_speed_slider = QSlider(Qt.Horizontal)
        self.launch_speed_slider.setRange(10, 50)  # 1.0 to 5.0 m/s (scaled by 10)
        self.launch_speed_slider.setValue(30)      # Default 3.0 m/s
        self.launch_speed_target_label = QLabel("3.0 m/s")
        self.launch_speed_slider.valueChanged.connect(self.update_launch_speed_label)
        targets_form.addRow("Target Launch Speed:", self.launch_speed_slider)
        targets_form.addRow("", self.launch_speed_target_label)

        # Draw force slider and display
        self.draw_force_slider = QSlider(Qt.Horizontal)
        self.draw_force_slider.setRange(20, 70)    # 2.0 to 7.0 N (scaled by 10)
        self.draw_force_slider.setValue(40)        # Default 4.0 N
        self.draw_force_target_label = QLabel("4.0 N")
        self.draw_force_slider.valueChanged.connect(self.update_draw_force_label)
        targets_form.addRow("Target Draw Force:", self.draw_force_slider)
        targets_form.addRow("", self.draw_force_target_label)

        # Checkbox to lock specific targets
        self.lock_speed_checkbox = QCheckBox("Prioritize Launch Speed")
        self.lock_force_checkbox = QCheckBox("Prioritize Draw Force") 
        targets_form.addRow(self.lock_speed_checkbox)
        targets_form.addRow(self.lock_force_checkbox)

        # UPDATE: Add User Reminder 
        targets_form.addRow(QLabel("Reminder: Because of the mutual constraints you"))
        targets_form.addRow(QLabel("should ideally fix at most one parameter at a time."))

        # Optimize Performance button
        optimize_performance_btn = QPushButton("Optimize Performance")
        optimize_performance_btn.clicked.connect(self.optimize_performance)
        targets_form.addRow(optimize_performance_btn)

        results_layout.addWidget(performance_targets_group)

        # Export buttons
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        
        export_stl_btn = QPushButton("Export STL")
        export_stl_btn.clicked.connect(self.export_stl)
        export_layout.addWidget(export_stl_btn)
        
        results_layout.addWidget(export_group)
        
        # Setup 3D view in right panel
        view_label = QLabel("3D Model View")
        view_label.setMaximumHeight(30)  # Fix a small height for text label
        right_layout.addWidget(view_label)
        
        # Create OpenGL widget for 3D rendering
        self.view3d = gl.GLViewWidget()
        right_layout.addWidget(self.view3d)
        
        # Add grid for reference
        grid = gl.GLGridItem()
        grid.setSize(200, 200)
        grid.setSpacing(10, 10)
        self.view3d.addItem(grid)
        
        # Add update view button
        update_view_btn = QPushButton("Update View")
        update_view_btn.clicked.connect(self.update_model_view)
        right_layout.addWidget(update_view_btn)
        
    def apply_profile(self):
        """Apply the selected user profile"""
        profile_name = self.profile_combo.currentText()
        palm_size = self.palm_size_spin.value()
        speed_pref = self.speed_combo.currentText()
        
        # Apply to optimizer
        if self.optimizer.set_user_profile(profile_name, palm_size, speed_pref):
            self.update_parameter_displays()
            QMessageBox.information(self, "Profile Applied", 
                                  f"Applied {profile_name} profile with palm size {palm_size}mm "
                                  f"and {speed_pref} speed preference.")
        else:
            QMessageBox.warning(self, "Profile Error", 
                              f"Failed to apply profile {profile_name}.")
    
    def apply_parameters(self):
        """Apply the current parameter values to the optimizer"""
        
        # Reapply current profile first
        profile_name = self.profile_combo.currentText()
        palm_size = self.palm_size_spin.value()
        speed_pref = self.speed_combo.currentText()
        self.optimizer.set_user_profile(profile_name, palm_size, speed_pref)
        
        # Get values from UI
        thickness = self.thickness_spin.value()
        curvature = self.curvature_spin.value()
        stiffness = self.stiffness_spin.value()
        grip_width = self.grip_width_spin.value()
        
        # Apply to optimizer
        self.optimizer.refresh_parameters(
            thickness, curvature, stiffness,
            grip_width, self.optimizer.arrow_length,
            self.optimizer.arrow_weight, self.optimizer.tip_diameter
        )
        
        # Update geometry
        self.optimizer.apply_geometry_update()
        
        # Update view
        self.update_model_view()
        
        QMessageBox.information(self, "Parameters Applied", 
                              "Parameters have been applied to the model.")
    
    # def optimize_design(self):
    #     """Run the optimization algorithm"""
    #     try:
    #         self.optimizer.optimize_model()
    #         self.update_parameter_displays()
    #         self.update_model_view()
    #         self.simulate_performance()  # Update performance metrics
    #         QMessageBox.information(self, "Optimization Complete", 
    #                               "Model has been optimized for the current profile.")
    #     except Exception as e:
    #         QMessageBox.critical(self, "Optimization Error", 
    #                            f"Failed to optimize model: {str(e)}")
    
    def update_parameter_displays(self):
        """Update UI elements with current optimizer parameters"""
        self.thickness_spin.setValue(self.optimizer.bow_thickness)
        self.curvature_spin.setValue(self.optimizer.bow_curvature)
        self.stiffness_spin.setValue(self.optimizer.limb_stiffness)
        self.grip_width_spin.setValue(self.optimizer.grip_width)
    
    def simulate_performance(self):
        """Run performance simulation and update display"""
        try:
            results = self.optimizer.simulate_performance()
            
            # Update display labels
            self.launch_speed_label.setText(f"{results['launch_speed']:.2f} m/s")
            self.draw_force_label.setText(f"{results['draw_force']:.2f} N")
            self.accuracy_label.setText(f"{results['accuracy_score']:.1f}")
            self.comfort_label.setText(f"{results['comfort_score']:.1f}")
            self.safety_label.setText(f"{results['safety_score']:.1f}")
            self.overall_label.setText(f"{results['performance_score']:.1f}")
            
            # Update sliders to match current performance values (added)
            self.launch_speed_slider.setValue(int(results['launch_speed'] * 10))
            self.draw_force_slider.setValue(int(results['draw_force'] * 10))
            
            QMessageBox.information(self, "Simulation Complete", 
                                f"Overall Performance Score: {results['performance_score']:.1f}/100")
        except Exception as e:
            QMessageBox.critical(self, "Simulation Error", 
                            f"Failed to simulate performance: {str(e)}")
            
    def export_stl(self):
        """Export the current model to STL file"""
        try:
            file_dialog = QFileDialog(self)
            file_dialog.setAcceptMode(QFileDialog.AcceptSave)
            file_dialog.setNameFilter("STL Files (*.stl)")
            file_dialog.setDefaultSuffix("stl")
            
            if file_dialog.exec_() == QFileDialog.Accepted:
                file_path = file_dialog.selectedFiles()[0]
                if file_path:
                    exported_path = self.optimizer.export_model(file_path)
                    QMessageBox.information(self, "Export Successful", 
                                          f"Model exported to:\n{exported_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", 
                               f"Failed to export model: {str(e)}")
    
    def update_model_view(self):
        """Update the 3D model display"""
        try:
            # Clear existing items (except grid which is item 0)
            for i in range(len(self.view3d.items)-1, 0, -1):
                self.view3d.removeItem(self.view3d.items[i])
            
            # Create mesh data from optimizer's current model
            verts = []
            faces = []
            colors = []
            
            # Process each component
            offset = 0
            for i, component in enumerate(self.optimizer.components):
                mesh_verts = np.array(component.vertices)
                mesh_faces = np.array(component.faces)
                
                # Add vertices to the list
                verts.append(mesh_verts)
                
                # Adjust face indices
                mesh_faces = mesh_faces + offset
                faces.append(mesh_faces)
                
                # Create colors for this component (different color for each component)
                component_color = [0.7, 0.3, 0.3, 1.0] if i == 0 else [0.3, 0.5, 0.7, 1.0]
                component_colors = np.tile(component_color, (len(mesh_verts), 1))
                colors.append(component_colors)
                
                offset += len(mesh_verts)
            
            # Combine all arrays
            if verts:
                verts = np.vstack(verts)
                faces = np.vstack(faces) if faces else np.array([])
                colors = np.vstack(colors) if colors else np.array([])
                
                # Create mesh item
                mesh = gl.GLMeshItem(
                    vertexes=verts, 
                    faces=faces, 
                    faceColors=colors,
                    smooth=True,
                    drawEdges=True
                )
                self.view3d.addItem(mesh)
                
                # Center view
                self.view3d.setCameraPosition(distance=150)
        except Exception as e:
            QMessageBox.warning(self, "Visualization Error", 
                              f"Failed to update 3D view: {str(e)}\n"
                              "The optimization will still work.")

def main():
    # Make sure required directories exist
    os.makedirs("models", exist_ok=True)
    
    # Check if model file exists
    model_path = 'models/Bow.stl'
    # model_path = 'models/Bow_Arrow_Combined.stl'
    if not os.path.exists(model_path):
        print(f"Warning: Model file not found at {model_path}")
        print("Please place your model file in the models directory.")
    
    # Start the application
    app = QApplication(sys.argv)
    window = BowArrowUI(model_path)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()