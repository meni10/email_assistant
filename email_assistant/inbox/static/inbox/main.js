// DOM Elements
const emailsDiv = document.getElementById('emails');
const paginationDiv = document.getElementById('pagination');
const loadBtn = document.getElementById('load');
const genBtn = document.getElementById('gen');
const saveBtn = document.getElementById('save');
const toInput = document.getElementById('to');
const subjectInput = document.getElementById('subject');
const saveStatus = document.getElementById('saveStatus');
const themeBtn = document.getElementById('theme-button');
const emailArea = document.getElementById('email_text');
const summaryArea = document.getElementById('summary');
const replyArea = document.getElementById('generated_reply');
const draftMessageArea = document.getElementById('draft_message');
let currentPage = 1;
let totalPages = 1;
let perPage = 10; // Default items per page

// Initialize the page
document.addEventListener('DOMContentLoaded', function () {
    loadEmails(currentPage);
    checkAuthStatus();
    
    // Theme toggle button functionality
    themeBtn.addEventListener('click', function () {
        document.body.classList.toggle('dark-theme');
        const isDark = document.body.classList.contains('dark-theme');
        themeBtn.innerText = isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme';
        localStorage.setItem('theme', isDark ? 'dark-theme' : 'light-theme');
    });
    
    if (loadBtn) {
        loadBtn.addEventListener('click', function () {
            loadEmails(1); // Always load page 1 on refresh
        });
    }
    
    if (genBtn) {
        genBtn.addEventListener('click', generateReply);
    }
    
    if (saveBtn) {
        saveBtn.addEventListener('click', saveDraft);
    }
    
    // Add event listener for "Select All" checkbox
    const selectAllCheckbox = document.getElementById('select-all-emails');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const emailCheckboxes = document.querySelectorAll('.email-item input[type="checkbox"]');
            emailCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            toggleBulkActionButton();
        });
    }
    
    // Add event listeners for individual email checkboxes (using event delegation)
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('form-check-input') && e.target.type === 'checkbox' && e.target.id !== 'select-all-emails') {
            toggleBulkActionButton();
            updateSelectAllCheckbox();
        }
    });
    
    // Add event listener for bulk mark as read button
    const bulkMarkReadBtn = document.getElementById('bulk-mark-read');
    if (bulkMarkReadBtn) {
        bulkMarkReadBtn.addEventListener('click', markSelectedAsRead);
    }
});

// Check authentication status
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth/status/');
        const data = await response.json();
        const authSection = document.getElementById('auth-section');
        const authBtn = document.getElementById('auth-btn');
        
        if (data.authenticated) {
            authSection.style.display = 'none';
        } else {
            authSection.style.display = 'block';
        }
    } catch (error) {
        console.error('Error checking auth status:', error);
    }
}

// Load emails for the current page
async function loadEmails(page = 1) {
    if (page < 1) page = 1;
    if (page > totalPages) page = totalPages;
    currentPage = page;
    
    if (!emailsDiv) return;
    
    // Show loading state
    emailsDiv.innerHTML = `  
        <div class="text-center p-4">
            <div class="spinner-border text-primary mb-2"></div>
            <p class="text-muted">Loading emails...</p>
        </div>
    `;
    
    if (loadBtn) {
        loadBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Loading...';
        loadBtn.disabled = true;
    }
    
    try {
        const response = await fetch(`/unread-emails/?page=${page}&per_page=${perPage}`);
        const data = await response.json();
        
        if (data.ok) {
            totalPages = data.total_pages || 1;
            currentPage = data.current_page || currentPage;
            perPage = data.per_page || perPage;
            
            renderEmails(data.emails);
            renderPagination(data);
        } else {
            emailsDiv.innerHTML = ` 
                <div class="alert alert-danger m-3">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Error: ${data.error}
                </div>
            `;
        }
    } catch (error) {
        emailsDiv.innerHTML = ` 
            <div class="alert alert-danger m-3">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Error loading emails: ${error.message}
            </div>
        `;
    } finally {
        if (loadBtn) {
            loadBtn.innerHTML = '<i class="fas fa-sync-alt me-2"></i>Refresh';
            loadBtn.disabled = false;
        }
    }
}

