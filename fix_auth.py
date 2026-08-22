import re
with open('../voting_managment_Front-end-/src/pages/AuthPage.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'const challenge = await authApi\.requestLoginOtp\(email\.trim\(\), password\);\s*setOtpChallengeId\(challenge\.challenge_id\);',
    'const session = await authApi.login(email.trim(), password);\n      loginWithSession(session, email);',
    content
)

content = content.replace('placeholder="123456"', 'placeholder={t("auth.enter_otp", "Enter 6-digit code")}')

with open('../voting_managment_Front-end-/src/pages/AuthPage.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
