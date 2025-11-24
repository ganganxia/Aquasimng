#!/usr/bin/env python3
"""
Run ALOHA simulation and print results script.

This script:
1. Executes ns3 "AlohaGridTest" in the ns-3.40 directory
2. Runs scripts/print_results_aloha.py to process results
3. Provides option to output directly to stdout instead of files
4. Allows modification of n_nodes and lambda parameters
"""

import os
import sys
import argparse
import subprocess
import re
import shutil


import glob


def clear_generated_files():
    """Clear generated trace and result files."""
    # Clear trace files in ns-3.40 directory (../../)
    trace_pattern = "../../aloha-density-trace-*.asc"
    trace_files = glob.glob(trace_pattern)
    for file in trace_files:
        try:
            os.remove(file)
            print(f"Removed trace file: {file}")
        except OSError as e:
            print(f"Error removing {file}: {e}")
    
    # Clear result files in current directory
    result_pattern = "aloha-density-*.txt"
    result_files = glob.glob(result_pattern)
    for file in result_files:
        try:
            os.remove(file)
            print(f"Removed result file: {file}")
        except OSError as e:
            print(f"Error removing {file}: {e}")
    
    print("Cleanup completed!")


def update_aloha_cc(n_nodes, lambda_val):
    """Update examples/aloha_grid_test.cc with new parameters."""
    cc_file = "examples/aloha_grid_test.cc"
    
    if not os.path.exists(cc_file):
        print(f"Error: {cc_file} not found!")
        return False
    
    with open(cc_file, 'r') as f:
        content = f.read()
    
    # Update n_nodes
    content = re.sub(r'int n_nodes = \d+;', f'int n_nodes = {n_nodes};', content)
    
    # Update lambda
    content = re.sub(r'double lambda = [\d\.]+;', f'double lambda = {lambda_val};', content)
    
    with open(cc_file, 'w') as f:
        f.write(content)
    
    print(f"Updated {cc_file}: n_nodes={n_nodes}, lambda={lambda_val}")
    return True


def update_print_script(n_nodes_list, lambda_list):
    """Update scripts/print_results_aloha.py with new parameters."""
    py_file = "scripts/print_results_aloha.py"
    
    if not os.path.exists(py_file):
        print(f"Error: {py_file} not found!")
        return False
    
    with open(py_file, 'r') as f:
        content = f.read()
    
    # Update NODES list
    nodes_str = str(n_nodes_list)
    content = re.sub(r'NODES = \[[^\]]*\]', f'NODES = {nodes_str}', content)
    
    # Update LAMBDAS list (convert to strings with proper formatting)
    lambda_str_list = [f"'{l:.4f}'" for l in lambda_list]
    lambdas_str = '[' + ', '.join(lambda_str_list) + ']'
    content = re.sub(r'LAMBDAS = \[[^\]]*\]', f'LAMBDAS = {lambdas_str}', content)
    
    with open(py_file, 'w') as f:
        f.write(content)
    
    print(f"Updated {py_file}: NODES={n_nodes_list}, LAMBDAS={lambda_list}")
    return True


def run_ns3_simulation():
    """Run ns3 AlohaGridTest simulation."""
    ns3_dir = "../../"
    
    if not os.path.exists(os.path.join(ns3_dir, "ns3")):
        print(f"Error: ns3 executable not found in {ns3_dir}")
        return False
    
    try:
        # Change to ns3 directory and run simulation
        result = subprocess.run(
            ["./ns3", "run", "AlohaGridTest"],
            cwd=ns3_dir,
            capture_output=True,
            text=True,
            check=True
        )
        print("NS3 simulation completed successfully")
        if result.stdout:
            print("Simulation output:")
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"NS3 simulation failed with return code {e.returncode}")
        if e.stderr:
            print("Error output:")
            print(e.stderr)
        return False
    except FileNotFoundError:
        print("Error: ns3 command not found")
        return False


