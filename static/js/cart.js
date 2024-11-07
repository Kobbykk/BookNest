// Cart functionality
document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
        console.error('CSRF token not found');
    }

    // Update cart count
    function updateCartCount() {
        fetch('/cart/count', {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
                'X-CSRF-Token': csrfToken || '',
                'Cache-Control': 'no-cache'
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (response.status === 401) {
                // User is not authenticated, hide cart count
                const cartCount = document.getElementById('cart-count');
                if (cartCount) {
                    cartCount.style.display = 'none';
                }
                return null;
            }
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data) return;
            
            const cartCount = document.getElementById('cart-count');
            if (cartCount && data.success) {
                cartCount.textContent = data.count;
                cartCount.style.display = data.count > 0 ? 'inline' : 'none';
            }
        })
        .catch(error => {
            console.error('Error fetching cart count:', error);
            // Don't update badge on error, but also don't show the error to user
        });
    }

    // Add to cart functionality
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const bookId = this.dataset.bookId;
            if (!bookId) {
                console.error('Book ID not found');
                return;
            }
            
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
            .then(response => {
                if (response.status === 401) {
                    window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                    return null;
                }
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
                console.error('Error:', error);
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
            .then(response => {
                if (response.status === 401) {
                    window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                    return null;
                }
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
                console.error('Error:', error);
                showToast('Error', error.message || 'Failed to update cart', 'danger');
                this.value = previousValue;
            });
        });
    });

    // Remove from cart functionality
    document.querySelectorAll('.remove-item').forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            if (!itemId) {
                console.error('Item ID not found');
                return;
            }
            
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
            .then(response => {
                if (response.status === 401) {
                    window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                    return null;
                }
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
                console.error('Error:', error);
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
