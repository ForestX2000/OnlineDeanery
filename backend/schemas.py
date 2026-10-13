from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    email: str
    firstName: str
    lastName: str
    role: str

class LoginResponse(BaseModel):
    success: bool
    token: str
    user: UserResponse

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class MessageResponse(BaseModel):
    success: bool
    message: str