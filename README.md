# Smart Attendance Management System - Backend

A Django-based REST API backend for managing student attendance in educational institutions.

## Features

- **Multi-User Authentication System**: Separate login and registration for Students, Teachers, and Management
- **JWT-based Authentication**: Secure stateless authentication using JSON Web Tokens
- **PostgreSQL Database**: Robust database for production use
- **RESTful API**: Clean API endpoints following REST principles
- **Comprehensive Testing**: Full test coverage for authentication system

## Tech Stack

- **Framework**: Django 5.2.8
- **Database**: PostgreSQL
- **API**: Django REST Framework 3.16.1
- **Authentication**: djangorestframework-simplejwt 5.5.1
- **Language**: Python 3.12+

## Installation

### Prerequisites

- Python 3.12 or higher
- PostgreSQL 12 or higher

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Rehan-Ur-Rehman-Sharif/FYP_Backend.git
   cd FYP_Backend
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure PostgreSQL**
   
   Create a PostgreSQL database:
   ```sql
   CREATE DATABASE school_db;
   CREATE USER dbuser WITH PASSWORD 'dbpass';
   GRANT ALL PRIVILEGES ON DATABASE school_db TO dbuser;
   ```

   Update `FYP_Backend/settings.py` with your database credentials if needed.

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

   The API will be available at `http://localhost:8000/`

## API Endpoints

### Authentication Endpoints

#### Student Registration
```
POST /api/auth/register/student/
```

**Request Body:**
```json
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

**Response:**
```json
{
    "message": "Student registered successfully",
    "student_id": 1,
    "email": "student@example.com",
    "student_name": "John Doe"
}
```

#### Student Login
```
POST /api/auth/login/student/
```

**Request Body:**
```json
{
    "email": "student@example.com",
    "password": "SecurePassword123!"
}
```

**Response:**
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

#### Teacher Registration
```
POST /api/auth/register/teacher/
```

**Request Body:**
```json
{
    "email": "teacher@example.com",
    "password": "SecurePassword123!",
    "password2": "SecurePassword123!",
    "teacher_name": "Jane Smith",
    "rfid": "RFID789012"
}
```

#### Teacher Login
```
POST /api/auth/login/teacher/
```

**Request Body:**
```json
{
    "email": "teacher@example.com",
    "password": "SecurePassword123!"
}
```

#### Management Registration
```
POST /api/auth/register/management/
```

**Request Body:**
```json
{
    "email": "admin@example.com",
    "password": "SecurePassword123!",
    "password2": "SecurePassword123!",
    "Management_name": "Admin User"
}
```

#### Management Login
```
POST /api/auth/login/management/
```

**Request Body:**
```json
{
    "email": "admin@example.com",
    "password": "SecurePassword123!"
}
```

### Using JWT Tokens

After logging in, you'll receive an access token and a refresh token. Use the access token in the Authorization header for authenticated requests:

```bash
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/protected-endpoint/
```

**Token Lifetimes:**
- Access Token: 1 hour
- Refresh Token: 7 days

## Running Tests

```bash
python manage.py test core
```

All tests use an in-memory SQLite database for speed and don't require PostgreSQL.

## Project Structure

```
FYP_Backend/
├── FYP_Backend/          # Project settings
│   ├── settings.py       # Django settings
│   └── urls.py           # Main URL configuration
├── core/                 # Main application
│   ├── models.py         # Database models
│   ├── views.py          # API views
│   ├── serializers.py    # DRF serializers
│   ├── urls.py           # App URL configuration
│   └── tests.py          # Test cases
├── manage.py             # Django management script
├── requirements.txt      # Python dependencies
└── IMPLEMENTATION.md     # Detailed implementation docs
```

## Models

### Student
- student_id (Primary Key)
- user (OneToOne with Django User)
- student_name
- email
- rfid
- overall_attendance
- year
- dept
- section

### Teacher
- teacher_id (Primary Key)
- user (OneToOne with Django User)
- teacher_name
- email
- rfid

### Management
- Management_id (Primary Key)
- user (OneToOne with Django User)
- Management_name
- email

### Course
- course_id (Primary Key)
- course_name

### Class
- classroom_id (Primary Key)
- scanner_id

### TaughtCourse
- course (ForeignKey)
- teacher (ForeignKey)
- classes_taken

### StudentCourse
- student (ForeignKey)
- course (ForeignKey)
- teacher (ForeignKey)
- classes_attended

## Security Features

- Password validation using Django's built-in validators
- Email uniqueness validation
- JWT token-based authentication
- User type separation (students can't login as teachers)
- CSRF protection enabled

## Documentation

For detailed implementation information, see [IMPLEMENTATION.md](IMPLEMENTATION.md)

## Development

### Adding New Endpoints

1. Add the view in `core/views.py`
2. Add the URL pattern in `core/urls.py`
3. Add tests in `core/tests.py`
4. Run tests to verify

### Database Migrations

After modifying models:
```bash
python manage.py makemigrations
python manage.py migrate
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This project is for educational purposes.

## Support

For issues or questions, please open an issue on GitHub.
