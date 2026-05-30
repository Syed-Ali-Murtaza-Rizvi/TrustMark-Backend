# Authentication System Implementation

## Overview
This document describes the implementation of a login and registration system for the Student Attendance Management System backend. The system supports three user types: Students, Teachers, and Management.

## Technical Stack
- **Backend Framework**: Django 5.2.8
- **Database**: PostgreSQL
- **API Framework**: Django REST Framework 3.16.1
- **Authentication**: JWT (JSON Web Tokens) using djangorestframework-simplejwt 5.5.1

## Architecture and Design Decisions

### 1. Model Extensions
Instead of replacing the existing models, we extended them to preserve existing functionality:

- **User Relationship**: Added `OneToOneField` relationship to Django's built-in `User` model for each user type (Student, Teacher, Management)
- **Email Field**: Added `email` field to all three models as the primary identifier for authentication
- **Backward Compatibility**: All new fields are nullable (`null=True, blank=True`) to maintain compatibility with existing data

**Modified Models:**
```python
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    # ... existing fields

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    # ... existing fields

class Management(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    # ... existing fields
```

### 2. Serializers
Created dedicated serializers for each user type to handle registration and login:

- **Registration Serializers**: Validate passwords, ensure email uniqueness, and create both User and profile records
- **Login Serializer**: Simple validation for email and password inputs

**Key Features:**
- Password validation using Django's built-in validators
- Password confirmation field (password2)
- Email uniqueness validation
- Atomic creation of User and corresponding profile

### 3. Views and Endpoints
Implemented class-based views using Django REST Framework:

**Registration Endpoints:**
- `POST /api/auth/register/student/` - Student registration
- `POST /api/auth/register/teacher/` - Teacher registration
- `POST /api/auth/register/management/` - Management registration

**Login Endpoints:**
- `POST /api/auth/login/student/` - Student login
- `POST /api/auth/login/teacher/` - Teacher login
- `POST /api/auth/login/management/` - Management login

### 4. JWT Authentication
JWT tokens are used for stateless authentication:

**Token Configuration:**
- Access token lifetime: 1 hour
- Refresh token lifetime: 7 days
- Algorithm: HS256
- Authentication header type: Bearer

**Token Response:**
Each successful login returns:
```json
{
    "message": "Login successful",
    "refresh": "<refresh_token>",
    "access": "<access_token>",
    "user_type": "student|teacher|management",
    "user_id": <id>,
    "user_name": "<name>",
    "email": "<email>"
}
```

## API Usage Examples

### Student Registration
```bash
POST /api/auth/register/student/
Content-Type: application/json

{
    "email": "student@example.com",
    "password": "SecurePassword123!",
    "password2": "SecurePassword123!",
    "student_name": "John Doe",
    "rfid": "RFID123456",
    "year": 2,
    "dept": "CS",
    "section": "A"
}
```

**Response (201 Created):**
```json
{
    "message": "Student registered successfully",
    "student_id": 1,
    "email": "student@example.com",
    "student_name": "John Doe"
}
```

### Student Login
```bash
POST /api/auth/login/student/
Content-Type: application/json

{
    "email": "student@example.com",
    "password": "SecurePassword123!"
}
```

**Response (200 OK):**
```json
{
    "message": "Login successful",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user_type": "student",
    "student_id": 1,
    "student_name": "John Doe",
    "email": "student@example.com"
}
```

### Teacher Registration
```bash
POST /api/auth/register/teacher/
Content-Type: application/json

{
    "email": "teacher@example.com",
    "password": "SecurePassword123!",
    "password2": "SecurePassword123!",
    "teacher_name": "Jane Smith",
    "rfid": "RFID789012"
}
```

### Management Registration
```bash
POST /api/auth/register/management/
Content-Type: application/json

{
    "email": "admin@example.com",
    "password": "SecurePassword123!",
    "password2": "SecurePassword123!",
    "Management_name": "Admin User"
}
```

