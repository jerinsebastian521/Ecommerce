

from flask import Flask, render_template, request, redirect, url_for, flash,session
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.validators import DataRequired, Email, Length
from forms import ContactForm, RegistrationForm, LoginForm
import requests

# Initialize Flask app and configure database
app = Flask(__name__)
app.config['SECRET_KEY'] = 'gksinfotech'

REGISTER_API_URL = "https://ecommerce-api-six-kappa.vercel.app/register"
LOGIN_API_URL = "https://ecommerce-api-six-kappa.vercel.app/login"

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Prepare the payload for the API
        payload = {
            "username": form.email.data,
            "password": form.password.data
        }
        try:
            # Call the external register API
            response = requests.post(REGISTER_API_URL, json=payload)
            if response.status_code == 201:  # Assuming 201 for successful registration
                flash('Registration successful. You can now log in.', 'success')
                return redirect(url_for('login'))
            else:
                # Handle API errors
                flash(f"Registration failed: {response.json().get('message', 'Unknown error')}", 'danger')
        except requests.exceptions.RequestException as e:
            # Handle connection errors
            flash(f"An error occurred: {str(e)}", 'danger')
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Prepare the payload for the API request
        payload = {
            "username": form.username.data,
            "password": form.password.data
        }
        try:
            # Call the external login API
            response = requests.post(LOGIN_API_URL, json=payload)
            if response.status_code == 200:
                # Assuming API returns a JSON response with user info
                user_data = response.json()
                user_role = user_data.get('role')  # Get the user's role from the API response
                
                if user_role == 'customer':
                    session['token'] = user_data['access_token']
                    session['user_id'] = user_data['id']
                    session['username'] = user_data['username']
                    session['role'] = user_role
                    flash('Login successful!', 'success')
                    return redirect(url_for('dashboard'))  # Redirect to customer dashboard
                elif user_role == 'admin':
                    session['access_token'] = user_data['access_token']
                    session['user_id'] = user_data['id']
                    session['username'] = user_data['username']
                    session['role'] = user_role
                    flash('Login successful!', 'success')
                    return redirect(url_for('admin_home'))  # Redirect to admin home page
                else:
                    flash('Invalid user role.', 'danger')
            else:
                # Handle invalid credentials or other errors from API
                flash(f"Login failed: {response.json().get('message', 'Unknown error')}", 'danger')
        except requests.exceptions.RequestException as e:
            # Handle any exceptions (e.g., network issues)
            flash(f"An error occurred: {str(e)}", 'danger')

    return render_template('login.html', form=form)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))
    
    # Call the API to get all products
    try:
        token = session.get('token')  # Assuming you store the token in session
        # Prepare the Authorization header
        headers = {
            'Authorization': f'Bearer {token}'  # Add Bearer token here
        }
        response = requests.get('https://ecommerce-api-six-kappa.vercel.app/items',headers=headers)  # Replace with your API URL
        if response.status_code == 200:
            products = response.json()  # Parse the JSON response into a Python dictionary/list
        else:
            flash('Failed to fetch products.', 'danger')
            products = []
    except requests.exceptions.RequestException as e:
        flash(f'An error occurred while fetching products: {e}', 'danger')
        products = []
    return render_template('dashboard.html', products=products,username=session.get('username'))


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Please log in to view your cart.', 'danger')
        return redirect(url_for('login'))
    try:
        token = session.get('token')
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get('https://ecommerce-api-six-kappa.vercel.app/cart', headers=headers)

        if response.status_code == 200:
            raw_cart_items = response.json()

            # Combine items with the same item ID
            combined_items = {}
            for entry in raw_cart_items:
                item_id = entry['item']['id']
                if item_id in combined_items:
                    combined_items[item_id]['quantity'] += entry['quantity']
                else:
                    combined_items[item_id] = {
                        'item': entry['item'],
                        'quantity': entry['quantity']
                    }

            # Flatten the dictionary back to a list
            cart_items = list(combined_items.values())

            # Calculate total price and total items
            total_price = sum(item['item']['price'] * item['quantity'] for item in cart_items)
            total_items = sum(item['quantity'] for item in cart_items)
        else:
            flash('Failed to fetch cart items. Please try again later.', 'danger')
            cart_items = []
            total_price = 0
            total_items = 0
    except requests.exceptions.RequestException as e:
        flash(f'Error while fetching cart items: {e}', 'danger')
        cart_items = []
        total_price = 0
        total_items = 0

    return render_template(
        'cart.html',
        cart_items=cart_items,
        total_price=total_price,
        total_items=total_items
    )


@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id')
    product_name = request.form.get('product_name')
    cart_data = {
        "item_id": product_id,
        "quantity": 1  # Default quantity
    }
    print(cart_data)
    # Call the external API to insert the product into the cart
    try:
        token = session.get('token')
        api_url = 'https://ecommerce-api-six-kappa.vercel.app/cart' 
        headers = {
            'Authorization': f'Bearer {token}'  
        } 

        # Sending POST request to the external API
        response = requests.post(api_url, json=cart_data, headers=headers)
        if response.status_code == 201:
            # If the API call is successful
            flash(f'{product_name} has been added to your cart.', 'success')
        else:
            # Handle failure if API responds with error
            flash('Failed to add product to cart. Please try again.', 'danger')
    except requests.exceptions.RequestException as e:
        # Handle error if API request fails (e.g., network error)
        flash(f'Error occurred while contacting the API: {e}', 'danger')

    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