// Render emails to the list
function renderEmails(emails) {
    emailsDiv.innerHTML = '';
    if (emails.length === 0) {
        emailsDiv.innerHTML = ` 
            <div class="text-center p-4 text-muted">
                <i class="fas fa-inbox fa-3x mb-3"></i>
                <p>No unread emails found</p>
            </div>
        `;
        return;
    }
    
    emails.forEach(email => {
        const emailItem = document.createElement('div');
        emailItem.classList.add('email-item');
        emailItem.setAttribute('data-email-id', email.id);
        
        // Replace the existing emailItem.innerHTML with this code that includes the checkbox
        emailItem.innerHTML = ` 
            <div class="d-flex align-items-start">
                <div class="form-check me-2">
                    <input class="form-check-input" type="checkbox" value="${email.id}" id="email-${email.id}">
                </div>
                <div class="flex-grow-1">
                    <div class="email-meta text-muted small mb-1">
                        <strong>From:</strong> ${email.from || 'Unknown'} •
                        <span>${email.date || ''}</span>
                    </div>
                    <h6 class="email-subject mb-1">${email.subject || '(no subject)'}</h6>
                    <p class="email-snippet text-muted mb-2">${(email.snippet || '').substring(0, 100)}...</p>
                </div>
            </div>
            <div class="email-actions">
                <button class="btn btn-sm btn-outline-primary use-email-btn me-1" 
                        onclick="useEmail(${JSON.stringify(email).replace(/"/g, '&quot;')})">
                    <i class="fas fa-reply me-1"></i> Reply
                </button>
                <button class="btn btn-sm btn-outline-secondary me-1" 
                        onclick="useEmailForReplyAll(${JSON.stringify(email).replace(/"/g, '&quot;')})">
                    <i class="fas fa-reply-all me-1"></i> Reply All
                </button>
                <button class="btn btn-sm btn-outline-success" 
                        onclick="markAsRead('${email.id}', this)">
                    <i class="fas fa-check me-1"></i> Mark as Read
                </button>
            </div>
        `;
        
        emailsDiv.appendChild(emailItem);
    });
}

