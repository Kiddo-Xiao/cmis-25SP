#include <igl/readOBJ.h>
#include <igl/opengl/glfw/Viewer.h>
#include <igl/opengl/glfw/imgui/ImGuiMenu.h>
#include <igl/opengl/glfw/imgui/ImGuiHelpers.h>
#include <imgui/imgui.h>

#include <iostream>

namespace mesh_viewer {
    int inner_main(int argc, char* argv[]);
}

int main(int argc, char* argv[]) {
    try {
        return mesh_viewer::inner_main(argc, argv);
    }
    catch (char const* x) {
        std::cerr << "Error: " << std::string(x) << std::endl;
    }
    return 1;
}

namespace mesh_viewer {

    igl::opengl::glfw::Viewer viewer;
    igl::opengl::glfw::imgui::ImGuiMenu menu;

    Eigen::MatrixXd V;
    Eigen::MatrixXi F;
    
    double scale = 1.0;
    double rotation_angle = 0.0;
    Eigen::RowVector3d rotation_axis = Eigen::RowVector3d(0, 1, 0);

    void draw_coordinate_indicator() {
        const auto coordinate_indicator = Eigen::MatrixXd::Identity(3, 3);
        viewer.data().add_edges(Eigen::MatrixXd::Zero(3, 3), coordinate_indicator * 0.2, coordinate_indicator);
    }

    void scale_mesh() {
        V *= scale;
        std::cout << "Mesh scaled by " << scale << "x" << std::endl;
    }

    void rotate_mesh() {
        Eigen::Matrix3d rotation_matrix;
        rotation_matrix = Eigen::AngleAxisd(rotation_angle, rotation_axis.normalized()).toRotationMatrix();
        V = (V * rotation_matrix.transpose()).eval();
        std::cout << "Mesh rotated by " << rotation_angle << " radians around axis " << rotation_axis.transpose() << std::endl;
    }

    bool callback_update_view(igl::opengl::glfw::Viewer& viewer) {
        viewer.data().clear();
        draw_coordinate_indicator();
        viewer.data().set_mesh(V, F);
        return false;
    }

    void callback_update_menu() {
        if (ImGui::CollapsingHeader("Mesh Control Panel", ImGuiTreeNodeFlags_DefaultOpen)) {
            ImGui::InputDouble("Scale Factor", &scale);
            if (ImGui::Button("Scale Mesh")) {
                scale_mesh();
            }

            ImGui::InputDouble("Rotation Angle (Radians)", &rotation_angle);
            ImGui::InputDouble("Rotation Axis", rotation_axis.data());
            if (ImGui::Button("Rotate Mesh")) {
                rotate_mesh();
            }
        }
    }

    void viewer_register_callbacks() {
        viewer.callback_pre_draw = callback_update_view;
        menu.callback_draw_viewer_menu = callback_update_menu;

        viewer.core().is_animating = true;
        viewer.core().animation_max_fps = 30.0;
    }

    void initialize_view() {
        viewer.plugins.push_back(&menu);
        viewer.core().background_color.setOnes();
        viewer.resize(1600, 1400);
        viewer_register_callbacks();
    }

    int inner_main(int argc, char* argv[]) {
        initialize_view();
        // igl::readOBJ("../models/final_smart_phone_stand_with_magnetic_joint.obj", V, F);
        igl::readOBJ("../models/optimized_phone_stand.obj", V, F);
        viewer.launch();
    }
}
