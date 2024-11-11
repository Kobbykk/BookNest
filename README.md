# 📚 Online Bookshop Platform

A comprehensive online bookshop application built with Flask, featuring a robust shopping cart system, secure payment processing, and an intuitive admin interface.

## 🌟 Features

- **User Authentication & Authorization**
  - Secure login and registration
  - Role-based access control
  - Profile management

- **Book Management**
  - Advanced search and filtering
  - Category organization
  - Multiple book formats support
  - Dynamic pricing system

- **Shopping Experience**
  - Intuitive shopping cart
  - Secure checkout process
  - Order history tracking
  - Wishlist functionality

- **Admin Dashboard**
  - Book inventory management
  - Order processing
  - User management
  - Category management
  - Sales analytics

- **Security Features**
  - CSRF protection
  - Secure session management
  - Password hashing
  - Input validation

## 🛠️ Technology Stack

- **Backend**: Flask (Python 3.11)
- **Database**: PostgreSQL
- **Frontend**: 
  - Bootstrap 5
  - Vanilla JavaScript
  - Jinja2 Templates
- **Payment Processing**: Stripe
- **Security**: Flask-Login, WTForms
- **Email**: Flask-Mail

## 🚀 Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/online-bookshop.git
   cd online-bookshop
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file with:
   ```
   FLASK_SECRET_KEY=your_secret_key
   DATABASE_URL=postgresql://user:password@localhost:5432/bookshop
   STRIPE_SECRET_KEY=your_stripe_secret_key
   STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
   ```

5. **Initialize database**
   ```bash
   python reset_db.py
   python seed_books.py
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

## 📝 API Documentation

The application provides RESTful APIs for:
- Book management
- Cart operations
- Order processing
- User management
- Category management

Detailed API documentation is available in the `/docs` directory.

## 🧪 Testing

Run the test suite:
```bash
python -m pytest
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- Edwin Addai - Initial work - [@Kobbykk](https://github.com/Kobbykk)

## 🙏 Acknowledgments

- Bootstrap for the UI components
- Stripe for payment processing
- Flask community for the excellent framework