import numpy as np

import pandas as pd

import subprocess

import os

import re



np.random.seed(42)



# --- CONFIGURATION ---

MODEL_FILE = "32nm_HP.pm"  # Ensure this file is in the current directory

L_MIN = 16e-9              # Feature size base multiplier for Width sweep

VDD_NOMINAL = 0.9          # Nominal VDD (0.9V or 1.0V)

NUM_SAMPLES = 10000



NOMINAL_PARAMS = {

    'vth0_n': 0.45, 'toxe_n': 1.2e-9, 'ndep_n': 1.5e18, 'u0_n': 0.04, 'xj_n': 1.5e-8,

    'vth0_p': -0.42, 'toxe_p': 1.2e-9, 'ndep_p': 1.5e18, 'u0_p': 0.02, 'xj_p': 1.5e-8

}



def draw_pvt_samples(n_samples):

    """Draws uniform random samples for PVT parameters."""

    vdd = np.random.uniform(VDD_NOMINAL * 0.9, VDD_NOMINAL * 1.1, n_samples)

    vd = np.random.uniform(0, vdd)

    vs = np.random.uniform(0, vdd)

    w = np.random.uniform(1 * L_MIN, 8 * L_MIN, n_samples)

    temp = np.random.uniform(-40, 125, n_samples)



    proc_data = {}

    for param in ['vth0', 'toxe', 'ndep', 'u0', 'xj']:

        proc_data[f'{param}_n'] = np.random.uniform(NOMINAL_PARAMS[f'{param}_n']*0.9, NOMINAL_PARAMS[f'{param}_n']*1.1, n_samples)

        proc_data[f'{param}_p'] = np.random.uniform(NOMINAL_PARAMS[f'{param}_p']*0.9, NOMINAL_PARAMS[f'{param}_p']*1.1, n_samples)



    return pd.DataFrame({'vdd': vdd, 'temp': temp, 'w': w, 'vd': vd, 'vs': vs, **proc_data})



def generate_netlist(case, row):

    """Generates SPICE netlist using nominal model length to guarantee Leff > 0."""

    is_nmos = "NMOS" in case

    is_on = "ON" in case



    vg = row['vdd'] if ((is_nmos and is_on) or (not is_nmos and not is_on)) else 0.0

    vb = 0.0 if is_nmos else row['vdd']

    fet_type = "nmos" if is_nmos else "pmos"



    # NOTE: L is omitted so NGspice defaults to the model file's calibrated length

    netlist = f"""* Single Transistor PVT Test - {case}

.include "{MODEL_FILE}"



.options gmin=1e-18 abstol=1e-18 reltol=1e-6 vntol=1e-9 temp={row['temp']}



Vd d 0 DC {row['vd']}

Vg g 0 DC {vg}

Vs s 0 DC {row['vs']}

Vb b 0 DC {vb}



M1 d g s b {fet_type} W={row['w']}



.control

op

print i(Vd) i(Vg) i(Vs) i(Vb)

.endc

.end

"""

    return netlist, vg, vb



def run_ngspice_batch(case, df_samples):

    results = []

    print(f"\n==================== Simulating {case} ({len(df_samples)} samples) ====================")



    for idx, row in df_samples.iterrows():

        netlist_str, vg, vb = generate_netlist(case, row)

        

        proc = subprocess.run(

            ["ngspice", "-b"],

            input=netlist_str,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            text=True

        )



        output = proc.stdout

        current_matches = re.findall(r"=\s*([-\+]?\d+(?:\.\d+)?[eE][-\+]?\d+)", output)

        

        if idx < 3:

            print(f"\n--- DEBUG SAMPLE #{idx + 1} ({case}) ---")

            print(f"[PARSED MATCHES]: {current_matches}")

            print("-" * 50)



        if len(current_matches) >= 4:

            id_, ig, is_, ib = map(float, current_matches[:4])

        else:

            all_numbers = re.findall(r"[-+]?\d+\.\d+e[-+]?\d+", output)

            if len(all_numbers) >= 4:

                id_, ig, is_, ib = map(float, all_numbers[-4:])

            else:

                id_, ig, is_, ib = np.nan, np.nan, np.nan, np.nan



        vth0_val = row['vth0_n'] if "NMOS" in case else row['vth0_p']

        toxe_val = row['toxe_n'] if "NMOS" in case else row['toxe_p']

        ndep_val = row['ndep_n'] if "NMOS" in case else row['ndep_p']

        u0_val   = row['u0_n']   if "NMOS" in case else row['u0_p']

        xj_val   = row['xj_n']   if "NMOS" in case else row['xj_p']



        results.append({

            'vdd': row['vdd'], 'temp': row['temp'], 'w': row['w'],

            'vd': row['vd'], 'vs': row['vs'], 'vg': vg, 'vb': vb,

            'vtho': vth0_val, 'toxe': toxe_val, 'ndep': ndep_val, 'u0': u0_val, 'xj': xj_val,

            'id': id_, 'ig': ig, 'is': is_, 'ib': ib

        })



        if (idx + 1) % 2000 == 0:

            print(f"  Processed {idx + 1}/{len(df_samples)} samples...")



    out_df = pd.DataFrame(results)

    out_df.to_csv(f"{case}.csv", index=False)

    print(f"Saved {case}.csv with {len(out_df)} records.")



if __name__ == "__main__":

    cases = ["NMOS_ON", "NMOS_OFF", "PMOS_ON", "PMOS_OFF"]

    samples_df = draw_pvt_samples(NUM_SAMPLES)

    for case in cases:

        run_ngspice_batch(case, samples_df)
