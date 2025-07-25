from database import Base, engine  # ajuste os imports conforme seu projeto
import models  # certifique-se de importar todos os modelos

Base.metadata.create_all(bind=engine)
print("✅ Banco de dados inicializado com sucesso.")
