import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from models import CustomItem
from app import db

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class NLPProcessor:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.food_quantity_patterns = [
            r'(\d+(?:\.\d+)?)\s*(cup|cups|g|grams|kg|kilograms|lb|lbs|pounds|oz|ounce|ounces|ml|l|liter|liters|tbsp|tablespoon|tablespoons|tsp|teaspoon|teaspoons|slice|slices|piece|pieces)',
            r'(\d+(?:\.\d+)?)',  # Just numbers
        ]
        self.activity_patterns = [
            r'(ran|running|jogging|jogged|walked|walking|cycling|cycled|swimming|swam|yoga|hiit|workout|exercised|training|trained)',
            r'(\d+(?:\.\d+)?)\s*(minutes|mins|min|hours|hour|hr|hrs)',
        ]
        
        # Common food database with nutrition info per standard unit
        self.food_database = {
            'apple': {'calories': 95, 'protein': 0.5, 'carbohydrates': 25, 'fiber': 4, 'sugar': 19, 'sodium': 2, 'unit': 'piece', 'quantity': 1},
            'banana': {'calories': 105, 'protein': 1.3, 'carbohydrates': 27, 'fiber': 3.1, 'sugar': 14, 'sodium': 1, 'unit': 'piece', 'quantity': 1},
            'orange': {'calories': 62, 'protein': 1.2, 'carbohydrates': 15.4, 'fiber': 3.1, 'sugar': 12, 'sodium': 0, 'unit': 'piece', 'quantity': 1},
            'bread': {'calories': 264, 'protein': 9, 'carbohydrates': 49, 'fiber': 3, 'sugar': 6, 'sodium': 491, 'unit': 'slice', 'quantity': 1},
            'rice': {'calories': 130, 'protein': 2.7, 'carbohydrates': 28, 'fiber': 0.6, 'sugar': 0.1, 'sodium': 1, 'unit': 'cup', 'quantity': 1},
            'pasta': {'calories': 221, 'protein': 8.1, 'carbohydrates': 43.2, 'fiber': 2.5, 'sugar': 0.8, 'sodium': 1, 'unit': 'cup', 'quantity': 1},
            'chicken': {'calories': 165, 'protein': 31, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 74, 'unit': 'piece', 'quantity': 1}, # 100g
            'beef': {'calories': 250, 'protein': 26, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 72, 'unit': 'piece', 'quantity': 1}, # 100g
            'milk': {'calories': 149, 'protein': 8, 'carbohydrates': 12, 'fiber': 0, 'sugar': 12, 'sodium': 105, 'unit': 'cup', 'quantity': 1},
            'egg': {'calories': 72, 'protein': 6.3, 'carbohydrates': 0.4, 'fiber': 0, 'sugar': 0.2, 'sodium': 71, 'unit': 'piece', 'quantity': 1},
        }
        
        # Common exercises with calories burned per minute (based on 70kg person)
        self.exercise_database = {
            'running': 10.0,  # 10 calories per minute
            'jogging': 8.0,
            'walking': 4.0,
            'cycling': 7.0,
            'swimming': 8.0,
            'yoga': 3.0,
            'hiit': 12.0,
            'workout': 8.0,
            'training': 7.0,
        }
    
    def process_food_query(self, query, user_id):
        """Process natural language food query and extract nutrition information"""
        query = query.lower()
        tokens = word_tokenize(query)
        tokens = [token for token in tokens if token.isalnum() and token not in self.stop_words]
        
        # Extract quantities
        quantity = 1.0
        unit = "serving"
        food_item = None
        
        # Try to find quantities and units
        for pattern in self.food_quantity_patterns:
            matches = re.findall(pattern, query)
            if matches:
                if isinstance(matches[0], tuple):
                    quantity = float(matches[0][0])
                    if len(matches[0]) > 1:
                        unit = matches[0][1]
                else:
                    quantity = float(matches[0])
                break
        
        # Try to find food item
        for token in tokens:
            if token in self.food_database:
                food_item = token
                break
        
        # If not found in basic database, check user's custom items
        if not food_item:
            custom_items = CustomItem.query.filter_by(user_id=user_id).all()
            for item in custom_items:
                if item.name.lower() in query:
                    food_item = item.name.lower()
                    nutrition_data = {
                        'calories': item.calories,
                        'protein': item.protein,
                        'carbohydrates': item.carbohydrates,
                        'fiber': item.fiber,
                        'sugar': item.sugar,
                        'sodium': item.sodium,
                        'unit': item.unit,
                        'quantity': item.quantity
                    }
                    result = self._calculate_nutrition(nutrition_data, quantity, item.quantity)
                    result['name'] = item.name
                    result['value'] = quantity
                    result['quantity'] = quantity
                    result['result'] = True
                    return result
        
        # Calculate nutrition based on the found food item
        if food_item:
            nutrition_data = self.food_database[food_item]
            result = self._calculate_nutrition(nutrition_data, quantity, nutrition_data['quantity'])
            result['name'] = food_item
            result['value'] = quantity
            result['quantity'] = quantity
            result['result'] = True
            return result
            
        # If no match found
        return {
            'result': False,
            'message': "Food item not recognized. Please try again or add a custom food item."
        }
    
    def process_exercise_query(self, query):
        """Process natural language exercise query and extract calories burned"""
        query = query.lower()
        
        # Extract exercise type
        exercise_type = None
        for pattern in self.activity_patterns:
            matches = re.findall(pattern, query)
            if matches and pattern.startswith('(ran|'):
                exercise_type = matches[0]
                if isinstance(exercise_type, tuple):
                    exercise_type = exercise_type[0]
                break
        
        # Extract duration
        duration = 30  # Default duration in minutes
        for pattern in self.activity_patterns:
            matches = re.findall(pattern, query)
            if matches and pattern.startswith('(\\d+'):
                if isinstance(matches[0], tuple):
                    duration_val = float(matches[0][0])
                    unit = matches[0][1] if len(matches[0]) > 1 else 'minutes'
                    if 'hour' in unit:
                        duration = duration_val * 60
                    else:
                        duration = duration_val
                    break
                else:
                    duration = float(matches[0])
                    break
        
        # Calculate calories burned
        if exercise_type:
            # Normalize the exercise type to match our database
            normalized_type = None
            for key in self.exercise_database:
                if key in exercise_type or exercise_type in key:
                    normalized_type = key
                    break
            
            if normalized_type:
                calories_per_minute = self.exercise_database[normalized_type]
                calories_burned = calories_per_minute * duration
                
                return {
                    'result': True,
                    'name': normalized_type,
                    'duration': duration,
                    'calories_burned': round(calories_burned),
                    'message': f"Burned approximately {round(calories_burned)} calories from {duration} minutes of {normalized_type}"
                }
        
        return {
            'result': False,
            'message': "Exercise not recognized or duration not specified. Please try again."
        }
    
    def _calculate_nutrition(self, nutrition_data, quantity, base_quantity):
        """Calculate nutrition values based on quantity"""
        ratio = quantity / base_quantity
        return {
            'calories': int(nutrition_data['calories'] * ratio),
            'protein': int(nutrition_data['protein'] * ratio),
            'carbohydrates': int(nutrition_data['carbohydrates'] * ratio),
            'fiber': int(nutrition_data['fiber'] * ratio),
            'sugar': int(nutrition_data['sugar'] * ratio),
            'sodium': int(nutrition_data['sodium'] * ratio),
        }
