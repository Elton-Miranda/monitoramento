from .logar_usuario import logar_usuario, obter_usuario_por_email
from .solicitar_acesso import cadastrar_novo_usuario
from .trocar_senha import atualizar_senha

__all__ = [
    "atualizar_senha",
    "cadastrar_novo_usuario",
    "logar_usuario",
    "obter_usuario_por_email",
]

def valida_senha(senha: str) -> str:
    senha = senha.strip()

    if len(senha) < 6:
        raise ValueError("A senha deve ter no mínimo 6 caracteres")

    if senha is None or senha == "":
        raise ValueError("A senha não pode ser vazia")

    return senha
