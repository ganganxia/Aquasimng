#!/usr/bin/env python3
"""
Run ALOHA simulation and print results script.

This script:
1. Executes ns3 "AlohaGridTest" in the ns-3.40 directory
2. Runs ./print_results_aloha.py to process results
3. Provides option to output directly to stdout instead of files
4. Allows modification of n_nodes and lambda parameters
5. Supports batch execution with multiple n_nodes and lambda combinations
"""

import os
import sys
import argparse
import subprocess
import re
import shutil
import csv
from itertools import product


import glob


def clear_generated_files():
    """Clear generated trace and result files."""
    # Clear trace files in ns-3.40 directory (../../../)
    trace_pattern = "../../../aloha-density-trace-*.asc"
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
    cc_file = "../examples/aloha_grid_test.cc"
    
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
    """Update ./print_results_aloha.py with new parameters."""
    py_file = "./print_results_aloha.py"
    
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


def run_ns3_simulation(rng_seed=None):
    """Run ns3 AlohaGridTest simulation with real-time output."""
    ns3_dir = "../../../"
    
    if not os.path.exists(os.path.join(ns3_dir, "ns3")):
        print(f"Error: ns3 executable not found in {ns3_dir}")
        return False
    
    try:
        # Build the command with optional random seed
        cmd = ["./ns3", "run", "AlohaGridTest"]
        if rng_seed is not None:
            cmd[-1] += f" --RngSeed={rng_seed}"
        
        # Change to ns3 directory and run simulation with real-time output
        print(f"Starting NS3 simulation with real-time output...{(' RNG seed: ' + str(rng_seed)) if rng_seed else ''}")
        process = subprocess.Popen(
            cmd,
            cwd=ns3_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Read and print output line by line in real-time
        for line in process.stdout:
            print(line, end='', flush=True)
        
        # Wait for process to complete
        process.wait()
        
        if process.returncode == 0:
            print("\nNS3 simulation completed successfully")
            return True
        else:
            print(f"\nNS3 simulation failed with return code {process.returncode}")
            return False
            
    except FileNotFoundError:
        print("Error: ns3 command not found")
        return False
    except Exception as e:
        print(f"Error running NS3 simulation: {e}")
        return False


def run_print_script(stdout_only=False, capture_output=False):
    """Run print_results_aloha.py script."""
    py_script = "./print_results_aloha.py"
    
    if not os.path.exists(py_script):
        print(f"Error: {py_script} not found!")
        return False, ""
    
    # Read the original script
    with open(py_script, 'r') as f:
        content = f.read()
    
    # Modify TRACE_PATH to point to the correct directory where trace files are generated
    # Trace files are generated in ../../../ (ns-3.40 directory)
    modified_content = re.sub(
        r'TRACE_PATH = ""',
        'TRACE_PATH = "../../../"',
        content
    )
    
    # Write modified version temporarily
    temp_script = "temp_print_results_aloha.py"
    with open(temp_script, 'w') as f:
        f.write(modified_content)
    
    try:
        if stdout_only or capture_output:
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
        
        # Determine output handling
        if capture_output:
            # Capture output for parsing
            result = subprocess.run([sys.executable, temp_script], capture_output=True, text=True, check=True)
            output_text = result.stdout
            if not stdout_only:
                print("Print results script completed successfully")
                if output_text:
                    print("Script output:")
                    print(output_text)
        else:
            # Run normally
            result = subprocess.run([sys.executable, temp_script], capture_output=True, text=True, check=True)
            output_text = result.stdout
            print("Print results script completed successfully")
            if output_text:
                print("Script output:")
                print(output_text)
        
        # Clean up temp file
        os.remove(temp_script)
        return True, output_text
    except subprocess.CalledProcessError as e:
        print(f"Print script failed with return code {e.returncode}")
        if e.stderr:
            print("Error output:")
            print(e.stderr)
        # Clean up temp file even if it fails
        if os.path.exists(temp_script):
            os.remove(temp_script)
        return False, ""


def extract_metrics_from_output(output_text):
    """
    Extract RxPackets and TxCount from the print script output.
    
    Args:
        output_text (str): Output from the print script
        
    Returns:
        tuple: (rx_packets, tx_count) or (None, None) if extraction fails
    """
    # Extract RxPackets pattern
    rx_match = re.search(r'RxPackets:\s*(\d+)', output_text)
    tx_match = re.search(r'TxCount:\s*(\d+)', output_text)
    
    rx_packets = int(rx_match.group(1)) if rx_match else None
    tx_count = int(tx_match.group(1)) if tx_match else None
    
    return rx_packets, tx_count


def run_single_simulation(n_nodes, lambda_val, stdout_only=False, skip_sim=False, skip_print=False, rng_seed=None):
    """
    Run a single simulation with given parameters.
    
    Args:
        n_nodes (int): Number of nodes
        lambda_val (float): Lambda value
        stdout_only (bool): Whether to output to stdout
        skip_sim (bool): Whether to skip simulation
        skip_print (bool): Whether to skip print script
        rng_seed (int): Random number generator seed (optional)
        
    Returns:
        tuple: (success, rx_packets, tx_count)
    """
    print(f"Configuration: n_nodes={n_nodes}, lambda={lambda_val}, stdout={stdout_only}{(', RNG seed: ' + str(rng_seed)) if rng_seed else ''}")
    
    # Update both files with new parameters
    if not update_aloha_cc(n_nodes, lambda_val):
        return False, None, None
    
    if not update_print_script([n_nodes], [lambda_val]):
        return False, None, None
    
    # Build ns3 project first
    if not skip_sim:
        print("\nBuilding and running NS3 simulation...")
        # ns3 automatically builds when running, so we don't need to build separately
        # Just run the simulation directly
        if not run_ns3_simulation(rng_seed=rng_seed):
            return False, None, None
    
    # Run print script
    if not skip_print:
        print("\nRunning print results script...")
        success, output_text = run_print_script(stdout_only=stdout_only, capture_output=True)
        if not success:
            return False, None, None
        
        # Extract metrics from output
        rx_packets, tx_count = extract_metrics_from_output(output_text)
        return True, rx_packets, tx_count
    
    return True, None, None


def run_batch_simulation(n_nodes_list, lambda_list, output_csv, stdout_only=False,
                        skip_sim=False, skip_print=False, skip_failed=False, repeat_count=1):
    """
    Run batch simulation with multiple parameter combinations.
    
    Args:
        n_nodes_list (list): List of node counts
        lambda_list (list): List of lambda values
        output_csv (str): Output CSV filename
        stdout_only (bool): Whether to output to stdout
        skip_sim (bool): Whether to skip simulation
        skip_print (bool): Whether to skip print script
        skip_failed (bool): Whether to skip failed simulations
        repeat_count (int): Number of times to repeat each experiment
        
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"Starting batch simulation with:")
    print(f"  n_nodes: {n_nodes_list}")
    print(f"  lambda: {lambda_list}")
    print(f"  repeats: {repeat_count}")
    print(f"  output: {output_csv}")
    
    # Prepare CSV file
    with open(output_csv, 'w', newline='') as csvfile:
        fieldnames = ['n_nodes', 'lambda', 'repeat', 'RxPackets', 'TxCount']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Run all combinations
        total_combinations = len(n_nodes_list) * len(lambda_list) * repeat_count
        completed = 0
        
        for n_nodes, lambda_val in product(n_nodes_list, lambda_list):
            for repeat in range(1, repeat_count + 1):
                completed += 1
                print(f"\n[{completed}/{total_combinations}] ", end="")
                
                # Use repeat number as RNG seed (starting from 1)
                rng_seed = repeat
                
                success, rx_packets, tx_count = run_single_simulation(
                    n_nodes, lambda_val, stdout_only, skip_sim, skip_print, rng_seed
                )
                
                if success and rx_packets is not None and tx_count is not None:
                    # Write successful result to CSV
                    writer.writerow({
                        'n_nodes': n_nodes,
                        'lambda': lambda_val,
                        'repeat': repeat,
                        'RxPackets': rx_packets,
                        'TxCount': tx_count
                    })
                    csvfile.flush()  # Ensure data is written immediately
                    print(f"  Success: RxPackets={rx_packets}, TxCount={tx_count}")
                else:
                    if skip_failed:
                        print(f"  Skipping failed combination: n_nodes={n_nodes}, lambda={lambda_val}, repeat={repeat}")
                        # Write empty values
                        writer.writerow({
                            'n_nodes': n_nodes,
                            'lambda': lambda_val,
                            'repeat': repeat,
                            'RxPackets': '',
                            'TxCount': ''
                        })
                        csvfile.flush()
                    else:
                        print(f"  Stopping due to failed simulation: n_nodes={n_nodes}, lambda={lambda_val}, repeat={repeat}")
                        return False
    
    print(f"\nBatch simulation completed! Results saved to {output_csv}")
    return True


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(description='Run ALOHA simulation and print results')
    parser.add_argument('--n-nodes', type=int, default=841, help='Number of nodes (default: 841)')
    parser.add_argument('--lambda', dest='lambda_val', type=float, default=0.01, help='Lambda value (default: 0.01)')
    parser.add_argument('--n-nodes-list', type=int, nargs='+', help='List of node counts for batch mode')
    parser.add_argument('--lambda-list', type=float, nargs='+', help='List of lambda values for batch mode')
    parser.add_argument('--repeat', type=int, default=1, help='Number of times to repeat each experiment (default: 1)')
    parser.add_argument('--output-csv', type=str, default='aloha_batch_results.csv',
                       help='Output CSV filename for batch mode (default: aloha_batch_results.csv)')
    parser.add_argument('--stdout', action='store_true', help='Output results to stdout instead of files')
    parser.add_argument('--no-sim', action='store_true', help='Skip simulation, only run print script')
    parser.add_argument('--no-print', action='store_true', help='Skip print script, only run simulation')
    parser.add_argument('--clear', action='store_true', help='Clear all generated trace and result files')
    parser.add_argument('--skip-failed', action='store_true', help='Skip failed simulations in batch mode')
    
    args = parser.parse_args()
    
    if args.clear:
        clear_generated_files()
        return 0
    
    # Check if batch mode is requested
    if args.n_nodes_list is not None and args.lambda_list is not None:
        # Batch mode
        return 0 if run_batch_simulation(
            args.n_nodes_list,
            args.lambda_list,
            args.output_csv,
            args.stdout,
            args.no_sim,
            args.no_print,
            args.skip_failed,
            args.repeat
        ) else 1
    elif args.n_nodes_list is not None or args.lambda_list is not None:
        print("Error: Both --n-nodes-list and --lambda-list must be specified for batch mode")
        return 1
    else:
        # Single simulation mode (original behavior)
        n_nodes = args.n_nodes
        lambda_val = args.lambda_val
        stdout_only = args.stdout
        skip_sim = args.no_sim
        skip_print = args.no_print
        rng_seed = 1 if args.repeat > 1 else None  # Use seed 1 for single run if repeat > 1
        
        success, rx_packets, tx_count = run_single_simulation(
            n_nodes, lambda_val, stdout_only, skip_sim, skip_print, rng_seed
        )
        
        if success:
            print("\nScript completed successfully!")
            return 0
        else:
            return 1


if __name__ == '__main__':
    sys.exit(main())