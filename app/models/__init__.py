# Importa todos os modelos para que o Alembic os detecte 
# ao gerar as migrations automaticamente

from app.models.user import User
from app.models.activation_key import ActivationKey
from app.models.sheet import Sheet, SheetLine