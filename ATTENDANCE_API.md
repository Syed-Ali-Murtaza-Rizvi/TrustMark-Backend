# Attendance Session System API Documentation

## Overview

The attendance system implements a 2-factor authentication (2FA) approach for marking student attendance:
- **RFID Scan**: Students scan their RFID card when entering class
- **QR Code Scan**: Students scan a QR code displayed by the teacher

**Important**: Attendance is only marked as present when BOTH RFID and QR code are scanned during an active session.

## Models

### AttendanceSession
Represents an attendance session started by a teacher for a specific course, section, and year.

**Fields:**
- `id`: Unique session identifier
- `teacher`: Foreign key to Teacher
- `course`: Foreign key to Course
- `section`: Section (e.g., "A", "B", "C")
- `year`: Academic year (e.g., 1, 2, 3, 4)
- `status`: Session status (`active` or `stopped`)
- `qr_code_token`: Unique token for QR code validation
- `attendance_type`: Attendance type (`regular` or `compensatory`)
- `program`: Optional program tag used by the frontend
- `latitude`: Optional session latitude for geo-fencing
- `longitude`: Optional session longitude for geo-fencing
- `radius_meters`: Allowed QR scan radius (meters) when latitude/longitude are set
- `started_at`: Timestamp when session started
- `stopped_at`: Timestamp when session stopped (null if still active)

### AttendanceRecord
Tracks individual student attendance within a session.

**Fields:**
- `session`: Foreign key to AttendanceSession
- `student`: Foreign key to Student
- `rfid_scanned`: Boolean indicating if RFID was scanned
- `rfid_scanned_at`: Timestamp of RFID scan
- `qr_scanned`: Boolean indicating if QR code was scanned
- `qr_scanned_at`: Timestamp of QR scan
- `is_present`: Boolean indicating if student is marked present (true only when both RFID and QR are scanned)
- `marked_present_at`: Timestamp when student was marked present

## API Endpoints

### 1. Start Attendance Session

**Endpoint:** `POST /api/attendance-sessions/`

**Authentication:** Required (Teacher)

**Request Body:**
```json
{
  "teacher": 1,
  "course": 1,
  "section": "A",
  "year": 1,
  "slot_count": 1,
  "attendance_type": "regular",
  "program": "CS",
  "latitude": 24.93553388673033,
  "longitude": 67.0442592957783,
  "radius_meters": 50
}
```

**Response (201 Created):**
```json
{
  "message": "Attendance session started successfully",
  "session": {
    "id": 1,
    "teacher": 1,
    "course": 1,
    "section": "A",
    "year": 1,
    "status": "active",
    "qr_code_token": "K2U-GcR-ersm2l7RA-N2TxVOCNGhvAdp9DQT8k-mkzM",
    "started_at": "2025-12-03T23:52:05.123456Z",
    "stopped_at": null,
    "teacher_name": "John Doe",
    "course_name": "Data Structures"
  }
}
```

### 2. Stop Attendance Session

**Endpoint:** `POST /api/attendance-sessions/{session_id}/stop/`

**Authentication:** Required (Teacher)

**Response (200 OK):**
```json
{
  "message": "Attendance session stopped successfully",
  "session": {
    "id": 1,
    "status": "stopped",
    "stopped_at": "2025-12-03T23:55:00.123456Z",
    ...
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "Session is already stopped"
}
```

### 3. List Attendance Sessions

**Endpoint:** `GET /api/attendance-sessions/`

**Authentication:** Required

**Query Parameters:**
- `teacher`: Filter by teacher ID
- `course`: Filter by course ID
- `status`: Filter by status (`active` or `stopped`)
- `section`: Filter by section
- `year`: Filter by year

**Example:** `GET /api/attendance-sessions/?teacher=1&status=active`

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "teacher": 1,
    "course": 1,
    "section": "A",
    "year": 1,
    "status": "active",
    "qr_code_token": "...",
    "started_at": "2025-12-03T23:52:05.123456Z",
    "stopped_at": null,
    "teacher_name": "John Doe",
    "course_name": "Data Structures"
  }
]
```

### 4. Get QR Code for Session

**Endpoint:** `GET /api/attendance-sessions/{session_id}/qr/`

**Authentication:** Required (Teacher)

**Response (200 OK):**
```json
{
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "qr_token": "K2U-GcR-ersm2l7RA-N2TxVOCNGhvAdp9DQT8k-mkzM",
  "session_id": 1
}
```

**Note:** The `qr_code` field contains a base64-encoded PNG image that can be displayed directly in HTML:
```html
<img src="data:image/png;base64,..." alt="QR Code">
```

**Error Response (400 Bad Request):**
```json
{
  "error": "Session is not active"
}
```

### 5. Get Attendance Statistics

**Endpoint:** `GET /api/attendance-sessions/{session_id}/attendance/`

**Authentication:** Required (Teacher)

**Response (200 OK):**
```json
{
  "records": [
    {
      "id": 1,
      "session": 1,
      "student": 1,
      "rfid_scanned": true,
      "rfid_scanned_at": "2025-12-03T23:52:10.123456Z",
      "qr_scanned": true,
      "qr_scanned_at": "2025-12-03T23:52:15.123456Z",
      "is_present": true,
      "marked_present_at": "2025-12-03T23:52:15.123456Z",
      "student_name": "Jane Smith",
      "session_details": {
        "course": "Data Structures",
        "teacher": "John Doe",
        "section": "A",
        "year": 1
      }
    }
  ],
  "statistics": {
    "total_students": 3,
    "present": 1,
    "absent": 2,
    "rfid_only": 1,
    "qr_only": 1
  }
}

