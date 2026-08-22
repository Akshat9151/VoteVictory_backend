with open('app/core/config.py', 'r') as f:
    content = f.read()

if 'GOOGLE_CLIENT_ID' not in content:
    content = content.replace('class Settings(BaseSettings):', 'class Settings(BaseSettings):\n    GOOGLE_CLIENT_ID: str = ""\n')
    with open('app/core/config.py', 'w') as f:
        f.write(content)
