from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta
from app import app, db
from models import User, CustomItem, Meal, MealItem, FoodLog, ExerciseLog
from forms import RegistrationForm, LoginForm, NaturalLanguageInputForm, CustomItemForm, MealForm, MealItemForm, ProfileForm
from nlp_processor import NLPProcessor
import json
from werkzeug.security import generate_password_hash

# Initialize NLP Processor
nlp_processor = NLPProcessor()

# Home route
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            weight=form.weight.data,
            height=form.height.data,
            age=form.age.data,
            gender=form.gender.data,
            activity_level=form.activity_level.data,
            motive=form.motive.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Login failed. Please check your email and password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Main dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    form = NaturalLanguageInputForm()
    
    # Get today's date and the date range for past week and month
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Calculate today's nutrition summary
    todays_food = FoodLog.query.filter(
        FoodLog.user_id == current_user.id,
        cast(FoodLog.date, Date) == today
    ).all()
    
    today_calories = sum(log.calories for log in todays_food)
    today_protein = sum(log.protein for log in todays_food)
    today_carbs = sum(log.carbohydrates for log in todays_food)
    today_fiber = sum(log.fiber for log in todays_food)
    today_sugar = sum(log.sugar for log in todays_food)
    today_sodium = sum(log.sodium for log in todays_food)
    
    # Calculate today's exercise summary
    todays_exercise = ExerciseLog.query.filter(
        ExerciseLog.user_id == current_user.id,
        cast(ExerciseLog.date, Date) == today
    ).all()
    
    today_calories_burned = sum(log.calories_burned for log in todays_exercise)
    
    # Calculate calorie data for the past week (for chart)
    daily_calories = []
    daily_calories_burned = []
    daily_labels = []
    
    for i in range(7):
        day = today - timedelta(days=6-i)
        daily_labels.append(day.strftime('%a'))
        
        # Food calories for this day
        day_food = FoodLog.query.filter(
            FoodLog.user_id == current_user.id,
            cast(FoodLog.date, Date) == day
        ).all()
        day_calories = sum(log.calories for log in day_food)
        daily_calories.append(day_calories)
        
        # Exercise calories for this day
        day_exercise = ExerciseLog.query.filter(
            ExerciseLog.user_id == current_user.id,
            cast(ExerciseLog.date, Date) == day
        ).all()
        day_calories_burned = sum(log.calories_burned for log in day_exercise)
        daily_calories_burned.append(day_calories_burned)
    
    # Get recent food logs
    recent_food_logs = FoodLog.query.filter_by(user_id=current_user.id).order_by(FoodLog.date.desc()).limit(5).all()
    
    # Get recent exercise logs
    recent_exercise_logs = ExerciseLog.query.filter_by(user_id=current_user.id).order_by(ExerciseLog.date.desc()).limit(5).all()
    
    return render_template(
        'dashboard.html', 
        form=form,
        today_calories=today_calories,
        today_protein=today_protein,
        today_carbs=today_carbs,
        today_fiber=today_fiber,
        today_sugar=today_sugar,
        today_sodium=today_sodium,
        today_calories_burned=today_calories_burned,
        net_calories=today_calories - today_calories_burned,
        daily_labels=json.dumps(daily_labels),
        daily_calories=json.dumps(daily_calories),
        daily_calories_burned=json.dumps(daily_calories_burned),
        recent_food_logs=recent_food_logs,
        recent_exercise_logs=recent_exercise_logs
    )

