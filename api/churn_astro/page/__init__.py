from .churn_prediction import make_predictions, process_prediction_results, predict_customer_churn, predict_batch_churn
from .churn_bot import process_natural_language_query

# Export the churn prediction functions (backend only, no UI)
__all__ = ['make_predictions', 'process_prediction_results', 'predict_customer_churn', 'predict_batch_churn', 'process_natural_language_query']
