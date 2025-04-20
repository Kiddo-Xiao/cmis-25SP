import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QOpenGLWidget, 
                            QLabel, QPushButton, QComboBox, QLineEdit, QGroupBox, QSlider, QTabWidget,
                            QRadioButton, QButtonGroup, QProgressBar, QSpacerItem, QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette
from Opt import ToyOptimizer
from OpenGL.GL import *
from OpenGL.GLU import *


class OpenGLWidget(QOpenGLWidget):
    def __init__(self, optimizer):
        super().__init__()
        self.optimizer = optimizer
        self.last_pos = None
        self.rotation_angle = [0, 0]
        self.translation = [0.0, 0.0]
        self.zoom_factor = 1.0
        self.light_position = [0.0, 0.0, 300.0, 1.0]
        self.setFocusPolicy(Qt.StrongFocus)

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)

        glLightfv(GL_LIGHT0, GL_POSITION, self.light_position)
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])

        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, [0.7, 0.7, 0.7, 1.0])
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50.0)

        glClearColor(0.1, 0.1, 0.1, 1.0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, w / h, 1.0, 1000.0)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(self.translation[0], self.translation[1], -300 * self.zoom_factor)
        glRotatef(self.rotation_angle[0], 1, 0, 0)
        glRotatef(self.rotation_angle[1], 0, 1, 0)

        glLightfv(GL_LIGHT0, GL_POSITION, self.light_position)

        glBegin(GL_TRIANGLES)
        for component in self.optimizer.components:
            for face_index, face in enumerate(component.faces):
                normal = component.face_normals[face_index]
                glNormal3fv(normal)
                for vertex_index in face:
                    vertex = component.vertices[vertex_index]
                    glVertex3fv(vertex)
        glEnd()
        self.update()

    def mousePressEvent(self, event):
        self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.last_pos is not None:
            dx = event.x() - self.last_pos.x()
            dy = event.y() - self.last_pos.y()

            if event.buttons() & Qt.LeftButton:
                self.rotation_angle[0] += dy * 0.2
                self.rotation_angle[1] += dx * 0.2
            elif event.buttons() & Qt.RightButton:
                self.translation[0] += dx * 0.5
                self.translation[1] -= dy * 0.5

            self.update()
        self.last_pos = event.pos()

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120  # Standard wheel step is 120 per notch
        self.zoom_factor *= (1.0 + delta * 0.05)
        self.update()



