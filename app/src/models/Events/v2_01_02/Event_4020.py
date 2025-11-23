import datetime
import pandas as pd
from src.utils.XmlModel import XmlModel
from src.config.logging_config import logger
from typing import List, Dict, Optional, Union


class Evento4020(XmlModel):
    """
    Classe responsável por processar e gerar eventos 4020 no formato XML a partir de uma spreadsheet.
    
    Attributes:
        nrInsc (str): Número de inscrição do contribuinte.
        nrInscEstab (str): Número de inscrição do estabelecimento.
        indRetif (str): Indicador de retificação. Valor padrão: '1'.
        tpAmb (str): Tipo de ambiente. Valor padrão: '1'.
        procEmi (str): Processo emissor. Valor padrão: '2'.
        verProc (str): Versão do processo emissor. Valor padrão: 'REINF.Web'.
        tpInsc (str): Tipo de inscrição do contribuinte. Valor padrão: '1'.
        tpInscEstab (str): Tipo de inscrição do estabelecimento. Valor padrão: '1'.
        sequencial (int): Contador sequencial para geração de IDs.
    """

    def __init__(self, file_path: str, nrInsc: str, nrInscEstab: str, **kwargs):
        """
        Inicializa a classe Evento4020 com os parâmetros fornecidos.

        Args:
            file_path (str): Caminho do file Excel contendo os dados dos eventos.
            nrInsc (str): Número de inscrição do contribuinte.
            nrInscEstab (str): Número de inscrição do estabelecimento.
            **kwargs: Parâmetros opcionais para configuração.
        """
        super().__init__(file_path, Evento4020)
        self.nrInsc: str = nrInsc
        self.nrInscEstab: str = nrInscEstab
        self.indRetif: str = kwargs.get("indRetif", "1")
        self.tpAmb: str = kwargs.get("tpAmb", "1")
        self.procEmi: str = kwargs.get("procEmi", "2")
        self.verProc: str = kwargs.get("verProc", "REINF.Web")
        self.tpInsc: str = kwargs.get("tpInsc", "1")
        self.tpInscEstab: str = kwargs.get("tpInscEstab", "1")
        self.sequencial: int = 1

    def validate_row(self, row: pd.Series, row_index: int) -> None:
        """
        Valida os campos obrigatórios de uma linha da spreadsheet.

        Args:
            row (pd.Series): Linha da spreadsheet.
            row_index (int): Índice da linha.

        Raises:
            ValueError: Se algum campo obrigatório estiver vazio.
        """
        required_fields: List[str] = [
            "Recolhedor",
            "Natureza de Rendimento",
            "Período Apuração",
            "Base de Cálculo",
            "Valor Receita",
        ]
        for field in required_fields:
            if pd.isna(row.get(field)) or row.get(field) == "":
                raise ValueError(f"Campo '{field}' vazio na linha {row_index + 1}.")

    def prepare_event(self, row: pd.Series, row_index: int) -> Dict[str, Union[str, None]]:
        """
        Prepara os dados do event com base em uma linha da spreadsheet.

        Args:
            row (pd.Series): Linha da spreadsheet.
            row_index (int): Índice da linha.

        Returns:
            Dict[str, Union[str, None]]: Evento processado ou erro em caso de falha.
        """
        try:
            self.validate_row(row, row_index)
            return {
                "cnpjBenef": self._format_cnpj_benef(row.get("Recolhedor")),
                "natRend": self._format_nature_of_income(row.get("Natureza de Rendimento")),
                "dtFG": self._format_date(row.get("Período Apuração")),
                "vlrBruto": self._format_value(float(row.get("Base de Cálculo") or 0)),
                "vlrBaseAgreg": self._format_value(float(row.get("Base de Cálculo") or 0)),
                "vlrAgreg": self._format_value(float(row.get("Valor Receita") or 0)),
                "perApur": self._format_period(row.get("Período Apuração")),
            }
        except ValueError as ve:
            logger.error(f"Erro de validação na linha {row_index + 1}: {ve}")
            return {"error": f"Erro de validação na linha {row_index + 1}: {ve}"}
        except Exception as e:
            logger.error(f"Erro ao preparar o event na linha {row_index + 1}: {e}")
            return {"error": f"Erro ao preparar o event na linha {row_index + 1}: {e}"}

    def generate_xml(self, event: Dict[str, str]) -> Optional[str]:
        """
        Gera o XML do event 4020.

        Args:
            event (Dict[str, str]): Dados do event.

        Returns:
            Optional[str]: XML gerado ou None em caso de erro.
        """
        try:
            event_4020: str = f"""
            <Reinf xmlns="http://www.reinf.esocial.gov.br/schemas/evt4020PagtoBeneficiarioPJ/v2_01_02">
                <evtRetPJ id="ID{self.generate_id()}">
                    <ideEvento>
                        <indRetif>{self.indRetif}</indRetif>
                        <perApur>{event['perApur']}</perApur>
                        <tpAmb>{self.tpAmb}</tpAmb>
                        <procEmi>{self.procEmi}</procEmi>
                        <verProc>{self.verProc}</verProc>
                    </ideEvento>
                    <ideContri>
                        <tpInsc>{self.tpInsc}</tpInsc>
                        <nrInsc>{self.nrInsc}</nrInsc>
                    </ideContri>
                    <ideEstab>
                        <tpInscEstab>{self.tpInscEstab}</tpInscEstab>
                        <nrInscEstab>{self.nrInscEstab}</nrInscEstab>
                        <ideBenef>
                            <cnpjBenef>{event['cnpjBenef']}</cnpjBenef>
                            <idePgto>
                                <natRend>{event['natRend']}</natRend>
                                <infoPgto>
                                    <dtFG>{event['dtFG']}</dtFG>
                                    <vlrBruto>{event['vlrBruto']}</vlrBruto>
                                    <retencoes>
                                        <vlrBaseAgreg>{event['vlrBaseAgreg']}</vlrBaseAgreg>
                                        <vlrAgreg>{event['vlrAgreg']}</vlrAgreg>
                                    </retencoes>
                                </infoPgto>
                            </idePgto>
                        </ideBenef>
                    </ideEstab>
                </evtRetPJ>
            </Reinf>"""
            return self.minify_xml(event_4020)
        except Exception as e:
            logger.error(f"Erro ao gerar XML: {e}")
            return None

    def process_spreadsheet(self) -> List[Dict[str, Union[str, None]]]:
        """
        Processa a spreadsheet e valida cada linha, preparando os eventos.

        Returns:
            List[Dict[str, Union[str, None]]]: Lista de eventos processados.
        """
        try:
            df: pd.DataFrame = pd.read_excel(self.file_path)
            events: List[Dict[str, Union[str, None]]] = []

            for row_index, row in df.iterrows():
                event = self.prepare_event(row, row_index)
                if "error" not in event:
                    events.append(event)
                else:
                    logger.info(f"Erro na linha {row_index + 1}: {event['error']}")

            return events
        except Exception as e:
            logger.error(f"Erro ao processar a spreadsheet: {e}")
            return []

    def generate_id(self):
        """Gera um ID único para o event."""
        try:
            nrInsc_formatted = str(self.nrInsc or "")
            now = datetime.datetime.now()
            formatted_date_time = now.strftime("%Y%m%d%H%M%S")
            sequential_formatted = f"{self.sequencial:05d}"
            generated_id = f"{self.tpInsc}{nrInsc_formatted}{formatted_date_time}{sequential_formatted}"
            self.sequencial += 1
            return generated_id
        except Exception as e:
            logger.error(f"Erro ao gerar ID: {e}")
            return None

    def _format_cnpj_benef(self, cnpj):
        try:
            return str(cnpj).zfill(14)
        except Exception as e:
            logger.error(f"Erro ao formatar CNPJ do beneficiário: {e}")
            return None

    def _format_nature_of_income(self, nature):
        """Formata a natureza de rendimento."""
        try:
            return str(nature).rstrip(".0") or "00000"
        except Exception as e:
            logger.error(f"Erro ao formatar a natureza de rendimento: {e}")
            return "00000"

    def _format_date(self, date):
        try:
            return (
                pd.to_datetime(date).strftime("%Y-%m-%d") if pd.notnull(date) else None
            )
        except Exception as e:
            logger.error(f"Erro ao formatar a data: {e}")
            return None

    def _format_value(self, value):
        try:
            return "{:.2f}".format(value).replace(".", ",")
        except Exception as e:
            logger.error(f"Erro ao formatar o valor: {e}")
            return "0,00"

    def _format_period(self, period):
        """
        Formata o período de apuração no formato YYYY-MM.

        Args:
            period: Período de apuração (pode ser Timestamp, string, ou None)

        Returns:
            str: Período formatado como YYYY-MM ou "00-0000" se inválido
        """
        try:
            if pd.isnull(period):
                return "00-0000"

            # Se for Timestamp, converte para string no formato YYYY-MM-DD
            if isinstance(period, pd.Timestamp):
                return period.strftime("%Y-%m")

            # Se for string, tenta extrair os primeiros 7 caracteres
            period_str = str(period)
            if len(period_str) >= 7:
                return period_str[:7]

            # Tenta converter para datetime e depois formatar
            date_obj = pd.to_datetime(period)
            return date_obj.strftime("%Y-%m")

        except Exception as e:
            logger.error(f"Erro ao formatar período: {e}")
            return "00-0000"