import sys
from pathlib import Path
from typing import Dict, List
import pandas as pd

# Add the parent directory to Python path to find the api package
parent_path = Path(__file__).parent.parent.parent.parent
if str(parent_path) not in sys.path:
    sys.path.append(str(parent_path))

# Add the astro_data directory to Python path
astro_data_path = Path(__file__).parent.parent.parent
if str(astro_data_path) not in sys.path:
    sys.path.append(str(astro_data_path))

class FeatureRegistry:
    def __init__(self):
        # Use absolute paths to ensure files can be found regardless of import path
        astro_data_path = Path(__file__).parent.parent.parent
        self.feature_sources = {
            'revenue_model': astro_data_path/'rev_model/imp_rev_features.md',
            'production_volume_model': astro_data_path/'prod_vol_model/imp_prod_features.md',
            'profit_margin_model': astro_data_path/'prof_marg_model/imp_prof_margin_features.md'
        }
        self.features = {}
        self._load_features()

    def _load_features(self):
        for model, path in self.feature_sources.items():
            with open(path) as f:
                lines = f.readlines()
            self.features[model] = [line.split('|')[1].strip() for line in lines[2:]]

    def get_features(self, model_name: str) -> List[str]:
        return self.features.get(model_name, [])

    def validate_features(self, model_name: str, input_data: pd.DataFrame) -> Dict[str, bool]:
        required_features = self.get_features(model_name)
        return {feature: feature in input_data.columns for feature in required_features}

feature_registry = FeatureRegistry()
