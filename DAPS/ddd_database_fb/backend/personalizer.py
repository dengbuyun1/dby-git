import numpy as np
import pandas as pd
import logging
from datetime import timedelta, datetime
import copy
from scipy.optimize import differential_evolution

# Import simglucose modules
# Assuming this file is in ddd_database_fb/backend/
from simglucose.patient.t1dpatient import T1DPatient
from simglucose.simulation.env import T1DSimEnv
from simglucose.sensor.cgm import CGMSensor
from simglucose.actuator.pump import InsulinPump
from simglucose.simulation.scenario import CustomScenario
from simglucose.controller.base import Action

logger = logging.getLogger("Personalizer")

class Personalizer:
    def __init__(self):
        pass

    def run_optimization(self, real_data, base_patient_name="adolescent#001", progress_callback=None):
        """
        Run the Differential Evolution algorithm to find optimal parameters.
        
        Args:
            real_data (dict): Dictionary containing arrays:
                              'bg': list of glucose values (mg/dL)
                              'insulin': list of insulin doses (U) - sparse or continuous
                              'cho': list of carbs (g) - sparse
                              'time': list of timestamps or relative minutes
            base_patient_name (str): Name of the starting patient template.
            progress_callback (func): Function to report progress (0-100).
            
        Returns:
            dict: Optimized parameters.
        """
        
        # 1. Prepare Base Patient
        # We load the base patient to get the initial structure of parameters
        try:
            patient = T1DPatient.withName(base_patient_name)
        except:
            # Fallback
            patient = T1DPatient.withName("adolescent#001")
            
        original_params = copy.deepcopy(patient._params)
        
        # 2. Define Parameter Bounds for Optimization
        # We focus on the most impactful parameters: Vmx, kabs, EGPb
        # Vmx: Insulin sensitivity (approx range: 0.01 - 0.1)
        # kabs: Carb absorption rate (approx range: 0.001 - 0.2)
        # EGPb: Endogenous Glucose Production (approx range: 0 - 5)
        # S_it: Insulin sensitivity? In UVA model Vmx is key.
        
        # Extract initial values (if available) or use defaults
        p_names = ['Vmx', 'kabs', 'EGPb']
        bounds = [
            (0.005, 0.15),   # Vmx range
            (0.001, 0.2),    # kabs range
            (0.5, 6.0)       # EGPb range
        ]
        
        # 3. Pre-process Real Data for Simulation
        # We need to create a Scenario that mimics the real events
        # Real data usually comes as a sequence. We need to extract meals.
        
        # Assuming real_data is already aligned and resampled to e.g. 5 min intervals
        # scenario_data = [(time, meal_size)]
        
        scenario = self._create_scenario_from_data(real_data)
        
        # 4. Define Cost Function
        def cost_func(x):
            # x is [Vmx, kabs, EGPb]
            
            # Construct params dict
            current_params = {
                'Vmx': x[0],
                'kabs': x[1],
                'EGPb': x[2]
            }
            # Add other static params from original if needed, but _run_single_simulation
            # handles updating a fresh patient object which has defaults.
            # To be safe, we should pass the FULL set if we want to preserve original's static traits.
            full_params = copy.deepcopy(original_params)
            full_params.update(current_params)
            
            sim_bg, real_bg = self._run_single_simulation(full_params, scenario, real_data, base_patient_name)
            
            if not sim_bg:
                return 1e9
                
            sim_arr = np.array(sim_bg)
            real_arr = np.array(real_bg)
            
            # Simple RMSE
            mse = np.mean((sim_arr - real_arr) ** 2)
            return np.sqrt(mse)

        # 5. Run Optimization
        # We use Differential Evolution for global search
        logger.info("Starting Differential Evolution...")
        
        result = differential_evolution(
            cost_func, 
            bounds, 
            strategy='best1bin', 
            maxiter=10,    # Low iteration count for demo speed (increase for prod)
            popsize=5,     # Low population for demo speed
            tol=0.1,
            mutation=(0.5, 1), 
            recombination=0.7,
            disp=False,
            callback=self._callback_wrapper(progress_callback) if progress_callback else None
        )
        
        logger.info(f"Optimization finished. Fun: {result.fun}")
        
        optimized_params = {
            'Vmx': result.x[0],
            'kabs': result.x[1],
            'EGPb': result.x[2]
        }
        
        # Merge with original to keep other params
        final_params = copy.deepcopy(original_params)
        final_params.update(optimized_params)
        
        return final_params

    def validate_model(self, real_data, patient_params, base_patient_name="adolescent#001"):
        """
        Run a simulation with the given parameters and calculate accuracy metrics.
        Returns: dict with RMSE, MARD, etc.
        """
        scenario = self._create_scenario_from_data(real_data)
        
        sim_bg, real_bg = self._run_single_simulation(patient_params, scenario, real_data, base_patient_name)
        
        if len(sim_bg) == 0:
            return {"error": "No valid simulation data"}
            
        # Calculate Metrics
        sim_arr = np.array(sim_bg)
        real_arr = np.array(real_bg)
        
        # 1. RMSE
        mse = np.mean((sim_arr - real_arr) ** 2)
        rmse = np.sqrt(mse)
        
        # 2. MARD (Mean Absolute Relative Difference)
        # Avoid division by zero
        non_zero = real_arr > 0
        if np.any(non_zero):
            ard = np.abs(sim_arr[non_zero] - real_arr[non_zero]) / real_arr[non_zero]
            mard = np.mean(ard) * 100.0
        else:
            mard = 0.0
            
        # 3. Correlation (Pearson)
        if len(sim_arr) > 1:
            correlation = np.corrcoef(sim_arr, real_arr)[0, 1]
        else:
            correlation = 0
            
        return {
            "rmse": rmse,
            "mard": mard,
            "correlation": correlation,
            "data_points": len(sim_arr)
        }

    def _run_single_simulation(self, params, scenario, real_data, base_patient_name):
        """
        Helper to run one simulation pass and return aligned BG arrays.
        """
        # Create temp patient with params
        temp_patient = T1DPatient.withName(base_patient_name)
        # Update params carefully
        temp_patient._params.update(params)
        # Re-init state (simplified) if possible, or rely on model convergence
        
        env = T1DSimEnv(
            patient=temp_patient,
            sensor=CGMSensor.withName("Dexcom", seed=1),
            pump=InsulinPump.withName("Insulet"),
            scenario=scenario
        )
        
        obs, _, _, _ = env.reset()
        
        sim_bg_list = []
        real_bg_list = []
        
        real_bg_values = real_data['bg']
        insulin_inputs = real_data['insulin']
        steps = min(len(real_bg_values), len(insulin_inputs))
        
        for t in range(steps):
            ins_val = insulin_inputs[t]
            action = Action(basal=0, bolus=ins_val)
            
            obs, _, _, _ = env.step(action)
            
            sim_val = obs.BG
            real_val = real_bg_values[t]
            
            if real_val > 0: # Only compare where we have real data
                sim_bg_list.append(sim_val)
                real_bg_list.append(real_val)
                
        return sim_bg_list, real_bg_list

    def _create_scenario_from_data(self, real_data):
        """
        Convert real CHO data into a CustomScenario
        """
        # real_data['cho'] is a list aligned with time
        # CustomScenario expects list of (time, size)
        
        scenario_list = []
        start_time = real_data.get('start_time', datetime.now())
        
        # Assuming data is 1-minute or similar fixed step
        step_minutes = real_data.get('step_minutes', 1)
        
        for i, cho in enumerate(real_data['cho']):
            if cho > 0:
                # Convert index to time
                t = start_time + timedelta(minutes=i*step_minutes)
                scenario_list.append((t, cho))
                
        return CustomScenario(start_time=start_time, scenario=scenario_list)

    def _callback_wrapper(self, callback):
        def wrapper(xk, convergence):
            # differential_evolution callback doesn't give percentage easily
            # but we can just pulse the progress
            if callback:
                callback(convergence) # convergence is not percentage, but it's something
        return wrapper

if __name__ == "__main__":
    # Test stub
    pass
