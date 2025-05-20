/**
 * Meals management functionality
 * Handles meal creation, editing, and management of meal items
 */

document.addEventListener('DOMContentLoaded', function() {
  // Handle meal form submission
  const mealForm = document.querySelector('form[action="/add_meal"]');
  if (mealForm) {
    mealForm.addEventListener('submit', function(e) {
      const nameInput = document.getElementById('name');
      if (!nameInput.value.trim()) {
        e.preventDefault();
        nameInput.classList.add('is-invalid');
        
        // Add invalid feedback if not present
        let feedback = nameInput.nextElementSibling;
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
          feedback = document.createElement('div');
          feedback.className = 'invalid-feedback';
          nameInput.parentNode.insertBefore(feedback, nameInput.nextSibling);
          feedback.textContent = 'Please enter a meal name';
        }
        return false;
      }
      
      // Show loading state
      const submitBtn = this.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
      
      // Let the form submit normally
      return true;
    });
  }
  
  // Handle meal item form submission
  const mealItemForms = document.querySelectorAll('form[action*="add_meal_item"]');
  mealItemForms.forEach(form => {
    form.addEventListener('submit', function(e) {
      let isValid = true;
      
      // Check select
      const foodItemSelect = this.querySelector('select[name="custom_item_id"]');
      if (foodItemSelect && (!foodItemSelect.value || foodItemSelect.value === '')) {
        isValid = false;
        foodItemSelect.classList.add('is-invalid');
      } else if (foodItemSelect) {
        foodItemSelect.classList.remove('is-invalid');
      }
      
      // Check quantity
      const quantityInput = this.querySelector('input[name="quantity"]');
      if (quantityInput) {
        const quantity = parseFloat(quantityInput.value);
        if (isNaN(quantity) || quantity <= 0) {
          isValid = false;
          quantityInput.classList.add('is-invalid');
          
          // Add invalid feedback if not present
          let feedback = quantityInput.nextElementSibling;
          if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            quantityInput.parentNode.insertBefore(feedback, quantityInput.nextSibling);
          }
          feedback.textContent = 'Please enter a valid positive number';
        } else {
          quantityInput.classList.remove('is-invalid');
        }
      }
      
      if (!isValid) {
        e.preventDefault();
        return false;
      }
      
      // Show loading state
      const submitBtn = this.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding...';
      
      // Let the form submit normally
      return true;
    });
  });
  
  // Handle delete buttons for meal items
  const deleteMealItemButtons = document.querySelectorAll('form[action*="delete_meal_item"] button');
  deleteMealItemButtons.forEach(button => {
    button.addEventListener('click', function() {
      this.disabled = true;
      this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
      this.closest('form').submit();
    });
  });
  
  // Handle "Add to Food Log" buttons
  const addToLogForms = document.querySelectorAll('form[action*="add_meal_to_log"]');
  addToLogForms.forEach(form => {
    form.addEventListener('submit', function() {
      const button = this.querySelector('button');
      if (button) {
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding...';
      }
    });
  });
  
  // Handle delete meal buttons
  const deleteMealButtons = document.querySelectorAll('form[action*="delete_meal"] button[type="submit"]');
  deleteMealButtons.forEach(button => {
    button.addEventListener('click', function() {
      this.disabled = true;
      this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Deleting...';
      this.closest('form').submit();
    });
  });
});
