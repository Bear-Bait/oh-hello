import fileinput
import sys
import re
import shutil

def create_fixed_timestamp_function():
    """Create function definition for a fixed timestamp function"""
    return '''
# Custom function to create timestamps in Eastern Time
def eastern_now():
    """Return time adjusted to Eastern Time Zone (UTC-4)"""
    # Simple offset method that doesn't require pytz
    return datetime.utcnow() - timedelta(hours=4)
'''

def update_timestamp_defaults(line):
    """Update model timestamp defaults"""
    if "default=datetime.utcnow" in line:
        return line.replace("default=datetime.utcnow", "default=eastern_now")
    return line

def update_direct_calls(line):
    """Update direct calls to datetime.utcnow()"""
    return line.replace("datetime.utcnow()", "eastern_now()")

def update_js_timestamp_display(line):
    """Update JavaScript timestamp display"""
    if "const timestamp = new Date(data.timestamp).toLocaleTimeString();" in line:
        return line.replace(
            "const timestamp = new Date(data.timestamp).toLocaleTimeString();", 
            "const timestamp = new Date(data.timestamp).toLocaleString();"
        )
    return line

# Main file to modify
filename = "forest-friends-chat.py"

# First make a backup
shutil.copy2(filename, f"{filename}.bak")
print(f"Created backup: {filename}.bak")

# First ensure timedelta is imported
with open(filename, 'r') as f:
    content = f.read()

if "from datetime import datetime, timedelta" not in content:
    # Replace datetime import with one that includes timedelta
    content = content.replace(
        "from datetime import datetime", 
        "from datetime import datetime, timedelta"
    )
    
    # Add the eastern_now function after imports
    import_section_end = content.find("app = Flask(__name__)")
    if import_section_end > 0:
        content = content[:import_section_end] + create_fixed_timestamp_function() + content[import_section_end:]
        
    # Write the updated content
    with open(filename, 'w') as f:
        f.write(content)
        
# Now update all references to datetime.utcnow()
modified_lines = 0
for line in fileinput.input(filename, inplace=True):
    original_line = line
    
    # Apply the transformations
    line = update_timestamp_defaults(line)
    line = update_direct_calls(line)
    line = update_js_timestamp_display(line)
    
    # Write the line back
    sys.stdout.write(line)
    
    # Count modified lines
    if line != original_line:
        modified_lines += 1

print(f"Modified {modified_lines} lines in {filename}")
print("Fixes applied successfully!")
