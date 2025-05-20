"""
Nutrition Calculator for HealthTracker App
Calculates recommended nutrition and exercise based on user attributes and goals
"""

def calculate_bmr(weight, height, age, gender):
    """
    Calculate Basal Metabolic Rate (BMR) using the Mifflin-St Jeor Equation
    
    Args:
        weight: Weight in kg
        height: Height in cm
        age: Age in years
        gender: 'male', 'female', or 'other'
    
    Returns:
        BMR value in calories
    """
    if gender == 'male':
        return (10 * weight) + (6.25 * height) - (5 * age) + 5
    elif gender == 'female':
        return (10 * weight) + (6.25 * height) - (5 * age) - 161
    else:
        # For non-binary gender, use average of male and female
        return (10 * weight) + (6.25 * height) - (5 * age) - 78

def calculate_tdee(bmr, activity_level):
    """
    Calculate Total Daily Energy Expenditure (TDEE) based on BMR and activity level
    
    Args:
        bmr: Basal Metabolic Rate
        activity_level: User's activity level
    
    Returns:
        TDEE value in calories
    """
    activity_multipliers = {
        'sedentary': 1.2,      # Little or no exercise
        'light': 1.375,        # Light exercise 1-3 days/week
        'moderate': 1.55,      # Moderate exercise 3-5 days/week
        'active': 1.725,       # Hard exercise 6-7 days/week
        'very_active': 1.9     # Very hard exercise & physical job
    }
    
    multiplier = activity_multipliers.get(activity_level, 1.2)
    return bmr * multiplier

def calculate_target_calories(tdee, motive, weight):
    """
    Calculate target calories based on TDEE and user's goal
    
    Args:
        tdee: Total Daily Energy Expenditure
        motive: User's goal ('lose', 'maintain', or 'gain')
        weight: User's weight in kg (used for calculating protein needs)
    
    Returns:
        Dictionary with target calories and macronutrient breakdowns
    """
    if motive == 'lose':
        # 20% calorie deficit for weight loss
        target_calories = tdee * 0.8
        protein_pct = 0.35  # Higher protein for preserving muscle during weight loss
        fat_pct = 0.25
        carb_pct = 0.4
    elif motive == 'gain':
        # 15% calorie surplus for weight gain
        target_calories = tdee * 1.15
        protein_pct = 0.3
        fat_pct = 0.25
        carb_pct = 0.45
    else:  # maintain
        target_calories = tdee
        protein_pct = 0.25
        fat_pct = 0.25
        carb_pct = 0.5

    # Calculate macros in grams
    # Protein: 4 calories per gram
    # Carbs: 4 calories per gram
    # Fat: 9 calories per gram
    protein_grams = (target_calories * protein_pct) / 4
    carbs_grams = (target_calories * carb_pct) / 4
    fat_grams = (target_calories * fat_pct) / 9

    # For weight loss, ensure adequate protein (min 1.6g per kg of body weight)
    if motive == 'lose' and protein_grams < (weight * 1.6):
        protein_grams = weight * 1.6
        
    # Fiber recommendation (14g per 1000 calories)
    fiber_grams = (target_calories / 1000) * 14
    
    # Sugar recommendation (max 10% of calories)
    sugar_grams = (target_calories * 0.1) / 4
    
    # Sodium recommendation (2300mg standard limit)
    sodium_mg = 2300
    
    return {
        'calories': round(target_calories),
        'protein': round(protein_grams),
        'carbs': round(carbs_grams),
        'fat': round(fat_grams),
        'fiber': round(fiber_grams),
        'sugar': round(sugar_grams),
        'sodium': sodium_mg
    }

def calculate_exercise_recommendations(weight, motive, activity_level):
    """
    Calculate recommended exercise based on weight, goal, and activity level
    
    Args:
        weight: Weight in kg
        motive: User's goal ('lose', 'maintain', or 'gain')
        activity_level: Current activity level
    
    Returns:
        Dictionary with exercise recommendations
    """
    # Base minutes of exercise per week
    if activity_level == 'sedentary':
        base_minutes = 150  # Start with 150 minutes for sedentary
    elif activity_level == 'light':
        base_minutes = 180
    elif activity_level == 'moderate':
        base_minutes = 210
    elif activity_level == 'active':
        base_minutes = 240
    else:  # very_active
        base_minutes = 300
    
    # Adjust based on motive
    if motive == 'lose':
        cardio_minutes = base_minutes * 1.2  # 20% more cardio for weight loss
        strength_days = 2  # At least 2 days of strength training
    elif motive == 'gain':
        cardio_minutes = base_minutes * 0.8  # Less cardio for muscle gain
        strength_days = 4  # More strength training for muscle gain
    else:  # maintain
        cardio_minutes = base_minutes
        strength_days = 3  # Balanced approach
    
    # Calculate calories burned per week based on weight and minutes
    # Rough estimate: calories burned per minute = 0.0175 * MET * weight in kg
    # Using MET of 7 for moderate-intensity exercise
    calories_burned_per_minute = 0.0175 * 7 * weight
    weekly_calories_burned = cardio_minutes * calories_burned_per_minute
    
    return {
        'weekly_cardio_minutes': round(cardio_minutes),
        'weekly_strength_days': strength_days,
        'daily_cardio_minutes': round(cardio_minutes / 7),  # Spread across 7 days
        'weekly_calories_burned': round(weekly_calories_burned),
        'daily_calories_burned': round(weekly_calories_burned / 7)
    }

def get_full_recommendations(user):
    """
    Get comprehensive nutrition and exercise recommendations based on user profile
    
    Args:
        user: User object with weight, height, age, gender, activity_level, and motive
    
    Returns:
        Dictionary with comprehensive recommendations
    """
    # Calculate BMR
    bmr = calculate_bmr(user.weight, user.height, user.age, user.gender)
    
    # Calculate TDEE
    tdee = calculate_tdee(bmr, user.activity_level)
    
    # Calculate target nutrition
    nutrition = calculate_target_calories(tdee, user.motive, user.weight)
    
    # Calculate exercise recommendations
    exercise = calculate_exercise_recommendations(user.weight, user.motive, user.activity_level)
    
    return {
        'bmr': round(bmr),
        'tdee': round(tdee),
        'nutrition': nutrition,
        'exercise': exercise
    }