// Mark email as read function
async function markAsRead(emailId, buttonElement) {
    try {
        // Disable the button to prevent multiple clicks
        buttonElement.disabled = true;
        buttonElement.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Marking...';
        
        const response = await fetch(`/mark-as-read/${emailId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        });
        
        const data = await response.json();
        
        if (data.ok) {
            // Find the email element and remove it with animation
            const emailElement = document.querySelector(`[data-email-id="${emailId}"]`);
            if (emailElement) {
                // Add fade-out animation
                emailElement.style.transition = 'opacity 0.3s ease';
                emailElement.style.opacity = '0';
                
                // Remove the element after animation completes
                setTimeout(() => {
                    emailElement.remove();
                    
                    // Update the email count
                    const emailCount = document.getElementById('email-count');
                    if (emailCount) {
                        const currentCount = parseInt(emailCount.textContent);
                        emailCount.textContent = Math.max(0, currentCount - 1);
                    }
                    
                    // Check if there are any emails left on the current page
                    const remainingEmails = document.querySelectorAll('.email-item');
                    if (remainingEmails.length === 0) {
                        // If we're not on the first page, go back one page
                        if (currentPage > 1) {
                            loadEmails(currentPage - 1);
                        } else {
                            // If we're on the first page, reload the current page
                            loadEmails(currentPage);
                        }
                    }
                }, 300);
            }
            
            showNotification('Email marked as read', 'success');
        } else {
            // Re-enable the button on error
            buttonElement.disabled = false;
            buttonElement.innerHTML = '<i class="fas fa-check me-1"></i> Mark as Read';
            showNotification('Failed to mark email as read: ' + data.error, 'error');
        }
    } catch (error) {
        // Re-enable the button on error
        buttonElement.disabled = false;
        buttonElement.innerHTML = '<i class="fas fa-check me-1"></i> Mark as Read';
        showNotification('Network error: ' + error.message, 'error');
    }
}

// Add this function to handle bulk mark as read
async function markSelectedAsRead() {
    const checkboxes = document.querySelectorAll('.email-item input[type="checkbox"]:checked');
    const emailIds = Array.from(checkboxes).map(cb => cb.value);
    
    if (emailIds.length === 0) {
        showNotification('Please select emails to mark as read', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/bulk-mark-as-read/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ email_ids: emailIds })
        });
        
        const data = await response.json();
        
        if (data.ok) {
            // Remove selected emails from the list
            checkboxes.forEach(checkbox => {
                const emailElement = checkbox.closest('.email-item');
                if (emailElement) {
                    emailElement.style.transition = 'opacity 0.3s ease';
                    emailElement.style.opacity = '0';
                    setTimeout(() => emailElement.remove(), 300);
                }
            });
            
            // Update email count
            const emailCount = document.getElementById('email-count');
            if (emailCount) {
                const currentCount = parseInt(emailCount.textContent);
                emailCount.textContent = Math.max(0, currentCount - emailIds.length);
            }
            
            // Reset the "Select All" checkbox
            const selectAllCheckbox = document.getElementById('select-all-emails');
            if (selectAllCheckbox) {
                selectAllCheckbox.indeterminate = false;
                selectAllCheckbox.checked = false;
            }
            
            // Hide the bulk action button
            const bulkButton = document.getElementById('bulk-mark-read');
            if (bulkButton) {
                bulkButton.style.display = 'none';
            }
            
            // Check if we need to reload the page
            const remainingEmails = document.querySelectorAll('.email-item');
            if (remainingEmails.length === 0) {
                // If we're not on the first page, go back one page
                if (currentPage > 1) {
                    loadEmails(currentPage - 1);
                } else {
                    // If we're on the first page, reload the current page
                    loadEmails(currentPage);
                }
            }
            
            showNotification(`${emailIds.length} email(s) marked as read`, 'success');
        } else {
            showNotification('Failed to mark emails as read: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Network error: ' + error.message, 'error');
    }
}

// Render pagination buttons
function renderPagination(data) {
    paginationDiv.innerHTML = ''; // clear existing
    const container = document.createElement('div');
    container.className = 'd-flex justify-content-between align-items-center flex-wrap mt-3';
    
    // Left side: Per page selector
    const perPageDiv = document.createElement('div');
    perPageDiv.className = 'd-flex align-items-center';
    
    const perPageLabel = document.createElement('span');
    perPageLabel.className = 'me-2';
    perPageLabel.textContent = 'Show:';
    
    const perPageSelect = document.createElement('select');
    perPageSelect.className = 'form-select form-select-sm';
    perPageSelect.style.width = 'auto';
    
    [5, 10, 20, 50].forEach(num => {
        const option = document.createElement('option');
        option.value = num;
        option.textContent = num;
        if (num === data.per_page) {
            option.selected = true;
        }
        perPageSelect.appendChild(option);
    });
    
    perPageSelect.addEventListener('change', function() {
        perPage = parseInt(this.value);
        loadEmails(1);
    });
    
    perPageDiv.appendChild(perPageLabel);
    perPageDiv.appendChild(perPageSelect);
    
    // Middle: Page numbers
    const pageNumbersDiv = document.createElement('div');
    pageNumbersDiv.className = 'd-flex align-items-center';
    
    // Previous button
    const prevBtn = document.createElement('button');
    prevBtn.className = 'btn btn-outline-primary btn-sm me-1';
    prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
    prevBtn.disabled = !data.has_previous;
    prevBtn.addEventListener('click', () => {
        if (data.has_previous) loadEmails(currentPage - 1);
    });
    pageNumbersDiv.appendChild(prevBtn);
    
    // Page numbers
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(data.total_pages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage < maxVisiblePages - 1) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    // First page
    if (startPage > 1) {
        const firstBtn = document.createElement('button');
        firstBtn.className = 'btn btn-outline-primary btn-sm me-1';
        firstBtn.textContent = '1';
        firstBtn.addEventListener('click', () => loadEmails(1));
        pageNumbersDiv.appendChild(firstBtn);
        
        if (startPage > 2) {
            const ellipsis = document.createElement('span');
            ellipsis.className = 'mx-1';
            ellipsis.textContent = '...';
            pageNumbersDiv.appendChild(ellipsis);
        }
    }
    
    // Visible page numbers
    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = `btn btn-sm me-1 ${i === currentPage ? 'btn-primary' : 'btn-outline-primary'}`;
        pageBtn.textContent = i;
        pageBtn.addEventListener('click', () => loadEmails(i));
        pageNumbersDiv.appendChild(pageBtn);
    }
    
    // Last page
    if (endPage < data.total_pages) {
        if (endPage < data.total_pages - 1) {
            const ellipsis = document.createElement('span');
            ellipsis.className = 'mx-1';
            ellipsis.textContent = '...';
            pageNumbersDiv.appendChild(ellipsis);
        }
        
        const lastBtn = document.createElement('button');
        lastBtn.className = 'btn btn-outline-primary btn-sm me-1';
        lastBtn.textContent = data.total_pages;
        lastBtn.addEventListener('click', () => loadEmails(data.total_pages));
        pageNumbersDiv.appendChild(lastBtn);
    }
    
    // Next button
    const nextBtn = document.createElement('button');
    nextBtn.className = 'btn btn-outline-primary btn-sm';
    nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
    nextBtn.disabled = !data.has_next;
    nextBtn.addEventListener('click', () => {
        if (data.has_next) loadEmails(currentPage + 1);
    });
    pageNumbersDiv.appendChild(nextBtn);
    
    // Right side: Page info
    const pageInfoDiv = document.createElement('div');
    pageInfoDiv.className = 'text-muted small';
    
    const startItem = (currentPage - 1) * perPage + 1;
    const endItem = Math.min(currentPage * perPage, data.total_emails);
    
    pageInfoDiv.textContent = `Showing ${startItem}-${endItem} of ${data.total_emails} emails`;
    
    // Add all parts to container
    container.appendChild(perPageDiv);
    container.appendChild(pageNumbersDiv);
    container.appendChild(pageInfoDiv);
    
    paginationDiv.appendChild(container);
}

// Helper function to extract email address from a string
function extractEmailAddress(text) {
    if (!text) return '';
    // Regular expression to match email addresses
    const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+)/;
    const match = text.match(emailRegex);
    return match ? match[0] : '';
}

// Use email function
async function useEmail(email) {
    if (emailArea) {
        // Show loading state
        emailArea.value = 'Loading email content...';
        
        try {
            // Fetch the full email details
            const response = await fetch(`/email/${email.id}/`);
            const data = await response.json();
            
            if (data.ok) {
                const fullEmail = data.email;
                const emailContent = `
From: ${fullEmail.from || 'Unknown'}
Subject: ${fullEmail.subject || 'No Subject'}
Date: ${fullEmail.date || ''}
${fullEmail.body_text || ''}
                `.trim();
                
                emailArea.value = emailContent;
                
                // Set recipient email address
                if (toInput) {
                    const recipientEmail = extractEmailAddress(fullEmail.from);
                    toInput.value = recipientEmail;
                    
                    // Add visual feedback
                    toInput.classList.add('border-success');
                    setTimeout(() => {
                        toInput.classList.remove('border-success');
                    }, 2000);
                    
                    console.log('Set recipient email to:', recipientEmail);
                }
                
                // Set subject
                if (subjectInput) {
                    subjectInput.value = fullEmail.subject ? `Re: ${fullEmail.subject}` : 'Re: Your email';
                }
            } else {
                // Handle the case where email is not found
                if (response.status === 404) {
                    emailArea.value = 'This email is no longer available. It may have been deleted or moved.';
                    showNotification('Email no longer available', 'warning');
                } else {
                    emailArea.value = `Error loading email: ${data.error}`;
                    showNotification('Failed to load email', 'error');
                }
            }
        } catch (error) {
            emailArea.value = `Error loading email: ${error.message}`;
            showNotification('Network error occurred', 'error');
        }
    }
    
    if (emailArea) {
        emailArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Add this function to handle "Reply All"
function useEmailForReplyAll(email) {
    // First, use the existing useEmail function to load the email content
    useEmail(email);
    
    // Then, if we have the full email details, add all recipients
    fetch(`/email/${email.id}/`)
        .then(response => response.json())
        .then(data => {
            if (data.ok && data.email) {
                const fullEmail = data.email;
                let recipients = [];
                
                // Add the original sender
                if (fullEmail.from) {
                    recipients.push(extractEmailAddress(fullEmail.from));
                }
                
                // Add "To" recipients
                if (fullEmail.to) {
                    const toEmails = fullEmail.to.split(',').map(email => extractEmailAddress(email.trim())).filter(email => email);
                    recipients = recipients.concat(toEmails);
                }
                
                // Add "Cc" recipients if available
                if (fullEmail.cc) {
                    const ccEmails = fullEmail.cc.split(',').map(email => extractEmailAddress(email.trim())).filter(email => email);
                    recipients = recipients.concat(ccEmails);
                }
                
                // Remove duplicates and set the recipient field
                const uniqueRecipients = [...new Set(recipients)];
                if (toInput) {
                    toInput.value = uniqueRecipients.join(', ');
                    
                    // Add visual feedback
                    toInput.classList.add('border-info');
                    setTimeout(() => {
                        toInput.classList.remove('border-info');
                    }, 2000);
                }
                
                // Change the subject to indicate it's a reply to all
                if (subjectInput) {
                    subjectInput.value = fullEmail.subject ? `Re: ${fullEmail.subject} (Reply All)` : 'Re: Your email (Reply All)';
                }
                
                showNotification('Reply All mode activated', 'info');
            }
        })
        .catch(error => {
            console.error('Error fetching email details for reply all:', error);
            showNotification('Error setting up Reply All', 'error');
        });
}

// Generate reply function
async function generateReply() {
    if (!emailArea || !summaryArea || !replyArea) return;
    const emailText = emailArea.value.trim();
    if (!emailText) {
        showNotification('Please enter email text first', 'error');
        return;
    }
    summaryArea.value = 'Generating summary...';
    replyArea.value = 'Generating reply...';
    if (genBtn) {
        genBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';
        genBtn.disabled = true;
    }
    try {
        const response = await fetch('/generate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ email_text: emailText })
        });
        const data = await response.json();
        if (data.ok) {
            summaryArea.value = data.summary || 'No summary generated';
            replyArea.value = data.draft_reply || 'No reply generated';
            showNotification('Reply generated successfully!', 'success');
            
            // Auto-populate draft message
            if (draftMessageArea) {
                draftMessageArea.value = data.draft_reply || '';
            }
        } else {
            summaryArea.value = 'Error: ' + (data.error || 'Unknown error');
            showNotification('Failed to generate reply', 'error');
        }
    } catch (error) {
        summaryArea.value = 'Error: ' + error.message;
        showNotification('Network error occurred', 'error');
    } finally {
        if (genBtn) {
            genBtn.innerHTML = '<i class="fas fa-robot me-2"></i> Summarize & Generate';
            genBtn.disabled = false;
        }
    }
}

// Save draft function
async function saveDraft() {
    if (!toInput || !subjectInput || !draftMessageArea) return;
    const to = toInput.value.trim();
    const subject = subjectInput.value.trim();
    const body = draftMessageArea.value.trim();
    if (!to || !subject || !body) {
        showNotification('Please fill in To, Subject, and Body', 'error');
        return;
    }
    try {
        const response = await fetch('/save-draft/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ to, subject, body })   // ✅ match backend
        });
        const data = await response.json();
        if (data.ok) {
            showNotification('Draft saved successfully!', 'success');
            subjectInput.value = '';
            draftMessageArea.value = '';
        } else {
            showNotification('Failed to save draft', 'error');
        }
    } catch (error) {
        showNotification('Network error: ' + error.message, 'error');
    }
}

// Get CSRF token for Django
function getCSRFToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Show notification function
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type === 'warning' ? 'warning' : 'success'} alert-dismissible fade show position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to document
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Toggle the visibility of the bulk action button
function toggleBulkActionButton() {
    const checkedBoxes = document.querySelectorAll('.email-item input[type="checkbox"]:checked');
    const bulkButton = document.getElementById('bulk-mark-read');
    
    if (bulkButton) {
        bulkButton.style.display = checkedBoxes.length > 0 ? 'inline-block' : 'none';
    }
}

// Update the "Select All" checkbox state based on individual checkboxes
function updateSelectAllCheckbox() {
    const selectAllCheckbox = document.getElementById('select-all-emails');
    const emailCheckboxes = document.querySelectorAll('.email-item input[type="checkbox"]');
    
    if (selectAllCheckbox && emailCheckboxes.length > 0) {
        const checkedBoxes = document.querySelectorAll('.email-item input[type="checkbox"]:checked');
        
        if (checkedBoxes.length === 0) {
            selectAllCheckbox.indeterminate = false;
            selectAllCheckbox.checked = false;
        } else if (checkedBoxes.length === emailCheckboxes.length) {
            selectAllCheckbox.indeterminate = false;
            selectAllCheckbox.checked = true;
        } else {
            selectAllCheckbox.indeterminate = true;
        }
    }
}