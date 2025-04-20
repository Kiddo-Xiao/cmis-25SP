import trimesh
import sys
import os

def convert_stl_to_obj(input_path, output_path):
    try:
        # Load the STL file
        mesh = trimesh.load(input_path)

        # Check if the file was loaded correctly
        if not isinstance(mesh, trimesh.Trimesh):
            raise ValueError('The provided file is not a valid STL mesh.')

        # Export the mesh to OBJ format
        mesh.export(output_path)

        print(f"Conversion successful! The file has been saved to: {output_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == '__main__':

    input_file = 'models/toy_complex_simplified.stl'
    output_file = 'models/toy_complex_simplified.obj'

    if not os.path.exists(input_file):
        print(f"Input file {input_file} does not exist.")
        sys.exit(1)

    convert_stl_to_obj(input_file, output_file)
