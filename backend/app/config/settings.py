import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

from app.models.config import (
    AppConfig, 
    EmbedderConfig, 
    VectorDBConfig,
    EmbedderType,
    VectorDBType,
    OpenAIEmbedderConfig,
    HuggingFaceEmbedderConfig,
    PineconeDBConfig,
    ChromaDBConfig,
    QdrantDBConfig
)


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # FastAPI settings
    app_name: str = Field(default="Document Embedding Platform", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # CORS settings
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:3001", env="CORS_ORIGINS")
    
    # Upload settings
    upload_dir: str = Field(default="/tmp/uploads", env="UPLOAD_DIR")
    max_file_size: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    
    # Document processing settings
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    
    # Config file path for runtime configuration
    config_file_path: str = Field(default="config/app_config.json", env="CONFIG_FILE_PATH")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def cors_origins_list(self) -> list:
        """Get CORS origins as a list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]


class ConfigManager:
    """Manages application configuration with runtime updates"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.config_file = Path(settings.config_file_path)
        self._app_config: Optional[AppConfig] = None
        
        # Ensure config directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
    
    async def load_config(self) -> Optional[AppConfig]:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                config_data = json.loads(self.config_file.read_text())
                self._app_config = AppConfig.model_validate(config_data)
                return self._app_config
        except Exception as e:
            print(f"Failed to load config: {e}")
        return None
    
    async def save_config(self, config: AppConfig) -> bool:
        """Save configuration to file"""
        try:
            config_data = config.model_dump()
            self.config_file.write_text(json.dumps(config_data, indent=2))
            self._app_config = config
            return True
        except Exception as e:
            print(f"Failed to save config: {e}")
            return False
    
    async def update_embedder_config(self, embedder_config: EmbedderConfig) -> bool:
        """Update embedder configuration"""
        try:
            if not self._app_config:
                # Create default config
                self._app_config = self._create_default_config()
            
            self._app_config.embedder = embedder_config
            return await self.save_config(self._app_config)
        except Exception as e:
            print(f"Failed to update embedder config: {e}")
            return False
    
    async def update_vector_db_config(self, vector_db_config: VectorDBConfig) -> bool:
        """Update vector database configuration"""
        try:
            if not self._app_config:
                # Create default config
                self._app_config = self._create_default_config()
            
            self._app_config.vector_db = vector_db_config
            return await self.save_config(self._app_config)
        except Exception as e:
            print(f"Failed to update vector DB config: {e}")
            return False
    
    def get_current_config(self) -> Optional[AppConfig]:
        """Get current application configuration"""
        return self._app_config
    
    def is_configured(self) -> bool:
        """Check if the application is properly configured"""
        return self._app_config is not None
    
    def _create_default_config(self) -> AppConfig:
        """Create a default configuration"""
        return AppConfig(
            embedder=EmbedderConfig(
                type=EmbedderType.HUGGINGFACE,
                huggingface=HuggingFaceEmbedderConfig()
            ),
            vector_db=VectorDBConfig(
                type=VectorDBType.CHROMADB,
                chromadb=ChromaDBConfig()
            ),
            max_file_size=self.settings.max_file_size,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap
        )


# Global settings instance
settings = Settings()

# Global config manager instance
config_manager = ConfigManager(settings) 