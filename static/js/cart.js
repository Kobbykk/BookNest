document.addEventListener('DOMContentLoaded', function() {
    // Fetch initial cart count
    fetchCartCount();

    // Add to cart functionality
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const bookId = this.dataset.bookId;
            try {
                const response = await fetch(`/cart/add/${bookId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        book_id: bookId,
                        quantity: 1
                    })
                });

                if (response.status === 401) {
                    window.location.href = '/login';
                    return;
                }

                if (!response.ok) {
                    throw new Error('Failed to add item to cart');
                }

                const data = await response.json();
                if (data.success) {
                    await fetchCartCount();  // Fetch updated count immediately
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

    // Remove item functionality
    const removeButtons = document.querySelectorAll('.remove-item');
    removeButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const itemId = this.dataset.itemId;
            try {
                const response = await fetch(`/cart/remove/${itemId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.error || `Failed to remove item: ${response.status}`);
                }

                const data = await response.json();
                if (data.success) {
                    const row = this.closest('tr');
                    if (row) {
                        row.remove();
                    }
                    
                    await fetchCartCount();
                    
                    window.location.reload();
                } else {
                    throw new Error(data.error || 'Failed to remove item');
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
            const itemId = this.dataset.itemId;
            const quantity = parseInt(this.value);
            
            try {
                const response = await fetch(`/cart/update/${itemId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({
                        quantity: quantity
                    })
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.error || `Failed to update cart: ${response.status}`);
                }

                const data = await response.json();
                if (data.success) {
                    if (quantity <= 0) {
                        window.location.reload();
                    } else {
                        await fetchCartCount();
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

// Update cart count badge (modified to ensure visibility)
function updateCartCount(count) {
    const cartCount = document.getElementById('cart-count');
    if (cartCount) {
        count = parseInt(count) || 0;
        cartCount.textContent = count.toString();
        cartCount.style.display = count > 0 ? 'inline-block' : 'none';  // Changed to inline-block
        
        // Force a reflow to ensure the badge updates
        cartCount.offsetHeight;
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
