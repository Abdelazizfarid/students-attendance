# Student Attendance Management System

A comprehensive desktop application for managing student attendance, built with Python and Tkinter.

## Features

- **Student Management**: Add, update, delete, and view student records
- **Center Management**: Manage different learning centers
- **Attendance Tracking**: Track daily attendance with barcode scanning
- **QR Code Generation**: Generate QR codes for students
- **Reporting**: Generate attendance reports with filtering options
- **Database Integration**: SQLite database for data persistence

## Requirements

- Python 3.x
- tkinter (usually comes with Python)
- sqlite3 (usually comes with Python)
- qrcode
- fpdf
- Pillow (PIL)
- requests

## Installation

1. Clone this repository
2. Install required dependencies:
   ```bash
   pip install qrcode fpdf Pillow requests
   ```
3. Run the application:
   ```bash
   python application.py
   ```

## Database Structure

The application uses SQLite database with the following tables:
- `students`: Student information including barcode
- `centers`: Learning center information
- `attendance`: Daily attendance records

## Usage

1. **Student Management**: Add new students with their details including barcode
2. **Attendance**: Scan student barcodes to mark attendance
3. **Reports**: View and filter attendance reports by date, center, or student type
4. **Centers**: Manage different learning centers

## Features Overview

- Multi-tab interface for different functions
- Real-time barcode validation
- Automatic attendance confirmation
- Exportable reports
- Database migration support

## Author

Created by: Shreif Farid
Contact: 01116788750
