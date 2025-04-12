import sqlite3
from typing import Optional, Any, Dict
import json
from datetime import date
from pathlib import Path


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)

class Cache:
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the cache with optional custom database path."""
        try:
            cache_dir = Path(r"C:\\Users\\athar\\OneDrive\\Documents\\GitHub\\form-factory\\modules\\data\\kg_cache")
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(cache_dir / 'cache.db')
            self._create_table()
        except Exception:
            # Fallback to in-memory cache if file-based cache fails
            self.db_path = ":memory:"
            self._create_table()

    def _create_table(self):
        """Create the cache table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    query TEXT PRIMARY KEY,
                    response TEXT
                )
            ''')

    def _serialize_value(self, value):
        """Serialize value with type preservation."""
        if isinstance(value, str):
            # Store plain text as-is
            return json.dumps({'type': 'text', 'value': value})
        elif isinstance(value, (dict, list)):
            # Handle JSON-compatible structures
            def convert_dates(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_dates(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_dates(item) for item in obj]
                return obj
            return json.dumps({'type': 'json', 'value': convert_dates(value)})
        else:
            # Fallback for other types
            return json.dumps({'type': 'other', 'value': str(value)})

    def _deserialize_value(self, value_str):
        """Deserialize value with type handling."""
        try:
            data = json.loads(value_str)
            if not isinstance(data, dict) or 'type' not in data:
                # Legacy format fallback
                def date_hook(obj_dict):
                    for key, value in obj_dict.items():
                        if isinstance(value, str):
                            try:
                                obj_dict[key] = date.fromisoformat(value)
                            except ValueError:
                                pass
                    return obj_dict
                return json.loads(value_str, object_hook=date_hook)

            if data['type'] == 'text':
                return data['value']
            elif data['type'] == 'json':
                def date_hook(obj_dict):
                    for key, value in obj_dict.items():
                        if isinstance(value, str):
                            try:
                                obj_dict[key] = date.fromisoformat(value)
                            except ValueError:
                                pass
                    return obj_dict
                return json.loads(json.dumps(data['value']), object_hook=date_hook)
            else:
                return data['value']
        except json.JSONDecodeError:
            return value_str

    def get(self, query: str) -> Optional[Any]:
        """Retrieve a cached response for the given query."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT response FROM cache WHERE query = ?', (query,))
                if result := cursor.fetchone():
                    return self._deserialize_value(result[0])
        except (sqlite3.Error, json.JSONDecodeError):
            pass
        return None

    def set(self, query: str, response: Any):
        """Store a response in the cache for the given query."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO cache (query, response)
                    VALUES (?, ?)
                ''', (query, self._serialize_value(response)))
        except sqlite3.Error:
            pass

    def close(self):
        """Close any open database connections."""
        pass

    def __del__(self):
        self.close()


def cacheable(cache_attr='cache'):
    """
    Decorator to handle caching logic for methods.
    
    Args:
        cache_attr (str): Name of the cache attribute in the instance
    """
    def decorator(func):
        def wrapper(instance, *args, **kwargs):
            # First argument is the instance
            question = args[0] if args else kwargs.get('question', '')
            
            # Get cache instance and bypass flag
            cache = getattr(instance, cache_attr)
            bypass_cache = True
            
            # Try cache if not bypassing
            if not bypass_cache:
                cached_result = cache.get(question)
                if cached_result:
                    print(f"Using cached result for query: {question}")
                    return cached_result
            
            # Execute original function
            result = func(instance, *args, **kwargs)
            
            # Store in cache if not bypassing
            if not bypass_cache:
                try:
                    cache.set(question, result)
                    print(f"Successfully cached result for query: {question}")
                except Exception as cache_error:
                    print(f"Error caching result: {str(cache_error)}")
            
            return result
        return wrapper
    return decorator
