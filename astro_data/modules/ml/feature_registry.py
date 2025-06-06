from pathlib import Path
from typing import Dict, List
import pandas as pd

class FeatureRegistry:
    def __init__(self):
        self.feature_sources = {
            'revenue_model': Path(__file__).parent.parent.parent/'rev_model/imp_rev_features.md',
            'production_volume_model': Path(__file__).parent.parent.parent/'prod_vol_model/imp_prod_features.md',
            'profit_margin_model': Path(__file__).parent.parent.parent/'prof_marg_model/imp_prof_margin_features.md'
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
