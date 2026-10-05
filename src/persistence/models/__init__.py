from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from .entities import (
    OcorrenciaEqTxt as OcorrenciaEq,
)
from .entities import (
    OcorrenciaFuncionarioTxt as OcorrenciaTecnico,
)
from .entities import (
    OcorrenciaPrimaria,
    Primaria,
    TelaOcorrencia,
    TelaPrimaria,
    TelaTecnico,
)
from .entities import (
    OcorrenciaTxt as Ocorrencias,
)
from .feedback import Feedback
from .user import User

__all__ = [
    "Base",
    "Feedback",
    "OcorrenciaEq",
    "OcorrenciaPrimaria",
    "OcorrenciaTecnico",
    "Ocorrencias",
    "Primaria",
    "TelaOcorrencia",
    "TelaPrimaria",
    "TelaTecnico",
    "User"
]
