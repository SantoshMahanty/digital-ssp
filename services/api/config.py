"""
Configuration management using environment variables
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database (MySQL)
    DATABASE_URL: str = "mysql+mysqlconnector://root:root@localhost:3306/gam360"
    
    # MySQL connection details (for direct connection if needed)
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root"
    MYSQL_DATABASE: str = "gam360"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    API_DEBUG: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
