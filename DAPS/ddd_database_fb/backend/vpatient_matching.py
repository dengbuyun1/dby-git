import pandas as pd
import numpy as np
import os
import logging
import json

logger = logging.getLogger("VPatientMatcher")


class VPatientMatcher:
    def __init__(self, params_path=None):
        if params_path is None:
            # 默认路径：当前文件所在目录下的 simglucose/params/vpatient_params.csv
            base_dir = os.path.dirname(os.path.abspath(__file__))
            params_path = os.path.join(
                base_dir, "simglucose", "params", "vpatient_params.csv"
            )

        self.params_path = params_path
        self.vpatient_df = None
        self._load_params()

    def _load_params(self):
        try:
            if os.path.exists(self.params_path):
                self.vpatient_df = pd.read_csv(self.params_path)

                # Load Quest.csv for advanced matching (CR, CF, TDI, Age)
                quest_path = os.path.join(
                    os.path.dirname(self.params_path), "Quest.csv"
                )
                if os.path.exists(quest_path):
                    try:
                        quest_df = pd.read_csv(quest_path)
                        # Merge on Name
                        self.vpatient_df = pd.merge(
                            self.vpatient_df, quest_df, on="Name", how="left"
                        )
                        logger.info(f"Merged Quest.csv data")
                    except Exception as e:
                        logger.error(f"Failed to merge Quest.csv: {e}")

                # Load Custom Params (New Patients)
                custom_params_path = os.path.join(
                    os.path.dirname(self.params_path), "custom_vpatient_params.csv"
                )
                custom_quest_path = os.path.join(
                    os.path.dirname(self.params_path), "custom_Quest.csv"
                )

                if os.path.exists(custom_params_path):
                    try:
                        custom_df = pd.read_csv(custom_params_path)
                        if os.path.exists(custom_quest_path):
                            custom_quest_df = pd.read_csv(custom_quest_path)
                            custom_df = pd.merge(
                                custom_df, custom_quest_df, on="Name", how="left"
                            )

                        self.vpatient_df = pd.concat(
                            [self.vpatient_df, custom_df], ignore_index=True
                        )
                        logger.info(f"Loaded custom patients from {custom_params_path}")
                    except Exception as e:
                        logger.error(f"Failed to load custom params: {e}")

                # 预计算虚拟患者特征
                self.vpatient_df["age_group"] = self.vpatient_df["Name"].apply(
                    lambda x: x.split("#")[0]
                )
                # basal_per_kg = 0.24 * u2ss (根据方案A)
                self.vpatient_df["basal_per_kg"] = 0.24 * self.vpatient_df["u2ss"]
                logger.info(
                    f"Loaded {len(self.vpatient_df)} virtual patients from {self.params_path}"
                )
            else:
                logger.error(f"Params file not found at {self.params_path}")
        except Exception as e:
            logger.error(f"Failed to load vpatient params: {e}")

    def get_stats(self):
        """返回虚拟患者库的统计信息"""
        if self.vpatient_df is None:
            return {}

        stats = self.vpatient_df["age_group"].value_counts().to_dict()
        return stats

    def get_library_data(self):
        """Return simplified data for plotting"""
        if self.vpatient_df is None:
            return []

        data = []
        for _, row in self.vpatient_df.iterrows():
            data.append(
                {
                    "id": row["Name"],
                    "weight": row["BW"],
                    "basal_per_kg": row["basal_per_kg"],
                    "age_group": row["age_group"],
                    "tdi": row.get("TDI", 0),
                    "cr": row.get("CR", 0),
                    "cf": row.get("CF", 0),
                    "age": row.get("Age", 0),
                }
            )
        return data

    def create_new_patient(self, real_profile, base_vp_id):
        """
        Create a new virtual patient based on real profile and base VP.
        Saves to custom_vpatient_params.csv and custom_Quest.csv.
        """
        if self.vpatient_df is None:
            return {"error": "Database not loaded"}

        # 1. Find Base VP Data
        # Note: self.vpatient_df is a merged view. We need to be careful about which columns belong to which file.
        # It's safer to read the original files again or filter columns if we knew them.
        # For simplicity, we'll assume we can extract relevant columns.

        base_vp = self.vpatient_df[self.vpatient_df["Name"] == base_vp_id]
        if base_vp.empty:
            return {"error": "Base VP not found"}

        base_vp = base_vp.iloc[0]

        # 2. Prepare New Patient Data
        new_id = real_profile.get(
            "patient_id", f"Custom_{base_vp_id}_{int(pd.Timestamp.now().timestamp())}"
        )

        # Check if ID already exists
        if new_id in self.vpatient_df["Name"].values:
            return {"error": f"Patient ID {new_id} already exists"}

        # 3. Construct Params Row (vpatient_params.csv columns)
        # We need the list of columns for vpatient_params.csv
        # We can get it from the original file read or hardcode/infer.
        # Let's read the header of the original file to be safe.
        try:
            orig_params_df = pd.read_csv(self.params_path, nrows=0)
            params_cols = orig_params_df.columns.tolist()
        except:
            return {"error": "Could not read params header"}

        new_params = base_vp[params_cols].copy()
        new_params["Name"] = new_id
        new_params["BW"] = float(real_profile.get("weight_kg", base_vp["BW"]))

        # Note: Changing BW might require re-calculating other params (like Vg, Vi) if we were strict.
        # But for "rough matching", we just update BW.

        # 4. Construct Quest Row (Quest.csv columns)
        quest_cols = ["Name", "CR", "CF", "Age", "TDI"]
        new_quest = pd.Series(index=quest_cols)
        new_quest["Name"] = new_id
        new_quest["CR"] = float(real_profile.get("cr_g_u", base_vp.get("CR", 0)))
        new_quest["CF"] = float(real_profile.get("cf_mg_dl_u", base_vp.get("CF", 0)))

        # Age mapping
        age_map = {"adult": 35, "adolescent": 16, "child": 8}
        real_age_group = real_profile.get("age_group", "adult")
        default_age = age_map.get(real_age_group, 30)
        new_quest["Age"] = float(
            real_profile.get("age", base_vp.get("Age", default_age))
        )

        new_quest["TDI"] = float(real_profile.get("tdd_u_day", base_vp.get("TDI", 0)))

        # 5. Save to Custom Files
        custom_params_path = os.path.join(
            os.path.dirname(self.params_path), "custom_vpatient_params.csv"
        )
        custom_quest_path = os.path.join(
            os.path.dirname(self.params_path), "custom_Quest.csv"
        )

        logger.info(f"Saving new patient to: {custom_params_path}")

        # Append Params
        new_params_df = pd.DataFrame([new_params])
        if not os.path.exists(custom_params_path):
            new_params_df.to_csv(custom_params_path, index=False)
        else:
            new_params_df.to_csv(
                custom_params_path, mode="a", header=False, index=False
            )

        # Append Quest
        new_quest_df = pd.DataFrame([new_quest])
        if not os.path.exists(custom_quest_path):
            new_quest_df.to_csv(custom_quest_path, index=False)
        else:
            new_quest_df.to_csv(custom_quest_path, mode="a", header=False, index=False)

        logger.info(f"Successfully saved patient {new_id}")

        # 6. Reload
        self._load_params()

        return {"status": "success", "new_id": new_id}

    def save_optimized_patient(self, new_id, optimized_params, base_vp_id):
        """
        Save optimized parameters directly to custom files.
        """
        if self.vpatient_df is None:
            return {"error": "Database not loaded"}

        # 1. Get Base VP Structure
        base_vp = self.vpatient_df[self.vpatient_df["Name"] == base_vp_id]
        if base_vp.empty:
            return {"error": "Base VP not found"}
        base_vp = base_vp.iloc[0]

        # 2. Prepare New Params
        try:
            orig_params_df = pd.read_csv(self.params_path, nrows=0)
            params_cols = orig_params_df.columns.tolist()
        except:
            return {"error": "Could not read params header"}
        
        new_params = base_vp[params_cols].copy()
        new_params["Name"] = new_id
        
        # Update with optimized values
        for k, v in optimized_params.items():
            if k in new_params:
                new_params[k] = v
                
        # 3. Save to Params CSV
        custom_params_path = os.path.join(
            os.path.dirname(self.params_path), "custom_vpatient_params.csv"
        )
        new_params_df = pd.DataFrame([new_params])
        if not os.path.exists(custom_params_path):
            new_params_df.to_csv(custom_params_path, index=False)
        else:
            # Check if ID exists and update or append? 
            # For simplicity, we append. If duplicate, last one usually wins or causes issues.
            # Ideally we should remove old entry.
            new_params_df.to_csv(
                custom_params_path, mode="a", header=False, index=False
            )
            
        # 4. Save to Quest CSV (Duplicate base quest for now)
        quest_cols = ["Name", "CR", "CF", "Age", "TDI"]
        new_quest = pd.Series(index=quest_cols)
        new_quest["Name"] = new_id
        # Copy from base or optimized if available
        for col in ["CR", "CF", "Age", "TDI"]:
            if col in optimized_params:
                new_quest[col] = optimized_params[col]
            else:
                new_quest[col] = base_vp.get(col, 0)
                
        custom_quest_path = os.path.join(
            os.path.dirname(self.params_path), "custom_Quest.csv"
        )
        new_quest_df = pd.DataFrame([new_quest])
        if not os.path.exists(custom_quest_path):
            new_quest_df.to_csv(custom_quest_path, index=False)
        else:
            new_quest_df.to_csv(custom_quest_path, mode="a", header=False, index=False)
            
        self._load_params()
        return {"status": "success", "new_id": new_id}

    def match(self, real_profile, top_k=3, weights=None):
        """
        执行匹配算法 (基于 simglucose 100% 匹配方案 Step 1)
        real_profile: dict
        """
        if self.vpatient_df is None:
            return {"error": "Virtual patient database not loaded"}

        # 默认权重
        if weights is None:
            weights = {
                "w_age": 0.5,  # 年龄权重
                "w_tdi": 5.0,  # TDI 权重 (Log space)
                "w_cr": 5.0,  # CR 权重 (Log space)
                "w_cf": 5.0,  # CF 权重 (Log space)
                "w_bw": 2.0,  # 体重权重 (Log space)
            }

        # 1. 提取真实特征
        # Age mapping if not provided
        age_map = {"adult": 35, "adolescent": 16, "child": 8}
        real_age_group = real_profile.get("age_group", "adult")
        real_age = float(real_profile.get("age", age_map.get(real_age_group, 30)))

        real_bw = float(real_profile.get("weight_kg", 70))
        real_tdd = float(real_profile.get("tdd_u_day", 0))
        real_cr = float(real_profile.get("cr_g_u", 0))
        real_cf = float(real_profile.get("cf_mg_dl_u", 0))

        # 2. 计算距离
        df = self.vpatient_df.copy()

        # Initialize distance squared
        df["dist_sq"] = 0.0

        # Age term
        if "Age" in df.columns:
            df["dist_sq"] += weights["w_age"] * (df["Age"] - real_age) ** 2

        # TDI term (Log space)
        if real_tdd > 0 and "TDI" in df.columns:
            # Avoid log(0)
            vp_tdi = df["TDI"].replace(0, 1e-6)
            df["dist_sq"] += weights["w_tdi"] * (np.log(real_tdd) - np.log(vp_tdi)) ** 2

        # CR term (Log space)
        if real_cr > 0 and "CR" in df.columns:
            vp_cr = df["CR"].replace(0, 1e-6)
            df["dist_sq"] += weights["w_cr"] * (np.log(real_cr) - np.log(vp_cr)) ** 2

        # CF term (Log space)
        if real_cf > 0 and "CF" in df.columns:
            vp_cf = df["CF"].replace(0, 1e-6)
            df["dist_sq"] += weights["w_cf"] * (np.log(real_cf) - np.log(vp_cf)) ** 2

        # Weight term (Log space)
        if real_bw > 0 and "BW" in df.columns:
            vp_bw = df["BW"].replace(0, 1e-6)
            df["dist_sq"] += weights["w_bw"] * (np.log(real_bw) - np.log(vp_bw)) ** 2

        # Sort
        df["score"] = 1.0 / (1.0 + np.sqrt(df["dist_sq"]))  # Convert distance to score
        candidates = df.sort_values("dist_sq").head(top_k)

        # Format results
        results = []
        for _, row in candidates.iterrows():
            results.append(
                {
                    "base_vp_id": row["Name"],
                    "score": row["score"],
                    "distance": np.sqrt(row["dist_sq"]),
                    "details": {
                        "real_weight": real_bw,
                        "vp_weight": row["BW"],
                        "real_basal_per_kg": 0,  # Placeholder
                        "vp_basal_per_kg": row["basal_per_kg"],
                        "vp_age": row.get("Age", 0),
                        "vp_tdi": row.get("TDI", 0),
                        "vp_cr": row.get("CR", 0),
                        "vp_cf": row.get("CF", 0),
                    },
                }
            )

        return {"candidates": results}
