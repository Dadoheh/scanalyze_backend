import datetime
import json
import logging

logger = logging.getLogger(__name__)

def save_analysis_results(data, prefix="ingredients_analysis"):
    """
    Save analysis data to a timestamped JSON file.
    
    Args:
        data: The data to save
        prefix: Prefix for the filename (default: "ingredients_analysis")
    
    Returns:
        str: The path to the saved file
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.json"
    
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return super().default(obj)
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, cls=DateTimeEncoder, ensure_ascii=False)
        logger.info(f"Analysis results saved to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to save analysis results: {str(e)}")
        return None