## Security Features

1. **Password Validation**: Django's built-in password validators ensure:
   - Minimum length requirement
   - Not too similar to user attributes
   - Not a commonly used password
   - Not entirely numeric

2. **Email Uniqueness**: Prevents duplicate accounts with the same email

3. **JWT Tokens**: Stateless authentication that doesn't require session storage

4. **User Type Verification**: Each login endpoint verifies that the user has the corresponding profile type

5. **CSRF Protection**: Django's CSRF middleware is enabled (though not required for API-only endpoints)

## Files Created/Modified

### New Files:
1. `/core/serializers.py` - Serializers for registration and login
2. `/core/urls.py` - URL routing for authentication endpoints
3. `/.gitignore` - Git ignore file for Python/Django projects
4. `/IMPLEMENTATION.md` - This documentation file

### Modified Files:
1. `/core/models.py` - Added User relationship and email fields to Student, Teacher, and Management models
2. `/core/views.py` - Implemented registration and login views
3. `/FYP_Backend/settings.py` - Added REST Framework and JWT configuration
4. `/FYP_Backend/urls.py` - Included core app URLs

### Generated Files:
1. `/core/migrations/0004_management_email_management_user_student_email_and_more.py` - Database migration

## Database Migration

To apply the changes to the database, run:
```bash
python manage.py migrate
```

**Note**: A PostgreSQL database must be configured and running for migrations to execute successfully.

## Testing the Implementation

### Manual Testing Steps:

1. **Start the Django development server:**
   ```bash
   python manage.py runserver
   ```

2. **Test Student Registration:**
   ```bash
   curl -X POST http://localhost:8000/api/auth/register/student/ \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test.student@example.com",
       "password": "TestPass123!",
       "password2": "TestPass123!",
       "student_name": "Test Student",
       "rfid": "TEST001",
       "year": 1,
       "dept": "CS",
       "section": "A"
     }'
   ```

3. **Test Student Login:**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login/student/ \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test.student@example.com",
       "password": "TestPass123!"
     }'
   ```

4. **Use the access token for authenticated requests:**
   ```bash
   curl -X GET http://localhost:8000/api/some-protected-endpoint/ \
     -H "Authorization: Bearer <access_token>"
   ```

## Future Enhancements

1. **Email Verification**: Add email verification during registration
2. **Password Reset**: Implement password reset functionality
3. **Rate Limiting**: Add rate limiting to prevent brute force attacks
4. **Logout/Token Blacklisting**: Implement token blacklisting for logout
5. **OAuth Integration**: Add support for social login (Google, Facebook, etc.)
6. **Two-Factor Authentication**: Add 2FA for enhanced security
7. **Refresh Token Rotation**: Implement automatic refresh token rotation
8. **Profile Management**: Add endpoints for updating user profiles
9. **Role-Based Permissions**: Implement granular permissions for different user types

## Minimal Changes Philosophy

This implementation follows a minimal changes approach:
- Existing models were extended, not replaced
- All new fields are optional to maintain backward compatibility
- No existing functionality was removed or altered
- The implementation is additive, not destructive
- Standard Django and DRF patterns were used without custom solutions

## Troubleshooting

### Common Issues:

1. **Database Connection Error**: Ensure PostgreSQL is running and credentials in `settings.py` are correct
2. **Migration Errors**: Run `python manage.py makemigrations` before `python manage.py migrate`
3. **Import Errors**: Ensure all required packages are installed: `pip install Django psycopg2-binary djangorestframework djangorestframework-simplejwt`
4. **Token Expiration**: Access tokens expire after 1 hour; use the refresh token to get a new access token

## Conclusion

This implementation provides a secure, scalable authentication system for the Student Attendance Management System. It uses industry-standard technologies (JWT, Django REST Framework) and follows Django best practices. The system is ready for production use after appropriate database configuration and testing.
