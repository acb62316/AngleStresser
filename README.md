# AngleStresser - Modern DDoS Panel and API

AngleStresser is a stress testing platform built with Python using the Flask framework. It uses an SQLite database and is designed to manage multiple attack servers through an easy-to-use web interface.

## Core Features

- Modern Interface: A clean and professional design that works on computers and mobile phones.
- Layer 7: Support for HTTP and node.js attack scripts.
- Layer 4: Support for UDP and TCP attacks with automated slot management.
- API System: Allows users to start attacks using a unique API key.
- Admin Panel: Tools for managing users, plans, and generating redeem codes.

## Installation Guide for Beginners

### 1. Requirements
- Python installed on your computer or server.
- Basic knowledge of how to run a Python script.

### 2. Getting the Files
Download the code or use git to clone the repository:
```bash
git clone https://github.com/acb62316/AngleStresser.git
cd AngleStresser
```

### 3. Installing Dependencies
Install the required Python libraries using the following command:
```bash
pip install flask flask-limiter paramiko werkzeug
```

### 4. Basic Configuration
Open the file named `sv.py` in a text editor to set up your servers:

Find this section on line 23 and replace the placeholder values with your server IP and root password:
```python
SERVER = {
    "SERVER_1": ["SERVER_IP", "SERVER_PW", "0"],
}
```

Change the secret key to a random string for security on line 18:
```python
app.config["SECRET_KEY"] = b"CHANGE_THIS_TO_A_LONG_RANDOM_STRING"
```

### 5. Starting the Panel
Run the following command to start the website:
```bash
python sv.py
```
The panel will be live on port 80. You can access it by typing your server's IP address or domain name into your web browser.

## Default Admin Credentials
- Username: admin
- Password: 1234

## API Information
To use the API, go to the API section of the panel to get your key. The format for requests is:
`http://yourdomain.com/api/attack?key=YOUR_KEY&host=1.1.1.1&port=80&time=60&method=udp`

## Disclaimer
This project is for educational and research purposes only. I am not responsible for any misuse of this software.
