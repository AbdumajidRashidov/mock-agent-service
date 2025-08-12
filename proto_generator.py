#!/usr/bin/env python3
"""
Wrapper script to generate protobuf files with warnings suppressed.
"""
import warnings
import sys
import os
import subprocess

# Suppress the specific pkg_resources deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pkg_resources")

# Path to the proto file
proto_path = "../../libs/grpc-protos/agents-serivce.proto"
output_dir = "src/generated"

# Create the output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Build the command to run protoc
cmd = [
    sys.executable,
    "-m", "grpc_tools.protoc",
    f"-I../../libs/grpc-protos",
    f"--python_out={output_dir}",
    f"--grpc_python_out={output_dir}",
    proto_path
]

# Run the protoc command
result = subprocess.run(cmd, check=True)

# Fix imports in the generated files
try:
    grpc_file = f"{output_dir}/agents_serivce_pb2_grpc.py"
    if os.path.exists(grpc_file):
        with open(grpc_file, "r") as f:
            content = f.read()

        content = content.replace("import agents_serivce_pb2", "from . import agents_serivce_pb2")

        with open(grpc_file, "w") as f:
            f.write(content)
        print(f"Fixed imports in {grpc_file}")
    else:
        print(f"Warning: {grpc_file} not found. Check if the protoc command generated the expected files.")
        # List files in the output directory to help diagnose the issue
        print(f"Files in {output_dir}:")
        for file in os.listdir(output_dir):
            print(f"  {file}")
except Exception as e:
    print(f"Error fixing imports: {e}")

print("Proto files generated successfully!")
