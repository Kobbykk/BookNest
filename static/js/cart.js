document.addEventListener('DOMContentLoaded', function() {
    // Fetch initial cart count
    fetchCartCount();

    // Add to cart functionality
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function() {
            const bookId = this.dataset.bookId;
            fetch('/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    book_id: bookId,
                    quantity: 1
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateCartCount(data.cart_count);
                    alert('Book added to cart!');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to add book to cart. Please try again.');
            });
        });
    });

    // Cart quantity update
    const quantityInputs = document.querySelectorAll('.cart-quantity');
    quantityInputs.forEach(input => {
        input.addEventListener('change', function() {
            const bookId = this.dataset.bookId;
            const quantity = this.value;
            
            fetch('/cart/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    book_id: bookId,
                    quantity: quantity
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    fetchCartCount();
                    if (quantity <= 0) {
                        window.location.reload();
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to update cart. Please try again.');
            });
        });
    });
});

// Fetch current cart count
function fetchCartCount() {
    fetch('/cart/count')
        .then(response => response.json())
        .then(data => {
            updateCartCount(data.count);
        })
        .catch(error => {
            console.error('Error fetching cart count:', error);
        });
}

// Update cart count badge
function updateCartCount(count) {
    const cartCount = document.getElementById('cart-count');
    if (cartCount) {
        count = parseInt(count) || 0;
        cartCount.textContent = count;
        cartCount.classList.toggle('d-none', count === 0);
    }
}
