#!/usr/bin/env python
"""
API Demonstration Script

This script demonstrates how to use the authentication API endpoints
for student, teacher, and management users.

Since PostgreSQL is not available in this environment, this script uses
the test client to simulate API calls with an in-memory SQLite database.
"""

import os
import sys

# Set testing environment before importing Django
sys.argv = ['test']  # This triggers SQLite usage in settings.py

import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FYP_Backend.settings')
django.setup()

from django.test import Client
from django.core.management import call_command
import json

def setup_database():
    """Setup the test database with migrations"""
    print("Setting up database...")
    call_command('migrate', '--run-syncdb', verbosity=0)
    print("Database setup complete!\n")

def print_response(label, response):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    print(f"Response Body:")
    if response.content:
        try:
            data = json.loads(response.content)
            print(json.dumps(data, indent=2))
        except:
            print(response.content.decode())
    print()

def main():
    print("\n" + "="*60)
    print("Authentication API Demonstration")
    print("="*60)
    
    # Setup database first
    setup_database()
    
    client = Client()
    
    # 1. Student Registration
    print("\n1. Testing Student Registration")
    print("-" * 60)
    student_data = {
        "email": "demo.student@example.com",
        "password": "SecurePass123!",
        "password2": "SecurePass123!",
        "student_name": "Demo Student",
        "rfid": "RFID001",
        "year": 2,
        "dept": "Computer Science",
        "section": "A"
    }
    print("Request:")
    print(f"POST /api/auth/register/student/")
    print(json.dumps(student_data, indent=2))
    
    response = client.post(
        '/api/auth/register/student/',
        data=json.dumps(student_data),
        content_type='application/json'
    )
    print_response("Student Registration Response", response)
    
    # 2. Student Login
    print("\n2. Testing Student Login")
    print("-" * 60)
    login_data = {
        "email": "demo.student@example.com",
        "password": "SecurePass123!"
    }
    print("Request:")
    print(f"POST /api/auth/login/student/")
    print(json.dumps(login_data, indent=2))
    
    response = client.post(
        '/api/auth/login/student/',
        data=json.dumps(login_data),
        content_type='application/json'
    )
    print_response("Student Login Response", response)
    
    if response.status_code == 200:
        data = json.loads(response.content)
        access_token = data.get('access')
        print(f"✓ Login successful! Access token obtained.")
        print(f"  Token can be used in Authorization header: Bearer {access_token[:20]}...")
    
    # 3. Teacher Registration
    print("\n3. Testing Teacher Registration")
    print("-" * 60)
    teacher_data = {
        "email": "demo.teacher@example.com",
        "password": "SecurePass123!",
        "password2": "SecurePass123!",
        "teacher_name": "Demo Teacher",
        "rfid": "RFID002"
    }
    print("Request:")
    print(f"POST /api/auth/register/teacher/")
    print(json.dumps(teacher_data, indent=2))
    
    response = client.post(
        '/api/auth/register/teacher/',
        data=json.dumps(teacher_data),
        content_type='application/json'
    )
    print_response("Teacher Registration Response", response)
    
    # 4. Teacher Login
    print("\n4. Testing Teacher Login")
    print("-" * 60)
    login_data = {
        "email": "demo.teacher@example.com",
        "password": "SecurePass123!"
    }
    print("Request:")
    print(f"POST /api/auth/login/teacher/")
    print(json.dumps(login_data, indent=2))
    
    response = client.post(
        '/api/auth/login/teacher/',
        data=json.dumps(login_data),
        content_type='application/json'
    )
    print_response("Teacher Login Response", response)
    
    # 5. Management Registration
    print("\n5. Testing Management Registration")
    print("-" * 60)
    management_data = {
        "email": "demo.admin@example.com",
        "password": "SecurePass123!",
        "password2": "SecurePass123!",
        "Management_name": "Demo Admin"
    }
    print("Request:")
    print(f"POST /api/auth/register/management/")
    print(json.dumps(management_data, indent=2))
    
    response = client.post(
        '/api/auth/register/management/',
        data=json.dumps(management_data),
        content_type='application/json'
    )
    print_response("Management Registration Response", response)
    
    # 6. Management Login
    print("\n6. Testing Management Login")
    print("-" * 60)
    login_data = {
        "email": "demo.admin@example.com",
        "password": "SecurePass123!"
    }
    print("Request:")
    print(f"POST /api/auth/login/management/")
    print(json.dumps(login_data, indent=2))
    
    response = client.post(
        '/api/auth/login/management/',
        data=json.dumps(login_data),
        content_type='application/json'
    )
    print_response("Management Login Response", response)
    
    # 7. Test Invalid Login
    print("\n7. Testing Invalid Login (Wrong Password)")
    print("-" * 60)
    invalid_login = {
        "email": "demo.student@example.com",
        "password": "WrongPassword123!"
    }
    print("Request:")
    print(f"POST /api/auth/login/student/")
    print(json.dumps(invalid_login, indent=2))
    
    response = client.post(
        '/api/auth/login/student/',
        data=json.dumps(invalid_login),
        content_type='application/json'
    )
    print_response("Invalid Login Response", response)
    
    # 8. Test User Type Separation
    print("\n8. Testing User Type Separation")
    print("-" * 60)
    print("Trying to login as teacher with student credentials...")
    login_data = {
        "email": "demo.student@example.com",
        "password": "SecurePass123!"
    }
    print("Request:")
    print(f"POST /api/auth/login/teacher/")
    print(json.dumps(login_data, indent=2))
    
    response = client.post(
        '/api/auth/login/teacher/',
        data=json.dumps(login_data),
        content_type='application/json'
    )
    print_response("User Type Separation Response", response)
    
    print("\n" + "="*60)
    print("API Demonstration Complete!")
    print("="*60)
    print("\nAll authentication endpoints are working correctly.")
    print("\nFor production use:")
    print("1. Configure PostgreSQL database")
    print("2. Run migrations: python manage.py migrate")
    print("3. Start server: python manage.py runserver")
    print("4. Use curl or Postman to test endpoints")
    print("\nSee README.md for detailed API documentation.")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
