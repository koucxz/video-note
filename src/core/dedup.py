"""文件去重模块"""
import hashlib
from pathlib import Path
from typing import Tuple

class FileDeduplicator:
    """基于内容 hash 的文件去重"""
    
    def __init__(self, upload_dir: str):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def process_upload(self, file_content: bytes, filename: str) -> Tuple[str, Path, bool]:
        """
        处理文件上传
        返回: (file_hash, file_path, is_new)
        """
        file_hash = self._calculate_hash(file_content)
        ext = Path(filename).suffix
        file_path = self.upload_dir / f"{file_hash}{ext}"
        
        is_new = not file_path.exists()
        if is_new:
            file_path.write_bytes(file_content)
        
        return file_hash, file_path, is_new
    
    def _calculate_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()[:16]
    
    def file_exists(self, file_hash: str, ext: str) -> bool:
        """检查文件是否已存在"""
        file_path = self.upload_dir / f"{file_hash}{ext}"
        return file_path.exists()
