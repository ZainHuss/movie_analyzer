# movies/utils.py
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def handle_uploaded_file(file):
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file)
        else:
            raise ValueError("نوع الملف غير مدعوم")
            
        required_columns = ['title', 'year', 'rating']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"أعمدة مفقودة: {missing}")
            
        return df
        
    except Exception as e:
        logger.error(f"خطأ في معالجة الملف: {str(e)}")
        raise