def run_print_script(stdout_only=False):
    """Run print_results_aloha.py script."""
    py_script = "scripts/print_results_aloha.py"
    
    if not os.path.exists(py_script):
        print(f"Error: {py_script} not found!")
        return False
    
    # Read the original script
    with open(py_script, 'r') as f:
        content = f.read()
    
    # Modify TRACE_PATH to point to the correct directory where trace files are generated
    # Trace files are generated in ../../ (ns-3.40 directory)
    modified_content = re.sub(
        r'TRACE_PATH = ""',
        'TRACE_PATH = "../../"',
        content
    )
    
    # Write modified version temporarily
    temp_script = "scripts/temp_print_results_aloha.py"
    with open(temp_script, 'w') as f:
        f.write(modified_content)
    
    try:
        if stdout_only:
            # Read the temp script and modify it for stdout output
            with open(temp_script, 'r') as f:
                temp_content = f.read()
            
            # Find the print_results function and replace file operations
            lines = temp_content.split('\n')
            in_print_results = False
            modified_lines = []
            
            for line in lines:
                if line.strip().startswith('def print_results():'):
                    in_print_results = True
                    modified_lines.append(line)
                elif in_print_results and line.strip().startswith('f.close()'):
                    # Skip f.close() lines
                    continue
                elif in_print_results and ('f =open(' in line or 'f = open(' in line):
                    # Replace file opening with stdout
                    indent = line[:len(line) - len(line.lstrip())]
                    modified_lines.append(f'{indent}import sys')
                    modified_lines.append(f'{indent}f = sys.stdout')
                else:
                    modified_lines.append(line)
                    # Exit print_results function when we see a dedent
                    if in_print_results and line.strip() == '' and len(modified_lines) > 0:
                        # Check if we're still in the function by looking at indentation
                        pass
            
            # Write the modified content
            with open(temp_script, 'w') as f:
                f.write('\n'.join(modified_lines))
        
        # Run the modified script
        result = subprocess.run([sys.executable, temp_script], capture_output=True, text=True, check=True)
        print("Print results script completed successfully")
        if result.stdout:
            print("Script output:")
            print(result.stdout)
        
        # Clean up temp file
        os.remove(temp_script)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Print script failed with return code {e.returncode}")
        if e.stderr:
            print("Error output:")
            print(e.stderr)
        # Clean up temp file even if it fails
        if os.path.exists(temp_script):
            os.remove(temp_script)
        return False


def main():
    parser = argparse.ArgumentParser(description='Run ALOHA simulation and print results')
    parser.add_argument('--n-nodes', type=int, default=841, help='Number of nodes (default: 841)')
    parser.add_argument('--lambda', dest='lambda_val', type=float, default=0.01, help='Lambda value (default: 0.01)')
    parser.add_argument('--stdout', action='store_true', help='Output results to stdout instead of files')
    parser.add_argument('--no-sim', action='store_true', help='Skip simulation, only run print script')
    parser.add_argument('--no-print', action='store_true', help='Skip print script, only run simulation')
    parser.add_argument('--clear', action='store_true', help='Clear all generated trace and result files')
    
    args = parser.parse_args()
    
    if args.clear:
        clear_generated_files()
        return 0
    
    n_nodes = args.n_nodes
    lambda_val = args.lambda_val
    stdout_only = args.stdout
    skip_sim = args.no_sim
    skip_print = args.no_print
    
    print(f"Configuration: n_nodes={n_nodes}, lambda={lambda_val}, stdout={stdout_only}")
    
    # Update both files with new parameters
    if not update_aloha_cc(n_nodes, lambda_val):
        return 1
    
    if not update_print_script([n_nodes], [lambda_val]):
        return 1
    
    # Build ns3 project first
    if not skip_sim:
        print("\nBuilding and running NS3 simulation...")
        # ns3 automatically builds when running, so we don't need to build separately
        # Just run the simulation directly
        if not run_ns3_simulation():
            return 1
    
    # Run print script
    if not skip_print:
        print("\nRunning print results script...")
        if not run_print_script(stdout_only):
            return 1
    
    print("\nScript completed successfully!")
    return 0


if __name__ == '__main__':
    sys.exit(main())