"""Acumula e imprime o resumo da execução."""
from dataclasses import dataclass, field


@dataclass
class Resumo:
    sucesso: list = field(default_factory=list)   # DWGs baixados
    sem_cad: list = field(default_factory=list)   # clientes sem nenhum DWG
    erro: list = field(default_factory=list)      # falhas durante o processo
    pulados: list = field(default_factory=list)   # DWGs que já existiam

    def texto_curto(self):
        """Resumo em uma linha, para a mensagem final da janela."""
        return (
            f"{len(self.sucesso)} DWG(s) baixado(s), "
            f"{len(self.pulados)} já existiam, "
            f"{len(self.sem_cad)} cliente(s) sem DWG e "
            f"{len(self.erro)} erro(s)."
        )

    def imprimir(self):
        print("\n==================================================")
        print("RESUMO FINAL")
        print("==================================================")
        self._secao("DWG baixados", self.sucesso)
        self._secao("Já existiam na pasta", self.pulados)
        self._secao("Clientes sem nenhum DWG", self.sem_cad)
        self._secao("Erros durante o processo", self.erro)

    @staticmethod
    def _secao(titulo, itens):
        print(f"\n{titulo} ({len(itens)}):")
        for item in itens:
            print(f"    - {item}")
