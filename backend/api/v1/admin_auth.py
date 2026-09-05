# Shared admin authorization module - consolidates AUTHORIZED_ADMIN_EMAILS
# This eliminates duplicate lists across auth.py, review.py, risk_review.py, and other files

# Authorized Admin Emails Whitelist
# Emails explicitly permitted to hold elevated Admin roles
AUTHORIZED_ADMIN_EMAILS = [
    "admin@tata.com",
    "generalcounsel@tata.com",
    "senior.reviewer@tata.com"
]

def check_is_admin(user) -> bool:
    """Verify if a user has admin privileges via role or authorized email.

    Checks:
    - User role is in ["Admin", "General Counsel", "Senior Reviewer"]
    - User email is in the AUTHORIZED_ADMIN_EMAILS whitelist

    Note: Substring matching (e.g., "admin" in email) has been removed to prevent
    non-admin users with "admin" in their email from gaining elevated privileges.
    """
    email_lower = user.email.lower() if user.email else ""
    is_role_admin = user.role in ["Admin", "General Counsel", "Senior Reviewer"]
    is_email_admin = email_lower in AUTHORIZED_ADMIN_EMAILS
    return is_role_admin or is_email_admin

def is_authorized_admin_email(email: str) -> bool:
    """Check if an email domain/local-part is authorized for admin roles."""
    return email.lower() in AUTHORIZED_ADMIN_EMAILS