# Natural language processing routes
@app.route('/process_query', methods=['POST'])
@login_required
def process_query():
    form = NaturalLanguageInputForm()
    if form.validate_on_submit():
        query = form.query.data
        
        # First try to process as a food query
        food_result = nlp_processor.process_food_query(query, current_user.id)
        
        if food_result.get('result'):
            # Add to food log
            food_log = FoodLog(
                user_id=current_user.id,
                name=food_result['name'],
                quantity=food_result['quantity'],
                calories=food_result['calories'],
                protein=food_result['protein'],
                carbohydrates=food_result['carbohydrates'],
                fiber=food_result['fiber'],
                sugar=food_result['sugar'],
                sodium=food_result['sodium'],
                description=query
            )
            db.session.add(food_log)
            db.session.commit()
            
            flash(f"Added {food_result['name']} with {food_result['calories']} calories to your food log!", 'success')
            return redirect(url_for('dashboard'))
        else:
            # Try to process as an exercise query
            exercise_result = nlp_processor.process_exercise_query(query)
            
            if exercise_result.get('result'):
                # Add to exercise log
                exercise_log = ExerciseLog(
                    user_id=current_user.id,
                    name=exercise_result['name'],
                    duration=exercise_result['duration'],
                    calories_burned=exercise_result['calories_burned'],
                    description=query
                )
                db.session.add(exercise_log)
                db.session.commit()
                
                flash(f"Added {exercise_result['name']} burning {exercise_result['calories_burned']} calories to your exercise log!", 'success')
                return redirect(url_for('dashboard'))
            else:
                flash("Couldn't understand your input. Please try again with more details.", 'danger')
                return redirect(url_for('dashboard'))
    
    flash('Invalid form submission.', 'danger')
    return redirect(url_for('dashboard'))

# Food item management routes
@app.route('/food_items')
@login_required
def food_items():
    form = CustomItemForm()
    items = CustomItem.query.filter_by(user_id=current_user.id).order_by(CustomItem.name).all()
    return render_template('food_items.html', items=items, form=form)

