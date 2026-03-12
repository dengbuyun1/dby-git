import csv
import os
import logging

logger = logging.getLogger("CSVDataProvider")


class CSVDataProvider:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.file = None
        self.reader = None
        self.headers = None

    def load_patient(self, patient_id):
        self.close()  # Close any existing file

        # Try to find the file with .csv extension
        file_path = os.path.join(self.data_dir, f"{patient_id}.csv")
        if not os.path.exists(file_path):
            # Try without extension if user provided it, or maybe just patient_id is the name
            file_path = os.path.join(self.data_dir, patient_id)
            if not os.path.exists(file_path):
                logger.error(f"CSV file not found: {file_path}")
                return False

        try:
            self.file = open(file_path, "r", encoding="utf-8")
            self.reader = csv.reader(self.file)
            self.headers = next(self.reader)  # Skip header
            logger.info(f"Loaded CSV file for patient {patient_id}")
            return True
        except Exception as e:
            logger.error(f"Error opening CSV file: {e}")
            return False

    def get_next_data(self):
        if not self.reader:
            return None

        try:
            row = next(self.reader)
            # CSV format: timestamp,bg,insulin,carbs,hr,dist,steps,cals,activity,device
            # Index:      0         1  2       3     4  5    6     7    8        9

            if not row:
                return None

            timestamp_str = row[0]
            bg_val = row[1]
            insulin_val = row[2]
            carbs_val = row[3]

            # Helper to parse float or return None
            def parse_float(val):
                if val and val.strip():
                    try:
                        return float(val)
                    except ValueError:
                        return None
                return None

            bg = parse_float(bg_val)
            insulin = parse_float(insulin_val)
            cho = parse_float(carbs_val)

            # Construct data object matching the simulator output format
            data = {
                "timestamp": timestamp_str,
                "bg": bg,
                "cgm": bg,  # Use BG as CGM
                "cho": cho,
                "cob": 0,  # Default to 0 as it's not in CSV
                "insulin": insulin,
                "iob": 0,  # Default to 0
            }
            return data
        except StopIteration:
            logger.info("End of CSV file reached")
            return None
        except Exception as e:
            logger.error(f"Error parsing row: {e}")
            return None

    def close(self):
        if self.file:
            try:
                self.file.close()
            except:
                pass
            self.file = None
            self.reader = None
