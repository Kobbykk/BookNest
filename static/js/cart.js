// Cart functionality
document.addEventListener('DOMContentLoaded', function() {
    // Update cart count
    function updateCartCount() {
        fetch('/cart/count')
            .then(response => {
                if (!response.ok) {
                    if (response.status === 401) {
                        // If unauthorized, just show 0 items
                        updateCartBadge(0);
                        return;
                    }
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data && data.success) {
                    updateCartBadge(data.count);
                }
            })
            .catch(error => {
                console.warn('Unable to fetch cart count:', error);
                // On error, don't update the badge
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
            const bookId = this.dataset.bookId;
            
            fetch('/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ book_id: bookId, quantity: 1 })
            })
            .then(response => {
                if (response.status === 401) {
                    // Redirect to login with return URL
                    window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                    return null;
                }
                return response.json();
            })
            .then(data => {
                if (!data) return; // Skip if redirecting to login
                
                if (data.success) {
                    updateCartCount();
                    showToast('Success', 'Book added to cart!', 'success');
                } else {
                    showToast('Error', data.error || 'Failed to add book to cart', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error', 'Failed to add book to cart. Please try again.', 'danger');
            });
        });
    });

    // Cart quantity update functionality
    document.querySelectorAll('.cart-quantity').forEach(input => {
        input.addEventListener('change', function() {
            const itemId = this.dataset.itemId;
            const newQuantity = parseInt(this.value);
            
            if (isNaN(newQuantity) || newQuantity < 0) {
                showToast('Error', 'Invalid quantity', 'danger');
                return;
            }

            fetch(`/cart/update/${itemId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ quantity: newQuantity })
            })
            .then(response => {
                if (!response.ok) {
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return null;
                    }
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (!data) return;
                
                if (data.success) {
                    if (newQuantity === 0) {
                        // Remove the item row if quantity is 0
                        const row = this.closest('tr');
                        if (row) row.remove();
                    }
                    updateCartCount();
                    // Reload the page to update totals
                    window.location.reload();
                } else {
                    showToast('Error', data.error || 'Failed to update cart', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error', 'Failed to update cart. Please try again.', 'danger');
            });
        });
    });

    // Remove from cart functionality
    document.querySelectorAll('.remove-item').forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            
            fetch(`/cart/remove/${itemId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => {
                if (!response.ok) {
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return null;
                    }
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (!data) return;
                
                if (data.success) {
                    const row = this.closest('tr');
                    if (row) row.remove();
                    updateCartCount();
                    // Reload the page to update totals
                    window.location.reload();
                } else {
                    showToast('Error', data.error || 'Failed to remove item', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error', 'Failed to remove item. Please try again.', 'danger');
            });
        });
    });

    // Initialize cart count on page load
    updateCartCount();

    // Toast notification function
    function showToast(title, message, type = 'info') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.style.position = 'fixed';
            container.style.top = '20px';
            container.style.right = '20px';
            container.style.zIndex = '1050';
            document.body.appendChild(container);
        }
        
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
        
        document.getElementById('toast-container').appendChild(toast);
        
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
