from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

class ExportStorage:
    
    @staticmethod
    def save(
        *,
        key: str,
        content: bytes
    ) -> str:
        
        return default_storage.save(
            key,
            ContentFile(content)
        )
        
    @staticmethod
    def exists(
        *,
        key: str,
    ) -> bool:
        
        return default_storage.exists(key)
    
    @staticmethod
    def delete(
        *,
        key: str,
    ) -> None:
        
        if default_storage.exists(key):
            default_storage.delete(key)
            
    @staticmethod
    def get_download_url(
        *,
        key: str,
    ) -> str:
        
        return default_storage.url(key)