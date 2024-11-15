// Cart functionality
document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token from meta tag at the start
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
        console.error('CSRF token not found');
    }

    // Update cart count
    function updateCartCount() {
        fetch('/cart/count', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
                'X-CSRF-Token': csrfToken || ''
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (response.status === 401) {
                // Don't redirect on cart count - just show 0
                return { success: true, count: 0 };
            }
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `HTTP error! status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                const cartCount = document.getElementById('cart-count');
                if (cartCount) {
                    cartCount.textContent = data.count;
                    cartCount.style.display = data.count > 0 ? 'inline' : 'none';
                }
            } else {
                throw new Error(data.error || 'Failed to update cart count');
            }
        })
        .catch(error => {
            console.error('Error fetching cart count:', error.message);
            // Don't update badge on error
        });
    }

    // Handle authentication redirects
    function handleAuthResponse(response) {
        if (response.status === 401) {
            return response.json().then(data => {
                if (data.redirect) {
                    window.location.href = data.redirect;
                } else {
                    window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                }
                return null;
            });
        }
        return response;
    }

    // Add to cart functionality
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const bookId = this.dataset.bookId;
            
            this.disabled = true;

            fetch('/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'X-CSRF-Token': csrfToken || ''
                },
                credentials: 'same-origin',
                body: JSON.stringify({ book_id: bookId })
            })
            .then(handleAuthResponse)
            .then(response => {
                if (!response) return null;
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || `HTTP error! status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (!data) return;
                
                if (data.success) {
                    updateCartCount();
                    showToast('Success', 'Book added to cart!', 'success');
                } else {
                    throw new Error(data.error || 'Failed to add book to cart');
                }
            })
            .catch(error => {
                console.error('Error:', error.message);
                showToast('Error', error.message || 'Failed to add book to cart', 'danger');
            })
            .finally(() => {
                this.disabled = false;
            });
        });
    });

    // Initialize cart count on page load
    updateCartCount();

    // Cart quantity update functionality
    document.querySelectorAll('.cart-quantity').forEach(input => {
        let previousValue = input.value;
        
        input.addEventListener('change', function() {
            const itemId = this.dataset.itemId;
            const newQuantity = parseInt(this.value);
            
            if (isNaN(newQuantity) || newQuantity < 0) {
                showToast('Error', 'Invalid quantity', 'danger');
                this.value = previousValue;
                return;
            }

            fetch(`/cart/update/${itemId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'X-CSRF-Token': csrfToken || ''
                },
                credentials: 'same-origin',
                body: JSON.stringify({ quantity: newQuantity })
            })
            .then(handleAuthResponse)
            .then(response => {
                if (!response) return null;
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || `HTTP error! status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (!data) return;
                
                if (data.success) {
                    updateCartCount();
                    if (newQuantity === 0) {
                        window.location.reload();
                    } else {
                        previousValue = newQuantity;
                        // Update total price if on cart page
                        const totalElement = document.querySelector('td[colspan="2"] strong');
                        if (totalElement && data.total) {
                            totalElement.textContent = `$${data.total.toFixed(2)}`;
                        }
                    }
                } else {
                    throw new Error(data.error || 'Failed to update cart');
                }
            })
            .catch(error => {
                console.error('Error:', error.message);
                showToast('Error', error.message || 'Failed to update cart', 'danger');
                this.value = previousValue;
            });
        });
    });

    // Remove from cart functionality
    document.querySelectorAll('.remove-item').forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            this.disabled = true;

            fetch(`/cart/remove/${itemId}`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'X-CSRF-Token': csrfToken || ''
                },
                credentials: 'same-origin'
            })
            .then(handleAuthResponse)
            .then(response => {
                if (!response) return null;
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || `HTTP error! status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (!data) return;
                
                if (data.success) {
                    updateCartCount();
                    const row = this.closest('tr');
                    if (row) {
                        row.remove();
                        if (data.count === 0) {
                            window.location.reload();
                        }
                    }
                } else {
                    throw new Error(data.error || 'Failed to remove item');
                }
            })
            .catch(error => {
                console.error('Error:', error.message);
                showToast('Error', error.message || 'Failed to remove item', 'danger');
            })
            .finally(() => {
                this.disabled = false;
            });
        });
    });

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
