from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from . import Base


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
    lat_lon: Mapped[str | None] = mapped_column(String(100), default=None)

    # Relacionamentos (1 para Muitos)
    equipamentos: Mapped[list[OcorrenciaEqTxt]] = relationship(
        back_populates="ocorrencia", cascade="all, delete-orphan"
    )
    funcionarios: Mapped[list[OcorrenciaFuncionarioTxt]] = relationship(
        back_populates="ocorrencia", cascade="all, delete-orphan"
    )


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
    ocorrencia: Mapped[OcorrenciaTxt] = relationship(back_populates="equipamentos")


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
    pda: Mapped[int | None] = mapped_column(SmallInteger, server_default="1", default=1)
    data_ocorrencia_capacity_funcionario: Mapped[datetime | None] = mapped_column(
        DateTime, default=None
    )
    id_estado: Mapped[int | None] = mapped_column(Integer, default=None)

    # Relacionamento Reverso (Muitos para 1)
    ocorrencia: Mapped[OcorrenciaTxt] = relationship(back_populates="funcionarios")


class ResponsavelPDA(str, Enum):
    SIM = "SIM"
    NAO = "NÃO"


class TelaOcorrencia(Base):
    __tablename__ = "tela_ocorrencias"

    ocorrencia: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    sla: Mapped[str | None] = mapped_column(String(50))
    reincidencia: Mapped[str | None] = mapped_column(String(10))

    tecnicos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    data_abertura: Mapped[datetime | None] = mapped_column(DateTime)
    data_promessa: Mapped[datetime | None] = mapped_column(DateTime)
    data_encerramento: Mapped[datetime | None] = mapped_column(DateTime)

    fluxo: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str | None] = mapped_column(String(50))
    origem: Mapped[str | None] = mapped_column(String(100))

    causa: Mapped[str | None] = mapped_column(String(100))
    sub_causa: Mapped[str | None] = mapped_column(String(100))

    afetacao: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    vip: Mapped[str | None] = mapped_column(String(10))
    cond_alto_valor: Mapped[str | None] = mapped_column(String(50))
    propenso_anatel: Mapped[str | None] = mapped_column(String(10))
    reclamado_anatel: Mapped[str | None] = mapped_column(String(10))

    equipamentos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    primarias: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    b2b_avancado: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    bd: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    contrato: Mapped[str | None] = mapped_column(String(50))
    escritorio: Mapped[str | None] = mapped_column(String(50))
    municipio: Mapped[str | None] = mapped_column(String(100))
    cnl: Mapped[str | None] = mapped_column(String(10))
    at: Mapped[str | None] = mapped_column(String(100))
    cabo: Mapped[str | None] = mapped_column(String(10))
    tecnologia: Mapped[str | None] = mapped_column(String(50))
    prioridade: Mapped[str | None] = mapped_column(String(50))

    usuario_criador: Mapped[str | None] = mapped_column(String(255))

    id_teste: Mapped[str | None] = mapped_column(String(50))
    status_teste: Mapped[str | None] = mapped_column(String(100))
    numero_or: Mapped[str | None] = mapped_column(String(50))

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    tecnicos_rel: Mapped[list[TelaTecnico]] = relationship(
        back_populates="ocorrencia_rel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    primarias_rel: Mapped[list[TelaPrimaria]] = relationship(
        back_populates="ocorrencia_rel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TelaTecnico(Base):
    __tablename__ = "tela_tecnicos"

    ocorrencia: Mapped[int] = mapped_column(
        ForeignKey(
            "tela_ocorrencias.ocorrencia",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    nome: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    re: Mapped[str | None] = mapped_column(String(20))

    contato: Mapped[str | None] = mapped_column(String(50))

    responsavel_pda: Mapped[ResponsavelPDA] = mapped_column(
        SQLEnum(
            ResponsavelPDA,
            name="responsavel_pda_enum",
            native_enum=False,
            length=3,
        ),
        nullable=False,
    )

    ocorrencia_rel: Mapped[TelaOcorrencia] = relationship(
        back_populates="tecnicos_rel",
    )


class TelaPrimaria(Base):
    __tablename__ = "tela_primarias"

    ocorrencia: Mapped[int] = mapped_column(
        ForeignKey(
            "tela_ocorrencias.ocorrencia",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    cod_primaria: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    ocorrencia_rel: Mapped[TelaOcorrencia] = relationship(
        back_populates="primarias_rel",
    )


class Primaria(Base):
    __tablename__ = "primarias"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    cod_primaria: Mapped[str | None] = mapped_column(
        String(16),
        unique=True,
    )

    municipio: Mapped[str | None] = mapped_column(String(30))

    at: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    ocorrencias: Mapped[list[OcorrenciaPrimaria]] = relationship(
        back_populates="primaria",
    )


class OcorrenciaPrimaria(Base):
    __tablename__ = "ocorrencia_primaria"

    cod_primaria: Mapped[str] = mapped_column(
        ForeignKey("primarias.cod_primaria"),
        primary_key=True,
    )

    id_ocorrencia: Mapped[int] = mapped_column(
        ForeignKey(
            "ocorrencias_txt.id_ocorrencia",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    primaria: Mapped[Primaria] = relationship(
        back_populates="ocorrencias",
    )
