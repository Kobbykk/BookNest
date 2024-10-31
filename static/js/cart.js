document.addEventListener('DOMContentLoaded', function() {
    // Fetch initial cart count
    fetchCartCount();

    // Add to cart functionality
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const bookId = this.dataset.bookId;
            try {
                const response = await fetch('/cart/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        book_id: bookId,
                        quantity: 1
                    })
                });

                if (!response.ok) {
                    throw new Error('Failed to add item to cart');
                }

                const data = await response.json();
                if (data.success) {
                    updateCartCount(data.cart_count);
                    showToast('Success', 'Book added to cart!', 'success');
                } else {
                    throw new Error(data.error || 'Failed to add book to cart');
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('Error', error.message, 'danger');
            }
        });
    });

    // Cart quantity update
    const quantityInputs = document.querySelectorAll('.cart-quantity');
    quantityInputs.forEach(input => {
        input.addEventListener('change', async function() {
            const bookId = this.dataset.bookId;
            const quantity = parseInt(this.value);
            
            try {
                const response = await fetch('/cart/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        book_id: bookId,
                        quantity: quantity
                    })
                });

                if (!response.ok) {
                    throw new Error('Failed to update cart');
                }

                const data = await response.json();
                if (data.success) {
                    updateCartCount(data.cart_count);
                    if (quantity <= 0) {
                        window.location.reload();
                    }
                } else {
                    throw new Error(data.error || 'Failed to update cart');
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('Error', error.message, 'danger');
                this.value = this.defaultValue;
            }
        });
    });
});

// Fetch current cart count
async function fetchCartCount() {
    try {
        const response = await fetch('/cart/count');
        if (!response.ok) {
            throw new Error('Failed to fetch cart count');
        }
        
        const data = await response.json();
        if (data.success) {
            updateCartCount(data.count);
        } else {
            throw new Error(data.error || 'Failed to fetch cart count');
        }
    } catch (error) {
        console.error('Error fetching cart count:', error);
        // Set count to 0 on error
        updateCartCount(0);
    }
}

// Update cart count badge
function updateCartCount(count) {
    const cartCount = document.getElementById('cart-count');
    if (cartCount) {
        count = parseInt(count) || 0;
        cartCount.textContent = count.toString();
        // Only show badge if count is greater than 0
        cartCount.style.display = count > 0 ? 'inline' : 'none';
    }
}

// Show toast notification
function showToast(title, message, type = 'info') {
    const toastContainer = document.createElement('div');
    toastContainer.style.position = 'fixed';
    toastContainer.style.top = '20px';
    toastContainer.style.right = '20px';
    toastContainer.style.zIndex = '1050';
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}</strong><br>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    document.body.appendChild(toastContainer);
    
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 3000
    });
    
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(toastContainer);
    });
}