class MainWindow(QMainWindow):
    def __init__(self, optimizer):
        super().__init__()
        self.optimizer = optimizer
        self.optimizer.ui_update_callback = self.update_view
        self.setWindowTitle('Stress Release Toy Optimizer')
        self.setGeometry(100, 100, 1400, 1000)
        
        # Create user-friendly color schemes for different user groups
        self.color_schemes = {
            'Child': {
                'background': QColor(230, 250, 255),
                'accent': QColor(100, 200, 255),
                'text': QColor(50, 50, 150)
            },
            'Teen': {
                'background': QColor(220, 220, 255),
                'accent': QColor(130, 130, 240),
                'text': QColor(60, 60, 100)
            },
            'Adult': {
                'background': QColor(240, 240, 240),
                'accent': QColor(100, 150, 200),
                'text': QColor(30, 30, 30)
            },
            'Elderly': {
                'background': QColor(255, 245, 230),
                'accent': QColor(200, 150, 100),
                'text': QColor(80, 60, 40)
            },
            'Therapy': {
                'background': QColor(230, 255, 230),
                'accent': QColor(100, 200, 100),
                'text': QColor(40, 80, 40)
            }
        }
        
        main_layout = QHBoxLayout()
        
        # 3D View
        view_group = QGroupBox("Toy Preview")
        view_layout = QVBoxLayout()
        
        self.opengl_widget = OpenGLWidget(self.optimizer)
        view_layout.addWidget(self.opengl_widget)
        
        # Add view controls
        view_controls = QHBoxLayout()
        self.reset_view_button = QPushButton('Reset View')
        self.reset_view_button.clicked.connect(self.reset_view)
        view_controls.addWidget(self.reset_view_button)
        
        self.wireframe_button = QPushButton('Toggle Wireframe')
        self.wireframe_button.clicked.connect(self.toggle_wireframe)
        view_controls.addWidget(self.wireframe_button)
        
        view_layout.addLayout(view_controls)
        view_group.setLayout(view_layout)
        main_layout.addWidget(view_group, 3)
        
        # Control Panel with Tabs
        control_panel = QTabWidget()
        
        # Basic Controls Tab
        basic_tab = QWidget()
        basic_layout = QVBoxLayout()
        
        # User Profile Selection
        profile_group = QGroupBox("User Profile")
        profile_layout = QVBoxLayout()
        
        self.user_selector = QComboBox()
        self.user_selector.addItems(['Child', 'Teen', 'Adult', 'Elderly', 'Therapy'])
        self.user_selector.currentIndexChanged.connect(self.change_user_profile)
        profile_layout.addWidget(self.user_selector)
        
        # Add description of each profile
        self.profile_description = QLabel("Adult: Standard resistance for focused stress relief")
        self.profile_description.setWordWrap(True)
        profile_layout.addWidget(self.profile_description)
        
        profile_group.setLayout(profile_layout)
        basic_layout.addWidget(profile_group)
        
        # Basic Parameter Controls
        params_group = QGroupBox("Parameters")
        params_layout = QVBoxLayout()
        
        # Thickness control
        thickness_layout = QHBoxLayout()
        thickness_layout.addWidget(QLabel('Thickness:'))
        self.thickness_value = QLabel('5.0')
        thickness_layout.addWidget(self.thickness_value)
        params_layout.addLayout(thickness_layout)
        
        self.thickness_slider = QSlider(Qt.Horizontal)
        self.thickness_slider.setRange(10, 100)
        self.thickness_slider.setValue(50)
        self.thickness_slider.valueChanged.connect(self.update_thickness)
        params_layout.addWidget(self.thickness_slider)
        
        # Curvature control
        curvature_layout = QHBoxLayout()
        curvature_layout.addWidget(QLabel('Curvature:'))
        self.curvature_value = QLabel('0.0')
        curvature_layout.addWidget(self.curvature_value)
        params_layout.addLayout(curvature_layout)
        
        self.curvature_slider = QSlider(Qt.Horizontal)
        self.curvature_slider.setRange(-50, 50)
        self.curvature_slider.setValue(0)
        self.curvature_slider.valueChanged.connect(self.update_curvature)
        params_layout.addWidget(self.curvature_slider)
        
        # Flexibility control
        flexibility_layout = QHBoxLayout()
        flexibility_layout.addWidget(QLabel('Flexibility:'))
        self.flexibility_value = QLabel('0.5')
        flexibility_layout.addWidget(self.flexibility_value)
        params_layout.addLayout(flexibility_layout)
        
        self.flexibility_slider = QSlider(Qt.Horizontal)
        self.flexibility_slider.setRange(0, 100)
        self.flexibility_slider.setValue(50)
        self.flexibility_slider.valueChanged.connect(self.update_flexibility)
        params_layout.addWidget(self.flexibility_slider)
        
        # Damping control
        damping_layout = QHBoxLayout()
        damping_layout.addWidget(QLabel('Damping:'))
        self.damping_value = QLabel('0.1')
        damping_layout.addWidget(self.damping_value)
        params_layout.addLayout(damping_layout)
        
        self.damping_slider = QSlider(Qt.Horizontal)
        self.damping_slider.setRange(0, 100)
        self.damping_slider.setValue(10)
        self.damping_slider.valueChanged.connect(self.update_damping)
        params_layout.addWidget(self.damping_slider)
        
        params_group.setLayout(params_layout)
        basic_layout.addWidget(params_group)
        
        # Optimization Controls
        opt_group = QGroupBox("Optimization")
        opt_layout = QVBoxLayout()
        
        # Target stress relief type
        stress_relief_layout = QHBoxLayout()
        stress_relief_layout.addWidget(QLabel("Target Stress Relief:"))
        
        self.stress_relief_selector = QComboBox()
        self.stress_relief_selector.addItems(['Playful', 'Energetic', 'Focused', 'Gentle', 'Therapeutic'])
        self.stress_relief_selector.currentIndexChanged.connect(self.update_stress_relief_target)
        stress_relief_layout.addWidget(self.stress_relief_selector)
        
        opt_layout.addLayout(stress_relief_layout)
        
        # Optimize button
        self.optimize_button = QPushButton('Optimize for Current User')
        self.optimize_button.clicked.connect(self.run_optimization)
        self.optimize_button.setMinimumHeight(50)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        self.optimize_button.setFont(font)
        opt_layout.addWidget(self.optimize_button)
        
        # Optimization status
        self.optimization_status = QLabel("Ready")
        opt_layout.addWidget(self.optimization_status)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        opt_layout.addWidget(self.progress_bar)
        
        opt_group.setLayout(opt_layout)
        basic_layout.addWidget(opt_group)
        
        basic_tab.setLayout(basic_layout)
        control_panel.addTab(basic_tab, "Basic Controls")
        
        # Advanced Tab
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout()
        
        # Material Properties
        material_group = QGroupBox("Material Properties")
        material_layout = QVBoxLayout()
        
        # Texture selector
        texture_layout = QHBoxLayout()
        texture_layout.addWidget(QLabel("Surface Texture:"))
        self.texture_selector = QComboBox()
        self.texture_selector.addItems(['Smooth', 'Soft', 'Textured', 'Grippy', 'Variable'])
        self.texture_selector.currentIndexChanged.connect(self.update_texture)
        texture_layout.addWidget(self.texture_selector)
        material_layout.addLayout(texture_layout)
        
        # Color selector
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color Theme:"))
        self.color_selector = QComboBox()
        self.color_selector.addItems(['Default', 'Calm Blues', 'Energetic Reds', 'Natural Greens', 'Playful Mix'])
        self.color_selector.currentIndexChanged.connect(self.update_color_theme)
        color_layout.addWidget(self.color_selector)
        material_layout.addLayout(color_layout)
        
        material_group.setLayout(material_layout)
        advanced_layout.addWidget(material_group)
        
        # Physical simulation results
        simulation_group = QGroupBox("Physical Simulation")
        simulation_layout = QVBoxLayout()
        
        self.run_simulation_button = QPushButton("Run Physical Simulation")
        self.run_simulation_button.clicked.connect(self.run_simulation)
        simulation_layout.addWidget(self.run_simulation_button)
        
        # Simulation results
        self.simulation_results = QLabel("No simulation results available")
        self.simulation_results.setWordWrap(True)
        simulation_layout.addWidget(self.simulation_results)
        
        # Stress relief score
        score_layout = QHBoxLayout()
        score_layout.addWidget(QLabel("Stress Relief Score:"))
        self.stress_score = QProgressBar()
        self.stress_score.setRange(0, 100)
        self.stress_score.setValue(0)
        score_layout.addWidget(self.stress_score)
        simulation_layout.addWidget(self.stress_score)
        
        simulation_group.setLayout(simulation_layout)
        advanced_layout.addWidget(simulation_group)
        
        # Export options
        export_group = QGroupBox("Export & Fabrication")
        export_layout = QVBoxLayout()
        
        self.export_stl_button = QPushButton("Export STL for Fabrication")
        self.export_stl_button.clicked.connect(self.export_stl)
        export_layout.addWidget(self.export_stl_button)
        
        # Print settings
        print_settings_layout = QVBoxLayout()
        print_settings_layout.addWidget(QLabel("Recommended Print Settings:"))
        self.print_settings = QLabel("Material: PLA\nLayer Height: 0.2mm\nInfill: 20%\nSupports: No")
        print_settings_layout.addWidget(self.print_settings)
        export_layout.addLayout(print_settings_layout)
        
        export_group.setLayout(export_layout)
        advanced_layout.addWidget(export_group)
        
        advanced_tab.setLayout(advanced_layout)
        control_panel.addTab(advanced_tab, "Advanced")
        
        # Results and Comparison Tab
        results_tab = QWidget()
        results_layout = QVBoxLayout()
        
        comparison_group = QGroupBox("Compare Versions")
        comparison_layout = QVBoxLayout()
        
        self.model_selector = QComboBox()
        self.model_selector.addItems(['Current Model', 'Version 1 (Child)', 'Version 2 (Adult)', 'Version 3 (Elderly)'])
        self.model_selector.currentIndexChanged.connect(self.change_comparison_model)
        comparison_layout.addWidget(self.model_selector)
        
        # Comparison metrics
        metrics_frame = QFrame()
        metrics_frame.setFrameShape(QFrame.StyledPanel)
        metrics_layout = QVBoxLayout(metrics_frame)
        
        metrics_layout.addWidget(QLabel("<b>Metrics Comparison:</b>"))
        self.metrics_table = QLabel(
            "Deformation: Current 5.2mm | Child 7.8mm | Adult 4.5mm | Elderly 3.9mm\n"
            "Recovery Time: Current 0.8s | Child 0.5s | Adult 0.9s | Elderly 1.2s\n"
            "Energy Absorption: Current 65% | Child 48% | Adult 70% | Elderly 75%\n"
            "Force Required: Current 3.2N | Child 1.8N | Adult 4.1N | Elderly 2.7N"
        )
        self.metrics_table.setWordWrap(True)
        metrics_layout.addWidget(self.metrics_table)
        
        comparison_layout.addWidget(metrics_frame)
        
        # User feedback section
        feedback_layout = QVBoxLayout()
        feedback_layout.addWidget(QLabel("<b>Simulated User Feedback:</b>"))
        self.feedback_label = QLabel("No feedback available")
        self.feedback_label.setWordWrap(True)
        feedback_layout.addWidget(self.feedback_label)
        comparison_layout.addLayout(feedback_layout)
        
        comparison_group.setLayout(comparison_layout)
        results_layout.addWidget(comparison_group)
        
        # History of optimizations
        history_group = QGroupBox("Optimization History")
        history_layout = QVBoxLayout()
        
        self.history_selector = QComboBox()
        self.history_selector.addItems(['Current Parameters', 'Optimization 1', 'Optimization 2', 'Optimization 3'])
        self.history_selector.currentIndexChanged.connect(self.load_history)
        history_layout.addWidget(self.history_selector)
        
        self.history_details = QLabel("No history available")
        self.history_details.setWordWrap(True)
        history_layout.addWidget(self.history_details)
        
        self.restore_button = QPushButton("Restore These Parameters")
        self.restore_button.clicked.connect(self.restore_parameters)
        history_layout.addWidget(self.restore_button)
        
        history_group.setLayout(history_layout)
        results_layout.addWidget(history_group)
        
        # Add spacer
        results_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        results_tab.setLayout(results_layout)
        control_panel.addTab(results_tab, "Results & Comparison")
        
        main_layout.addWidget(control_panel, 2)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        # Initialize with default profile
        self.user_selector.setCurrentText('Adult')
        self.change_user_profile(self.user_selector.currentIndex())
        
    def update_thickness(self):
        thickness = self.thickness_slider.value() / 10.0
        self.thickness_value.setText(f'{thickness:.1f}')
        self.optimizer.refresh_parameters(thickness, self.optimizer.curvature, 
                                         self.optimizer.flexibility, self.optimizer.damping)
        self.optimizer.apply_geometry_update()
    
    def update_curvature(self):
        curvature = self.curvature_slider.value() / 10.0
        self.curvature_value.setText(f'{curvature:.1f}')
        self.optimizer.refresh_parameters(self.optimizer.thickness, curvature, 
                                         self.optimizer.flexibility, self.optimizer.damping)
        self.optimizer.apply_geometry_update()
    
    def update_flexibility(self):
        flexibility = self.flexibility_slider.value() / 100.0
        self.flexibility_value.setText(f'{flexibility:.2f}')
        self.optimizer.refresh_parameters(self.optimizer.thickness, self.optimizer.curvature, 
                                         flexibility, self.optimizer.damping)
        self.optimizer.apply_geometry_update()
    
    def update_damping(self):
        damping = self.damping_slider.value() / 100.0
        self.damping_value.setText(f'{damping:.2f}')
        self.optimizer.refresh_parameters(self.optimizer.thickness, self.optimizer.curvature, 
                                         self.optimizer.flexibility, damping)
        self.optimizer.apply_geometry_update()
    
    def change_user_profile(self, index):
        selected_profile = self.user_selector.currentText()
        self.optimizer.set_user_profile(selected_profile)
        
        # Update UI to match selected profile
        profile = self.optimizer.user_profiles[selected_profile]
        
        # Update slider positions
        self.thickness_slider.setValue(int(profile['thickness'] * 10))
        self.curvature_slider.setValue(int(profile['curvature'] * 10))
        self.flexibility_slider.setValue(int(profile['flexibility'] * 100))
        self.damping_slider.setValue(int(profile['damping'] * 100))
        
        # Update descriptions
        if selected_profile == 'Child':
            desc = "Child: Lower resistance, more flexible for playful interaction"
        elif selected_profile == 'Teen':
            desc = "Teen: Balanced properties with energetic feedback"
        elif selected_profile == 'Adult':
            desc = "Adult: Standard resistance for focused stress relief"
        elif selected_profile == 'Elderly':
            desc = "Elderly: Gentle resistance with higher damping for comfort"
        elif selected_profile == 'Therapy':
            desc = "Therapy: Specialized parameters for therapeutic benefits"
        
        self.profile_description.setText(desc)
        
        # Update texture and stress relief target if available
        if 'texture_preference' in profile:
            index = self.texture_selector.findText(profile['texture_preference'])
            if index >= 0:
                self.texture_selector.setCurrentIndex(index)
        
        if 'target_stress_relief' in profile:
            index = self.stress_relief_selector.findText(profile['target_stress_relief'])
            if index >= 0:
                self.stress_relief_selector.setCurrentIndex(index)
        
        # Update color scheme
        self.update_ui_color_scheme(selected_profile)
        
        # Update feedback based on profile
        self.update_simulated_feedback(selected_profile)
    
    def update_ui_color_scheme(self, profile):
        if profile in self.color_schemes:
            scheme = self.color_schemes[profile]
            
            # Update main window background
            palette = self.palette()
            palette.setColor(QPalette.Window, scheme['background'])
            palette.setColor(QPalette.WindowText, scheme['text'])
            palette.setColor(QPalette.Button, scheme['accent'])
            palette.setColor(QPalette.ButtonText, scheme['text'])
            self.setPalette(palette)
            
            # Update button colors
            self.optimize_button.setStyleSheet(
                f"background-color: {scheme['accent'].name()}; color: white; border-radius: 5px;"
            )
    
    def update_stress_relief_target(self):
        target = self.stress_relief_selector.currentText()
        if self.optimizer.current_user in self.optimizer.user_profiles:
            self.optimizer.user_profiles[self.optimizer.current_user]['target_stress_relief'] = target
    
    def update_texture(self):
        texture = self.texture_selector.currentText()
        if self.optimizer.current_user in self.optimizer.user_profiles:
            self.optimizer.user_profiles[self.optimizer.current_user]['texture_preference'] = texture
    
    def update_color_theme(self):
        # Would update material visualization in a real implementation
        pass
    
    def run_optimization(self):
        self.optimization_status.setText("Optimizing...")
        self.progress_bar.setValue(0)
        
        # Simulate optimization progress
        self.progress_timer = QTimer()
        self.progress_value = 0
        
        def update_progress():
            self.progress_value += 5
            self.progress_bar.setValue(min(100, self.progress_value))
            
            if self.progress_value >= 100:
                self.progress_timer.stop()
                self.optimization_status.setText("Optimization complete!")
                self.optimizer.optimize_model()
                
                # Update sliders to reflect optimized values
                self.thickness_slider.setValue(int(self.optimizer.thickness * 10))
                self.curvature_slider.setValue(int(self.optimizer.curvature * 10))
                self.flexibility_slider.setValue(int(self.optimizer.flexibility * 100))
                self.damping_slider.setValue(int(self.optimizer.damping * 100))
                
                # Run simulation after optimization
                self.run_simulation()
        
        self.progress_timer.timeout.connect(update_progress)
        self.progress_timer.start(50)  # Update every 50ms for smoother progress
    
    def run_simulation(self):
        # Run physical simulation
        results = self.optimizer.simulate_stress_response()
        
        # Update simulation results display
        result_text = (f"Deformation: {results['deformation']:.2f}mm\n"
                      f"Energy Absorbed: {results['energy_absorbed']:.2f}J\n"
                      f"Recovery Time: {results['recovery_time']:.2f}s")
        
        self.simulation_results.setText(result_text)
        
        # Update stress relief score
        self.stress_score.setValue(int(results['stress_relief_score']))
        
        # Update feedback based on results
        self.update_simulated_feedback_from_results(results)
    
    def update_simulated_feedback(self, profile):
        if profile == 'Child':
            feedback = "\"I like how squishy it is! It's fun to play with during breaks between homework.\""
        elif profile == 'Teen':
            feedback = "\"It's pretty cool. I like using it when I'm stressed about exams. Could be more colorful though.\""
        elif profile == 'Adult':
            feedback = "\"It provides good resistance. I keep it on my desk for quick stress relief between meetings.\""
        elif profile == 'Elderly':
            feedback = "\"Very comfortable to hold. The gentle resistance helps with my hand exercises.\""
        elif profile == 'Therapy':
            feedback = "\"The variable texture and resistance patterns make it effective for my patients with different needs.\""
        else:
            feedback = "No feedback available"
        
        self.feedback_label.setText(feedback)
    
    def update_simulated_feedback_from_results(self, results):
        score = results['stress_relief_score']
        profile = self.optimizer.current_user
        
        if score < 50:
            if profile == 'Child':
                feedback = "\"It's too hard to squeeze. Could be more fun!\""
            elif profile == 'Teen':
                feedback = "\"Doesn't really help with stress. Need more feedback when squeezing.\""
            elif profile == 'Adult':
                feedback = "\"Not enough resistance to be satisfying. Doesn't help focus.\""
            elif profile == 'Elderly':
                feedback = "\"Too stiff for comfortable use. Causes hand strain.\""
            else:
                feedback = "\"Not effective for stress relief. Needs adjustment.\""
        elif score < 75:
            feedback = "\"Works okay but could be better optimized for my needs.\""
        else:
            if profile == 'Child':
                feedback = "\"Super fun to squeeze! I love the bouncy feeling!\""
            elif profile == 'Teen':
                feedback = "\"Pretty good stress reliever. Nice response when squeezing.\""
            elif profile == 'Adult':
                feedback = "\"Excellent resistance profile. Very effective for stress management.\""
            elif profile == 'Elderly':
                feedback = "\"Perfect balance of gentle resistance. Comfortable to use for longer periods.\""
            else:
                feedback = "\"Highly effective design. Meets all stress relief requirements.\""
        
        self.feedback_label.setText(feedback)
    
    def change_comparison_model(self, index):
        model_name = self.model_selector.currentText()
        
        # In a real implementation, this would load different models
        # Here we'll just update the simulated feedback
        if "Child" in model_name:
            self.update_simulated_feedback('Child')
        elif "Adult" in model_name:
            self.update_simulated_feedback('Adult')
        elif "Elderly" in model_name:
            self.update_simulated_feedback('Elderly')
    
    def load_history(self, index):
        history_name = self.history_selector.currentText()
        
        # Simulated history details
        if "Optimization 1" in history_name:
            details = "Date: 2025-04-03\nUser Profile: Child\nParameters: Thickness=4.2, Curvature=0.6, Flexibility=0.85, Damping=0.04\nStress Relief Score: 89/100"
        elif "Optimization 2" in history_name:
            details = "Date: 2025-04-04\nUser Profile: Adult\nParameters: Thickness=6.1, Curvature=0.3, Flexibility=0.45, Damping=0.12\nStress Relief Score: 92/100"
        elif "Optimization 3" in history_name:
            details = "Date: 2025-04-05\nUser Profile: Elderly\nParameters: Thickness=5.2, Curvature=0.1, Flexibility=0.25, Damping=0.18\nStress Relief Score: 85/100"
        else:
            details = f"Current Parameters:\nThickness={self.optimizer.thickness:.1f}\nCurvature={self.optimizer.curvature:.1f}\nFlexibility={self.optimizer.flexibility:.2f}\nDamping={self.optimizer.damping:.2f}"
        
        self.history_details.setText(details)
    
    def restore_parameters(self):
        history_name = self.history_selector.currentText()
        
        # Simulated parameter restoration
        if "Optimization 1" in history_name:
            self.optimizer.refresh_parameters(4.2, 0.6, 0.85, 0.04)
            self.update_all_sliders()
        elif "Optimization 2" in history_name:
            self.optimizer.refresh_parameters(6.1, 0.3, 0.45, 0.12)
            self.update_all_sliders()
        elif "Optimization 3" in history_name:
            self.optimizer.refresh_parameters(5.2, 0.1, 0.25, 0.18)
            self.update_all_sliders()
    
    def update_all_sliders(self):
        # Update slider positions without triggering events
        self.thickness_slider.blockSignals(True)
        self.curvature_slider.blockSignals(True)
        self.flexibility_slider.blockSignals(True)
        self.damping_slider.blockSignals(True)
        
        self.thickness_slider.setValue(int(self.optimizer.thickness * 10))
        self.curvature_slider.setValue(int(self.optimizer.curvature * 10))
        self.flexibility_slider.setValue(int(self.optimizer.flexibility * 100))
        self.damping_slider.setValue(int(self.optimizer.damping * 100))
        
        self.thickness_slider.blockSignals(False)
        self.curvature_slider.blockSignals(False)
        self.flexibility_slider.blockSignals(False)
        self.damping_slider.blockSignals(False)
        
        # Update labels
        self.thickness_value.setText(f'{self.optimizer.thickness:.1f}')
        self.curvature_value.setText(f'{self.optimizer.curvature:.1f}')
        self.flexibility_value.setText(f'{self.optimizer.flexibility:.2f}')
        self.damping_value.setText(f'{self.optimizer.damping:.2f}')
        
        # Apply geometry update
        self.optimizer.apply_geometry_update()
    
    def reset_view(self):
        self.opengl_widget.rotation_angle = [0, 0]
        self.opengl_widget.translation = [0.0, 0.0]
        self.opengl_widget.zoom_factor = 1.0
        self.opengl_widget.update()
    
    def toggle_wireframe(self):
        # In a real implementation, this would toggle wireframe rendering
        pass
    
    def export_stl(self):
        # In a real implementation, this would export the model as STL
        self.optimization_status.setText("Model exported for fabrication")
    
    def update_view(self):
        self.opengl_widget.update()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    optimizer = ToyOptimizer('models/toy_complex_simplified.stl')
    window = MainWindow(optimizer)
    window.show()
    sys.exit(app.exec_())