@app.route('/add_food_item', methods=['POST'])
@login_required
def add_food_item():
    form = CustomItemForm()
    if form.validate_on_submit():
        item = CustomItem(
            user_id=current_user.id,
            name=form.name.data,
            description=form.description.data,
            unit=form.unit.data,
            quantity=form.quantity.data,
            calories=form.calories.data,
            protein=form.protein.data,
            carbohydrates=form.carbohydrates.data,
            fiber=form.fiber.data,
            sugar=form.sugar.data,
            sodium=form.sodium.data
        )
        db.session.add(item)
        db.session.commit()
        flash(f'Food item "{form.name.data}" added successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('food_items'))

@app.route('/edit_food_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_food_item(item_id):
    item = CustomItem.query.get_or_404(item_id)
    
    # Check if item belongs to the current user
    if item.user_id != current_user.id:
        flash('You are not authorized to edit this item.', 'danger')
        return redirect(url_for('food_items'))
    
    form = CustomItemForm()
    
    if request.method == 'GET':
        form.name.data = item.name
        form.description.data = item.description
        form.unit.data = item.unit
        form.quantity.data = item.quantity
        form.calories.data = item.calories
        form.protein.data = item.protein
        form.carbohydrates.data = item.carbohydrates
        form.fiber.data = item.fiber
        form.sugar.data = item.sugar
        form.sodium.data = item.sodium
    
    if form.validate_on_submit():
        item.name = form.name.data
        item.description = form.description.data
        item.unit = form.unit.data
        item.quantity = form.quantity.data
        item.calories = form.calories.data
        item.protein = form.protein.data
        item.carbohydrates = form.carbohydrates.data
        item.fiber = form.fiber.data
        item.sugar = form.sugar.data
        item.sodium = form.sodium.data
        
        db.session.commit()
        flash(f'Food item "{item.name}" updated successfully!', 'success')
        return redirect(url_for('food_items'))
    
    return render_template('food_items.html', form=form, edit_item=item, items=CustomItem.query.filter_by(user_id=current_user.id).all())

@app.route('/delete_food_item/<int:item_id>', methods=['POST'])
@login_required
def delete_food_item(item_id):
    item = CustomItem.query.get_or_404(item_id)
    
    # Check if item belongs to the current user
    if item.user_id != current_user.id:
        flash('You are not authorized to delete this item.', 'danger')
        return redirect(url_for('food_items'))
    
    db.session.delete(item)
    db.session.commit()
    flash(f'Food item "{item.name}" deleted successfully!', 'success')
    return redirect(url_for('food_items'))

# Meal management routes
@app.route('/meals')
@login_required
def meals():
    meal_form = MealForm()
    meal_item_form = MealItemForm()
    
    # Populate the food item choices for the meal item form
    meal_item_form.custom_item_id.choices = [
        (item.id, f"{item.name} ({item.quantity} {item.unit})")
        for item in CustomItem.query.filter_by(user_id=current_user.id).order_by(CustomItem.name).all()
    ]
    
    meals = Meal.query.filter_by(user_id=current_user.id).order_by(Meal.name).all()
    
    return render_template('meals.html', 
                          meals=meals, 
                          meal_form=meal_form, 
                          meal_item_form=meal_item_form)

@app.route('/add_meal', methods=['POST'])
@login_required
def add_meal():
    form = MealForm()
    if form.validate_on_submit():
        meal = Meal(
            user_id=current_user.id,
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(meal)
        db.session.commit()
        flash(f'Meal "{form.name.data}" created successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('meals'))

@app.route('/edit_meal/<int:meal_id>', methods=['GET', 'POST'])
@login_required
def edit_meal(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    
    # Check if meal belongs to the current user
    if meal.user_id != current_user.id:
        flash('You are not authorized to edit this meal.', 'danger')
        return redirect(url_for('meals'))
    
    form = MealForm()
    
    if request.method == 'GET':
        form.name.data = meal.name
        form.description.data = meal.description
    
    if form.validate_on_submit():
        meal.name = form.name.data
        meal.description = form.description.data
        
        db.session.commit()
        flash(f'Meal "{meal.name}" updated successfully!', 'success')
        return redirect(url_for('meals'))
    
    return render_template('edit_meal.html', form=form, meal=meal)

@app.route('/delete_meal/<int:meal_id>', methods=['POST'])
@login_required
def delete_meal(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    
    # Check if meal belongs to the current user
    if meal.user_id != current_user.id:
        flash('You are not authorized to delete this meal.', 'danger')
        return redirect(url_for('meals'))
    
    db.session.delete(meal)
    db.session.commit()
    flash(f'Meal "{meal.name}" deleted successfully!', 'success')
    return redirect(url_for('meals'))

@app.route('/add_meal_item/<int:meal_id>', methods=['POST'])
@login_required
def add_meal_item(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    
    # Check if meal belongs to the current user
    if meal.user_id != current_user.id:
        flash('You are not authorized to modify this meal.', 'danger')
        return redirect(url_for('meals'))
    
    form = MealItemForm()
    
    # Populate the food item choices for the form
    form.custom_item_id.choices = [
        (item.id, f"{item.name} ({item.quantity} {item.unit})")
        for item in CustomItem.query.filter_by(user_id=current_user.id).all()
    ]
    
    if form.validate_on_submit():
        # Check if the selected food item exists and belongs to the user
        food_item = CustomItem.query.get(form.custom_item_id.data)
        if not food_item or food_item.user_id != current_user.id:
            flash('Invalid food item selected.', 'danger')
            return redirect(url_for('meals'))
        
        meal_item = MealItem(
            meal_id=meal.id,
            custom_item_id=form.custom_item_id.data,
            quantity=form.quantity.data
        )
        
        db.session.add(meal_item)
        db.session.commit()
        flash(f'Added {food_item.name} to meal "{meal.name}"!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('meals'))

@app.route('/delete_meal_item/<int:meal_item_id>', methods=['POST'])
@login_required
def delete_meal_item(meal_item_id):
    meal_item = MealItem.query.get_or_404(meal_item_id)
    meal = Meal.query.get(meal_item.meal_id)
    
    # Check if the meal belongs to the current user
    if meal.user_id != current_user.id:
        flash('You are not authorized to modify this meal.', 'danger')
        return redirect(url_for('meals'))
    
    food_item = CustomItem.query.get(meal_item.custom_item_id)
    db.session.delete(meal_item)
    db.session.commit()
    
    flash(f'Removed {food_item.name} from meal "{meal.name}"!', 'success')
    return redirect(url_for('meals'))

@app.route('/add_meal_to_log/<int:meal_id>', methods=['POST'])
@login_required
def add_meal_to_log(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    
    # Check if meal belongs to the current user
    if meal.user_id != current_user.id:
        flash('You are not authorized to use this meal.', 'danger')
        return redirect(url_for('meals'))
    
    # Create a food log entry for the entire meal
    food_log = FoodLog(
        user_id=current_user.id,
        name=meal.name,
        quantity=1,
        calories=meal.total_calories,
        protein=meal.total_protein,
        carbohydrates=meal.total_carbs,
        fiber=meal.total_fiber,
        sugar=meal.total_sugar,
        sodium=meal.total_sodium,
        description=f"Added meal: {meal.name}",
        meal_id=meal.id
    )
    
    db.session.add(food_log)
    db.session.commit()
    
    flash(f'Added meal "{meal.name}" with {meal.total_calories} calories to your food log!', 'success')
    return redirect(url_for('dashboard'))

# User profile route
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    
    if request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.weight.data = current_user.weight
        form.height.data = current_user.height
        form.age.data = current_user.age
        form.gender.data = current_user.gender
        form.activity_level.data = current_user.activity_level
        form.motive.data = current_user.motive
    
    if form.validate_on_submit():
        # Check if the username is being changed and is already taken
        if form.username.data != current_user.username and User.query.filter_by(username=form.username.data).first():
            flash('That username is already taken. Please choose another one.', 'danger')
            return redirect(url_for('profile'))
        
        # Check if the email is being changed and is already registered
        if form.email.data != current_user.email and User.query.filter_by(email=form.email.data).first():
            flash('That email is already registered. Please use a different one.', 'danger')
            return redirect(url_for('profile'))
        
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.weight = form.weight.data
        current_user.height = form.height.data
        current_user.age = form.age.data
        current_user.gender = form.gender.data
        current_user.activity_level = form.activity_level.data
        current_user.motive = form.motive.data
        
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', form=form)

# API routes for chart data
@app.route('/api/chart_data')
@login_required
def chart_data():
    # Get date range parameters
    period = request.args.get('period', 'week')
    
    today = datetime.now().date()
    
    if period == 'week':
        days = 7
        start_date = today - timedelta(days=days-1)
        date_format = '%a'  # Abbreviated weekday name
    elif period == 'month':
        days = 30
        start_date = today - timedelta(days=days-1)
        date_format = '%d'  # Day of month
    else:  # year
        # Group by month for a year
        months = 12
        start_date = (today - timedelta(days=365)).replace(day=1)
        date_format = '%b'  # Abbreviated month name
        
    # Initialize data structures
    if period == 'year':
        # For year, we group by month
        labels = [(today - timedelta(days=30*i)).strftime(date_format) for i in range(months-1, -1, -1)]
        food_data = [0] * months
        exercise_data = [0] * months
        
        # Get food logs for the past year
        food_logs = FoodLog.query.filter(
            FoodLog.user_id == current_user.id,
            FoodLog.date >= start_date
        ).all()
        
        # Get exercise logs for the past year
        exercise_logs = ExerciseLog.query.filter(
            ExerciseLog.user_id == current_user.id,
            ExerciseLog.date >= start_date
        ).all()
        
        # Aggregate data by month
        for log in food_logs:
            month_idx = months - 1 - ((today.year - log.date.year) * 12 + (today.month - log.date.month))
            if 0 <= month_idx < months:
                food_data[month_idx] += log.calories
        
        for log in exercise_logs:
            month_idx = months - 1 - ((today.year - log.date.year) * 12 + (today.month - log.date.month))
            if 0 <= month_idx < months:
                exercise_data[month_idx] += log.calories_burned
    else:
        # For week or month, we group by day
        labels = [(start_date + timedelta(days=i)).strftime(date_format) for i in range(days)]
        food_data = [0] * days
        exercise_data = [0] * days
        
        # Get food logs for the period
        food_logs = FoodLog.query.filter(
            FoodLog.user_id == current_user.id,
            cast(FoodLog.date, Date) >= start_date,
            cast(FoodLog.date, Date) <= today
        ).all()
        
        # Get exercise logs for the period
        exercise_logs = ExerciseLog.query.filter(
            ExerciseLog.user_id == current_user.id,
            cast(ExerciseLog.date, Date) >= start_date,
            cast(ExerciseLog.date, Date) <= today
        ).all()
        
        # Aggregate data by day
        for log in food_logs:
            day_idx = (log.date.date() - start_date).days
            if 0 <= day_idx < days:
                food_data[day_idx] += log.calories
        
        for log in exercise_logs:
            day_idx = (log.date.date() - start_date).days
            if 0 <= day_idx < days:
                exercise_data[day_idx] += log.calories_burned
    
    # Calculate net calories (intake - burned)
    net_data = [food_data[i] - exercise_data[i] for i in range(len(food_data))]
    
    return jsonify({
        'labels': labels,
        'foodData': food_data,
        'exerciseData': exercise_data,
        'netData': net_data
    })

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/compare')
@login_required
def compare():
    """
    Page to compare ideal vs. actual nutrition and exercise
    """
    # Import nutrition calculator
    from nutrition_calculator import get_full_recommendations
    
    # Check if user has enough profile data
    if not all([current_user.weight, current_user.height, current_user.age, 
                current_user.gender, current_user.activity_level, current_user.motive]):
        flash('Please complete your profile first to get personalized recommendations.', 'warning')
        return redirect(url_for('profile'))
    
    # Get recommendations
    recommendations = get_full_recommendations(current_user)
    
    # Calculate today's nutrition summary
    today = datetime.now().date()
    todays_food = FoodLog.query.filter(
        FoodLog.user_id == current_user.id,
        cast(FoodLog.date, Date) == today
    ).all()
    
    today_calories = sum(log.calories for log in todays_food)
    today_protein = sum(log.protein for log in todays_food)
    today_carbs = sum(log.carbohydrates for log in todays_food)
    today_fiber = sum(log.fiber for log in todays_food)
    today_sugar = sum(log.sugar for log in todays_food)
    today_sodium = sum(log.sodium for log in todays_food)
    
    # Calculate today's exercise summary
    todays_exercise = ExerciseLog.query.filter(
        ExerciseLog.user_id == current_user.id,
        cast(ExerciseLog.date, Date) == today
    ).all()
    
    today_exercise_minutes = sum(log.duration for log in todays_exercise)
    today_calories_burned = sum(log.calories_burned for log in todays_exercise)
    
    # Calculate past week's exercise data
    week_ago = today - timedelta(days=7)
    
    weekly_exercise = ExerciseLog.query.filter(
        ExerciseLog.user_id == current_user.id,
        cast(ExerciseLog.date, Date) >= week_ago,
        cast(ExerciseLog.date, Date) <= today
    ).all()
    
    weekly_exercise_minutes = sum(log.duration for log in weekly_exercise)
    weekly_calories_burned = sum(log.calories_burned for log in weekly_exercise)
    
    # Count unique days with strength training in the past week
    strength_training_days = set()
    for log in weekly_exercise:
        # Simple heuristic: workouts with less than 20 minutes and burning
        # fewer than 100 calories are likely strength training
        if (log.duration < 20 and log.calories_burned < 100) or "strength" in log.name.lower() or "weight" in log.name.lower():
            strength_training_days.add(log.date.date())
    
    return render_template(
        'compare.html',
        recommendations=recommendations,
        today_nutrition={
            'calories': today_calories,
            'protein': today_protein,
            'carbs': today_carbs,
            'fiber': today_fiber,
            'sugar': today_sugar,
            'sodium': today_sodium
        },
        today_exercise={
            'minutes': today_exercise_minutes,
            'calories_burned': today_calories_burned
        },
        weekly_exercise={
            'minutes': weekly_exercise_minutes,
            'calories_burned': weekly_calories_burned,
            'strength_days': len(strength_training_days)
        }
    )

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
