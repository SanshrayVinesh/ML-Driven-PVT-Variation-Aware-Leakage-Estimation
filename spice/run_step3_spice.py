import os

import subprocess

import pandas as pd

import numpy as np



# --- CONFIGURATION ---

MODEL_FILE = "32nm_HP.pm"      # Your assigned model file

NOMINAL_VDD = 1              # Your assigned VDD

NUM_CORNERS = 200

SEED = 42

SPICE_CMD = "ngspice"



np.random.seed(SEED)



GATE_INPUT_CASES = [

    ("INV",   "A",   ["0", "1"]),

    ("NAND2", "AB",  ["00", "01", "10", "11"]),

    ("NOR2",  "AB",  ["00", "01", "10", "11"]),

    ("AND2",  "AB",  ["00", "01", "10", "11"]),

    ("OR2",   "AB",  ["00", "01", "10", "11"]),

]



def generate_corners(num_corners=200, vdd_nom=0.9):

    corners = []

    for c_idx in range(num_corners):

        vdd = np.random.uniform(vdd_nom * 0.9, vdd_nom * 1.1)

        temp = np.random.uniform(-40, 125)

        nmos_p = {p: np.random.uniform(0.9, 1.1) for p in ['vth0', 'toxe', 'ndep', 'u0', 'xj']}

        pmos_p = {p: np.random.uniform(0.9, 1.1) for p in ['vth0', 'toxe', 'ndep', 'u0', 'xj']}

        corners.append({'corner_id': c_idx, 'vdd': vdd, 'temp': temp, 'nmos': nmos_p, 'pmos': pmos_p})

    return corners



def simulate_gate_case(gate_name, in_vec, corner):

    vdd_val = corner['vdd']

    temp_val = corner['temp']

    

    if len(in_vec) == 1:

        v_a = vdd_val if in_vec[0] == '1' else 0.0

        input_sources = f"Va a 0 DC {v_a}\n"

    else:

        v_a = vdd_val if in_vec[0] == '1' else 0.0

        v_b = vdd_val if in_vec[1] == '1' else 0.0

        input_sources = f"Va a 0 DC {v_a}\nVb b 0 DC {v_b}\n"



    # We use wrdata to dump numerical values directly to an external text file

    netlist_str = f"""* Step 3 Gate Reference Simulation

.include "{MODEL_FILE}"

.include "gates.sp"



VVDD vdd 0 DC {vdd_val}

VVSS vss 0 DC 0.0

{input_sources}

Xgate {"a " if len(in_vec)==1 else "a b "} out vdd vss {gate_name}



.temp {temp_val}

.op



.control

run

wrdata temp_out.dat v(out) i(VVDD)

.endc

.end

"""

    

    sp_filename = "temp_sim.sp"

    dat_filename = "temp_out.dat"

    out_log = "temp_sim.log"

    

    with open(sp_filename, "w") as f:

        f.write(netlist_str)

        

    cmd = [SPICE_CMD, "-b", "-o", out_log, sp_filename]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    

    i_vdd = None

    v_out = None

    

    # Read raw numerical matrix written by wrdata

    if os.path.exists(dat_filename):

        with open(dat_filename, "r") as f:

            for line in f:

                line = line.strip()

                if not line or line.startswith('*'):

                    continue

                parts = line.split()

                # wrdata format: scale_val v(out) scale_val i(VVDD)

                if len(parts) >= 4:

                    try:

                        v_out = float(parts[1])

                        i_vdd = abs(float(parts[3]))

                    except ValueError:

                        pass

                elif len(parts) >= 2:

                    try:

                        v_out = float(parts[0])

                        i_vdd = abs(float(parts[1]))

                    except ValueError:

                        pass



    # Cleanup temp files

    for tmp in [sp_filename, dat_filename, out_log]:

        if os.path.exists(tmp):

            os.remove(tmp)

            

    return i_vdd, v_out



def main():

    print("Running Step 3 Data Collection with wrdata file output...")

    corners = generate_corners(NUM_CORNERS, NOMINAL_VDD)

    results = []

    

    total_runs = 18 * NUM_CORNERS

    count = 0



    for gate_name, _, input_list in GATE_INPUT_CASES:

        for in_vec in input_list:

            for corner in corners:

                count += 1

                i_leak, v_out = simulate_gate_case(gate_name, in_vec, corner)

                

                results.append({

                    'gate': gate_name,

                    'input_vector': in_vec,

                    'corner_id': corner['corner_id'],

                    'vdd': corner['vdd'],

                    'temp': corner['temp'],

                    'v_out': v_out,

                    'spice_leakage_i': i_leak

                })

                

                if count % 200 == 0:

                    print(f"Completed {count}/{total_runs} simulations...")



    df = pd.DataFrame(results)

    df.to_csv("step3_gate_data.csv", index=False)

    

    # Check if empty values exist

    null_count = df['v_out'].isnull().sum()

    if null_count > 0:

        print(f"WARNING: {null_count} rows failed to parse! Check if model file '{MODEL_FILE}' matches the transistor names in gates.sp.")

    else:

        print("SUCCESS! All 3,600 rows successfully populated with numeric data in 'step3_gate_data.csv'.")



if __name__ == "__main__":

    main()
