import os
from typing import Optional
from minio import Minio
from minio.error import S3Error

class FileStorage:
    def upload(self, local_path: str, remote_path: str) -> str:
        raise NotImplementedError
    def download(self, remote_path: str, local_path: str) -> None:
        raise NotImplementedError
    def delete(self, remote_path: str) -> None:
        raise NotImplementedError

class LocalFileStorage(FileStorage):
    def upload(self, local_path: str, remote_path: str) -> str:
        os.makedirs(os.path.dirname(remote_path), exist_ok=True)
        os.rename(local_path, remote_path)
        return remote_path
    def download(self, remote_path: str, local_path: str) -> None:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(remote_path, "rb") as src, open(local_path, "wb") as dst:
            dst.write(src.read())
    def delete(self, remote_path: str) -> None:
        os.remove(remote_path)

class MinioFileStorage(FileStorage):
    def __init__(self, bucket: str, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self.bucket = bucket
        # Crée le bucket s'il n'existe pas
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)
    def upload(self, local_path: str, remote_path: str) -> str:
        self.client.fput_object(self.bucket, remote_path, local_path)
        return remote_path
    def download(self, remote_path: str, local_path: str) -> None:
        self.client.fget_object(self.bucket, remote_path, local_path)
    def delete(self, remote_path: str) -> None:
        self.client.remove_object(self.bucket, remote_path)

def get_file_storage() -> FileStorage:
    """
    Retourne l'instance du backend de stockage approprié selon la config/env.
    Utilise la variable d'environnement FILE_STORAGE_BACKEND ('local' ou 'minio').
    """
    backend = os.environ.get('FILE_STORAGE_BACKEND', 'local').lower()
    if backend == 'minio':
        bucket = os.environ.get('MINIO_BUCKET', 'dataflow')
        endpoint = os.environ.get('MINIO_ENDPOINT', 'localhost:9000')
        access_key = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
        secret_key = os.environ.get('MINIO_SECRET_KEY', 'minioadmin123')
        secure = bool(int(os.environ.get('MINIO_SECURE', '0')))
        return MinioFileStorage(bucket, endpoint, access_key, secret_key, secure)
    return LocalFileStorage() 