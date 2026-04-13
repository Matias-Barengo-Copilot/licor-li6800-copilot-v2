"""
Constants and configuration for Program IQ.
"""

# Urban Arts brand colors
COLORS = {
    "primary": "#FF6B35",       # Urban orange
    "secondary": "#1A1A2E",     # Deep navy
    "accent": "#7C3AED",        # Creative purple
    "success": "#10B981",       # Green
    "warning": "#F59E0B",       # Amber
    "danger": "#EF4444",        # Red
    "background": "#0F0F1A",    # Dark background
    "surface": "#1E1E30",       # Card surface
    "surface_light": "#2A2A3E", # Lighter surface
    "text": "#F1F5F9",          # Light text
    "text_muted": "#94A3B8",    # Muted text
    "border": "#334155",        # Border color
}

# Plotly chart theme
CHART_THEME = {
    "plot_bgcolor": "#1E1E30",
    "paper_bgcolor": "#1E1E30",
    "font": {"color": "#F1F5F9", "family": "Inter, sans-serif"},
    "gridcolor": "#2A2A3E",
    "colorway": [
        "#FF6B35", "#7C3AED", "#10B981", "#F59E0B",
        "#3B82F6", "#EC4899", "#06B6D4", "#84CC16"
    ],
}

# Attendance status mapping
ATTENDANCE_MAP = {
    "p": "Present",
    "a": "Absent",
    "l": "Late",
    "e": "Excused",
    "afk": "Away (AFK)",
}

ATTENDANCE_COLORS = {
    "Present": "#10B981",
    "Absent": "#EF4444",
    "Late": "#F59E0B",
    "Excused": "#3B82F6",
    "Away (AFK)": "#8B5CF6",
}

# Risk thresholds
AT_RISK_THRESHOLDS = {
    "attendance_low": 70,       # % below this is at-risk
    "attendance_critical": 50,  # % below this is critical
    "missing_work_high": 50,    # % missing above this is at-risk
    "absences_high": 8,         # Raw absences above this is at-risk
    "late_arrivals_flag": 5,    # Late arrivals above this is flagged
}

# Synthetic student names (realistic NYC youth demographics)
SYNTHETIC_NAMES = [
    ("Jordan", "Martinez"), ("Aaliyah", "Johnson"), ("Marcus", "Chen"),
    ("Sofia", "Williams"), ("DeShawn", "Brown"), ("Priya", "Patel"),
    ("Jaylen", "Rivera"), ("Amara", "Thompson"), ("Elijah", "Kim"),
    ("Destiny", "Davis"), ("Carlos", "Rodriguez"), ("Zara", "Washington"),
    ("Isaiah", "Garcia"), ("Nadia", "Anderson"), ("Malik", "Jackson"),
    ("Yesenia", "Lopez"), ("Tre", "Harris"), ("Fatima", "Wilson"),
    ("Darius", "Lee"), ("Camille", "Taylor"), ("Xavier", "Thomas"),
    ("Brianna", "Moore"), ("Kevin", "Martinez"), ("Layla", "Jackson"),
    ("Tyrone", "White"), ("Valentina", "Hernandez"), ("Amir", "Clark"),
    ("Kiara", "Lewis"), ("Dominic", "Robinson"), ("Imani", "Walker"),
    ("Jalen", "Hall"), ("Alexis", "Young"), ("Rashid", "Allen"),
    ("Monique", "Scott"),
]

# Program definitions from yearly data
PROGRAM_DATA = [
    {"name": "2D Game Dev (Summer)", "type": "Summer", "enrolled_2024": 96, "completed_2024": 89, "retention": 0.93},
    {"name": "2D Game Dev (After-school)", "type": "After-school", "enrolled_2024": 99, "completed_2024": 68, "retention": 0.69},
    {"name": "3D Game Dev", "type": "After-school", "enrolled_2024": 90, "completed_2024": 74, "retention": 0.82},
    {"name": "Senior XP", "type": "Summer", "enrolled_2024": 22, "completed_2024": 18, "retention": 0.82},
    {"name": "Studio", "type": "After-school", "enrolled_2024": 29, "completed_2024": 28, "retention": 0.97},
    {"name": "Play Lab", "type": "After-school", "enrolled_2024": 8, "completed_2024": 7, "retention": 0.88},
    {"name": "Spring Break Lab", "type": "Special", "enrolled_2024": 51, "completed_2024": 37, "retention": 0.73},
    {"name": "Pop-Up Classes", "type": "Special", "enrolled_2024": 273, "completed_2024": 190, "retention": 0.70},
]
