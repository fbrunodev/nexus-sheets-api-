# Importa todos os modelos para que o Alembic os detecte 
# ao gerar as migrations automaticamente

from app.models.user import User
from app.models.activation_key import ActivationKey
from app.models.platform import Platform
from app.models.sheet import Sheet, SheetLine
from app.models.cost import CostType, Cost
from app.models.push_subscription import PushSubscription