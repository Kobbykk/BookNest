// Cart functionality
document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    // Common headers for all fetch requests
    const headers = {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken || ''
    };

    // Update cart count
    function updateCartCount() {
        fetch('/cart/count', {
            headers: {
                'X-CSRF-Token': csrfToken || ''
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                updateCartBadge(data.count);
            } else {
                console.error('Server error:', data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching cart count:', error);
        });
    }

    function updateCartBadge(count) {
        const cartCount = document.getElementById('cart-count');
        if (cartCount) {
            cartCount.textContent = count;
            cartCount.style.display = count > 0 ? 'inline' : 'none';
        }
    }

    // Add to cart functionality
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            
            if (!csrfToken) {
                showToast('Error', 'Session expired. Please refresh the page.', 'danger');
                return;
            }

            const bookId = this.dataset.bookId;
            
            // Disable button while processing
            this.disabled = true;
            
            fetch('/cart/add', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ book_id: bookId })
            })
            .then(response => {
                if (!response.ok) {
                    if (response.status === 401) {
                        window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                        return null;
                    }
                    return response.json().then(data => {
                        throw new Error(data.error || `HTTP error! status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (!data) return;
                
                if (data.success) {
                    updateCartBadge(data.count);
                    showToast('Success', 'Book added to cart!', 'success');
                } else {
                    throw new Error(data.error || 'Failed to add book to cart');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error', error.message || 'Failed to add book to cart', 'danger');
            })
            .finally(() => {
                // Re-enable button after processing
                this.disabled = false;
            });
        });
    });

    // Cart quantity update functionality
    document.querySelectorAll('.cart-quantity').forEach(input => {
        let previousValue = input.value;
        
        input.addEventListener('change', function() {
            if (!csrfToken) {
                showToast('Error', 'Session expired. Please refresh the page.', 'danger');
                this.value = previousValue;
                return;
            }

            const itemId = this.dataset.itemId;
            const newQuantity = parseInt(this.value);
            
            if (isNaN(newQuantity) || newQuantity < 0) {
                showToast('Error', 'Invalid quantity', 'danger');
                this.value = previousValue;
                return;
            }

            fetch(`/cart/update/${itemId}`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ quantity: newQuantity })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || `HTTP error! status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    updateCartBadge(data.count);
                    if (newQuantity === 0) {
                        window.location.reload();
                    } else {
                        previousValue = newQuantity;
                    }
                } else {
                    throw new Error(data.error || 'Failed to update cart');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error', error.message || 'Failed to update cart', 'danger');
                this.value = previousValue;
            });
        });
    });

    // Remove from cart functionality
    document.querySelectorAll('.remove-item').forEach(button => {
        button.addEventListener('click', function() {
            if (!csrfToken) {
                showToast('Error', 'Session expired. Please refresh the page.', 'danger');
                return;
            }

            const itemId = this.dataset.itemId;
            
            // Disable button while processing
            this.disabled = true;
            
            fetch(`/cart/remove/${itemId}`, {
                method: 'POST',
                headers: headers
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || `HTTP error! status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    updateCartBadge(data.count);
                    window.location.reload();
                } else {
                    throw new Error(data.error || 'Failed to remove item');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error', error.message || 'Failed to remove item', 'danger');
            })
            .finally(() => {
                // Re-enable button after processing
                this.disabled = false;
            });
        });
    });

    // Initialize cart count on page load
    updateCartCount();

    // Toast notification function
    function showToast(title, message, type = 'info') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) return;
        
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
        
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: 3000
        });
        
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
});
