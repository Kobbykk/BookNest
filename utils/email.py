from flask_mail import Message
from app import mail
from flask import render_template_string

def send_order_status_email(user_email, order_id, status, items):
    """Send an email notification when order status changes"""
    
    # HTML template for the email
    template = """
    <html>
    <body>
        <h2>Order Status Update</h2>
        <p>Your order #{{ order_id }} status has been updated to: <strong>{{ status }}</strong></p>
        
        <h3>Order Details:</h3>
        <ul>
        {% for item in items %}
            <li>{{ item.book.title }} - Quantity: {{ item.quantity }}</li>
        {% endfor %}
        </ul>
        
        <p>Thank you for shopping with us!</p>
    </body>
    </html>
    """
    
    # Render the template with the provided data
    html_content = render_template_string(
        template,
        order_id=order_id,
        status=status,
        items=items
    )
    
    # Create the email message
    subject = f"Order #{order_id} Status Update - {status}"
    msg = Message(
        subject=subject,
        recipients=[user_email],
        html=html_content
    )
    
    # Send the email
    mail.send(msg)
