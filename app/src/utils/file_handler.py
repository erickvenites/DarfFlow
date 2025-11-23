import os

# Verifica se a extensão da spreadsheet enviada tem xlsx
def allowed_file_xlsx(filename):
    ALLOWED_EXTENSIONS = {'xlsx'}  # Defina as extensões permitidas
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#Função responsavel em percorrer um diretorio e retorna todos os itens dentro dele
def list_files(directory):
    files = []
    for root, dirs, file_list in os.walk(directory):
        for file in file_list:
            files.append(os.path.join(root, file))
    return files


# Verifica se a extensão da spreadsheet enviada tem xlsx
def allowed_file_zip(filename):
    ALLOWED_EXTENSIONS = {'zip'}  # Defina as extensões permitidas
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

