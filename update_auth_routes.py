with open('app/api/v1/endpoints/auth.py', 'r') as f:
    content = f.read()

if 'GoogleAuthRequest' not in content:
    content = content.replace('from app.schemas.auth import (', 'from app.schemas.auth import (\n    GoogleAuthRequest,')

if '@router.post("/google"' not in content:
    new_route = '''
@router.post("/google", response_model=APIResponse[TokenResponse])
async def google_auth(
    request: Request,
    data: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    token_response = await service.authenticate_google(request, data.credential)
    return APIResponse(
        success=True,
        message="Google authentication successful.",
        data=token_response
    )
'''
    content += new_route
    with open('app/api/v1/endpoints/auth.py', 'w') as f:
        f.write(content)