### 6. QR Scan (Student)

**Endpoint:** `POST /api/attendance/qr-scan/`

**Authentication:** Required

**Request Body:**
```json
{
  "qr_token": "<token from /attendance-sessions/{id}/qr/>",
  "student_id": 1,
  "latitude": 24.93553388673033,
  "longitude": 67.0442592957783
}
```

**Geo-fencing rule:** If the session was started with `latitude` and `longitude`, the QR scan must include `latitude/longitude` and must be within `radius_meters` of the session location. Otherwise the server returns `400`.
```

### 6. RFID Scan

**Endpoint:** `POST /api/attendance/rfid-scan/`

**Authentication:** Not required (for hardware integration)

**Request Body:**
```json
{
  "rfid": "STUDENT_RFID_001",
  "session_id": 1
}
```

**Response (200 OK):**
```json
{
  "message": "RFID scanned successfully",
  "student": "Jane Smith",
  "rfid_scanned": true,
  "qr_scanned": false,
  "is_present": false,
  "needs_qr": true
}
```

**After Both Scans:**
```json
{
  "message": "RFID scanned successfully",
  "student": "Jane Smith",
  "rfid_scanned": true,
  "qr_scanned": true,
  "is_present": true,
  "needs_qr": false
}
```

**Error Responses:**

*Student Not Found (404):*
```json
{
  "error": "Student not found with this RFID"
}
```

*Session Not Active (400):*
```json
{
  "error": "Attendance session is not active"
}
```

*Wrong Section/Year (400):*
```json
{
  "error": "Student is not enrolled in this section/year"
}
```

### 7. QR Code Scan

**Endpoint:** `POST /api/attendance/qr-scan/`

**Authentication:** Required (Student)

**Request Body:**
```json
{
  "qr_token": "K2U-GcR-ersm2l7RA-N2TxVOCNGhvAdp9DQT8k-mkzM",
  "student_id": 1
}
```

**Response (200 OK):**
```json
{
  "message": "QR code scanned successfully",
  "student": "Jane Smith",
  "rfid_scanned": true,
  "qr_scanned": true,
  "is_present": true,
  "needs_rfid": false
}
```

**Error Responses:**

*Invalid QR Token (404):*
```json
{
  "error": "Invalid QR code or session not found"
}
```

*Session Not Active (400):*
```json
{
  "error": "Attendance session is not active"
}
```

## Usage Flow

### Teacher Workflow

1. **Login** as teacher
2. **Start a session** for a specific course, section, and year
3. **Display QR code** on screen (obtained from `/attendance-sessions/{id}/qr/`)
4. **Monitor attendance** in real-time via `/attendance-sessions/{id}/attendance/`
5. **Stop the session** when class ends

### Student Workflow

1. **Enter classroom** and scan RFID at the door
2. **Scan QR code** displayed by teacher
3. System marks attendance as present after both scans

### Hardware Integration

The RFID scanner should make a POST request to `/api/attendance/rfid-scan/` with the scanned RFID and the active session ID.

## Attendance Rules

| RFID Scanned | QR Scanned | Is Present | StudentCourse Updated |
|-------------|------------|------------|----------------------|
| ✅ Yes      | ✅ Yes     | ✅ Yes     | ✅ Yes               |
| ✅ Yes      | ❌ No      | ❌ No      | ❌ No                |
| ❌ No       | ✅ Yes     | ❌ No      | ❌ No                |
| ❌ No       | ❌ No      | ❌ No      | ❌ No                |

## Important Notes

1. **Session Must Be Active**: All scans are rejected if the session is not in `active` status
2. **Section/Year Validation**: Students can only mark attendance for sessions matching their section and year
3. **Order Doesn't Matter**: Students can scan RFID first then QR, or QR first then RFID
4. **Unique QR Token**: Each session gets a unique QR code token for security
5. **Attendance Update**: When both scans are complete, the StudentCourse record is automatically updated with the session date

## Example: Complete Flow

```bash
# 1. Teacher starts session
POST /api/attendance-sessions/
{
  "teacher": 1,
  "course": 1,
  "section": "A",
  "year": 1
}

# Response includes session_id and qr_code_token

# 2. Teacher gets QR code to display
GET /api/attendance-sessions/1/qr/

# 3. Student scans RFID at door (hardware)
POST /api/attendance/rfid-scan/
{
  "rfid": "STUDENT_001",
  "session_id": 1
}

# 4. Student scans QR code (mobile app)
POST /api/attendance/qr-scan/
{
  "qr_token": "...",
  "student_id": 1
}

# 5. Teacher checks attendance
GET /api/attendance-sessions/1/attendance/

# 6. Teacher stops session when class ends
POST /api/attendance-sessions/1/stop/
```

## Testing

Run automated tests:
```bash
python manage.py test core.tests.AttendanceSessionTestCase
python manage.py test core.tests.RFIDScanTestCase
python manage.py test core.tests.QRScanTestCase
python manage.py test core.tests.TwoFactorAttendanceTestCase
```

All tests verify:
- Session creation and management
- QR code generation
- RFID scanning
- QR code scanning
- 2FA attendance marking
- Session state validation
- Error handling
