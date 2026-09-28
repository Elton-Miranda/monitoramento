from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# 1. Classe Base Declarativa
class Base(DeclarativeBase):
    pass


# 2. Tabela Principal (Pai): ocorrencias_txt
class OcorrenciaTxt(Base):
    __tablename__ = "ocorrencias_txt"

    # Chave Primária
    id_ocorrencia: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Campos Obrigatórios (NOT NULL)
    cnl: Mapped[str] = mapped_column(String(10), nullable=False)
    at: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    contratada: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    cabo: Mapped[str] = mapped_column(String(10), nullable=False)
    data_ocorrencia: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )
    afetacao: Mapped[int] = mapped_column(
        Integer, server_default="0", default=0, nullable=False
    )

    # Campos Opcionais (Nullable)
    municipio: Mapped[str | None] = mapped_column(String(100), default=None, index=True)
    id_suspeita: Mapped[int | None] = mapped_column(Integer, default=None)
    usuario: Mapped[str | None] = mapped_column(String(100), default=None)
    sobrenome: Mapped[str | None] = mapped_column(String(100), default=None)
    falha: Mapped[str | None] = mapped_column(String(100), default=None)
    causa: Mapped[str | None] = mapped_column(String(100), default=None)
    id_teste: Mapped[int | None] = mapped_column(Integer, default=None)
    data_ocorrencia_promessa: Mapped[datetime | None] = mapped_column(
        DateTime, default=None
    )
    data_ocorrencia_final: Mapped[datetime | None] = mapped_column(
        DateTime, default=None
    )
    bd: Mapped[int | None] = mapped_column(Integer, default=None)
    primaria: Mapped[int | None] = mapped_column(Integer, default=None)
    equipamento: Mapped[int | None] = mapped_column(Integer, default=None)
    iptv: Mapped[int | None] = mapped_column(Integer, default=None)
    cliente_v: Mapped[int | None] = mapped_column(Integer, default=None)
    cliente_vip: Mapped[int | None] = mapped_column(Integer, default=None)
    fluxo: Mapped[str | None] = mapped_column(String(50), default=None)
    nome_criacao: Mapped[str | None] = mapped_column(String(100), default=None)
    sobrenome_criacao: Mapped[str | None] = mapped_column(String(100), default=None)
    ocorrencia_teste_status: Mapped[str | None] = mapped_column(
        String(50), default=None
    )
    ordem_de_rede: Mapped[str | None] = mapped_column(String(50), default=None)
    ata: Mapped[int | None] = mapped_column(Integer, default=None)
    contrato: Mapped[str | None] = mapped_column(String(50), default=None)
    logradouro: Mapped[str | None] = mapped_column(Text, default=None)
    b2b_avancado: Mapped[int | None] = mapped_column(Integer, default=None)
    regional: Mapped[str | None] = mapped_column(String(50), default=None)
    hunter: Mapped[int | None] = mapped_column(Integer, default=None)
    influenciador: Mapped[int | None] = mapped_column(Integer, default=None)
    flag_anatel: Mapped[int | None] = mapped_column(Integer, default=None)
    perfil_reclamador_anatel: Mapped[int | None] = mapped_column(Integer, default=None)
    reincidencia: Mapped[int] = mapped_column(Integer, server_default="0", default=0)
    area: Mapped[str | None] = mapped_column(String(10), default=None)

    # Relacionamentos (1 para Muitos)
    equipamentos: Mapped[list["OcorrenciaEqTxt"]] = relationship(
        back_populates="ocorrencia", cascade="all, delete-orphan"
    )
    funcionarios: Mapped[list["OcorrenciaFuncionarioTxt"]] = relationship(
        back_populates="ocorrencia", cascade="all, delete-orphan"
    )


# 3. Tabela Relacionada: ocorrencias_eq_txt
class OcorrenciaEqTxt(Base):
    __tablename__ = "ocorrencias_eq_txt"

    # Chave Primária
    id_ocorrencia_eq: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Chave Estrangeira
    id_ocorrencia: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ocorrencias_txt.id_ocorrencia", ondelete="CASCADE"),
        nullable=False,
    )

    # Campos Obrigatórios (NOT NULL)
    cabo: Mapped[str] = mapped_column(String(10), nullable=False)
    primaria: Mapped[int] = mapped_column(Integer, nullable=False)
    data_ocorrencia_eq: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Campos Opcionais (Nullable)
    lateral: Mapped[str | None] = mapped_column(String(10), default=None)
    equipamento: Mapped[str | None] = mapped_column(String(100), default=None)
    status: Mapped[str | None] = mapped_column(String(20), default=None, index=True)
    data_ocorrencia_eq_final: Mapped[datetime | None] = mapped_column(
        DateTime, default=None
    )
    afetacao: Mapped[int] = mapped_column(Integer, server_default="0", default=0)
    iptv: Mapped[int | None] = mapped_column(Integer, default=None)
    cliente_v: Mapped[int | None] = mapped_column(Integer, default=None)
    cliente_vip: Mapped[int | None] = mapped_column(Integer, default=None)
    nome: Mapped[str | None] = mapped_column(String(100), default=None)
    sobrenome: Mapped[str | None] = mapped_column(String(100), default=None)
    id_ocorrencia_eq_de: Mapped[int | None] = mapped_column(Integer, default=None)

    # Relacionamento Reverso (Muitos para 1)
    ocorrencia: Mapped["OcorrenciaTxt"] = relationship(back_populates="equipamentos")


# 4. Tabela Relacionada (Chave Composta): ocorrencias_funcionario_txt
class OcorrenciaFuncionarioTxt(Base):
    __tablename__ = "ocorrencias_funcionario_txt"

    # Chaves Primárias Compostas (id_ocorrencia também é FK)
    id_ocorrencia: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ocorrencias_txt.id_ocorrencia", ondelete="CASCADE"),
        primary_key=True,
    )
    funcionario: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)

    # Campos Opcionais
    re: Mapped[str | None] = mapped_column(String(20), default=None, index=True)
    contato: Mapped[str | None] = mapped_column(String(50), default=None)
    usuario_sigma: Mapped[str | None] = mapped_column(String(100), default=None)
    sobrenome_usuario_sigma: Mapped[str | None] = mapped_column(
        String(100), default=None
    )
    pda: Mapped[int | None] = mapped_column(
        SmallInteger, server_default="1", default=1
    )  # tinyint(4) mapeia bem para SmallInteger
    data_ocorrencia_capacity_funcionario: Mapped[datetime | None] = mapped_column(
        DateTime, default=None
    )
    id_estado: Mapped[int | None] = mapped_column(Integer, default=None)

    # Relacionamento Reverso (Muitos para 1)
    ocorrencia: Mapped["OcorrenciaTxt"] = relationship(back_populates="funcionarios")
