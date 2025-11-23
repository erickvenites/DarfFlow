from io import BytesIO
import io
import os
import zipfile

# Essa função recebe uma lista de arquivos XML para compactar
def zip_files(file_paths):
    """Compacta arquivos em um file ZIP e retorna como um objeto de bytes."""
    zip_memory = io.BytesIO()
    with zipfile.ZipFile(zip_memory, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in file_paths:
            zip_file.write(file_path, os.path.basename(file_path))
    zip_memory.seek(0)  # Volta ao início do objeto BytesIO
    return zip_memory