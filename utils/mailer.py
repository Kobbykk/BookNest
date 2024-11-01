from flask_mail import Message
from extensions import mail

def send_order_status_email(user_email, order_id, status, items):
    """Send email notification for order status updates"""
    subject = f'Order #{order_id} Status Update'
    
    items_html = '<ul>'
    for item in items:
        items_html += f'<li>{item.book.title} x {item.quantity}</li>'
    items_html += '</ul>'
    
    html = f'''
    <h2>Order Status Update</h2>
    <p>Your order #{order_id} status has been updated to: <strong>{status}</strong></p>
    <h3>Order Items:</h3>
    {items_html}
    '''
    
    msg = Message(
        subject=subject,
        recipients=[user_email],
        html=html
    )
    
    mail.send(msg)
